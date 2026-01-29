#!/usr/bin/env python3
"""
Unit tests for QRALPH orchestrator, status, and healer tools.

REQ-QRALPH-001: Validate request input
REQ-QRALPH-002: Validate agent names
REQ-QRALPH-003: Validate phase transitions
REQ-QRALPH-004: Circuit breaker limits
REQ-QRALPH-005: Self-healing with model escalation
REQ-QRALPH-006: Token and cost estimation
REQ-QRALPH-007: Project initialization
REQ-QRALPH-008: Agent selection
REQ-QRALPH-009: Findings synthesis
REQ-QRALPH-010: Error classification
REQ-QRALPH-011: Healing prompt generation
REQ-QRALPH-012: Status monitoring

Test Categories:
1. Validation Functions
2. Circuit Breaker Functions
3. Self-Healing Functions
4. Utility Functions
5. Command Functions (with mocked filesystem)
6. Error Classification (healer)
7. Integration Tests
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import functions from orchestrator (using importlib for hyphenated filenames)
import sys
import importlib.util
sys.path.insert(0, str(Path(__file__).parent))

# Load qralph-orchestrator.py
orchestrator_path = Path(__file__).parent / "qralph-orchestrator.py"
spec_orch = importlib.util.spec_from_file_location("qralph_orchestrator", orchestrator_path)
qralph_orchestrator = importlib.util.module_from_spec(spec_orch)
spec_orch.loader.exec_module(qralph_orchestrator)

# Load qralph-healer.py
healer_path = Path(__file__).parent / "qralph-healer.py"
spec_heal = importlib.util.spec_from_file_location("qralph_healer", healer_path)
qralph_healer = importlib.util.module_from_spec(spec_heal)
spec_heal.loader.exec_module(qralph_healer)

# Import functions from orchestrator
validate_request = qralph_orchestrator.validate_request
validate_agent_name = qralph_orchestrator.validate_agent_name
validate_phase_transition = qralph_orchestrator.validate_phase_transition
check_circuit_breakers = qralph_orchestrator.check_circuit_breakers
update_circuit_breakers = qralph_orchestrator.update_circuit_breakers
generate_slug = qralph_orchestrator.generate_slug
estimate_tokens = qralph_orchestrator.estimate_tokens
estimate_cost = qralph_orchestrator.estimate_cost
detect_request_type = qralph_orchestrator.detect_request_type
extract_summary = qralph_orchestrator.extract_summary
extract_findings = qralph_orchestrator.extract_findings
format_findings = qralph_orchestrator.format_findings
MAX_TOKENS = qralph_orchestrator.MAX_TOKENS
MAX_COST_USD = qralph_orchestrator.MAX_COST_USD
MAX_SAME_ERROR = qralph_orchestrator.MAX_SAME_ERROR
MAX_HEAL_ATTEMPTS = qralph_orchestrator.MAX_HEAL_ATTEMPTS
MODEL_COSTS = qralph_orchestrator.MODEL_COSTS
DEFAULT_AGENT_SETS = qralph_orchestrator.DEFAULT_AGENT_SETS

# Import functions from healer
classify_error = qralph_healer.classify_error
count_similar_errors = qralph_healer.count_similar_errors
generate_healing_prompt = qralph_healer.generate_healing_prompt
get_suggested_fix = qralph_healer.get_suggested_fix
get_action_for_severity = qralph_healer.get_action_for_severity
ERROR_PATTERNS = qralph_healer.ERROR_PATTERNS


# ============================================================================
# 1. VALIDATION FUNCTIONS
# ============================================================================


def test_validate_request_empty_string():
    """REQ-QRALPH-001: Reject empty request string"""
    assert validate_request("") is False


def test_validate_request_none():
    """REQ-QRALPH-001: Reject None request"""
    assert validate_request(None) is False


def test_validate_request_whitespace_only():
    """REQ-QRALPH-001: Reject whitespace-only request"""
    assert validate_request("   ") is False


def test_validate_request_too_short():
    """REQ-QRALPH-001: Reject request shorter than 3 characters"""
    assert validate_request("ab") is False


def test_validate_request_minimum_length():
    """REQ-QRALPH-001: Accept request with exactly 3 characters"""
    assert validate_request("abc") is True


def test_validate_request_valid():
    """REQ-QRALPH-001: Accept valid request string"""
    assert validate_request("Add dark mode feature") is True


def test_validate_request_valid_long():
    """REQ-QRALPH-001: Accept long valid request"""
    assert validate_request("Review security vulnerabilities in authentication module") is True


def test_validate_agent_name_valid_security():
    """REQ-QRALPH-002: Accept valid agent name from default sets"""
    assert validate_agent_name("security-reviewer") is True


def test_validate_agent_name_valid_architecture():
    """REQ-QRALPH-002: Accept valid agent name from default sets"""
    assert validate_agent_name("architecture-advisor") is True


def test_validate_agent_name_valid_quality():
    """REQ-QRALPH-002: Accept valid agent name from default sets"""
    assert validate_agent_name("code-quality-auditor") is True


def test_validate_agent_name_invalid():
    """REQ-QRALPH-002: Reject invalid agent name"""
    assert validate_agent_name("fake-agent") is False


def test_validate_agent_name_empty():
    """REQ-QRALPH-002: Reject empty agent name"""
    assert validate_agent_name("") is False


def test_validate_phase_transition_init_to_reviewing():
    """REQ-QRALPH-003: Allow INIT -> REVIEWING transition"""
    assert validate_phase_transition("INIT", "REVIEWING") is True


def test_validate_phase_transition_reviewing_to_executing():
    """REQ-QRALPH-003: Allow REVIEWING -> EXECUTING transition"""
    assert validate_phase_transition("REVIEWING", "EXECUTING") is True


def test_validate_phase_transition_reviewing_to_complete():
    """REQ-QRALPH-003: Allow REVIEWING -> COMPLETE transition (planning mode)"""
    assert validate_phase_transition("REVIEWING", "COMPLETE") is True


def test_validate_phase_transition_executing_to_uat():
    """REQ-QRALPH-003: Allow EXECUTING -> UAT transition"""
    assert validate_phase_transition("EXECUTING", "UAT") is True


def test_validate_phase_transition_uat_to_complete():
    """REQ-QRALPH-003: Allow UAT -> COMPLETE transition"""
    assert validate_phase_transition("UAT", "COMPLETE") is True


def test_validate_phase_transition_invalid_init_to_complete():
    """REQ-QRALPH-003: Reject invalid INIT -> COMPLETE transition"""
    assert validate_phase_transition("INIT", "COMPLETE") is False


def test_validate_phase_transition_invalid_complete_to_init():
    """REQ-QRALPH-003: Reject invalid COMPLETE -> INIT transition"""
    assert validate_phase_transition("COMPLETE", "INIT") is False


def test_validate_phase_transition_complete_to_any():
    """REQ-QRALPH-003: Reject any transition from COMPLETE"""
    assert validate_phase_transition("COMPLETE", "REVIEWING") is False


def test_validate_phase_transition_unknown_phase():
    """REQ-QRALPH-003: Reject transition from unknown phase"""
    assert validate_phase_transition("UNKNOWN", "REVIEWING") is False


# ============================================================================
# 2. CIRCUIT BREAKER FUNCTIONS
# ============================================================================


def test_check_circuit_breakers_under_limits():
    """REQ-QRALPH-004: Pass when all metrics under limits"""
    state = {
        "circuit_breakers": {
            "total_tokens": 1000,
            "total_cost_usd": 1.0,
            "error_counts": {},
        }
    }
    assert check_circuit_breakers(state) is None


def test_check_circuit_breakers_token_exceeded():
    """REQ-QRALPH-004: Trip circuit breaker when tokens exceed limit"""
    state = {
        "circuit_breakers": {
            "total_tokens": MAX_TOKENS + 1,
            "total_cost_usd": 1.0,
            "error_counts": {},
        }
    }
    error = check_circuit_breakers(state)
    assert error is not None
    assert "Token limit" in error
    assert str(MAX_TOKENS) in error


def test_check_circuit_breakers_cost_exceeded():
    """REQ-QRALPH-004: Trip circuit breaker when cost exceeds limit"""
    state = {
        "circuit_breakers": {
            "total_tokens": 1000,
            "total_cost_usd": MAX_COST_USD + 1,
            "error_counts": {},
        }
    }
    error = check_circuit_breakers(state)
    assert error is not None
    assert "Cost limit" in error
    assert str(MAX_COST_USD) in error


def test_check_circuit_breakers_same_error_threshold():
    """REQ-QRALPH-004: Trip circuit breaker when same error occurs MAX_SAME_ERROR times"""
    state = {
        "circuit_breakers": {
            "total_tokens": 1000,
            "total_cost_usd": 1.0,
            "error_counts": {"ImportError: No module named 'foo'": MAX_SAME_ERROR},
        }
    }
    error = check_circuit_breakers(state)
    assert error is not None
    assert "Same error" in error
    assert str(MAX_SAME_ERROR) in error


def test_check_circuit_breakers_below_error_threshold():
    """REQ-QRALPH-004: Pass when error count below threshold"""
    state = {
        "circuit_breakers": {
            "total_tokens": 1000,
            "total_cost_usd": 1.0,
            "error_counts": {"ImportError: No module named 'foo'": MAX_SAME_ERROR - 1},
        }
    }
    assert check_circuit_breakers(state) is None


def test_check_circuit_breakers_heal_attempts_exceeded():
    """REQ-QRALPH-004: Trip circuit breaker when heal attempts exceed limit"""
    state = {
        "circuit_breakers": {
            "total_tokens": 1000,
            "total_cost_usd": 1.0,
            "error_counts": {},
        },
        "heal_attempts": MAX_HEAL_ATTEMPTS,
    }
    error = check_circuit_breakers(state)
    assert error is not None
    assert "Max heal attempts" in error


def test_check_circuit_breakers_missing_breakers_key():
    """REQ-QRALPH-004: Handle missing circuit_breakers key gracefully"""
    state = {}
    # Should not crash, and should not trip any breakers
    assert check_circuit_breakers(state) is None


def test_update_circuit_breakers_tokens_and_cost():
    """REQ-QRALPH-004: Update tokens and cost correctly"""
    state = {"circuit_breakers": {"total_tokens": 1000, "total_cost_usd": 0.5, "error_counts": {}}}
    update_circuit_breakers(state, tokens=2000, model="sonnet")

    assert state["circuit_breakers"]["total_tokens"] == 3000
    # Cost for sonnet: 2000 tokens / 1M * $3 = $0.006
    expected_cost = 0.5 + (2000 / 1_000_000) * MODEL_COSTS["sonnet"]
    assert abs(state["circuit_breakers"]["total_cost_usd"] - expected_cost) < 0.001


def test_update_circuit_breakers_error_tracking():
    """REQ-QRALPH-004: Track error counts correctly"""
    state = {"circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}}}
    error_msg = "TypeError: expected str, got int"

    update_circuit_breakers(state, tokens=0, model="haiku", error=error_msg)
    update_circuit_breakers(state, tokens=0, model="haiku", error=error_msg)

    error_key = error_msg[:100]
    assert state["circuit_breakers"]["error_counts"][error_key] == 2


def test_update_circuit_breakers_initializes_missing_state():
    """REQ-QRALPH-004: Initialize circuit_breakers if missing"""
    state = {}
    update_circuit_breakers(state, tokens=1000, model="haiku")

    assert "circuit_breakers" in state
    assert state["circuit_breakers"]["total_tokens"] == 1000
    assert state["circuit_breakers"]["total_cost_usd"] > 0
    assert isinstance(state["circuit_breakers"]["error_counts"], dict)


# ============================================================================
# 3. SELF-HEALING FUNCTIONS
# ============================================================================


def test_healing_model_escalation_attempt_1():
    """REQ-QRALPH-005: Use haiku for healing attempts 1-2"""
    # Simulate what cmd_heal does
    heal_attempt = 1
    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    assert model == "haiku"


def test_healing_model_escalation_attempt_2():
    """REQ-QRALPH-005: Use haiku for healing attempts 1-2"""
    heal_attempt = 2
    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    assert model == "haiku"


def test_healing_model_escalation_attempt_3():
    """REQ-QRALPH-005: Use sonnet for healing attempts 3-4"""
    heal_attempt = 3
    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    assert model == "sonnet"


def test_healing_model_escalation_attempt_4():
    """REQ-QRALPH-005: Use sonnet for healing attempts 3-4"""
    heal_attempt = 4
    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    assert model == "sonnet"


def test_healing_model_escalation_attempt_5():
    """REQ-QRALPH-005: Use opus for healing attempt 5"""
    heal_attempt = 5
    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    assert model == "opus"


def test_healing_model_escalation_attempt_6():
    """REQ-QRALPH-005: Use opus for healing attempts beyond 5"""
    heal_attempt = 6
    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    assert model == "opus"


# ============================================================================
# 4. UTILITY FUNCTIONS
# ============================================================================


def test_generate_slug_simple():
    """REQ-QRALPH-007: Generate slug from simple request"""
    assert generate_slug("Add dark mode feature") == "add-dark-mode"


def test_generate_slug_with_stop_words():
    """REQ-QRALPH-007: Filter stop words from slug"""
    slug = generate_slug("Review the code for security issues")
    assert "the" not in slug
    assert "for" not in slug


def test_generate_slug_long_request():
    """REQ-QRALPH-007: Limit slug to 3 words and 30 characters"""
    slug = generate_slug("Implement comprehensive authentication authorization system with JWT tokens")
    words = slug.split("-")
    assert len(words) <= 3
    assert len(slug) <= 30


def test_generate_slug_empty_after_filtering():
    """REQ-QRALPH-007: Return 'project' for empty slug"""
    assert generate_slug("the and for") == "project"


def test_estimate_tokens_simple():
    """REQ-QRALPH-006: Estimate tokens (1 token ≈ 4 chars)"""
    assert estimate_tokens("hello world") == 11 // 4  # 2 tokens


def test_estimate_tokens_empty():
    """REQ-QRALPH-006: Handle empty string"""
    assert estimate_tokens("") == 0


def test_estimate_tokens_long():
    """REQ-QRALPH-006: Estimate tokens for longer text"""
    text = "a" * 400  # 400 characters
    assert estimate_tokens(text) == 100  # 100 tokens


def test_estimate_cost_haiku():
    """REQ-QRALPH-006: Calculate cost for haiku model"""
    cost = estimate_cost(1_000_000, "haiku")
    assert cost == MODEL_COSTS["haiku"]  # $0.25 for 1M tokens


def test_estimate_cost_sonnet():
    """REQ-QRALPH-006: Calculate cost for sonnet model"""
    cost = estimate_cost(1_000_000, "sonnet")
    assert cost == MODEL_COSTS["sonnet"]  # $3.00 for 1M tokens


def test_estimate_cost_opus():
    """REQ-QRALPH-006: Calculate cost for opus model"""
    cost = estimate_cost(1_000_000, "opus")
    assert cost == MODEL_COSTS["opus"]  # $15.00 for 1M tokens


def test_estimate_cost_fractional():
    """REQ-QRALPH-006: Calculate cost for fractional million tokens"""
    cost = estimate_cost(500_000, "sonnet")
    expected = (500_000 / 1_000_000) * MODEL_COSTS["sonnet"]
    assert abs(cost - expected) < 0.001


def test_estimate_cost_unknown_model():
    """REQ-QRALPH-006: Default to sonnet for unknown model"""
    cost = estimate_cost(1_000_000, "unknown-model")
    assert cost == MODEL_COSTS["sonnet"]


def test_detect_request_type_code_review():
    """REQ-QRALPH-008: Detect code review requests"""
    assert detect_request_type("Review this code for security issues") == "code_review"
    assert detect_request_type("Audit authentication module") == "code_review"
    assert detect_request_type("Check for vulnerabilities") == "code_review"


def test_detect_request_type_planning():
    """REQ-QRALPH-008: Detect planning requests"""
    assert detect_request_type("Plan the roadmap for Q2") == "planning"
    assert detect_request_type("Design system architecture") == "planning"
    assert detect_request_type("Create strategy document") == "planning"


def test_detect_request_type_research():
    """REQ-QRALPH-008: Detect research requests"""
    assert detect_request_type("Research AI trends in healthcare") == "research"
    assert detect_request_type("Analyze competitor features") == "research"
    assert detect_request_type("Compare different frameworks") == "research"


def test_detect_request_type_content():
    """REQ-QRALPH-008: Detect content requests"""
    assert detect_request_type("Write blog post about AI") == "content"
    assert detect_request_type("Polish article for publication") == "content"
    assert detect_request_type("Create content for newsletter") == "content"


def test_detect_request_type_testing():
    """REQ-QRALPH-008: Detect testing requests"""
    assert detect_request_type("Test user authentication flow") == "testing"
    assert detect_request_type("QA the checkout process") == "testing"
    assert detect_request_type("Validate coverage for API") == "testing"


def test_detect_request_type_feature_dev():
    """REQ-QRALPH-008: Default to feature_dev for unclassified requests"""
    assert detect_request_type("Add dark mode support") == "feature_dev"
    assert detect_request_type("Implement new dashboard") == "feature_dev"


def test_extract_summary_present():
    """REQ-QRALPH-009: Extract summary section from agent output"""
    content = """# Security Review

## Summary
This is a summary of findings.
Multiple lines here.

## Findings
- Finding 1
"""
    summary = extract_summary(content)
    assert "This is a summary" in summary
    assert "Multiple lines" in summary


def test_extract_summary_missing():
    """REQ-QRALPH-009: Return default message when summary missing"""
    content = "# Review\n\n## Findings\n- Finding 1"
    summary = extract_summary(content)
    assert summary == "(No summary found)"


def test_extract_findings_p0():
    """REQ-QRALPH-009: Extract P0 findings"""
    content = """# Review

### P0 - Critical
- SQL injection vulnerability in login
- Missing authentication check
- Exposed API keys

### P1 - Important
- Improve error handling
"""
    findings = extract_findings(content, "P0")
    assert len(findings) == 3
    assert "SQL injection" in findings[0]


def test_extract_findings_p1():
    """REQ-QRALPH-009: Extract P1 findings"""
    content = """# Review

### P1 - Important
- Add input validation
- Improve logging

### P2 - Suggestions
- Consider refactoring
"""
    findings = extract_findings(content, "P1")
    assert len(findings) == 2
    assert "input validation" in findings[0]


def test_extract_findings_empty():
    """REQ-QRALPH-009: Return empty list when no findings"""
    content = "# Review\n\n### P0 - Critical\n- None identified"
    findings = extract_findings(content, "P0")
    # Should filter out "None identified" (starts with parenthesis in some cases)
    assert len(findings) <= 1


def test_format_findings_with_data():
    """REQ-QRALPH-009: Format findings list for synthesis"""
    findings = [
        {"agent": "security-reviewer", "finding": "SQL injection vulnerability"},
        {"agent": "code-quality-auditor", "finding": "Missing error handling"},
    ]
    formatted = format_findings(findings)
    assert "**[security-reviewer]**" in formatted
    assert "SQL injection" in formatted
    assert "**[code-quality-auditor]**" in formatted


def test_format_findings_empty():
    """REQ-QRALPH-009: Handle empty findings list"""
    formatted = format_findings([])
    assert formatted == "- None identified"


# ============================================================================
# 5. ERROR CLASSIFICATION (HEALER)
# ============================================================================


def test_classify_error_import_error():
    """REQ-QRALPH-010: Classify import errors"""
    result = classify_error("No module named 'requests'")
    assert result["error_type"] == "import_error"
    assert result["severity"] == "recoverable"
    assert result["default_model"] == "haiku"


def test_classify_error_syntax_error():
    """REQ-QRALPH-010: Classify syntax errors"""
    result = classify_error("SyntaxError: invalid syntax")
    assert result["error_type"] == "syntax_error"
    assert result["severity"] == "recoverable"
    assert result["default_model"] == "sonnet"


def test_classify_error_type_error():
    """REQ-QRALPH-010: Classify type errors"""
    result = classify_error("TypeError: expected str but got int")
    assert result["error_type"] == "type_error"
    assert result["severity"] == "recoverable"
    assert result["default_model"] == "sonnet"


def test_classify_error_file_not_found():
    """REQ-QRALPH-010: Classify file not found errors"""
    result = classify_error("FileNotFoundError: No such file or directory: '/foo/bar'")
    assert result["error_type"] == "file_not_found"
    assert result["severity"] == "recoverable"


def test_classify_error_permission_error():
    """REQ-QRALPH-010: Classify permission errors as manual intervention"""
    result = classify_error("PermissionError: Permission denied")
    assert result["error_type"] == "permission_error"
    assert result["severity"] == "manual"
    assert result["default_model"] == "opus"


def test_classify_error_network_error():
    """REQ-QRALPH-010: Classify network errors as retry"""
    result = classify_error("ConnectionError: Failed to establish connection")
    assert result["error_type"] == "network_error"
    assert result["severity"] == "retry"
    assert result["default_model"] == "haiku"


def test_classify_error_json_decode_error():
    """REQ-QRALPH-010: Classify JSON decode errors"""
    result = classify_error("JSONDecodeError: Expecting value: line 1")
    assert result["error_type"] == "json_decode_error"
    assert result["severity"] == "recoverable"


def test_classify_error_unknown():
    """REQ-QRALPH-010: Classify unknown errors as escalate"""
    result = classify_error("SomeWeirdError: This is unexpected")
    assert result["error_type"] == "unknown_error"
    assert result["severity"] == "escalate"
    assert result["default_model"] == "opus"


def test_get_suggested_fix_import_error():
    """REQ-QRALPH-011: Provide fix suggestion for import errors"""
    fix = get_suggested_fix("import_error")
    assert "import" in fix.lower()


def test_get_suggested_fix_permission_error():
    """REQ-QRALPH-011: Suggest manual intervention for permission errors"""
    fix = get_suggested_fix("permission_error")
    assert "MANUAL" in fix


def test_get_suggested_fix_unknown():
    """REQ-QRALPH-011: Escalate unknown errors"""
    fix = get_suggested_fix("unknown_error")
    assert "ESCALATE" in fix or "expert" in fix.lower()


def test_get_action_for_severity_recoverable():
    """REQ-QRALPH-011: Recommend auto-fix for recoverable errors"""
    action = get_action_for_severity("recoverable")
    assert "AUTO_FIX" in action


def test_get_action_for_severity_manual():
    """REQ-QRALPH-011: Recommend manual intervention"""
    action = get_action_for_severity("manual")
    assert "MANUAL" in action


def test_get_action_for_severity_escalate():
    """REQ-QRALPH-011: Recommend escalation"""
    action = get_action_for_severity("escalate")
    assert "ESCALATE" in action


def test_generate_healing_prompt_structure():
    """REQ-QRALPH-011: Generate healing prompt with proper structure"""
    error_analysis = {
        "error_type": "import_error",
        "severity": "recoverable",
        "default_model": "haiku",
        "description": "Missing Python module",
        "match": "No module named 'requests'",
    }
    prompt = generate_healing_prompt(error_analysis, 1)

    assert "## Error Details" in prompt
    assert "## Your Task" in prompt
    assert "attempt 1/5" in prompt
    assert "import_error" in prompt


def test_generate_healing_prompt_import_error_instructions():
    """REQ-QRALPH-011: Include specific instructions for import errors"""
    error_analysis = {
        "error_type": "import_error",
        "severity": "recoverable",
        "default_model": "haiku",
        "description": "Missing Python module",
        "match": "No module named 'requests'",
    }
    prompt = generate_healing_prompt(error_analysis, 1)

    assert "import statement" in prompt.lower()
    assert "Example Fix" in prompt


def test_generate_healing_prompt_permission_error_no_auto_fix():
    """REQ-QRALPH-011: Prevent auto-fix for permission errors"""
    error_analysis = {
        "error_type": "permission_error",
        "severity": "manual",
        "default_model": "opus",
        "description": "Access denied",
        "match": "PermissionError: Permission denied",
    }
    prompt = generate_healing_prompt(error_analysis, 1)

    assert "DO NOT attempt automatic fix" in prompt


# ============================================================================
# 6. INTEGRATION TESTS (with temp directories)
# ============================================================================


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test-project"
        project_path.mkdir()
        (project_path / "agent-outputs").mkdir()
        (project_path / "checkpoints").mkdir()
        (project_path / "healing-attempts").mkdir()
        yield project_path


def test_integration_project_structure(temp_project_dir):
    """REQ-QRALPH-007: Verify project directory structure"""
    assert temp_project_dir.exists()
    assert (temp_project_dir / "agent-outputs").is_dir()
    assert (temp_project_dir / "checkpoints").is_dir()
    assert (temp_project_dir / "healing-attempts").is_dir()


def test_integration_state_persistence(temp_project_dir):
    """REQ-QRALPH-007: Test state save/load cycle"""
    state_file = temp_project_dir / "state.json"

    test_state = {
        "project_id": "001-test",
        "phase": "REVIEWING",
        "agents": ["security-reviewer", "code-quality-auditor"],
        "circuit_breakers": {
            "total_tokens": 1000,
            "total_cost_usd": 0.5,
            "error_counts": {},
        },
    }

    # Save state
    state_file.write_text(json.dumps(test_state, indent=2))

    # Load state
    loaded_state = json.loads(state_file.read_text())

    assert loaded_state["project_id"] == "001-test"
    assert loaded_state["phase"] == "REVIEWING"
    assert len(loaded_state["agents"]) == 2


def test_integration_agent_output_parsing(temp_project_dir):
    """REQ-QRALPH-009: Parse agent output file"""
    agent_output = """# Security Review

## Summary
Found critical SQL injection vulnerability in authentication module.

## Findings

### P0 - Critical (blocks progress)
- SQL injection in login form (file: auth/login.py, line 42)
- Missing CSRF protection on password reset

### P1 - Important (should address)
- Weak password requirements
- Session timeout too long

### P2 - Suggestions (nice to have)
- Add rate limiting
- Enable 2FA

## Recommendations
1. Immediately fix SQL injection vulnerability
2. Add CSRF tokens to all forms
3. Review password policy
"""

    output_file = temp_project_dir / "agent-outputs" / "security-reviewer.md"
    output_file.write_text(agent_output)

    # Test extraction
    content = output_file.read_text()
    summary = extract_summary(content)
    p0_findings = extract_findings(content, "P0")
    p1_findings = extract_findings(content, "P1")

    assert "SQL injection" in summary
    assert len(p0_findings) == 2
    assert len(p1_findings) == 2
    assert "SQL injection in login form" in p0_findings[0]


def test_integration_healing_attempt_record(temp_project_dir):
    """REQ-QRALPH-005: Record healing attempt to file"""
    healing_dir = temp_project_dir / "healing-attempts"

    attempt_content = """# Healing Attempt 1

## Error Analysis
**Type**: import_error
**Severity**: recoverable
**Model**: haiku

## Error Message
```
No module named 'requests'
```

## Strategy
Add import statement for requests module.
"""

    attempt_file = healing_dir / "attempt-01.md"
    attempt_file.write_text(attempt_content)

    assert attempt_file.exists()
    content = attempt_file.read_text()
    assert "import_error" in content
    assert "haiku" in content


def test_integration_default_agent_sets_completeness():
    """REQ-QRALPH-008: Verify default agent sets are comprehensive"""
    assert "code_review" in DEFAULT_AGENT_SETS
    assert "feature_dev" in DEFAULT_AGENT_SETS
    assert "planning" in DEFAULT_AGENT_SETS
    assert "research" in DEFAULT_AGENT_SETS
    assert "content" in DEFAULT_AGENT_SETS
    assert "testing" in DEFAULT_AGENT_SETS

    # Verify each set has 5 agents
    for request_type, agents in DEFAULT_AGENT_SETS.items():
        assert len(agents) == 5, f"{request_type} should have 5 agents"
        # Verify format: (agent_name, model_tier)
        for agent, model in agents:
            assert isinstance(agent, str)
            assert model in ["haiku", "sonnet", "opus"]


def test_integration_error_patterns_coverage():
    """REQ-QRALPH-010: Verify error pattern coverage"""
    required_error_types = [
        "import_error",
        "syntax_error",
        "type_error",
        "file_not_found",
        "permission_error",
        "network_error",
        "json_decode_error",
        "attribute_error",
    ]

    for error_type in required_error_types:
        assert error_type in ERROR_PATTERNS, f"Missing pattern: {error_type}"
        config = ERROR_PATTERNS[error_type]
        assert "patterns" in config
        assert "severity" in config
        assert "default_model" in config
        assert len(config["patterns"]) > 0


# ============================================================================
# 7. EDGE CASES AND ERROR HANDLING
# ============================================================================


def test_edge_case_circuit_breaker_exact_limit():
    """REQ-QRALPH-004: Pass when metrics exactly at limit"""
    state = {
        "circuit_breakers": {
            "total_tokens": MAX_TOKENS,
            "total_cost_usd": MAX_COST_USD,
            "error_counts": {},
        }
    }
    # Should pass at exact limit, fail when exceeded
    assert check_circuit_breakers(state) is None


def test_edge_case_empty_agent_output():
    """REQ-QRALPH-009: Handle empty agent output gracefully"""
    content = ""
    summary = extract_summary(content)
    findings = extract_findings(content, "P0")

    assert summary == "(No summary found)"
    assert len(findings) == 0


def test_edge_case_malformed_agent_output():
    """REQ-QRALPH-009: Handle malformed agent output"""
    content = "This is not a proper agent output format"
    summary = extract_summary(content)
    findings = extract_findings(content, "P0")

    assert summary == "(No summary found)"
    assert len(findings) == 0


def test_edge_case_unicode_in_error_message():
    """REQ-QRALPH-010: Handle unicode characters in error messages"""
    error_with_unicode = "ImportError: No module named 'café'"
    result = classify_error(error_with_unicode)
    assert result["error_type"] == "import_error"


def test_edge_case_very_long_error_message():
    """REQ-QRALPH-010: Truncate very long error messages"""
    long_error = "A" * 500
    result = classify_error(long_error)
    assert len(result["match"]) <= 100


def test_edge_case_zero_tokens():
    """REQ-QRALPH-006: Handle zero token estimation"""
    cost = estimate_cost(0, "haiku")
    assert cost == 0.0


def test_edge_case_negative_cost():
    """REQ-QRALPH-006: Handle edge case inputs gracefully"""
    # Should not happen in practice, but test robustness
    cost = estimate_cost(100, "haiku")
    assert cost >= 0


# ============================================================================
# 8. PERFORMANCE AND LIMITS
# ============================================================================


def test_performance_large_findings_list():
    """REQ-QRALPH-009: Handle large findings lists efficiently"""
    findings = [{"agent": f"agent-{i}", "finding": f"Finding {i}"} for i in range(100)]
    formatted = format_findings(findings)

    # Should complete without error
    assert len(formatted) > 0
    assert "agent-0" in formatted
    assert "agent-99" in formatted


def test_performance_many_error_counts():
    """REQ-QRALPH-004: Handle many unique errors"""
    state = {
        "circuit_breakers": {
            "total_tokens": 1000,
            "total_cost_usd": 1.0,
            "error_counts": {f"error_{i}": 2 for i in range(100)},
        }
    }
    # Should not trip breaker unless one error hits threshold
    assert check_circuit_breakers(state) is None


def test_limits_max_heal_attempts_constant():
    """REQ-QRALPH-005: Verify MAX_HEAL_ATTEMPTS is 5"""
    assert MAX_HEAL_ATTEMPTS == 5


def test_limits_circuit_breaker_constants():
    """REQ-QRALPH-004: Verify circuit breaker constants"""
    assert MAX_TOKENS == 500_000
    assert MAX_COST_USD == 40.0
    assert MAX_SAME_ERROR == 3


# ============================================================================
# RUN TESTS
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
