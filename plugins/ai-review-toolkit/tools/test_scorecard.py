"""Tests for scorecard.py — deterministic end-of-run report (REQ-103, REQ-104)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

scorecard = load_sibling("scorecard.py")

normalize_model = scorecard.normalize_model
load_pricing = scorecard.load_pricing
token_cost = scorecard.token_cost
aggregate_transcript = scorecard.aggregate_transcript
aggregate_workflow = scorecard.aggregate_workflow
build_scorecard = scorecard.build_scorecard
render_markdown = scorecard.render_markdown
lens_yield = scorecard.lens_yield
main = scorecard.main


# ---------------------------------------------------------------------------
# Model name normalization
# ---------------------------------------------------------------------------

class TestNormalizeModel:
    def test_opus_family(self):
        assert normalize_model("claude-opus-4-8") == "opus"

    def test_opus_1m_is_a_distinct_tier(self):
        # OPT-004: the 1M-context variant is bucketed separately (matched
        # BEFORE the plain-opus substring check) so it can be flagged as a
        # defaultModel-inheritance signal, even though it bills at the same
        # rate as plain opus (Opus 4.8 has no long-context premium).
        assert normalize_model("claude-opus-4-8[1m]") == "opus_1m"
        assert normalize_model("claude-opus-4-8[1m]") != "opus"

    def test_sonnet_family(self):
        assert normalize_model("claude-sonnet-5") == "sonnet"

    def test_haiku_family(self):
        assert normalize_model("claude-haiku-4-5-20251001") == "haiku"

    def test_fable_family(self):
        # OPT-003: fable must resolve before the sonnet/opus checks.
        assert normalize_model("claude-fable-5") == "fable"

    def test_unknown_returns_raw(self):
        assert normalize_model("some-future-model") == "some-future-model"


# ---------------------------------------------------------------------------
# Pricing + cost
# ---------------------------------------------------------------------------

class TestTokenCost:
    def test_cost_sums_all_billable_components(self):
        pricing = load_pricing()
        usage = {
            "input_tokens": 1_000_000,
            "cache_read_input_tokens": 1_000_000,
            "cache_creation_input_tokens": 1_000_000,
            "output_tokens": 1_000_000,
        }
        # sonnet: 3 + 0.30 + 3.75 + 15 = 22.05
        assert token_cost(usage, "sonnet", pricing) == pytest.approx(22.05)

    def test_opus_more_expensive_than_sonnet(self):
        pricing = load_pricing()
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        assert token_cost(usage, "opus", pricing) > token_cost(usage, "sonnet", pricing)

    def test_unknown_model_costs_zero_but_no_crash(self):
        pricing = load_pricing()
        usage = {"input_tokens": 500, "output_tokens": 500}
        assert token_cost(usage, "mystery-model", pricing) == 0.0

    def test_opus_rates_match_current_claude_opus_4_8_pricing(self):
        # OPT-004: opus was priced at Opus-4.1-era rates ($15/$75). Verified
        # current rates ($5/$25, cache 0.50/6.25) via the claude-api skill.
        pricing = load_pricing()
        usage = {
            "input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000,
            "cache_creation_input_tokens": 1_000_000, "output_tokens": 1_000_000,
        }
        assert token_cost(usage, "opus", pricing) == pytest.approx(5.0 + 0.50 + 6.25 + 25.0)

    def test_opus_1m_bills_at_the_same_rate_as_plain_opus(self):
        # Opus 4.8's 1M context window carries no long-context premium; the
        # [1m] bucket exists to flag potential defaultModel inheritance
        # (OPT-001/OPT-004), not to charge a different rate.
        pricing = load_pricing()
        usage = {
            "input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000,
            "cache_creation_input_tokens": 1_000_000, "output_tokens": 1_000_000,
        }
        assert token_cost(usage, "opus_1m", pricing) == token_cost(usage, "opus", pricing)

    def test_fable_rates_are_priced_not_zero(self):
        # OPT-003: fable agents previously fell through normalize_model's
        # substring checks and cost $0.00 across the corpus.
        pricing = load_pricing()
        usage = {
            "input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000,
            "cache_creation_input_tokens": 1_000_000, "output_tokens": 1_000_000,
        }
        assert token_cost(usage, "fable", pricing) == pytest.approx(10.0 + 1.00 + 12.50 + 50.0)

    def test_custom_pricing_override(self, tmp_path):
        p = tmp_path / "pricing.json"
        p.write_text(json.dumps({"sonnet": {"input": 99, "output": 0,
                                            "cache_read": 0, "cache_write": 0}}))
        pricing = load_pricing(str(p))
        usage = {"input_tokens": 1_000_000, "output_tokens": 0,
                 "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        assert token_cost(usage, "sonnet", pricing) == pytest.approx(99.0)


# ---------------------------------------------------------------------------
# Transcript aggregation
# ---------------------------------------------------------------------------

def _line(model, ts, dur, inp=0, out=0, cr=0, cc=0, sidechain=False):
    return {
        "timestamp": ts,
        "durationMs": dur,
        "isSidechain": sidechain,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": inp,
                "output_tokens": out,
                "cache_read_input_tokens": cr,
                "cache_creation_input_tokens": cc,
            },
        },
    }


class TestAggregateTranscript:
    def test_groups_by_model_and_sums_tokens_and_duration(self):
        lines = [
            _line("claude-opus-4-8", "2026-06-30T10:00:00Z", 1000, inp=100, out=50),
            _line("claude-sonnet-5", "2026-06-30T10:01:00Z", 2000, inp=200, out=80, sidechain=True),
            _line("claude-sonnet-5", "2026-06-30T10:02:00Z", 500, inp=10, out=5, sidechain=True),
        ]
        agg = aggregate_transcript(lines)
        assert agg["by_model"]["opus"]["input"] == 100
        assert agg["by_model"]["sonnet"]["input"] == 210
        assert agg["by_model"]["sonnet"]["duration_ms"] == 2500
        assert agg["by_model"]["sonnet"]["requests"] == 2
        assert agg["total"]["duration_ms"] == 3500

    def test_since_filters_earlier_lines(self):
        lines = [
            _line("claude-sonnet-5", "2026-06-30T09:00:00Z", 1000, inp=999),
            _line("claude-sonnet-5", "2026-06-30T11:00:00Z", 1000, inp=7),
        ]
        agg = aggregate_transcript(lines, since="2026-06-30T10:00:00Z")
        assert agg["by_model"]["sonnet"]["input"] == 7
        assert agg["by_model"]["sonnet"]["requests"] == 1

    def test_lines_without_usage_are_ignored(self):
        lines = [{"timestamp": "2026-06-30T10:00:00Z", "message": {"content": "hi"}}]
        agg = aggregate_transcript(lines)
        assert agg["total"]["requests"] == 0


# ---------------------------------------------------------------------------
# Workflow aggregation (ultracode Workflow runs) — per-agent wall-clock deltas
# rolled per model + tokens from agent-*.jsonl; wall-clock total from wf json.
# ---------------------------------------------------------------------------

def _agent_line(model, ts, inp=0, out=0, cr=0, cc=0):
    # Mirrors an agent-*.jsonl usage line: NO durationMs field (per real runs).
    return {
        "timestamp": ts,
        "message": {
            "model": model,
            "usage": {
                "input_tokens": inp,
                "output_tokens": out,
                "cache_read_input_tokens": cr,
                "cache_creation_input_tokens": cc,
            },
        },
    }


class TestAggregateWorkflow:
    def test_tokens_summed_per_model_across_agents(self):
        agents = {
            "a1": [_agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=100, out=20)],
            "a2": [_agent_line("claude-sonnet-5", "2026-07-01T01:00:00Z", inp=200, out=30)],
        }
        agg = aggregate_workflow(agents)
        assert agg["by_model"]["opus"]["input"] == 100
        assert agg["by_model"]["sonnet"]["input"] == 200
        assert agg["by_model"]["opus"]["requests"] == 1

    def test_per_agent_duration_is_last_minus_first_timestamp(self):
        agents = {
            # spans 3s (first->last line), even though lines carry no durationMs
            "a1": [
                _agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=10),
                {"timestamp": "2026-07-01T01:00:03Z", "message": {"content": "tool"}},
                _agent_line("claude-opus-4-8", "2026-07-01T01:00:03Z", out=5),
            ],
        }
        agg = aggregate_workflow(agents)
        assert agg["by_model"]["opus"]["duration_ms"] == 3000
        assert agg["by_model"]["opus"]["agents"] == 1
        assert agg["total"]["duration_ms"] == 3000
        assert agg["total"]["agents"] == 1

    def test_two_agents_same_model_sum_durations_and_agent_count(self):
        agents = {
            "a1": [_agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=1),
                   _agent_line("claude-opus-4-8", "2026-07-01T01:00:02Z", out=1)],
            "a2": [_agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=1),
                   _agent_line("claude-opus-4-8", "2026-07-01T01:00:05Z", out=1)],
        }
        agg = aggregate_workflow(agents)
        assert agg["by_model"]["opus"]["duration_ms"] == 7000
        assert agg["by_model"]["opus"]["agents"] == 2

    def test_workflow_meta_supplies_wall_clock_total(self):
        agents = {"a1": [_agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=1)]}
        meta = {"runId": "wf_x", "durationMs": 221855, "agentCount": 5,
                "status": "completed", "totalTokens": 310307,
                "workflowProgress": [
                    {"type": "workflow_phase", "index": 1, "title": "Profile",
                     "startedAt": 1782869054158, "durationMs": 178000},
                    {"type": "workflow_phase", "index": 2, "title": "Synthesize"},
                ]}
        agg = aggregate_workflow(agents, meta)
        assert agg["workflow"]["wall_clock_ms"] == 221855
        assert agg["workflow"]["agent_count"] == 5
        assert agg["workflow"]["status"] == "completed"
        # only phases with a durationMs are surfaced
        assert agg["workflow"]["phases"] == [{"title": "Profile", "duration_ms": 178000}]

    # -- OPT-001(3): model-leak detection ---------------------------------

    def test_model_leak_detected_when_agents_inherit_opus_default(self):
        agents = {
            "a1": [_agent_line("claude-opus-4-8[1m]", "2026-07-01T01:00:00Z", inp=1)],
            "a2": [_agent_line("claude-opus-4-8[1m]", "2026-07-01T01:00:00Z", inp=1)],
            "a3": [_agent_line("claude-haiku-4-5", "2026-07-01T01:00:00Z", inp=1)],
        }
        meta = {"runId": "wf_x", "defaultModel": "claude-opus-4-8[1m]"}
        agg = aggregate_workflow(agents, meta)
        leak = agg["workflow"]["model_leak"]
        assert leak["default_model"] == "claude-opus-4-8[1m]"
        assert leak["count"] == 2

    def test_no_model_leak_when_default_is_not_opus(self):
        agents = {"a1": [_agent_line("claude-sonnet-5", "2026-07-01T01:00:00Z", inp=1)]}
        meta = {"runId": "wf_x", "defaultModel": "claude-sonnet-5"}
        agg = aggregate_workflow(agents, meta)
        assert "model_leak" not in agg["workflow"]

    def test_no_model_leak_when_no_agent_matches_default(self):
        agents = {"a1": [_agent_line("claude-sonnet-5", "2026-07-01T01:00:00Z", inp=1)]}
        meta = {"runId": "wf_x", "defaultModel": "claude-opus-4-8"}
        agg = aggregate_workflow(agents, meta)
        assert "model_leak" not in agg["workflow"]

    def test_no_model_leak_when_workflow_meta_has_no_default_model(self):
        agents = {"a1": [_agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=1)]}
        meta = {"runId": "wf_x"}
        agg = aggregate_workflow(agents, meta)
        assert "model_leak" not in agg["workflow"]


class TestBuildScorecardWorkflow:
    def test_time_section_carries_workflow_wall_clock_and_agent_counts(self):
        agents = {
            "a1": [_agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=1000, out=1),
                   _agent_line("claude-opus-4-8", "2026-07-01T01:00:04Z", out=1)],
        }
        meta = {"runId": "wf_x", "durationMs": 5000, "agentCount": 1, "status": "completed"}
        agg = aggregate_workflow(agents, meta)
        report = build_scorecard({}, agg, load_pricing())
        assert report["time"]["workflow_wall_clock_ms"] == 5000
        assert report["time"]["by_model_agents"]["opus"] == 1
        assert report["time"]["by_model_ms"]["opus"] == 4000

    def test_render_shows_workflow_wall_clock_line(self):
        agents = {"a1": [_agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=1),
                         _agent_line("claude-opus-4-8", "2026-07-01T01:00:04Z", out=1)]}
        meta = {"runId": "wf_x", "durationMs": 5000, "agentCount": 1, "status": "completed"}
        report = build_scorecard({}, aggregate_workflow(agents, meta), load_pricing())
        md = render_markdown(report)
        assert "workflow total (wall-clock)" in md.lower()
        assert "opus" in md

    def test_render_shows_model_leak_banner(self):
        agents = {
            "a1": [_agent_line("claude-opus-4-8[1m]", "2026-07-01T01:00:00Z", inp=1)],
            "a2": [_agent_line("claude-opus-4-8[1m]", "2026-07-01T01:00:00Z", inp=1)],
        }
        meta = {"runId": "wf_x", "durationMs": 1000, "defaultModel": "claude-opus-4-8[1m]"}
        report = build_scorecard({}, aggregate_workflow(agents, meta), load_pricing())
        md = render_markdown(report)
        assert "MODEL LEAK" in md
        assert "2" in md
        assert "claude-opus-4-8[1m]" in md

    def test_render_omits_model_leak_banner_when_absent(self):
        agents = {"a1": [_agent_line("claude-sonnet-5", "2026-07-01T01:00:00Z", inp=1)]}
        meta = {"runId": "wf_x", "durationMs": 1000}
        report = build_scorecard({}, aggregate_workflow(agents, meta), load_pricing())
        md = render_markdown(report)
        assert "MODEL LEAK" not in md


# ---------------------------------------------------------------------------
# Scorecard assembly
# ---------------------------------------------------------------------------

def _qreview_state():
    return {
        "status": "synthesized",
        "created_at": "2026-06-30T10:00:00Z",
        "team": [
            {"name": "requirements-reviewer", "model": "sonnet", "review_lens": "reqs"},
            {"name": "security-reviewer", "model": "opus", "review_lens": "sec"},
        ],
        "test_results": {"all_passed": False, "summary": "4/5 passed",
                         "failures_as_findings": [{"severity": "P1"}]},
        "reviewer_outputs": {"0": [{"severity": "P2"}], "1": [{"severity": "P0"}]},
        "validation_dropped": {"0": 1},
        "synthesis": {
            "total": 3,
            "counts": {"P0": 1, "P1": 1, "P2": 1, "P3": 0},
            "converged": False,
            "convergence_message": "1 P0 remains",
            "dropped_count": 2,
        },
    }


class TestBuildScorecard:
    def test_issue_counts_from_synthesis(self):
        agg = aggregate_transcript([])
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        assert report["issues"]["total"] == 3
        assert report["issues"]["by_severity"]["P0"] == 1
        assert report["issues"]["dropped"] == 2

    def test_process_steps_include_team_and_tests(self):
        agg = aggregate_transcript([])
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        step_names = " ".join(s["name"].lower() for s in report["process"]["steps"])
        assert "team" in step_names
        assert "test" in step_names
        assert report["process"]["converged"] is False

    def test_tokens_and_time_carry_through(self):
        lines = [_line("claude-sonnet-5", "2026-06-30T10:05:00Z", 1234, inp=1_000_000, out=0)]
        agg = aggregate_transcript(lines)
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        assert report["tokens"]["by_model"]["sonnet"]["cost_usd"] == pytest.approx(3.0)
        assert report["time"]["total_ms"] == 1234


# ---------------------------------------------------------------------------
# OPT-003: unpriced models render loud instead of a silent $0.0000
# ---------------------------------------------------------------------------

class TestUnpricedModels:
    def test_unpriced_model_flagged_in_tokens_by_model(self):
        lines = [_line("some-future-model", "2026-06-30T10:00:00Z", 100, inp=1000, out=100)]
        agg = aggregate_transcript(lines)
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        row = report["tokens"]["by_model"]["some-future-model"]
        assert row["unpriced"] is True
        assert row["cost_usd"] == 0.0

    def test_unpriced_models_excluded_from_total_cost_and_listed(self):
        lines = [
            _line("some-future-model", "2026-06-30T10:00:00Z", 100, inp=1_000_000, out=0),
            _line("claude-sonnet-5", "2026-06-30T10:00:01Z", 100, inp=1_000_000, out=0),
        ]
        agg = aggregate_transcript(lines)
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        assert report["tokens"]["unpriced_models"] == ["some-future-model"]
        # total cost only reflects the priced (sonnet) row
        assert report["tokens"]["total"]["cost_usd"] == pytest.approx(3.0)

    def test_priced_model_not_listed_as_unpriced(self):
        lines = [_line("claude-sonnet-5", "2026-06-30T10:00:00Z", 100, inp=1000, out=100)]
        agg = aggregate_transcript(lines)
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        assert report["tokens"]["by_model"]["sonnet"]["unpriced"] is False
        assert "unpriced_models" not in report["tokens"] or not report["tokens"]["unpriced_models"]


class TestRenderMarkdown:
    def test_contains_four_sections(self):
        agg = aggregate_transcript([])
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        md = render_markdown(report)
        assert "Process" in md
        assert "Issues Found" in md
        assert "Token" in md
        assert "Model Execution Time" in md
        # honesty label about wall clock
        assert "not wall clock" in md.lower()

    def test_unpriced_row_renders_loud_not_silent_zero(self):
        lines = [
            _line("some-future-model", "2026-06-30T10:00:00Z", 100, inp=1000, out=100),
            _line("claude-sonnet-5", "2026-06-30T10:00:01Z", 100, inp=1000, out=100),
        ]
        agg = aggregate_transcript(lines)
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        md = render_markdown(report)
        assert "UNPRICED" in md
        unpriced_row = next(l for l in md.splitlines() if l.startswith("| some-future-model"))
        assert "$0.0000" not in unpriced_row
        assert "n/a (UNPRICED)" in unpriced_row

    def test_opus_1m_row_gets_a_defaultmodel_check_note(self):
        lines = [_line("claude-opus-4-8[1m]", "2026-06-30T10:00:00Z", 100, inp=1000, out=100)]
        agg = aggregate_transcript(lines)
        report = build_scorecard(_qreview_state(), agg, load_pricing())
        md = render_markdown(report)
        assert "1M-context variant" in md
        assert "defaultModel inheritance" in md


# ---------------------------------------------------------------------------
# Deploy gate surfacing (Phase F2: the §6 guardrail verdict lives in the scorecard)
# ---------------------------------------------------------------------------

class TestDeployGate:
    def test_no_deploy_section_when_state_has_no_gate(self):
        report = build_scorecard(_qreview_state(), aggregate_transcript([]), load_pricing())
        assert report.get("deploy") is None

    def test_deploy_section_surfaces_allowed_verdict(self):
        state = {**_qreview_state(), "deploy_gate": {"allowed": True, "blockers": [],
                 "checklist": {"unit_green": True}}}
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        assert report["deploy"]["allowed"] is True
        assert report["deploy"]["blockers"] == []

    def test_deploy_section_surfaces_blockers(self):
        state = {**_qreview_state(), "deploy_gate": {"allowed": False,
                 "blockers": ["unit suite is not green", "qdecide returned decline"]}}
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        assert report["deploy"]["allowed"] is False
        assert len(report["deploy"]["blockers"]) == 2

    def test_deploy_section_carries_prod_smoke_and_status(self):
        state = {**_qreview_state(), "status": "promoted",
                 "deploy_gate": {"allowed": True, "blockers": []},
                 "prod_smoke": {"ok": True, "total": 210, "passed": 210, "failed": []}}
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        assert report["deploy"]["prod_smoke"]["passed"] == 210

    def test_render_shows_deploy_gate_verdict_and_blockers(self):
        state = {**_qreview_state(), "deploy_gate": {"allowed": False,
                 "blockers": ["no rollbackCmd declared"]}}
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        md = render_markdown(report)
        assert "Deploy" in md
        assert "REFUSED" in md or "BLOCKED" in md
        assert "no rollbackCmd declared" in md

    def test_render_omits_deploy_section_without_a_gate(self):
        report = build_scorecard(_qreview_state(), aggregate_transcript([]), load_pricing())
        md = render_markdown(report)
        assert "Deploy Gate" not in md


# ---------------------------------------------------------------------------
# Blockers surfacing (SMOKE-005: an incomplete run can't read as clean)
# ---------------------------------------------------------------------------

class TestBlockers:
    def test_no_blockers_key_when_state_is_clean(self):
        report = build_scorecard(_qreview_state(), aggregate_transcript([]), load_pricing())
        assert report.get("blockers") is None

    def test_blockers_surface_from_state(self):
        state = {**_qreview_state(), "blockers": [
            "slice S-004 dropped: green gate failed",
            "artifact integration_plan escalated unresolved: 1 P1 remains",
        ]}
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        assert report["blockers"] == state["blockers"]

    def test_render_shows_blockers_and_marks_incomplete(self):
        state = {**_qreview_state(), "blockers": ["slice S-004 dropped: green gate failed"]}
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        md = render_markdown(report)
        assert "Blockers" in md
        assert "INCOMPLETE" in md
        assert "S-004" in md

    def test_render_no_blockers_section_when_clean(self):
        report = build_scorecard(_qreview_state(), aggregate_transcript([]), load_pricing())
        md = render_markdown(report)
        assert "Blockers" not in md

    def test_empty_blockers_list_is_not_surfaced(self):
        state = {**_qreview_state(), "blockers": []}
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        assert report.get("blockers") is None


# ---------------------------------------------------------------------------
# OPT-025: per-lens unique-contribution tracking (deterministic — delegates
# to finding-parser's deduplicate_findings, no LLM). Recovers lens identity
# from data already on disk: reviewer_outputs/reviewer_findings["source"]
# (each finding's "source" field is the reviewer's stable team name per
# REVIEWER_OUTPUT_INSTRUCTIONS) falling back to team[index].name when a
# finding predates that convention.
# ---------------------------------------------------------------------------

def _finding(sev, title, source=None):
    f = {"id": f"{sev}-{title[:3]}", "severity": sev, "title": title,
         "requirement": "r", "finding": "f", "recommendation": "rec"}
    if source is not None:
        f["source"] = source
    return f


class TestLensYield:
    def test_single_round_qreview_state_yields_raw_and_unique_counts(self):
        state = {
            "team": [
                {"name": "security-reviewer", "review_lens": "security"},
                {"name": "architecture-reviewer", "review_lens": "architecture"},
            ],
            "reviewer_outputs": {
                "0": [_finding("P1", "SQL injection in login", "security-reviewer")],
                "1": [
                    _finding("P2", "SQL injection in login", "architecture-reviewer"),
                    _finding("P2", "God object in UserService", "architecture-reviewer"),
                ],
            },
        }
        rows = lens_yield(state)
        by_lens = {r["lens"]: r for r in rows}
        # both reviewers raised "SQL injection..." -> merges to one finding
        # with 2 sources, so neither lens gets unique credit for it.
        assert by_lens["security-reviewer"]["raw"] == 1
        assert by_lens["security-reviewer"]["unique"] == 0
        assert by_lens["architecture-reviewer"]["raw"] == 2
        assert by_lens["architecture-reviewer"]["unique"] == 1  # only the God-object finding

    def test_falls_back_to_team_name_when_source_field_absent(self):
        # Older/simplified findings (e.g. the shared _qreview_state fixture)
        # don't carry "source" -- recover lens identity from team index.
        state = _qreview_state()
        rows = lens_yield(state)
        lenses = {r["lens"] for r in rows}
        assert lenses == {"requirements-reviewer", "security-reviewer"}

    def test_multi_round_qloop_state_tracks_yield_per_round(self):
        state = {
            "team": [{"name": "security-reviewer", "review_lens": "security"}],
            "rounds": [
                {"round_num": 1, "reviewer_findings": [
                    {"reviewer_index": 0, "findings": [_finding("P1", "issue A")]},
                ]},
                {"round_num": 2, "reviewer_findings": [
                    {"reviewer_index": 0, "findings": [_finding("P1", "issue A"),
                                                       _finding("P2", "issue B")]},
                ]},
            ],
        }
        rows = lens_yield(state)
        assert [r["round"] for r in rows] == [1, 2]
        assert rows[1]["raw"] == 2
        assert rows[1]["unique"] == 2

    def test_no_reviewer_data_returns_empty(self):
        assert lens_yield({}) == []
        assert lens_yield({"status": "initialized"}) == []


class TestRenderPerLensYield:
    def test_render_shows_per_lens_yield_table(self):
        state = {
            "team": [{"name": "security-reviewer", "review_lens": "security"}],
            "reviewer_outputs": {"0": [_finding("P1", "issue A", "security-reviewer")]},
        }
        report = build_scorecard(state, aggregate_transcript([]), load_pricing())
        md = render_markdown(report)
        assert "Per-Lens Yield" in md
        assert "security-reviewer" in md

    def test_render_omits_per_lens_section_when_no_reviewer_data(self):
        report = build_scorecard(_qreview_state() | {"reviewer_outputs": {}, "team": []},
                                  aggregate_transcript([]), load_pricing())
        md = render_markdown(report)
        assert "Per-Lens Yield" not in md


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------

class TestCLI:
    def _write_fixtures(self, tmp_path):
        state_dir = tmp_path / ".qreview"
        state_dir.mkdir()
        (state_dir / "state.json").write_text(json.dumps(_qreview_state()))
        transcript = tmp_path / "session.jsonl"
        transcript.write_text("\n".join(json.dumps(l) for l in [
            _line("claude-opus-4-8", "2026-06-30T10:00:30Z", 900, inp=1000, out=200),
            _line("claude-sonnet-5", "2026-06-30T10:03:00Z", 4100, inp=5000, out=900, sidechain=True),
        ]))
        return state_dir / "state.json", transcript

    def test_cli_json_output(self, tmp_path, capsys):
        state, transcript = self._write_fixtures(tmp_path)
        rc = main(["--state", str(state), "--transcript", str(transcript), "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["issues"]["total"] == 3
        assert "sonnet" in payload["tokens"]["by_model"]
        assert payload["time"]["total_ms"] == 5000

    def test_cli_markdown_default(self, tmp_path, capsys):
        state, transcript = self._write_fixtures(tmp_path)
        rc = main(["--state", str(state), "--transcript", str(transcript)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Issues Found" in out
        assert "Model Execution Time" in out

    def test_cli_missing_transcript_degrades_gracefully(self, tmp_path, capsys):
        state, _ = self._write_fixtures(tmp_path)
        rc = main(["--state", str(state), "--transcript", str(tmp_path / "nope.jsonl")])
        assert rc == 0
        out = capsys.readouterr().out
        assert "unavailable" in out.lower()


class TestCLIWorkflow:
    def _write_workflow_run(self, tmp_path):
        """Lay out a realistic <session>/workflows + subagents/workflows tree."""
        run_id = "wf_test123"
        session = tmp_path / "session"
        wf_dir = session / "workflows"
        agents_dir = session / "subagents" / "workflows" / run_id
        wf_dir.mkdir(parents=True)
        agents_dir.mkdir(parents=True)

        wf_json = wf_dir / f"{run_id}.json"
        wf_json.write_text(json.dumps({
            "runId": run_id, "durationMs": 6000, "agentCount": 2,
            "status": "completed", "totalTokens": 9999,
            "workflowProgress": [
                {"type": "workflow_phase", "index": 1, "title": "Profile",
                 "startedAt": 1, "durationMs": 4000},
            ],
        }))
        (agents_dir / "agent-aaa.jsonl").write_text("\n".join(json.dumps(l) for l in [
            _agent_line("claude-opus-4-8", "2026-07-01T01:00:00Z", inp=1000, out=100),
            _agent_line("claude-opus-4-8", "2026-07-01T01:00:03Z", out=50),
        ]))
        (agents_dir / "agent-bbb.jsonl").write_text("\n".join(json.dumps(l) for l in [
            _agent_line("claude-sonnet-5", "2026-07-01T01:00:00Z", inp=2000, out=200),
        ]))
        return wf_json

    def test_cli_workflow_json_output(self, tmp_path, capsys):
        wf_json = self._write_workflow_run(tmp_path)
        rc = main(["--workflow", str(wf_json), "--json"])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["tokens"]["by_model"]["opus"]["input"] == 1000
        assert payload["tokens"]["by_model"]["sonnet"]["input"] == 2000
        assert payload["time"]["workflow_wall_clock_ms"] == 6000
        assert payload["time"]["by_model_ms"]["opus"] == 3000

    def test_cli_workflow_markdown_default(self, tmp_path, capsys):
        wf_json = self._write_workflow_run(tmp_path)
        rc = main(["--workflow", str(wf_json)])
        assert rc == 0
        out = capsys.readouterr().out
        assert "Token" in out
        assert "workflow total (wall-clock)" in out.lower()
