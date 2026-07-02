"""Tests for tdd-harness.py — the deterministic TDD-slice cores (Phase B)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

h = load_sibling("tdd-harness.py")


def _slice(sid, files, test_files, req_ids, depends_on=None):
    return {
        "id": sid, "files": files, "test_files": test_files,
        "req_ids": req_ids, "depends_on": depends_on or [],
        "public_contract": "f()",
    }


class TestValidateSlices:
    def test_valid_partition_covering_all_reqs(self):
        slices = [
            _slice("S-001", ["src/a.py"], ["tests/a.py"], ["REQ-1"]),
            _slice("S-002", ["src/b.py"], ["tests/b.py"], ["REQ-2"], ["S-001"]),
        ]
        ok, errors = h.validate_slices(slices, ["REQ-1", "REQ-2"])
        assert ok, errors

    def test_uncovered_req_fails(self):
        slices = [_slice("S-001", ["src/a.py"], ["tests/a.py"], ["REQ-1"])]
        ok, errors = h.validate_slices(slices, ["REQ-1", "REQ-2"])
        assert not ok
        assert any("REQ-2" in e for e in errors)

    def test_shared_impl_file_breaks_partition(self):
        slices = [
            _slice("S-001", ["src/shared.py"], ["tests/a.py"], ["REQ-1"]),
            _slice("S-002", ["src/shared.py"], ["tests/b.py"], ["REQ-2"]),
        ]
        ok, errors = h.validate_slices(slices, ["REQ-1", "REQ-2"])
        assert not ok
        assert any("src/shared.py" in e and "partition" in e for e in errors)

    def test_shared_test_file_breaks_partition(self):
        slices = [
            _slice("S-001", ["src/a.py"], ["tests/shared.py"], ["REQ-1"]),
            _slice("S-002", ["src/b.py"], ["tests/shared.py"], ["REQ-2"]),
        ]
        ok, errors = h.validate_slices(slices, ["REQ-1", "REQ-2"])
        assert not ok
        assert any("tests/shared.py" in e for e in errors)

    def test_duplicate_ids_fail(self):
        slices = [
            _slice("S-001", ["src/a.py"], ["tests/a.py"], ["REQ-1"]),
            _slice("S-001", ["src/b.py"], ["tests/b.py"], ["REQ-1"]),
        ]
        ok, errors = h.validate_slices(slices, ["REQ-1"])
        assert not ok
        assert any("duplicate slice id" in e for e in errors)

    def test_unknown_dependency_fails(self):
        slices = [_slice("S-001", ["src/a.py"], ["tests/a.py"], ["REQ-1"], ["S-999"])]
        ok, errors = h.validate_slices(slices, ["REQ-1"])
        assert not ok
        assert any("S-999" in e for e in errors)

    def test_dependency_cycle_detected(self):
        slices = [
            _slice("S-001", ["src/a.py"], ["tests/a.py"], ["REQ-1"], ["S-002"]),
            _slice("S-002", ["src/b.py"], ["tests/b.py"], ["REQ-2"], ["S-001"]),
        ]
        ok, errors = h.validate_slices(slices, ["REQ-1", "REQ-2"])
        assert not ok
        assert any("cycle" in e for e in errors)


class TestComputeWaves:
    def test_independent_slices_share_wave_zero(self):
        slices = [
            _slice("S-002", ["b"], ["tb"], ["R2"]),
            _slice("S-001", ["a"], ["ta"], ["R1"]),
        ]
        assert h.compute_waves(slices) == [["S-001", "S-002"]]

    def test_dependency_chains_form_later_waves(self):
        slices = [
            _slice("S-000", ["k"], ["tk"], ["R0"]),
            _slice("S-001", ["a"], ["ta"], ["R1"], ["S-000"]),
            _slice("S-002", ["b"], ["tb"], ["R2"], ["S-000"]),
            _slice("S-003", ["c"], ["tc"], ["R3"], ["S-001", "S-002"]),
        ]
        assert h.compute_waves(slices) == [["S-000"], ["S-001", "S-002"], ["S-003"]]

    def test_cycle_raises(self):
        slices = [
            _slice("S-001", ["a"], ["ta"], ["R1"], ["S-002"]),
            _slice("S-002", ["b"], ["tb"], ["R2"], ["S-001"]),
        ]
        try:
            h.compute_waves(slices)
            assert False, "expected ValueError"
        except ValueError:
            pass


class TestRedGreenGates:
    def test_red_requires_failure_with_tests(self):
        assert h.red_gate(1, 3)["ok"] is True
        assert h.red_gate(0, 3)["ok"] is False  # passes pre-impl → bad tests
        assert h.red_gate(1, 0)["ok"] is False  # nothing collected → vacuous

    def test_green_requires_pass(self):
        assert h.green_gate(0, 3)["ok"] is True
        assert h.green_gate(1, 3)["ok"] is False
        assert h.green_gate(0, 0)["ok"] is False  # tests vanished


class TestCheckTamper:
    def test_in_scope_impl_only_passes(self):
        res = h.check_tamper(
            changed_files=["src/a.py"],
            allowed_impl_files=["src/a.py"],
            test_hashes_before={"tests/a.py": "h1"},
            test_hashes_after={"tests/a.py": "h1"},
        )
        assert res["ok"] is True
        assert res["violations"] == []

    def test_out_of_scope_change_flagged(self):
        res = h.check_tamper(
            changed_files=["src/a.py", "src/other.py"],
            allowed_impl_files=["src/a.py"],
            test_hashes_before={"tests/a.py": "h1"},
            test_hashes_after={"tests/a.py": "h1"},
        )
        assert res["ok"] is False
        assert any("src/other.py" in v for v in res["violations"])

    def test_mutated_test_file_flagged(self):
        res = h.check_tamper(
            changed_files=["src/a.py"],
            allowed_impl_files=["src/a.py"],
            test_hashes_before={"tests/a.py": "h1"},
            test_hashes_after={"tests/a.py": "TAMPERED"},
        )
        assert res["ok"] is False
        assert any("tests/a.py" in v and "frozen" in v for v in res["violations"])

    def test_added_shadow_test_file_flagged(self):
        # implementer sneaks in a new passing test file
        res = h.check_tamper(
            changed_files=["src/a.py", "tests/shadow.py"],
            allowed_impl_files=["src/a.py"],
            test_hashes_before={"tests/a.py": "h1"},
            test_hashes_after={"tests/a.py": "h1", "tests/shadow.py": "new"},
        )
        assert res["ok"] is False
        # caught both as out-of-scope change AND as a test-file hash change
        assert any("tests/shadow.py" in v for v in res["violations"])


class TestCLI:
    def test_validate_slices_cli(self, tmp_path, capsys):
        import json
        p = tmp_path / "slices.json"
        p.write_text(json.dumps([_slice("S-001", ["a"], ["ta"], ["R1"])]))
        rc = h.main(["validate-slices", "--slices", str(p), "--req-ids", "R1"])
        assert rc == 0
        assert json.loads(capsys.readouterr().out)["ok"] is True

    def test_validate_slices_cli_fails_on_gap(self, tmp_path, capsys):
        import json
        p = tmp_path / "slices.json"
        p.write_text(json.dumps([_slice("S-001", ["a"], ["ta"], ["R1"])]))
        rc = h.main(["validate-slices", "--slices", str(p), "--req-ids", "R1,R2"])
        assert rc == 1

    def test_waves_cli(self, tmp_path, capsys):
        import json
        p = tmp_path / "slices.json"
        p.write_text(json.dumps([
            _slice("S-000", ["k"], ["tk"], ["R0"]),
            _slice("S-001", ["a"], ["ta"], ["R1"], ["S-000"]),
        ]))
        rc = h.main(["waves", "--slices", str(p)])
        assert rc == 0
        assert json.loads(capsys.readouterr().out)["waves"] == [["S-000"], ["S-001"]]
