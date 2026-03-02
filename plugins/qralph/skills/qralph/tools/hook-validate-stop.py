#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""Stop hook: Block session exit if QRALPH pipeline is mid-phase."""

import importlib.util
import json
import os
import sys
from pathlib import Path

_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

SESSION_LOCK = Path(__file__).parent.parent / "active-session.lock"
STOP_HOOK_ENV = "QRALPH_STOP_HOOK_ACTIVE"


def main():
    # No session lock = QRALPH is not running in this session → allow
    if not SESSION_LOCK.exists():
        return

    # Prevent infinite loop: if this hook already ran once, allow stop
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

    print(json.dumps({
        "decision": "block",
        "reason": (
            f"QRALPH is still working (phase: {sub_phase}). "
            "Call 'python3 .qralph/tools/qralph-pipeline.py next' to continue. "
            "If you need to start over, use /clear to begin a new session."
        ),
    }))


if __name__ == "__main__":
    main()
