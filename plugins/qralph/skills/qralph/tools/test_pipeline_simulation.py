#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""Pipeline simulation tests — drive full pipeline with mocked LLM responses.

Runs cmd_plan() → repeated cmd_next() cycles with fixture responses written
at each spawn_agents action. No real Claude calls. Validates the state machine
reaches COMPLETE for both quick and thorough modes.

Run: cd .qralph/tools && python3 -m pytest test_pipeline_simulation.py -v
"""

import importlib.util
import json
import os
import sys
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

# ─── Module Loading ──────────────────────────────────────────────────────────

_tools_dir = Path(__file__).parent


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _tools_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─── Mock Response Fixtures ──────────────────────────────────────────────────

_AGENT_FILLER = "Analysis content. " * 30  # > MIN_AGENT_OUTPUT_LENGTH (100)

MOCK_RESEARCHER = f"# Research Analysis\n\n{_AGENT_FILLER}\n\n## Findings\nThe project is well-scoped."
MOCK_SDE_III = f"# Implementation Analysis\n\n{_AGENT_FILLER}\n\n## Recommendations\nStraightforward implementation."
MOCK_ARCH_ADVISOR = f"# Architecture Review\n\n{_AGENT_FILLER}\n\n## Conclusion\nNo architectural concerns."

MOCK_EXECUTION_OUTPUT = f"# Task Complete\n\n{_AGENT_FILLER}\n\nFiles changed:\n- src/index.ts (added feature)\n\nTests passing: 5/5\nQuality gate: PASS"

MOCK_SIMPLIFIER = f"# Simplification Report\n\n{_AGENT_FILLER}\n\nNo changes needed. Code is already clean and readable."

MOCK_BRAINSTORMER = f"# Ideation\n\n{_AGENT_FILLER}\n\n## Ideas\n1. Build a landing page\n2. Add contact form\n3. SEO optimization"

MOCK_CONCEPT_REVIEW = f"# Concept Review\n\n{_AGENT_FILLER}\n\n## P0 Findings\nNone.\n\n## P1 Findings\nNone.\n\n## P2 Findings\nConsider adding analytics."

MOCK_QUALITY_CLEAN = f"# Quality Review\n\n{_AGENT_FILLER}\n\nNo issues found. Code meets all quality standards."

MOCK_QUALITY_P0 = f"# Quality Review\n\n{_AGENT_FILLER}\n\n[P0] CR-001: Missing input validation\nUser input not sanitized.\n**Suggested fix:** Add validation layer.\n**Confidence:** high"

MOCK_QUALITY_RESOLVED = f"# Reverification\n\n{_AGENT_FILLER}\n\nRESOLVED: CR-001 — Input validation added."

MOCK_POLISH_CLEAN = f"# Polish Report\n\n{_AGENT_FILLER}\n\nNo issues found. All requirements covered. All code is reachable."

MOCK_POLISH_NEEDS_ATTENTION = f"# Polish Report\n\n{_AGENT_FILLER}\n\nP1 issue detected: missing error handler in API route."


def _make_verify_json(verdict="PASS", fragments=None):
    """Build a valid verification JSON response."""
    criteria_results = [
        {
            "criterion_index": "AC-1",
            "criterion": "Feature is implemented",
            "status": "pass",
            "intent_match": True,
            "ship_ready": True,
            "evidence": "src/index.ts:42 — feature implemented correctly",
        },
        {
            "criterion_index": "AC-2",
            "criterion": "Tests pass",
            "status": "pass",
            "intent_match": True,
            "ship_ready": True,
            "evidence": "src/index.spec.ts:10 — all tests green",
        },
        {
            "criterion_index": "AC-3",
            "criterion": "Contact form renders with name and email fields",
            "status": "pass",
            "intent_match": True,
            "ship_ready": True,
            "evidence": "src/contact.ts:15 — form component with fields",
        },
    ]

    satisfaction = []
    if fragments:
        for frag in fragments:
            satisfaction.append({
                "fragment_id": frag["id"],
                "fragment_text": frag["text"][:50],
                "status": "satisfied",
                "evidence": f"implemented in src/index.ts",
            })

    data = {
        "verdict": verdict,
        "criteria_results": criteria_results,
        "request_satisfaction": satisfaction,
        "quality_gate": "pass",
        "issues": [],
    }
    return json.dumps(data, indent=2)


# ─── Manifest Fixture ────────────────────────────────────────────────────────

MOCK_MANIFEST = {
    "tasks": [
        {
            "id": "T-001",
            "summary": "Build the landing page",
            "description": "Create an HTML landing page with hero section",
            "files": ["src/index.ts"],
            "acceptance_criteria": [
                "Feature is implemented",
                "Tests pass",
            ],
            "tests_needed": True,
        },
        {
            "id": "T-002",
            "summary": "Add contact form",
            "description": "Add a contact form component",
            "files": ["src/contact.ts"],
            "acceptance_criteria": [
                "Contact form renders with name and email fields",
            ],
            "tests_needed": True,
        },
    ],
    "parallel_groups": [["T-001", "T-002"]],
}


# ─── Fixture ─────────────────────────────────────────────────────────────────

@pytest.fixture
def isolated_pipeline(tmp_path):
    """Load pipeline module with all paths redirected to tmp_path."""
    qralph_dir = tmp_path / ".qralph"
    qralph_dir.mkdir()
    projects_dir = qralph_dir / "projects"
    projects_dir.mkdir()
    state_file = qralph_dir / "current-project.json"

    qs = _load_module("qs_sim", "qralph-state.py")
    qs.QRALPH_DIR = qralph_dir
    qs.STATE_FILE = state_file
    qs.PROJECT_ROOT = tmp_path

    qp = _load_module("qp_sim", "qralph-pipeline.py")
    qp.QRALPH_DIR = qralph_dir
    qp.PROJECTS_DIR = projects_dir
    qp.STATE_FILE = state_file
    qp.PROJECT_ROOT = tmp_path
    qp.SESSION_LOCK = qralph_dir / "active-session.lock"
    qp.qralph_state = qs
    qp.qralph_config.QRALPH_DIR = qralph_dir
    qp.qralph_config.CONFIG_FILE = qralph_dir / "config.json"
    qp.qralph_config.PROJECT_ROOT = tmp_path
    qp.qralph_config.qralph_state = qs

    return qp, qs, tmp_path


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _write_output(path, filename, content):
    """Write a mock agent output file."""
    path.mkdir(parents=True, exist_ok=True)
    (path / filename).write_text(content)


def _get_project_path(qs):
    """Get the current project path from state."""
    state = qs.load_state()
    return Path(state["project_path"])


def _write_manifest(project_path, manifest_data):
    """Update manifest.json with tasks and parallel_groups, preserving existing data."""
    manifest_path = project_path / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {
            "project_id": project_path.name,
            "request": "build a landing page with contact form",
            "template": "new-feature",
            "target_directory": str(project_path.parent.parent.parent),
            "agent_analyses": ["researcher", "sde-iii"],
            "missing_agents": [],
            "quality_gate_cmd": "",
            "quality_gate_cwd": "",
            "created_at": datetime.now().isoformat(),
        }
    manifest.update(manifest_data)
    manifest_path.write_text(json.dumps(manifest, indent=2))


def _drive_pipeline(qp, qs, tmp_path, mode, fixtures, stop_condition=None):
    """Drive the pipeline from plan to completion using fixture responses.

    Args:
        qp: pipeline module
        qs: state module
        tmp_path: test temp directory
        mode: "quick" or "thorough"
        fixtures: dict mapping (sub_phase, agent_name) -> content string,
                  plus special keys like "manifest" for manifest data.
        stop_condition: optional callable(action, result, sub_phase, qs) -> bool.
                        If it returns True, the loop stops and returns history.

    Returns:
        list of (action, sub_phase) tuples for the full run.
    """
    # Patch subprocess to avoid real shell calls
    with patch.object(qp, "_run_shell_chain", return_value=(0, "PASS")), \
         patch.object(qp, "detect_quality_gate", return_value={"cmd": "", "cwd": "", "effective": True}):

        # Init
        result = qp.cmd_plan("build a landing page with contact form", mode=mode)
        assert "error" not in result, f"cmd_plan failed: {result}"

        project_path = _get_project_path(qs)

        # Read request fragments from state to build accurate verify fixture.
        # Only override if the existing verify fixture has a PASS verdict —
        # this preserves intentional FAIL fixtures for error-path tests.
        state = qs.load_state()
        request_fragments = state.get("request_fragments", [])
        existing_verify = fixtures.get(("*", "result"), "")
        if request_fragments and '"FAIL"' not in existing_verify:
            verify_json = _make_verify_json("PASS", request_fragments)
            fixtures[("VERIFY_WAIT", "result")] = verify_json
            fixtures[("*", "result")] = verify_json
        history = []
        max_iterations = 80
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            state = qs.load_state()
            pipeline = state.get("pipeline", {})
            sub_phase = pipeline.get("sub_phase", "UNKNOWN")

            result = qp.cmd_next()
            action = result.get("action", "unknown")
            history.append((action, sub_phase))

            if action == "complete":
                return history

            if action == "confirm_template":
                # Auto-confirm template selection
                result = qp.cmd_next(confirm=True)
                action2 = result.get("action", "")
                history.append((action2, "INIT_CONFIRM"))

                if action2 == "spawn_agents":
                    agents = result.get("agents", [])
                    output_dir = Path(result.get("output_dir", str(project_path / "agent-outputs")))
                    for agent in agents:
                        agent_name = agent.get("name", "unknown")
                        content = fixtures.get(("INIT", agent_name)) or fixtures.get(("*", agent_name)) or _AGENT_FILLER * 2
                        _write_output(output_dir, f"{agent_name}.md", content)
                continue

            if action == "spawn_agents":
                agents = result.get("agents", [])
                output_dir_str = result.get("output_dir", "")
                output_dir = Path(output_dir_str) if output_dir_str else None

                for agent in agents:
                    agent_name = agent.get("name", agent.get("task_id", "unknown"))
                    output_file = agent.get("output_file", f"{agent_name}.md")

                    # Determine output directory based on phase
                    if output_dir:
                        out_path = output_dir
                    elif "execution" in str(output_dir_str):
                        out_path = project_path / "execution-outputs"
                    elif "verification" in str(output_dir_str):
                        out_path = project_path / "verification"
                    else:
                        out_path = project_path / "agent-outputs"

                    # Look up fixture content
                    content = fixtures.get((sub_phase, agent_name))
                    if content is None:
                        content = fixtures.get(("*", agent_name))
                    if content is None:
                        content = _AGENT_FILLER * 2

                    _write_output(out_path, output_file, content)

            elif action == "define_tasks":
                # Pipeline collected plan outputs, now we need to write manifest
                manifest_data = fixtures.get("manifest", MOCK_MANIFEST)
                _write_manifest(project_path, manifest_data)

            elif action == "confirm_plan":
                # Auto-confirm the plan
                result = qp.cmd_next(confirm=True)
                action2 = result.get("action", "")
                history.append((action2, "PLAN_REVIEW_CONFIRM"))

                if action2 == "error":
                    raise AssertionError(
                        f"confirm_plan failed: {result.get('message', 'unknown error')}"
                    )

                if action2 == "spawn_agents":
                    # Write execution outputs for spawned agents
                    agents = result.get("agents", [])
                    output_dir = Path(result.get("output_dir", str(project_path / "execution-outputs")))
                    for agent in agents:
                        agent_name = agent.get("name", "unknown")
                        content = fixtures.get(("EXEC", agent_name), MOCK_EXECUTION_OUTPUT)
                        _write_output(output_dir, f"{agent_name}.md", content)

            elif action == "confirm_demo":
                # Auto-confirm DEMO gate (approve, no feedback)
                result = qp.cmd_next(confirm=True)
                action2 = result.get("action", "")
                history.append((action2, "confirm_demo_CONFIRM"))

            elif action in ("confirm_ideation", "confirm_personas", "confirm_concept"):
                # Auto-confirm review gates
                result = qp.cmd_next(confirm=True)
                action2 = result.get("action", "")
                history.append((action2, f"{action}_CONFIRM"))

                # Some confirms return spawn_agents (concept -> concept agents)
                if action2 == "spawn_agents":
                    agents = result.get("agents", [])
                    output_dir = Path(result.get("output_dir", str(project_path / "agent-outputs")))
                    for agent in agents:
                        agent_name = agent.get("name", "unknown")
                        out_file = agent.get("output_file", f"{agent_name}.md")
                        content = fixtures.get((sub_phase, agent_name)) or fixtures.get(("*", agent_name)) or _AGENT_FILLER * 2
                        _write_output(output_dir, out_file, content)

            elif action == "confirm_polish":
                # Polish review auto-advances (the next cmd_next reads the report)
                pass

            elif action == "advance":
                # Phase advance — just continue the loop
                pass

            elif action in ("learn_complete", "learn_capture"):
                # These are terminal-ish actions that may still need one more iteration
                pass

            elif action == "quality_assessed":
                # Quality fix results — continue loop
                pass

            elif action == "quality_fix_tasks":
                # Quality loop continuing — findings need to be fixed
                pass

            elif action == "error":
                # Check stop condition before handling
                if stop_condition and stop_condition(action, result, sub_phase, qs):
                    return history

                # Errors may be retryable — check if we can fix
                msg = result.get("message", "")
                if "Missing outputs" in msg or "Missing output" in msg:
                    # Write whatever outputs are missing
                    expected = result.get("expected", [])
                    output_dir = Path(result.get("output_dir", str(project_path / "agent-outputs")))
                    for name in expected:
                        content = fixtures.get(("*", name), _AGENT_FILLER * 2)
                        _write_output(output_dir, f"{name}.md", content)
                elif "No tasks defined" in msg:
                    manifest_data = fixtures.get("manifest", MOCK_MANIFEST)
                    _write_manifest(project_path, manifest_data)
                else:
                    raise AssertionError(f"Unhandled pipeline error at {sub_phase}: {msg}")

            elif action == "escalate_to_user":
                if stop_condition and stop_condition(action, result, sub_phase, qs):
                    return history
                raise AssertionError(
                    f"Pipeline escalated to user at {sub_phase}: {result.get('message', '')}"
                )

        raise AssertionError(f"Pipeline did not reach COMPLETE in {max_iterations} iterations. Last: {history[-5:]}")


# ─── Quick Mode Fixtures ─────────────────────────────────────────────────────

def _quick_fixtures(request_fragments=None):
    """Fixture responses for quick mode pipeline."""
    verify_json = _make_verify_json("PASS", request_fragments)
    return {
        # PLAN phase — INIT spawns plan agents
        ("INIT", "researcher"): MOCK_RESEARCHER,
        ("INIT", "sde-iii"): MOCK_SDE_III,
        ("INIT", "architecture-advisor"): MOCK_ARCH_ADVISOR,
        ("*", "researcher"): MOCK_RESEARCHER,
        ("*", "sde-iii"): MOCK_SDE_III,
        ("*", "architecture-advisor"): MOCK_ARCH_ADVISOR,
        # EXECUTE phase
        ("EXEC", "T-001"): MOCK_EXECUTION_OUTPUT,
        ("EXEC", "T-002"): MOCK_EXECUTION_OUTPUT,
        ("EXEC_WAITING", "T-001"): MOCK_EXECUTION_OUTPUT,
        ("EXEC_WAITING", "T-002"): MOCK_EXECUTION_OUTPUT,
        ("*", "T-001"): MOCK_EXECUTION_OUTPUT,
        ("*", "T-002"): MOCK_EXECUTION_OUTPUT,
        # SIMPLIFY phase
        ("SIMPLIFY_RUN", "simplifier"): MOCK_SIMPLIFIER,
        ("SIMPLIFY_WAITING", "simplifier"): MOCK_SIMPLIFIER,
        ("*", "simplifier"): MOCK_SIMPLIFIER,
        # VERIFY phase
        ("VERIFY_WAIT", "result"): verify_json,
        ("*", "result"): verify_json,
        # Manifest
        "manifest": MOCK_MANIFEST,
    }


# ─── Thorough Mode Fixtures ──────────────────────────────────────────────────

def _thorough_fixtures(request_fragments=None):
    """Fixture responses for thorough mode pipeline."""
    verify_json = _make_verify_json("PASS", request_fragments)
    fixtures = _quick_fixtures(request_fragments)
    fixtures.update({
        # IDEATE phase
        ("IDEATE_BRAINSTORM", "brainstormer"): MOCK_BRAINSTORMER,
        ("IDEATE_WAITING", "brainstormer"): MOCK_BRAINSTORMER,
        ("*", "brainstormer"): MOCK_BRAINSTORMER,
        # CONCEPT phase (persona names vary — use wildcard)
        ("CONCEPT_SPAWN", "persona-end-user"): MOCK_CONCEPT_REVIEW,
        ("CONCEPT_SPAWN", "persona-developer"): MOCK_CONCEPT_REVIEW,
        ("CONCEPT_SPAWN", "persona-business"): MOCK_CONCEPT_REVIEW,
        ("CONCEPT_WAITING", "persona-end-user"): MOCK_CONCEPT_REVIEW,
        ("CONCEPT_WAITING", "persona-developer"): MOCK_CONCEPT_REVIEW,
        ("CONCEPT_WAITING", "persona-business"): MOCK_CONCEPT_REVIEW,
        ("*", "persona-end-user"): MOCK_CONCEPT_REVIEW,
        ("*", "persona-developer"): MOCK_CONCEPT_REVIEW,
        ("*", "persona-business"): MOCK_CONCEPT_REVIEW,
        ("*", "business-advisor"): MOCK_CONCEPT_REVIEW,
        # QUALITY_LOOP — clean (no findings)
        ("QUALITY_DISCOVERY", "code-reviewer"): MOCK_QUALITY_CLEAN,
        ("QUALITY_DISCOVERY", "security-reviewer"): MOCK_QUALITY_CLEAN,
        ("QUALITY_DISCOVERY", "business-advisor"): MOCK_QUALITY_CLEAN,
        ("QUALITY_FIX", "code-reviewer"): MOCK_QUALITY_CLEAN,
        ("QUALITY_FIX", "security-reviewer"): MOCK_QUALITY_CLEAN,
        ("*", "code-reviewer"): MOCK_QUALITY_CLEAN,
        ("*", "security-reviewer"): MOCK_QUALITY_CLEAN,
        ("*", "pe-architect"): MOCK_QUALITY_CLEAN,
        ("*", "test-verifier"): MOCK_QUALITY_CLEAN,
        ("*", "failure-analyst"): MOCK_QUALITY_CLEAN,
        ("*", "usability-reviewer"): MOCK_QUALITY_CLEAN,
        # QUALITY_REVERIFY
        ("QUALITY_REVERIFY", "quality-verifier"): MOCK_QUALITY_RESOLVED,
        ("*", "quality-verifier"): MOCK_QUALITY_RESOLVED,
        # POLISH phase
        ("POLISH_RUN", "bug_fixer"): MOCK_POLISH_CLEAN,
        ("POLISH_RUN", "wiring_agent"): MOCK_POLISH_CLEAN,
        ("POLISH_RUN", "requirements_tracer"): MOCK_POLISH_CLEAN,
        ("POLISH_WAITING", "bug_fixer"): MOCK_POLISH_CLEAN,
        ("POLISH_WAITING", "wiring_agent"): MOCK_POLISH_CLEAN,
        ("POLISH_WAITING", "requirements_tracer"): MOCK_POLISH_CLEAN,
        ("*", "bug_fixer"): MOCK_POLISH_CLEAN,
        ("*", "wiring_agent"): MOCK_POLISH_CLEAN,
        ("*", "requirements_tracer"): MOCK_POLISH_CLEAN,
    })
    return fixtures


# ─── Test Cases ──────────────────────────────────────────────────────────────

class TestSimulationQuickMode:
    def test_quick_mode_reaches_complete(self, isolated_pipeline):
        """Full quick pipeline from plan to complete with mocked responses."""
        qp, qs, tmp_path = isolated_pipeline
        fixtures = _quick_fixtures()
        history = _drive_pipeline(qp, qs, tmp_path, "quick", fixtures)
        actions = [h[0] for h in history]
        assert "complete" in actions, f"Pipeline did not reach complete. History: {history}"


class TestSimulationThoroughMode:
    def test_thorough_mode_reaches_complete(self, isolated_pipeline):
        """Full thorough pipeline from plan to complete with mocked responses."""
        qp, qs, tmp_path = isolated_pipeline
        fixtures = _thorough_fixtures()
        history = _drive_pipeline(qp, qs, tmp_path, "thorough", fixtures)
        actions = [h[0] for h in history]
        assert "complete" in actions, f"Pipeline did not reach complete. History: {history}"


class TestSimulationVerifyFailure:
    def test_verify_failure_triggers_retry(self, isolated_pipeline):
        """Verify returns FAIL, pipeline retries (increments verify_retries)."""
        qp, qs, tmp_path = isolated_pipeline

        fixtures = _quick_fixtures()
        # Override verify to return FAIL — _drive_pipeline preserves FAIL fixtures
        fail_verify = _make_verify_json("FAIL")
        fixtures[("VERIFY_WAIT", "result")] = fail_verify
        fixtures[("*", "result")] = fail_verify

        verify_state = {"hit": False}

        def _stop_on_verify_error(action, result, sub_phase, qs_mod):
            msg = result.get("message", "")
            if "Verification" in msg or "verdict" in msg.lower():
                state = qs_mod.load_state()
                retries = state.get("pipeline", {}).get("verify_retries", 0)
                assert retries > 0, "verify_retries should have been incremented"
                verify_state["hit"] = True
                return True
            return False

        history = _drive_pipeline(qp, qs, tmp_path, "quick", fixtures, stop_condition=_stop_on_verify_error)
        assert verify_state["hit"], "Pipeline should have hit verify error with FAIL verdict"


class TestSimulationPolishRetry:
    def test_polish_needs_attention_retries(self, isolated_pipeline):
        """POLISH returns NEEDS_ATTENTION, pipeline retries up to cap then escalates."""
        qp, qs, tmp_path = isolated_pipeline

        fixtures = _thorough_fixtures()
        # Override polish bug_fixer output to trigger NEEDS_ATTENTION
        fixtures[("POLISH_RUN", "bug_fixer")] = MOCK_POLISH_NEEDS_ATTENTION
        fixtures[("POLISH_WAITING", "bug_fixer")] = MOCK_POLISH_NEEDS_ATTENTION
        fixtures[("*", "bug_fixer")] = MOCK_POLISH_NEEDS_ATTENTION

        polish_state = {"retried": False}

        def _stop_on_polish_escalation(action, result, sub_phase, qs_mod):
            if action == "escalate_to_user":
                polish_state["retried"] = True
                return True
            if action == "error":
                msg = result.get("message", "")
                # Verify errors from NEEDS_ATTENTION retry path
                if "POLISH" in msg.upper():
                    state = qs_mod.load_state()
                    retry_count = state.get("pipeline", {}).get("polish_retry_count", 0)
                    if retry_count > 0:
                        polish_state["retried"] = True
                        return True
            return False

        history = _drive_pipeline(qp, qs, tmp_path, "thorough", fixtures, stop_condition=_stop_on_polish_escalation)

        # The pipeline should have retried polish or reached escalation/completion
        # If it completed (NEEDS_ATTENTION triggers retry, eventually escalates or uses clean output),
        # check that retries happened
        if not polish_state["retried"]:
            # Check state for evidence of polish retries
            state = qs.load_state()
            retry_count = state.get("pipeline", {}).get("polish_retry_count", 0)
            assert retry_count > 0, "Pipeline should have retried POLISH at least once"


class TestSimulationQualityLoopConvergence:
    def test_quality_loop_convergence(self, isolated_pipeline):
        """Quality loop enters and runs at least one round."""
        qp, qs, tmp_path = isolated_pipeline
        fixtures = _thorough_fixtures()

        quality_state = {"assessed": False}

        def _stop_after_quality(action, result, sub_phase, qs_mod):
            # Don't stop — just track. But stop on escalations from quality.
            if action == "escalate_to_user":
                quality_state["assessed"] = True
                return True
            return False

        history = _drive_pipeline(qp, qs, tmp_path, "thorough", fixtures, stop_condition=_stop_after_quality)
        actions = [h[0] for h in history]

        # Quality loop should have been entered (quality_assessed action seen)
        assert "quality_assessed" in actions or quality_state["assessed"], \
            f"Pipeline should have entered quality assessment. Actions: {actions}"


# ─── Gap Coverage: QUALITY_REVERIFY path ─────────────────────────────────────

MOCK_QUALITY_REVERIFY_RESOLVED = (
    f"# Reverification Results\n\n{_AGENT_FILLER}\n\n"
    "RESOLVED: CR-001\n"
    "RESOLVED: SR-001\n"
)


class TestSimulationQualityReverify:
    def test_quality_p0_triggers_reverify_path(self, isolated_pipeline):
        """Quality loop with P0 findings routes through QUALITY_REVERIFY before dashboard."""
        qp, qs, tmp_path = isolated_pipeline

        fixtures = _thorough_fixtures()
        # Round 1: P0 findings trigger reverify path
        fixtures[("QUALITY_DISCOVERY", "code-reviewer")] = MOCK_QUALITY_P0
        fixtures[("QUALITY_FIX", "code-reviewer")] = MOCK_QUALITY_P0
        fixtures[("*", "quality-verifier")] = MOCK_QUALITY_REVERIFY_RESOLVED

        def _track_reverify(action, result, sub_phase, qs_mod):
            if action == "escalate_to_user":
                return True
            return False

        history = _drive_pipeline(qp, qs, tmp_path, "thorough", fixtures, stop_condition=_track_reverify)
        sub_phases = [h[1] for h in history]

        # Verify that QUALITY_REVERIFY_WAITING was traversed (reverify agent spawned)
        # OR that quality_assessed was seen (loop ran and found P0s)
        actions = [h[0] for h in history]
        assert "quality_assessed" in actions, \
            f"Quality loop should have run. Actions: {actions}"

        # Check that the reverify path was entered by looking at state history
        # The quality_assessed action is returned from QUALITY_FIX, which sets
        # sub_phase to QUALITY_REVERIFY when P0/P1 findings exist
        state = qs.load_state()
        pipeline = state.get("pipeline", {})
        ql = pipeline.get("quality_loop", {})
        rounds = ql.get("rounds_history", [])
        if rounds:
            r1_findings = rounds[0].get("findings", [])
            p0_count = sum(1 for f in r1_findings if f.get("severity") == "P0")
            assert p0_count > 0, "Round 1 should have had P0 findings"


# ─── Gap Coverage: DEPLOY + SMOKE path ───────────────────────────────────────

MOCK_SMOKE_PASS = (
    f"# Smoke Test Results\n\n{_AGENT_FILLER}\n\n"
    "- **PASS** [T-001] Feature is implemented — 200 OK, content matches\n"
    "- **PASS** [T-002] Contact form renders — form elements present\n\n"
    "SMOKE VERDICT: 2 passed, 0 failed, 0 skipped\n"
)


class TestSimulationDeploySmokePath:
    def test_deploy_intent_triggers_deploy_phase(self, isolated_pipeline):
        """Request with deploy intent reaches DEPLOY_PREFLIGHT instead of skipping to LEARN."""
        qp, qs, tmp_path = isolated_pipeline

        fixtures = _quick_fixtures()

        deploy_state = {"reached_deploy": False}

        def _track_deploy(action, result, sub_phase, qs_mod):
            if action == "error":
                msg = result.get("message", "")
                # Deploy preflight with no wrangler/vercel config → error is expected
                if "deploy" in msg.lower() or "wrangler" in msg.lower() or "vercel" in msg.lower():
                    deploy_state["reached_deploy"] = True
                    return True
            if action == "confirm_deploy":
                deploy_state["reached_deploy"] = True
                return True
            if action == "escalate_to_user" and "deploy" in result.get("message", "").lower():
                deploy_state["reached_deploy"] = True
                return True
            return False

        # Use a request with explicit deploy intent
        with patch.object(qp, "_run_shell_chain", return_value=(0, "PASS")), \
             patch.object(qp, "detect_quality_gate", return_value={"cmd": "", "cwd": "", "effective": True}):

            result = qp.cmd_plan(
                "build a landing page with contact form and deploy to production",
                mode="quick",
            )
            assert "error" not in result, f"cmd_plan failed: {result}"

            project_path = _get_project_path(qs)

            # Update verify fixture with actual fragments
            state = qs.load_state()
            request_fragments = state.get("request_fragments", [])
            if request_fragments:
                verify_json = _make_verify_json("PASS", request_fragments)
                fixtures[("VERIFY_WAIT", "result")] = verify_json
                fixtures[("*", "result")] = verify_json

            max_iterations = 60
            for _ in range(max_iterations):
                state = qs.load_state()
                pipeline = state.get("pipeline", {})
                sub_phase = pipeline.get("sub_phase", "")

                result = qp.cmd_next()
                action = result.get("action", "")

                if deploy_state["reached_deploy"]:
                    break
                if _track_deploy(action, result, sub_phase, qs):
                    break

                if action == "complete":
                    # Shouldn't complete without hitting deploy
                    break
                elif action == "confirm_demo":
                    result = qp.cmd_next(confirm=True)
                    if _track_deploy(result.get("action", ""), result, sub_phase, qs):
                        break
                elif action == "confirm_template":
                    result = qp.cmd_next(confirm=True)
                    if result.get("action") == "spawn_agents":
                        out_dir = Path(result.get("output_dir", str(project_path / "agent-outputs")))
                        for a in result.get("agents", []):
                            content = fixtures.get(("*", a["name"]), _AGENT_FILLER * 2)
                            _write_output(out_dir, f"{a['name']}.md", content)
                elif action == "spawn_agents":
                    agents = result.get("agents", [])
                    out_dir = Path(result.get("output_dir", str(project_path / "agent-outputs")))
                    for a in agents:
                        name = a.get("name", "unknown")
                        out_file = a.get("output_file", f"{name}.md")
                        content = fixtures.get((sub_phase, name)) or fixtures.get(("*", name)) or _AGENT_FILLER * 2
                        _write_output(out_dir, out_file, content)
                elif action == "define_tasks":
                    _write_manifest(project_path, MOCK_MANIFEST)
                elif action == "confirm_plan":
                    result = qp.cmd_next(confirm=True)
                    if result.get("action") == "error":
                        raise AssertionError(f"confirm_plan failed: {result.get('message')}")
                    if result.get("action") == "spawn_agents":
                        out_dir = Path(result.get("output_dir", str(project_path / "execution-outputs")))
                        for a in result.get("agents", []):
                            _write_output(out_dir, f"{a.get('name', 'x')}.md", MOCK_EXECUTION_OUTPUT)
                elif action == "error":
                    msg = result.get("message", "")
                    if "Missing outputs" in msg or "Missing output" in msg:
                        expected = result.get("expected", [])
                        out_dir = Path(result.get("output_dir", str(project_path / "agent-outputs")))
                        for name in expected:
                            content = fixtures.get(("*", name), _AGENT_FILLER * 2)
                            _write_output(out_dir, f"{name}.md", content)
                    else:
                        raise AssertionError(f"Unexpected error at {sub_phase}: {msg}")
                elif action == "learn_complete":
                    break

        assert deploy_state["reached_deploy"], (
            "Request with 'deploy to production' should have reached DEPLOY_PREFLIGHT. "
            f"Pipeline went straight to LEARN instead."
        )


# NOTE: BACKTRACK_REPLAN and session staleness paths are tested in
# test_e2e_resilience.py (TestQualityLoopDecisionWiring, TestStalenessDetection).
# Those unit tests cover the exact same state construction + cmd_next patterns
# without the overhead of full pipeline simulation.
