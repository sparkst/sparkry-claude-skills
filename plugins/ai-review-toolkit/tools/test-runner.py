"""Deterministic test discovery and execution for the AI Review Toolkit.

Discovers co-located tests for any artifact and runs them via subprocess.
Auto-classifies failures as P0/P1 findings compatible with finding-parser.py schema.

Usage:
    python tools/test-runner.py <artifact_path> [--test-cmd CMD] [--timeout SECS] [--json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


MAX_OUTPUT_SIZE = 64 * 1024  # 64 KB


def _cap_output(text: str) -> str:
    if len(text) <= MAX_OUTPUT_SIZE:
        return text
    return text[:MAX_OUTPUT_SIZE] + f"\n... [truncated at {MAX_OUTPUT_SIZE} bytes]"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class RunSpec:
    """A single discovered test run spec."""

    path: str
    type: str  # "pytest" | "vitest" | "make" | "script" | "rubric"
    command: str
    description: str


@dataclass
class RunResult:
    """Outcome of running a single RunSpec."""

    spec: RunSpec
    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass
class RunResults:
    """Aggregated results across all run specs."""

    results: list[RunResult] = field(default_factory=list)
    all_passed: bool = True
    summary: str = ""
    failures_as_findings: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def _is_executable(path: Path) -> bool:
    """Check if a file is executable."""
    return os.access(path, os.X_OK)


def _makefile_has_test_target(makefile_path: Path) -> bool:
    """Check whether a Makefile contains a 'test' target."""
    try:
        content = makefile_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    # Match lines like "test:" or "test: deps" at the start of a line
    return bool(re.search(r"^test\s*:", content, re.MULTILINE))


def discover_tests(artifact_path: str, test_cmd: str | None = None) -> list[RunSpec]:
    """Discover co-located tests for the given artifact.

    Search order:
      1. Explicit --test-cmd override
      2. Python test files (*_test.py, test_*.py) in same dir and tests/ subdir
      3. TypeScript/JS test files (*.spec.ts, *.test.ts) in same dir and tests/ subdir
      4. Makefile with 'test' target in same dir
      5. Executable test/validate/check scripts in same dir
      6. Rubric files (*.rubric.md, *.rubric.json) in same dir
    """
    specs: list[RunSpec] = []
    artifact = Path(artifact_path).resolve()

    if artifact.is_file():
        base_dir = artifact.parent
    elif artifact.is_dir():
        base_dir = artifact
    elif artifact.parent.is_dir():
        # Artifact doesn't exist yet but parent does — search siblings
        base_dir = artifact.parent
    else:
        return specs

    # 0. Explicit override ------------------------------------------------
    if test_cmd:
        specs.append(RunSpec(
            path=str(base_dir),
            type="script",
            command=test_cmd,
            description=f"Explicit test command: {test_cmd}",
        ))
        return specs

    search_dirs = [base_dir]
    tests_subdir = base_dir / "tests"
    if tests_subdir.is_dir():
        search_dirs.append(tests_subdir)

    for d in search_dirs:
        for p in sorted(d.iterdir()):
            if not p.is_file():
                continue
            name = p.name
            if (name.endswith("_test.py") or name.startswith("test_")) and name.endswith(".py"):
                specs.append(RunSpec(
                    path=str(p),
                    type="pytest",
                    command=f"{shlex.quote(sys.executable)} -m pytest {shlex.quote(str(p))} -v",
                    description=f"pytest: {p.name}",
                ))
            elif name.endswith(".spec.ts") or name.endswith(".test.ts"):
                specs.append(RunSpec(
                    path=str(p),
                    type="vitest",
                    command=f"npx vitest run {shlex.quote(str(p))} --reporter=verbose",
                    description=f"vitest: {p.name}",
                ))

    # 3. Makefile -----------------------------------------------------------
    makefile = base_dir / "Makefile"
    if makefile.is_file() and _makefile_has_test_target(makefile):
        specs.append(RunSpec(
            path=str(makefile),
            type="make",
            command=f"make -C {shlex.quote(str(base_dir))} test",
            description=f"make test in {base_dir.name}/",
        ))

    # 4. Executable scripts -------------------------------------------------
    prefixes = ("test", "validate", "check")
    for p in sorted(base_dir.iterdir()):
        if not p.is_file():
            continue
        name_lower = p.name.lower()
        # Skip Python/TS test files already captured above
        if p.suffix in (".py", ".ts"):
            continue
        if any(name_lower.startswith(pfx) for pfx in prefixes) and _is_executable(p):
            specs.append(RunSpec(
                path=str(p),
                type="script",
                command=shlex.quote(str(p)),
                description=f"script: {p.name}",
            ))

    # 5. Rubric files -------------------------------------------------------
    for p in sorted(base_dir.iterdir()):
        if not p.is_file():
            continue
        if p.name.endswith(".rubric.md") or p.name.endswith(".rubric.json"):
            specs.append(RunSpec(
                path=str(p),
                type="rubric",
                command=f"cat {shlex.quote(str(p))}",
                description=f"rubric: {p.name}",
            ))

    return specs


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_tests(specs: list[RunSpec], timeout: int = 120, round_num: int = 1) -> RunResults:
    """Execute each run spec via subprocess and collect results."""
    results: list[RunResult] = []

    for spec in specs:
        # Rubric files are informational — always pass, content in stdout
        if spec.type == "rubric":
            start = time.monotonic()
            rubric_path = Path(spec.path)
            try:
                file_size = rubric_path.stat().st_size
            except OSError:
                file_size = 0
            if file_size > 512 * 1024:
                results.append(RunResult(
                    spec=spec,
                    passed=False,
                    exit_code=1,
                    stdout="",
                    stderr=f"Rubric file exceeds 512KB limit ({file_size} bytes): {spec.path}",
                    duration_seconds=time.monotonic() - start,
                ))
                continue
            try:
                content = rubric_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                content = ""
                results.append(RunResult(
                    spec=spec,
                    passed=False,
                    exit_code=1,
                    stdout="",
                    stderr=str(exc),
                    duration_seconds=time.monotonic() - start,
                ))
                continue
            results.append(RunResult(
                spec=spec,
                passed=True,
                exit_code=0,
                stdout=content,
                stderr="",
                duration_seconds=time.monotonic() - start,
            ))
            continue

        use_shell = spec.type == "script" and any(
            c in spec.command for c in "|;&"
        )
        cmd = spec.command if use_shell else shlex.split(spec.command)

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                shell=use_shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(spec.path).parent) if Path(spec.path).is_file() else spec.path,
            )
            elapsed = time.monotonic() - start
            results.append(RunResult(
                spec=spec,
                passed=proc.returncode == 0,
                exit_code=proc.returncode,
                stdout=_cap_output(proc.stdout),
                stderr=_cap_output(proc.stderr),
                duration_seconds=elapsed,
            ))
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            results.append(RunResult(
                spec=spec,
                passed=False,
                exit_code=-1,
                stdout=_cap_output(""),
                stderr=_cap_output(f"Test timed out after {timeout}s"),
                duration_seconds=elapsed,
            ))
        except (OSError, ValueError) as exc:
            elapsed = time.monotonic() - start
            results.append(RunResult(
                spec=spec,
                passed=False,
                exit_code=-2,
                stdout=_cap_output(""),
                stderr=_cap_output(f"Failed to start: {exc}"),
                duration_seconds=elapsed,
            ))

    all_passed = all(r.passed for r in results) if results else True
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    summary = f"{passed_count}/{total_count} passed"
    if passed_count < total_count:
        summary += f", {total_count - passed_count} failed"

    test_results = RunResults(
        results=results,
        all_passed=all_passed,
        summary=summary,
    )
    test_results.failures_as_findings = failures_to_findings(test_results, round_num=round_num)
    return test_results


# ---------------------------------------------------------------------------
# Finding generation
# ---------------------------------------------------------------------------

def _extract_evidence(stderr: str, stdout: str) -> str:
    """Try to extract file:line evidence from a traceback or test output."""
    combined = stderr + "\n" + stdout
    # Python traceback: File "path", line N
    match = re.search(r'File "([^"]+)", line (\d+)', combined)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    # pytest short form: path.py:N: AssertionError
    match = re.search(r"(\S+\.py):(\d+):", combined)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    # vitest / generic: at path:line
    match = re.search(r"at\s+(\S+):(\d+)", combined)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    return ""


def failures_to_findings(
    results: RunResults,
    round_num: int = 1,
) -> list[dict[str, Any]]:
    """Convert test failures into findings compatible with finding-parser.py schema.

    Classification:
      - P0 (regression): if a test that ran in a prior round now fails (round > 1)
      - P1 (new failure): any test failure in round 1, or first-time discovery
    """
    findings: list[dict] = []
    failure_index = 0
    for r in results.results:
        if r.passed:
            continue
        severity = "P0" if round_num > 1 else "P1"
        finding_id = f"{severity}-T{failure_index + 1:03d}"
        failure_index += 1
        evidence = _extract_evidence(r.stderr, r.stdout)

        failure_detail = r.stderr.strip() or r.stdout.strip()
        if len(failure_detail) > 500:
            failure_detail = failure_detail[:500] + "..."

        findings.append({
            "id": finding_id,
            "severity": severity,
            "title": f"Test failure: {r.spec.description}",
            "requirement": "R5",
            "finding": failure_detail,
            "recommendation": "Fix the failing test",
            "source": "test-runner",
            "evidence": evidence,
            "round": round_num,
        })
    return findings


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _results_to_markdown(test_results: RunResults) -> str:
    """Render test results as Markdown."""
    lines: list[str] = []
    lines.append(f"## Test Results: {test_results.summary}\n")
    for r in test_results.results:
        icon = "PASS" if r.passed else "FAIL"
        lines.append(f"- [{icon}] {r.spec.description} ({r.duration_seconds:.2f}s)")
        if not r.passed:
            snippet = r.stderr.strip() or r.stdout.strip()
            if snippet:
                truncated = snippet[:300] + ("..." if len(snippet) > 300 else "")
                for line in truncated.splitlines():
                    lines.append(f"    {line}")
    if test_results.failures_as_findings:
        lines.append(f"\n### Auto-Generated Findings ({len(test_results.failures_as_findings)})\n")
        for f in test_results.failures_as_findings:
            lines.append(f"- **{f['id']}** ({f['severity']}): {f['title']}")
    return "\n".join(lines)


def _results_to_json(test_results: RunResults) -> str:
    """Serialize test results to JSON."""
    payload = {
        "all_passed": test_results.all_passed,
        "summary": test_results.summary,
        "results": [
            {
                "spec": asdict(r.spec),
                "passed": r.passed,
                "exit_code": r.exit_code,
                "stdout": r.stdout,
                "stderr": r.stderr,
                "duration_seconds": r.duration_seconds,
            }
            for r in test_results.results
        ],
        "failures_as_findings": test_results.failures_as_findings,
    }
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Discover and run co-located tests for an artifact.",
    )
    parser.add_argument("artifact_path", help="Path to artifact (file or directory)")
    parser.add_argument("--test-cmd", default=None, help="Explicit test command override")
    parser.add_argument("--timeout", type=int, default=120, help="Per-test timeout in seconds")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output as JSON")
    parser.add_argument("--round", type=int, default=1, dest="round_num", help="Review round number (default: 1); round > 1 classifies failures as P0 regressions")

    args = parser.parse_args(argv)

    specs = discover_tests(args.artifact_path, test_cmd=args.test_cmd)
    if not specs:
        msg = f"No tests discovered for {args.artifact_path}"
        if args.output_json:
            sys.stdout.write(json.dumps({"all_passed": True, "summary": "0/0 passed", "results": [], "failures_as_findings": [], "message": msg}) + "\n")
        else:
            sys.stdout.write(msg + "\n")
        return 0

    results = run_tests(specs, timeout=args.timeout, round_num=args.round_num)

    if args.output_json:
        sys.stdout.write(_results_to_json(results) + "\n")
    else:
        sys.stdout.write(_results_to_markdown(results) + "\n")

    return 0 if results.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
