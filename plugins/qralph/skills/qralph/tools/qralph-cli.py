#!/usr/bin/env python3
"""QRALPH CLI -- Deterministic pipeline orchestration with agentic escalation.

Drives the QRALPH state machine directly. Spawns claude -p sessions for
work (agent tasks) and decisions (gate confirmations). Reuses sessions
within phases to avoid context waste.

Usage:
    python3 qralph-cli.py run "<request>" [--mode thorough|quick] [--target-dir <path>]
    python3 qralph-cli.py resume --project <project_id>
    python3 qralph-cli.py status --project <project_id>
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Sibling module imports (hyphenated directory names need path manipulation)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from cli_escalation import SessionStore, escalate  # noqa: E402
from cli_handlers import classify_action, handle_spawn_agents  # noqa: E402
from cli_rules import get_rules  # noqa: E402

# ---------------------------------------------------------------------------
# Pipeline import -- load qralph-pipeline.py as a library
# ---------------------------------------------------------------------------
_pipeline_path = Path(__file__).parent / "qralph-pipeline.py"
_pipeline_spec = importlib.util.spec_from_file_location("qralph_pipeline", _pipeline_path)
_pipeline_mod = importlib.util.module_from_spec(_pipeline_spec)
_pipeline_spec.loader.exec_module(_pipeline_mod)


def pipeline_plan(request: str, target_dir: str | None = None, mode: str = "thorough") -> dict:
    """Wrapper around pipeline's cmd_plan for mockability."""
    return _pipeline_mod.cmd_plan(request, target_dir=target_dir, mode=mode)


def pipeline_next(project_id: str | None = None, confirm: bool = False, feedback: str = "") -> dict:
    """Wrapper around pipeline's cmd_next for mockability."""
    return _pipeline_mod.cmd_next(confirm=confirm, project_id=project_id, feedback=feedback)


# ---------------------------------------------------------------------------
# Work agent spawning
# ---------------------------------------------------------------------------

def spawn_work_agent(
    name: str,
    model: str,
    prompt: str,
    output_file: str,
    working_dir: str,
) -> str:
    """Spawn a single ``claude -p`` work agent via subprocess.

    Writes the agent's result to *output_file* (creating parent dirs as needed).
    Returns the output text.
    """
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--model", model]
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=working_dir,
        )
        output = json.loads(result.stdout)
        text = output.get("result", "")
    except Exception as exc:
        text = f"ERROR ({name}): {exc}"

    out_path.write_text(text)
    return text


def spawn_work_agents_parallel(agents: list[dict], working_dir: str) -> list[str]:
    """Run multiple work agents concurrently using asyncio."""

    async def _run_all() -> list[str]:
        current_loop = asyncio.get_event_loop()
        tasks = [
            current_loop.run_in_executor(
                None,
                spawn_work_agent,
                a["name"],
                a["model"],
                a["prompt"],
                a["output_file"],
                working_dir,
            )
            for a in agents
        ]
        return list(await asyncio.gather(*tasks))

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_all())
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_decision_context(response: dict, progress: dict) -> str:
    """Build context string from a pipeline response and progress info."""
    action_type = response.get("action", "unknown")
    parts = [f"Action type: {action_type}"]
    if "message" in response:
        parts.append(f"Message: {response['message']}")
    for key in ("template", "scores", "plan_path", "summary_path"):
        if key in response:
            parts.append(f"{key}: {json.dumps(response[key])}")
    if progress:
        parts.append(
            f"Phase: {progress.get('current_phase', '?')} "
            f"({progress.get('phase_index', 0)}/{progress.get('total_phases', 0)})"
        )
    return "\n".join(parts)


def _parse_decision(text: str) -> str:
    """Extract decision from agent response.

    Looks for a ``DECISION: <value>`` line. Falls back to ``escalate_to_user``
    as the safe default when no decision line is found.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("DECISION:"):
            return stripped.split(":", 1)[1].strip().lower()
    return "escalate_to_user"


def _print_status(msg: str) -> None:
    """Print a status message to stderr."""
    print(f"[qralph] {msg}", file=sys.stderr)


def _escalate_to_human(response: dict, agent_result: str) -> str:
    """Show context and agent assessment to human, return their input."""
    _print_status("=== HUMAN DECISION REQUIRED ===")
    _print_status(f"Action: {response.get('action', 'unknown')}")
    if "message" in response:
        _print_status(f"Context: {response['message']}")
    if agent_result:
        _print_status(f"Agent assessment:\n{agent_result}")
    _print_status("===============================")
    return input("[qralph] Your input (Enter to continue): ")


def _run_escalation(
    response: dict,
    progress: dict,
    sub_phase: str,
    session_store: SessionStore,
    project_id: str,
    working_dir: str,
) -> str:
    """Escalate to decision agent and return the parsed decision.

    Consolidates the shared escalation logic used by both error handling
    and decision-agent gate confirmation in run_loop.
    """
    rules = get_rules(sub_phase)
    ctx = _build_decision_context(response, progress)
    result = escalate(
        store=session_store,
        project_id=project_id,
        phase_key=sub_phase,
        prompt=ctx,
        rules=rules,
        progress=progress,
        working_dir=working_dir,
    )
    decision = _parse_decision(result.get("decision", ""))

    if decision == "escalate_to_user":
        human_input = _escalate_to_human(response, result.get("decision", ""))
        pipeline_next(project_id=project_id, feedback=human_input)
    elif decision == "confirm":
        pipeline_next(project_id=project_id, confirm=True)
    elif decision == "reject":
        reason = result.get("decision", "Rejected by decision agent")
        pipeline_next(project_id=project_id, feedback=reason)
    else:
        _print_status(f"Unknown decision: {decision}")
        input("[qralph] Press Enter to continue...")
        pipeline_next(project_id=project_id, confirm=True)

    return decision


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------

def run_loop(
    project_id: str,
    working_dir: str,
    session_store: SessionStore | None = None,
) -> dict:
    """Drive the pipeline to completion.

    Returns the final ``complete`` action dict.
    """
    if session_store is None:
        store_path = Path(working_dir) / ".qralph" / "cli-sessions.json"
        session_store = SessionStore(store_path)

    last_phase: str | None = None

    while True:
        response = pipeline_next(project_id=project_id)
        action_type = response.get("action", "")
        progress = response.get("phase_progress", {})
        sub_phase = progress.get("sub_phase", "")
        current_phase = progress.get("current_phase", "")

        # Phase change -- invalidate stale sessions
        if current_phase and current_phase != last_phase:
            if last_phase is not None:
                session_store.advance_phase(project_id, current_phase)
            last_phase = current_phase

        category = classify_action(response)

        # ---- complete ----
        if action_type == "complete":
            _print_status(f"Project {project_id} complete.")
            return response

        # ---- deterministic ----
        if category == "deterministic":
            _print_status(f"Auto-advancing: {action_type}")
            if action_type.startswith("confirm_"):
                pipeline_next(project_id=project_id, confirm=True)
            continue

        # ---- work_agent ----
        if category == "work_agent":
            agent_configs = handle_spawn_agents(response, working_dir)
            _print_status(f"Spawning {len(agent_configs)} work agent(s)")
            if len(agent_configs) == 1:
                spawn_work_agent(**agent_configs[0], working_dir=working_dir)
            elif len(agent_configs) > 1:
                spawn_work_agents_parallel(agent_configs, working_dir)
            pipeline_next(project_id=project_id, confirm=True)
            continue

        # ---- decision_agent (includes error and escalate_to_user) ----
        _run_escalation(
            response=response,
            progress=progress,
            sub_phase=sub_phase,
            session_store=session_store,
            project_id=project_id,
            working_dir=working_dir,
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_EPILOG = """\
examples:

  Start a new project (thorough mode, default):
    qralph run "Add user authentication with OAuth2"

  Start a new project in quick mode (skips ideation/personas/concept):
    qralph run "Fix the login redirect bug" --mode quick

  Target a specific directory for implementation files:
    qralph run "Build a landing page" --target-dir ./projects/landing

  Resume a project that was interrupted:
    qralph resume --project 025-dashboard-error-ux

  Check where a project left off:
    qralph status --project 025-dashboard-error-ux

how it works:

  The CLI drives QRALPH's state machine directly — no LLM orchestrator.
  At each step, it classifies the pipeline's response:

    deterministic   Auto-advances (file I/O, high-confidence gates)
    work_agent      Spawns claude -p to do creative work (code, analysis)
    decision_agent  Spawns claude -p with step-specific rules to decide
    human           Only when the decision agent explicitly escalates

  Decision agent sessions are reused within a phase (via --resume) so
  context isn't wasted. Phase transitions invalidate old sessions.

modes:

  thorough (default)
    IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → ...
    Full lifecycle with brainstorming, personas, and concept review.
    Best for greenfield features and non-technical users.

  quick
    PLAN → EXECUTE → SIMPLIFY → VERIFY → DEMO → DEPLOY → SMOKE → LEARN
    Skips ideation phases. Best for developers who know what they want.

recovery:

  State is checkpointed at every phase transition. If the CLI crashes
  or is interrupted, resume picks up exactly where it left off:
    qralph resume --project <project_id>

  Project IDs are printed at startup and stored in:
    .qralph/projects/<project_id>/state.json
"""


def main() -> None:
    """Parse CLI arguments and dispatch."""
    parser = argparse.ArgumentParser(
        prog="qralph",
        description="QRALPH CLI — deterministic pipeline orchestration with agentic escalation",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- run ---
    run_parser = subparsers.add_parser(
        "run",
        help="Start a new project and run the pipeline to completion",
        description="Initialize a QRALPH project and drive it through all phases.",
        epilog=(
            "examples:\n"
            '  qralph run "Add OAuth2 authentication"\n'
            '  qralph run "Fix login bug" --mode quick\n'
            '  qralph run "Build landing page" --target-dir ./projects/landing\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_parser.add_argument(
        "request",
        help="What to build — a plain-language description of the project",
    )
    run_parser.add_argument(
        "--mode",
        choices=["thorough", "quick"],
        default="thorough",
        help="Pipeline mode: thorough (full lifecycle, default) or quick (skip ideation)",
    )
    run_parser.add_argument(
        "--target-dir",
        default=None,
        help="Directory for implementation files (default: current directory)",
    )

    # --- resume ---
    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume an interrupted project from its last checkpoint",
        description=(
            "Resume a project that was interrupted. State is checkpointed at\n"
            "every phase transition, so this picks up exactly where it left off."
        ),
        epilog=(
            "examples:\n"
            "  qralph resume --project 025-dashboard-error-ux\n"
            "  qralph resume --project 014-redesign-checkout-flow\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    resume_parser.add_argument(
        "--project",
        required=True,
        dest="project_id",
        metavar="PROJECT_ID",
        help="Project ID to resume (printed at startup, or find in .qralph/projects/)",
    )

    # --- status ---
    status_parser = subparsers.add_parser(
        "status",
        help="Show current phase, progress, and state for a project",
        description="Display the current state of a QRALPH project as JSON.",
        epilog=(
            "examples:\n"
            "  qralph status --project 025-dashboard-error-ux\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    status_parser.add_argument(
        "--project",
        required=True,
        dest="project_id",
        metavar="PROJECT_ID",
        help="Project ID to check",
    )

    args = parser.parse_args()

    if args.command == "run":
        target_dir = args.target_dir or str(Path.cwd())
        plan_result = pipeline_plan(args.request, target_dir=target_dir, mode=args.mode)
        project_id = plan_result.get("project_id", "")
        if not project_id:
            _print_status(f"Plan failed: {plan_result}")
            sys.exit(1)
        _print_status(f"Project {project_id} created. Starting loop.")
        run_loop(project_id=project_id, working_dir=target_dir)

    elif args.command == "resume":
        wd = str(Path.cwd())
        run_loop(project_id=args.project_id, working_dir=wd)

    elif args.command == "status":
        result = _pipeline_mod.cmd_status(project_id=args.project_id)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
