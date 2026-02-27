#!/usr/bin/env python3
"""
Tests for QRALPH Process Monitor.

REQ-PROC-001: PID registration
REQ-PROC-002: Orphan detection and sweep
REQ-PROC-003: Safety constraints
REQ-PROC-004: Audit logging
REQ-PROC-005: Circuit breaker integration
REQ-PROC-006: Full lifecycle integration

Test Categories:
1. Registration (3 tests)
2. Orphan detection (5 tests)
3. Safety (3 tests)
4. Audit log (2 tests)
5. Circuit breaker (2 tests)
6. Integration (1 test)
"""

import json
import os
import signal
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import importlib.util

# Load process-monitor.py
monitor_path = Path(__file__).parent / "process-monitor.py"
spec = importlib.util.spec_from_file_location("process_monitor", monitor_path)
process_monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(process_monitor)


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up mock QRALPH environment with temp registry and log paths."""
    qralph_dir = tmp_path / ".qralph"
    qralph_dir.mkdir(parents=True)
    projects_dir = qralph_dir / "projects"
    projects_dir.mkdir(parents=True)

    registry_file = qralph_dir / "process-registry.json"
    log_file = qralph_dir / "process-kills.log"

    monkeypatch.setattr(process_monitor, "QRALPH_DIR", qralph_dir)
    monkeypatch.setattr(process_monitor, "REGISTRY_FILE", registry_file)
    monkeypatch.setattr(process_monitor, "KILL_LOG_FILE", log_file)

    return {
        "tmp_path": tmp_path,
        "qralph_dir": qralph_dir,
        "projects_dir": projects_dir,
        "registry_file": registry_file,
        "log_file": log_file,
    }


def _write_registry(env, registry_data):
    """Helper to write registry data directly."""
    env["registry_file"].write_text(json.dumps(registry_data, indent=2))


def _read_registry(env) -> dict:
    """Helper to read registry data directly."""
    return json.loads(env["registry_file"].read_text())


# ============================================================================
# 1. REGISTRATION (REQ-PROC-001)
# ============================================================================


def test_register_adds_pid(mock_env):
    """REQ-PROC-001: register adds PID to the registry."""
    process_monitor.cmd_register(
        pid=12345, proc_type="node", purpose="test-runner",
        registry_file=mock_env["registry_file"],
        log_file=mock_env["log_file"],
    )
    registry = _read_registry(mock_env)
    pids = [p["pid"] for p in registry["spawned_processes"]]
    assert 12345 in pids


def test_register_records_type_and_purpose(mock_env):
    """REQ-PROC-001: register records type and purpose correctly."""
    process_monitor.cmd_register(
        pid=99999, proc_type="vitest", purpose="unit-tests",
        registry_file=mock_env["registry_file"],
        log_file=mock_env["log_file"],
    )
    registry = _read_registry(mock_env)
    proc = registry["spawned_processes"][0]
    assert proc["type"] == "vitest"
    assert proc["purpose"] == "unit-tests"
    assert "spawned_at" in proc


def test_register_creates_registry_if_missing(mock_env):
    """REQ-PROC-001: register creates registry file if it does not exist."""
    # Ensure file does not exist
    if mock_env["registry_file"].exists():
        mock_env["registry_file"].unlink()
    assert not mock_env["registry_file"].exists()

    process_monitor.cmd_register(
        pid=11111, proc_type="claude", purpose="agent-runner",
        registry_file=mock_env["registry_file"],
        log_file=mock_env["log_file"],
    )
    assert mock_env["registry_file"].exists()
    registry = _read_registry(mock_env)
    assert len(registry["spawned_processes"]) == 1


# ============================================================================
# 2. ORPHAN DETECTION (REQ-PROC-002)
# ============================================================================


def test_sweep_detects_dead_process(mock_env):
    """REQ-PROC-002: sweep detects already-dead processes."""
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": os.getpid(),
        "spawned_processes": [
            {"pid": 999999999, "type": "node", "spawned_at": datetime.now(timezone.utc).isoformat(), "purpose": "dead-proc"}
        ],
        "grace_periods": process_monitor.DEFAULT_GRACE_PERIODS,
    })

    with patch.object(process_monitor, "_is_pid_alive", return_value=False):
        result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert len(result["dead"]) == 1
    assert result["dead"][0]["pid"] == 999999999


def test_sweep_respects_grace_period(mock_env):
    """REQ-PROC-002: sweep does not kill processes within grace period."""
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,  # Non-existent parent
        "spawned_processes": [
            {"pid": 55555, "type": "node", "spawned_at": datetime.now(timezone.utc).isoformat(), "purpose": "recent-proc"}
        ],
        "grace_periods": {"node": 1800, "default": 900},
    })

    def mock_alive(pid):
        if pid == 1:
            return False  # parent dead
        return True  # child alive

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive):
        result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    # Process is within grace period, so it should be in alive, not killed
    assert len(result["killed"]) == 0
    assert len(result["alive"]) == 1


def test_sweep_skips_when_parent_alive(mock_env):
    """REQ-PROC-002: sweep does not kill when parent PID is alive."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": os.getpid(),  # Current process, definitely alive
        "spawned_processes": [
            {"pid": 77777, "type": "node", "spawned_at": old_time, "purpose": "old-proc"}
        ],
        "grace_periods": {"node": 1800, "default": 900},
    })

    def mock_alive(pid):
        return True  # Both parent and child alive

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive):
        result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert len(result["killed"]) == 0
    assert len(result["alive"]) == 1


def test_sweep_kills_orphan(mock_env):
    """REQ-PROC-002: sweep kills orphan (parent dead + past grace)."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,  # Non-existent parent
        "spawned_processes": [
            {"pid": 88888, "type": "node", "spawned_at": old_time, "purpose": "orphan-proc"}
        ],
        "grace_periods": {"node": 1800, "default": 900},
    })

    call_count = {"kill": 0}

    def mock_alive(pid):
        if pid == 1:
            return False  # parent dead
        if pid == 88888:
            # After kill is called, report dead
            return call_count["kill"] == 0
        return False

    def mock_kill(pid, sig):
        call_count["kill"] += 1

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive), \
         patch.object(process_monitor, "_verify_process_identity", return_value=True), \
         patch("os.kill", side_effect=mock_kill):
        result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert len(result["killed"]) == 1
    assert result["killed"][0]["pid"] == 88888


def test_sweep_dry_run_does_not_kill(mock_env):
    """REQ-PROC-002: sweep --dry-run reports but does not kill orphans."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,
        "spawned_processes": [
            {"pid": 66666, "type": "node", "spawned_at": old_time, "purpose": "dry-run-proc"}
        ],
        "grace_periods": {"node": 1800, "default": 900},
    })

    def mock_alive(pid):
        if pid == 1:
            return False  # parent dead
        return True  # child alive

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive):
        result = process_monitor.cmd_sweep(
            dry_run=True,
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert result["dry_run"] is True
    assert len(result["warned"]) == 1
    assert len(result["killed"]) == 0
    # Registry should still contain the process
    registry = _read_registry(mock_env)
    assert len(registry["spawned_processes"]) == 1


# ============================================================================
# 3. SAFETY (REQ-PROC-003)
# ============================================================================


def test_safety_never_kills_unregistered(mock_env):
    """REQ-PROC-003: sweep never kills unregistered processes."""
    # Empty registry - no processes registered
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,
        "spawned_processes": [],
        "grace_periods": process_monitor.DEFAULT_GRACE_PERIODS,
    })

    with patch("os.kill") as mock_kill:
        result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    # os.kill should never be called (no _is_pid_alive check calls os.kill with signal 0,
    # but those are via _is_pid_alive, not direct kills)
    assert len(result["killed"]) == 0
    assert len(result["warned"]) == 0


def test_safety_warns_on_unknown_type(mock_env):
    """REQ-PROC-003: sweep handles unknown process types using default grace."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,
        "spawned_processes": [
            {"pid": 44444, "type": "unknown_type", "spawned_at": old_time, "purpose": "mystery-proc"}
        ],
        "grace_periods": process_monitor.DEFAULT_GRACE_PERIODS,
    })

    def mock_alive(pid):
        if pid == 1:
            return False  # parent dead
        return True  # child alive

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive):
        result = process_monitor.cmd_sweep(
            dry_run=True,
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    # Should warn using default grace period (900s), and old_time is 2h ago > 900s
    assert len(result["warned"]) == 1
    assert result["warned"][0]["type"] == "unknown_type"


def test_cleanup_scoped_to_project(mock_env):
    """REQ-PROC-003: cleanup only affects the matching project."""
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": os.getpid(),
        "spawned_processes": [
            {"pid": 33333, "type": "node", "spawned_at": datetime.now(timezone.utc).isoformat(), "purpose": "some-proc"}
        ],
        "grace_periods": process_monitor.DEFAULT_GRACE_PERIODS,
    })

    result = process_monitor.cmd_cleanup(
        project_id="002-other",
        registry_file=mock_env["registry_file"],
        log_file=mock_env["log_file"],
    )

    assert result["status"] == "no_match"
    # Original processes should still be in registry
    registry = _read_registry(mock_env)
    assert len(registry["spawned_processes"]) == 1


# ============================================================================
# 4. AUDIT LOG (REQ-PROC-004)
# ============================================================================


def test_audit_log_kill_format(mock_env):
    """REQ-PROC-004: kill actions are logged with timestamp and details."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,
        "spawned_processes": [
            {"pid": 22222, "type": "node", "spawned_at": old_time, "purpose": "kill-log-test"}
        ],
        "grace_periods": {"node": 1800, "default": 900},
    })

    call_count = {"n": 0}

    def mock_alive(pid):
        if pid == 1:
            return False
        if pid == 22222:
            return call_count["n"] == 0
        return False

    def mock_kill(pid, sig):
        call_count["n"] += 1

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive), \
         patch.object(process_monitor, "_verify_process_identity", return_value=True), \
         patch("os.kill", side_effect=mock_kill):
        process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    log_content = mock_env["log_file"].read_text()
    assert "KILL" in log_content
    assert "22222" in log_content
    # Verify timestamp format [ISO]
    assert "[" in log_content


def test_audit_log_warn_format(mock_env):
    """REQ-PROC-004: warn actions are logged in dry-run mode."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,
        "spawned_processes": [
            {"pid": 11111, "type": "vitest", "spawned_at": old_time, "purpose": "warn-log-test"}
        ],
        "grace_periods": {"vitest": 1800, "default": 900},
    })

    def mock_alive(pid):
        if pid == 1:
            return False
        return True

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive):
        process_monitor.cmd_sweep(
            dry_run=True,
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    log_content = mock_env["log_file"].read_text()
    assert "WARN" in log_content
    assert "DRY-RUN" in log_content
    assert "11111" in log_content


# ============================================================================
# 5. CIRCUIT BREAKER (REQ-PROC-005)
# ============================================================================


def test_circuit_breaker_trips_on_multiple_orphans(mock_env):
    """REQ-PROC-005: 3+ orphans trip the circuit breaker."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    project_dir = mock_env["projects_dir"] / "001-test"
    project_dir.mkdir(parents=True, exist_ok=True)

    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,
        "spawned_processes": [
            {"pid": 10001, "type": "node", "spawned_at": old_time, "purpose": "orphan-1"},
            {"pid": 10002, "type": "node", "spawned_at": old_time, "purpose": "orphan-2"},
            {"pid": 10003, "type": "node", "spawned_at": old_time, "purpose": "orphan-3"},
        ],
        "grace_periods": {"node": 1800, "default": 900},
    })

    killed_pids = set()

    def mock_alive(pid):
        if pid == 1:
            return False  # parent dead
        if pid in killed_pids:
            return False  # already killed
        return True  # all children alive until killed

    def mock_kill(pid, sig):
        killed_pids.add(pid)

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive), \
         patch("os.kill", side_effect=mock_kill):
        result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert result.get("circuit_breaker_tripped") is True
    assert result["orphan_count"] >= 3


def test_circuit_breaker_writes_pause(mock_env):
    """REQ-PROC-005: circuit breaker writes PAUSE to CONTROL.md."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    project_dir = mock_env["projects_dir"] / "001-test"
    project_dir.mkdir(parents=True, exist_ok=True)

    _write_registry(mock_env, {
        "session_id": datetime.now(timezone.utc).isoformat(),
        "project_id": "001-test",
        "parent_pid": 1,
        "spawned_processes": [
            {"pid": 20001, "type": "node", "spawned_at": old_time, "purpose": "orphan-a"},
            {"pid": 20002, "type": "vitest", "spawned_at": old_time, "purpose": "orphan-b"},
            {"pid": 20003, "type": "claude", "spawned_at": old_time, "purpose": "orphan-c"},
        ],
        "grace_periods": {"node": 1800, "vitest": 1800, "claude": 3600, "default": 900},
    })

    killed_pids = set()

    def mock_alive(pid):
        if pid == 1:
            return False  # parent dead
        if pid in killed_pids:
            return False
        return True

    def mock_kill(pid, sig):
        killed_pids.add(pid)

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive), \
         patch("os.kill", side_effect=mock_kill):
        process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    control_file = project_dir / "CONTROL.md"
    assert control_file.exists()
    content = control_file.read_text()
    assert "PAUSE" in content


# ============================================================================
# 6. INTEGRATION (REQ-PROC-006)
# ============================================================================


def test_full_register_sweep_cleanup_cycle(mock_env):
    """REQ-PROC-006: full register -> sweep -> cleanup lifecycle."""
    project_dir = mock_env["projects_dir"] / "001-lifecycle"
    project_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Register processes
    process_monitor.cmd_register(
        pid=50001, proc_type="node", purpose="dev-server",
        registry_file=mock_env["registry_file"],
        log_file=mock_env["log_file"],
    )
    process_monitor.cmd_register(
        pid=50002, proc_type="vitest", purpose="test-runner",
        registry_file=mock_env["registry_file"],
        log_file=mock_env["log_file"],
    )

    registry = _read_registry(mock_env)
    assert len(registry["spawned_processes"]) == 2

    # Step 2: Sweep (all alive, parent alive) -- should not kill anything
    def mock_alive_all(pid):
        return True

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive_all):
        sweep_result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert len(sweep_result["killed"]) == 0
    assert len(sweep_result["alive"]) == 2

    # Step 3: Set project_id for cleanup
    registry = _read_registry(mock_env)
    registry["project_id"] = "001-lifecycle"
    _write_registry(mock_env, registry)

    # Step 4: Cleanup all project processes
    def mock_alive_for_cleanup(pid):
        return pid in (50001, 50002)

    def mock_kill_noop(pid, sig):
        pass

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive_for_cleanup), \
         patch("os.kill", side_effect=mock_kill_noop):
        cleanup_result = process_monitor.cmd_cleanup(
            project_id="001-lifecycle",
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert cleanup_result["status"] == "cleaned"
    assert cleanup_result["killed_count"] == 2

    # Verify registry is empty after cleanup
    final_registry = _read_registry(mock_env)
    assert len(final_registry["spawned_processes"]) == 0

    # Verify log file has entries
    log_content = mock_env["log_file"].read_text()
    assert "REGISTER" in log_content
    assert "CLEANUP" in log_content


def test_sweep_double_kill_prevention(mock_env):
    """F-012: Second sweep after killing processes should not try to kill already-dead PIDs."""
    # Register a process
    process_monitor.cmd_register(
        pid=60001, proc_type="node", purpose="test-server",
        registry_file=mock_env["registry_file"],
        log_file=mock_env["log_file"],
    )

    kill_calls = []

    def mock_alive_first_sweep(pid):
        # Parent dead, registered process alive for first sweep
        if pid == mock_env.get("parent_pid", 1):
            return False
        return pid == 60001 and len(kill_calls) == 0

    def mock_alive_second_sweep(pid):
        # Parent dead, registered process now dead (killed in first sweep)
        if pid == mock_env.get("parent_pid", 1):
            return False
        return False

    def mock_verify_identity(pid, expected_type):
        return True

    def mock_kill_process(pid, log_file=None, expected_type=None):
        kill_calls.append(pid)
        return True

    # First sweep: kills the orphan
    registry = _read_registry(mock_env)
    registry["parent_pid"] = 1  # dead parent
    registry["spawned_processes"][0]["spawned_at"] = "2020-01-01T00:00:00+00:00"  # past grace
    _write_registry(mock_env, registry)

    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive_first_sweep), \
         patch.object(process_monitor, "_verify_process_identity", side_effect=mock_verify_identity), \
         patch.object(process_monitor, "_kill_process", side_effect=mock_kill_process):
        first_result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    assert len(first_result["killed"]) == 1
    assert kill_calls == [60001]

    # Second sweep: process is dead, should appear in "dead" not "killed"
    kill_calls.clear()
    with patch.object(process_monitor, "_is_pid_alive", side_effect=mock_alive_second_sweep):
        second_result = process_monitor.cmd_sweep(
            registry_file=mock_env["registry_file"],
            log_file=mock_env["log_file"],
        )

    # No kills on second sweep - process was removed from registry after first kill
    assert len(second_result["killed"]) == 0
    assert kill_calls == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
