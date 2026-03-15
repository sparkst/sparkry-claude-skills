"""End-to-end integration tests for QRALPH CLI loop.

Tests the full pipeline orchestration with mocked pipeline and claude calls.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import importlib.util
import json
import tempfile
from unittest.mock import patch, MagicMock, call

import pytest

from cli_escalation import SessionStore

# ---------------------------------------------------------------------------
# Import qralph-cli.py (hyphenated filename requires importlib)
# ---------------------------------------------------------------------------
_cli_path = Path(__file__).parent / "qralph-cli.py"
_cli_spec = importlib.util.spec_from_file_location("qralph_cli", _cli_path)
qralph_cli = importlib.util.module_from_spec(_cli_spec)
_cli_spec.loader.exec_module(qralph_cli)


def _make_response(
    action_type: str,
    current_phase: str,
    phase_index: int,
    total_phases: int,
    sub_phase: str,
    *,
    agents: list[dict] | None = None,
    scores: dict | None = None,
    description: str = "",
) -> dict:
    """Build a pipeline response dict matching real pipeline output.

    The pipeline returns ``"action"`` as a string (e.g. ``"spawn_agents"``),
    with other fields at the top level of the response dict.
    """
    response: dict = {
        "action": action_type,
        "phase_progress": {
            "current_phase": current_phase,
            "phase_index": phase_index,
            "total_phases": total_phases,
            "sub_phase": sub_phase,
        },
    }
    if agents is not None:
        response["agents"] = agents
        response["output_dir"] = "/tmp/qralph-test-output"
    if scores is not None:
        response["scores"] = scores
    if description:
        response["description"] = description
    return response


def _agent(name: str, model: str = "sonnet") -> dict:
    return {"name": name, "model": model, "prompt": f"Do {name} work"}


# ---------------------------------------------------------------------------
# Test: full loop IDEATE → PLAN → COMPLETE
# ---------------------------------------------------------------------------

class TestFullLoopIdeateThroughPlan:
    """Simulate the full pipeline from IDEATE through PLAN to COMPLETE."""

    def test_full_loop_ideate_through_plan(self):
        """run_loop drives through all phases and returns complete action."""
        # Build the pipeline_next response sequence:
        # 1. IDEATE: spawn_agents (brainstormer) -> confirm_ideation
        # 2. PERSONA: spawn_agents (persona-gen) -> confirm_personas
        # 3. CONCEPT: spawn_agents (reviewer) -> confirm_concept
        # 4. PLAN: confirm_template -> spawn_agents (sde-iii) -> define_tasks -> confirm_plan
        # 5. complete
        #
        # Note: each spawn_agents and each decision-agent confirm_ triggers
        # an extra pipeline_next call (the auto-advance after work/decision).
        sequence = [
            # IDEATE phase
            _make_response("spawn_agents", "IDEATE", 1, 5, "IDEATE_BRAINSTORM",
                           agents=[_agent("brainstormer")]),
            # ^ after spawn completes, run_loop calls pipeline_next(confirm=True)
            _make_response("confirm_ideation", "IDEATE", 1, 5, "IDEATE_REVIEW"),
            # ^ confirm_ideation is a decision_agent (should_escalate_gate returns True)
            #   escalate returns confirm → pipeline_next(confirm=True)
            # PERSONA phase
            _make_response("spawn_agents", "PERSONA", 2, 5, "PERSONA_GEN",
                           agents=[_agent("persona-gen")]),
            _make_response("confirm_personas", "PERSONA", 2, 5, "PERSONA_REVIEW"),
            # CONCEPT phase
            _make_response("spawn_agents", "CONCEPT", 3, 5, "CONCEPT_SPAWN",
                           agents=[_agent("reviewer")]),
            _make_response("confirm_concept", "CONCEPT", 3, 5, "CONCEPT_REVIEW"),
            # PLAN phase
            _make_response("confirm_template", "PLAN", 4, 5, "INIT",
                           scores={"web-app": 9, "cli-tool": 3}),
            # ^ confirm_template with score gap >= 2 → deterministic
            _make_response("spawn_agents", "PLAN", 4, 5, "PLAN_WAITING",
                           agents=[_agent("sde-iii")]),
            _make_response("define_tasks", "PLAN", 4, 5, "PLAN_REVIEW",
                           description="Break plan into tasks"),
            # ^ define_tasks is deterministic — does NOT call pipeline_next (no confirm_ prefix)
            #   The loop just falls through to next iteration which calls pipeline_next at top
            _make_response("confirm_plan", "PLAN", 4, 5, "PLAN_REVIEW"),
            # ^ decision_agent → escalate returns confirm → pipeline_next(confirm=True)
            # COMPLETE
            _make_response("complete", "COMPLETE", 5, 5, "COMPLETE"),
        ]

        call_index = {"i": 0}

        def mock_pipeline_next(project_id=None, confirm=False, feedback=""):
            idx = call_index["i"]
            call_index["i"] += 1
            if idx < len(sequence):
                return sequence[idx]
            # Safety fallback — should never be reached
            return _make_response("complete", "COMPLETE", 5, 5, "COMPLETE")

        def mock_escalate(store, project_id, phase_key, prompt, rules, progress, working_dir, model="opus"):
            return {"decision": "DECISION: confirm\nLooks good.", "session_id": "test-sess"}

        def mock_spawn(name, model, prompt, output_file, working_dir):
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            Path(output_file).write_text("mocked output")
            return "mocked output"

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions.json")

            with patch.object(qralph_cli, "pipeline_next", side_effect=mock_pipeline_next), \
                 patch.object(qralph_cli, "escalate", side_effect=mock_escalate), \
                 patch.object(qralph_cli, "spawn_work_agent", side_effect=mock_spawn):

                result = qralph_cli.run_loop(
                    project_id="test-001",
                    working_dir=tmpdir,
                    session_store=store,
                )

            assert result["action"] == "complete"
            # The loop calls pipeline_next at the top of each iteration,
            # plus extra calls for confirm/advance after work and decisions.
            # Should be at least 10 calls for the full sequence.
            assert call_index["i"] >= 10, f"Expected >= 10 pipeline_next calls, got {call_index['i']}"

    def test_phase_invalidation_across_transitions(self):
        """Session store invalidates old-phase sessions on phase change."""
        # Call flow:
        # 1. top-of-loop → confirm_ideation (IDEATE) → escalate → confirm
        # 2. post-escalation pipeline_next(confirm=True) → ignored response
        # 3. top-of-loop → confirm_plan (PLAN) → phase change invalidates IDEATE → escalate → confirm
        # 4. post-escalation pipeline_next(confirm=True) → ignored response
        # 5. top-of-loop → complete
        sequence = [
            _make_response("confirm_ideation", "IDEATE", 1, 3, "IDEATE_REVIEW"),
            _make_response("confirm_ideation", "IDEATE", 1, 3, "IDEATE_REVIEW"),  # ignored advance response
            _make_response("confirm_plan", "PLAN", 2, 3, "PLAN_REVIEW"),
            _make_response("confirm_plan", "PLAN", 2, 3, "PLAN_REVIEW"),  # ignored advance response
            _make_response("complete", "COMPLETE", 3, 3, "COMPLETE"),
        ]

        call_index = {"i": 0}
        phase_at_call = []

        def mock_pipeline_next(project_id=None, confirm=False, feedback=""):
            idx = call_index["i"]
            call_index["i"] += 1
            if idx < len(sequence):
                return sequence[idx]
            return _make_response("complete", "COMPLETE", 3, 3, "COMPLETE")

        escalation_count = {"i": 0}

        def mock_escalate(store, project_id, phase_key, prompt, rules, progress, working_dir, model="opus"):
            escalation_count["i"] += 1
            sid = f"sess-{escalation_count['i']}"
            store.set(project_id, phase_key, sid)
            return {"decision": "DECISION: confirm\nLooks good.", "session_id": sid}

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions.json")
            # Pre-seed an IDEATE session
            store.set("test-001", "IDEATE_REVIEW", "ideate-sess-original")

            with patch.object(qralph_cli, "pipeline_next", side_effect=mock_pipeline_next), \
                 patch.object(qralph_cli, "escalate", side_effect=mock_escalate), \
                 patch.object(qralph_cli, "spawn_work_agent", return_value="mocked"):

                qralph_cli.run_loop(
                    project_id="test-001",
                    working_dir=tmpdir,
                    session_store=store,
                )

            # After transitioning to PLAN, IDEATE sessions should be invalidated
            assert store.get("test-001", "IDEATE_REVIEW") is None
            # After transitioning to COMPLETE, PLAN sessions also invalidated
            assert store.get("test-001", "PLAN_REVIEW") is None
            # Both confirm gates triggered escalation
            assert escalation_count["i"] == 2


# ---------------------------------------------------------------------------
# Test: escalation session reuse within a phase
# ---------------------------------------------------------------------------

class TestEscalationSessionReuse:
    """Verify session reuse within the same phase."""

    def test_escalation_session_reuse_within_phase(self):
        """Two consecutive escalations in the same phase reuse the session ID."""
        # Call flow:
        # 1. top-of-loop → confirm_plan (escalate → confirm)
        # 2. post-escalation pipeline_next(confirm=True) → ignored
        # 3. top-of-loop → confirm_plan again (escalate → confirm, should reuse session)
        # 4. post-escalation pipeline_next(confirm=True) → ignored
        # 5. top-of-loop → complete
        sequence = [
            _make_response("confirm_plan", "PLAN", 1, 2, "PLAN_REVIEW"),
            _make_response("confirm_plan", "PLAN", 1, 2, "PLAN_REVIEW"),  # ignored advance
            _make_response("confirm_plan", "PLAN", 1, 2, "PLAN_REVIEW"),
            _make_response("confirm_plan", "PLAN", 1, 2, "PLAN_REVIEW"),  # ignored advance
            _make_response("complete", "COMPLETE", 2, 2, "COMPLETE"),
        ]

        call_index = {"i": 0}

        def mock_pipeline_next(project_id=None, confirm=False, feedback=""):
            idx = call_index["i"]
            call_index["i"] += 1
            if idx < len(sequence):
                return sequence[idx]
            return _make_response("complete", "COMPLETE", 2, 2, "COMPLETE")

        escalation_calls = []

        def mock_escalate(store, project_id, phase_key, prompt, rules, progress, working_dir, model="opus"):
            # Record what session was already stored before this call
            existing = store.get(project_id, phase_key)
            escalation_calls.append({
                "phase_key": phase_key,
                "existing_session": existing,
            })
            # First call returns sess-1, second returns sess-2
            sid = f"sess-{len(escalation_calls)}"
            # But the real escalate stores the session via store.set —
            # we simulate that here since we're mocking escalate entirely
            store.set(project_id, phase_key, sid)
            return {"decision": "DECISION: confirm\nOK.", "session_id": sid}

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions.json")

            with patch.object(qralph_cli, "pipeline_next", side_effect=mock_pipeline_next), \
                 patch.object(qralph_cli, "escalate", side_effect=mock_escalate), \
                 patch.object(qralph_cli, "spawn_work_agent", return_value="mocked"):

                qralph_cli.run_loop(
                    project_id="test-002",
                    working_dir=tmpdir,
                    session_store=store,
                )

            assert len(escalation_calls) == 2
            # First call: no existing session
            assert escalation_calls[0]["existing_session"] is None
            # Second call: should have the session from first call
            assert escalation_calls[1]["existing_session"] == "sess-1"


# ---------------------------------------------------------------------------
# Test: error action escalates then continues
# ---------------------------------------------------------------------------

class TestErrorActionEscalation:
    """Verify error actions are handled via escalation and the loop continues."""

    def test_error_action_escalates_then_continues(self):
        """Pipeline returns error, escalation confirms, loop continues to complete."""
        sequence = [
            # Error action
            _make_response("error", "PLAN", 1, 2, "PLAN_REVIEW",
                           description="Template scoring failed"),
            # After error handling, pipeline returns complete
            _make_response("complete", "COMPLETE", 2, 2, "COMPLETE"),
        ]

        call_index = {"i": 0}

        def mock_pipeline_next(project_id=None, confirm=False, feedback=""):
            idx = call_index["i"]
            call_index["i"] += 1
            if idx < len(sequence):
                return sequence[idx]
            return _make_response("complete", "COMPLETE", 2, 2, "COMPLETE")

        escalate_called = {"count": 0}

        def mock_escalate(store, project_id, phase_key, prompt, rules, progress, working_dir, model="opus"):
            escalate_called["count"] += 1
            return {"decision": "DECISION: confirm\nProceed despite error.", "session_id": "err-sess"}

        with tempfile.TemporaryDirectory() as tmpdir:
            store = SessionStore(Path(tmpdir) / "sessions.json")

            with patch.object(qralph_cli, "pipeline_next", side_effect=mock_pipeline_next), \
                 patch.object(qralph_cli, "escalate", side_effect=mock_escalate), \
                 patch.object(qralph_cli, "spawn_work_agent", return_value="mocked"):

                result = qralph_cli.run_loop(
                    project_id="test-003",
                    working_dir=tmpdir,
                    session_store=store,
                )

            # Loop should complete
            assert result["action"] == "complete"
            # Escalation should have been called for the error
            assert escalate_called["count"] == 1
            # pipeline_next should have been called at least 3 times:
            # 1. top of loop → error
            # 2. error handler feeds back → complete response
            # 3. top of loop (but wait — error handler calls pipeline_next internally,
            #    then loop continues and calls pipeline_next at top again)
            assert call_index["i"] >= 2
