#!/usr/bin/env python3
"""
QRALPH Session State Manager - STATE.md lifecycle, session persistence, CLAUDE.md injection.

Implements PRD requirements REQ-STATE-001 through REQ-STATE-007.

Commands:
    python3 session-state.py create-state <project-id>     # REQ-STATE-001
    python3 session-state.py session-start                  # REQ-STATE-004
    python3 session-state.py session-end <project-id>       # REQ-STATE-005
    python3 session-state.py recover <project-id>           # REQ-STATE-006
    python3 session-state.py inject-claude-md [path]        # REQ-STATE-003
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import shared state module
import importlib.util
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

safe_write = qralph_state.safe_write
safe_write_json = qralph_state.safe_write_json
safe_read_json = qralph_state.safe_read_json

# Constants
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
PROJECTS_DIR = QRALPH_DIR / "projects"
CURRENT_PROJECT_FILE = QRALPH_DIR / "current-project.json"

# QRALPH execution phases
QRALPH_PHASES = [
    "INIT", "DISCOVERING", "REVIEWING", "EXECUTING", "UAT", "COMPLETE",
]

CLAUDE_MD_SECTION_HEADER = "## QRALPH Project State"


def _get_project_path(project_id: str) -> Optional[Path]:
    """Resolve project path from ID or partial match."""
    if not PROJECTS_DIR.exists():
        return None
    matches = list(PROJECTS_DIR.glob(f"{project_id}*"))
    return matches[0] if matches else None


def _get_state_md_path(project_path: Path) -> Path:
    return project_path / "STATE.md"


def _get_git_diff_stat() -> str:
    """Get git diff --stat output for uncommitted work detection."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _get_git_log_oneline(n: int = 5) -> str:
    """Get recent git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{n}"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _format_checklist(phases: List[str], current_phase: str) -> str:
    """Generate markdown checklist from phases."""
    lines = []
    phase_reached = False
    for phase in phases:
        if phase == current_phase:
            phase_reached = True
            lines.append(f"- [ ] **{phase}** (current)")
        elif not phase_reached:
            lines.append(f"- [x] {phase}")
        else:
            lines.append(f"- [ ] {phase}")
    return "\n".join(lines)


def cmd_create_state(project_id: str):
    """
    REQ-STATE-001: Create STATE.md for a project.

    Creates STATE.md with Meta, Execution Plan, Current Step Detail,
    Uncommitted Work, Session Log, and Next Session Instructions sections.
    """
    project_path = _get_project_path(project_id)
    if not project_path:
        print(json.dumps({"error": f"Project not found: {project_id}"}))
        return

    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    state_md_path = _get_state_md_path(project_path)

    # Don't overwrite existing STATE.md (idempotent)
    if state_md_path.exists():
        print(json.dumps({
            "status": "exists",
            "state_file": str(state_md_path),
            "message": "STATE.md already exists",
        }))
        return

    now = datetime.now().isoformat()
    request = state.get("request", "")
    mode = state.get("mode", "coding")
    current_phase = state.get("phase", "INIT")
    agents = state.get("agents", [])

    checklist = _format_checklist(QRALPH_PHASES, current_phase)

    state_md = f"""# QRALPH Project State: {project_id}

## Meta

| Field | Value |
|-------|-------|
| Project ID | {project_id} |
| Request | {request} |
| Mode | {mode} |
| Created | {state.get('created_at', now)} |
| Last Updated | {now} |
| Status | active |

## Execution Plan

{checklist}

## Current Step Detail

**Phase**: {current_phase}
**Agents**: {', '.join(agents) if agents else 'Not yet selected'}
**Notes**: Initial state created

## Uncommitted Work

_No uncommitted work detected._

## Session Log

| Session | Date | Duration | Phase Start | Phase End | Notes |
|---------|------|----------|-------------|-----------|-------|
| 1 | {datetime.now().strftime('%Y-%m-%d')} | - | {current_phase} | {current_phase} | State created |

## Next Session Instructions

1. Read this STATE.md at session start
2. Check current phase and continue from where you left off
3. Review any uncommitted work alerts
4. Update checklist as phases complete

---
*Generated by session-state.py at {now}*
"""

    safe_write(state_md_path, state_md)

    # Update current-project.json with state_file reference
    if state:
        rel_path = str(state_md_path.relative_to(PROJECT_ROOT))
        state["state_file"] = rel_path
        state["title"] = request[:80] if request else project_id
        state["last_session"] = now
        state["total_steps"] = len(QRALPH_PHASES)
        state["current_step"] = QRALPH_PHASES.index(current_phase) + 1 if current_phase in QRALPH_PHASES else 1
        safe_write_json(CURRENT_PROJECT_FILE, state)

    output = {
        "status": "created",
        "state_file": str(state_md_path),
        "project_id": project_id,
        "phase": current_phase,
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_session_start():
    """
    REQ-STATE-004: Output session context on start.

    Reads current-project.json then STATE.md, outputs JSON summary
    (<2000 tokens) with next instructions, step progress, uncommitted work alerts.
    """
    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    if not state:
        output = {
            "status": "no_active_project",
            "message": "No active QRALPH project. Run QRALPH init first.",
        }
        print(json.dumps(output))
        return output

    project_id = state.get("project_id", "unknown")
    project_path = _get_project_path(project_id)

    if not project_path:
        output = {
            "status": "project_missing",
            "project_id": project_id,
            "message": f"Project directory not found for {project_id}",
        }
        print(json.dumps(output))
        return output

    state_md_path = _get_state_md_path(project_path)

    # Check for uncommitted work
    git_diff = _get_git_diff_stat()
    uncommitted_alert = bool(git_diff)

    # Parse STATE.md for next instructions
    next_instructions = ""
    if state_md_path.exists():
        try:
            content = state_md_path.read_text()
            match = re.search(r'## Next Session Instructions\s*\n(.*?)(?=\n---|\Z)', content, re.DOTALL)
            if match:
                next_instructions = match.group(1).strip()
        except Exception:
            pass

    phase = state.get("phase", "INIT")
    total_steps = len(QRALPH_PHASES)
    current_step = QRALPH_PHASES.index(phase) + 1 if phase in QRALPH_PHASES else 0

    output = {
        "status": "session_started",
        "project_id": project_id,
        "request": state.get("request", "")[:200],
        "mode": state.get("mode", "coding"),
        "phase": phase,
        "progress": f"{current_step}/{total_steps}",
        "agents": state.get("agents", []),
        "heal_attempts": state.get("heal_attempts", 0),
        "uncommitted_work": uncommitted_alert,
        "uncommitted_details": git_diff[:500] if git_diff else None,
        "next_instructions": next_instructions[:1500],
        "state_file": str(state_md_path),
    }

    print(json.dumps(output, indent=2))
    return output


def cmd_session_end(project_id: str):
    """
    REQ-STATE-005: Update STATE.md on session end.

    Updates checkboxes, advances step if complete, populates uncommitted work
    from git diff --stat, appends session log row, writes next instructions.
    """
    project_path = _get_project_path(project_id)
    if not project_path:
        print(json.dumps({"error": f"Project not found: {project_id}"}))
        return

    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    state_md_path = _get_state_md_path(project_path)

    if not state_md_path.exists():
        cmd_create_state(project_id)

    now = datetime.now()
    phase = state.get("phase", "INIT")
    git_diff = _get_git_diff_stat()

    # Read current STATE.md
    try:
        content = state_md_path.read_text()
    except Exception:
        content = ""

    # Update checklist
    new_checklist = _format_checklist(QRALPH_PHASES, phase)
    content = re.sub(
        r'## Execution Plan\s*\n(.*?)(?=\n## )',
        f"## Execution Plan\n\n{new_checklist}\n\n",
        content, flags=re.DOTALL
    )

    # Update current step detail
    agents = state.get("agents", [])
    step_detail = f"""**Phase**: {phase}
**Agents**: {', '.join(agents) if agents else 'Not yet selected'}
**Notes**: Session ended at {now.strftime('%H:%M:%S')}"""

    content = re.sub(
        r'## Current Step Detail\s*\n(.*?)(?=\n## )',
        f"## Current Step Detail\n\n{step_detail}\n\n",
        content, flags=re.DOTALL
    )

    # Update uncommitted work
    if git_diff:
        uncommitted = f"**Warning**: Uncommitted changes detected:\n\n```\n{git_diff}\n```\n"
    else:
        uncommitted = "_No uncommitted work detected._\n"

    content = re.sub(
        r'## Uncommitted Work\s*\n(.*?)(?=\n## )',
        f"## Uncommitted Work\n\n{uncommitted}\n",
        content, flags=re.DOTALL
    )

    # Append session log row
    session_count = content.count("| ") - 2  # subtract header rows
    session_count = max(session_count, 1)
    log_row = f"| {session_count} | {now.strftime('%Y-%m-%d')} | - | {phase} | {phase} | Session end |\n"

    # Insert before the closing --- in the session log
    content = re.sub(
        r'(## Session Log.*?)(---)',
        lambda m: m.group(1) + log_row + "\n" + m.group(2),
        content, flags=re.DOTALL
    )

    # Update next session instructions
    next_phase_idx = QRALPH_PHASES.index(phase) + 1 if phase in QRALPH_PHASES else 0
    next_phase = QRALPH_PHASES[next_phase_idx] if next_phase_idx < len(QRALPH_PHASES) else "COMPLETE"

    next_instructions = f"""1. Read this STATE.md at session start
2. Current phase: **{phase}** - continue from here
3. Next expected phase: **{next_phase}**"""

    if git_diff:
        next_instructions += "\n4. **WARNING**: Review uncommitted work before proceeding"

    if phase == "COMPLETE":
        next_instructions = "Project is complete. Review SUMMARY.md and SYNTHESIS.md."

    content = re.sub(
        r'## Next Session Instructions\s*\n(.*?)(?=\n---)',
        f"## Next Session Instructions\n\n{next_instructions}\n\n",
        content, flags=re.DOTALL
    )

    # Update meta last updated
    content = re.sub(
        r'\| Last Updated \| .+ \|',
        f'| Last Updated | {now.isoformat()} |',
        content
    )

    # Detect completion
    is_complete = phase == "COMPLETE"
    if is_complete:
        content = content.replace("| Status | active |", "| Status | complete |")

    safe_write(state_md_path, content)

    # Update current-project.json
    state["last_session"] = now.isoformat()
    state["current_step"] = QRALPH_PHASES.index(phase) + 1 if phase in QRALPH_PHASES else 0
    safe_write_json(CURRENT_PROJECT_FILE, state)

    output = {
        "status": "session_ended",
        "project_id": project_id,
        "phase": phase,
        "uncommitted_work": bool(git_diff),
        "is_complete": is_complete,
        "state_file": str(state_md_path),
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_recover(project_id: str):
    """
    REQ-STATE-006: Reconstruct STATE.md from checkpoints + git log + git status.

    Used when STATE.md is missing or corrupt. Marks uncertain items as STATUS UNKNOWN.
    """
    project_path = _get_project_path(project_id)
    if not project_path:
        print(json.dumps({"error": f"Project not found: {project_id}"}))
        return

    # Try to reconstruct state from checkpoints
    checkpoint_dir = project_path / "checkpoints"
    state = {}

    if checkpoint_dir.exists():
        checkpoints = sorted(checkpoint_dir.glob("*.json"))
        if checkpoints:
            state = safe_read_json(checkpoints[-1], {})

    if not state:
        # Minimal reconstruction
        state = {
            "project_id": project_id,
            "project_path": str(project_path),
            "request": "STATUS UNKNOWN - recovered from crash",
            "mode": "coding",
            "phase": "INIT",
            "created_at": datetime.now().isoformat(),
            "agents": [],
            "heal_attempts": 0,
            "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
        }

    # Check for agent outputs to infer phase
    agent_outputs = list((project_path / "agent-outputs").glob("*.md")) if (project_path / "agent-outputs").exists() else []
    synthesis_exists = (project_path / "SYNTHESIS.md").exists()
    uat_exists = (project_path / "UAT.md").exists()

    if uat_exists:
        state["phase"] = "UAT"
    elif synthesis_exists:
        state["phase"] = "EXECUTING"
    elif agent_outputs:
        state["phase"] = "REVIEWING"
    # else keep whatever phase was in checkpoint

    # Save recovered state
    safe_write_json(CURRENT_PROJECT_FILE, state)

    # Create STATE.md via the normal flow
    cmd_create_state(project_id)

    # Mark recovery in STATE.md
    state_md_path = _get_state_md_path(project_path)
    if state_md_path.exists():
        content = state_md_path.read_text()
        recovery_note = f"\n**RECOVERED**: State reconstructed at {datetime.now().isoformat()}. Some items may be STATUS UNKNOWN.\n"
        content = content.replace("## Current Step Detail\n", f"## Current Step Detail\n{recovery_note}")
        safe_write(state_md_path, content)

    git_log = _get_git_log_oneline()

    output = {
        "status": "recovered",
        "project_id": project_id,
        "phase": state["phase"],
        "agent_outputs_found": len(agent_outputs),
        "synthesis_exists": synthesis_exists,
        "uat_exists": uat_exists,
        "recent_git_log": git_log[:500],
        "state_file": str(state_md_path),
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_inject_claude_md(claude_md_path: Optional[str] = None):
    """
    REQ-STATE-003: Inject QRALPH project state pointer into CLAUDE.md.

    Append-only, never modifies existing content. Idempotent - safe to call repeatedly.
    """
    if claude_md_path:
        target = Path(claude_md_path)
    else:
        target = PROJECT_ROOT / "CLAUDE.md"

    if not target.exists():
        print(json.dumps({"error": f"CLAUDE.md not found at {target}"}))
        return

    # Read existing content
    existing = target.read_text()

    # Check if section already exists (idempotent)
    if CLAUDE_MD_SECTION_HEADER in existing:
        print(json.dumps({
            "status": "already_injected",
            "file": str(target),
            "message": "QRALPH section already present in CLAUDE.md",
        }))
        return

    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    project_id = state.get("project_id", "unknown")
    state_file = state.get("state_file", f".qralph/projects/{project_id}/STATE.md")

    section = f"""

---

{CLAUDE_MD_SECTION_HEADER}

Active QRALPH project: `{project_id}`

At session start, read `.qralph/tools/session-state.py session-start` for context.
State file: `{state_file}`
"""

    # Append (never modify existing content)
    safe_write(target, existing + section)

    output = {
        "status": "injected",
        "file": str(target),
        "project_id": project_id,
    }
    print(json.dumps(output, indent=2))
    return output


def main():
    parser = argparse.ArgumentParser(description="QRALPH Session State Manager")
    subparsers = parser.add_subparsers(dest="command")

    create = subparsers.add_parser("create-state", help="Create STATE.md")
    create.add_argument("project_id", help="Project ID")

    subparsers.add_parser("session-start", help="Output session context")

    end = subparsers.add_parser("session-end", help="Update STATE.md on end")
    end.add_argument("project_id", help="Project ID")

    recover = subparsers.add_parser("recover", help="Reconstruct from crash")
    recover.add_argument("project_id", help="Project ID")

    inject = subparsers.add_parser("inject-claude-md", help="Inject into CLAUDE.md")
    inject.add_argument("path", nargs="?", help="Path to CLAUDE.md (default: ./CLAUDE.md)")

    args = parser.parse_args()

    if args.command == "create-state":
        cmd_create_state(args.project_id)
    elif args.command == "session-start":
        cmd_session_start()
    elif args.command == "session-end":
        cmd_session_end(args.project_id)
    elif args.command == "recover":
        cmd_recover(args.project_id)
    elif args.command == "inject-claude-md":
        cmd_inject_claude_md(getattr(args, "path", None))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
