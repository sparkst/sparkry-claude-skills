#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""PostToolUse(Write) hook: Validate output paths match pipeline expectations."""

import json
import sys
from pathlib import Path

import importlib.util

_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

# Expected output directories for each sub-phase
EXPECTED_DIRS = {
    "PLAN_WAITING": "agent-outputs",
    "EXEC_WAITING": "execution-outputs",
    "VERIFY_WAIT": "verification",
}


def main():
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
    expected_dir = project_path / EXPECTED_DIRS[sub_phase]

    # Get the file path being written
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    file_path = Path(file_path).resolve()
    expected_dir_resolved = expected_dir.resolve()

    # Check if write is to the expected directory
    if not str(file_path).startswith(str(expected_dir_resolved)):
        print(
            f"Warning: Writing to '{file_path}' but pipeline expects outputs in '{expected_dir}'.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
