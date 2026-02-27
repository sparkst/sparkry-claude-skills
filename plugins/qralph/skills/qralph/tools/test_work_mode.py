#!/usr/bin/env python3
"""
Tests for QRALPH Work Mode (Sprint 6A).

Coverage:
- Init with mode="work"
- Agent count: simple=1, moderate=2, complex=3
- Plan generation creates PLAN.md
- Skill discovery for writing/research keywords
- TDD trigger for code signals
- Escalation triggers (multi-domain, P0, user request, phase transitions)
- Phase transitions specific to work mode
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

import importlib.util

# Load orchestrator
orch_path = Path(__file__).parent / "qralph-orchestrator.py"
spec = importlib.util.spec_from_file_location("qralph_orch_wm", orch_path)
qralph_orchestrator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qralph_orchestrator)

# Load shared state module
state_mod_path = Path(__file__).parent / "qralph-state.py"
spec_state = importlib.util.spec_from_file_location("qralph_state_wm", state_mod_path)
qralph_state = importlib.util.module_from_spec(spec_state)
spec_state.loader.exec_module(qralph_state)


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up mock QRALPH environment for work mode tests."""
    qralph_dir = tmp_path / ".qralph"
    projects_dir = qralph_dir / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(qralph_orchestrator, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(qralph_orchestrator, 'QRALPH_DIR', qralph_dir)
    monkeypatch.setattr(qralph_orchestrator, 'PROJECTS_DIR', projects_dir)
    monkeypatch.setattr(qralph_orchestrator, 'AGENTS_DIR', tmp_path / ".claude" / "agents")
    monkeypatch.setattr(qralph_orchestrator, 'PLUGINS_DIR', tmp_path / ".claude" / "plugins")
    monkeypatch.setattr(qralph_state, 'STATE_FILE', qralph_dir / "current-project.json")

    return tmp_path


def _init_work_project(mock_env, request="write a proposal for the client"):
    """Helper to init a work-mode project."""
    result = qralph_orchestrator.cmd_init(request, mode="work")
    # Clear CONTROL.md to avoid PAUSE interference
    project_path = Path(result["project_path"])
    (project_path / "CONTROL.md").write_text("# Control\n")
    return result


# ============================================================================
# INIT WITH WORK MODE
# ============================================================================


def test_init_work_mode_accepted(mock_env):
    """Init accepts mode='work'."""
    result = _init_work_project(mock_env)
    assert result["status"] == "initialized"
    assert result["mode"] == "work"


def test_init_work_mode_state(mock_env):
    """State records work mode."""
    result = _init_work_project(mock_env)
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    assert state["mode"] == "work"


# ============================================================================
# AGENT COUNT (WORK MODE)
# ============================================================================


def test_work_complexity_simple():
    """Simple request = 1 agent."""
    count = qralph_orchestrator.estimate_work_complexity("write an email", ["marketing"])
    assert count == 1


def test_work_complexity_moderate():
    """Moderate request = 2 agents."""
    count = qralph_orchestrator.estimate_work_complexity(
        "research and " + "analyze " * 15 + "the market landscape for AI tools in pharma",
        ["marketing", "research", "strategy", "finance"]
    )
    assert count == 2


def test_work_complexity_complex():
    """Complex request = 3 agents (capped)."""
    count = qralph_orchestrator.estimate_work_complexity(
        "comprehensive " + "word " * 100 + " analysis",
        ["marketing", "research", "strategy", "finance", "legal", "operations"]
    )
    assert count == 3


def test_work_complexity_clamped():
    """Agent count never exceeds 3 for work mode."""
    count = qralph_orchestrator.estimate_work_complexity(
        "a " * 200,
        ["a", "b", "c", "d", "e", "f", "g", "h"]
    )
    assert count <= 3


# ============================================================================
# PLAN GENERATION
# ============================================================================


def test_work_plan_creates_file(mock_env):
    """work-plan creates PLAN.md."""
    result = _init_work_project(mock_env)
    project_path = Path(result["project_path"])

    # Advance to DISCOVERING first
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state["phase"] = "DISCOVERING"
    (mock_env / ".qralph" / "current-project.json").write_text(json.dumps(state, indent=2))

    plan_result = qralph_orchestrator.cmd_work_plan()
    assert (project_path / "PLAN.md").exists()


def test_work_plan_has_sections(mock_env):
    """PLAN.md contains required sections."""
    result = _init_work_project(mock_env)
    project_path = Path(result["project_path"])

    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state["phase"] = "DISCOVERING"
    (mock_env / ".qralph" / "current-project.json").write_text(json.dumps(state, indent=2))

    qralph_orchestrator.cmd_work_plan()
    content = (project_path / "PLAN.md").read_text()
    assert "## Request" in content
    assert "## Steps" in content
    assert "## Escalation Criteria" in content


def test_work_plan_advances_phase(mock_env):
    """work-plan transitions DISCOVERING -> PLANNING."""
    _init_work_project(mock_env)

    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state["phase"] = "DISCOVERING"
    (mock_env / ".qralph" / "current-project.json").write_text(json.dumps(state, indent=2))

    qralph_orchestrator.cmd_work_plan()
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    assert state["phase"] == "PLANNING"


# ============================================================================
# SKILL DISCOVERY
# ============================================================================


def test_skill_discovery_writing():
    """Writing keywords map to writing skills."""
    skills = qralph_orchestrator.discover_work_skills("write a blog post about AI")
    assert "writing" in skills


def test_skill_discovery_research():
    """Research keywords map to research skills."""
    skills = qralph_orchestrator.discover_work_skills("research market trends")
    assert "research-workflow" in skills


def test_skill_discovery_no_code_signal():
    """No code signals in pure writing request."""
    assert not qralph_orchestrator.contains_code_signals("write a proposal for the client")


# ============================================================================
# TDD TRIGGER
# ============================================================================


def test_tdd_code_signal_script():
    """'script' triggers code signal."""
    assert qralph_orchestrator.contains_code_signals("write a script to process data")


def test_tdd_code_signal_api():
    """'api' triggers code signal."""
    assert qralph_orchestrator.contains_code_signals("build an API endpoint for users")


def test_tdd_no_false_positive():
    """Pure business request doesn't trigger code signal."""
    assert not qralph_orchestrator.contains_code_signals("review the quarterly financial report")


# ============================================================================
# ESCALATION
# ============================================================================


def test_escalation_multi_domain():
    """4+ domains triggers escalation."""
    state = {"domains": ["a", "b", "c", "d"], "heal_attempts": 0, "findings": []}
    assert qralph_orchestrator.should_escalate_to_coding(state)


def test_escalation_p0_findings():
    """P0 findings trigger escalation."""
    state = {"domains": ["a"], "heal_attempts": 0,
             "findings": [{"priority": "P0", "desc": "critical"}]}
    assert qralph_orchestrator.should_escalate_to_coding(state)


def test_escalation_heal_failures():
    """3+ heal attempts trigger escalation."""
    state = {"domains": ["a"], "heal_attempts": 3, "findings": []}
    assert qralph_orchestrator.should_escalate_to_coding(state)


def test_no_escalation_normal():
    """Normal work mode doesn't escalate."""
    state = {"domains": ["a", "b"], "heal_attempts": 0, "findings": []}
    assert not qralph_orchestrator.should_escalate_to_coding(state)


def test_cmd_escalate_changes_mode(mock_env):
    """escalate command switches to coding mode."""
    _init_work_project(mock_env)

    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state["phase"] = "EXECUTING"
    (mock_env / ".qralph" / "current-project.json").write_text(json.dumps(state, indent=2))

    result = qralph_orchestrator.cmd_escalate()
    assert result["old_mode"] == "work"
    assert result["new_mode"] == "coding"

    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    assert state["mode"] == "coding"


# ============================================================================
# PHASE TRANSITIONS (WORK MODE)
# ============================================================================


def test_work_phase_init_to_discovering():
    """INIT -> DISCOVERING valid in work mode."""
    assert qralph_orchestrator.validate_phase_transition("INIT", "DISCOVERING", "work")


def test_work_phase_discovering_to_planning():
    """DISCOVERING -> PLANNING valid in work mode."""
    assert qralph_orchestrator.validate_phase_transition("DISCOVERING", "PLANNING", "work")


def test_work_phase_planning_to_user_review():
    """PLANNING -> USER_REVIEW valid in work mode."""
    assert qralph_orchestrator.validate_phase_transition("PLANNING", "USER_REVIEW", "work")


def test_work_phase_user_review_to_executing():
    """USER_REVIEW -> EXECUTING valid in work mode."""
    assert qralph_orchestrator.validate_phase_transition("USER_REVIEW", "EXECUTING", "work")


def test_work_phase_user_review_to_planning():
    """USER_REVIEW -> PLANNING valid in work mode (iterate)."""
    assert qralph_orchestrator.validate_phase_transition("USER_REVIEW", "PLANNING", "work")


def test_work_phase_executing_to_escalate():
    """EXECUTING -> ESCALATE valid in work mode."""
    assert qralph_orchestrator.validate_phase_transition("EXECUTING", "ESCALATE", "work")


def test_work_phase_escalate_to_reviewing():
    """ESCALATE -> REVIEWING valid in work mode."""
    assert qralph_orchestrator.validate_phase_transition("ESCALATE", "REVIEWING", "work")


def test_work_phase_invalid():
    """INIT -> EXECUTING invalid in work mode."""
    assert not qralph_orchestrator.validate_phase_transition("INIT", "EXECUTING", "work")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
