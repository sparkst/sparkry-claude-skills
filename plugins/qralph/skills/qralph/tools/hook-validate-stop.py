#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""Stop hook: Block session exit if pipeline is mid-phase with missing outputs."""

import json
import os
import sys
from pathlib import Path

import importlib.util

_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

# Prevent infinite loop: if this hook already ran once, allow stop
STOP_HOOK_ENV = "QRALPH_STOP_HOOK_ACTIVE"


def main():
    if os.environ.get(STOP_HOOK_ENV):
        print(json.dumps({"decision": "allow"}))
        return

    state = qralph_state.load_state()
    if not state:
        print(json.dumps({"decision": "allow"}))
        return

    pipeline = state.get("pipeline", {})
    sub_phase = pipeline.get("sub_phase", "")

    # Allow stop if pipeline is complete or not active
    if sub_phase in ("COMPLETE", ""):
        print(json.dumps({"decision": "allow"}))
        return

    # Set env var to prevent infinite loop on second pass
    os.environ[STOP_HOOK_ENV] = "1"

    phase_descriptions = {
        "INIT": "template confirmation pending",
        "PLAN_WAITING": "plan agent outputs not yet collected",
        "PLAN_REVIEW": "plan review pending",
        "EXEC_WAITING": "execution outputs not yet collected",
        "VERIFY_WAIT": "verification output not yet collected",
    }

    desc = phase_descriptions.get(sub_phase, sub_phase)
    print(json.dumps({
        "decision": "block",
        "reason": f"QRALPH pipeline is in phase '{sub_phase}' ({desc}). Call 'python3 .qralph/tools/qralph-pipeline.py next' to continue.",
    }))


if __name__ == "__main__":
    main()
