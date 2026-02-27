#!/usr/bin/env python3
"""
Tests for QRALPH Watchdog - Health checks, agent monitoring, preconditions.

Sprint 5B/5E coverage:
- Agent health checks (stuck, empty, missing output)
- State integrity validation
- Phase precondition checks
- Escalation logic
- Timeout configuration
"""

import json
import pytest
import time
from datetime import datetime
from pathlib import Path

import importlib.util

# Load watchdog
watchdog_path = Path(__file__).parent / "qralph-watchdog.py"
spec = importlib.util.spec_from_file_location("qralph_watchdog", watchdog_path)
qralph_watchdog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qralph_watchdog)

# Load shared state module
state_mod_path = Path(__file__).parent / "qralph-state.py"
spec_state = importlib.util.spec_from_file_location("qralph_state_wd", state_mod_path)
qralph_state = importlib.util.module_from_spec(spec_state)
spec_state.loader.exec_module(qralph_state)


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up mock QRALPH environment."""
    qralph_dir = tmp_path / ".qralph"
    projects_dir = qralph_dir / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(qralph_watchdog, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(qralph_watchdog, 'QRALPH_DIR', qralph_dir)
    monkeypatch.setattr(qralph_watchdog, 'CURRENT_PROJECT_FILE', qralph_dir / "current-project.json")

    return tmp_path


def _create_project(mock_env, project_id="001-test", phase="EXECUTING", agents=None):
    """Helper to create a test project."""
    project_path = mock_env / ".qralph" / "projects" / project_id
    project_path.mkdir(parents=True, exist_ok=True)
    outputs_dir = project_path / "agent-outputs"
    outputs_dir.mkdir(exist_ok=True)

    if agents is None:
        agents = ["sde-iii", "security-reviewer", "docs-writer"]

    state = {
        "project_id": project_id,
        "project_path": str(project_path),
        "request": "Test request for watchdog",
        "mode": "coding",
        "phase": phase,
        "created_at": datetime.now().isoformat(),
        "agents": agents,
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 1000, "total_cost_usd": 0.5, "error_counts": {}},
    }

    state_file = mock_env / ".qralph" / "current-project.json"
    state_file.write_text(json.dumps(state, indent=2))

    return project_path, state


# ============================================================================
# AGENT HEALTH CHECKS
# ============================================================================


def test_agent_health_missing_outputs_dir(mock_env):
    """Reports error when agent-outputs directory is missing."""
    project_path, state = _create_project(mock_env)
    import shutil
    shutil.rmtree(project_path / "agent-outputs")

    issues = qralph_watchdog.check_agent_health(state, project_path)
    assert len(issues) == 1
    assert issues[0]["level"] == "error"
    assert "missing" in issues[0]["message"].lower()


def test_agent_health_missing_output_file(mock_env):
    """Reports warning when agent output file doesn't exist."""
    project_path, state = _create_project(mock_env)
    # No output files created

    issues = qralph_watchdog.check_agent_health(state, project_path)
    assert len(issues) == 3  # One per agent
    assert all(i["level"] == "warning" for i in issues)


def test_agent_health_empty_critical_file(mock_env):
    """Reports critical for empty output from critical agent."""
    project_path, state = _create_project(mock_env)
    # Create empty file for critical agent
    (project_path / "agent-outputs" / "security-reviewer.md").write_text("")
    # Create good file for others
    (project_path / "agent-outputs" / "sde-iii.md").write_text("x" * 200)
    (project_path / "agent-outputs" / "docs-writer.md").write_text("x" * 200)

    issues = qralph_watchdog.check_agent_health(state, project_path)
    critical_issues = [i for i in issues if i.get("level") == "critical"]
    assert len(critical_issues) == 1
    assert critical_issues[0]["agent"] == "security-reviewer"
    assert critical_issues[0]["action"] == "retry"


def test_agent_health_empty_noncritical_file(mock_env):
    """Reports warning (not critical) for empty non-critical agent output."""
    project_path, state = _create_project(mock_env)
    (project_path / "agent-outputs" / "docs-writer.md").write_text("")
    (project_path / "agent-outputs" / "sde-iii.md").write_text("x" * 200)
    (project_path / "agent-outputs" / "security-reviewer.md").write_text("x" * 200)

    issues = qralph_watchdog.check_agent_health(state, project_path)
    warning_issues = [i for i in issues if i.get("level") == "warning" and i.get("agent") == "docs-writer"]
    assert len(warning_issues) == 1
    assert warning_issues[0]["action"] == "skip"


def test_agent_health_good_outputs(mock_env):
    """No issues for healthy agent outputs."""
    project_path, state = _create_project(mock_env)
    for agent in state["agents"]:
        (project_path / "agent-outputs" / f"{agent}.md").write_text("Good output " * 50)

    issues = qralph_watchdog.check_agent_health(state, project_path)
    assert len(issues) == 0


# ============================================================================
# STATE INTEGRITY
# ============================================================================


def test_state_integrity_valid(mock_env):
    """No issues for valid state."""
    project_path, state = _create_project(mock_env)
    issues = qralph_watchdog.check_state_integrity(state, project_path)
    assert len(issues) == 0


def test_state_integrity_missing_project_path(mock_env):
    """Critical issue when project directory doesn't exist."""
    project_path, state = _create_project(mock_env)
    fake_path = mock_env / "nonexistent"
    issues = qralph_watchdog.check_state_integrity(state, fake_path)
    assert any(i["level"] == "critical" for i in issues)


def test_state_integrity_mismatched_id(mock_env):
    """Warning when project_id doesn't match directory name."""
    project_path, state = _create_project(mock_env)
    state["project_id"] = "999-wrong-name"
    issues = qralph_watchdog.check_state_integrity(state, project_path)
    assert any("doesn't match" in i.get("message", "") for i in issues)


def test_state_integrity_invalid_phase(mock_env):
    """Error for unknown phase."""
    project_path, state = _create_project(mock_env)
    state["phase"] = "NONEXISTENT_PHASE"
    issues = qralph_watchdog.check_state_integrity(state, project_path)
    assert any(i["level"] == "error" and "Unknown phase" in i.get("message", "") for i in issues)


def test_state_integrity_orphan_outputs(mock_env):
    """Info when output files exist but agent not in list."""
    project_path, state = _create_project(mock_env)
    (project_path / "agent-outputs" / "orphan-agent.md").write_text("orphaned output")

    issues = qralph_watchdog.check_state_integrity(state, project_path)
    assert any("orphan" in i.get("message", "").lower() for i in issues)


def test_state_integrity_negative_tokens(mock_env):
    """Error for negative token count."""
    project_path, state = _create_project(mock_env)
    state["circuit_breakers"]["total_tokens"] = -100
    issues = qralph_watchdog.check_state_integrity(state, project_path)
    assert any("negative" in i.get("message", "").lower() for i in issues)


def test_state_integrity_invalid_timestamp(mock_env):
    """Warning for invalid created_at timestamp."""
    project_path, state = _create_project(mock_env)
    state["created_at"] = "not-a-timestamp"
    issues = qralph_watchdog.check_state_integrity(state, project_path)
    assert any("timestamp" in i.get("message", "").lower() for i in issues)


# ============================================================================
# PHASE PRECONDITIONS
# ============================================================================


def test_preconditions_discovering_ok(mock_env):
    """DISCOVERING preconditions met when project exists and request non-empty."""
    project_path, state = _create_project(mock_env)
    issues = qralph_watchdog.check_phase_preconditions("DISCOVERING", state, project_path)
    assert len(issues) == 0


def test_preconditions_discovering_empty_request(mock_env):
    """DISCOVERING blocked when request is empty."""
    project_path, state = _create_project(mock_env)
    state["request"] = ""
    issues = qralph_watchdog.check_phase_preconditions("DISCOVERING", state, project_path)
    assert any(i["precondition"] == "request_non_empty" for i in issues)


def test_preconditions_reviewing_no_discovery(mock_env):
    """REVIEWING blocked when no discovery results."""
    project_path, state = _create_project(mock_env)
    issues = qralph_watchdog.check_phase_preconditions("REVIEWING", state, project_path)
    assert any(i["precondition"] == "discovery_results_exist" for i in issues)


def test_preconditions_reviewing_no_domains(mock_env):
    """REVIEWING blocked when no domains detected."""
    project_path, state = _create_project(mock_env)
    (project_path / "discovered-plugins.json").write_text("[]")
    issues = qralph_watchdog.check_phase_preconditions("REVIEWING", state, project_path)
    assert any(i["precondition"] == "at_least_one_capability" for i in issues)


def test_preconditions_executing_no_synthesis(mock_env):
    """EXECUTING blocked when SYNTHESIS.md missing."""
    project_path, state = _create_project(mock_env)
    issues = qralph_watchdog.check_phase_preconditions("EXECUTING", state, project_path)
    assert any(i["precondition"] == "synthesis_exists" for i in issues)


def test_preconditions_executing_ok(mock_env):
    """EXECUTING preconditions met when SYNTHESIS.md exists."""
    project_path, state = _create_project(mock_env)
    (project_path / "SYNTHESIS.md").write_text("# Synthesis\n\nFindings...")
    issues = qralph_watchdog.check_phase_preconditions("EXECUTING", state, project_path)
    assert len(issues) == 0


def test_preconditions_uat_no_artifacts(mock_env):
    """UAT blocked when no execution artifacts."""
    project_path, state = _create_project(mock_env)
    import shutil
    shutil.rmtree(project_path / "agent-outputs")
    issues = qralph_watchdog.check_phase_preconditions("UAT", state, project_path)
    assert any(i["precondition"] == "execution_artifacts_exist" for i in issues)


def test_preconditions_complete_no_uat(mock_env):
    """COMPLETE blocked when UAT.md missing."""
    project_path, state = _create_project(mock_env)
    issues = qralph_watchdog.check_phase_preconditions("COMPLETE", state, project_path)
    assert any(i["precondition"] == "uat_exists" for i in issues)


def test_preconditions_complete_ok(mock_env):
    """COMPLETE preconditions met when UAT.md exists."""
    project_path, state = _create_project(mock_env)
    (project_path / "UAT.md").write_text("# UAT Results\n\nPassed.")
    issues = qralph_watchdog.check_phase_preconditions("COMPLETE", state, project_path)
    assert len(issues) == 0


# ============================================================================
# ESCALATION LOGIC
# ============================================================================


def test_escalation_critical_agent():
    """Critical agents get retry_then_alert action."""
    action = qralph_watchdog.get_escalation_action("security-reviewer", {})
    assert action == "retry_then_alert"


def test_escalation_noncritical_agent():
    """Non-critical agents get skip action."""
    action = qralph_watchdog.get_escalation_action("docs-writer", {})
    assert action == "skip"


def test_escalation_default_agent():
    """Default agents get retry_once action."""
    action = qralph_watchdog.get_escalation_action("some-random-agent", {})
    assert action == "retry_once"


# ============================================================================
# TIMEOUT CONFIGURATION
# ============================================================================


def test_timeout_haiku():
    """Haiku timeout is 120s."""
    assert qralph_watchdog.AGENT_TIMEOUTS["haiku"] == 120


def test_timeout_sonnet():
    """Sonnet timeout is 300s."""
    assert qralph_watchdog.AGENT_TIMEOUTS["sonnet"] == 300


def test_timeout_opus():
    """Opus timeout is 600s."""
    assert qralph_watchdog.AGENT_TIMEOUTS["opus"] == 600


# ============================================================================
# COMMAND FUNCTIONS
# ============================================================================


def test_cmd_check_no_project(mock_env, capsys):
    """cmd_check handles no active project."""
    qralph_watchdog.cmd_check()
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()


def test_cmd_check_agents_no_project(mock_env, capsys):
    """cmd_check_agents handles no active project."""
    qralph_watchdog.cmd_check_agents()
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()


def test_cmd_check_preconditions_no_project(mock_env, capsys):
    """cmd_check_preconditions handles no active project."""
    qralph_watchdog.cmd_check_preconditions("EXECUTING")
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()


def test_cmd_check_preconditions_ready(mock_env, capsys):
    """cmd_check_preconditions reports ready when preconditions met."""
    project_path, state = _create_project(mock_env, phase="DISCOVERING")
    result = qralph_watchdog.cmd_check_preconditions("DISCOVERING")
    assert result["status"] == "ready"
    assert result["can_proceed"] is True


def test_cmd_check_preconditions_blocked(mock_env, capsys):
    """cmd_check_preconditions reports blocked when preconditions unmet."""
    project_path, state = _create_project(mock_env, phase="REVIEWING")
    result = qralph_watchdog.cmd_check_preconditions("EXECUTING")
    assert result["status"] == "blocked"
    assert result["can_proceed"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
