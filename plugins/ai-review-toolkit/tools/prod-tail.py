"""Production-tail safety cores for /qpipeline auto (Phase F).

The prod tail is the only genuinely new safety primitive in the pipeline, so its
judgment is deterministic and unit-tested here — the workflow (Phase F2) gathers
deploy/smoke state and hands it to these pure functions. Matches the tdd-harness.py
/ integrator.py discipline.

  1. deploy_gate            -- the §6 GUARDRAIL GATE: a green-across-the-board
                               checklist that must ALL pass before prod publish;
                               a missing rollback command or a qdecide decline
                               refuses prod outright.
  2. aggregate_smoke        -- the curated cumulative smoke suite is all-or-nothing;
                               a zero-check run is never a pass.
  3. plan_smoke_batches     -- chunk 200+ checks for cheap parallel Haiku fan-out.
  4. rollback_decision      -- on a prod-smoke failure: auto-rollback, or (when the
                               target is stateful, decision #7) downgrade to a
                               hard-page because code rollback can't undo data.
  5. validate_smoke_suite   -- the versioned smoke/prod.suite.json each feature
                               appends its checks to.

See ~/.claude/plans/qpipeline-auto-design.md (§6, Prod model, Phase F).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def deploy_gate(state: dict[str, Any]) -> dict[str, Any]:
    """Deterministic prod GUARDRAIL GATE. Returns {allowed, blockers, checklist}.

    Every check must pass; `allowed` is true only when there are zero blockers.
    ALL blockers are listed (not just the first) so a run surfaces everything it
    must fix in one shot.
    """
    checklist: dict[str, bool] = {}
    blockers: list[str] = []

    def check(name: str, ok: bool, blocker_msg: str) -> None:
        checklist[name] = bool(ok)
        if not ok:
            blockers.append(blocker_msg)

    artifacts = state.get("artifacts", []) or []
    clean = all(int(a.get("p0", 0)) == 0 and int(a.get("p1", 0)) == 0 for a in artifacts)
    check("artifacts_zero_p0p1", bool(artifacts) and clean,
          "one or more artifacts still carry P0/P1 findings")
    check("unit_green", state.get("unit_green") is True, "unit suite is not green")
    check("integration_green", state.get("integration_green") is True, "integration suite is not green")

    smoke = state.get("staging_smoke") or {}
    total = int(smoke.get("total", 0))
    passed = int(smoke.get("passed", 0))
    check("staging_smoke_100", total > 0 and passed == total,
          f"staging smoke not 100% ({passed}/{total})")

    check("rollback_present", state.get("rollback_cmd_present") is True,
          "no rollbackCmd declared — prod is REFUSED without a validated rollback")
    check("rollback_dry_ok", state.get("rollback_dry_ok") is True,
          "rollbackCmd failed dry validation")
    check("prod_smoke_reviewed", state.get("prod_smoke_reviewed") is True,
          "prod smoke assertions were not reviewed up front")
    check("new_smoke_checks_added", state.get("new_smoke_checks_added") is True,
          "this feature added no new smoke check for its new behavior")
    check("qdecide_not_decline", state.get("qdecide_decision") != "decline",
          "qdecide returned decline — prod is blocked")
    check("authorized", state.get("prod_autonomous") is True or state.get("human_confirmed") is True,
          "neither prodAutonomous nor a human confirmation is present")

    return {"allowed": not blockers, "blockers": blockers, "checklist": checklist}


def aggregate_smoke(results: list[dict[str, Any]]) -> dict[str, Any]:
    """The smoke suite is all-or-nothing. A zero-check run is never a pass."""
    failed = [str(r.get("id")) for r in results if not r.get("passed")]
    total = len(results)
    return {
        "ok": total > 0 and not failed,
        "total": total,
        "passed": total - len(failed),
        "failed": failed,
    }


def plan_smoke_batches(checks: list[Any], batch_size: int) -> list[list[Any]]:
    """Chunk checks (order-preserving) into batches for parallel Haiku fan-out."""
    size = max(1, int(batch_size))
    return [checks[i:i + size] for i in range(0, len(checks), size)]


def rollback_decision(*, smoke_failed: bool, stateful: bool, rollback_present: bool) -> dict[str, Any]:
    """Decide what to do on a prod-smoke result.

    - smoke passed → nothing.
    - stateful target → hard-page (code rollback can't undo DB/KV/R2 mutations; #7).
    - no rollback command → hard-page (should never reach prod; fail-safe).
    - otherwise → auto-rollback.
    """
    if not smoke_failed:
        return {"action": "none", "reason": "prod smoke passed"}
    if stateful:
        return {"action": "hard-page",
                "reason": "stateful target — code rollback cannot undo data mutations; page a human"}
    if not rollback_present:
        return {"action": "hard-page", "reason": "no rollbackCmd available to auto-rollback"}
    return {"action": "rollback", "reason": "stateless target with a validated rollback — auto-rolling back"}


SMOKE_CHECK_REQUIRED = ("id", "description", "feature")


def validate_smoke_suite(suite: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the cumulative smoke/prod.suite.json: unique ids + required fields."""
    errors: list[str] = []
    checks = suite.get("checks", [])
    if not isinstance(checks, list):
        return False, ["`checks` must be a list"]

    seen: set[str] = set()
    for i, c in enumerate(checks):
        missing = [f for f in SMOKE_CHECK_REQUIRED if not c.get(f)]
        if missing:
            errors.append(f"check[{i}] missing fields: {missing}")
        cid = c.get("id")
        if cid in seen:
            errors.append(f"duplicate smoke check id: '{cid}'")
        elif cid:
            seen.add(cid)
    return (not errors, errors)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Production-tail safety cores.")
    sub = parser.add_subparsers(dest="command")

    dg = sub.add_parser("deploy-gate", help="Evaluate the prod guardrail gate")
    dg.add_argument("--state", required=True, help="Path to gate-state JSON (or - for stdin)")

    vs = sub.add_parser("validate-suite", help="Validate a smoke suite JSON")
    vs.add_argument("--suite", required=True, help="Path to smoke suite JSON (or - for stdin)")

    args = parser.parse_args(argv)

    if args.command == "deploy-gate":
        res = deploy_gate(_load(args.state))
        print(json.dumps(res, indent=2))
        return 0 if res["allowed"] else 1

    if args.command == "validate-suite":
        ok, errors = validate_smoke_suite(_load(args.suite))
        print(json.dumps({"ok": ok, "errors": errors}, indent=2))
        return 0 if ok else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
