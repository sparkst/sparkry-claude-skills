"""Tests for the production-tail safety cores (Phase F1 of /qpipeline auto)."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "prod_tail", Path(__file__).with_name("prod-tail.py")
)
prod_tail = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prod_tail)

deploy_gate = prod_tail.deploy_gate
aggregate_smoke = prod_tail.aggregate_smoke
plan_smoke_batches = prod_tail.plan_smoke_batches
rollback_decision = prod_tail.rollback_decision
validate_smoke_suite = prod_tail.validate_smoke_suite


# A fully-green state that SHOULD be allowed to deploy to prod.
GREEN_STATE = {
    "artifacts": [{"name": "REQUIREMENTS.md", "p0": 0, "p1": 0}, {"name": "src", "p0": 0, "p1": 0}],
    "unit_green": True,
    "integration_green": True,
    "staging_smoke": {"total": 210, "passed": 210},
    "rollback_cmd_present": True,
    "rollback_dry_ok": True,
    "prod_smoke_reviewed": True,
    "new_smoke_checks_added": True,
    "qdecide_decision": "draft",
    "prod_autonomous": True,
    "human_confirmed": False,
}


# ── deploy_gate (the §6 deterministic guardrail checklist) ───────────────

def test_deploy_gate_allows_a_fully_green_state():
    g = deploy_gate(GREEN_STATE)
    assert g["allowed"] is True
    assert g["blockers"] == []


def test_deploy_gate_blocks_when_any_artifact_has_a_p0_or_p1():
    state = {**GREEN_STATE, "artifacts": [{"name": "src", "p0": 0, "p1": 1}]}
    g = deploy_gate(state)
    assert g["allowed"] is False
    assert any("P0/P1" in b for b in g["blockers"])


def test_deploy_gate_refuses_prod_without_a_rollback_command():
    # Absent/dry-invalid rollback → prod REFUSED even under prodAutonomous.
    g = deploy_gate({**GREEN_STATE, "rollback_cmd_present": False})
    assert g["allowed"] is False
    assert any("rollback" in b.lower() for b in g["blockers"])
    g2 = deploy_gate({**GREEN_STATE, "rollback_dry_ok": False})
    assert g2["allowed"] is False


def test_deploy_gate_blocks_a_qdecide_decline():
    g = deploy_gate({**GREEN_STATE, "qdecide_decision": "decline"})
    assert g["allowed"] is False
    assert any("decline" in b.lower() for b in g["blockers"])


def test_deploy_gate_blocks_on_staging_smoke_below_100_percent():
    g = deploy_gate({**GREEN_STATE, "staging_smoke": {"total": 210, "passed": 209}})
    assert g["allowed"] is False
    assert any("staging" in b.lower() for b in g["blockers"])


def test_deploy_gate_requires_the_feature_to_add_its_smoke_checks():
    # A feature that ships no new smoke check for its new behavior fails the gate.
    g = deploy_gate({**GREEN_STATE, "new_smoke_checks_added": False})
    assert g["allowed"] is False
    assert any("smoke" in b.lower() for b in g["blockers"])


def test_deploy_gate_requires_autonomous_or_human_confirmation():
    g = deploy_gate({**GREEN_STATE, "prod_autonomous": False, "human_confirmed": False})
    assert g["allowed"] is False
    assert any("confirm" in b.lower() or "autonomous" in b.lower() for b in g["blockers"])
    # human confirmation alone is sufficient
    g2 = deploy_gate({**GREEN_STATE, "prod_autonomous": False, "human_confirmed": True})
    assert g2["allowed"] is True


def test_deploy_gate_lists_every_blocker_not_just_the_first():
    bad = {**GREEN_STATE, "unit_green": False, "integration_green": False, "qdecide_decision": "decline"}
    g = deploy_gate(bad)
    assert g["allowed"] is False
    assert len(g["blockers"]) >= 3


# ── aggregate_smoke (all checks must pass) ───────────────────────────────

def test_aggregate_smoke_ok_when_all_pass():
    r = aggregate_smoke([{"id": "c1", "passed": True}, {"id": "c2", "passed": True}])
    assert r["ok"] is True
    assert r["total"] == 2 and r["passed"] == 2 and r["failed"] == []


def test_aggregate_smoke_fails_and_names_the_failures():
    r = aggregate_smoke([{"id": "c1", "passed": True}, {"id": "c2", "passed": False}])
    assert r["ok"] is False
    assert r["failed"] == ["c2"]


def test_aggregate_smoke_empty_is_not_ok():
    # Zero checks means the suite didn't run — never a pass.
    r = aggregate_smoke([])
    assert r["ok"] is False


# ── plan_smoke_batches (parallel fan-out for 200+ checks) ─────────────────

def test_plan_smoke_batches_chunks_in_order():
    checks = [f"c{i}" for i in range(10)]
    batches = plan_smoke_batches(checks, 4)
    assert batches == [["c0", "c1", "c2", "c3"], ["c4", "c5", "c6", "c7"], ["c8", "c9"]]


def test_plan_smoke_batches_handles_200_plus_cheaply():
    batches = plan_smoke_batches([f"c{i}" for i in range(205)], 25)
    assert sum(len(b) for b in batches) == 205
    assert all(len(b) <= 25 for b in batches)


# ── rollback_decision (§6 + stateful downgrade, decision #7) ─────────────

def test_rollback_not_needed_when_smoke_passed():
    assert rollback_decision(smoke_failed=False, stateful=False, rollback_present=True)["action"] == "none"


def test_rollback_auto_rolls_back_a_stateless_failure():
    d = rollback_decision(smoke_failed=True, stateful=False, rollback_present=True)
    assert d["action"] == "rollback"


def test_rollback_downgrades_to_hard_page_when_stateful():
    # Code rollback cannot undo DB/KV/R2 mutations → page a human, do not auto-rollback.
    d = rollback_decision(smoke_failed=True, stateful=True, rollback_present=True)
    assert d["action"] == "hard-page"
    assert "stateful" in d["reason"].lower()


def test_rollback_hard_pages_when_no_rollback_command():
    d = rollback_decision(smoke_failed=True, stateful=False, rollback_present=False)
    assert d["action"] == "hard-page"


# ── validate_smoke_suite (the curated cumulative artifact) ───────────────

def test_valid_smoke_suite_passes():
    suite = {"version": 3, "checks": [
        {"id": "SMK-001", "description": "home 200", "feature": "F-1"},
        {"id": "SMK-002", "description": "login 200", "feature": "F-2"},
    ]}
    ok, errors = validate_smoke_suite(suite)
    assert ok is True and errors == []


def test_smoke_suite_rejects_duplicate_ids():
    suite = {"version": 1, "checks": [
        {"id": "SMK-001", "description": "a", "feature": "F-1"},
        {"id": "SMK-001", "description": "b", "feature": "F-2"},
    ]}
    ok, errors = validate_smoke_suite(suite)
    assert ok is False
    assert any("SMK-001" in e for e in errors)


def test_smoke_suite_rejects_missing_required_fields():
    suite = {"version": 1, "checks": [{"id": "SMK-001"}]}
    ok, errors = validate_smoke_suite(suite)
    assert ok is False
