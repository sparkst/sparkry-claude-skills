"""Tests for cli_escalation — SessionStore, escalation engine, and prompt building."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli_escalation import SessionStore, escalate, _build_escalation_prompt


class TestSessionStore:
    """REQ-CLI-001 — SessionStore tracks session IDs by (project_id, phase_key)."""

    def test_session_store_roundtrip(self, tmp_path: Path) -> None:
        """REQ-CLI-001a — store and retrieve a session ID."""
        store = SessionStore(tmp_path / "sessions.json")
        store.set("proj-1", "CONCEPT", "sess-abc-123")

        assert store.get("proj-1", "CONCEPT") == "sess-abc-123"
        assert store.get("proj-1", "NONEXISTENT") is None
        assert store.get("other-proj", "CONCEPT") is None

    def test_session_store_invalidate_on_phase_change(self, tmp_path: Path) -> None:
        """REQ-CLI-001b — advance_phase removes sessions from old phases."""
        store = SessionStore(tmp_path / "sessions.json")
        store.set("proj-1", "CONCEPT", "sess-concept")
        store.set("proj-1", "CONCEPT_REVIEW", "sess-concept-review")
        store.set("proj-1", "BUILD", "sess-build")

        store.advance_phase("proj-1", "BUILD")

        # BUILD phase sessions survive
        assert store.get("proj-1", "BUILD") == "sess-build"
        # CONCEPT* sessions are invalidated
        assert store.get("proj-1", "CONCEPT") is None
        assert store.get("proj-1", "CONCEPT_REVIEW") is None

    def test_session_store_persists_to_disk(self, tmp_path: Path) -> None:
        """REQ-CLI-001c — reload from disk preserves data."""
        path = tmp_path / "sessions.json"
        store = SessionStore(path)
        store.set("proj-1", "CONCEPT", "sess-concept")
        store.set("proj-2", "BUILD", "sess-build")

        # Create a new instance from the same path
        store2 = SessionStore(path)
        assert store2.get("proj-1", "CONCEPT") == "sess-concept"
        assert store2.get("proj-2", "BUILD") == "sess-build"

    def test_advance_phase_only_affects_target_project(self, tmp_path: Path) -> None:
        """REQ-CLI-001d — advance_phase for one project doesn't touch another."""
        store = SessionStore(tmp_path / "sessions.json")
        store.set("proj-1", "CONCEPT", "sess-1")
        store.set("proj-2", "CONCEPT", "sess-2")

        store.advance_phase("proj-1", "BUILD")

        assert store.get("proj-1", "CONCEPT") is None
        assert store.get("proj-2", "CONCEPT") == "sess-2"

    def test_advance_phase_persists(self, tmp_path: Path) -> None:
        """REQ-CLI-001e — invalidation is persisted to disk."""
        path = tmp_path / "sessions.json"
        store = SessionStore(path)
        store.set("proj-1", "CONCEPT", "sess-concept")
        store.set("proj-1", "BUILD", "sess-build")

        store.advance_phase("proj-1", "BUILD")

        store2 = SessionStore(path)
        assert store2.get("proj-1", "CONCEPT") is None
        assert store2.get("proj-1", "BUILD") == "sess-build"


class TestEscalate:
    """REQ-CLI-002 — escalate() spawns/resumes claude sessions for decisions."""

    def _make_store(self, tmp_path: Path) -> SessionStore:
        return SessionStore(tmp_path / "sessions.json")

    @patch("cli_escalation.subprocess.run")
    def test_escalate_returns_decision(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """REQ-CLI-002a — successful escalation returns decision and stores session."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "DECISION: proceed\nReasoning here.", "session_id": "sess-new-123"}),
            stderr="",
        )
        store = self._make_store(tmp_path)
        result = escalate(
            store=store,
            project_id="proj-1",
            phase_key="CONCEPT",
            prompt="Should we proceed?",
            rules="Always proceed unless blocked.",
            progress={"phase_index": 1, "phase_total": 5, "current_phase": "CONCEPT", "sub_phase": "synthesis"},
            working_dir="/tmp/test",
        )

        assert result["decision"] == "DECISION: proceed\nReasoning here."
        assert result["session_id"] == "sess-new-123"
        assert store.get("proj-1", "CONCEPT") == "sess-new-123"

        # Verify subprocess was called without --resume
        cmd_args = mock_run.call_args[0][0]
        assert "--resume" not in cmd_args

    @patch("cli_escalation.subprocess.run")
    def test_escalate_resumes_existing_session(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """REQ-CLI-002b — existing session ID triggers --resume flag."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"result": "DECISION: continue", "session_id": "sess-existing-456"}),
            stderr="",
        )
        store = self._make_store(tmp_path)
        store.set("proj-1", "CONCEPT", "sess-existing-456")

        result = escalate(
            store=store,
            project_id="proj-1",
            phase_key="CONCEPT",
            prompt="Continue?",
            rules="Rules here.",
            progress={"phase_index": 2, "phase_total": 5, "current_phase": "CONCEPT", "sub_phase": "review"},
            working_dir="/tmp/test",
        )

        cmd_args = mock_run.call_args[0][0]
        resume_idx = cmd_args.index("--resume")
        assert cmd_args[resume_idx + 1] == "sess-existing-456"

    @patch("cli_escalation.subprocess.run")
    def test_escalate_handles_subprocess_error(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """REQ-CLI-002c — subprocess failure returns error dict."""
        mock_run.side_effect = Exception("claude not found")
        store = self._make_store(tmp_path)

        result = escalate(
            store=store,
            project_id="proj-1",
            phase_key="CONCEPT",
            prompt="Decide.",
            rules="Rules.",
            progress={"phase_index": 1, "phase_total": 3, "current_phase": "CONCEPT", "sub_phase": "init"},
            working_dir="/tmp/test",
        )

        assert result["decision"] == ""
        assert result["session_id"] == ""
        assert "error" in result
        assert "claude not found" in result["error"]


class TestBuildEscalationPrompt:
    """REQ-CLI-003 — _build_escalation_prompt composes structured prompts."""

    def test_build_escalation_prompt_includes_all_sections(self) -> None:
        """REQ-CLI-003a — output contains all 4 required sections."""
        prompt = _build_escalation_prompt(
            prompt="Should we refactor?",
            rules="Only refactor if tests pass.",
            progress={"phase_index": 2, "phase_total": 6, "current_phase": "BUILD", "sub_phase": "implement"},
        )

        assert "## Pipeline Progress" in prompt
        assert "2/6" in prompt or "2 of 6" in prompt
        assert "BUILD" in prompt
        assert "implement" in prompt
        assert "## Decision Rules for This Step" in prompt
        assert "Only refactor if tests pass." in prompt
        assert "## Current Situation" in prompt
        assert "Should we refactor?" in prompt
        assert "## Your Response Format" in prompt
        assert "DECISION:" in prompt
        assert "escalate_to_user" in prompt
