#!/usr/bin/env python3
"""
Tests for QRALPH Session State Manager.

REQ-STATE-001: STATE.md creation
REQ-STATE-003: CLAUDE.md injection
REQ-STATE-004: Session start context
REQ-STATE-005: Session end updates
REQ-STATE-006: Crash recovery
REQ-STATE-007: MEMORY.md integration (pointer only)
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import sys
import importlib.util

# Load session-state.py
session_state_path = Path(__file__).parent / "session-state.py"
spec = importlib.util.spec_from_file_location("session_state", session_state_path)
session_state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_state)

# Load shared state module
state_mod_path = Path(__file__).parent / "qralph-state.py"
spec_state = importlib.util.spec_from_file_location("qralph_state", state_mod_path)
qralph_state = importlib.util.module_from_spec(spec_state)
spec_state.loader.exec_module(qralph_state)


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up mock QRALPH environment."""
    qralph_dir = tmp_path / ".qralph"
    projects_dir = qralph_dir / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(session_state, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(session_state, 'QRALPH_DIR', qralph_dir)
    monkeypatch.setattr(session_state, 'PROJECTS_DIR', projects_dir)
    monkeypatch.setattr(session_state, 'CURRENT_PROJECT_FILE', qralph_dir / "current-project.json")

    return tmp_path


def _create_test_project(mock_env, project_id="001-test-project"):
    """Helper to create a test project with state."""
    projects_dir = mock_env / ".qralph" / "projects"
    project_path = projects_dir / project_id
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "agent-outputs").mkdir(exist_ok=True)
    (project_path / "checkpoints").mkdir(exist_ok=True)
    (project_path / "healing-attempts").mkdir(exist_ok=True)

    state = {
        "project_id": project_id,
        "project_path": str(project_path),
        "request": "Test request for state management",
        "mode": "coding",
        "phase": "INIT",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
    }

    current_file = mock_env / ".qralph" / "current-project.json"
    current_file.write_text(json.dumps(state, indent=2))

    return project_path, state


# ============================================================================
# STATE.MD CREATION (REQ-STATE-001)
# ============================================================================


def test_create_state_creates_file(mock_env):
    """REQ-STATE-001: create-state creates STATE.md"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    assert (project_path / "STATE.md").exists()


def test_create_state_has_all_sections(mock_env):
    """REQ-STATE-001: STATE.md contains all required sections"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    content = (project_path / "STATE.md").read_text()
    assert "## Meta" in content
    assert "## Execution Plan" in content
    assert "## Current Step Detail" in content
    assert "## Uncommitted Work" in content
    assert "## Session Log" in content
    assert "## Next Session Instructions" in content


def test_create_state_meta_fields(mock_env):
    """REQ-STATE-001: Meta section contains required fields"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    content = (project_path / "STATE.md").read_text()
    assert "001-test-project" in content
    assert "Test request" in content
    assert "coding" in content


def test_create_state_checkbox_syntax(mock_env):
    """REQ-STATE-001: Execution plan uses checkbox syntax"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    content = (project_path / "STATE.md").read_text()
    assert "- [ ]" in content or "- [x]" in content


def test_create_state_idempotent(mock_env, capsys):
    """REQ-STATE-001: Calling create-state twice doesn't overwrite"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    first_content = (project_path / "STATE.md").read_text()
    session_state.cmd_create_state("001-test-project")
    second_content = (project_path / "STATE.md").read_text()
    assert first_content == second_content


# ============================================================================
# CURRENT-PROJECT.JSON (REQ-STATE-002)
# ============================================================================


def test_current_project_has_state_file(mock_env):
    """REQ-STATE-002: current-project.json includes state_file field"""
    _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    assert "state_file" in state


def test_current_project_relative_path(mock_env):
    """REQ-STATE-002: state_file uses relative path"""
    _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state_file = state.get("state_file", "")
    assert not state_file.startswith("/")


def test_current_project_single_active(mock_env):
    """REQ-STATE-002: Only one active project tracked"""
    _create_test_project(mock_env, "001-first")
    session_state.cmd_create_state("001-first")
    _create_test_project(mock_env, "002-second")
    session_state.cmd_create_state("002-second")
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    assert state["project_id"] == "002-second"


def test_current_project_status_match(mock_env):
    """REQ-STATE-002: current-project.json phase matches STATE.md"""
    _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    content = (mock_env / ".qralph" / "projects" / "001-test-project" / "STATE.md").read_text()
    assert state["phase"] in content


# ============================================================================
# CLAUDE.MD INJECTION (REQ-STATE-003)
# ============================================================================


def test_inject_claude_md_appends(mock_env):
    """REQ-STATE-003: Injection appends QRALPH section"""
    _create_test_project(mock_env)
    claude_md = mock_env / "CLAUDE.md"
    claude_md.write_text("# Project\n\nExisting content.\n")
    session_state.cmd_inject_claude_md(str(claude_md))
    content = claude_md.read_text()
    assert "## QRALPH Project State" in content
    assert "Existing content" in content


def test_inject_claude_md_idempotent(mock_env):
    """REQ-STATE-003: Multiple injections don't duplicate"""
    _create_test_project(mock_env)
    claude_md = mock_env / "CLAUDE.md"
    claude_md.write_text("# Project\n\nContent.\n")
    session_state.cmd_inject_claude_md(str(claude_md))
    first = claude_md.read_text()
    session_state.cmd_inject_claude_md(str(claude_md))
    second = claude_md.read_text()
    assert first == second


def test_inject_claude_md_preserves_existing(mock_env):
    """REQ-STATE-003: Injection preserves all existing content"""
    _create_test_project(mock_env)
    claude_md = mock_env / "CLAUDE.md"
    original = "# My Project\n\n## Important Rules\n\n- Rule 1\n- Rule 2\n"
    claude_md.write_text(original)
    session_state.cmd_inject_claude_md(str(claude_md))
    content = claude_md.read_text()
    assert original.rstrip() in content


def test_inject_claude_md_has_separator(mock_env):
    """REQ-STATE-003: Injection includes --- separator"""
    _create_test_project(mock_env)
    claude_md = mock_env / "CLAUDE.md"
    claude_md.write_text("# Project\n")
    session_state.cmd_inject_claude_md(str(claude_md))
    content = claude_md.read_text()
    assert "---" in content


def test_inject_claude_md_empty_file(mock_env):
    """REQ-STATE-003: Handles empty CLAUDE.md"""
    _create_test_project(mock_env)
    claude_md = mock_env / "CLAUDE.md"
    claude_md.write_text("")
    session_state.cmd_inject_claude_md(str(claude_md))
    content = claude_md.read_text()
    assert "## QRALPH Project State" in content


def test_inject_claude_md_missing_file(mock_env, capsys):
    """REQ-STATE-003: Error when CLAUDE.md doesn't exist"""
    session_state.cmd_inject_claude_md(str(mock_env / "nonexistent.md"))
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()


# ============================================================================
# SESSION START (REQ-STATE-004)
# ============================================================================


def test_session_start_active_project(mock_env, capsys):
    """REQ-STATE-004: session-start detects active project"""
    _create_test_project(mock_env)
    result = session_state.cmd_session_start()
    assert result["status"] == "session_started"
    assert result["project_id"] == "001-test-project"


def test_session_start_includes_next_instructions(mock_env):
    """REQ-STATE-004: Output includes next instructions"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    result = session_state.cmd_session_start()
    assert "next_instructions" in result


@patch.object(session_state, '_get_git_diff_stat', return_value="foo.py | 5 +++--")
def test_session_start_uncommitted_alerts(mock_git, mock_env):
    """REQ-STATE-004: Alerts for uncommitted work"""
    _create_test_project(mock_env)
    result = session_state.cmd_session_start()
    assert result["uncommitted_work"] is True


def test_session_start_output_size(mock_env):
    """REQ-STATE-004: Output stays under 2000 tokens (~8000 chars)"""
    _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    result = session_state.cmd_session_start()
    output_str = json.dumps(result)
    assert len(output_str) < 8000


def test_session_start_no_active_project(mock_env, capsys):
    """REQ-STATE-004: Handles no active project"""
    result = session_state.cmd_session_start()
    assert result["status"] == "no_active_project"


# ============================================================================
# SESSION END (REQ-STATE-005)
# ============================================================================


def test_session_end_updates_checklist(mock_env):
    """REQ-STATE-005: session-end updates checklist"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")

    # Simulate phase advance
    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state["phase"] = "REVIEWING"
    (mock_env / ".qralph" / "current-project.json").write_text(json.dumps(state, indent=2))

    session_state.cmd_session_end("001-test-project")
    content = (project_path / "STATE.md").read_text()
    assert "REVIEWING" in content


def test_session_end_advances_step(mock_env):
    """REQ-STATE-005: session-end updates current_step in state"""
    _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")

    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state["phase"] = "DISCOVERING"
    (mock_env / ".qralph" / "current-project.json").write_text(json.dumps(state, indent=2))

    session_state.cmd_session_end("001-test-project")
    updated_state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    assert updated_state["current_step"] == 2  # DISCOVERING is step 2


@patch.object(session_state, '_get_git_diff_stat', return_value="bar.py | 10 ++++++----")
def test_session_end_uncommitted_work(mock_git, mock_env):
    """REQ-STATE-005: session-end captures uncommitted work"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    session_state.cmd_session_end("001-test-project")
    content = (project_path / "STATE.md").read_text()
    assert "bar.py" in content


def test_session_end_appends_session_log(mock_env):
    """REQ-STATE-005: session-end adds row to session log"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")
    session_state.cmd_session_end("001-test-project")
    content = (project_path / "STATE.md").read_text()
    assert "Session end" in content


def test_session_end_completion_detection(mock_env):
    """REQ-STATE-005: session-end detects COMPLETE phase"""
    project_path, _ = _create_test_project(mock_env)
    session_state.cmd_create_state("001-test-project")

    state = json.loads((mock_env / ".qralph" / "current-project.json").read_text())
    state["phase"] = "COMPLETE"
    (mock_env / ".qralph" / "current-project.json").write_text(json.dumps(state, indent=2))

    result = session_state.cmd_session_end("001-test-project")
    assert result["is_complete"] is True


# ============================================================================
# RECOVERY (REQ-STATE-006)
# ============================================================================


def test_recover_from_git(mock_env):
    """REQ-STATE-006: Reconstruct state from checkpoints"""
    project_path, state = _create_test_project(mock_env)

    # Create a checkpoint
    checkpoint = project_path / "checkpoints" / "state.json"
    state["phase"] = "REVIEWING"
    checkpoint.write_text(json.dumps(state, indent=2))

    result = session_state.cmd_recover("001-test-project")
    assert result["status"] == "recovered"


def test_recover_marks_uncertain(mock_env):
    """REQ-STATE-006: Recovery marks items as STATUS UNKNOWN"""
    project_path, _ = _create_test_project(mock_env)
    result = session_state.cmd_recover("001-test-project")
    state_md = (project_path / "STATE.md").read_text()
    assert "RECOVERED" in state_md


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


def test_format_checklist_init():
    """Checklist shows INIT as current"""
    result = session_state._format_checklist(session_state.QRALPH_PHASES, "INIT")
    assert "**INIT** (current)" in result


def test_format_checklist_reviewing():
    """Checklist marks earlier phases as complete"""
    result = session_state._format_checklist(session_state.QRALPH_PHASES, "REVIEWING")
    assert "[x] INIT" in result
    assert "[x] DISCOVERING" in result
    assert "**REVIEWING** (current)" in result
    assert "[ ] EXECUTING" in result


# ============================================================================
# LOOP BUG FIXES (Phase 1H)
# ============================================================================


def test_recover_preserves_complete_phase(mock_env):
    """Bug 1F: Recovery should not override COMPLETE phase based on SYNTHESIS.md existence."""
    project_path, state = _create_test_project(mock_env)

    # Set state to COMPLETE with SUMMARY.md
    state["phase"] = "COMPLETE"
    state["completed_at"] = datetime.now().isoformat()
    checkpoint_dir = project_path / "checkpoints"
    checkpoint_file = checkpoint_dir / "state.json"
    checkpoint_file.write_text(json.dumps(state, indent=2))

    # Create SYNTHESIS.md (which would normally cause phase to be inferred as EXECUTING)
    (project_path / "SYNTHESIS.md").write_text("# Synthesis\nDone.")
    # Create SUMMARY.md (definitive proof of COMPLETE)
    (project_path / "SUMMARY.md").write_text("# Summary\nProject complete.")

    session_state.cmd_recover("001-test-project")

    # Verify phase is still COMPLETE, not overridden to EXECUTING
    current_file = mock_env / ".qralph" / "current-project.json"
    recovered = json.loads(current_file.read_text())
    assert recovered["phase"] == "COMPLETE"


def test_recover_infers_executing_without_summary(mock_env):
    """Bug 1F: Recovery infers EXECUTING from SYNTHESIS.md when phase is non-terminal."""
    project_path, state = _create_test_project(mock_env)

    # Set state to REVIEWING (non-terminal)
    state["phase"] = "REVIEWING"
    checkpoint_dir = project_path / "checkpoints"
    checkpoint_file = checkpoint_dir / "state.json"
    checkpoint_file.write_text(json.dumps(state, indent=2))

    # Create SYNTHESIS.md without SUMMARY.md
    (project_path / "SYNTHESIS.md").write_text("# Synthesis\nIn progress.")

    session_state.cmd_recover("001-test-project")

    current_file = mock_env / ".qralph" / "current-project.json"
    recovered = json.loads(current_file.read_text())
    assert recovered["phase"] == "EXECUTING"


def test_recover_from_corrupt_checkpoint_with_fallback(mock_env):
    """F-012: Recovery from corrupt checkpoint falls back to minimal state reconstruction."""
    project_id = "001-corrupt-test"
    project_dir = mock_env / ".qralph" / "projects" / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "agent-outputs").mkdir()
    checkpoint_dir = project_dir / "checkpoints"
    checkpoint_dir.mkdir()

    # Write a corrupt checkpoint (invalid JSON)
    (checkpoint_dir / "state.json").write_text("{invalid json content!!!")

    # Write a valid older checkpoint
    valid_state = {
        "project_id": project_id,
        "project_path": str(project_dir),
        "request": "test request",
        "mode": "coding",
        "phase": "REVIEWING",
        "created_at": datetime.now().isoformat(),
        "agents": ["security-reviewer"],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
    }
    # Also put a corrupt one as the latest (sorted last)
    (checkpoint_dir / "reviewing-120000.json").write_text(json.dumps(valid_state))
    (checkpoint_dir / "reviewing-130000.json").write_text("totally corrupt {{{")

    # Run recovery
    with patch.object(session_state, '_get_git_diff_stat', return_value=""), \
         patch.object(session_state, '_get_git_log_oneline', return_value=""):
        result = session_state.cmd_recover(project_id)

    # Should recover from the valid checkpoint (reviewing-120000.json) after corrupt one fails
    assert result is not None
    assert result["status"] == "recovered"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
