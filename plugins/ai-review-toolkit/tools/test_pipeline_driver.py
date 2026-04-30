"""Comprehensive tests for the pipeline driver."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure the tools package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

pipeline_driver = load_sibling("pipeline-driver.py")
_driver_path = Path(__file__).resolve().parent / "pipeline-driver.py"

init_pipeline = pipeline_driver.init_pipeline
next_action = pipeline_driver.next_action
record_phase_result = pipeline_driver.record_phase_result
validate_phases = pipeline_driver.validate_phases
get_status = pipeline_driver.get_status
resume = pipeline_driver.resume
reset = pipeline_driver.reset
generate_project_id = pipeline_driver.generate_project_id
PRESETS = pipeline_driver.PRESETS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def base(tmp_path: Path) -> str:
    """Return a temp directory string for state storage."""
    return str(tmp_path)


@pytest.fixture()
def artifact(tmp_path: Path) -> str:
    """Create a minimal artifact file and return its path."""
    p = tmp_path / "artifact.py"
    p.write_text("# placeholder artifact\n", encoding="utf-8")
    return str(p)


@pytest.fixture()
def requirements(tmp_path: Path) -> str:
    """Create a minimal requirements file and return its path."""
    p = tmp_path / "requirements.md"
    p.write_text("# Requirements\n- R1: it should work\n", encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Preset expansion
# ---------------------------------------------------------------------------

class TestPresetExpansion:
    def test_review_preset_expands_correctly(self, base: str) -> None:
        state = init_pipeline(preset="review", base_dir=base)
        assert state["phases"] == ["test-gate", "review-loop", "verify"]
        assert state["preset"] == "review"

    def test_thorough_preset_expands_correctly(self, base: str) -> None:
        state = init_pipeline(preset="thorough", base_dir=base)
        assert state["phases"] == [
            "ideate", "plan", "execute", "review-loop",
            "test-gate", "verify", "demo",
        ]
        assert state["preset"] == "thorough"

    def test_content_preset_expands_correctly(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        assert state["phases"] == ["review-loop", "verify"]
        assert state["preset"] == "content"

    def test_code_preset_expands_correctly(self, base: str) -> None:
        state = init_pipeline(preset="code", base_dir=base)
        assert state["phases"] == ["review-loop", "test-gate", "verify"]
        assert state["preset"] == "code"

    def test_unknown_preset_raises(self, base: str) -> None:
        with pytest.raises(ValueError, match="Unknown preset"):
            init_pipeline(preset="nonexistent", base_dir=base)

    def test_default_preset_is_review(self, base: str) -> None:
        state = init_pipeline(base_dir=base)
        assert state["phases"] == PRESETS["review"]


# ---------------------------------------------------------------------------
# Compositional integrity
# ---------------------------------------------------------------------------

class TestCompositionalIntegrity:
    def test_valid_custom_phases_accepted(self, base: str) -> None:
        state = init_pipeline(
            phases=["review-loop", "test-gate", "verify"],
            base_dir=base,
        )
        assert state["phases"] == ["review-loop", "test-gate", "verify"]
        assert state["preset"] == "custom"

    def test_execute_without_review_loop_rejected(self, base: str) -> None:
        with pytest.raises(ValueError, match="review-loop"):
            init_pipeline(
                phases=["execute", "test-gate", "verify"],
                base_dir=base,
            )

    def test_fix_without_review_loop_rejected(self, base: str) -> None:
        with pytest.raises(ValueError, match="review-loop"):
            init_pipeline(
                phases=["fix", "test-gate"],
                base_dir=base,
            )

    def test_execute_with_review_loop_accepted(self, base: str) -> None:
        state = init_pipeline(
            phases=["execute", "review-loop", "verify"],
            base_dir=base,
        )
        assert "execute" in state["phases"]
        assert "review-loop" in state["phases"]

    def test_unrecognized_phase_rejected(self, base: str) -> None:
        with pytest.raises(ValueError, match="unrecognized"):
            init_pipeline(
                phases=["review-loop", "magic-phase"],
                base_dir=base,
            )

    def test_validate_phases_accepts_valid(self) -> None:
        valid, errors = validate_phases(["review-loop", "test-gate", "verify"])
        assert valid is True
        assert errors == []

    def test_validate_phases_rejects_execute_alone(self) -> None:
        valid, errors = validate_phases(["execute", "test-gate"])
        assert valid is False
        assert any("review-loop" in e for e in errors)

    def test_validate_phases_rejects_unknown(self) -> None:
        valid, errors = validate_phases(["review-loop", "banana"])
        assert valid is False
        assert any("banana" in e for e in errors)


# ---------------------------------------------------------------------------
# Project ID generation
# ---------------------------------------------------------------------------

class TestProjectId:
    def test_project_id_nnn_slug_format(self, base: str, artifact: str) -> None:
        state = init_pipeline(
            preset="review", artifact_path=artifact, base_dir=base,
        )
        pid = state["project_id"]
        assert pid.startswith("001-")
        assert "artifact" in pid

    def test_project_id_increments(self, base: str) -> None:
        init_pipeline(preset="content", base_dir=base)
        state2 = init_pipeline(preset="content", base_dir=base)
        assert state2["project_id"].startswith("002-")

    def test_project_id_without_artifact_uses_pipeline(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        assert "pipeline" in state["project_id"]

    def test_project_id_slug_sanitized(self, base: str, tmp_path: Path) -> None:
        weird = tmp_path / "My Weird File!!! (v2).py"
        weird.write_text("# weird\n", encoding="utf-8")
        state = init_pipeline(
            preset="content", artifact_path=str(weird), base_dir=base,
        )
        pid = state["project_id"]
        # Should only contain lowercase alphanumeric and hyphens after prefix
        slug_part = pid[4:]  # strip "NNN-"
        assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in slug_part)


# ---------------------------------------------------------------------------
# Next action
# ---------------------------------------------------------------------------

class TestNextAction:
    def test_first_action_matches_first_phase(self, base: str) -> None:
        state = init_pipeline(preset="review", base_dir=base)
        action = next_action(state, base_dir=base)
        assert action["phase"] == "test-gate"
        assert action["action"] == "run_tests"

    def test_review_phase_returns_spawn_reviewers(self, base: str) -> None:
        state = init_pipeline(
            phases=["review", "review-loop"],
            base_dir=base,
        )
        action = next_action(state, base_dir=base)
        assert action["action"] == "spawn_reviewers"
        assert action["phase"] == "review"

    def test_review_loop_returns_run_loop(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        action = next_action(state, base_dir=base)
        assert action["action"] == "run_loop"
        assert action["phase"] == "review-loop"
        assert "loop_config" in action

    def test_verify_phase_returns_spawn_verifier(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        # Record review-loop result to advance
        record_phase_result(state, "review-loop", {"converged": True}, base_dir=base)
        action = next_action(state, base_dir=base)
        assert action["action"] == "spawn_verifier"
        assert action["phase"] == "verify"

    def test_test_gate_returns_run_tests(self, base: str) -> None:
        state = init_pipeline(
            phases=["test-gate", "review-loop"],
            base_dir=base,
        )
        action = next_action(state, base_dir=base)
        assert action["action"] == "run_tests"

    def test_complete_after_all_phases(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        record_phase_result(state, "review-loop", {"converged": True}, base_dir=base)
        next_action(state, base_dir=base)  # advance to verify
        record_phase_result(state, "verify", {"passed": True}, base_dir=base)
        action = next_action(state, base_dir=base)
        assert action["action"] == "complete"
        assert "summary" in action

    def test_action_includes_phase_index_and_total(self, base: str) -> None:
        state = init_pipeline(preset="code", base_dir=base)
        action = next_action(state, base_dir=base)
        assert action["phase_index"] == 0
        assert action["total_phases"] == 3


# ---------------------------------------------------------------------------
# Gate behavior
# ---------------------------------------------------------------------------

class TestGates:
    def test_gate_phase_blocks_without_confirm(self, base: str) -> None:
        state = init_pipeline(preset="thorough", base_dir=base)
        action = next_action(state, base_dir=base)
        assert action["phase"] == "ideate"
        assert action["action"] == "gate"
        assert action["gate_pending"] is True
        assert "message" in action

    def test_gate_phase_stays_pending_on_repeat_next(self, base: str) -> None:
        state = init_pipeline(preset="thorough", base_dir=base)
        action1 = next_action(state, base_dir=base)
        assert action1["gate_pending"] is True
        # Call next again without confirm -> same gate
        state_reloaded = pipeline_driver._read_state(state["project_id"], base)
        action2 = next_action(state_reloaded, base_dir=base)
        assert action2["gate_pending"] is True
        assert action2["phase"] == "ideate"

    def test_gate_advances_with_confirm(self, base: str) -> None:
        state = init_pipeline(preset="thorough", base_dir=base)
        # Trigger gate
        next_action(state, base_dir=base)
        # Reload and confirm
        state = pipeline_driver._read_state(state["project_id"], base)
        action = next_action(state, confirm=True, base_dir=base)
        # After confirming ideate, next phase is plan (also a gate)
        assert action["phase"] == "plan"
        assert action["gate_pending"] is True


# ---------------------------------------------------------------------------
# Phase results
# ---------------------------------------------------------------------------

class TestPhaseResults:
    def test_record_phase_result(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        result = {"converged": True, "findings": []}
        updated = record_phase_result(state, "review-loop", result, base_dir=base)
        assert "review-loop" in updated["phase_results"]
        assert updated["phase_results"]["review-loop"]["converged"] is True

    def test_phase_without_result_returns_same_action(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        action1 = next_action(state, base_dir=base)
        state = pipeline_driver._read_state(state["project_id"], base)
        action2 = next_action(state, base_dir=base)
        assert action1["phase"] == action2["phase"]
        assert action1["action"] == action2["action"]


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

class TestCheckpointing:
    def test_checkpoint_saved_on_phase_transition(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        assert len(state["checkpoints"]) == 0
        # Record result for first phase -> triggers checkpoint on next advance
        record_phase_result(state, "review-loop", {"converged": True}, base_dir=base)
        next_action(state, base_dir=base)
        # Reload state to see checkpoint
        reloaded = pipeline_driver._read_state(state["project_id"], base)
        assert len(reloaded["checkpoints"]) >= 1
        cp = reloaded["checkpoints"][0]
        assert "timestamp" in cp
        assert "phase" in cp


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------

class TestResume:
    def test_resume_loads_state_and_returns_next_action(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        pid = state["project_id"]
        # Record first phase
        record_phase_result(state, "review-loop", {"converged": True}, base_dir=base)
        # Resume should return the verify phase action
        action = resume(pid, base_dir=base)
        assert action["phase"] == "verify"
        assert action["action"] == "spawn_verifier"

    def test_resume_nonexistent_project_raises(self, base: str) -> None:
        with pytest.raises(FileNotFoundError):
            resume("999-nonexistent", base_dir=base)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_returns_current_phase_and_progress(self, base: str) -> None:
        state = init_pipeline(preset="code", base_dir=base)
        pid = state["project_id"]
        status = get_status(project_id=pid, base_dir=base)
        assert status["project_id"] == pid
        assert status["current_phase"] == "review-loop"
        assert status["total_phases"] == 3
        assert status["phases_completed"] == 0
        assert status["preset"] == "code"

    def test_status_reflects_progress(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        pid = state["project_id"]
        record_phase_result(state, "review-loop", {"converged": True}, base_dir=base)
        status = get_status(project_id=pid, base_dir=base)
        assert status["phases_completed"] == 1

    def test_status_no_project_raises(self, base: str) -> None:
        with pytest.raises(FileNotFoundError):
            get_status(base_dir=base)


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_reset_clears_project_state(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        pid = state["project_id"]
        reset(project_id=pid, base_dir=base)
        with pytest.raises(FileNotFoundError):
            pipeline_driver._read_state(pid, base)

    def test_reset_all_clears_everything(self, base: str) -> None:
        init_pipeline(preset="content", base_dir=base)
        init_pipeline(preset="code", base_dir=base)
        reset(base_dir=base)
        state_root = Path(base) / ".qpipeline"
        assert not state_root.exists()

    def test_reset_nonexistent_is_safe(self, base: str) -> None:
        # Should not raise
        reset(project_id="999-gone", base_dir=base)


# ---------------------------------------------------------------------------
# Init with artifact/requirements
# ---------------------------------------------------------------------------

class TestInitWithPaths:
    def test_init_with_artifact_and_requirements(
        self, base: str, artifact: str, requirements: str,
    ) -> None:
        state = init_pipeline(
            preset="review",
            artifact_path=artifact,
            requirements_path=requirements,
            base_dir=base,
        )
        assert state["artifact_path"] is not None
        assert state["requirements_path"] is not None
        assert Path(state["artifact_path"]).exists()
        assert Path(state["requirements_path"]).exists()

    def test_init_without_paths_sets_none(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        assert state["artifact_path"] is None
        assert state["requirements_path"] is None

    def test_action_includes_paths_when_set(
        self, base: str, artifact: str, requirements: str,
    ) -> None:
        state = init_pipeline(
            preset="content",
            artifact_path=artifact,
            requirements_path=requirements,
            base_dir=base,
        )
        action = next_action(state, base_dir=base)
        assert action["artifact_path"] == state["artifact_path"]
        assert action["requirements_path"] == state["requirements_path"]


# ---------------------------------------------------------------------------
# No-skip enforcement
# ---------------------------------------------------------------------------

class TestNoSkipEnforcement:
    def test_cannot_advance_without_phase_result(self, base: str) -> None:
        """Calling next_action repeatedly without recording a result
        must return the same phase action each time."""
        state = init_pipeline(preset="content", base_dir=base)
        pid = state["project_id"]

        action1 = next_action(state, base_dir=base)
        assert action1["phase"] == "review-loop"
        assert action1["action"] == "run_loop"

        # Reload and call again -- no result recorded
        state2 = pipeline_driver._read_state(pid, base)
        action2 = next_action(state2, base_dir=base)
        assert action2["phase"] == action1["phase"]
        assert action2["action"] == action1["action"]

        # Third time -- still the same
        state3 = pipeline_driver._read_state(pid, base)
        action3 = next_action(state3, base_dir=base)
        assert action3["phase"] == action1["phase"]
        assert action3["action"] == action1["action"]


# ---------------------------------------------------------------------------
# Duplicate gate prevention
# ---------------------------------------------------------------------------

class TestDuplicateGatePrevention:
    def test_gate_not_duplicated_in_gates_pending(self, base: str) -> None:
        state = init_pipeline(preset="thorough", base_dir=base)
        pid = state["project_id"]

        # First call triggers gate
        next_action(state, base_dir=base)
        state = pipeline_driver._read_state(pid, base)
        assert state["gates_pending"].count("ideate") == 1

        # Second call should not duplicate
        next_action(state, base_dir=base)
        state = pipeline_driver._read_state(pid, base)
        assert state["gates_pending"].count("ideate") == 1


# ---------------------------------------------------------------------------
# Configurable loop parameters
# ---------------------------------------------------------------------------

class TestConfigurableLoopParams:
    def test_default_max_rounds_is_five(self, base: str) -> None:
        state = init_pipeline(preset="content", base_dir=base)
        action = next_action(state, base_dir=base)
        assert action["loop_config"]["max_rounds"] == 5

    def test_custom_max_rounds_and_threshold(self, base: str) -> None:
        state = init_pipeline(
            preset="content",
            base_dir=base,
            convergence_threshold=2,
            max_rounds=10,
        )
        action = next_action(state, base_dir=base)
        assert action["loop_config"]["max_rounds"] == 10
        assert action["loop_config"]["convergence_threshold"] == 2

    def test_custom_params_stored_in_state(self, base: str) -> None:
        state = init_pipeline(
            preset="content",
            base_dir=base,
            convergence_threshold=3,
            max_rounds=7,
        )
        assert state["convergence_threshold"] == 3
        assert state["max_rounds"] == 7


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    """Test CLI entry point via subprocess."""

    def _run_cli(
        self, args: list[str], cwd: str, input_text: str | None = None,
    ) -> tuple[int, str, str]:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(_driver_path)] + args,
            capture_output=True, text=True, cwd=cwd,
            input=input_text,
        )
        return result.returncode, result.stdout, result.stderr

    def test_init_with_preset(self, tmp_path: Path) -> None:
        rc, stdout, stderr = self._run_cli(
            ["init", "--preset", "review"], cwd=str(tmp_path),
        )
        assert rc == 0, f"stderr: {stderr}"
        output = json.loads(stdout)
        assert output["preset"] == "review"
        assert output["phases"] == ["test-gate", "review-loop", "verify"]
        # State file should exist
        state_files = list(tmp_path.rglob("state.json"))
        assert len(state_files) == 1

    def test_init_with_custom_phases(self, tmp_path: Path) -> None:
        rc, stdout, stderr = self._run_cli(
            ["init", "--phases", "review-loop,verify"], cwd=str(tmp_path),
        )
        assert rc == 0, f"stderr: {stderr}"
        output = json.loads(stdout)
        assert output["phases"] == ["review-loop", "verify"]
        assert output["preset"] == "custom"

    def test_next_without_confirm(self, tmp_path: Path) -> None:
        # Init first
        rc, stdout, _ = self._run_cli(
            ["init", "--preset", "content"], cwd=str(tmp_path),
        )
        assert rc == 0
        init_state = json.loads(stdout)
        pid = init_state["project_id"]

        # Next without confirm
        rc, stdout, stderr = self._run_cli(
            ["next", "--project", pid], cwd=str(tmp_path),
        )
        assert rc == 0, f"stderr: {stderr}"
        action = json.loads(stdout)
        assert action["phase"] == "review-loop"
        assert action["action"] == "run_loop"

    def test_status(self, tmp_path: Path) -> None:
        rc, stdout, _ = self._run_cli(
            ["init", "--preset", "code"], cwd=str(tmp_path),
        )
        assert rc == 0
        pid = json.loads(stdout)["project_id"]

        rc, stdout, stderr = self._run_cli(
            ["status", "--project", pid], cwd=str(tmp_path),
        )
        assert rc == 0, f"stderr: {stderr}"
        status = json.loads(stdout)
        assert status["project_id"] == pid
        assert status["total_phases"] == 3

    def test_reset(self, tmp_path: Path) -> None:
        rc, stdout, _ = self._run_cli(
            ["init", "--preset", "content"], cwd=str(tmp_path),
        )
        assert rc == 0

        rc, stdout, stderr = self._run_cli(
            ["reset"], cwd=str(tmp_path),
        )
        assert rc == 0, f"stderr: {stderr}"
        assert "cleared" in stdout.lower()

        # State root should be gone
        state_root = tmp_path / ".qpipeline"
        assert not state_root.exists()

    def test_record_result(self, tmp_path: Path) -> None:
        # Init
        rc, stdout, _ = self._run_cli(
            ["init", "--preset", "content"], cwd=str(tmp_path),
        )
        assert rc == 0
        pid = json.loads(stdout)["project_id"]

        # Create result file
        result_file = tmp_path / "result.json"
        result_file.write_text(
            json.dumps({"converged": True, "findings": []}),
            encoding="utf-8",
        )

        # Record result
        rc, stdout, stderr = self._run_cli(
            ["record-result", "--phase", "review-loop",
             "--result-file", str(result_file), "--project", pid],
            cwd=str(tmp_path),
        )
        assert rc == 0, f"stderr: {stderr}"
        assert "Recorded" in stdout

    def test_init_with_threshold_and_max_rounds(self, tmp_path: Path) -> None:
        rc, stdout, stderr = self._run_cli(
            ["init", "--preset", "content",
             "--threshold", "2", "--max-rounds", "8"],
            cwd=str(tmp_path),
        )
        assert rc == 0, f"stderr: {stderr}"
        output = json.loads(stdout)
        assert output["convergence_threshold"] == 2
        assert output["max_rounds"] == 8


# ---------------------------------------------------------------------------
# Tests: Round 4 fixes — duplicate phase, ordering, test-gate validation
# ---------------------------------------------------------------------------

class TestRound4Fixes:
    def test_duplicate_phases_rejected(self) -> None:
        valid, errors = validate_phases(["review-loop", "test-gate", "review-loop"])
        assert valid is False
        assert any("duplicate" in e for e in errors)

    def test_mutation_before_review_required(self) -> None:
        valid, errors = validate_phases(["review-loop", "execute"])
        assert valid is False
        assert any("before" in e for e in errors)

    def test_valid_ordering_accepted(self) -> None:
        valid, errors = validate_phases(["execute", "review-loop", "verify"])
        assert valid is True

    def test_test_gate_rejects_failed_results(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        reqs = tmp_path / "r.md"
        reqs.write_text("# Reqs\n- R1: pass")
        state = init_pipeline(
            phases=["test-gate", "review-loop", "verify"],
            artifact_path=str(artifact),
            requirements_path=str(reqs),
            base_dir=str(tmp_path),
        )
        with pytest.raises(ValueError, match="all_passed=False"):
            record_phase_result(
                state, "test-gate",
                {"all_passed": False, "summary": "0/1"},
                base_dir=str(tmp_path),
            )

    def test_test_gate_accepts_passed_results(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        reqs = tmp_path / "r.md"
        reqs.write_text("# Reqs\n- R1: pass")
        state = init_pipeline(
            phases=["test-gate", "review-loop", "verify"],
            artifact_path=str(artifact),
            requirements_path=str(reqs),
            base_dir=str(tmp_path),
        )
        state = record_phase_result(
            state, "test-gate",
            {"all_passed": True, "summary": "1/1"},
            base_dir=str(tmp_path),
        )
        assert "test-gate" in state["phase_results"]

    def test_verify_rejects_fail_verdict(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        reqs = tmp_path / "r.md"
        reqs.write_text("# Reqs\n- R1: pass")
        state = init_pipeline(
            phases=["review-loop", "verify"],
            artifact_path=str(artifact),
            requirements_path=str(reqs),
            base_dir=str(tmp_path),
        )
        record_phase_result(state, "review-loop", {"converged": True}, base_dir=str(tmp_path))
        next_action(state, base_dir=str(tmp_path))  # advance to verify
        with pytest.raises(ValueError, match="passing verdict"):
            record_phase_result(
                state, "verify",
                {"verdict": "FAIL"},
                base_dir=str(tmp_path),
            )

    def test_verify_accepts_pass_verdict(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        reqs = tmp_path / "r.md"
        reqs.write_text("# Reqs\n- R1: pass")
        state = init_pipeline(
            phases=["review-loop", "verify"],
            artifact_path=str(artifact),
            requirements_path=str(reqs),
            base_dir=str(tmp_path),
        )
        record_phase_result(state, "review-loop", {"converged": True}, base_dir=str(tmp_path))
        next_action(state, base_dir=str(tmp_path))  # advance to verify
        state = record_phase_result(
            state, "verify",
            {"verdict": "PASS"},
            base_dir=str(tmp_path),
        )
        assert "verify" in state["phase_results"]

    def test_review_loop_rejects_non_converged_non_escalated(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        reqs = tmp_path / "r.md"
        reqs.write_text("# Reqs\n- R1: pass")
        state = init_pipeline(
            phases=["review-loop", "verify"],
            artifact_path=str(artifact),
            requirements_path=str(reqs),
            base_dir=str(tmp_path),
        )
        with pytest.raises(ValueError, match="converged=True"):
            record_phase_result(
                state, "review-loop",
                {"converged": False},
                base_dir=str(tmp_path),
            )

    def test_review_loop_accepts_escalated(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        reqs = tmp_path / "r.md"
        reqs.write_text("# Reqs\n- R1: pass")
        state = init_pipeline(
            phases=["review-loop", "verify"],
            artifact_path=str(artifact),
            requirements_path=str(reqs),
            base_dir=str(tmp_path),
        )
        record_phase_result(
            state, "review-loop",
            {"status": "escalated", "converged": False},
            base_dir=str(tmp_path),
        )
        assert "review-loop" in state["phase_results"]

    def test_gate_phase_cannot_be_recorded_directly(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        state = init_pipeline(
            preset="thorough",
            artifact_path=str(artifact),
            base_dir=str(tmp_path),
        )
        # ideate is a gate phase -- recording directly must raise
        with pytest.raises(ValueError, match="Gate phase"):
            record_phase_result(
                state, "ideate",
                {"ok": True},
                base_dir=str(tmp_path),
            )

    def test_corrupt_state_json_raises_valueerror(self, tmp_path: Path) -> None:
        state = init_pipeline(preset="content", base_dir=str(tmp_path))
        pid = state["project_id"]
        # Corrupt the state file
        state_file = tmp_path / ".qpipeline" / "projects" / pid / "state.json"
        state_file.write_text("NOT VALID JSON {{{", encoding="utf-8")
        with pytest.raises(ValueError, match="Corrupt state file"):
            pipeline_driver._read_state(pid, str(tmp_path))

    def test_corrupt_phase_index_raises_valueerror(self, tmp_path: Path) -> None:
        state = init_pipeline(preset="content", base_dir=str(tmp_path))
        # Corrupt the phase index to an invalid value
        state["current_phase_index"] = 999
        with pytest.raises(ValueError, match="Corrupt phase index"):
            next_action(state, base_dir=str(tmp_path))

    def test_negative_phase_index_raises_valueerror(self, tmp_path: Path) -> None:
        state = init_pipeline(preset="content", base_dir=str(tmp_path))
        state["current_phase_index"] = -1
        with pytest.raises(ValueError, match="Corrupt phase index"):
            next_action(state, base_dir=str(tmp_path))

    def test_nonexistent_phase_rejected(self, tmp_path: Path) -> None:
        artifact = tmp_path / "a.py"
        artifact.write_text("x = 1")
        reqs = tmp_path / "r.md"
        reqs.write_text("# Reqs\n- R1: pass")
        state = init_pipeline(
            phases=["review-loop", "verify"],
            artifact_path=str(artifact),
            requirements_path=str(reqs),
            base_dir=str(tmp_path),
        )
        with pytest.raises(ValueError, match="not in the pipeline"):
            record_phase_result(
                state, "nonexistent-phase",
                {"ok": True},
                base_dir=str(tmp_path),
            )
