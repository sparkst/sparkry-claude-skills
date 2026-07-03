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
main = scorecard.main


# ---------------------------------------------------------------------------
# Model name normalization
# ---------------------------------------------------------------------------

class TestNormalizeModel:
    def test_opus_family(self):
        assert normalize_model("claude-opus-4-8") == "opus"
        assert normalize_model("claude-opus-4-8[1m]") == "opus"

    def test_sonnet_family(self):
        assert normalize_model("claude-sonnet-5") == "sonnet"

    def test_haiku_family(self):
        assert normalize_model("claude-haiku-4-5-20251001") == "haiku"

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
