"""Tests for qralph-cli.py — QRALPH CLI orchestration loop."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make sibling modules importable
sys.path.insert(0, str(Path(__file__).parent))

import importlib.util

_cli_path = Path(__file__).parent / "qralph-cli.py"
_cli_spec = importlib.util.spec_from_file_location("qralph_cli", _cli_path)
qralph_cli = importlib.util.module_from_spec(_cli_spec)
_cli_spec.loader.exec_module(qralph_cli)


class TestSpawnWorkAgent:
    """test_spawn_work_agent_writes_output — mock subprocess, verify file written."""

    def test_spawn_work_agent_writes_output(self, tmp_path: Path) -> None:
        output_file = tmp_path / "sub" / "agent-out.md"
        mock_result = MagicMock()
        mock_result.stdout = json.dumps({"result": "Agent output text here"})

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = qralph_cli.spawn_work_agent(
                name="test-agent",
                model="sonnet",
                prompt="Do the thing",
                output_file=str(output_file),
                working_dir=str(tmp_path),
            )

        assert output_file.exists()
        assert output_file.read_text() == "Agent output text here"
        assert result == "Agent output text here"
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "claude" in cmd[0]
        assert "-p" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd


class TestParseDecision:
    """Tests for _parse_decision helper."""

    def test_parse_decision_confirm(self) -> None:
        text = "DECISION: confirm\nThe plan looks good and covers all requirements."
        assert qralph_cli._parse_decision(text) == "confirm"

    def test_parse_decision_escalate(self) -> None:
        text = "Some preamble\nDECISION: escalate_to_user\nThis needs human input."
        assert qralph_cli._parse_decision(text) == "escalate_to_user"

    def test_parse_decision_no_decision_line(self) -> None:
        text = "I think this looks fine but I'm not sure what to do."
        assert qralph_cli._parse_decision(text) == "escalate_to_user"


class TestRunLoop:
    """test_run_loop_deterministic_to_complete — verify loop completes without escalation."""

    def test_run_loop_deterministic_to_complete(self, tmp_path: Path) -> None:
        # Simulate: pipeline returns two deterministic actions, then complete
        call_count = 0
        def fake_next(project_id=None, confirm=False, feedback=""):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return {
                    "action": "define_tasks",
                    "phase_progress": {
                        "phase_index": 1,
                        "total_phases": 5,
                        "current_phase": "PLAN",
                        "sub_phase": "PLAN_TASKS",
                    },
                }
            return {
                "action": "complete",
                "phase_progress": {
                    "phase_index": 5,
                    "total_phases": 5,
                    "current_phase": "COMPLETE",
                    "sub_phase": "COMPLETE",
                },
            }

        with (
            patch.object(qralph_cli, "pipeline_next", side_effect=fake_next),
            patch.object(qralph_cli, "escalate") as mock_escalate,
        ):
            result = qralph_cli.run_loop(
                project_id="test-001",
                working_dir=str(tmp_path),
            )

        assert result["action"] == "complete"
        mock_escalate.assert_not_called()
        assert call_count == 3
