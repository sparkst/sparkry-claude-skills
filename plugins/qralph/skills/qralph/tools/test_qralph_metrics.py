#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""Tests for qralph-metrics.py — structured telemetry for QRALPH pipeline."""

from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Import from qralph-metrics.py (hyphenated filename requires importlib)
sys.path.insert(0, str(Path(__file__).parent))
_mod_path = Path(__file__).parent / "qralph-metrics.py"
_spec = importlib.util.spec_from_file_location("qralph_metrics", _mod_path)
qralph_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qralph_metrics)

ProjectMetrics = qralph_metrics.ProjectMetrics


# --- Phase timing ---


class TestPhaseTiming:
    """REQ-MET-001 — Phase start/end records timestamps and computes duration."""

    def test_phase_start_end_computes_duration(self):
        """REQ-MET-001 — phase_end computes duration_s >= elapsed time."""
        m = ProjectMetrics("proj-001")
        m.phase_start("concept")
        time.sleep(0.01)
        m.phase_end("concept")
        phase = m.to_dict()["phases"]["concept"]
        assert "start" in phase
        assert "end" in phase
        assert phase["duration_s"] >= 0.01

    def test_phase_end_without_start_raises(self):
        """REQ-MET-002 — phase_end for unknown phase raises KeyError."""
        m = ProjectMetrics("proj-001")
        with pytest.raises(KeyError):
            m.phase_end("never-started")

    def test_multiple_phases_tracked_independently(self):
        """REQ-MET-003 — multiple phases each have their own timing."""
        m = ProjectMetrics("proj-001")
        m.phase_start("concept")
        m.phase_end("concept")
        m.phase_start("execution")
        m.phase_end("execution")
        phases = m.to_dict()["phases"]
        assert "concept" in phases
        assert "execution" in phases
        assert phases["concept"]["duration_s"] >= 0
        assert phases["execution"]["duration_s"] >= 0


# --- Agent timing ---


class TestAgentTiming:
    """REQ-MET-010 — Agent start/end records model, phase, committed, and duration."""

    def test_agent_start_end_basic(self):
        """REQ-MET-010 — agent_end computes duration and records metadata."""
        m = ProjectMetrics("proj-001")
        m.agent_start("security-reviewer", model="opus-4", phase="execution")
        m.agent_end("security-reviewer", committed=True, duration_override=1.5)
        agent = m.to_dict()["agents"]["security-reviewer"]
        assert agent["model"] == "opus-4"
        assert agent["phase"] == "execution"
        assert agent["committed"] is True
        assert agent["duration_s"] == 1.5

    def test_agent_defaults(self):
        """REQ-MET-011 — agent_start defaults: model='', phase=''."""
        m = ProjectMetrics("proj-001")
        m.agent_start("reviewer")
        m.agent_end("reviewer", duration_override=0.1)
        agent = m.to_dict()["agents"]["reviewer"]
        assert agent["model"] == ""
        assert agent["phase"] == ""
        assert agent["committed"] is False

    def test_agent_end_without_start_raises(self):
        """REQ-MET-012 — agent_end for unknown agent raises KeyError."""
        m = ProjectMetrics("proj-001")
        with pytest.raises(KeyError):
            m.agent_end("ghost")

    def test_agent_duration_without_override(self):
        """REQ-MET-013 — agent_end without override uses wall-clock time."""
        m = ProjectMetrics("proj-001")
        m.agent_start("slow-agent")
        time.sleep(0.01)
        m.agent_end("slow-agent")
        agent = m.to_dict()["agents"]["slow-agent"]
        assert agent["duration_s"] >= 0.01


# --- Group timing ---


class TestGroupTiming:
    """REQ-MET-020 — Execution group start/end with task_ids and duration."""

    def test_group_start_end(self):
        """REQ-MET-020 — group records task_ids and computes duration."""
        m = ProjectMetrics("proj-001")
        m.group_start(0, ["task-a", "task-b"])
        time.sleep(0.01)
        m.group_end(0)
        group = m.to_dict()["execution_groups"][0]
        assert group["task_ids"] == ["task-a", "task-b"]
        assert group["duration_s"] >= 0.01

    def test_group_end_without_start_raises(self):
        """REQ-MET-021 — group_end for unknown index raises KeyError."""
        m = ProjectMetrics("proj-001")
        with pytest.raises(KeyError):
            m.group_end(99)

    def test_multiple_groups(self):
        """REQ-MET-022 — multiple groups tracked independently."""
        m = ProjectMetrics("proj-001")
        m.group_start(0, ["a"])
        m.group_end(0)
        m.group_start(1, ["b", "c"])
        m.group_end(1)
        groups = m.to_dict()["execution_groups"]
        assert len(groups) == 2
        assert groups[0]["task_ids"] == ["a"]
        assert groups[1]["task_ids"] == ["b", "c"]


# --- Quality round ---


class TestQualityRound:
    """REQ-MET-030 — Quality loop round metrics."""

    def test_quality_round_recorded(self):
        """REQ-MET-030 — quality_round stores p0/p1/p2/converged for each round."""
        m = ProjectMetrics("proj-001")
        m.quality_round(1, p0=2, p1=5, p2=10, converged=False)
        m.quality_round(2, p0=1, p1=3, p2=8, converged=True)
        ql = m.to_dict()["quality_loop"]
        assert len(ql) == 2
        assert ql[0]["round"] == 1
        assert ql[0]["p0"] == 2
        assert ql[0]["p1"] == 5
        assert ql[0]["p2"] == 10
        assert ql[0]["converged"] is False
        assert ql[1]["round"] == 2
        assert ql[1]["converged"] is True


# --- Record arbitrary keys ---


class TestRecord:
    """REQ-MET-040 — record() stores arbitrary key-value pairs."""

    def test_record_stores_values(self):
        """REQ-MET-040 — record() values appear in to_dict() output."""
        m = ProjectMetrics("proj-001")
        m.record("estimated_sp", 8)
        m.record("budget_usd", 0.42)
        m.record("template", "standard-fullstack")
        d = m.to_dict()
        assert d["estimated_sp"] == 8
        assert d["budget_usd"] == 0.42
        assert d["template"] == "standard-fullstack"

    def test_record_overwrites(self):
        """REQ-MET-041 — record() with same key overwrites previous value."""
        m = ProjectMetrics("proj-001")
        m.record("status", "running")
        m.record("status", "complete")
        assert m.to_dict()["status"] == "complete"


# --- Bottleneck detection ---


class TestBottleneckDetection:
    """REQ-MET-050 — detect_bottlenecks finds slow agents in execution groups."""

    def test_bottleneck_detected(self):
        """REQ-MET-050 — agent 6x average is flagged as bottleneck."""
        m = ProjectMetrics("proj-001")
        m.group_start(0, ["fast-a", "fast-b", "slow-c"])
        # fast agents: 1s each, slow agent: 6s
        m.agent_start("fast-a")
        m.agent_end("fast-a", duration_override=1.0)
        m.agent_start("fast-b")
        m.agent_end("fast-b", duration_override=1.0)
        m.agent_start("slow-c")
        m.agent_end("slow-c", duration_override=6.0)
        m.group_end(0)

        bottlenecks = m.detect_bottlenecks(threshold=2.0)
        assert len(bottlenecks) == 1
        assert bottlenecks[0]["agent"] == "slow-c"
        assert bottlenecks[0]["duration_s"] == 6.0
        # Average is (1+1+6)/3 = 2.667, ratio = 6/2.667 ≈ 2.25
        assert bottlenecks[0]["ratio"] > 2.0
        assert bottlenecks[0]["group_index"] == 0

    def test_no_bottleneck_when_similar(self):
        """REQ-MET-051 — all agents similar duration returns empty list."""
        m = ProjectMetrics("proj-001")
        m.group_start(0, ["a", "b", "c"])
        m.agent_start("a")
        m.agent_end("a", duration_override=1.0)
        m.agent_start("b")
        m.agent_end("b", duration_override=1.1)
        m.agent_start("c")
        m.agent_end("c", duration_override=0.9)
        m.group_end(0)

        bottlenecks = m.detect_bottlenecks(threshold=2.0)
        assert bottlenecks == []

    def test_single_task_group_ignored(self):
        """REQ-MET-052 — single-task groups are skipped (no comparison possible)."""
        m = ProjectMetrics("proj-001")
        m.group_start(0, ["only-one"])
        m.agent_start("only-one")
        m.agent_end("only-one", duration_override=100.0)
        m.group_end(0)

        bottlenecks = m.detect_bottlenecks(threshold=2.0)
        assert bottlenecks == []

    def test_bottleneck_custom_threshold(self):
        """REQ-MET-053 — custom threshold changes detection sensitivity."""
        m = ProjectMetrics("proj-001")
        m.group_start(0, ["x", "y"])
        m.agent_start("x")
        m.agent_end("x", duration_override=1.0)
        m.agent_start("y")
        m.agent_end("y", duration_override=2.0)
        m.group_end(0)

        # avg = 1.5, y ratio = 2/1.5 = 1.33
        assert m.detect_bottlenecks(threshold=1.2) != []
        assert m.detect_bottlenecks(threshold=1.5) == []


# --- write() ---


class TestWrite:
    """REQ-MET-060 — write() creates valid metrics.json."""

    def test_write_creates_json_file(self):
        """REQ-MET-060 — write() produces parseable JSON at project_path/metrics.json."""
        m = ProjectMetrics("proj-001")
        m.phase_start("concept")
        m.phase_end("concept")
        m.record("estimated_sp", 5)

        with tempfile.TemporaryDirectory() as tmpdir:
            m.write(Path(tmpdir))
            metrics_path = Path(tmpdir) / "metrics.json"
            assert metrics_path.exists()
            data = json.loads(metrics_path.read_text())
            assert data["project_id"] == "proj-001"
            assert "summary" in data
            assert data["estimated_sp"] == 5


# --- to_dict() summary ---


class TestToDict:
    """REQ-MET-070 — to_dict() includes complete summary."""

    def test_to_dict_summary_counts(self):
        """REQ-MET-070 — summary includes phase_count, agent_count, group_count, quality_rounds."""
        m = ProjectMetrics("proj-001")
        m.phase_start("concept")
        m.phase_end("concept")
        m.phase_start("execution")
        m.phase_end("execution")
        m.agent_start("a")
        m.agent_end("a", duration_override=1.0)
        m.agent_start("b")
        m.agent_end("b", duration_override=2.0)
        m.group_start(0, ["a", "b"])
        m.group_end(0)
        m.quality_round(1, p0=0, p1=1, p2=2, converged=True)

        d = m.to_dict()
        s = d["summary"]
        assert s["phase_count"] == 2
        assert s["agent_count"] == 2
        assert s["group_count"] == 1
        assert s["quality_rounds"] == 1

    def test_to_dict_has_project_id_and_timestamps(self):
        """REQ-MET-071 — to_dict includes project_id, created_at, completed_at."""
        m = ProjectMetrics("proj-001")
        d = m.to_dict()
        assert d["project_id"] == "proj-001"
        assert "created_at" in d
        assert "completed_at" in d

    def test_to_dict_total_phase_duration(self):
        """REQ-MET-072 — summary.total_phase_duration_s sums all phase durations."""
        m = ProjectMetrics("proj-001")
        m.phase_start("a")
        m.phase_end("a")
        m.phase_start("b")
        m.phase_end("b")
        d = m.to_dict()
        total = d["summary"]["total_phase_duration_s"]
        phase_sum = sum(p["duration_s"] for p in d["phases"].values())
        assert total == pytest.approx(phase_sum)

    def test_to_dict_bottlenecks_in_summary(self):
        """REQ-MET-073 — summary.bottlenecks reflects detect_bottlenecks()."""
        m = ProjectMetrics("proj-001")
        m.group_start(0, ["fast-1", "fast-2", "slow"])
        m.agent_start("fast-1")
        m.agent_end("fast-1", duration_override=1.0)
        m.agent_start("fast-2")
        m.agent_end("fast-2", duration_override=1.0)
        m.agent_start("slow")
        m.agent_end("slow", duration_override=10.0)
        m.group_end(0)
        d = m.to_dict()
        # avg = 4.0, slow ratio = 10/4 = 2.5 > 2.0
        assert len(d["summary"]["bottlenecks"]) == 1

    def test_to_dict_json_serializable(self):
        """REQ-MET-074 — to_dict() output is fully JSON-serializable."""
        m = ProjectMetrics("proj-001")
        m.phase_start("x")
        m.phase_end("x")
        m.agent_start("y")
        m.agent_end("y", duration_override=0.5)
        m.quality_round(1, 0, 0, 0, True)
        m.record("foo", {"nested": [1, 2, 3]})
        # Should not raise
        result = json.dumps(m.to_dict())
        assert isinstance(result, str)


# --- Round-trip timing ---


class TestRoundTrip:
    """REQ-MET-020 — Metrics survive save/reload and timing still works."""

    def test_round_trip_preserves_timing(self, tmp_path):
        """REQ-MET-020: Metrics can be saved, reloaded, and phase_end still works."""
        from datetime import datetime

        m = ProjectMetrics("test")
        m.phase_start("EXECUTE")
        m.write(tmp_path)
        # Reload
        data = json.loads((tmp_path / "metrics.json").read_text())
        m2 = ProjectMetrics("test")
        m2._phases = data.get("phases", {})
        # Reconstruct _start_ts
        for name, phase in m2._phases.items():
            if "start" in phase:
                phase["_start_ts"] = datetime.fromisoformat(phase["start"]).timestamp()
        # Now phase_end should work
        m2.phase_end("EXECUTE")
        assert m2._phases["EXECUTE"]["duration_s"] >= 0
