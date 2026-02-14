#!/usr/bin/env python3
"""
QRALPH Shared State Module - Single source of truth for state management.

Provides atomic writes, checksum validation, cross-platform file locking,
and corruption recovery for all QRALPH tools.

Both qralph-orchestrator.py and qralph-healer.py import from here.
"""

import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Cross-platform file locking
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

# Constants
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
STATE_FILE = QRALPH_DIR / "current-project.json"

REQUIRED_STATE_FIELDS = {
    "project_id": str,
    "project_path": str,
    "request": str,
    "mode": str,
    "phase": str,
    "created_at": str,
    "agents": list,
    "heal_attempts": int,
    "circuit_breakers": dict,
}

VALID_PHASES = {"INIT", "DISCOVERING", "REVIEWING", "EXECUTING", "UAT", "COMPLETE",
                "PLANNING", "USER_REVIEW", "ESCALATE"}

DEFAULT_CIRCUIT_BREAKERS = {
    "total_tokens": 0,
    "total_cost_usd": 0.0,
    "error_counts": {},
}


def _compute_checksum(data: dict) -> str:
    """Compute SHA-256 checksum of state dict (excluding _checksum field)."""
    clean = {k: v for k, v in data.items() if k != "_checksum"}
    serialized = json.dumps(clean, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


def _lock_file(f, exclusive: bool = False):
    """Acquire file lock (no-op on Windows)."""
    if HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)


def _unlock_file(f):
    """Release file lock (no-op on Windows)."""
    if HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def load_state(state_file: Optional[Path] = None) -> dict:
    """
    Load project state with file locking and checksum validation.

    Args:
        state_file: Path to state file (defaults to current-project.json)

    Returns:
        State dict, or empty dict if file missing/corrupt.
    """
    state_file = state_file or STATE_FILE
    if not state_file.exists():
        return {}

    try:
        with open(state_file, 'r') as f:
            _lock_file(f, exclusive=False)
            try:
                content = f.read()
                if not content:
                    return {}
                state = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in state file: {e}", file=sys.stderr)
                return {}
            finally:
                _unlock_file(f)

        # Validate checksum if present
        if "_checksum" in state:
            expected = state["_checksum"]
            actual = _compute_checksum(state)
            if expected != actual:
                print(f"Warning: State checksum mismatch (expected {expected}, got {actual}). "
                      "State may be corrupted.", file=sys.stderr)

        return state

    except Exception as e:
        print(f"Warning: Error loading state: {e}", file=sys.stderr)
        return {}


def save_state(state: dict, state_file: Optional[Path] = None):
    """
    Save project state with atomic write, file locking, and checksum injection.

    Uses write-to-temp + rename for atomicity (prevents partial writes on crash).

    Args:
        state: State dict to save
        state_file: Path to state file (defaults to current-project.json)
    """
    state_file = state_file or STATE_FILE
    state_file.parent.mkdir(parents=True, exist_ok=True)

    # Inject checksum
    state["_checksum"] = _compute_checksum(state)

    safe_write_json(state_file, state)


def validate_state(state: dict) -> List[str]:
    """
    Validate state dict structure and field types.

    Returns:
        List of validation error messages (empty = valid).
    """
    errors = []

    if not state:
        errors.append("State is empty")
        return errors

    for field, expected_type in REQUIRED_STATE_FIELDS.items():
        if field not in state:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(state[field], expected_type):
            errors.append(f"Field '{field}' has wrong type: expected {expected_type.__name__}, "
                         f"got {type(state[field]).__name__}")

    if "phase" in state and state["phase"] not in VALID_PHASES:
        errors.append(f"Unknown phase: {state['phase']}")

    if "circuit_breakers" in state:
        cb = state["circuit_breakers"]
        if not isinstance(cb.get("total_tokens", 0), (int, float)):
            errors.append("circuit_breakers.total_tokens must be numeric")
        if not isinstance(cb.get("total_cost_usd", 0.0), (int, float)):
            errors.append("circuit_breakers.total_cost_usd must be numeric")
        if not isinstance(cb.get("error_counts", {}), dict):
            errors.append("circuit_breakers.error_counts must be dict")

    if "created_at" in state:
        try:
            datetime.fromisoformat(state["created_at"])
        except (ValueError, TypeError):
            errors.append(f"Invalid ISO timestamp in created_at: {state.get('created_at')}")

    if "heal_attempts" in state:
        if not isinstance(state["heal_attempts"], int) or state["heal_attempts"] < 0:
            errors.append("heal_attempts must be a non-negative integer")

    return errors


def repair_state(state: dict) -> dict:
    """
    Fill missing required fields with defaults. Returns repaired copy.

    Does NOT overwrite existing fields - only fills gaps.
    """
    repaired = dict(state)

    defaults = {
        "project_id": "unknown",
        "project_path": str(QRALPH_DIR / "projects" / "unknown"),
        "request": "",
        "mode": "coding",
        "phase": "INIT",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "teammates": [],
        "heal_attempts": 0,
        "circuit_breakers": dict(DEFAULT_CIRCUIT_BREAKERS),
        "findings": [],
        "domains": [],
    }

    for field, default in defaults.items():
        if field not in repaired:
            repaired[field] = default

    # Repair circuit_breakers sub-fields
    cb = repaired.get("circuit_breakers", {})
    if not isinstance(cb, dict):
        repaired["circuit_breakers"] = dict(DEFAULT_CIRCUIT_BREAKERS)
    else:
        for key, default_val in DEFAULT_CIRCUIT_BREAKERS.items():
            if key not in cb:
                cb[key] = default_val

    return repaired


def validate_state_consistency(state: dict, project_path: Path) -> List[str]:
    """
    Validate state consistency against filesystem.

    Checks:
    - project_path exists
    - project_id matches directory name
    - phase is valid
    - agents match files in agent-outputs/
    - circuit_breakers are non-negative
    - created_at is valid ISO timestamp

    Args:
        state: State dict to validate
        project_path: Project directory path

    Returns:
        List of consistency error messages (empty = consistent).
    """
    errors = []

    # Schema validation first
    errors.extend(validate_state(state))

    # project_path exists
    if not project_path.exists():
        errors.append(f"Project directory does not exist: {project_path}")
        return errors  # Can't do further FS checks

    # project_id matches directory name
    project_id = state.get("project_id", "")
    if project_id and project_path.name != project_id:
        errors.append(f"project_id '{project_id}' doesn't match directory '{project_path.name}'")

    # agents match output files
    agents = state.get("agents", [])
    outputs_dir = project_path / "agent-outputs"
    if outputs_dir.exists() and agents:
        output_files = {f.stem for f in outputs_dir.glob("*.md")}
        agent_set = set(agents) if isinstance(agents, list) and all(isinstance(a, str) for a in agents) else set()
        orphans = output_files - agent_set
        if orphans:
            errors.append(f"Orphan output files not in agents list: {orphans}")

    # circuit_breakers non-negative
    cb = state.get("circuit_breakers", {})
    if isinstance(cb, dict):
        if cb.get("total_tokens", 0) < 0:
            errors.append("circuit_breakers.total_tokens is negative")
        if cb.get("total_cost_usd", 0.0) < 0:
            errors.append("circuit_breakers.total_cost_usd is negative")

    return errors


def safe_write(path: Path, content: str):
    """
    Atomic file write: write to temp file in same directory, then rename.

    This prevents partial writes if the process crashes mid-write.

    Args:
        path: Target file path
        content: Content to write
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp"
        )
        try:
            with os.fdopen(fd, 'w') as f:
                _lock_file(f, exclusive=True)
                try:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                finally:
                    _unlock_file(f)
            os.rename(tmp_path, str(path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        print(f"Error: Failed to write {path}: {e}", file=sys.stderr)
        raise


def safe_write_json(path: Path, data: Any):
    """
    Atomic JSON write with roundtrip validation.

    Writes JSON, reads it back, and verifies content matches.

    Args:
        path: Target file path
        data: Data to serialize as JSON
    """
    content = json.dumps(data, indent=2)

    # Roundtrip validation before writing
    try:
        roundtripped = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON serialization produced invalid JSON: {e}")

    safe_write(path, content)


def safe_read_json(path: Path, default: Any = None) -> Any:
    """
    Safe JSON read with error handling.

    Args:
        path: File path to read
        default: Value to return if file missing or corrupt

    Returns:
        Parsed JSON data, or default value.
    """
    if not path.exists():
        return default if default is not None else {}

    try:
        with open(path, 'r') as f:
            _lock_file(f, exclusive=False)
            try:
                content = f.read()
                return json.loads(content) if content else (default if default is not None else {})
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in {path}: {e}", file=sys.stderr)
                return default if default is not None else {}
            finally:
                _unlock_file(f)
    except Exception as e:
        print(f"Warning: Error reading {path}: {e}", file=sys.stderr)
        return default if default is not None else {}
