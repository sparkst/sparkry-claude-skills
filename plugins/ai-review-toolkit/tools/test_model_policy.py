"""Tests for reviewer model tiering — REQ-101, REQ-102.

Sonnet 5 is the default. Opus is spent surgically under the revised policy
(OPT-005/006/014):

- resolve_reviewer_model is a *pure* function of explicit per-reviewer signals
  (escalation_eligible, high_stakes) — the team-level decisions of *who* is
  eligible now live in select_team_with_scores, so the JS mirror can stay a
  dumb parity-locked unit.
- Complexity escalation is per-reviewer, not team-wide: only the top-2
  domain-scoring specialist lenses are eligible, and the triggers are raised
  to file_count>3 / context_fraction>0.4 (the tool_types trigger is dropped).
- Security's opus seat is gated on the security/compliance domain scoring
  (>0.3) or an explicit --high-stakes flag, not on the lens name;
  architecture-reviewer is no longer an unconditional high-stakes seat.
- A hard cap of 2 opus seats per team.
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


@pytest.fixture
def simple() -> "Complexity":
    """A trivial change: one file, few tools, tiny context."""
    return Complexity(file_count=1, tool_types=1, context_fraction=0.0)


# ---------------------------------------------------------------------------
# REQ-101: resolve_reviewer_model is a pure function of explicit signals
# ---------------------------------------------------------------------------

class TestResolveReviewerModel:
    def test_simple_stays_sonnet(self, simple):
        # OPT-005: not eligible + no high-stakes -> the catalog model.
        assert resolve_reviewer_model(_agent("code-quality-reviewer"), simple) == "sonnet"

    def test_high_stakes_forces_opus(self, simple):
        # OPT-006: the caller decides high_stakes (domain score / flag); the
        # function just honours the boolean regardless of complexity.
        assert resolve_reviewer_model(
            _agent("security-reviewer"), simple, high_stakes=True
        ) == "opus"

    def test_security_name_alone_no_longer_opus(self, simple):
        # OPT-006: the lens NAME no longer auto-escalates. Without a scored
        # security domain (high_stakes=False) and without eligibility, sonnet.
        assert resolve_reviewer_model(
            _agent("security-reviewer"), simple,
            escalation_eligible=False, high_stakes=False,
        ) == "sonnet"

    def test_architecture_name_alone_no_longer_opus(self, simple):
        # OPT-006: architecture-reviewer dropped from the high-stakes set; it
        # only reaches opus via the per-reviewer complexity path.
        assert resolve_reviewer_model(
            _agent("architecture-reviewer"), simple,
            escalation_eligible=False, high_stakes=False,
        ) == "sonnet"

    def test_eligible_multi_file_escalates(self):
        # OPT-005: file_count>3 escalates, but only when eligible (top-2 lens).
        c = Complexity(file_count=4, tool_types=1, context_fraction=0.0)
        assert resolve_reviewer_model(
            _agent("ux-reviewer"), c, escalation_eligible=True
        ) == "opus"

    def test_not_eligible_multi_file_stays_sonnet(self):
        # OPT-005 keystone: complexity no longer escalates the WHOLE team. A
        # reviewer outside the top-2 domain lenses stays sonnet even on a big
        # multi-file change.
        c = Complexity(file_count=9, tool_types=1, context_fraction=0.0)
        assert resolve_reviewer_model(
            _agent("ux-reviewer"), c, escalation_eligible=False
        ) == "sonnet"

    def test_three_files_does_not_escalate(self):
        # OPT-005: trigger raised from >1 to >3.
        c = Complexity(file_count=3, tool_types=1, context_fraction=0.0)
        assert resolve_reviewer_model(
            _agent("ux-reviewer"), c, escalation_eligible=True
        ) == "sonnet"

    def test_tool_types_no_longer_a_trigger(self):
        # OPT-005: the tool_types>2 trigger is dropped entirely.
        c = Complexity(file_count=1, tool_types=9, context_fraction=0.0)
        assert resolve_reviewer_model(
            _agent("ux-reviewer"), c, escalation_eligible=True
        ) == "sonnet"

    def test_context_over_forty_percent_escalates(self):
        # OPT-005: context trigger raised from >0.20 to >0.40.
        c = Complexity(file_count=1, tool_types=1, context_fraction=0.41)
        assert resolve_reviewer_model(
            _agent("ux-reviewer"), c, escalation_eligible=True
        ) == "opus"

    def test_context_at_forty_percent_stays_sonnet(self):
        c = Complexity(file_count=1, tool_types=1, context_fraction=0.40)
        assert resolve_reviewer_model(
            _agent("ux-reviewer"), c, escalation_eligible=True
        ) == "sonnet"

    def test_high_stakes_beats_missing_complexity(self):
        # high_stakes short-circuits before complexity is even consulted.
        assert resolve_reviewer_model(
            _agent("security-reviewer"), complexity=None, high_stakes=True
        ) == "opus"


# ---------------------------------------------------------------------------
# REQ-102: Complexity construction + escalation thresholds
# ---------------------------------------------------------------------------

class TestComplexity:
    def test_from_artifact_bytes_computes_context_fraction(self):
        c = Complexity.from_signals(file_count=1, tool_types=1,
                                    artifact_bytes=160_000, context_window=200_000)
        assert c.context_fraction == pytest.approx(0.20)

    def test_defaults_are_conservative(self):
        c = Complexity()
        assert c.file_count == 1
        assert c.tool_types == 1
        assert c.context_fraction == 0.0

    def test_escalates_only_on_files_over_three_or_context_over_forty(self):
        assert Complexity(file_count=4).escalates() is True
        assert Complexity(file_count=3).escalates() is False
        assert Complexity(context_fraction=0.41).escalates() is True
        assert Complexity(context_fraction=0.40).escalates() is False
        # tool_types is no longer consulted at any value
        assert Complexity(tool_types=99).escalates() is False


# ---------------------------------------------------------------------------
# OPT-005/006/014: team-level wiring of the per-reviewer policy
# ---------------------------------------------------------------------------

class TestTeamWiringModel:
    def test_security_domain_scored_gives_security_opus(self):
        # OPT-006: security/compliance domain scores > 0.3 -> security seat opus.
        team, _ = select_team_with_scores(
            "add auth token credential validation to the api endpoint",
            complexity=Complexity(file_count=1, tool_types=1, context_fraction=0.0),
        )
        by_name = {a.name: a.model for a in team}
        assert by_name.get("security-reviewer") == "opus"

    def test_requirements_reviewer_never_opus_by_default(self):
        # OPT-005: the generalist lens is not a domain specialist, so it is
        # never one of the top-2 escalation seats and never high-stakes.
        team, _ = select_team_with_scores(
            "refactor backend modules across the service layer",
            complexity=Complexity(file_count=9, tool_types=1, context_fraction=0.0),
        )
        by_name = {a.name: a.model for a in team}
        assert by_name.get("requirements-reviewer") == "sonnet"

    def test_multi_file_escalates_only_top_two_specialists(self):
        # OPT-005: not the whole team. At most the 2 top domain lenses (+ any
        # high-stakes seat), never every reviewer.
        team, _ = select_team_with_scores(
            "refactor backend api endpoint and react component and css layout",
            complexity=Complexity(file_count=9, tool_types=1, context_fraction=0.0),
        )
        opus = [a.name for a in team if a.model == "opus"]
        assert 0 < len(opus) <= 2

    def test_hard_cap_two_opus_seats(self):
        # OPT-005: even a security artifact with a big multi-file change caps at 2.
        team, _ = select_team_with_scores(
            "auth token credential secret encryption api endpoint react component css",
            complexity=Complexity(file_count=20, tool_types=1, context_fraction=0.9),
            max_reviewers=5,
        )
        opus = [a.name for a in team if a.model == "opus"]
        assert len(opus) <= 2

    def test_high_stakes_flag_forces_security_opus_without_domain(self):
        # OPT-006: explicit override still available.
        team, _ = select_team_with_scores(
            "tweak a copy string in the marketing blurb",
            complexity=Complexity(),
            high_stakes=True,
        )
        by_name = {a.name: a.model for a in team}
        if "security-reviewer" in by_name:
            assert by_name["security-reviewer"] == "opus"

    def test_simple_change_stays_all_sonnet(self):
        # No scored security domain, no complexity escalation -> zero opus.
        team, _ = select_team_with_scores(
            "fix a typo in the readme content",
            complexity=Complexity(file_count=1, tool_types=1, context_fraction=0.0),
        )
        assert all(a.model == "sonnet" for a in team)

    def test_default_max_team_is_three(self):
        # OPT-014: a broad description caps at 3 reviewers by default.
        team, _ = select_team_with_scores(
            "auth token api endpoint database schema deploy docker react component "
            "test coverage perf latency strategy roadmap gdpr research analysis content",
            complexity=Complexity(),
        )
        assert len(team) <= 3


class TestCLIModelFlags:
    def test_json_reflects_per_reviewer_escalation(self, capsys):
        # A security artifact with a big multi-file change: some opus, but
        # capped and not the whole team.
        rc = main([
            "add security auth credential to endpoint and react component",
            "--files", "9",
            "--json",
        ])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        models = [a["model"] for a in payload["team"]]
        opus = [m for m in models if m == "opus"]
        assert 0 < len(opus) <= 2
        assert "sonnet" in models  # never the whole team

    def test_json_stays_sonnet_when_simple(self, capsys):
        rc = main([
            "tweak a copy string",
            "--files", "1",
            "--tool-types", "1",
            "--json",
        ])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert all(a["model"] == "sonnet" for a in payload["team"])

    def test_high_stakes_flag_escalates_security(self, capsys):
        rc = main([
            "add auth token to endpoint",
            "--high-stakes",
            "--json",
        ])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        by_name = {a["name"]: a["model"] for a in payload["team"]}
        if "security-reviewer" in by_name:
            assert by_name["security-reviewer"] == "opus"

    def test_default_max_is_three(self, capsys):
        rc = main([
            "auth api database deploy react test perf strategy gdpr research content",
            "--json",
        ])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert len(payload["team"]) <= 3
