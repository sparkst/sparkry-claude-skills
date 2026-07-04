"""Serialized-integrator cores for /qpipeline auto (Phase C).

After the per-slice TDD waves (Phase B) run in parallel worktrees, a SERIALIZED
integrator merges each green worktree back one at a time — the only serialization
point — running the full suite after every merge and, on failure, an impl-only
conflict-resolver. This module is the PURE, side-effect-free decision layer for
that barrier, matching tdd-harness.py's discipline: the workflow (Phase E) gathers
git/test state and hands it to these functions.

  1. compute_merge_order     -- the serialized, dependency-respecting order in
                                which green slices merge (kernel first); a green
                                slice whose dependency never went green is blocked.
  2. merge_gate              -- interpret the full-suite run after one merge:
                                advance / resolve (conflict-resolver) / abort.
  3. classify_merge_conflict -- tests stay FROZEN at integration time too — an
                                impl-only conflict is resolvable, a conflict that
                                touches a test file escalates.

See ~/.claude/plans/qpipeline-auto-design.md (Phase C).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

# tdd-harness.py is hyphenated (not a normal import name); load compute_waves from
# it by path so the topological wave ordering has a single source of truth.
_HARNESS = Path(__file__).with_name("tdd-harness.py")
_spec = importlib.util.spec_from_file_location("tdd_harness", _HARNESS)
_tdd_harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tdd_harness)
compute_waves = _tdd_harness.compute_waves


def compute_merge_order(
    slices: list[dict[str, Any]],
    green_ids: list[str],
    merged_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Serialized merge order over the green slices.

    Returns {"order", "blocked", "skipped"}:
      - order:   slice ids in dependency-topological order, restricted to slices
                 that are green AND whose dependencies are all (transitively)
                 integrable. Kernel (no deps) merges first.
      - blocked: green slices that cannot integrate because a dependency never
                 went green (directly or transitively).
      - skipped: slices that are not green at all (already-merged slices are
                 neither skipped nor re-ordered).

    `merged_ids` are slices already integrated in earlier waves — their
    dependencies count as satisfied. Wave-by-wave callers pass the accumulated
    merged set; all-at-once callers omit it for the legacy semantics.

    The workflow merges `order` one worktree at a time; `blocked`/`skipped`
    surface to the escalation broker.
    """
    green = set(green_ids)
    merged = set(merged_ids or [])
    deps = {str(s["id"]): set(s.get("depends_on", [])) for s in slices}

    order: list[str] = []
    blocked: list[str] = []
    integrable: set[str] = set(merged)

    for wave in compute_waves(slices):
        for sid in wave:  # already sorted within a wave for determinism
            if sid in merged:
                continue  # already on main → nothing to order
            if sid not in green:
                continue  # not green → skipped, not blocked
            if deps[sid] <= integrable:
                order.append(sid)
                integrable.add(sid)
            else:
                blocked.append(sid)

    skipped = sorted(set(deps) - green - merged)
    return {"order": order, "blocked": sorted(blocked), "skipped": skipped}


def merge_gate(exit_code: int, tests_collected: int) -> dict[str, Any]:
    """Interpret the FULL-suite run after merging one worktree.

    - collected 0 tests → the integration workspace is broken (not "all passing");
      abort and escalate rather than falsely advancing.
    - exit != 0 → a real regression the merge introduced; hand to the impl-only
      conflict-resolver.
    - exit == 0 with tests collected → advance to the next worktree.
    """
    if tests_collected < 1:
        return {
            "ok": False,
            "action": "abort",
            "reason": "full suite collected no tests after merge — integration workspace broken",
        }
    if exit_code != 0:
        return {
            "ok": False,
            "action": "resolve",
            "reason": "full suite failing after merge — invoke the impl-only conflict-resolver",
        }
    return {
        "ok": True,
        "action": "advance",
        "reason": f"full suite green after merge ({tests_collected} test(s))",
    }


def classify_merge_conflict(
    conflicted_files: list[str],
    test_files: list[str],
) -> dict[str, Any]:
    """Split a set of git-reported conflicted paths into impl vs frozen-test.

    Tests are the frozen contract at integration time exactly as during
    implementation: a conflict confined to impl files is resolvable by the
    conflict-resolver, but any conflict touching a test file must escalate (the
    resolver is forbidden from editing tests).
    """
    frozen = set(test_files)
    impl_conflicts = [f for f in conflicted_files if f not in frozen]
    test_conflicts = [f for f in conflicted_files if f in frozen]
    return {
        "resolvable": not test_conflicts,
        "impl_conflicts": impl_conflicts,
        "test_conflicts": test_conflicts,
        "reason": (
            "conflict touches frozen test file(s) — escalate, the resolver may not edit tests"
            if test_conflicts
            else "impl-only conflict — resolvable by the conflict-resolver"
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serialized-integrator cores.")
    sub = parser.add_subparsers(dest="command")

    mo = sub.add_parser("merge-order", help="Serialized merge order over green slices")
    mo.add_argument("--slices", required=True, help="Path to slices JSON (or - for stdin)")
    mo.add_argument("--green", required=True, help="Comma-separated ids of slices that passed the green gate")
    mo.add_argument("--merged", default="", help="Comma-separated ids of slices already integrated in earlier waves (their deps count as satisfied)")

    args = parser.parse_args(argv)

    if args.command == "merge-order":
        slices = _load(args.slices)
        green = [g.strip() for g in args.green.split(",") if g.strip()]
        merged = [m.strip() for m in args.merged.split(",") if m.strip()]
        res = compute_merge_order(slices, green, merged_ids=merged)
        print(json.dumps(res, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
