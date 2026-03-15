"""Decision agent escalation and session management for QRALPH CLI."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


class SessionStore:
    """Tracks `claude -p` session IDs by (project_id, phase_key).

    Sessions expire when the pipeline transitions to a new major phase
    (to prevent context clash between phases).
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, dict[str, str]] = {}
        if path.exists():
            self._data = json.loads(path.read_text())

    def get(self, project_id: str, phase_key: str) -> str | None:
        """Return session ID for the given project/phase, or None."""
        return self._data.get(project_id, {}).get(phase_key)

    def set(self, project_id: str, phase_key: str, session_id: str) -> None:
        """Store a session ID and persist to disk."""
        self._data.setdefault(project_id, {})[phase_key] = session_id
        self._persist()

    def advance_phase(self, project_id: str, new_phase: str) -> None:
        """Invalidate sessions from phases that don't start with new_phase."""
        project_sessions = self._data.get(project_id)
        if not project_sessions:
            return
        self._data[project_id] = {
            phase: sid
            for phase, sid in project_sessions.items()
            if phase.startswith(new_phase)
        }
        self._persist()

    def _persist(self) -> None:
        """Write current state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))


def _build_escalation_prompt(prompt: str, rules: str, progress: dict) -> str:
    """Compose a structured prompt with pipeline context for the decision agent."""
    phase_index = progress.get("phase_index", 0)
    phase_total = progress.get("phase_total", 0)
    current_phase = progress.get("current_phase", "UNKNOWN")
    sub_phase = progress.get("sub_phase", "")

    return f"""## Pipeline Progress
Phase {phase_index}/{phase_total} — {current_phase} (sub-phase: {sub_phase})

## Decision Rules for This Step
{rules}

## Current Situation
{prompt}

## Your Response Format
Start your response with `DECISION: <your decision>` on the first line.
Then explain your reasoning below.
Use `DECISION: escalate_to_user` when the situation requires human judgment."""


def escalate(
    store: SessionStore,
    project_id: str,
    phase_key: str,
    prompt: str,
    rules: str,
    progress: dict,
    working_dir: str,
    model: str = "opus",
) -> dict:
    """Spawn or resume a claude session to make a pipeline decision."""
    existing_session = store.get(project_id, phase_key)
    full_prompt = _build_escalation_prompt(prompt, rules, progress)

    cmd = ["claude", "-p", full_prompt, "--output-format", "json", "--model", model]
    if existing_session:
        cmd.extend(["--resume", existing_session])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=working_dir,
        )
        output = json.loads(result.stdout)
        decision = output.get("result", "")
        session_id = output.get("session_id", "")
        if session_id:
            store.set(project_id, phase_key, session_id)
        return {"decision": decision, "session_id": session_id}
    except Exception as exc:
        return {"decision": "", "session_id": "", "error": str(exc)}
