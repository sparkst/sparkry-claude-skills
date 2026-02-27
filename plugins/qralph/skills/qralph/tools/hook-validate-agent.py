#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""SubagentStop hook: Validate agent outputs match pipeline expectations."""

import json
import sys
from pathlib import Path

import importlib.util

_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)


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

    agent_name = hook_input.get("agent_name", "")
    if not agent_name:
        return

    # During PLAN_WAITING, check agent is one of the expected plan agents
    if sub_phase == "PLAN_WAITING":
        expected = [a["name"] for a in pipeline.get("plan_agents", [])]
        if agent_name not in expected:
            print(
                f"Warning: Unexpected agent '{agent_name}'. "
                f"Expected plan agents: {', '.join(expected)}",
                file=sys.stderr,
            )

    # During EXEC_WAITING, check agent matches current execution group
    elif sub_phase == "EXEC_WAITING":
        groups = pipeline.get("execution_groups", [])
        idx = pipeline.get("current_group_index", 0)
        if idx < len(groups):
            expected_names = [a["name"] for a in groups[idx].get("agents", [])]
            if agent_name not in expected_names:
                print(
                    f"Warning: Unexpected agent '{agent_name}'. "
                    f"Expected execution agents: {', '.join(expected_names)}",
                    file=sys.stderr,
                )

    # During VERIFY_WAIT, only expect verifier
    elif sub_phase == "VERIFY_WAIT":
        if agent_name != "result":
            print(
                f"Warning: Unexpected agent '{agent_name}'. Expected 'result'.",
                file=sys.stderr,
            )


if __name__ == "__main__":
    main()
