"""Tests for reviewer model tiering — REQ-101, REQ-102.

Sonnet 5 default; deterministic escalation to Opus for high-stakes lenses
(security/architecture) or when change complexity crosses thresholds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

team_selector = load_sibling("team-selector.py")

AgentDef = team_selector.AgentDef
Complexity = team_selector.Complexity
resolve_reviewer_model = team_selector.resolve_reviewer_model
select_team_with_scores = team_selector.select_team_with_scores
main = team_selector.main


def _agent(name: str, model: str = "sonnet", domains=None, lens: str = "x") -> "AgentDef":
    return AgentDef(
        name=name,
        domains=domains or ["backend"],
        model=model,
        description="d",
        review_lens=lens,
    )


SIMPLE = None  # set in fixture below


@pytest.fixture
def simple() -> "Complexity":
    """A trivial change: one file, few tools, tiny context."""
    return Complexity(file_count=1, tool_types=1, context_fraction=0.0)


# ---------------------------------------------------------------------------
# REQ-101: escalation rules
# ---------------------------------------------------------------------------

class TestResolveReviewerModel:
    def test_simple_non_high_stakes_reviewer_is_sonnet(self, simple):
        assert resolve_reviewer_model(_agent("code-quality-reviewer"), simple) == "sonnet"

    def test_security_reviewer_always_opus(self, simple):
        assert resolve_reviewer_model(_agent("security-reviewer"), simple) == "opus"

    def test_architecture_reviewer_always_opus(self, simple):
        assert resolve_reviewer_model(_agent("architecture-reviewer"), simple) == "opus"

    def test_multi_file_change_escalates_to_opus(self):
        c = Complexity(file_count=2, tool_types=1, context_fraction=0.0)
        assert resolve_reviewer_model(_agent("ux-reviewer"), c) == "opus"

    def test_more_than_two_tool_types_escalates(self):
        c = Complexity(file_count=1, tool_types=3, context_fraction=0.0)
        assert resolve_reviewer_model(_agent("ux-reviewer"), c) == "opus"

    def test_exactly_two_tool_types_does_not_escalate(self):
        c = Complexity(file_count=1, tool_types=2, context_fraction=0.0)
        assert resolve_reviewer_model(_agent("ux-reviewer"), c) == "sonnet"

    def test_context_over_twenty_percent_escalates(self):
        c = Complexity(file_count=1, tool_types=1, context_fraction=0.21)
        assert resolve_reviewer_model(_agent("ux-reviewer"), c) == "opus"

    def test_context_at_twenty_percent_does_not_escalate(self):
        c = Complexity(file_count=1, tool_types=1, context_fraction=0.20)
        assert resolve_reviewer_model(_agent("ux-reviewer"), c) == "sonnet"


# ---------------------------------------------------------------------------
# REQ-102: Complexity construction + wiring
# ---------------------------------------------------------------------------

class TestComplexity:
    def test_from_artifact_bytes_computes_context_fraction(self):
        # 40_000 est tokens (160_000 bytes / 4) over a 200_000 window = 0.20
        c = Complexity.from_signals(file_count=1, tool_types=1,
                                    artifact_bytes=160_000, context_window=200_000)
        assert c.context_fraction == pytest.approx(0.20)

    def test_defaults_are_conservative(self):
        c = Complexity()
        assert c.file_count == 1
        assert c.tool_types == 1
        assert c.context_fraction == 0.0


class TestTeamWiringModel:
    def test_team_models_reflect_resolution(self):
        # A backend/security artifact selects a team; security -> opus, others sonnet
        team, _ = select_team_with_scores(
            "add auth token validation to the api endpoint security",
            complexity=Complexity(file_count=1, tool_types=1, context_fraction=0.0),
        )
        by_name = {a.name: a.model for a in team}
        if "security-reviewer" in by_name:
            assert by_name["security-reviewer"] == "opus"
        # requirements-reviewer is always present and non-high-stakes -> sonnet
        assert by_name.get("requirements-reviewer") == "sonnet"

    def test_multi_file_complexity_promotes_all_non_haiku(self):
        team, _ = select_team_with_scores(
            "refactor backend modules",
            complexity=Complexity(file_count=5, tool_types=1, context_fraction=0.0),
        )
        # every reviewer escalates under multi-file complexity
        assert all(a.model == "opus" for a in team)


class TestCLIModelFlags:
    def test_json_output_reflects_escalation(self, capsys):
        rc = main([
            "add security auth to endpoint",
            "--files", "3",
            "--json",
        ])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert all(a["model"] == "opus" for a in payload["team"])

    def test_json_output_stays_sonnet_when_simple(self, capsys):
        rc = main([
            "tweak a copy string",
            "--files", "1",
            "--tool-types", "1",
            "--json",
        ])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        # non-high-stakes reviewers stay sonnet
        models = {a["name"]: a["model"] for a in payload["team"]}
        assert models.get("requirements-reviewer") == "sonnet"
