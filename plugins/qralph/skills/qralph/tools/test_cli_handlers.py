"""Tests for action handlers for QRALPH CLI."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from cli_handlers import classify_action, handle_spawn_agents, should_escalate_gate


class TestClassifyAction:
    """REQ-CLI-HANDLERS — action classification."""

    @pytest.mark.parametrize(
        "action_type",
        [
            "define_tasks",
            "demo_feedback",
            "demo_replan",
            "backtrack_replan",
            "complete",
            "quality_dashboard",
            "learn_complete",
            "smoke_results",
        ],
    )
    def test_classify_deterministic_actions(self, action_type: str) -> None:
        """Deterministic actions return 'deterministic'."""
        action = {"action": action_type}
        assert classify_action(action) == "deterministic"

    def test_classify_spawn_agents(self) -> None:
        """spawn_agents returns 'work_agent'."""
        action = {"action": "spawn_agents", "agents": []}
        assert classify_action(action) == "work_agent"

    def test_classify_confirm_with_escalation(self) -> None:
        """confirm_plan always escalates → 'decision_agent'."""
        action = {"action": "confirm_plan"}
        assert classify_action(action) == "decision_agent"

    def test_classify_confirm_concept_escalates(self) -> None:
        """confirm_concept always escalates → 'decision_agent'."""
        action = {"action": "confirm_concept"}
        assert classify_action(action) == "decision_agent"

    def test_classify_confirm_template_auto_confirms_clear_winner(self) -> None:
        """confirm_template with clear score margin → 'deterministic'."""
        action = {
            "action": "confirm_template",
            "scores": {"landing": 9, "dashboard": 5, "blog": 3},
        }
        assert classify_action(action) == "deterministic"

    def test_classify_confirm_template_escalates_tied(self) -> None:
        """confirm_template with tied scores → 'decision_agent'."""
        action = {
            "action": "confirm_template",
            "scores": {"landing": 8, "dashboard": 7},
        }
        assert classify_action(action) == "decision_agent"

    def test_classify_escalate_to_user(self) -> None:
        """escalate_to_user returns 'decision_agent'."""
        action = {"action": "escalate_to_user"}
        assert classify_action(action) == "decision_agent"

    def test_classify_error(self) -> None:
        """error returns 'decision_agent'."""
        action = {"action": "error"}
        assert classify_action(action) == "decision_agent"

    def test_classify_unknown_defaults_to_decision(self) -> None:
        """Unknown action type defaults to 'decision_agent'."""
        action = {"action": "totally_unknown_action_xyz"}
        assert classify_action(action) == "decision_agent"


class TestShouldEscalateGate:
    """REQ-CLI-HANDLERS — escalation gate logic."""

    def test_should_escalate_gate_tied_scores(self) -> None:
        """Tied template scores → True."""
        action = {
            "action": "confirm_template",
            "scores": {"landing": 7, "dashboard": 7},
        }
        assert should_escalate_gate(action) is True

    def test_should_escalate_gate_close_scores(self) -> None:
        """Close template scores (diff < 2) → True."""
        action = {
            "action": "confirm_template",
            "scores": {"landing": 8, "dashboard": 7},
        }
        assert should_escalate_gate(action) is True

    def test_should_escalate_gate_clear_winner(self) -> None:
        """Clear template winner (diff >= 2) → False."""
        action = {
            "action": "confirm_template",
            "scores": {"landing": 9, "dashboard": 5},
        }
        assert should_escalate_gate(action) is False

    def test_should_escalate_gate_confirm_concept(self) -> None:
        """confirm_concept always escalates."""
        action = {"action": "confirm_concept"}
        assert should_escalate_gate(action) is True

    def test_should_escalate_gate_confirm_plan(self) -> None:
        """confirm_plan always escalates."""
        action = {"action": "confirm_plan"}
        assert should_escalate_gate(action) is True

    def test_should_escalate_gate_confirm_ideation(self) -> None:
        """confirm_ideation always escalates."""
        action = {"action": "confirm_ideation"}
        assert should_escalate_gate(action) is True

    def test_should_escalate_gate_confirm_personas(self) -> None:
        """confirm_personas always escalates."""
        action = {"action": "confirm_personas"}
        assert should_escalate_gate(action) is True

    def test_should_escalate_gate_unknown_defaults_true(self) -> None:
        """Unknown confirm type defaults to True."""
        action = {"action": "confirm_something_new"}
        assert should_escalate_gate(action) is True


class TestHandleSpawnAgents:
    """REQ-CLI-HANDLERS — spawn_agents command building."""

    def test_handle_spawn_agents_builds_commands(self) -> None:
        """Builds correct command config dicts from agent list."""
        action = {
            "action": "spawn_agents",
            "agents": [
                {"name": "researcher", "model": "sonnet", "prompt": "Research the topic"},
                {"name": "designer", "model": "haiku", "prompt": "Design the layout"},
            ],
            "output_dir": "/tmp/qralph/agents",
        }
        result = handle_spawn_agents(action, "/tmp/qralph")
        assert len(result) == 2
        assert result[0]["name"] == "researcher"
        assert result[0]["model"] == "sonnet"
        assert result[0]["prompt"] == "Research the topic"
        assert result[0]["output_file"] == "/tmp/qralph/agents/researcher.md"
        assert result[1]["name"] == "designer"
        assert result[1]["output_file"] == "/tmp/qralph/agents/designer.md"

    def test_handle_spawn_agents_empty_list(self) -> None:
        """Empty agents list returns empty result."""
        action = {"action": "spawn_agents", "agents": [], "output_dir": "/tmp/out"}
        result = handle_spawn_agents(action, "/tmp/qralph")
        assert result == []
