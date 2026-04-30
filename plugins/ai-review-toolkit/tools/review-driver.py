"""Review driver for /qreview skill.

State machine that manages the multi-agent review lifecycle.
Creates review state, generates reviewer prompts, records findings,
and runs synthesis.

Usage:
    python tools/review-driver.py init --artifact PATH --requirements PATH [--reviewers N] [--catalog PATH]
    python tools/review-driver.py status
    python tools/review-driver.py synthesize
    python tools/review-driver.py reset
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve sibling tool imports
# ---------------------------------------------------------------------------

from tools._loader import load_sibling as _load_sibling


def _get_finding_parser() -> Any:
    return _load_sibling("finding-parser.py")


def _get_test_runner() -> Any:
    return _load_sibling("test-runner.py")


def _get_team_selector() -> Any:
    return _load_sibling("team-selector.py")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR_NAME = ".qreview"
STATE_FILE_NAME = "state.json"

REVIEWER_PROMPT_TEMPLATE = """\
You are a {reviewer_name} reviewing an artifact.

Your review lens: {review_lens}

## Artifact

{artifact_content}

## Requirements

{requirements_content}

## Test Results

{test_results_summary}

## Instructions

Review the artifact against the requirements through your lens of {review_lens}.
Read only files relevant to your review domain. Use Grep to find relevant sections rather than reading entire files.

Output your findings as a JSON array. Each finding must have these fields:
- id: string matching pattern P[0-3]-NNN (e.g., P0-001, P1-002)
- severity: one of P0, P1, P2, P3
- title: concise description of the issue
- requirement: which requirement this relates to
- finding: detailed description of the problem
- recommendation: how to fix it
- source: "{reviewer_name}"
- evidence: file path and line number if applicable

Severity guide:
- P0: Blocks shipping (correctness, security, data loss, requirement violation)
- P1: Must fix before v1 (quality, error handling, incomplete coverage)
- P2: Should fix (code smell, suboptimal pattern, minor UX, doc gap)
- P3: Nice to have (style, optional optimization, cosmetic)

Output ONLY the JSON array. No other text.\
"""


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _state_dir(base: str | None = None) -> Path:
    """Return the .qreview directory path."""
    root = Path(base) if base else Path.cwd()
    return root / STATE_DIR_NAME


def _state_path(base: str | None = None) -> Path:
    return _state_dir(base) / STATE_FILE_NAME


def _read_state(base: str | None = None) -> dict[str, Any]:
    """Read state from disk. Raises FileNotFoundError if missing."""
    path = _state_path(base)
    if not path.exists():
        raise FileNotFoundError(
            f"No review state found at {path}. Run 'init' first."
        )
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"State file corrupt at {path}. Run 'reset' to clear."
            ) from exc


def _write_state(state: dict[str, Any], base: str | None = None) -> None:
    """Write state to disk atomically, creating the directory if needed."""
    d = _state_dir(base)
    d.mkdir(parents=True, exist_ok=True)
    target = _state_path(base)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    fd, tmp = tempfile.mkstemp(dir=str(d), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, default=str)
        os.replace(tmp, str(target))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


MAX_FILE_SIZE = 512 * 1024  # 512 KB


def _read_file_safe(path: str) -> str:
    """Read a file, raising if it does not exist or exceeds size limit."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    size = p.stat().st_size
    if size > MAX_FILE_SIZE:
        raise ValueError(
            f"File too large ({size} bytes, limit {MAX_FILE_SIZE}): {path}"
        )
    return p.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def init_review(
    artifact_path: str,
    requirements_path: str,
    reviewer_count: int | None = None,
    catalog_path: str | None = None,
    base_dir: str | None = None,
) -> dict[str, Any]:
    """Set up review state. Discover tests and select team.

    Returns the full state dict with team composition and test results.
    """
    # Validate inputs
    artifact_abs = str(Path(artifact_path).resolve())
    requirements_abs = str(Path(requirements_path).resolve())

    if not Path(artifact_abs).exists():
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")
    if not Path(requirements_abs).exists():
        raise FileNotFoundError(f"Requirements not found: {requirements_path}")

    # Read files for description-based domain classification
    artifact_content = _read_file_safe(artifact_abs)
    requirements_content = _read_file_safe(requirements_abs)

    # Discover and run tests
    test_runner = _get_test_runner()
    specs = test_runner.discover_tests(artifact_abs)
    if specs:
        test_results_obj = test_runner.run_tests(specs)
        test_results: dict[str, Any] = {
            "all_passed": test_results_obj.all_passed,
            "summary": test_results_obj.summary,
            "failures_as_findings": test_results_obj.failures_as_findings,
        }
    else:
        test_results = {
            "all_passed": True,
            "summary": "0/0 passed (no tests discovered)",
            "failures_as_findings": [],
        }

    # Select team
    team_selector = _get_team_selector()
    description = f"{requirements_content[:500]}\n{artifact_content[:500]}"
    min_rev = max(reviewer_count or 2, 2)
    max_rev = max(reviewer_count or 5, min_rev)

    team_agents = team_selector.select_team(
        description=description,
        artifact_path=artifact_abs,
        min_reviewers=min_rev,
        max_reviewers=max_rev,
        catalog_path=catalog_path,
    )

    team_dicts: list[dict[str, Any]] = [
        {"name": agent.name, "model": agent.model, "review_lens": agent.review_lens}
        for agent in team_agents
    ]

    state: dict[str, Any] = {
        "artifact_path": artifact_abs,
        "requirements_path": requirements_abs,
        "team": team_dicts,
        "test_results": test_results,
        "reviewer_outputs": {},
        "synthesis": None,
        "convergence_threshold": 0,
        "status": "initialized",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    _write_state(state, base_dir)
    return state


def get_reviewer_prompt(state: dict[str, Any], reviewer_index: int) -> str:
    """Generate the prompt for a specific reviewer agent.

    Includes artifact content, requirements, test results, and the
    reviewer's specific lens. Does NOT include prior findings or
    implementation context beyond the artifact.
    """
    team = state.get("team", [])
    if reviewer_index < 0 or reviewer_index >= len(team):
        raise IndexError(
            f"Reviewer index {reviewer_index} out of range "
            f"(team size: {len(team)})"
        )

    reviewer = team[reviewer_index]
    artifact_content = _read_file_safe(state["artifact_path"])
    requirements_content = _read_file_safe(state["requirements_path"])

    test_results = state.get("test_results", {})
    test_summary = test_results.get("summary", "No tests run")
    failures = test_results.get("failures_as_findings", [])
    if failures:
        failure_lines = [f"- {f['title']}: {f['finding'][:200]}" for f in failures]
        test_results_summary = f"{test_summary}\n\nFailures:\n" + "\n".join(failure_lines)
    else:
        test_results_summary = test_summary

    return REVIEWER_PROMPT_TEMPLATE.format(
        reviewer_name=reviewer["name"],
        review_lens=reviewer["review_lens"],
        artifact_content=artifact_content,
        requirements_content=requirements_content,
        test_results_summary=test_results_summary,
    )


def record_findings(
    state: dict[str, Any],
    reviewer_index: int,
    findings_raw: str,
    base_dir: str | None = None,
) -> list[dict[str, Any]]:
    """Parse a reviewer's raw output into structured findings.

    Validates each finding via finding-parser. Returns the list of valid
    findings. Updates state on disk.
    """
    team = state.get("team", [])
    if reviewer_index < 0 or reviewer_index >= len(team):
        raise IndexError(
            f"Reviewer index {reviewer_index} out of range "
            f"(team size: {len(team)})"
        )

    if state.get("status") == "synthesized":
        raise ValueError(
            "Review is already synthesized; cannot accept new findings."
        )

    if str(reviewer_index) in state.get("reviewer_outputs", {}):
        raise ValueError(
            f"Reviewer {reviewer_index} already submitted findings."
        )

    finding_parser = _get_finding_parser()

    parsed_findings: list[dict[str, Any]] = []
    try:
        parsed_findings = json.loads(findings_raw)
        if not isinstance(parsed_findings, list):
            parsed_findings = [parsed_findings]
    except json.JSONDecodeError:
        greedy_match = re.search(r"\[.*\]", findings_raw, re.DOTALL)
        if greedy_match:
            try:
                candidate = json.loads(greedy_match.group())
                if isinstance(candidate, list):
                    parsed_findings = candidate
            except json.JSONDecodeError:
                pass
        if not parsed_findings:
            for match in re.finditer(r"\[.*?\]", findings_raw, re.DOTALL):
                try:
                    candidate = json.loads(match.group())
                    if isinstance(candidate, list):
                        parsed_findings = candidate
                        break
                except json.JSONDecodeError:
                    continue

    valid_findings: list[dict[str, Any]] = []
    dropped_count = 0
    for finding in parsed_findings:
        if not isinstance(finding, dict):
            dropped_count += 1
            continue
        is_valid, errors = finding_parser.validate_finding(finding)
        if is_valid:
            valid_findings.append(finding)
        else:
            dropped_count += 1

    # Record in state
    state["reviewer_outputs"][str(reviewer_index)] = valid_findings
    if dropped_count > 0:
        state.setdefault("validation_dropped", {})[str(reviewer_index)] = dropped_count
    state["status"] = "reviewing"
    _write_state(state, base_dir)

    return valid_findings


def synthesize_round(
    state: dict[str, Any],
    threshold: int | None = None,
    base_dir: str | None = None,
) -> dict[str, Any]:
    """Run synthesis across all reviewer findings.

    Args:
        state: Current review state dict.
        threshold: Convergence threshold for low-severity findings.
            If None, reads from state (set at init, default 0).
        base_dir: Override base directory for state persistence.

    Returns a dict with counts, sorted findings, and convergence check.
    Updates state on disk.
    """
    finding_parser = _get_finding_parser()

    if threshold is None:
        threshold = state.get("convergence_threshold", 0)

    team_size = len(state.get("team", []))
    reported = len(state.get("reviewer_outputs", {}))
    if reported < team_size:
        missing = [
            i for i in range(team_size)
            if str(i) not in state.get("reviewer_outputs", {})
        ]
        raise ValueError(
            f"Only {reported} of {team_size} reviewers have submitted findings. "
            f"Missing: {missing}. All reviewers must report before synthesis."
        )

    # Collect all reviewer findings
    reviewer_results: list[list[dict[str, Any]]] = list(
        state.get("reviewer_outputs", {}).values()
    )

    # Include test failure findings
    test_failures = state.get("test_results", {}).get("failures_as_findings", [])
    if test_failures:
        reviewer_results.append(test_failures)

    # Synthesize: validate, deduplicate (max-severity), sort
    warnings: list[dict[str, object]] = []
    synthesized = finding_parser.synthesize_findings(reviewer_results, warnings=warnings)

    # Count by severity
    counts = finding_parser.count_by_severity(synthesized)

    # Check convergence
    converged, convergence_message = finding_parser.check_convergence(
        synthesized, threshold=threshold
    )

    synthesis: dict[str, Any] = {
        "findings": synthesized,
        "counts": counts,
        "total": len(synthesized),
        "converged": converged,
        "convergence_message": convergence_message,
        "dropped_count": len(warnings),
    }
    if warnings:
        synthesis["dropped_findings"] = warnings

    state["synthesis"] = synthesis
    state["status"] = "synthesized"
    _write_state(state, base_dir)

    return synthesis


def get_status(base_dir: str | None = None) -> dict[str, Any]:
    """Read and return the current review state from disk."""
    return _read_state(base_dir)


def reset(base_dir: str | None = None) -> None:
    """Clear the .qreview state directory."""
    d = _state_dir(base_dir)
    if d.exists():
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_team(state: dict[str, Any]) -> None:
    """Print team composition."""
    team = state.get("team", [])
    print(f"\nReview team ({len(team)} reviewers):")
    for i, reviewer in enumerate(team):
        print(f"  {i}. {reviewer['name']} ({reviewer['model']}) -- {reviewer['review_lens']}")


def _print_test_results(state: dict[str, Any]) -> None:
    """Print test results summary."""
    tr = state.get("test_results", {})
    print(f"\nTest results: {tr.get('summary', 'N/A')}")
    failures = tr.get("failures_as_findings", [])
    if failures:
        print(f"  {len(failures)} failure(s) auto-classified as findings")


def _print_synthesis(synthesis: dict[str, Any]) -> None:
    """Print synthesis results."""
    counts = synthesis.get("counts", {})
    total = synthesis.get("total", 0)
    converged = synthesis.get("converged", False)
    msg = synthesis.get("convergence_message", "")

    print(f"\nSynthesis: {total} finding(s)")
    print(f"  P0={counts.get('P0', 0)}  P1={counts.get('P1', 0)}  "
          f"P2={counts.get('P2', 0)}  P3={counts.get('P3', 0)}")
    print(f"  Convergence: {'YES' if converged else 'NO'} -- {msg}")

    findings = synthesis.get("findings", [])
    if findings:
        finding_parser = _get_finding_parser()
        print(f"\n{finding_parser.format_findings(findings)}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Review driver for /qreview skill.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a review")
    init_parser.add_argument("--artifact", required=True, help="Path to artifact")
    init_parser.add_argument("--requirements", required=True, help="Path to requirements")
    init_parser.add_argument("--reviewers", type=int, default=None, help="Number of reviewers")
    init_parser.add_argument("--catalog", default=None, help="Path to custom agent catalog")

    # status
    subparsers.add_parser("status", help="Show current review status")

    # synthesize
    subparsers.add_parser("synthesize", help="Synthesize findings")

    # reset
    subparsers.add_parser("reset", help="Clear review state")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "init":
        try:
            state = init_review(
                artifact_path=args.artifact,
                requirements_path=args.requirements,
                reviewer_count=args.reviewers,
                catalog_path=args.catalog,
            )
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Review initialized: {state['status']}")
        _print_team(state)
        _print_test_results(state)
        return 0

    if args.command == "status":
        try:
            state = get_status()
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Status: {state['status']}")
        print(f"Artifact: {state.get('artifact_path', 'N/A')}")
        _print_team(state)
        _print_test_results(state)
        outputs = state.get("reviewer_outputs", {})
        print(f"\nReviewer outputs: {len(outputs)} recorded")
        if state.get("synthesis"):
            _print_synthesis(state["synthesis"])
        return 0

    if args.command == "synthesize":
        try:
            state = get_status()
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        synthesis = synthesize_round(state)
        _print_synthesis(synthesis)
        return 0

    if args.command == "reset":
        reset()
        print("Review state cleared.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
