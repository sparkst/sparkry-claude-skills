"""Tests for step-specific agentic rules for QRALPH CLI decision agents."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from cli_rules import get_rules

_ALL_PHASES = [
    "IDEATE_BRAINSTORM",
    "IDEATE_WAITING",
    "IDEATE_REVIEW",
    "PERSONA_GEN",
    "PERSONA_REVIEW",
    "CONCEPT_SPAWN",
    "CONCEPT_WAITING",
    "CONCEPT_REVIEW",
    "INIT",
    "PLAN_WAITING",
    "PLAN_REVIEW",
]


class TestCliRules:
    """REQ-CLI-RULES — step-specific agentic rules."""

    @pytest.mark.parametrize("phase", _ALL_PHASES)
    def test_all_phases_have_rules(self, phase: str) -> None:
        """Every phase in scope returns a non-empty string > 50 chars."""
        rules = get_rules(phase)
        assert isinstance(rules, str)
        assert len(rules) > 50, f"{phase} rules too short: {len(rules)} chars"

    def test_rules_mention_escalation(self) -> None:
        """Rules for PLAN_REVIEW contain 'escalate'."""
        rules = get_rules("PLAN_REVIEW")
        assert "escalate" in rules.lower()

    def test_default_rules_for_unknown_phase(self) -> None:
        """Unknown phase returns default rules (not empty, not error)."""
        rules = get_rules("TOTALLY_UNKNOWN_PHASE_XYZ")
        assert isinstance(rules, str)
        assert len(rules) > 0
