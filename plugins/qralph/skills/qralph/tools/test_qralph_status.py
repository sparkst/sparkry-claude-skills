#!/usr/bin/env python3
"""
Tests for QRALPH Status Monitor (qralph-status.py).

T-1: Basic tests for list view, detail view, and helpers.
"""

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

# Load qralph-status.py
SCRIPT_DIR = Path(__file__).parent
status_path = SCRIPT_DIR / "qralph-status.py"
spec = importlib.util.spec_from_file_location("qralph_status", status_path)
qralph_status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qralph_status)


@pytest.fixture
def mock_qralph(tmp_path):
    """Create a temporary .qralph directory structure."""
    qralph_dir = tmp_path / ".qralph"
    projects_dir = qralph_dir / "projects"

    # Create project 001
    proj_001 = projects_dir / "001-test-project"
    (proj_001 / "checkpoints").mkdir(parents=True)

    state_001 = {
        "project_id": "001-test-project",
        "project_path": str(proj_001),
        "request": "Fix the authentication bug",
        "mode": "coding",
        "phase": "REVIEWING",
        "created_at": datetime.now().isoformat(),
        "agents": ["security-reviewer", "sde-iii"],
        "findings": [],
        "heal_attempts": 0,
        "circuit_breakers": {
            "total_tokens": 5000,
            "total_cost_usd": 1.50,
            "error_counts": {},
        },
    }
    (proj_001 / "checkpoints" / "state.json").write_text(json.dumps(state_001))

    # Create project 002
    proj_002 = projects_dir / "002-complete-project"
    (proj_002 / "checkpoints").mkdir(parents=True)

    state_002 = {
        "project_id": "002-complete-project",
        "project_path": str(proj_002),
        "request": "Add dark mode",
        "mode": "coding",
        "phase": "COMPLETE",
        "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        "agents": ["ux-designer"],
        "findings": [],
        "heal_attempts": 0,
        "circuit_breakers": {
            "total_tokens": 200000,
            "total_cost_usd": 12.00,
            "error_counts": {},
        },
    }
    (proj_002 / "checkpoints" / "state.json").write_text(json.dumps(state_002))

    # Create current-project.json
    (qralph_dir / "current-project.json").write_text(json.dumps({"project_id": "001-test-project"}))

    return qralph_dir


# ──── Helper function tests ────


class TestHelpers:
    def test_format_duration_seconds(self):
        """Duration < 1 minute shows seconds."""
        recent = (datetime.now() - timedelta(seconds=30)).isoformat()
        result = qralph_status.format_duration(recent)
        assert "s" in result

    def test_format_duration_minutes(self):
        """Duration shows minutes and seconds."""
        recent = (datetime.now() - timedelta(minutes=5, seconds=30)).isoformat()
        result = qralph_status.format_duration(recent)
        assert "m" in result

    def test_format_duration_hours(self):
        """Duration shows hours and minutes."""
        recent = (datetime.now() - timedelta(hours=2, minutes=15)).isoformat()
        result = qralph_status.format_duration(recent)
        assert "h" in result

    def test_format_duration_days(self):
        """Duration shows days for multi-day durations."""
        recent = (datetime.now() - timedelta(days=3, hours=5)).isoformat()
        result = qralph_status.format_duration(recent)
        assert "d" in result

    def test_format_duration_invalid(self):
        """Invalid timestamp returns 'unknown'."""
        assert qralph_status.format_duration("not-a-date") == "unknown"

    def test_format_percentage(self):
        """Percentage formatting works correctly."""
        assert qralph_status.format_percentage(250000, 500000) == "50%"
        assert qralph_status.format_percentage(0, 500000) == "0%"
        assert qralph_status.format_percentage(0, 0) == "0%"

    def test_get_phase_progress(self):
        """Phase progress returns correct position."""
        current, total = qralph_status.get_phase_progress("INIT")
        assert current == 1
        assert total > 0

        current, total = qralph_status.get_phase_progress("COMPLETE")
        assert current == total

        current, total = qralph_status.get_phase_progress("NONEXISTENT")
        assert current == 0

    def test_count_findings_by_priority(self):
        """Findings are counted by priority."""
        findings = [
            {"priority": "P0"},
            {"priority": "P0"},
            {"priority": "P1"},
            {"priority": "P2"},
            {"priority": "P2"},
            {"priority": "P2"},
        ]
        counts = qralph_status.count_findings_by_priority(findings)
        assert counts["P0"] == 2
        assert counts["P1"] == 1
        assert counts["P2"] == 3

    def test_count_findings_empty(self):
        """Empty findings returns zeros."""
        counts = qralph_status.count_findings_by_priority([])
        assert counts == {"P0": 0, "P1": 0, "P2": 0}

    def test_get_agent_status_icon(self):
        """Status icons return strings with ANSI codes or fallback chars."""
        # Just verify they return non-empty strings
        assert qralph_status.get_agent_status_icon({"status": "complete"})
        assert qralph_status.get_agent_status_icon({"status": "running"})
        assert qralph_status.get_agent_status_icon({"status": "error"})
        assert qralph_status.get_agent_status_icon({"status": "pending"})
        assert qralph_status.get_agent_status_icon({})


# ──── Data loading tests ────


class TestDataLoading:
    def test_list_all_projects(self, mock_qralph):
        """Lists all project directories."""
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            projects = qralph_status.list_all_projects()
        assert "001-test-project" in projects
        assert "002-complete-project" in projects

    def test_list_all_projects_empty(self, tmp_path):
        """Returns empty list when no projects exist."""
        with patch.object(qralph_status, "get_qralph_root", return_value=tmp_path / ".qralph"):
            projects = qralph_status.list_all_projects()
        assert projects == []

    def test_load_current_project(self, mock_qralph):
        """Loads current project metadata."""
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            current = qralph_status.load_current_project()
        assert current is not None
        assert current["project_id"] == "001-test-project"

    def test_load_current_project_missing(self, tmp_path):
        """Returns None when no current project."""
        with patch.object(qralph_status, "get_qralph_root", return_value=tmp_path):
            current = qralph_status.load_current_project()
        assert current is None

    def test_load_project_state(self, mock_qralph):
        """Loads project state from checkpoint."""
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            state = qralph_status.load_project_state("001-test-project")
        assert state is not None
        assert state["phase"] == "REVIEWING"

    def test_load_project_state_missing(self, mock_qralph):
        """Returns None for nonexistent project."""
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            state = qralph_status.load_project_state("999-nonexistent")
        assert state is None


# ──── Display tests ────


class TestDisplay:
    def test_display_list_view_no_crash(self, mock_qralph, capsys):
        """List view runs without errors."""
        qralph_status.Colors.disable()
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            qralph_status.display_list_view()
        output = capsys.readouterr().out
        assert "001-test-project" in output
        assert "002-complete-project" in output

    def test_display_list_view_empty(self, tmp_path, capsys):
        """List view handles no projects gracefully."""
        qralph_status.Colors.disable()
        qralph_root = tmp_path / ".qralph"
        qralph_root.mkdir()
        with patch.object(qralph_status, "get_qralph_root", return_value=qralph_root):
            qralph_status.display_list_view()
        output = capsys.readouterr().out
        assert "No projects found" in output

    def test_display_detailed_view_no_crash(self, mock_qralph, capsys):
        """Detail view runs without errors for valid project."""
        qralph_status.Colors.disable()
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            qralph_status.display_detailed_view("001-test-project")
        output = capsys.readouterr().out
        assert "REVIEWING" in output
        assert "001-test-project" in output
        assert "Circuit Breakers" in output

    def test_display_detailed_view_complete(self, mock_qralph, capsys):
        """Detail view renders COMPLETE phase."""
        qralph_status.Colors.disable()
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            qralph_status.display_detailed_view("002-complete-project")
        output = capsys.readouterr().out
        assert "COMPLETE" in output
        assert "complete" in output.lower()

    def test_display_detailed_view_missing(self, mock_qralph, capsys):
        """Detail view handles missing project gracefully."""
        qralph_status.Colors.disable()
        with patch.object(qralph_status, "get_qralph_root", return_value=mock_qralph):
            qralph_status.display_detailed_view("999-nonexistent")
        output = capsys.readouterr().out
        assert "Error" in output or "No state" in output


# ──── Colors tests ────


class TestColors:
    def test_colors_disable(self):
        """Colors.disable() sets all codes to empty string."""
        qralph_status.Colors.disable()
        assert qralph_status.Colors.RESET == ""
        assert qralph_status.Colors.BOLD == ""
        assert qralph_status.Colors.GREEN == ""
