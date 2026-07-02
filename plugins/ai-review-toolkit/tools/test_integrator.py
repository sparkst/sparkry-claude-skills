"""Tests for the serialized-integrator cores (Phase C of /qpipeline auto)."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "integrator", Path(__file__).with_name("integrator.py")
)
integrator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(integrator)

compute_merge_order = integrator.compute_merge_order
merge_gate = integrator.merge_gate
classify_merge_conflict = integrator.classify_merge_conflict


# A kernel + two leaf slices; S-101 and S-102 both depend on the kernel.
SLICES = [
    {"id": "S-000", "depends_on": []},
    {"id": "S-101", "depends_on": ["S-000"]},
    {"id": "S-102", "depends_on": ["S-000"]},
]


# ── compute_merge_order ──────────────────────────────────────────────────

def test_merge_order_is_serialized_and_dependency_respecting():
    res = compute_merge_order(SLICES, ["S-000", "S-101", "S-102"])
    # kernel first, then the leaves (sorted within a wave for determinism)
    assert res["order"] == ["S-000", "S-101", "S-102"]
    assert res["blocked"] == []
    assert res["skipped"] == []


def test_merge_order_skips_slices_that_never_went_green():
    res = compute_merge_order(SLICES, ["S-000", "S-101"])
    assert res["order"] == ["S-000", "S-101"]
    assert res["skipped"] == ["S-102"]
    assert res["blocked"] == []


def test_merge_order_blocks_a_green_slice_whose_dependency_failed():
    # S-101 is green but its kernel dependency S-000 is not — cannot integrate on
    # top of a missing dependency.
    res = compute_merge_order(SLICES, ["S-101", "S-102"])
    assert res["order"] == []
    assert res["blocked"] == ["S-101", "S-102"]
    assert res["skipped"] == ["S-000"]


def test_merge_order_blocks_transitively():
    chain = [
        {"id": "A", "depends_on": []},
        {"id": "B", "depends_on": ["A"]},
        {"id": "C", "depends_on": ["B"]},
    ]
    # A failed → B blocked → C blocked (even though B and C are green)
    res = compute_merge_order(chain, ["B", "C"])
    assert res["order"] == []
    assert set(res["blocked"]) == {"B", "C"}
    assert res["skipped"] == ["A"]


# ── merge_gate (interpret the full-suite run after each merge) ────────────

def test_merge_gate_advances_when_full_suite_is_green():
    g = merge_gate(exit_code=0, tests_collected=42)
    assert g["ok"] is True
    assert g["action"] == "advance"


def test_merge_gate_routes_to_conflict_resolver_on_suite_failure():
    g = merge_gate(exit_code=1, tests_collected=42)
    assert g["ok"] is False
    assert g["action"] == "resolve"


def test_merge_gate_aborts_when_the_suite_collected_nothing():
    # A zero-test run means the integration workspace is broken, not "all passing".
    g = merge_gate(exit_code=0, tests_collected=0)
    assert g["ok"] is False
    assert g["action"] == "abort"


# ── classify_merge_conflict (tests stay frozen at integration time too) ──

def test_impl_only_conflict_is_resolvable_by_the_conflict_resolver():
    c = classify_merge_conflict(
        conflicted_files=["src/a.ts", "src/b.ts"],
        test_files=["src/a.spec.ts", "src/b.spec.ts"],
    )
    assert c["resolvable"] is True
    assert c["impl_conflicts"] == ["src/a.ts", "src/b.ts"]
    assert c["test_conflicts"] == []


def test_a_conflict_touching_a_frozen_test_escalates():
    c = classify_merge_conflict(
        conflicted_files=["src/a.ts", "src/a.spec.ts"],
        test_files=["src/a.spec.ts"],
    )
    assert c["resolvable"] is False
    assert c["test_conflicts"] == ["src/a.spec.ts"]


def test_no_conflicts_is_trivially_resolvable():
    c = classify_merge_conflict(conflicted_files=[], test_files=["src/a.spec.ts"])
    assert c["resolvable"] is True
    assert c["impl_conflicts"] == []
    assert c["test_conflicts"] == []
