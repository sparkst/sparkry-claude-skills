#!/usr/bin/env python3
"""
Tests for QRALPH Healer v1.0 - Enhanced healing patterns, catastrophic rollback.

Sprint 5A coverage:
- Pattern matching (match found, match not found, record outcome, skip failed fixes)
- Catastrophic rollback
- Build healing context
- Error normalization and signatures
- Security: input sanitization
"""

import json
import pytest
from datetime import datetime
from pathlib import Path

import importlib.util

# Load healer
healer_path = Path(__file__).parent / "qralph-healer.py"
spec = importlib.util.spec_from_file_location("qralph_healer", healer_path)
qralph_healer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qralph_healer)

# Load shared state module
state_mod_path = Path(__file__).parent / "qralph-state.py"
spec_state = importlib.util.spec_from_file_location("qralph_state", state_mod_path)
qralph_state = importlib.util.module_from_spec(spec_state)
spec_state.loader.exec_module(qralph_state)


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Set up mock QRALPH environment for healer tests."""
    qralph_dir = tmp_path / ".qralph"
    projects_dir = qralph_dir / "projects"
    projects_dir.mkdir(parents=True)

    monkeypatch.setattr(qralph_healer, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(qralph_healer, 'QRALPH_DIR', qralph_dir)
    monkeypatch.setattr(qralph_state, 'STATE_FILE', qralph_dir / "current-project.json")

    return tmp_path


def _create_project(mock_env, project_id="001-test"):
    """Helper to create a test project with state."""
    project_path = mock_env / ".qralph" / "projects" / project_id
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "agent-outputs").mkdir(exist_ok=True)
    (project_path / "checkpoints").mkdir(exist_ok=True)
    (project_path / "healing-attempts").mkdir(exist_ok=True)

    state = {
        "project_id": project_id,
        "project_path": str(project_path),
        "request": "Test request",
        "mode": "coding",
        "phase": "EXECUTING",
        "created_at": datetime.now().isoformat(),
        "agents": ["sde-iii", "security-reviewer"],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 1000, "total_cost_usd": 0.5, "error_counts": {}},
    }

    state_file = mock_env / ".qralph" / "current-project.json"
    state_file.write_text(json.dumps(state, indent=2))

    return project_path, state


# ============================================================================
# ERROR NORMALIZATION & SIGNATURES
# ============================================================================


def test_normalize_strips_paths():
    """Normalization replaces absolute paths."""
    result = qralph_healer._normalize_error("FileNotFoundError: /Users/foo/bar/baz.py not found")
    assert "/Users/foo/bar/" not in result
    assert "<PATH>" in result


def test_normalize_strips_line_numbers():
    """Normalization replaces line numbers."""
    result = qralph_healer._normalize_error("SyntaxError at line 42 in file.py")
    assert "line 42" not in result
    assert "line <N>" in result


def test_normalize_strips_timestamps():
    """Normalization replaces timestamps."""
    result = qralph_healer._normalize_error("Error at 2025-01-15T10:30:45 in module")
    assert "2025-01-15T10:30:45" not in result
    assert "<TIMESTAMP>" in result


def test_error_signature_deterministic():
    """Same error produces same signature."""
    sig1 = qralph_healer._error_signature("ImportError: No module named 'foo'")
    sig2 = qralph_healer._error_signature("ImportError: No module named 'foo'")
    assert sig1 == sig2


def test_error_signature_different_for_different_errors():
    """Different errors produce different signatures."""
    sig1 = qralph_healer._error_signature("ImportError: No module named 'foo'")
    sig2 = qralph_healer._error_signature("TypeError: expected str got int")
    assert sig1 != sig2


def test_error_signature_same_after_normalization():
    """Errors that differ only in paths/lines produce same signature."""
    sig1 = qralph_healer._error_signature("Error at line 10 in /path/a/file.py")
    sig2 = qralph_healer._error_signature("Error at line 99 in /path/b/file.py")
    assert sig1 == sig2


# ============================================================================
# PATTERN MATCHING
# ============================================================================


def test_match_pattern_not_found(mock_env):
    """match_healing_pattern returns None for novel errors."""
    project_path, _ = _create_project(mock_env)
    result = qralph_healer.match_healing_pattern("ImportError: No module named 'xyz'", project_path)
    assert result is None


def test_match_pattern_found_after_recording(mock_env):
    """match_healing_pattern returns pattern after recording."""
    project_path, _ = _create_project(mock_env)
    error = "ImportError: No module named 'requests'"
    qralph_healer.record_healing_outcome(error, "pip install requests", "success", project_path)

    result = qralph_healer.match_healing_pattern(error, project_path)
    assert result is not None
    assert result["successful_fix"] == "pip install requests"


def test_record_outcome_success(mock_env):
    """record_healing_outcome stores successful fix."""
    project_path, _ = _create_project(mock_env)
    error = "TypeError: expected str"
    qralph_healer.record_healing_outcome(error, "added str() cast", "success", project_path)

    patterns_file = project_path / "healing-attempts" / "healing-patterns.json"
    assert patterns_file.exists()
    patterns = json.loads(patterns_file.read_text())
    assert len(patterns["patterns"]) == 1
    assert patterns["patterns"][0]["successful_fix"] == "added str() cast"


def test_record_outcome_failure(mock_env):
    """record_healing_outcome stores failed attempt."""
    project_path, _ = _create_project(mock_env)
    error = "ConnectionError: refused"
    qralph_healer.record_healing_outcome(error, "added retry", "failed", project_path)

    patterns = qralph_healer._load_healing_patterns(project_path)
    assert patterns["patterns"][0]["successful_fix"] is None
    assert patterns["patterns"][0]["fixes_attempted"][0]["result"] == "failed"


def test_record_multiple_outcomes(mock_env):
    """Multiple outcomes for same error are tracked."""
    project_path, _ = _create_project(mock_env)
    error = "ImportError: No module named 'foo'"
    qralph_healer.record_healing_outcome(error, "pip install foo", "failed", project_path)
    qralph_healer.record_healing_outcome(error, "pip install foo-lib", "success", project_path)

    pattern = qralph_healer.match_healing_pattern(error, project_path)
    assert len(pattern["fixes_attempted"]) == 2
    assert pattern["successful_fix"] == "pip install foo-lib"


def test_skip_failed_fixes_in_attempt(mock_env, capsys):
    """cmd_attempt includes failed fixes to skip in prompt."""
    project_path, state = _create_project(mock_env)
    error = "ImportError: No module named 'bar'"

    # Record a failed fix
    qralph_healer.record_healing_outcome(error, "pip install bar-wrong", "failed", project_path)

    # Now attempt healing
    result = qralph_healer.cmd_attempt(error)
    assert "Known Failed Fixes" in result["heal_prompt"]
    assert "bar-wrong" in result["heal_prompt"]


# ============================================================================
# BUILD HEALING CONTEXT
# ============================================================================


def test_build_context_includes_phase(mock_env):
    """build_healing_context includes current phase."""
    project_path, state = _create_project(mock_env)
    ctx = qralph_healer.build_healing_context(state, "some error")
    assert ctx["phase"] == "EXECUTING"


def test_build_context_remaining_budget(mock_env):
    """build_healing_context calculates remaining budget."""
    project_path, state = _create_project(mock_env)
    ctx = qralph_healer.build_healing_context(state, "some error")
    assert ctx["remaining_token_budget"] == 499000  # 500000 - 1000
    assert ctx["remaining_cost_budget"] == pytest.approx(39.5)  # 40.0 - 0.5


def test_build_context_known_pattern(mock_env):
    """build_healing_context flags known patterns."""
    project_path, state = _create_project(mock_env)
    error = "ImportError: No module named 'test'"
    qralph_healer.record_healing_outcome(error, "pip install test", "success", project_path)

    ctx = qralph_healer.build_healing_context(state, error)
    assert ctx["known_pattern"] is True
    assert ctx["successful_fix"] == "pip install test"


def test_build_context_novel_error(mock_env):
    """build_healing_context flags novel errors."""
    project_path, state = _create_project(mock_env)
    ctx = qralph_healer.build_healing_context(state, "never seen this before")
    assert ctx["known_pattern"] is False


# ============================================================================
# CATASTROPHIC ROLLBACK
# ============================================================================


def test_catastrophic_rollback_restores_checkpoint(mock_env):
    """catastrophic_rollback restores from last valid checkpoint."""
    project_path, state = _create_project(mock_env)

    # Create a checkpoint at REVIEWING phase
    checkpoint_state = dict(state)
    checkpoint_state["phase"] = "REVIEWING"
    checkpoint_state["heal_attempts"] = 0
    (project_path / "checkpoints" / "state.json").write_text(json.dumps(checkpoint_state, indent=2))

    # Corrupt current state
    state["phase"] = "EXECUTING"
    state["heal_attempts"] = 5

    restored = qralph_healer.catastrophic_rollback(state, project_path)
    assert restored["phase"] == "REVIEWING"
    assert restored["heal_attempts"] == 0


def test_catastrophic_rollback_saves_corrupted(mock_env):
    """catastrophic_rollback saves corrupted state for forensics."""
    project_path, state = _create_project(mock_env)

    checkpoint_state = dict(state)
    checkpoint_state["phase"] = "INIT"
    (project_path / "checkpoints" / "state.json").write_text(json.dumps(checkpoint_state, indent=2))

    qralph_healer.catastrophic_rollback(state, project_path)

    corrupted_files = list((project_path / "healing-attempts").glob("corrupted-state-*.json"))
    assert len(corrupted_files) == 1


def test_catastrophic_rollback_no_checkpoints(mock_env):
    """catastrophic_rollback returns original state when no checkpoints."""
    project_path, state = _create_project(mock_env)
    # Remove checkpoints dir
    import shutil
    shutil.rmtree(project_path / "checkpoints")

    result = qralph_healer.catastrophic_rollback(state, project_path)
    assert result == state


def test_catastrophic_rollback_resets_counters(mock_env):
    """catastrophic_rollback resets heal_attempts and error_counts."""
    project_path, state = _create_project(mock_env)

    checkpoint_state = dict(state)
    checkpoint_state["phase"] = "DISCOVERING"
    (project_path / "checkpoints" / "state.json").write_text(json.dumps(checkpoint_state, indent=2))

    state["heal_attempts"] = 5
    state["circuit_breakers"]["error_counts"] = {"err1": 3, "err2": 2}

    restored = qralph_healer.catastrophic_rollback(state, project_path)
    assert restored["heal_attempts"] == 0
    assert restored["circuit_breakers"]["error_counts"] == {}


def test_catastrophic_rollback_logs_decision(mock_env):
    """catastrophic_rollback writes to decisions.log."""
    project_path, state = _create_project(mock_env)

    checkpoint_state = dict(state)
    (project_path / "checkpoints" / "state.json").write_text(json.dumps(checkpoint_state, indent=2))

    qralph_healer.catastrophic_rollback(state, project_path)

    log = (project_path / "decisions.log").read_text()
    assert "CATASTROPHIC ROLLBACK" in log


# ============================================================================
# EXISTING HEALER FUNCTIONS
# ============================================================================


def test_classify_error_import():
    """classify_error recognizes import errors."""
    result = qralph_healer.classify_error("No module named 'requests'")
    assert result["error_type"] == "import_error"


def test_classify_error_syntax():
    """classify_error recognizes syntax errors."""
    result = qralph_healer.classify_error("SyntaxError: unexpected EOF while parsing")
    assert result["error_type"] == "syntax_error"


def test_classify_error_unknown():
    """classify_error returns unknown for unrecognized errors."""
    result = qralph_healer.classify_error("Something completely unrecognizable happened")
    assert result["error_type"] == "unknown_error"
    assert result["default_model"] == "opus"


def test_analyze_empty_error():
    """cmd_analyze rejects empty error."""
    result = qralph_healer.cmd_analyze("")
    assert "error" in result


def test_generate_healing_prompt_contains_attempt_number():
    """Healing prompt includes attempt number."""
    analysis = qralph_healer.classify_error("ImportError: No module named 'foo'")
    prompt = qralph_healer.generate_healing_prompt(analysis, 3)
    assert "attempt 3/5" in prompt


# ============================================================================
# SECURITY: INPUT SANITIZATION
# ============================================================================


def test_sanitize_request_strips_null_bytes():
    """sanitize_request removes null bytes."""
    # Import orchestrator
    orch_path = Path(__file__).parent / "qralph-orchestrator.py"
    orch_spec = importlib.util.spec_from_file_location("qralph_orch_test", orch_path)
    orch = importlib.util.module_from_spec(orch_spec)
    orch_spec.loader.exec_module(orch)

    result = orch.sanitize_request("test\x00request")
    assert "\x00" not in result
    assert "testrequest" == result


def test_sanitize_request_strips_path_traversal():
    """sanitize_request removes path traversal sequences."""
    orch_path = Path(__file__).parent / "qralph-orchestrator.py"
    orch_spec = importlib.util.spec_from_file_location("qralph_orch_test2", orch_path)
    orch = importlib.util.module_from_spec(orch_spec)
    orch_spec.loader.exec_module(orch)

    result = orch.sanitize_request("../../etc/passwd")
    assert "../" not in result


def test_sanitize_request_truncates_long_input():
    """sanitize_request limits to 2000 chars."""
    orch_path = Path(__file__).parent / "qralph-orchestrator.py"
    orch_spec = importlib.util.spec_from_file_location("qralph_orch_test3", orch_path)
    orch = importlib.util.module_from_spec(orch_spec)
    orch_spec.loader.exec_module(orch)

    result = orch.sanitize_request("a" * 5000)
    assert len(result) == 2000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
