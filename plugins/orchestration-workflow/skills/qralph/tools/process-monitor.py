#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
QRALPH Process Monitor - Manages spawned processes during orchestration.

Commands:
  register  --pid <PID> --type <node|vitest|claude> --purpose <desc>
  sweep     [--dry-run] [--force]
  cleanup   --project-id <id>
  status

PID Registry: .qralph/process-registry.json

Safety:
- Only kills processes found in the registry
- Unregistered processes get warnings, never killed
- Never kills if parent PID is alive
- Circuit breaker: 3+ orphans trips breaker, writes PAUSE to CONTROL.md
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
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
_lock_file = qralph_state._lock_file
_unlock_file = qralph_state._unlock_file

# Constants
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
REGISTRY_FILE = QRALPH_DIR / "process-registry.json"
KILL_LOG_FILE = QRALPH_DIR / "process-kills.log"

DEFAULT_GRACE_PERIODS = {
    "node": 1800,
    "vitest": 1800,
    "claude": 3600,
    "team-agent": 1800,
    "default": 900,
}

ORPHAN_CIRCUIT_BREAKER_THRESHOLD = 3


def _now_iso() -> str:
    """Return current time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _load_registry(registry_file: Optional[Path] = None) -> dict:
    """Load the process registry from disk."""
    registry_file = registry_file or REGISTRY_FILE
    default = {
        "session_id": _now_iso(),
        "project_id": None,
        "parent_pid": os.getpid(),
        "spawned_processes": [],
        "grace_periods": dict(DEFAULT_GRACE_PERIODS),
    }
    return safe_read_json(registry_file, default)


def _save_registry(registry: dict, registry_file: Optional[Path] = None):
    """Save the process registry to disk."""
    registry_file = registry_file or REGISTRY_FILE
    safe_write_json(registry_file, registry)


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _get_process_age_seconds(spawned_at: str) -> float:
    """Get the age of a process in seconds from its spawned_at timestamp."""
    try:
        spawned = datetime.fromisoformat(spawned_at)
        if spawned.tzinfo is None:
            spawned = spawned.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - spawned).total_seconds()
    except (ValueError, TypeError):
        return 0.0


def _get_grace_period(proc_type: str, grace_periods: dict) -> int:
    """Get the grace period for a process type."""
    return grace_periods.get(proc_type, grace_periods.get("default", DEFAULT_GRACE_PERIODS["default"]))


def _log_action(message: str, log_file: Optional[Path] = None):
    """Append a timestamped message to the kill log."""
    log_file = log_file or KILL_LOG_FILE
    timestamp = _now_iso()
    sanitized_msg = re.sub(r'[\x00-\x1f\x7f]', ' ', message)
    entry = f"[{timestamp}] {sanitized_msg}\n"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if os.path.islink(str(log_file)):
        print(f"Warning: Refusing to write to symlink: {log_file}", file=sys.stderr)
        return
    fd = os.open(str(log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        with os.fdopen(fd, "a") as f:
            _lock_file(f, exclusive=True)
            try:
                f.write(entry)
                f.flush()
            finally:
                _unlock_file(f)
    except Exception as e:
        print(f"Warning: Failed to log action: {e}", file=sys.stderr)


def _verify_process_identity(pid: int, expected_type: str) -> bool:
    """Verify process command matches expected type before killing (PID reuse safety).

    On Windows, ``ps -p`` is unavailable and there is no reliable stdlib way to
    inspect a process command line.  Returns False (safe default) so callers
    skip the kill.  Windows users must manage stale processes manually.
    """
    if os.name == "nt":
        return False  # ps unavailable on Windows; refuse kill when identity unverifiable
    type_patterns = {
        "node": ["node", "npm"],
        "vitest": ["vitest", "node"],
        "claude": ["claude", "node"],
    }
    patterns = type_patterns.get(expected_type, [expected_type])
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "comm="],
            capture_output=True, text=True, timeout=5
        )
        comm = result.stdout.strip().lower()
        return any(p in comm for p in patterns)
    except Exception:
        return False  # On failure, refuse kill (safe default: don't kill unverified PIDs)


def _kill_process(pid: int, log_file: Optional[Path] = None,
                  expected_type: Optional[str] = None) -> bool:
    """
    Kill a process: SIGTERM first, wait 5s, then SIGKILL if needed.

    Returns True if the process was successfully terminated.
    """
    if expected_type and not _verify_process_identity(pid, expected_type):
        _log_action(f"SKIP PID {pid}: process identity mismatch (expected {expected_type})", log_file)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        _log_action(f"KILL SIGTERM sent to PID {pid}", log_file)
    except (OSError, ProcessLookupError):
        _log_action(f"KILL PID {pid} already dead before SIGTERM", log_file)
        return True

    # Wait up to 5 seconds for graceful shutdown
    for _ in range(50):
        if not _is_pid_alive(pid):
            _log_action(f"KILL PID {pid} terminated after SIGTERM", log_file)
            return True
        time.sleep(0.1)

    # Force kill
    try:
        os.kill(pid, signal.SIGKILL)
        _log_action(f"KILL SIGKILL sent to PID {pid} (SIGTERM timeout)", log_file)
    except (OSError, ProcessLookupError):
        _log_action(f"KILL PID {pid} died between SIGTERM and SIGKILL", log_file)
        return True

    return not _is_pid_alive(pid)


def _write_pause_to_control(project_id: str):
    """Write PAUSE to the project's CONTROL.md (circuit breaker)."""
    projects_dir = QRALPH_DIR / "projects"
    control_file = projects_dir / project_id / "CONTROL.md"
    if control_file.parent.exists():
        safe_write(control_file, "PAUSE\n# Circuit breaker tripped: 3+ orphan processes detected\n")


def _verify_pid_ownership(pid: int) -> bool:
    """Verify caller is parent of the registered PID (Unix only).

    Returns True if verification passes or cannot be performed (process
    not found, platform unsupported). Only returns False when the process
    exists but has a different parent.
    """
    if os.name == "nt":
        return True  # Skip on Windows
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "ppid="],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip()
        if not output:
            return True  # Process not found; allow registration (sweep handles dead PIDs)
        ppid = int(output)
        return ppid == os.getpid()
    except (ValueError, subprocess.TimeoutExpired, OSError):
        return True  # On failure, allow registration (safe default for CLI tool)


def cmd_register(pid: int, proc_type: str, purpose: str,
                 registry_file: Optional[Path] = None,
                 log_file: Optional[Path] = None):
    """Register a spawned process in the registry."""
    if not _verify_pid_ownership(pid):
        _log_action(f"REGISTER REJECTED PID {pid}: caller is not parent", log_file)
        result = {"error": f"PID {pid} not owned by caller (ppid mismatch)"}
        print(json.dumps(result, indent=2))
        return result

    lock_path = (registry_file or REGISTRY_FILE).with_suffix('.lock')
    with qralph_state.exclusive_state_lock(lock_path):
        registry = _load_registry(registry_file)

        entry = {
            "pid": pid,
            "type": proc_type,
            "spawned_at": _now_iso(),
            "purpose": purpose,
        }

        registry["spawned_processes"].append(entry)
        _save_registry(registry, registry_file)
    _log_action(f"REGISTER PID {pid} type={proc_type} purpose={purpose}", log_file)

    result = {"status": "registered", "pid": pid, "type": proc_type, "purpose": purpose}
    print(json.dumps(result, indent=2))
    return result


def cmd_sweep(dry_run: bool = False, force: bool = False,
              registry_file: Optional[Path] = None,
              log_file: Optional[Path] = None) -> dict:
    """
    Sweep registered processes for orphans and kill them.

    Logic per registered PID:
    1. Check alive (os.kill(pid, 0))
    2. Check age vs grace period
    3. Check if parent is dead
    4. If orphan (parent dead + past grace): SIGTERM, wait 5s, SIGKILL if needed
    5. Unregistered processes: warn only, never kill
    """
    lock_path = (registry_file or REGISTRY_FILE).with_suffix('.lock')
    with qralph_state.exclusive_state_lock(lock_path):
        return _cmd_sweep_locked(dry_run, force, registry_file, log_file)


def _cmd_sweep_locked(dry_run: bool = False, force: bool = False,
                      registry_file: Optional[Path] = None,
                      log_file: Optional[Path] = None) -> dict:
    """Inner sweep logic, called under exclusive lock."""
    registry = _load_registry(registry_file)
    parent_pid = registry.get("parent_pid")
    grace_periods = registry.get("grace_periods", DEFAULT_GRACE_PERIODS)
    project_id = registry.get("project_id")

    parent_alive = _is_pid_alive(parent_pid) if parent_pid else True

    results = {
        "status": "sweep_complete",
        "alive": [],
        "dead": [],
        "killed": [],
        "warned": [],
        "dry_run": dry_run,
        "orphan_count": 0,
    }

    remaining_processes = []
    orphan_count = 0

    for proc in registry.get("spawned_processes", []):
        pid = proc["pid"]
        proc_type = proc.get("type", "default")
        purpose = proc.get("purpose", "unknown")
        spawned_at = proc.get("spawned_at", "")

        alive = _is_pid_alive(pid)

        if not alive:
            results["dead"].append({"pid": pid, "type": proc_type, "purpose": purpose})
            _log_action(f"SWEEP PID {pid} already dead (type={proc_type})", log_file)
            continue

        age = _get_process_age_seconds(spawned_at)
        grace = _get_grace_period(proc_type, grace_periods)
        past_grace = age > grace

        is_orphan = (not parent_alive or force) and past_grace

        if is_orphan:
            orphan_count += 1
            if dry_run:
                results["warned"].append({
                    "pid": pid, "type": proc_type, "purpose": purpose,
                    "age_seconds": round(age), "reason": "orphan (dry-run)",
                })
                _log_action(f"WARN DRY-RUN would kill PID {pid} (orphan, age={round(age)}s, grace={grace}s)", log_file)
                remaining_processes.append(proc)
            else:
                # Re-verify process identity before killing to guard against PID reuse
                if not _verify_process_identity(pid, proc_type):
                    _log_action(f"SKIP PID {pid}: identity changed (possible PID reuse), not killing", log_file)
                    remaining_processes.append(proc)
                    continue
                killed = _kill_process(pid, log_file, expected_type=proc_type)
                results["killed"].append({
                    "pid": pid, "type": proc_type, "purpose": purpose,
                    "age_seconds": round(age), "killed": killed,
                })
                if not killed:
                    remaining_processes.append(proc)  # Keep in registry if kill failed
        else:
            results["alive"].append({
                "pid": pid, "type": proc_type, "purpose": purpose,
                "age_seconds": round(age),
            })
            remaining_processes.append(proc)

    results["orphan_count"] = orphan_count

    # Update registry: remove dead and killed processes
    if not dry_run:
        registry["spawned_processes"] = remaining_processes
        _save_registry(registry, registry_file)

    # Circuit breaker: 3+ orphans trips breaker
    if orphan_count >= ORPHAN_CIRCUIT_BREAKER_THRESHOLD and project_id:
        if not dry_run:
            _write_pause_to_control(project_id)
            _log_action(
                f"CIRCUIT_BREAKER tripped for project {project_id}: {orphan_count} orphans detected",
                log_file,
            )
        results["circuit_breaker_tripped"] = True
        results["circuit_breaker_message"] = (
            f"Circuit breaker tripped: {orphan_count} orphans detected for project {project_id}. "
            f"PAUSE written to CONTROL.md."
        )

    print(json.dumps(results, indent=2))
    return results


def cmd_cleanup(project_id: str,
                registry_file: Optional[Path] = None,
                log_file: Optional[Path] = None) -> dict:
    """Clean up all processes associated with a project."""
    lock_path = (registry_file or REGISTRY_FILE).with_suffix('.lock')
    with qralph_state.exclusive_state_lock(lock_path):
        return _cmd_cleanup_locked(project_id, registry_file, log_file)


def _cmd_cleanup_locked(project_id: str,
                        registry_file: Optional[Path] = None,
                        log_file: Optional[Path] = None) -> dict:
    """Inner cleanup logic, called under exclusive lock."""
    registry = _load_registry(registry_file)

    if registry.get("project_id") != project_id:
        result = {
            "status": "no_match",
            "message": f"Registry project_id '{registry.get('project_id')}' does not match '{project_id}'",
        }
        print(json.dumps(result, indent=2))
        return result

    killed = []
    for proc in registry.get("spawned_processes", []):
        pid = proc["pid"]
        if _is_pid_alive(pid):
            success = _kill_process(pid, log_file, expected_type=proc.get("type"))
            killed.append({"pid": pid, "type": proc.get("type"), "killed": success})
        else:
            _log_action(f"CLEANUP PID {pid} already dead", log_file)

    registry["spawned_processes"] = []
    _save_registry(registry, registry_file)

    result = {
        "status": "cleaned",
        "project_id": project_id,
        "killed_count": len(killed),
        "killed": killed,
    }
    _log_action(f"CLEANUP project {project_id}: killed {len(killed)} processes", log_file)
    print(json.dumps(result, indent=2))
    return result


def cmd_status(registry_file: Optional[Path] = None) -> dict:
    """Show the current status of all registered processes."""
    registry = _load_registry(registry_file)

    processes = []
    for proc in registry.get("spawned_processes", []):
        pid = proc["pid"]
        alive = _is_pid_alive(pid)
        age = _get_process_age_seconds(proc.get("spawned_at", ""))
        processes.append({
            "pid": pid,
            "type": proc.get("type", "unknown"),
            "purpose": proc.get("purpose", "unknown"),
            "alive": alive,
            "age_seconds": round(age),
        })

    parent_pid = registry.get("parent_pid")
    parent_alive = _is_pid_alive(parent_pid) if parent_pid else None

    result = {
        "status": "ok",
        "session_id": registry.get("session_id"),
        "project_id": registry.get("project_id"),
        "parent_pid": parent_pid,
        "parent_alive": parent_alive,
        "process_count": len(processes),
        "processes": processes,
    }
    print(json.dumps(result, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description="QRALPH Process Monitor")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # register
    reg_parser = subparsers.add_parser("register", help="Register a spawned process")
    reg_parser.add_argument("--pid", type=int, required=True, help="Process ID")
    reg_parser.add_argument("--type", dest="proc_type", required=True,
                            choices=["node", "vitest", "claude"],
                            help="Process type")
    reg_parser.add_argument("--purpose", required=True, help="Purpose description")

    # sweep
    sweep_parser = subparsers.add_parser("sweep", help="Sweep for orphan processes")
    sweep_parser.add_argument("--dry-run", action="store_true", help="Report only, don't kill")
    sweep_parser.add_argument("--force", action="store_true", help="Force kill past-grace processes")

    # cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up project processes")
    cleanup_parser.add_argument("--project-id", required=True, help="Project ID to clean up")

    # status
    subparsers.add_parser("status", help="Show process status")

    args = parser.parse_args()

    if args.command == "register":
        cmd_register(args.pid, args.proc_type, args.purpose)
    elif args.command == "sweep":
        cmd_sweep(dry_run=args.dry_run, force=args.force)
    elif args.command == "cleanup":
        cmd_cleanup(args.project_id)
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    if sys.version_info < (3, 6):
        sys.exit("QRALPH requires Python 3.6+")
    main()
