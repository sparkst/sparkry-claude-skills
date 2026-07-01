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
