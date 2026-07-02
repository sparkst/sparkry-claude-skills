"""Deterministic TDD-slice harness for /qpipeline auto (Phase B).

Pure, side-effect-free cores + thin CLI wrappers for the separate-context TDD
model:

  1. validate_slices  -- the slice decomposition is a valid, complete partition:
                         every REQ-ID covered, no two slices share a file, deps
                         reference real slices, no dependency cycle.
  2. compute_waves    -- topological levels for parallel fan-out (deterministic).
  3. red_gate/green_gate -- interpret a test run: RED must fail with >=1 test
                         collected (rejects vacuous tests); GREEN must pass.
  4. check_tamper     -- prove the implementer touched only its impl files and
                         never mutated the frozen test files.

The judgment is deterministic here; the CLI wrappers gather git/test state and
hand it to these functions. Mirrors pipeline-driver.py's compositional-integrity
style. See ~/.claude/plans/qpipeline-auto-design.md (Phase B).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Slice decomposition validation
# ---------------------------------------------------------------------------

SLICE_REQUIRED_FIELDS = ("id", "files", "test_files", "req_ids", "depends_on")


def validate_slices(
    slices: list[dict[str, Any]],
    req_ids: list[str],
) -> tuple[bool, list[str]]:
    """Validate a slice decomposition. Returns (ok, errors).

    Invariants (all hard):
      - each slice has the required fields with list-typed file/req/dep fields;
      - slice ids are unique;
      - file ownership is a PARTITION — no two slices share a `files` or
        `test_files` entry (shared code must live in its own kernel slice);
      - every REQ-ID in *req_ids* is discharged by >=1 slice;
      - every depends_on entry references an existing slice id;
      - the dependency graph is acyclic.
    """
    errors: list[str] = []

    ids: list[str] = []
    for i, s in enumerate(slices):
        missing = [f for f in SLICE_REQUIRED_FIELDS if f not in s]
        if missing:
            errors.append(f"slice[{i}] missing fields: {missing}")
            continue
        for field in ("files", "test_files", "req_ids", "depends_on"):
            if not isinstance(s[field], list):
                errors.append(f"slice '{s['id']}' field '{field}' must be a list")
        ids.append(str(s["id"]))

    dup_ids = sorted({x for x in ids if ids.count(x) > 1})
    for d in dup_ids:
        errors.append(f"duplicate slice id: '{d}'")

    # File-ownership partition (impl and test namespaces checked independently).
    for field in ("files", "test_files"):
        owner: dict[str, str] = {}
        for s in slices:
            if not isinstance(s.get(field), list):
                continue
            for path in s[field]:
                if path in owner and owner[path] != s["id"]:
                    errors.append(
                        f"file '{path}' is claimed by slices '{owner[path]}' and "
                        f"'{s['id']}' ({field} must be a partition)"
                    )
                else:
                    owner[path] = s["id"]

    # REQ coverage.
    covered: set[str] = set()
    for s in slices:
        if isinstance(s.get("req_ids"), list):
            covered.update(str(r) for r in s["req_ids"])
    for req in req_ids:
        if req not in covered:
            errors.append(f"REQ '{req}' is not covered by any slice")

    # Dependency references + acyclicity.
    id_set = set(ids)
    for s in slices:
        for dep in s.get("depends_on", []) if isinstance(s.get("depends_on"), list) else []:
            if dep not in id_set:
                errors.append(f"slice '{s['id']}' depends on unknown slice '{dep}'")
    cycle_err = _detect_cycle(slices, id_set)
    if cycle_err:
        errors.append(cycle_err)

    return (not errors, errors)


def _detect_cycle(slices: list[dict[str, Any]], id_set: set[str]) -> str | None:
    """Return an error string if depends_on has a cycle, else None."""
    graph = {
        str(s["id"]): [d for d in s.get("depends_on", []) if d in id_set]
        for s in slices
        if "id" in s
    }
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}

    def visit(n: str, stack: list[str]) -> str | None:
        color[n] = GRAY
        for m in graph.get(n, []):
            if color.get(m) == GRAY:
                return "dependency cycle: " + " -> ".join(stack + [n, m])
            if color.get(m) == WHITE:
                res = visit(m, stack + [n])
                if res:
                    return res
        color[n] = BLACK
        return None

    for n in sorted(graph):
        if color[n] == WHITE:
            res = visit(n, [])
            if res:
                return res
    return None


def compute_waves(slices: list[dict[str, Any]]) -> list[list[str]]:
    """Topological levels for parallel fan-out.

    Wave 0 = slices with no dependencies; each later wave = slices whose deps are
    all in earlier waves. Ids are sorted within a wave for determinism. Raises
    ValueError on a cycle (validate first to get a friendly message).
    """
    deps = {str(s["id"]): set(s.get("depends_on", [])) for s in slices}
    resolved: set[str] = set()
    waves: list[list[str]] = []
    remaining = set(deps)

    while remaining:
        ready = sorted(sid for sid in remaining if deps[sid] <= resolved)
        if not ready:
            raise ValueError(f"cycle or unresolved dependency among: {sorted(remaining)}")
        waves.append(ready)
        resolved.update(ready)
        remaining -= set(ready)
    return waves


# ---------------------------------------------------------------------------
# Red / green gates (interpret a test run)
# ---------------------------------------------------------------------------

def red_gate(exit_code: int, tests_collected: int) -> dict[str, Any]:
    """RED must FAIL (exit != 0) AND collect >= 1 test.

    A passing red-gate means the tests are vacuous (nothing asserted / nothing
    collected) — reject so the test-writer is re-spawned.
    """
    if tests_collected < 1:
        return {"ok": False, "reason": "no tests collected — vacuous or non-discovering test file"}
    if exit_code == 0:
        return {"ok": False, "reason": "tests pass before implementation — tests do not exercise the missing behavior"}
    return {"ok": True, "reason": f"red confirmed ({tests_collected} test(s) failing pre-impl)"}


def green_gate(exit_code: int, tests_collected: int) -> dict[str, Any]:
    """GREEN must PASS (exit == 0) with the same tests still present."""
    if tests_collected < 1:
        return {"ok": False, "reason": "no tests collected at green gate — test files went missing"}
    if exit_code != 0:
        return {"ok": False, "reason": "tests still failing after implementation"}
    return {"ok": True, "reason": f"green confirmed ({tests_collected} test(s) passing)"}


# ---------------------------------------------------------------------------
# Tamper check (implementer must not touch the frozen test files)
# ---------------------------------------------------------------------------

def check_tamper(
    changed_files: list[str],
    allowed_impl_files: list[str],
    test_hashes_before: dict[str, str],
    test_hashes_after: dict[str, str],
) -> dict[str, Any]:
    """Prove the implementer stayed in scope and never mutated the tests.

    Returns {ok, violations}. Violations:
      - any changed file not in *allowed_impl_files* (scope creep / shadow tests);
      - any test file whose hash changed (or vanished/appeared) between before
        and after (the implementer edited a frozen test).
    """
    violations: list[str] = []

    allowed = set(allowed_impl_files)
    for path in changed_files:
        if path not in allowed:
            violations.append(f"out-of-scope change: '{path}' (impl may only touch {sorted(allowed)})")

    for path in sorted(set(test_hashes_before) | set(test_hashes_after)):
        before = test_hashes_before.get(path)
        after = test_hashes_after.get(path)
        if before != after:
            violations.append(f"test file mutated: '{path}' (tests are frozen for the implementer)")

    return {"ok": not violations, "violations": violations}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic TDD-slice harness.")
    sub = parser.add_subparsers(dest="command")

    vs = sub.add_parser("validate-slices", help="Validate a slice decomposition")
    vs.add_argument("--slices", required=True, help="Path to slices JSON (or - for stdin)")
    vs.add_argument("--req-ids", required=True, help="Comma-separated REQ-IDs that must be covered")

    wv = sub.add_parser("waves", help="Compute parallel waves from depends_on")
    wv.add_argument("--slices", required=True, help="Path to slices JSON (or - for stdin)")

    args = parser.parse_args(argv)

    if args.command == "validate-slices":
        slices = _load(args.slices)
        req_ids = [r.strip() for r in args.req_ids.split(",") if r.strip()]
        ok, errors = validate_slices(slices, req_ids)
        print(json.dumps({"ok": ok, "errors": errors}, indent=2))
        return 0 if ok else 1

    if args.command == "waves":
        slices = _load(args.slices)
        try:
            waves = compute_waves(slices)
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "waves": waves}, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
