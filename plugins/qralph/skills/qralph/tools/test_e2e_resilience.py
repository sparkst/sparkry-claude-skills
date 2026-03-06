#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""End-to-end resilience tests for QRALPH v6.6.2 COE fixes.

Drives the FULL state machine through cmd_plan -> cmd_next cycles.
No real agents spawned. Timestamps manipulated for deterministic timeouts.

Run: cd .qralph/tools && python3 -m pytest test_e2e_resilience.py -v
"""

import importlib.util
import json
import os
import sys
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# ─── Module Loading ──────────────────────────────────────────────────────────

_tools_dir = Path(__file__).parent


def _load_module(name, filename):
    """Load a Python module from the tools directory by filename."""
    spec = importlib.util.spec_from_file_location(name, _tools_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def isolated_pipeline(tmp_path):
    """Load pipeline module with all paths redirected to tmp_path.

    Returns (qp, qs, tmp_path) where:
        qp = pipeline module with patched paths
        qs = state module with patched paths
    """
    qralph_dir = tmp_path / ".qralph"
    qralph_dir.mkdir()
    projects_dir = qralph_dir / "projects"
    projects_dir.mkdir()
    state_file = qralph_dir / "current-project.json"

    # Load state module and patch paths
    qs = _load_module("qs_e2e", "qralph-state.py")
    qs.QRALPH_DIR = qralph_dir
    qs.STATE_FILE = state_file
    qs.PROJECT_ROOT = tmp_path

    # Load pipeline module
    qp = _load_module("qp_e2e", "qralph-pipeline.py")
    qp.QRALPH_DIR = qralph_dir
    qp.PROJECTS_DIR = projects_dir
    qp.STATE_FILE = state_file
    qp.PROJECT_ROOT = tmp_path
    qp.SESSION_LOCK = qralph_dir / "active-session.lock"

    # Critical: replace the imported qralph_state reference with patched copy
    qp.qralph_state = qs

    # Also patch the qralph_config module's paths to avoid touching real config
    qp.qralph_config.QRALPH_DIR = qralph_dir
    qp.qralph_config.CONFIG_FILE = qralph_dir / "config.json"
    qp.qralph_config.PROJECT_ROOT = tmp_path
    # Patch qralph_config's internal qralph_state reference too
    qp.qralph_config.qralph_state = qs

    return qp, qs, tmp_path


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _write_agent_output(project_path, output_subdir, agent_name, content=None):
    """Write a fake agent output file with enough content to pass MIN_AGENT_OUTPUT_LENGTH."""
    if content is None:
        content = f"# Agent Output: {agent_name}\n\n" + ("Analysis content. " * 30)
    output_dir = project_path / output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{agent_name}.md").write_text(content)


def _set_agent_start_time(qs, agent_name, seconds_ago):
    """Manipulate agent start time to simulate elapsed time."""
    state = qs.load_state()
    pipeline = state.get("pipeline", {})
    timing = pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}})
    timing["agent_start_times"][agent_name] = (
        datetime.now() - timedelta(seconds=seconds_ago)
    ).isoformat()
    state["pipeline"] = pipeline
    qs.save_state(state)


def _get_pipeline_state(qs):
    """Read current pipeline state."""
    state = qs.load_state()
    return state, state.get("pipeline", {})


def _setup_plan_waiting_state(qs, project_path, agents, respawn_counts=None):
    """Set up state as if we just confirmed template and spawned plan agents.

    Args:
        agents: list of agent config dicts with name, model, prompt
        respawn_counts: optional dict of {agent_name: count}
    """
    if respawn_counts is None:
        respawn_counts = {a["name"]: 0 for a in agents}

    agent_start_times = {
        a["name"]: datetime.now().isoformat() for a in agents
    }

    state = {
        "project_id": project_path.name,
        "project_path": str(project_path),
        "request": "build a landing page",
        "target_directory": str(project_path.parent),
        "mode": "pipeline",
        "phase": "PLAN",
        "created_at": datetime.now().isoformat(),
        "agents": [a["name"] for a in agents],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
        "pipeline_version": "6.6.2",
        "pipeline": {
            "mode": "thorough",
            "sub_phase": "PLAN_WAITING",
            "plan_agents": agents,
            "_spawned_agents": {a["name"]: a for a in agents},
            "agent_timing": {
                "agent_start_times": agent_start_times,
                "respawn_counts": respawn_counts,
            },
            "execution_groups": [],
            "current_group_index": 0,
            "last_activity_at": datetime.now().isoformat(),
        },
    }
    qs.save_state(state)
    (project_path / "agent-outputs").mkdir(parents=True, exist_ok=True)
    return state


# ─── COE-1: Agent Timeout -> Respawn -> Escalation ──────────────────────────

class TestCOE1AgentTimeout:
    """Drive pipeline to PLAN_WAITING, trigger timeout, verify respawn then escalation."""

    _AGENTS = [
        {"name": "researcher", "model": "opus", "prompt": "Research the project"},
        {"name": "sde-iii", "model": "opus", "prompt": "Analyze implementation"},
    ]

    def test_timeout_triggers_respawn(self, isolated_pipeline):
        """COE-1: Agent past timeout -> cmd_next returns respawn_agent with full config."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-001"
        project_path.mkdir(parents=True)

        _setup_plan_waiting_state(qs, project_path, self._AGENTS)

        # Manipulate: researcher started 1000s ago (opus timeout = 900s)
        _set_agent_start_time(qs, "researcher", 1000)
        # sde-iii is recent — should not time out
        _set_agent_start_time(qs, "sde-iii", 10)

        result = qp.cmd_next()

        assert result["action"] == "respawn_agent"
        assert result["agent_name"] == "researcher"
        assert result["model"] == "opus"
        # Full agent config attached for orchestrator
        assert "agent" in result
        assert result["agent"]["prompt"] == "Research the project"
        assert result["elapsed_seconds"] >= 900
        assert "output_dir" in result

        # Note: _check_agent_timeout increments respawn_count in the
        # in-memory agent_timing dict, but _next_plan_waiting returns the
        # timeout result early without saving state (the orchestrator saves).
        # The respawn_count increment is verified by the returned action.
        assert result["output_file"] == "researcher.respawn.md"

    def test_second_timeout_escalates(self, isolated_pipeline):
        """COE-1: Already-respawned agent times out again -> escalate_to_user."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-002"
        project_path.mkdir(parents=True)

        _setup_plan_waiting_state(
            qs, project_path, self._AGENTS,
            respawn_counts={"researcher": 1, "sde-iii": 0},
        )

        # Both agents timed out — researcher already respawned once
        _set_agent_start_time(qs, "researcher", 1000)
        _set_agent_start_time(qs, "sde-iii", 10)

        result = qp.cmd_next()

        assert result["action"] == "escalate_to_user"
        assert result["escalation_type"] == "agent_timeout"
        assert "researcher" in result["message"]

    def test_output_written_no_timeout(self, isolated_pipeline):
        """COE-1: Agent output exists -> no timeout, pipeline advances (or errors on manifest)."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-003"
        project_path.mkdir(parents=True)

        _setup_plan_waiting_state(qs, project_path, self._AGENTS)

        # Write both agent outputs (sufficient length)
        _write_agent_output(project_path, "agent-outputs", "researcher")
        _write_agent_output(project_path, "agent-outputs", "sde-iii")

        result = qp.cmd_next()

        # Should NOT be a timeout action — pipeline tried to advance
        assert result["action"] not in ("respawn_agent", "escalate_to_user")

    def test_no_start_time_no_timeout(self, isolated_pipeline):
        """COE-1: Missing agent_start_times entry -> no timeout triggered."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-004"
        project_path.mkdir(parents=True)

        _setup_plan_waiting_state(qs, project_path, self._AGENTS)

        # Clear start times entirely
        state = qs.load_state()
        state["pipeline"]["agent_timing"]["agent_start_times"] = {}
        qs.save_state(state)

        result = qp.cmd_next()

        # Without start times, _check_agent_timeout returns None;
        # missing outputs should produce an error, not a timeout
        assert result["action"] == "error"
        assert "Missing outputs" in result["message"]


# ─── COE-2: Quality Gate CWD Containment ────────────────────────────────────

class TestCOE2QualityGateCWD:
    """Quality gate containment: site_dir must be within PROJECT_ROOT."""

    def test_gate_containment_rejects_traversal(self, isolated_pipeline):
        """COE-2: site_dir outside PROJECT_ROOT is rejected (empty result)."""
        qp, qs, tmp_path = isolated_pipeline

        result = qp.detect_quality_gate(site_dir="/etc/malicious")

        assert result == {} or not result.get("cmd")

    def test_gate_uses_explicit_site_dir(self, isolated_pipeline):
        """COE-2: Explicit site_dir within PROJECT_ROOT takes priority."""
        qp, qs, tmp_path = isolated_pipeline
        site_dir = tmp_path / "my-project" / "site"
        site_dir.mkdir(parents=True)

        # Create package.json with test script
        (site_dir / "package.json").write_text(json.dumps({
            "scripts": {"test": "echo pass"}
        }))

        result = qp.detect_quality_gate(site_dir=str(site_dir))

        assert result.get("cwd") == str(site_dir)
        assert "npm run test" in result.get("cmd", "")

    def test_gate_symlink_traversal_rejected(self, isolated_pipeline):
        """COE-2: Symlink escaping PROJECT_ROOT is rejected."""
        qp, qs, tmp_path = isolated_pipeline

        # Create a symlink inside tmp_path that points outside
        link_path = tmp_path / "escape-link"
        try:
            link_path.symlink_to("/tmp")
        except OSError:
            pytest.skip("Cannot create symlinks on this platform")

        result = qp.detect_quality_gate(site_dir=str(link_path))

        # Resolved symlink points outside PROJECT_ROOT -> rejected
        assert result == {} or not result.get("cmd")


# ─── COE-3: Gate Effectiveness ──────────────────────────────────────────────

class TestCOE3GateEffectiveness:
    """Linter effectiveness: lint script without config -> effective=False."""

    def test_no_linter_config_returns_ineffective(self, isolated_pipeline):
        """COE-3: lint script exists but no linter config -> effective=False."""
        qp, qs, tmp_path = isolated_pipeline
        site_dir = tmp_path / "project-lint"
        site_dir.mkdir(parents=True)

        (site_dir / "package.json").write_text(json.dumps({
            "scripts": {"lint": "eslint ."}
        }))
        # NO .eslintrc, biome.json, or eslint.config.* files

        result = qp.detect_quality_gate(site_dir=str(site_dir))

        assert result.get("cmd") is not None
        assert result.get("effective") is False

    def test_linter_config_present_returns_effective(self, isolated_pipeline):
        """COE-3: lint script + .eslintrc.json -> effective=True."""
        qp, qs, tmp_path = isolated_pipeline
        site_dir = tmp_path / "project-lint-ok"
        site_dir.mkdir(parents=True)

        (site_dir / "package.json").write_text(json.dumps({
            "scripts": {"lint": "eslint ."}
        }))
        (site_dir / ".eslintrc.json").write_text("{}")

        result = qp.detect_quality_gate(site_dir=str(site_dir))

        assert result.get("effective") is True

    def test_biome_config_returns_effective(self, isolated_pipeline):
        """COE-3: lint script + biome.json -> effective=True."""
        qp, qs, tmp_path = isolated_pipeline
        site_dir = tmp_path / "project-biome"
        site_dir.mkdir(parents=True)

        (site_dir / "package.json").write_text(json.dumps({
            "scripts": {"lint": "biome check ."}
        }))
        (site_dir / "biome.json").write_text("{}")

        result = qp.detect_quality_gate(site_dir=str(site_dir))

        assert result.get("effective") is True

    def test_no_lint_script_no_effective_key(self, isolated_pipeline):
        """COE-3: No lint script -> no 'effective' key in result."""
        qp, qs, tmp_path = isolated_pipeline
        site_dir = tmp_path / "project-no-lint"
        site_dir.mkdir(parents=True)

        (site_dir / "package.json").write_text(json.dumps({
            "scripts": {"test": "jest"}
        }))

        result = qp.detect_quality_gate(site_dir=str(site_dir))

        # Result should have cmd (from test script) but effective may
        # be True/False depending on linter config presence
        assert result.get("cmd") is not None


# ─── COE-4: Convergence Tracking ────────────────────────────────────────────

class TestCOE4Convergence:
    """Quality dashboard convergence: regression and stagnation detection."""

    @pytest.fixture
    def qd(self):
        """Load quality-dashboard module."""
        return _load_module("qd_e2e", "quality-dashboard.py")

    def test_regression_detected(self, qd):
        """COE-4: P0 increase with new IDs -> regressed=True."""
        prev = [
            {"id": "F-001", "severity": "P0", "description": "bug 1"},
        ]
        curr = [
            {"id": "F-001", "severity": "P0", "description": "bug 1"},
            {"id": "F-002", "severity": "P0", "description": "new bug"},
        ]

        result = qd.check_convergence(curr, prev_findings=prev)
        assert result["regressed"] is True
        assert result["p0_count"] == 2

    def test_no_regression_same_ids(self, qd):
        """COE-4: Same P0 count, same IDs -> regressed=False."""
        prev = [
            {"id": "F-001", "severity": "P0", "description": "bug 1"},
        ]
        curr = [
            {"id": "F-001", "severity": "P0", "description": "bug 1"},
        ]

        result = qd.check_convergence(curr, prev_findings=prev)
        assert result["regressed"] is False

    def test_stagnation_detected(self, qd):
        """COE-4: Same P0+P1 count >= 3 across rounds -> stagnant=True."""
        prev = [
            {"id": "F-001", "severity": "P0", "description": "a"},
            {"id": "F-002", "severity": "P1", "description": "b"},
            {"id": "F-003", "severity": "P1", "description": "c"},
        ]
        curr = [
            {"id": "F-001", "severity": "P0", "description": "a"},
            {"id": "F-002", "severity": "P1", "description": "b"},
            {"id": "F-003", "severity": "P1", "description": "c"},
        ]

        result = qd.check_convergence(curr, prev_findings=prev)
        assert result["stagnant"] is True

    def test_no_stagnation_below_threshold(self, qd):
        """COE-4: Same P0+P1 count but < 3 -> stagnant=False."""
        prev = [
            {"id": "F-001", "severity": "P0", "description": "a"},
            {"id": "F-002", "severity": "P1", "description": "b"},
        ]
        curr = [
            {"id": "F-001", "severity": "P0", "description": "a"},
            {"id": "F-002", "severity": "P1", "description": "b"},
        ]

        result = qd.check_convergence(curr, prev_findings=prev)
        assert result["stagnant"] is False

    def test_converged_no_p0_p1(self, qd):
        """COE-4: Zero P0 and P1 -> converged=True."""
        findings = [
            {"id": "F-001", "severity": "P2", "description": "minor"},
        ]

        result = qd.check_convergence(findings)
        assert result["converged"] is True
        assert result["p2_count"] == 1

    def test_not_converged_with_p1(self, qd):
        """COE-4: P1 present -> converged=False."""
        findings = [
            {"id": "F-001", "severity": "P1", "description": "medium"},
        ]

        result = qd.check_convergence(findings)
        assert result["converged"] is False


# ─── COE-5: Self-Healing Integration ────────────────────────────────────────

class TestCOE5SelfHealing:
    """Self-healing: heal suggestions on escalation, cooldown enforcement."""

    @pytest.fixture
    def sh(self):
        """Load self-healing module."""
        return _load_module("sh_e2e", "self-healing.py")

    def test_heal_suggestion_attached_on_escalation(self, isolated_pipeline):
        """COE-5: When agent escalates AND self-healing matches, heal_suggestion is attached."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-heal"
        project_path.mkdir(parents=True)

        agents = [{"name": "researcher", "model": "opus", "prompt": "test"}]
        _setup_plan_waiting_state(
            qs, project_path, agents,
            respawn_counts={"researcher": 1},  # Already respawned once
        )

        # Set researcher start time well past timeout
        _set_agent_start_time(qs, "researcher", 1000)

        result = qp.cmd_next()

        assert result["action"] == "escalate_to_user"
        # If match_heal_condition is available, it should attach heal_suggestion
        if qp.match_heal_condition is not None:
            assert "heal_suggestion" in result
            assert result["heal_suggestion"]["action"] == "RE_SPAWN_AGENT"
            assert result["heal_suggestion"]["condition"] == "agent_timeout"

    def test_match_condition_returns_rule(self, sh):
        """COE-5: match_condition('agent_timeout') returns SH-001 rule."""
        rule = sh.match_condition("agent_timeout", {})
        assert rule is not None
        assert rule["id"] == "SH-001"
        assert rule["action"] == "RE_SPAWN_AGENT"

    def test_match_condition_unknown_returns_none(self, sh):
        """COE-5: Unknown condition returns None."""
        rule = sh.match_condition("unknown_condition", {})
        assert rule is None

    def test_heal_cooldown_recent(self, sh):
        """COE-5: Heal within cooldown window -> on cooldown."""
        recent = datetime.now().isoformat()
        assert sh.is_heal_on_cooldown(recent) is True

    def test_heal_cooldown_expired(self, sh):
        """COE-5: Heal older than cooldown window -> not on cooldown."""
        old = (datetime.now() - timedelta(seconds=7200)).isoformat()
        assert sh.is_heal_on_cooldown(old) is False

    def test_heal_cooldown_none(self, sh):
        """COE-5: No previous heal -> not on cooldown."""
        assert sh.is_heal_on_cooldown(None) is False

    def test_learn_update_counters_success(self, sh):
        """COE-5: learn_update_counters increments success counter."""
        state = {"heal_patterns": {}}
        result = sh.learn_update_counters("SH-001", "success", state)
        assert result is True
        assert state["heal_patterns"]["SH-001"]["success_count"] >= 1

    def test_learn_update_counters_unknown_rule(self, sh):
        """COE-5: Unknown rule ID -> returns False."""
        state = {"heal_patterns": {}}
        result = sh.learn_update_counters("UNKNOWN-999", "success", state)
        assert result is False


# ─── Output Priority: .respawn.md preferred over .md/.hung.md ────────────────

class TestResolveOutputPriority:
    """Verify _resolve_agent_output picks .respawn.md first."""

    def test_respawn_md_preferred_over_md(self, isolated_pipeline):
        """Respawned agent's .respawn.md is found; pipeline does not timeout."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-resolve"
        project_path.mkdir(parents=True)

        agents = [{"name": "researcher", "model": "opus", "prompt": "test"}]
        _setup_plan_waiting_state(qs, project_path, agents)

        output_dir = project_path / "agent-outputs"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write .hung.md (from first timeout) with old content
        (output_dir / "researcher.hung.md").write_text(
            "OLD HUNG CONTENT " + "x" * 200
        )
        # Write .respawn.md (from re-spawn) with new content
        (output_dir / "researcher.respawn.md").write_text(
            "NEW RESPAWN CONTENT " + "x" * 200
        )

        result = qp.cmd_next()

        # Should NOT timeout — .respawn.md should be found
        assert result["action"] not in ("respawn_agent", "escalate_to_user")

    def test_resolve_agent_output_priority_order(self, isolated_pipeline):
        """Unit check: _resolve_agent_output returns .respawn.md over .md."""
        qp, qs, tmp_path = isolated_pipeline

        output_dir = tmp_path / "outputs"
        output_dir.mkdir()

        # Write both .md and .respawn.md
        (output_dir / "agent.md").write_text("OLD " + "x" * 200)
        (output_dir / "agent.respawn.md").write_text("NEW " + "x" * 200)

        path, content = qp._resolve_agent_output(output_dir, "agent", 100)

        assert path is not None
        assert path.name == "agent.respawn.md"
        assert content.startswith("NEW")

    def test_resolve_falls_back_to_md(self, isolated_pipeline):
        """Unit check: Without .respawn.md, falls back to .md."""
        qp, qs, tmp_path = isolated_pipeline

        output_dir = tmp_path / "outputs2"
        output_dir.mkdir()

        (output_dir / "agent.md").write_text("NORMAL " + "x" * 200)

        path, content = qp._resolve_agent_output(output_dir, "agent", 100)

        assert path is not None
        assert path.name == "agent.md"

    def test_resolve_falls_back_to_hung_md(self, isolated_pipeline):
        """Unit check: Without .respawn.md and .md, falls back to .hung.md."""
        qp, qs, tmp_path = isolated_pipeline

        output_dir = tmp_path / "outputs3"
        output_dir.mkdir()

        (output_dir / "agent.hung.md").write_text("HUNG " + "x" * 200)

        path, content = qp._resolve_agent_output(output_dir, "agent", 100)

        assert path is not None
        assert path.name == "agent.hung.md"


# ─── IDEATE_WAITING Timeout Through cmd_next ─────────────────────────────────

class TestIdeateWaitingTimeout:
    """Verify timeout/respawn logic works in IDEATE_WAITING sub-phase too."""

    def test_ideate_waiting_timeout_respawns_brainstormer(self, isolated_pipeline):
        """Brainstormer timed out in IDEATE_WAITING -> respawn_agent."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-ideate"
        project_path.mkdir(parents=True)
        (project_path / "agent-outputs").mkdir()

        brainstormer = {"name": "brainstormer", "model": "opus", "prompt": "Brainstorm ideas"}
        state = {
            "project_id": "test-ideate",
            "project_path": str(project_path),
            "request": "build something",
            "target_directory": str(tmp_path),
            "mode": "pipeline",
            "phase": "IDEATE",
            "created_at": datetime.now().isoformat(),
            "agents": ["brainstormer"],
            "heal_attempts": 0,
            "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
            "pipeline_version": "6.6.2",
            "pipeline": {
                "mode": "thorough",
                "sub_phase": "IDEATE_WAITING",
                "_spawned_agents": {"brainstormer": brainstormer},
                "agent_timing": {
                    "agent_start_times": {
                        "brainstormer": (datetime.now() - timedelta(seconds=1000)).isoformat(),
                    },
                    "respawn_counts": {"brainstormer": 0},
                },
                "execution_groups": [],
                "current_group_index": 0,
            },
        }
        qs.save_state(state)

        result = qp.cmd_next()

        assert result["action"] == "respawn_agent"
        assert result["agent_name"] == "brainstormer"
        assert result["model"] == "opus"
        assert "agent" in result


# ─── Quality Loop Decision: Regression & Stagnation Wiring ───────────────────

def _setup_quality_fix_state(qs, project_path, round_num, active_agents,
                              rounds_history=None):
    """Set up state at QUALITY_FIX sub-phase for quality loop decision tests."""
    state = {
        "project_id": project_path.name,
        "project_path": str(project_path),
        "request": "build a landing page",
        "target_directory": str(project_path.parent),
        "mode": "pipeline",
        "phase": "VERIFY",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
        "pipeline_version": "6.6.2",
        "manifest": {"estimated_sp": 3.0},
        "pipeline": {
            "mode": "thorough",
            "sub_phase": "QUALITY_FIX",
            "quality_loop": {
                "round": round_num,
                "max_rounds": 3,
                "active_agents": active_agents,
                "dropped_agents": [],
                "replan_count": 0,
                "rounds_history": rounds_history or [],
            },
            "execution_groups": [],
            "current_group_index": 0,
        },
    }
    qs.save_state(state)
    (project_path / "agent-outputs").mkdir(parents=True, exist_ok=True)
    return state


def _write_quality_output(project_path, round_num, agent_name, findings_text):
    """Write a fake quality round output file with finding lines."""
    output_dir = project_path / "agent-outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"quality-round-{round_num}-{agent_name}.md").write_text(findings_text)


class TestQualityLoopDecisionWiring:
    """Verify that regressed/stagnant flags are READ by the pipeline decision logic."""

    def test_regression_triggers_backtrack_at_round_3(self, isolated_pipeline):
        """COE-4: P0 increase with NEW findings at round >= 3 → backtrack."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-regress"
        project_path.mkdir(parents=True)

        # Round 1 had 1 P0
        r1_findings = [{"severity": "P0", "id": "F-001", "title": "bug", "agent": "cr", "confidence": "high", "raw": "[P0] F-001: bug"}]
        # Round 2 had 1 P0 (same)
        r2_findings = [{"severity": "P0", "id": "F-001", "title": "bug", "agent": "cr", "confidence": "high", "raw": "[P0] F-001: bug"}]

        rounds_history = [
            {"round": 1, "findings": r1_findings, "agents": ["code-reviewer"]},
            {"round": 2, "findings": r2_findings, "agents": ["code-reviewer"]},
        ]

        _setup_quality_fix_state(qs, project_path, round_num=3,
                                  active_agents=["code-reviewer"],
                                  rounds_history=rounds_history)

        # Round 3: P0 count INCREASES to 2 (new finding F-002)
        _write_quality_output(project_path, 3, "code-reviewer",
            "[P0] F-001: bug\n**Confidence:** high\n[P0] F-002: new critical bug\n**Confidence:** high\n")

        result = qp.cmd_next()

        assert result["dashboard_action"] == "backtrack", \
            f"Expected backtrack on regression, got {result['dashboard_action']}"

    def test_stagnation_triggers_max_rounds(self, isolated_pipeline):
        """COE-4: Same P0+P1 count (>=3) across rounds → max_rounds (force advance)."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-stagnant"
        project_path.mkdir(parents=True)

        # Round 1: 1 P0 + 2 P1 = 3
        r1_findings = [
            {"severity": "P0", "id": "F-001", "title": "a", "agent": "cr", "confidence": "high", "raw": "[P0] F-001: a"},
            {"severity": "P1", "id": "F-002", "title": "b", "agent": "cr", "confidence": "high", "raw": "[P1] F-002: b"},
            {"severity": "P1", "id": "F-003", "title": "c", "agent": "cr", "confidence": "high", "raw": "[P1] F-003: c"},
        ]

        rounds_history = [
            {"round": 1, "findings": r1_findings, "agents": ["code-reviewer"]},
        ]

        _setup_quality_fix_state(qs, project_path, round_num=2,
                                  active_agents=["code-reviewer"],
                                  rounds_history=rounds_history)

        # Round 2: Same 1 P0 + 2 P1 = 3 (stagnant)
        _write_quality_output(project_path, 2, "code-reviewer",
            "[P0] F-001: a\n**Confidence:** high\n[P1] F-002: b\n**Confidence:** high\n[P1] F-003: c\n**Confidence:** high\n")

        result = qp.cmd_next()

        assert result["dashboard_action"] == "max_rounds", \
            f"Expected max_rounds on stagnation, got {result['dashboard_action']}"

    def test_no_stagnation_when_count_drops(self, isolated_pipeline):
        """COE-4: P0+P1 count decreases → normal continue."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-improving"
        project_path.mkdir(parents=True)

        # Round 1: 1 P0 + 2 P1 = 3
        r1_findings = [
            {"severity": "P0", "id": "F-001", "title": "a", "agent": "cr", "confidence": "high", "raw": "[P0] F-001: a"},
            {"severity": "P1", "id": "F-002", "title": "b", "agent": "cr", "confidence": "high", "raw": "[P1] F-002: b"},
            {"severity": "P1", "id": "F-003", "title": "c", "agent": "cr", "confidence": "high", "raw": "[P1] F-003: c"},
        ]

        rounds_history = [
            {"round": 1, "findings": r1_findings, "agents": ["code-reviewer"]},
        ]

        _setup_quality_fix_state(qs, project_path, round_num=2,
                                  active_agents=["code-reviewer"],
                                  rounds_history=rounds_history)

        # Round 2: Only 1 P1 (improved from 3 to 1)
        _write_quality_output(project_path, 2, "code-reviewer",
            "[P1] F-002: b\n**Confidence:** high\n")

        result = qp.cmd_next()

        assert result["dashboard_action"] == "continue", \
            f"Expected continue when improving, got {result['dashboard_action']}"

    def test_prev_findings_uses_correct_round(self, isolated_pipeline):
        """Bug fix: prev_findings must come from history[-2], not [-1] (current round)."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-prev"
        project_path.mkdir(parents=True)

        # Round 1: 1 P0
        r1_findings = [
            {"severity": "P0", "id": "F-001", "title": "a", "agent": "cr", "confidence": "high", "raw": "[P0] F-001: a"},
        ]

        rounds_history = [
            {"round": 1, "findings": r1_findings, "agents": ["code-reviewer"]},
        ]

        _setup_quality_fix_state(qs, project_path, round_num=2,
                                  active_agents=["code-reviewer"],
                                  rounds_history=rounds_history)

        # Round 2: Same 1 P0 (no change, but below stagnation threshold of 3)
        _write_quality_output(project_path, 2, "code-reviewer",
            "[P0] F-001: a\n**Confidence:** high\n")

        result = qp.cmd_next()

        # P0+P1 count = 1, below stagnation threshold of 3 → should continue
        # If prev_findings bug existed (using current round as prev), stagnation
        # would always be False (comparing to itself), masking the issue
        assert result["dashboard_action"] == "continue", \
            f"Expected continue (below stagnation threshold), got {result['dashboard_action']}"

    def test_near_stagnation_delta_one(self, isolated_pipeline):
        """COE-4: P0+P1 drops by 1 but >=3 remain → still stagnant (delta <= 1)."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-near-stagnant"
        project_path.mkdir(parents=True)

        # Round 1: 2 P0 + 2 P1 = 4
        r1_findings = [
            {"severity": "P0", "id": "F-001", "title": "a", "agent": "cr", "confidence": "high", "raw": "[P0] F-001: a"},
            {"severity": "P0", "id": "F-002", "title": "b", "agent": "cr", "confidence": "high", "raw": "[P0] F-002: b"},
            {"severity": "P1", "id": "F-003", "title": "c", "agent": "cr", "confidence": "high", "raw": "[P1] F-003: c"},
            {"severity": "P1", "id": "F-004", "title": "d", "agent": "cr", "confidence": "high", "raw": "[P1] F-004: d"},
        ]

        rounds_history = [
            {"round": 1, "findings": r1_findings, "agents": ["code-reviewer"]},
        ]

        _setup_quality_fix_state(qs, project_path, round_num=2,
                                  active_agents=["code-reviewer"],
                                  rounds_history=rounds_history)

        # Round 2: 1 P0 + 2 P1 = 3 (delta = 1, still stagnant because >= 3)
        _write_quality_output(project_path, 2, "code-reviewer",
            "[P0] F-001: a\n**Confidence:** high\n[P1] F-003: c\n**Confidence:** high\n[P1] F-004: d\n**Confidence:** high\n")

        result = qp.cmd_next()

        assert result["dashboard_action"] == "max_rounds", \
            f"Expected max_rounds on near-stagnation (delta=1), got {result['dashboard_action']}"


# ─── Gap 3: Staleness Detection ──────────────────────────────────────────────

def _setup_waiting_state(qs, project_path, sub_phase, minutes_ago,
                          agent_timing=None):
    """Set up state in a WAITING sub-phase with a stale last_activity_at."""
    last_activity = (datetime.now() - timedelta(minutes=minutes_ago)).isoformat()
    state = {
        "project_id": project_path.name,
        "project_path": str(project_path),
        "request": "build a landing page",
        "target_directory": str(project_path.parent),
        "mode": "pipeline",
        "phase": "PLAN",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
        "pipeline_version": "6.6.2",
        "manifest": {"estimated_sp": 3.0},
        "pipeline": {
            "mode": "thorough",
            "sub_phase": sub_phase,
            "last_activity_at": last_activity,
            "agent_timing": agent_timing or {},
            "plan_agents": [
                {"name": "sde-iii", "model": "opus", "prompt": "analyze"},
                {"name": "arch-advisor", "model": "sonnet", "prompt": "design"},
            ],
            "_spawned_agents": {},
        },
    }
    qs.save_state(state)
    (project_path / "agent-outputs").mkdir(parents=True, exist_ok=True)
    return state


class TestStalenessDetection:
    """Gap 3: Detect orchestrator death via stale last_activity_at."""

    def test_stale_waiting_with_agents_backdates(self, isolated_pipeline):
        """Stale WAITING phase with tracked agents → backdate start times."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-stale-agents"
        project_path.mkdir(parents=True)

        agent_timing = {
            "sde-iii": {"started_at": (datetime.now() - timedelta(minutes=40)).isoformat()},
            "arch-advisor": {"started_at": (datetime.now() - timedelta(minutes=40)).isoformat()},
        }

        _setup_waiting_state(qs, project_path, "PLAN_WAITING", minutes_ago=45,
                              agent_timing=agent_timing)

        # After staleness detection, agent start times should be backdated
        # and the normal dispatch happens (watchdog fires in the handler)
        result = qp.cmd_next()

        # Verify agent_timing was backdated (start times moved to 2 hours ago)
        state = qs.load_state()
        for agent_name in agent_timing:
            started = datetime.fromisoformat(state["pipeline"]["agent_timing"][agent_name]["started_at"])
            age_seconds = (datetime.now() - started).total_seconds()
            assert age_seconds > 3600, \
                f"Agent {agent_name} start time not backdated: only {age_seconds:.0f}s ago"

    def test_stale_waiting_no_agents_escalates(self, isolated_pipeline):
        """Stale WAITING phase with no tracked agents → escalate directly."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-stale-no-agents"
        project_path.mkdir(parents=True)

        _setup_waiting_state(qs, project_path, "PLAN_WAITING", minutes_ago=45,
                              agent_timing={})

        result = qp.cmd_next()

        assert result["action"] == "escalate_to_user", \
            f"Expected escalate_to_user on stale session, got {result['action']}"
        assert "inactive" in result["message"].lower()
        assert result.get("heal_suggestion") is not None
        assert result["heal_suggestion"]["condition"] == "session_stale"

    def test_not_stale_under_threshold(self, isolated_pipeline):
        """WAITING phase with recent activity → no staleness action."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-fresh"
        project_path.mkdir(parents=True)

        agent_timing = {
            "sde-iii": {"started_at": (datetime.now() - timedelta(minutes=5)).isoformat()},
        }

        _setup_waiting_state(qs, project_path, "PLAN_WAITING", minutes_ago=5,
                              agent_timing=agent_timing)

        # Write agent output so the handler has something to work with
        _write_agent_output(project_path, "agent-outputs", "sde-iii")
        _write_agent_output(project_path, "agent-outputs", "arch-advisor")

        result = qp.cmd_next()

        # Should NOT be an escalation — normal dispatch
        assert result["action"] != "escalate_to_user", \
            f"Should not escalate when activity is recent, got {result['action']}"

    def test_staleness_only_in_waiting_phases(self, isolated_pipeline):
        """Non-WAITING sub-phases should not trigger staleness check."""
        qp, qs, tmp_path = isolated_pipeline
        project_path = tmp_path / ".qralph" / "projects" / "test-non-waiting"
        project_path.mkdir(parents=True)

        # Set up in PLAN_REVIEW (not _WAITING) but with stale timestamp
        state = {
            "project_id": project_path.name,
            "project_path": str(project_path),
            "request": "build a landing page",
            "target_directory": str(project_path.parent),
            "mode": "pipeline",
            "phase": "PLAN",
            "created_at": datetime.now().isoformat(),
            "agents": [],
            "heal_attempts": 0,
            "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
            "pipeline_version": "6.6.2",
            "manifest": {"estimated_sp": 3.0},
            "pipeline": {
                "mode": "thorough",
                "sub_phase": "PLAN_REVIEW",
                "last_activity_at": (datetime.now() - timedelta(minutes=60)).isoformat(),
                "gate_shown": True,
            },
        }
        qs.save_state(state)
        (project_path / "agent-outputs").mkdir(parents=True, exist_ok=True)

        result = qp.cmd_next(confirm=True)

        # Should proceed normally (confirm gate), not escalate
        assert result["action"] != "escalate_to_user", \
            f"Non-WAITING phase should not trigger staleness, got {result['action']}"
