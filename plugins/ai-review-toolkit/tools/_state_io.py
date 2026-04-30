"""Shared state I/O primitives for driver modules.

Atomic JSON write (tempfile + os.replace) and JSON read with
decode-error wrapping. All three drivers delegate here instead
of duplicating the pattern.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_state_atomic(target: Path, state: dict[str, Any]) -> None:
    """Write *state* to *target* atomically.

    Stamps ``updated_at``, writes to a tempfile in the same directory,
    then ``os.replace``s into place.  On any failure the tempfile is
    cleaned up.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    fd, tmp = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, default=str)
        os.replace(tmp, str(target))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_json_state(path: Path, context: str) -> dict[str, Any]:
    """Read JSON state from *path*.

    Wraps ``JSONDecodeError`` in a ``ValueError`` with *context* for
    actionable error messages.
    """
    if not path.exists():
        raise FileNotFoundError(f"No state found at {path}. {context}")
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Corrupt state file at {path}: {exc}. {context}"
            ) from exc
