"""Pipeline driver for /qpipeline skill.

Manages composable multi-phase workflows with presets, compositional
integrity validation, checkpointing, and gate-based transitions.

Usage:
    python tools/pipeline-driver.py init --preset PRESET [--artifact PATH] [--requirements PATH] [--phases LIST] [--threshold N] [--max-rounds N]
    python tools/pipeline-driver.py next [--confirm]
    python tools/pipeline-driver.py status
    python tools/pipeline-driver.py resume --project PROJECT_ID
    python tools/pipeline-driver.py reset
    python tools/pipeline-driver.py record-result --phase PHASE --result-file PATH [--project PROJECT_ID]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_ROOT = ".qpipeline"
PROJECTS_DIR = "projects"

PRESETS: dict[str, list[str]] = {
    "review": ["test-gate", "review-loop", "verify"],
    "thorough": [
        "ideate", "plan", "execute", "review-loop",
        "test-gate", "verify", "demo",
    ],
    "content": ["review-loop", "verify"],
    "code": ["review-loop", "test-gate", "verify"],
}

ALL_PHASE_TYPES: list[str] = [
    "ideate", "plan", "execute",
    "review", "review-loop",
    "test-gate", "verify", "demo",
    "deploy", "smoke", "learn",
    "fix", "re-review", "converge",
]

GATE_PHASES: set[str] = {"ideate", "plan", "demo", "deploy"}

# Phases that produce changes and therefore require review-loop.
MUTATION_PHASES: set[str] = {"execute", "fix"}

VALID_STATUSES: list[str] = [
    "initialized",
    "running",
    "gate-pending",
    "converged",
    "escalated",
    "failed",
]

# Action mapping: phase type -> action name
PHASE_ACTIONS: dict[str, str] = {
    "ideate": "gate",
    "plan": "gate",
    "execute": "execute_plan",
    "review": "spawn_reviewers",
    "review-loop": "run_loop",
    "test-gate": "run_tests",
    "verify": "spawn_verifier",
    "demo": "gate",
    "deploy": "gate",
    "smoke": "run_smoke",
    "learn": "extract_learnings",
    "fix": "apply_fixes",
    "re-review": "spawn_reviewers",
    "converge": "check_convergence",
}

GATE_MESSAGES: dict[str, str] = {
    "ideate": "Review the ideation output and confirm the concept to proceed.",
    "plan": "Review the implementation plan and confirm to proceed.",
    "demo": "Review the completed work. Approve to proceed or provide feedback (max 2 revision cycles).",
    "deploy": "All pre-deployment checks passed. Confirm deployment to proceed.",
}


# ---------------------------------------------------------------------------
# State directory helpers
# ---------------------------------------------------------------------------

def _projects_dir(base: str | None = None) -> Path:
    root = Path(base) if base else Path.cwd()
    return root / STATE_ROOT / PROJECTS_DIR


_PROJECT_ID_RE = re.compile(r"^[0-9]{3}-[a-z0-9][a-z0-9-]{0,40}$")


def _validate_project_id(project_id: str) -> None:
    if not _PROJECT_ID_RE.match(project_id):
        raise ValueError(
            f"Invalid project_id '{project_id}'; "
            f"expected format NNN-slug (e.g. 001-my-project)."
        )


def _project_dir(project_id: str, base: str | None = None) -> Path:
    _validate_project_id(project_id)
    return _projects_dir(base) / project_id


def _state_path(project_id: str, base: str | None = None) -> Path:
    return _project_dir(project_id, base) / "state.json"


def _find_active_project(base: str | None = None) -> str | None:
    """Find the most recently updated non-terminal project."""
    pdir = _projects_dir(base)
    if not pdir.exists():
        return None
    terminal_statuses = {"converged", "failed", "escalated"}
    candidates: list[tuple[str, str]] = []
    for child in pdir.iterdir():
        if child.is_dir():
            state_file = child / "state.json"
            if state_file.exists():
                try:
                    with open(state_file, "r", encoding="utf-8") as fh:
                        state = json.load(fh)
                except (json.JSONDecodeError, OSError):
                    continue
                if state.get("status") in terminal_statuses:
                    continue
                updated_at = state.get("updated_at", "")
                candidates.append((updated_at, child.name))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def _read_state(project_id: str, base: str | None = None) -> dict[str, Any]:
    path = _state_path(project_id, base)
    if not path.exists():
        raise FileNotFoundError(
            f"No pipeline state for project '{project_id}' at {path}."
        )
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Corrupt state file for project '{project_id}' at {path}: {exc}. "
                f"Delete the file or run reset to recover."
            ) from exc


def _write_state(state: dict[str, Any], base: str | None = None) -> None:
    project_id = state["project_id"]
    d = _project_dir(project_id, base)
    d.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    target = _state_path(project_id, base)
    fd, tmp_path = tempfile.mkstemp(dir=str(d), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, default=str)
        os.replace(tmp_path, str(target))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Project ID generation
# ---------------------------------------------------------------------------

def _next_project_number(base: str | None = None) -> int:
    """Return the next available NNN project number.

    Checks for directory existence to avoid collisions from concurrent calls.
    """
    pdir = _projects_dir(base)
    if not pdir.exists():
        return 1
    max_num = 0
    for child in pdir.iterdir():
        if child.is_dir():
            match = re.match(r"^(\d{3})-", child.name)
            if match:
                max_num = max(max_num, int(match.group(1)))
    # Guard against concurrent init: if the computed dir already exists, increment
    candidate = max_num + 1
    while (pdir / f"{candidate:03d}-").exists() or any(
        c.is_dir() and c.name.startswith(f"{candidate:03d}-") for c in pdir.iterdir()
    ):
        candidate += 1
    return candidate


def _slugify(name: str) -> str:
    """Convert a name into a URL-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    slug = slug.strip("-")
    return slug[:40] if slug else "project"


def generate_project_id(
    artifact_path: str | None = None,
    base: str | None = None,
) -> str:
    """Generate a project ID in NNN-slug format."""
    num = _next_project_number(base)
    if artifact_path:
        name = Path(artifact_path).stem
    else:
        name = "pipeline"
    slug = _slugify(name)
    return f"{num:03d}-{slug}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_phases(phases: list[str]) -> tuple[bool, list[str]]:
    """Validate a phase list for compositional integrity.

    Rules:
    - All phases must be recognized types.
    - Any pipeline with execute or fix MUST also have review-loop.

    Returns (valid, errors).
    """
    errors: list[str] = []

    for phase in phases:
        if phase not in ALL_PHASE_TYPES:
            errors.append(f"unrecognized phase type: '{phase}'")

    # Reject duplicate phase names — phase_results is keyed by name
    seen: set[str] = set()
    for phase in phases:
        if phase in seen:
            errors.append(f"duplicate phase '{phase}' — each phase name must appear once")
        seen.add(phase)

    phase_set = set(phases)
    mutation_present = phase_set & MUTATION_PHASES
    if mutation_present and "review-loop" not in phase_set:
        errors.append(
            f"phases {sorted(mutation_present)} require 'review-loop' "
            f"in the pipeline (compositional integrity)"
        )

    # Ordering: mutation phases must come before review-loop
    if mutation_present and "review-loop" in phase_set:
        review_idx = phases.index("review-loop")
        for mp in sorted(mutation_present):
            if mp in phases:
                mp_idx = phases.index(mp)
                if mp_idx > review_idx:
                    errors.append(
                        f"phase '{mp}' must come before 'review-loop' "
                        f"(found at index {mp_idx}, review-loop at {review_idx})"
                    )

    return (not errors, errors)


# ---------------------------------------------------------------------------
# Checkpointing
# ---------------------------------------------------------------------------

def _save_checkpoint(state: dict[str, Any], base: str | None = None) -> None:
    """Save a checkpoint of the current state."""
    checkpoint = {
        "phase_index": state["current_phase_index"],
        "phase": state["current_phase"],
        "status": state["status"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase_results_snapshot": dict(state.get("phase_results", {})),
    }
    state.setdefault("checkpoints", []).append(checkpoint)
    _write_state(state, base)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def init_pipeline(
    preset: str | None = None,
    phases: list[str] | None = None,
    artifact_path: str | None = None,
    requirements_path: str | None = None,
    base_dir: str | None = None,
    convergence_threshold: int | None = None,
    max_rounds: int | None = None,
) -> dict[str, Any]:
    """Initialize a new pipeline.

    Either preset or phases must be provided. If both are given,
    phases takes precedence.
    """
    if phases is not None:
        phase_list = list(phases)
    elif preset is not None:
        if preset not in PRESETS:
            raise ValueError(
                f"Unknown preset '{preset}'. "
                f"Available: {sorted(PRESETS.keys())}"
            )
        phase_list = list(PRESETS[preset])
    else:
        phase_list = list(PRESETS["review"])

    valid, errors = validate_phases(phase_list)
    if not valid:
        raise ValueError(
            f"Invalid phase composition: {'; '.join(errors)}"
        )

    artifact_abs: str | None = None
    if artifact_path:
        artifact_abs = str(Path(artifact_path).resolve())

    requirements_abs: str | None = None
    if requirements_path:
        requirements_abs = str(Path(requirements_path).resolve())

    project_id = generate_project_id(artifact_path, base_dir)

    state: dict[str, Any] = {
        "project_id": project_id,
        "preset": preset or "custom",
        "phases": phase_list,
        "current_phase_index": 0,
        "current_phase": phase_list[0],
        "artifact_path": artifact_abs,
        "requirements_path": requirements_abs,
        "phase_results": {},
        "checkpoints": [],
        "gates_pending": [],
        "status": "initialized",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if convergence_threshold is not None:
        state["convergence_threshold"] = convergence_threshold
    if max_rounds is not None:
        state["max_rounds"] = max_rounds

    _write_state(state, base_dir)
    return state


def _build_action(state: dict[str, Any]) -> dict[str, Any]:
    """Build the action dict for the current phase."""
    phase = state["current_phase"]
    action_name = PHASE_ACTIONS.get(phase, "unknown")

    action: dict[str, Any] = {
        "action": action_name,
        "phase": phase,
        "phase_index": state["current_phase_index"],
        "total_phases": len(state["phases"]),
    }

    if phase in GATE_PHASES:
        action["message"] = GATE_MESSAGES.get(phase, f"Gate: confirm to proceed past {phase}.")

    if phase == "review-loop":
        action["loop_config"] = {
            "max_rounds": state.get("max_rounds", 5),
            "convergence_threshold": state.get("convergence_threshold", 0),
        }

    if state.get("artifact_path"):
        action["artifact_path"] = state["artifact_path"]
    if state.get("requirements_path"):
        action["requirements_path"] = state["requirements_path"]

    return action


def next_action(
    state: dict[str, Any],
    confirm: bool = False,
    base_dir: str | None = None,
) -> dict[str, Any]:
    """Determine and return the next action for the pipeline.

    If a gate is pending and confirm is False, return the gate info.
    If a gate is pending and confirm is True, advance past the gate.
    If the current phase has no recorded result, return its action again.

    Uses an iterative loop instead of recursion to avoid stack overflow
    on pipelines with many pre-completed phases.
    """
    while True:
        phases = state["phases"]
        idx = state["current_phase_index"]

        # Validate index bounds
        if idx < 0 or idx > len(phases):
            raise ValueError(
                f"Corrupt phase index {idx} for {len(phases)} phases. Run reset."
            )

        # Pipeline complete?
        if idx >= len(phases):
            return {
                "action": "complete",
                "summary": f"Pipeline '{state['project_id']}' completed all {len(phases)} phases.",
                "phase_results": state.get("phase_results", {}),
            }

        current_phase = phases[idx]
        state["current_phase"] = current_phase

        # Gate pending?
        if state["status"] == "gate-pending":
            if confirm:
                state["status"] = "running"
                state["gates_pending"] = [
                    g for g in state.get("gates_pending", [])
                    if g != current_phase
                ]
                # Gate confirmed -> record phase result and advance
                state["phase_results"][current_phase] = {
                    "status": "gate-confirmed",
                    "confirmed_at": datetime.now(timezone.utc).isoformat(),
                }
                state["current_phase_index"] = idx + 1
                _save_checkpoint(state, base_dir)
                # Continue loop instead of recursing
                confirm = False
                continue
            else:
                action = _build_action(state)
                action["gate_pending"] = True
                return action

        # Current phase already has a result? Advance.
        if current_phase in state.get("phase_results", {}):
            state["current_phase_index"] = idx + 1
            _save_checkpoint(state, base_dir)
            # Continue loop instead of recursing
            continue

        # Gate phase with no result -> set gate-pending
        if current_phase in GATE_PHASES:
            state["status"] = "gate-pending"
            pending = state.setdefault("gates_pending", [])
            if current_phase not in pending:
                pending.append(current_phase)
            _write_state(state, base_dir)
            action = _build_action(state)
            action["gate_pending"] = True
            return action

        # Non-gate phase with no result -> return its action
        state["status"] = "running"
        _write_state(state, base_dir)
        return _build_action(state)


def record_phase_result(
    state: dict[str, Any],
    phase: str,
    result: dict[str, Any],
    base_dir: str | None = None,
) -> dict[str, Any]:
    """Record the outcome of a phase. Returns updated state.

    Validates result content for critical phases (test-gate must pass).
    Gate phases (ideate, plan, demo, deploy) cannot be recorded directly.
    """
    if phase in GATE_PHASES:
        raise ValueError(
            f"Gate phase '{phase}' cannot be recorded directly. "
            f"Use next_action(confirm=True) to advance past gates."
        )

    if phase == "test-gate" and not result.get("all_passed", False):
        raise ValueError(
            "test-gate result has all_passed=False; cannot record a "
            "failing test-gate. Fix test failures and re-run."
        )

    if phase == "verify":
        verdict = result.get("verdict", result.get("passed", None))
        if verdict not in (True, "PASS", "pass"):
            raise ValueError(
                f"verify result requires passing verdict (True, 'PASS'); "
                f"got {verdict!r}. Fix issues and re-verify."
            )

    if phase == "review-loop":
        is_escalated = result.get("status") in ("escalated", "failed")
        if not result.get("converged", False) and not is_escalated:
            raise ValueError(
                "review-loop result must have converged=True or "
                "status='escalated'/'failed' to advance; "
                "got converged={!r}, status={!r}.".format(
                    result.get("converged"), result.get("status")
                )
            )

    phases = state.get("phases", [])
    if phase not in phases:
        raise ValueError(
            f"phase '{phase}' is not in the pipeline's phase list: {phases}"
        )
    current_idx = state.get("current_phase_index", 0)
    phase_idx = phases.index(phase)
    if phase_idx != current_idx:
        raise ValueError(
            f"Cannot record result for phase '{phase}' "
            f"(index {phase_idx}); current phase is "
            f"'{phases[current_idx]}' (index {current_idx}). "
            f"Results can only be recorded for the current phase."
        )

    state["phase_results"][phase] = result
    _write_state(state, base_dir)
    return state


def get_status(
    project_id: str | None = None,
    base_dir: str | None = None,
) -> dict[str, Any]:
    """Read and return pipeline status."""
    if project_id is None:
        project_id = _find_active_project(base_dir)
        if project_id is None:
            raise FileNotFoundError("No active pipeline project found.")

    state = _read_state(project_id, base_dir)

    phases = state.get("phases", [])
    idx = state.get("current_phase_index", 0)
    completed = len(state.get("phase_results", {}))

    return {
        "project_id": state["project_id"],
        "preset": state.get("preset", "unknown"),
        "status": state.get("status", "unknown"),
        "current_phase": state.get("current_phase", "none"),
        "current_phase_index": idx,
        "total_phases": len(phases),
        "phases_completed": completed,
        "phases": phases,
        "phase_results": state.get("phase_results", {}),
        "gates_pending": state.get("gates_pending", []),
        "checkpoints": len(state.get("checkpoints", [])),
    }


def resume(
    project_id: str,
    base_dir: str | None = None,
) -> dict[str, Any]:
    """Load state from disk and return the next action."""
    state = _read_state(project_id, base_dir)
    return next_action(state, confirm=False, base_dir=base_dir)


def reset(
    project_id: str | None = None,
    base_dir: str | None = None,
) -> None:
    """Clear pipeline state for a project, or all projects."""
    if project_id:
        d = _project_dir(project_id, base_dir)
        if d.exists():
            shutil.rmtree(d)
    else:
        root = Path(base_dir) if base_dir else Path.cwd()
        d = root / STATE_ROOT
        if d.exists():
            shutil.rmtree(d)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pipeline driver for /qpipeline skill.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # init
    init_p = subparsers.add_parser("init", help="Initialize a pipeline")
    init_p.add_argument(
        "--preset", default=None,
        help=f"Preset name: {', '.join(sorted(PRESETS.keys()))}",
    )
    init_p.add_argument("--artifact", default=None, help="Path to artifact")
    init_p.add_argument("--requirements", default=None, help="Path to requirements")
    init_p.add_argument(
        "--phases", default=None,
        help="Comma-separated custom phase list",
    )
    init_p.add_argument(
        "--threshold", type=int, default=None,
        help="Convergence threshold for review-loop (default: 0)",
    )
    init_p.add_argument(
        "--max-rounds", type=int, default=None,
        help="Max review-loop rounds (default: 5)",
    )

    # next
    next_p = subparsers.add_parser("next", help="Get next action")
    next_p.add_argument(
        "--confirm", action="store_true",
        help="Confirm a pending gate",
    )
    next_p.add_argument("--project", default=None, help="Project ID")

    # status
    status_p = subparsers.add_parser("status", help="Show pipeline status")
    status_p.add_argument("--project", default=None, help="Project ID")

    # resume
    resume_p = subparsers.add_parser("resume", help="Resume a pipeline")
    resume_p.add_argument("--project", required=True, help="Project ID")

    # reset
    reset_p = subparsers.add_parser("reset", help="Clear pipeline state")
    reset_p.add_argument("--project", default=None, help="Project ID (omit to clear all)")

    # record-result
    record_p = subparsers.add_parser("record-result", help="Record a phase result")
    record_p.add_argument("--phase", required=True, help="Phase name to record result for")
    record_p.add_argument("--result-file", required=True, help="Path to JSON file with result data")
    record_p.add_argument("--project", default=None, help="Project ID")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "init":
        phases_list: list[str] | None = None
        if args.phases:
            phases_list = [p.strip() for p in args.phases.split(",")]
        try:
            state = init_pipeline(
                preset=args.preset,
                phases=phases_list,
                artifact_path=args.artifact,
                requirements_path=args.requirements,
                convergence_threshold=args.threshold,
                max_rounds=args.max_rounds,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(state, indent=2, default=str))
        return 0

    if args.command == "next":
        project_id = getattr(args, "project", None) or _find_active_project()
        if not project_id:
            print("Error: no active project found.", file=sys.stderr)
            return 1
        try:
            state = _read_state(project_id)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        action = next_action(state, confirm=args.confirm)
        print(json.dumps(action, indent=2, default=str))
        return 0

    if args.command == "status":
        try:
            status = get_status(project_id=getattr(args, "project", None))
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(status, indent=2, default=str))
        return 0

    if args.command == "resume":
        try:
            action = resume(args.project)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(action, indent=2, default=str))
        return 0

    if args.command == "reset":
        reset(project_id=getattr(args, "project", None))
        print("Pipeline state cleared.")
        return 0

    if args.command == "record-result":
        project_id = getattr(args, "project", None) or _find_active_project()
        if not project_id:
            print("Error: no active project found.", file=sys.stderr)
            return 1
        result_path = Path(args.result_file)
        if not result_path.exists():
            print(f"Error: result file not found: {args.result_file}", file=sys.stderr)
            return 1
        try:
            with open(result_path, "r", encoding="utf-8") as fh:
                result_data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Error reading result file: {exc}", file=sys.stderr)
            return 1
        try:
            state = _read_state(project_id)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        try:
            record_phase_result(state, args.phase, result_data)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Recorded result for phase '{args.phase}' in project '{project_id}'.")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
