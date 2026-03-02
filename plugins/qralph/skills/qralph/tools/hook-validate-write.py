#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""PreToolUse(Write) hook: Block writes to wrong directories during active pipeline phases."""

import importlib.util
import json
import sys
from pathlib import Path

_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

SESSION_LOCK = Path(__file__).parent.parent / "active-session.lock"

# Maps sub_phase → expected output directory name (relative to project_path).
EXPECTED_DIRS = {
    "PLAN_WAITING": "agent-outputs",
    "EXEC_WAITING": "execution-outputs",
    "VERIFY_WAIT": "verification",
}


def main():
    # No session lock = QRALPH is not running → allow all writes
    if not SESSION_LOCK.exists():
        return

    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, IOError):
        return

    state = qralph_state.load_state()
    if not state:
        return

    pipeline = state.get("pipeline", {})
    sub_phase = pipeline.get("sub_phase", "")

    if sub_phase not in EXPECTED_DIRS:
        return

    project_path = Path(state.get("project_path", ""))
    if not project_path.exists():
        return

    expected_dir = project_path / EXPECTED_DIRS[sub_phase]

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    file_path_resolved = Path(file_path).resolve()
    expected_dir_resolved = expected_dir.resolve()

    try:
        file_path_resolved.relative_to(expected_dir_resolved)
        return  # Write is inside expected dir — allow
    except ValueError:
        pass  # Falls through to block

    print(json.dumps({
        "decision": "block",
        "reason": (
            f"QRALPH pipeline is in phase {sub_phase} and expects agent outputs in "
            f"'{EXPECTED_DIRS[sub_phase]}/'. You wrote to '{file_path}'. "
            f"Move the output to '{expected_dir}/{Path(file_path).name}' and try again."
        ),
    }))


if __name__ == "__main__":
    main()
