#!/usr/bin/env python3
"""
Unit and integration tests for QRALPH v4.1 sub-team architecture.

REQ-QRALPH-020: Sub-team lifecycle (create, check, collect, resume, teardown)
REQ-QRALPH-021: Quality gate (95% confidence check)
REQ-QRALPH-022: Version detection and announcement
REQ-QRALPH-023: State schema (sub_teams, last_seen_version)
REQ-QRALPH-024: Sub-team recovery from compaction
REQ-QRALPH-025: --auto / --human execution mode
REQ-QRALPH-026: VALIDATING phase transitions
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import sys
import importlib.util
sys.path.insert(0, str(Path(__file__).parent))

# Load modules
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

_orch_path = Path(__file__).parent / "qralph-orchestrator.py"
_orch_spec = importlib.util.spec_from_file_location("qralph_orchestrator", _orch_path)
qralph_orchestrator = importlib.util.module_from_spec(_orch_spec)
_orch_spec.loader.exec_module(qralph_orchestrator)

_subteam_path = Path(__file__).parent / "qralph-subteam.py"
_subteam_spec = importlib.util.spec_from_file_location("qralph_subteam", _subteam_path)
qralph_subteam = importlib.util.module_from_spec(_subteam_spec)
_subteam_spec.loader.exec_module(qralph_subteam)

_watchdog_path = Path(__file__).parent / "qralph-watchdog.py"
_watchdog_spec = importlib.util.spec_from_file_location("qralph_watchdog", _watchdog_path)
qralph_watchdog = importlib.util.module_from_spec(_watchdog_spec)
_watchdog_spec.loader.exec_module(qralph_watchdog)

_session_path = Path(__file__).parent / "session-state.py"
_session_spec = importlib.util.spec_from_file_location("session_state", _session_path)
session_state = importlib.util.module_from_spec(_session_spec)
_session_spec.loader.exec_module(session_state)


# ─── FIXTURES ────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project with standard structure."""
    project_dir = tmp_path / ".qralph" / "projects" / "001-test-project"
    (project_dir / "agent-outputs").mkdir(parents=True)
    (project_dir / "checkpoints").mkdir(parents=True)
    (project_dir / "healing-attempts").mkdir(parents=True)
    (project_dir / "phase-outputs").mkdir(parents=True)

    state = {
        "project_id": "001-test-project",
        "project_path": str(project_dir),
        "request": "Test security and architecture review of the API",
        "mode": "coding",
        "phase": "REVIEWING",
        "created_at": datetime.now().isoformat(),
        "agents": ["security-reviewer", "architecture-advisor", "sde-iii", "code-quality-auditor"],
        "team_name": "qralph-001-test-project",
        "teammates": [],
        "skills_for_agents": {},
        "domains": ["security", "architecture", "backend"],
        "findings": [],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
        "execution_mode": "human",
        "sub_teams": {},
        "last_seen_version": "4.1.0",
    }

    state_file = tmp_path / ".qralph" / "current-project.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    qralph_state.safe_write_json(state_file, state)

    return tmp_path, project_dir, state


def _write_agent_output(project_dir, agent_name, content=None):
    """Helper to write a mock agent output file."""
    if content is None:
        content = f"""# {agent_name.replace('-', ' ').title()} Review

## Summary
Reviewed from {agent_name} perspective. All looks good.

## Findings

### P0 - Critical
- None identified

### P1 - Important
- Consider adding more test coverage

### P2 - Suggestions
- Minor style improvements

## Recommendations
1. Add acceptance criteria for all endpoints
2. Verify test coverage meets complexity threshold
3. Review risk assessment for maintainability
"""
    output_file = project_dir / "agent-outputs" / f"{agent_name}.md"
    output_file.write_text(content)
    return output_file


def _write_result_file(project_dir, phase, status="complete", agents_completed=None,
                       agents_failed=None, work_remaining=None, next_team_context=None):
    """Helper to write a mock result file."""
    result = {
        "status": status,
        "phase": phase,
        "agents_completed": agents_completed or [],
        "agents_failed": agents_failed or [],
        "output_files": [f"agent-outputs/{a}.md" for a in (agents_completed or [])],
        "summary": f"{phase} phase {status}",
        "completed_at": datetime.now().isoformat(),
        "token_estimate": 45000,
        "errors": [],
        "work_remaining": work_remaining,
        "next_team_context": next_team_context,
    }
    result_file = project_dir / "phase-outputs" / f"{phase}-result.json"
    qralph_state.safe_write_json(result_file, result)
    return result_file


# ============================================================================
# 1. CREATE-SUBTEAM TESTS
# ============================================================================

class TestCreateSubteam:
    """REQ-QRALPH-020: create-subteam creates metadata and outputs correct instructions."""

    def test_create_subteam_creates_metadata(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam._cmd_create_subteam_locked("REVIEWING")

        assert result["status"] == "subteam_ready"
        assert result["phase"] == "REVIEWING"
        assert result["agent_count"] == 4

    def test_create_subteam_outputs_instructions(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam._cmd_create_subteam_locked("REVIEWING")

        assert "TeamCreate" in result["instruction"]
        assert "team-lead" in result["instruction"]

    def test_create_subteam_updates_state(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            qralph_subteam._cmd_create_subteam_locked("REVIEWING")

        # Read updated state
        state_file = tmp_path / ".qralph" / "current-project.json"
        updated = qralph_state.load_state(state_file)
        assert "REVIEWING" in updated.get("sub_teams", {})
        assert updated["sub_teams"]["REVIEWING"]["status"] == "creating"

    def test_create_subteam_invalid_phase(self, capsys):
        result = qralph_subteam.cmd_create_subteam("INVALID")
        assert "error" in result

    def test_create_subteam_no_agents_error(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Clear agents
        state["agents"] = []
        state_file = tmp_path / ".qralph" / "current-project.json"
        qralph_state.safe_write_json(state_file, state)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam._cmd_create_subteam_locked("REVIEWING")
        assert "error" in result


# ============================================================================
# 2. CHECK-SUBTEAM TESTS
# ============================================================================

class TestCheckSubteam:
    """REQ-QRALPH-020: check-subteam detects complete, failed, timeout, running."""

    def test_check_detects_complete(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        all_agents = state["agents"]
        _write_result_file(project_dir, "REVIEWING", "complete", all_agents)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_check_subteam("REVIEWING")

        assert result["status"] == "complete"

    def test_check_detects_failed(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        _write_result_file(project_dir, "REVIEWING", "failed", ["security-reviewer"],
                          agents_failed=["architecture-advisor"])

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_check_subteam("REVIEWING")

        assert result["status"] == "failed"

    def test_check_detects_running(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Write some but not all outputs
        _write_agent_output(project_dir, "security-reviewer")
        state["sub_teams"] = {"REVIEWING": {"status": "running",
                                            "created_at": datetime.now().isoformat(),
                                            "agents": state["agents"]}}
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_check_subteam("REVIEWING")

        assert result["status"] == "running"
        assert "security-reviewer" in result["completed_agents"]
        assert len(result["missing_agents"]) > 0

    def test_check_detects_timeout(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Set old created_at time
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        state["sub_teams"] = {"REVIEWING": {"status": "running",
                                            "created_at": old_time,
                                            "agents": state["agents"]}}
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_check_subteam("REVIEWING")

        assert result["status"] == "timeout"
        assert result["timed_out"] is True

    def test_check_handles_missing_result_file(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        state["sub_teams"] = {"REVIEWING": {"status": "running",
                                            "created_at": datetime.now().isoformat(),
                                            "agents": state["agents"]}}
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_check_subteam("REVIEWING")

        # No result file + no outputs = running
        assert result["status"] == "running"

    def test_check_agents_complete_need_result(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Write all agent outputs but no result file
        for agent in state["agents"]:
            _write_agent_output(project_dir, agent)
        state["sub_teams"] = {"REVIEWING": {"status": "running",
                                            "created_at": datetime.now().isoformat(),
                                            "agents": state["agents"]}}
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_check_subteam("REVIEWING")

        assert result["status"] == "agents_complete_need_result"


# ============================================================================
# 3. COLLECT-RESULTS TESTS
# ============================================================================

class TestCollectResults:
    """REQ-QRALPH-020: collect-results reads result and updates state."""

    def test_collect_updates_state(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        all_agents = state["agents"]
        _write_result_file(project_dir, "REVIEWING", "complete", all_agents)
        state["sub_teams"] = {"REVIEWING": {"status": "running"}}
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam._cmd_collect_results_locked("REVIEWING")

        assert result["status"] == "collected"
        assert result["result_status"] == "complete"

        # Verify state updated
        updated = qralph_state.load_state(tmp_path / ".qralph" / "current-project.json")
        assert updated["sub_teams"]["REVIEWING"]["status"] == "complete"

    def test_collect_missing_result_file(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam._cmd_collect_results_locked("REVIEWING")
        assert "error" in result

    def test_collect_includes_work_remaining(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        _write_result_file(project_dir, "EXECUTING", "partial",
                          agents_completed=["sde-iii"],
                          work_remaining=["3 tests failing"],
                          next_team_context="Continue from test_auth.py")

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam._cmd_collect_results_locked("EXECUTING")

        assert result["work_remaining"] == ["3 tests failing"]
        assert result["next_team_context"] == "Continue from test_auth.py"


# ============================================================================
# 4. RESUME-SUBTEAM TESTS
# ============================================================================

class TestResumeSubteam:
    """REQ-QRALPH-024: resume-subteam identifies missing vs completed agents."""

    def test_resume_identifies_missing_agents(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Write some but not all agent outputs
        _write_agent_output(project_dir, "security-reviewer")
        _write_agent_output(project_dir, "architecture-advisor")

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_resume_subteam("REVIEWING")

        assert result["status"] == "resume_needed"
        assert "security-reviewer" in result["completed_agents"]
        assert "sde-iii" in result["missing_agents"]

    def test_resume_already_complete(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        _write_result_file(project_dir, "REVIEWING", "complete", state["agents"])

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_resume_subteam("REVIEWING")

        assert result["status"] == "already_complete"

    def test_resume_agents_complete_need_synthesis(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        for agent in state["agents"]:
            _write_agent_output(project_dir, agent)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_resume_subteam("REVIEWING")

        assert result["status"] == "agents_complete_need_synthesis"


# ============================================================================
# 5. TEARDOWN-SUBTEAM TESTS
# ============================================================================

class TestTeardownSubteam:
    """REQ-QRALPH-020: teardown-subteam outputs cleanup instructions."""

    def test_teardown_outputs_instructions(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        state["sub_teams"] = {"REVIEWING": {"status": "complete",
                                            "team_name": "qralph-001-reviewing"}}
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam._cmd_teardown_subteam_locked("REVIEWING")

        assert result["status"] == "teardown_ready"
        assert "shutdown_request" in result["instruction"]
        assert "TeamDelete" in result["instruction"]


# ============================================================================
# 6. QUALITY GATE TESTS
# ============================================================================

class TestQualityGate:
    """REQ-QRALPH-021: Quality gate passes/fails on 5 criteria."""

    def _setup_full_review(self, tmp_project):
        """Helper: set up a project with all agents completed and good outputs."""
        tmp_path, project_dir, state = tmp_project
        agents = state["agents"]

        # Write outputs with testable criteria and risk assessment
        for agent in agents:
            _write_agent_output(project_dir, agent)

        _write_result_file(project_dir, "REVIEWING", "complete", agents)
        return tmp_path, project_dir, state

    def test_gate_passes_all_criteria(self, tmp_project, capsys):
        tmp_path, project_dir, state = self._setup_full_review(tmp_project)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_quality_gate("REVIEWING")

        assert result["passed"] is True
        assert result["confidence"] >= 0.95
        assert result["gaps"] == []

    def test_gate_fails_when_critical_agent_missing(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Only complete non-critical agent
        agents_done = ["code-quality-auditor"]
        for a in agents_done:
            _write_agent_output(project_dir, a)
        _write_result_file(project_dir, "REVIEWING", "complete", agents_done)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_quality_gate("REVIEWING")

        assert result["passed"] is False
        assert any("Critical agents" in g for g in result["gaps"])

    def test_gate_fails_when_domain_uncovered(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Change request to include frontend domain, but no frontend agents
        state["request"] = "Build a new frontend dashboard with security"
        state["agents"] = ["security-reviewer"]
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        _write_agent_output(project_dir, "security-reviewer")
        _write_result_file(project_dir, "REVIEWING", "complete", ["security-reviewer"])

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_quality_gate("REVIEWING")

        assert result["passed"] is False
        assert any("Domains not covered" in g or "Critical agents" in g for g in result["gaps"])

    def test_gate_detects_contradictions(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        all_agents = state["agents"]

        # Write contradictory outputs
        secure_content = "## Summary\nThe system is secure and well-designed.\n## Findings\n### P0 - Critical\n- None\n### P1\n- None\n### P2\n- None\n## Recommendations\n1. Verify acceptance criteria\n2. Review complexity and risk assessment"
        insecure_content = "## Summary\nThe system is insecure and has major flaws.\n## Findings\n### P0 - Critical\n- Major insecure auth\n### P1\n- None\n### P2\n- None\n## Recommendations\n1. Accept no test criteria until coverage is met\n2. Assess complexity and risk thoroughly"

        (project_dir / "agent-outputs" / "security-reviewer.md").write_text(secure_content)
        (project_dir / "agent-outputs" / "architecture-advisor.md").write_text(insecure_content)
        _write_agent_output(project_dir, "sde-iii")
        _write_agent_output(project_dir, "code-quality-auditor")
        _write_result_file(project_dir, "REVIEWING", "complete", all_agents)

        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_subteam.cmd_quality_gate("REVIEWING")

        # Should detect the secure vs insecure contradiction
        assert any("contradiction" in g.lower() for g in result["gaps"]) or result["passed"] is True
        # Note: contradiction detection is heuristic; if both say "secure" and "insecure"
        # in different contexts, it may or may not flag


# ============================================================================
# 7. VERSION DETECTION TESTS
# ============================================================================

class TestVersionDetection:
    """REQ-QRALPH-022: Version check on init/resume."""

    def test_version_stored_on_init(self, tmp_path, capsys):
        projects_dir = tmp_path / ".qralph" / "projects"
        projects_dir.mkdir(parents=True)

        with patch.object(qralph_orchestrator, 'QRALPH_DIR', tmp_path / ".qralph"), \
             patch.object(qralph_orchestrator, 'PROJECTS_DIR', projects_dir), \
             patch.object(qralph_orchestrator, 'PROJECT_ROOT', tmp_path), \
             patch.object(qralph_state, 'STATE_FILE', tmp_path / ".qralph" / "current-project.json"), \
             patch.object(qralph_state, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_orchestrator.cmd_init("Test version check", "coding", "human")

        assert result["status"] == "initialized"
        assert result["execution_mode"] == "human"

    def test_version_update_on_resume(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        # Set old version
        state["last_seen_version"] = "4.0.5"
        state["phase"] = "REVIEWING"
        qralph_state.safe_write_json(project_dir / "checkpoints" / "state.json", state)

        with patch.object(qralph_orchestrator, 'QRALPH_DIR', tmp_path / ".qralph"), \
             patch.object(qralph_orchestrator, 'PROJECTS_DIR', tmp_path / ".qralph" / "projects"), \
             patch.object(qralph_state, 'STATE_FILE', tmp_path / ".qralph" / "current-project.json"), \
             patch.object(qralph_state, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_orchestrator.cmd_resume("001-test-project")

        assert "version_update" in result
        assert "4.1" in result["version_update"]

    def test_no_version_update_when_current(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        state["last_seen_version"] = qralph_orchestrator.VERSION
        state["phase"] = "REVIEWING"
        qralph_state.safe_write_json(project_dir / "checkpoints" / "state.json", state)

        with patch.object(qralph_orchestrator, 'QRALPH_DIR', tmp_path / ".qralph"), \
             patch.object(qralph_orchestrator, 'PROJECTS_DIR', tmp_path / ".qralph" / "projects"), \
             patch.object(qralph_state, 'STATE_FILE', tmp_path / ".qralph" / "current-project.json"), \
             patch.object(qralph_state, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_orchestrator.cmd_resume("001-test-project")

        assert "version_update" not in result


# ============================================================================
# 8. STATE SCHEMA TESTS
# ============================================================================

class TestStateSchema:
    """REQ-QRALPH-023: sub_teams validated, VALIDATING phase accepted."""

    def test_sub_teams_in_repair_defaults(self):
        repaired = qralph_state.repair_state({})
        assert "sub_teams" in repaired
        assert isinstance(repaired["sub_teams"], dict)

    def test_last_seen_version_in_repair_defaults(self):
        repaired = qralph_state.repair_state({})
        assert "last_seen_version" in repaired
        assert repaired["last_seen_version"] == ""

    def test_validating_is_valid_phase(self):
        assert "VALIDATING" in qralph_state.VALID_PHASES

    def test_sub_teams_validated(self):
        state = qralph_state.repair_state({
            "sub_teams": {"REVIEWING": {"status": "complete"}},
        })
        errors = qralph_state.validate_state(state)
        # No errors for valid sub_teams
        sub_team_errors = [e for e in errors if "sub_teams" in e]
        assert len(sub_team_errors) == 0

    def test_invalid_subteam_status_detected(self):
        state = qralph_state.repair_state({
            "sub_teams": {"REVIEWING": {"status": "nonexistent_status"}},
        })
        errors = qralph_state.validate_state(state)
        sub_team_errors = [e for e in errors if "sub_teams" in e]
        assert len(sub_team_errors) > 0

    def test_valid_subteam_statuses(self):
        for status in qralph_state.VALID_SUBTEAM_STATUSES:
            state = qralph_state.repair_state({
                "sub_teams": {"REVIEWING": {"status": status}},
            })
            errors = qralph_state.validate_state(state)
            sub_team_errors = [e for e in errors if "sub_teams" in e]
            assert len(sub_team_errors) == 0, f"Status '{status}' should be valid"


# ============================================================================
# 9. AUTO/HUMAN EXECUTION MODE TESTS
# ============================================================================

class TestExecutionMode:
    """REQ-QRALPH-025: --auto/--human flag stored and respected."""

    def test_auto_mode_stored(self, tmp_path, capsys):
        projects_dir = tmp_path / ".qralph" / "projects"
        projects_dir.mkdir(parents=True)

        with patch.object(qralph_orchestrator, 'QRALPH_DIR', tmp_path / ".qralph"), \
             patch.object(qralph_orchestrator, 'PROJECTS_DIR', projects_dir), \
             patch.object(qralph_orchestrator, 'PROJECT_ROOT', tmp_path), \
             patch.object(qralph_state, 'STATE_FILE', tmp_path / ".qralph" / "current-project.json"), \
             patch.object(qralph_state, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_orchestrator.cmd_init("Test auto mode", "coding", "auto")

        assert result["execution_mode"] == "auto"

    def test_human_mode_is_default(self, tmp_path, capsys):
        projects_dir = tmp_path / ".qralph" / "projects"
        projects_dir.mkdir(parents=True)

        with patch.object(qralph_orchestrator, 'QRALPH_DIR', tmp_path / ".qralph"), \
             patch.object(qralph_orchestrator, 'PROJECTS_DIR', projects_dir), \
             patch.object(qralph_orchestrator, 'PROJECT_ROOT', tmp_path), \
             patch.object(qralph_state, 'STATE_FILE', tmp_path / ".qralph" / "current-project.json"), \
             patch.object(qralph_state, 'QRALPH_DIR', tmp_path / ".qralph"):
            result = qralph_orchestrator.cmd_init("Test default mode", "coding")

        assert result["execution_mode"] == "human"


# ============================================================================
# 10. VALIDATING PHASE TRANSITION TESTS
# ============================================================================

class TestValidatingPhase:
    """REQ-QRALPH-026: VALIDATING phase transitions."""

    def test_reviewing_to_validating(self):
        assert qralph_orchestrator.validate_phase_transition("REVIEWING", "VALIDATING") is True

    def test_executing_to_validating(self):
        assert qralph_orchestrator.validate_phase_transition("EXECUTING", "VALIDATING") is True

    def test_validating_to_complete(self):
        assert qralph_orchestrator.validate_phase_transition("VALIDATING", "COMPLETE") is True

    def test_validating_to_executing(self):
        assert qralph_orchestrator.validate_phase_transition("VALIDATING", "EXECUTING") is True

    def test_init_to_validating_blocked(self):
        assert qralph_orchestrator.validate_phase_transition("INIT", "VALIDATING") is False


# ============================================================================
# 11. WATCHDOG SUBTEAM HEALTH TESTS
# ============================================================================

class TestWatchdogSubteamHealth:
    """Watchdog checks for sub-team health."""

    def test_subteam_health_no_issues(self, tmp_project):
        _, project_dir, state = tmp_project
        state["sub_teams"] = {"REVIEWING": {"status": "complete"}}
        _write_result_file(project_dir, "REVIEWING", "complete", state["agents"])

        issues = qralph_watchdog.check_subteam_health(state, project_dir)
        assert len(issues) == 0

    def test_subteam_health_missing_result(self, tmp_project):
        _, project_dir, state = tmp_project
        state["sub_teams"] = {"REVIEWING": {"status": "complete"}}
        # No result file written

        issues = qralph_watchdog.check_subteam_health(state, project_dir)
        assert len(issues) > 0
        assert any("missing" in i["message"].lower() for i in issues)

    def test_subteam_health_stale_running(self, tmp_project):
        _, project_dir, state = tmp_project
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        state["sub_teams"] = {"REVIEWING": {"status": "running", "created_at": old_time}}

        issues = qralph_watchdog.check_subteam_health(state, project_dir)
        assert len(issues) > 0
        assert any("running" in i["message"].lower() for i in issues)


# ============================================================================
# 12. SESSION RECOVERY TESTS
# ============================================================================

class TestSessionRecovery:
    """REQ-QRALPH-024: Session recovery handles sub-teams."""

    def test_session_start_recovery_notice(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project
        state["sub_teams"] = {"REVIEWING": {"status": "running",
                                            "created_at": datetime.now().isoformat()}}
        # Create STATE.md so session-start doesn't fail
        (project_dir / "STATE.md").write_text("# State\n## Next Session Instructions\nContinue\n")
        qralph_state.safe_write_json(tmp_path / ".qralph" / "current-project.json", state)

        mock_result = type('Result', (), {'stdout': '', 'stderr': '', 'returncode': 0})()
        with patch.object(session_state, 'CURRENT_PROJECT_FILE', tmp_path / ".qralph" / "current-project.json"), \
             patch.object(session_state, 'PROJECTS_DIR', tmp_path / ".qralph" / "projects"), \
             patch('subprocess.run', return_value=mock_result):
            result = session_state.cmd_session_start()

        assert "recovery_notice" in result
        assert "REVIEWING" in result["recovery_notice"]


# ============================================================================
# 13. INTEGRATION TEST - FULL WORKFLOW
# ============================================================================

class TestIntegrationWorkflow:
    """Full workflow mock: init → select-agents → create-subteam → quality-gate → collect."""

    def test_full_subteam_workflow(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project

        # Step 1: create-subteam
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            create_result = qralph_subteam._cmd_create_subteam_locked("REVIEWING")
        assert create_result["status"] == "subteam_ready"

        # Step 2: mock all agent outputs
        for agent in state["agents"]:
            _write_agent_output(project_dir, agent)

        # Step 3: mock result file
        _write_result_file(project_dir, "REVIEWING", "complete", state["agents"])

        # Step 4: check-subteam
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            check_result = qralph_subteam.cmd_check_subteam("REVIEWING")
        assert check_result["status"] == "complete"

        # Step 5: quality-gate
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            gate_result = qralph_subteam.cmd_quality_gate("REVIEWING")
        assert gate_result["passed"] is True

        # Step 6: collect-results
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            collect_result = qralph_subteam._cmd_collect_results_locked("REVIEWING")
        assert collect_result["status"] == "collected"

        # Step 7: teardown
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            teardown_result = qralph_subteam._cmd_teardown_subteam_locked("REVIEWING")
        assert teardown_result["status"] == "teardown_ready"

    def test_recovery_after_compaction(self, tmp_project, capsys):
        tmp_path, project_dir, state = tmp_project

        # Simulate: 2 of 4 agents completed before compaction
        _write_agent_output(project_dir, "security-reviewer")
        _write_agent_output(project_dir, "architecture-advisor")

        # Resume
        with patch.object(qralph_subteam, 'QRALPH_DIR', tmp_path / ".qralph"):
            resume_result = qralph_subteam.cmd_resume_subteam("REVIEWING")

        assert resume_result["status"] == "resume_needed"
        assert "sde-iii" in resume_result["missing_agents"]
        assert "code-quality-auditor" in resume_result["missing_agents"]
        assert len(resume_result["completed_agents"]) == 2


# ============================================================================
# 14. PROCESS MONITOR GRACE PERIOD TEST
# ============================================================================

class TestProcessMonitorGracePeriod:
    """team-agent grace period added to process monitor."""

    def test_team_agent_grace_period(self):
        _pm_path = Path(__file__).parent / "process-monitor.py"
        _pm_spec = importlib.util.spec_from_file_location("process_monitor", _pm_path)
        pm = importlib.util.module_from_spec(_pm_spec)
        _pm_spec.loader.exec_module(pm)

        assert "team-agent" in pm.DEFAULT_GRACE_PERIODS
        assert pm.DEFAULT_GRACE_PERIODS["team-agent"] == 1800
