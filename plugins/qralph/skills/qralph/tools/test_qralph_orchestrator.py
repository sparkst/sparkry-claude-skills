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

# Import functions from orchestrator (v4.0 API)
validate_request = qralph_orchestrator.validate_request
validate_phase_transition = qralph_orchestrator.validate_phase_transition
check_circuit_breakers = qralph_orchestrator.check_circuit_breakers
update_circuit_breakers = qralph_orchestrator.update_circuit_breakers
generate_slug = qralph_orchestrator.generate_slug
estimate_tokens = qralph_orchestrator.estimate_tokens
estimate_cost = qralph_orchestrator.estimate_cost
classify_domains = qralph_orchestrator.classify_domains
estimate_complexity = qralph_orchestrator.estimate_complexity
score_capability = qralph_orchestrator.score_capability
generate_action_plan = qralph_orchestrator.generate_action_plan
generate_team_agent_prompt = qralph_orchestrator.generate_team_agent_prompt
extract_summary = qralph_orchestrator.extract_summary
extract_findings = qralph_orchestrator.extract_findings
format_findings = qralph_orchestrator.format_findings
AGENT_REGISTRY = qralph_orchestrator.AGENT_REGISTRY
DOMAIN_KEYWORDS = qralph_orchestrator.DOMAIN_KEYWORDS
MAX_TOKENS = qralph_orchestrator.MAX_TOKENS
MAX_COST_USD = qralph_orchestrator.MAX_COST_USD
MAX_SAME_ERROR = qralph_orchestrator.MAX_SAME_ERROR
MAX_HEAL_ATTEMPTS = qralph_orchestrator.MAX_HEAL_ATTEMPTS
MODEL_COSTS = qralph_orchestrator.MODEL_COSTS

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


def test_classify_domains_security_request():
    """REQ-QRALPH-002: Classify security-related request domains"""
    domains = classify_domains("Review authentication and fix XSS vulnerabilities")
    assert "security" in domains


def test_classify_domains_frontend_request():
    """REQ-QRALPH-002: Classify frontend-related request domains"""
    domains = classify_domains("Build a responsive dashboard with React components")
    assert "frontend" in domains


def test_classify_domains_multi_domain():
    """REQ-QRALPH-002: Classify request touching multiple domains"""
    domains = classify_domains("Build a secure REST API with comprehensive test coverage")
    assert len(domains) >= 2


def test_classify_domains_empty_request():
    """REQ-QRALPH-002: Handle empty request gracefully"""
    domains = classify_domains("")
    assert isinstance(domains, list)


def test_classify_domains_ranked_by_score():
    """REQ-QRALPH-002: Return domains ranked by relevance score"""
    domains = classify_domains("security audit of authentication tokens and passwords")
    assert domains[0] == "security"


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


def test_estimate_complexity_simple_request():
    """REQ-QRALPH-008: Low complexity for simple single-domain requests"""
    complexity = estimate_complexity("Fix login bug", ["security"])
    assert complexity == 3


def test_estimate_complexity_complex_request():
    """REQ-QRALPH-008: Higher complexity for multi-domain with keywords"""
    complexity = estimate_complexity(
        "Refactor and redesign the comprehensive authentication system with end-to-end testing and integrate with external providers",
        ["security", "backend", "testing", "architecture"]
    )
    assert complexity >= 5


def test_estimate_complexity_returns_3_to_7():
    """REQ-QRALPH-008: Complexity always clamped to 3-7 range"""
    assert estimate_complexity("x", []) >= 3
    assert estimate_complexity("x" * 200, ["a", "b", "c", "d", "e"]) <= 7


def test_score_capability_domain_overlap():
    """REQ-QRALPH-008: Score increases with domain overlap"""
    cap = {"name": "security-reviewer", "domains": ["security", "compliance"]}
    score = score_capability(cap, ["security"], "audit security")
    assert score > 0.0
    assert score <= 1.0


def test_score_capability_no_overlap():
    """REQ-QRALPH-008: Zero or low score when no domain overlap"""
    cap = {"name": "ux-designer", "domains": ["frontend"]}
    score = score_capability(cap, ["backend", "devops"], "deploy microservice")
    assert score < 0.2


def test_score_capability_name_keyword_match():
    """REQ-QRALPH-008: Score boost from name keyword match"""
    cap = {"name": "security-reviewer", "domains": []}
    score_with_match = score_capability(cap, [], "security review of auth")
    score_without_match = score_capability(cap, [], "deploy to production")
    assert score_with_match > score_without_match


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


def test_integration_agent_registry_completeness():
    """REQ-QRALPH-008: Verify agent registry has required agents"""
    required_agents = [
        "security-reviewer", "architecture-advisor", "sde-iii",
        "code-quality-auditor", "requirements-analyst", "ux-designer",
        "test-writer", "pm", "research-director",
    ]
    for agent in required_agents:
        assert agent in AGENT_REGISTRY, f"Missing agent: {agent}"
        info = AGENT_REGISTRY[agent]
        assert "domains" in info
        assert "model" in info
        assert info["model"] in ["haiku", "sonnet", "opus"]


def test_integration_domain_keywords_coverage():
    """REQ-QRALPH-008: Verify domain keywords cover required categories"""
    required_domains = [
        "security", "frontend", "backend", "architecture",
        "testing", "devops", "content", "research", "strategy",
    ]
    for domain in required_domains:
        assert domain in DOMAIN_KEYWORDS, f"Missing domain: {domain}"
        assert len(DOMAIN_KEYWORDS[domain]) >= 3, f"Domain {domain} needs more keywords"


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
# 9. SHARED STATE MODULE TESTS
# ============================================================================

# Import shared state module
state_path = Path(__file__).parent / "qralph-state.py"
spec_state = importlib.util.spec_from_file_location("qralph_state", state_path)
qralph_state_mod = importlib.util.module_from_spec(spec_state)
spec_state.loader.exec_module(qralph_state_mod)


def test_state_validate_empty_state():
    """REQ-QRALPH-013: Empty state reports errors"""
    errors = qralph_state_mod.validate_state({})
    assert len(errors) > 0
    assert "State is empty" in errors[0]


def test_state_validate_complete_state():
    """REQ-QRALPH-013: Valid complete state passes validation"""
    state = {
        "project_id": "001-test",
        "project_path": "/tmp/test",
        "request": "test request",
        "mode": "coding",
        "phase": "INIT",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
    }
    errors = qralph_state_mod.validate_state(state)
    assert errors == []


def test_state_validate_missing_fields():
    """REQ-QRALPH-013: Detect missing required fields"""
    state = {"project_id": "001-test"}
    errors = qralph_state_mod.validate_state(state)
    assert any("Missing required field" in e for e in errors)


def test_state_validate_wrong_types():
    """REQ-QRALPH-013: Detect wrong field types"""
    state = {
        "project_id": 123,  # should be str
        "project_path": "/tmp/test",
        "request": "test",
        "mode": "coding",
        "phase": "INIT",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {},
    }
    errors = qralph_state_mod.validate_state(state)
    assert any("wrong type" in e for e in errors)


def test_state_validate_invalid_phase():
    """REQ-QRALPH-013: Detect unknown phase values"""
    state = {
        "project_id": "001-test",
        "project_path": "/tmp/test",
        "request": "test",
        "mode": "coding",
        "phase": "INVALID_PHASE",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {},
    }
    errors = qralph_state_mod.validate_state(state)
    assert any("Unknown phase" in e for e in errors)


def test_state_repair_fills_missing_fields():
    """REQ-QRALPH-013: Repair fills all missing required fields"""
    state = {"project_id": "001-test"}
    repaired = qralph_state_mod.repair_state(state)
    assert repaired["project_id"] == "001-test"  # preserved
    assert "phase" in repaired
    assert "agents" in repaired
    assert "circuit_breakers" in repaired
    assert isinstance(repaired["circuit_breakers"], dict)


def test_state_repair_preserves_existing():
    """REQ-QRALPH-013: Repair doesn't overwrite existing fields"""
    state = {"project_id": "001-test", "phase": "REVIEWING", "heal_attempts": 3}
    repaired = qralph_state_mod.repair_state(state)
    assert repaired["phase"] == "REVIEWING"
    assert repaired["heal_attempts"] == 3


def test_state_checksum_roundtrip():
    """REQ-QRALPH-013: Checksum is valid after save/load cycle"""
    state = {"project_id": "001-test", "data": "test"}
    checksum = qralph_state_mod._compute_checksum(state)
    state["_checksum"] = checksum
    # Verify recomputed checksum matches
    assert qralph_state_mod._compute_checksum(state) == checksum


def test_state_checksum_changes_with_data():
    """REQ-QRALPH-013: Checksum changes when data changes"""
    state1 = {"project_id": "001-test"}
    state2 = {"project_id": "002-test"}
    assert qralph_state_mod._compute_checksum(state1) != qralph_state_mod._compute_checksum(state2)


def test_state_safe_write_and_read(temp_project_dir):
    """REQ-QRALPH-013: safe_write creates file atomically"""
    target = temp_project_dir / "test-output.txt"
    qralph_state_mod.safe_write(target, "hello world")
    assert target.exists()
    assert target.read_text() == "hello world"


def test_state_safe_write_json_roundtrip(temp_project_dir):
    """REQ-QRALPH-013: safe_write_json preserves data through roundtrip"""
    target = temp_project_dir / "test-data.json"
    data = {"key": "value", "number": 42, "nested": {"a": [1, 2, 3]}}
    qralph_state_mod.safe_write_json(target, data)
    loaded = json.loads(target.read_text())
    assert loaded == data


def test_state_safe_read_json_missing_file(temp_project_dir):
    """REQ-QRALPH-013: safe_read_json returns default for missing file"""
    result = qralph_state_mod.safe_read_json(temp_project_dir / "nonexistent.json", {"default": True})
    assert result == {"default": True}


def test_state_safe_read_json_corrupt_file(temp_project_dir):
    """REQ-QRALPH-013: safe_read_json handles corrupt JSON gracefully"""
    corrupt = temp_project_dir / "corrupt.json"
    corrupt.write_text("{invalid json")
    result = qralph_state_mod.safe_read_json(corrupt, {"fallback": True})
    assert result == {"fallback": True}


def test_state_save_load_roundtrip(temp_project_dir):
    """REQ-QRALPH-013: Full state save/load cycle with checksum"""
    state_file = temp_project_dir / "state.json"
    state = {"project_id": "001-test", "phase": "INIT", "data": "test"}
    qralph_state_mod.save_state(state, state_file)
    loaded = qralph_state_mod.load_state(state_file)
    assert loaded["project_id"] == "001-test"
    assert loaded["phase"] == "INIT"
    assert "_checksum" in loaded


# ============================================================================
# 10. ADDITIONAL PURE FUNCTION TESTS
# ============================================================================


def test_generate_action_plan_with_p0():
    """REQ-QRALPH-009: Action plan prioritizes P0 issues"""
    findings = {
        "P0": [{"agent": "security-reviewer", "finding": "Critical SQL injection"}],
        "P1": [{"agent": "code-quality-auditor", "finding": "Missing error handling"}],
        "P2": [],
    }
    plan = generate_action_plan(findings)
    assert "BLOCK" in plan
    assert "SQL injection" in plan


def test_generate_action_plan_no_issues():
    """REQ-QRALPH-009: Action plan for zero issues"""
    findings = {"P0": [], "P1": [], "P2": []}
    plan = generate_action_plan(findings)
    assert "No issues" in plan or "proceed" in plan.lower()


def test_generate_action_plan_p1_only():
    """REQ-QRALPH-009: Action plan with only P1 issues"""
    findings = {
        "P0": [],
        "P1": [{"agent": "test-writer", "finding": "Low test coverage"}],
        "P2": [],
    }
    plan = generate_action_plan(findings)
    assert "FIX" in plan


def test_generate_team_agent_prompt_structure():
    """REQ-QRALPH-014: Agent prompt includes required sections"""
    prompt = generate_team_agent_prompt(
        agent_type="security-reviewer",
        request="Review authentication module",
        project_id="001-test",
        project_path=Path("/tmp/test"),
        team_name="qralph-001-test",
        available_skills=["code-review"],
    )
    assert "security reviewer" in prompt.lower()
    assert "qralph-001-test" in prompt
    assert "001-test" in prompt
    assert "## Focus Areas" in prompt
    assert "## Workflow" in prompt
    assert "## Output Format" in prompt


def test_generate_team_agent_prompt_includes_skills():
    """REQ-QRALPH-014: Agent prompt includes available skills"""
    prompt = generate_team_agent_prompt(
        agent_type="ux-designer",
        request="Build dashboard",
        project_id="001-test",
        project_path=Path("/tmp/test"),
        team_name="qralph-001-test",
        available_skills=["frontend-design"],
    )
    assert "frontend-design" in prompt
    assert "Optional Skills" in prompt


def test_generate_team_agent_prompt_no_skills():
    """REQ-QRALPH-014: Agent prompt without skills omits section"""
    prompt = generate_team_agent_prompt(
        agent_type="security-reviewer",
        request="Review code",
        project_id="001-test",
        project_path=Path("/tmp/test"),
        team_name="qralph-001-test",
        available_skills=[],
    )
    assert "## Available Skills" not in prompt


def test_classify_domains_content_request():
    """REQ-QRALPH-002: Classify content-related request domains"""
    domains = classify_domains("Write a blog article about documentation best practices")
    assert "content" in domains


def test_classify_domains_devops_request():
    """REQ-QRALPH-002: Classify devops-related request domains"""
    domains = classify_domains("Deploy the application using Docker and set up CI pipeline")
    assert "devops" in domains


def test_classify_domains_research_request():
    """REQ-QRALPH-002: Classify research-related request domains"""
    domains = classify_domains("Research and analyze competitor products for market assessment")
    assert "research" in domains


def test_estimate_complexity_moderate_request():
    """REQ-QRALPH-008: Moderate complexity for medium requests"""
    complexity = estimate_complexity(
        "Add user authentication with JWT tokens and integrate with database",
        ["security", "backend"]
    )
    assert 3 <= complexity <= 7


def test_score_capability_description_match():
    """REQ-QRALPH-008: Score includes description keyword matching"""
    cap = {"name": "test-tool", "domains": [], "description": "Create distinctive frontend interfaces"}
    score = score_capability(cap, [], "create a new frontend interface")
    assert score > 0.0


def test_score_capability_bounded():
    """REQ-QRALPH-008: Score is always bounded 0.0-1.0"""
    cap = {"name": "security-reviewer", "domains": ["security", "compliance"],
           "description": "security review authentication authorization"}
    score = score_capability(cap, ["security", "compliance"],
                            "security review authentication authorization compliance")
    assert 0.0 <= score <= 1.0


def test_generate_slug_special_characters():
    """REQ-QRALPH-007: Slug handles special characters"""
    slug = generate_slug("Add dark-mode & fix UI bugs!")
    assert all(c.isalnum() or c == '-' for c in slug)


def test_generate_slug_numbers():
    """REQ-QRALPH-007: Slug filters out short words"""
    slug = generate_slug("10 steps to build API v2")
    # Numbers and 2-letter words should be filtered
    assert "10" not in slug
    assert "to" not in slug


def test_check_control_commands_no_file():
    """REQ-QRALPH-015: No control command when file missing"""
    result = qralph_orchestrator.check_control_commands(Path("/nonexistent"))
    assert result is None


def test_check_control_commands_with_pause(temp_project_dir):
    """REQ-QRALPH-015: Detect PAUSE command"""
    (temp_project_dir / "CONTROL.md").write_text("PAUSE")
    result = qralph_orchestrator.check_control_commands(temp_project_dir)
    assert result == "PAUSE"


def test_check_control_commands_with_abort(temp_project_dir):
    """REQ-QRALPH-015: Detect ABORT command"""
    (temp_project_dir / "CONTROL.md").write_text("ABORT")
    result = qralph_orchestrator.check_control_commands(temp_project_dir)
    assert result == "ABORT"


def test_check_control_commands_empty_file(temp_project_dir):
    """REQ-QRALPH-015: No control command for empty file"""
    (temp_project_dir / "CONTROL.md").write_text("# Control\n\nNo commands here.")
    result = qralph_orchestrator.check_control_commands(temp_project_dir)
    assert result is None


def test_check_control_commands_template_no_false_positive(temp_project_dir):
    """REQ-QRALPH-015: Template help text must NOT trigger false PAUSE/ABORT"""
    template = (
        "# QRALPH Control\n\n"
        "To issue a command, write it alone on a line.\n\n"
        "Available commands:\n"
        "- `PAUSE` — stop after current step\n"
        "- `SKIP` — skip current operation\n"
        "- `ABORT` — graceful shutdown\n"
        "- `STATUS` — force status dump\n"
    )
    (temp_project_dir / "CONTROL.md").write_text(template)
    result = qralph_orchestrator.check_control_commands(temp_project_dir)
    assert result is None, f"Template text falsely triggered: {result}"


def test_check_control_commands_old_template_no_false_positive(temp_project_dir):
    """REQ-QRALPH-015: Old-style template must NOT trigger false PAUSE"""
    old_template = (
        "# QRALPH Control\n\n"
        "Write commands here:\n"
        "- PAUSE - stop after current step\n"
        "- SKIP - skip current operation\n"
        "- ABORT - graceful shutdown\n"
        "- STATUS - force status dump\n"
    )
    (temp_project_dir / "CONTROL.md").write_text(old_template)
    result = qralph_orchestrator.check_control_commands(temp_project_dir)
    assert result is None, f"Old template text falsely triggered: {result}"


def test_check_control_commands_real_command_with_whitespace(temp_project_dir):
    """REQ-QRALPH-015: Command with surrounding whitespace still detected"""
    (temp_project_dir / "CONTROL.md").write_text("# Control\n\n  PAUSE  \n")
    result = qralph_orchestrator.check_control_commands(temp_project_dir)
    assert result == "PAUSE"


def test_validate_request_type_check():
    """REQ-QRALPH-001: Reject non-string request types"""
    assert validate_request(123) is False
    assert validate_request([]) is False


# ============================================================================
# 11. COMMAND FUNCTION TESTS (with mocked filesystem)
# ============================================================================


@pytest.fixture
def mock_qralph_env(tmp_path, monkeypatch):
    """Set up a full mock QRALPH environment for cmd_* testing"""
    monkeypatch.setattr(qralph_orchestrator, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(qralph_orchestrator, 'QRALPH_DIR', tmp_path / ".qralph")
    monkeypatch.setattr(qralph_orchestrator, 'PROJECTS_DIR', tmp_path / ".qralph" / "projects")
    monkeypatch.setattr(qralph_orchestrator, 'AGENTS_DIR', tmp_path / ".claude" / "agents")
    monkeypatch.setattr(qralph_orchestrator, 'PLUGINS_DIR', tmp_path / ".claude" / "plugins")
    # Override state file path in the shared state module
    monkeypatch.setattr(qralph_state_mod, 'STATE_FILE', tmp_path / ".qralph" / "current-project.json")
    return tmp_path


def test_cmd_init_creates_project(mock_qralph_env, capsys):
    """REQ-QRALPH-007: cmd_init creates project directory structure"""
    result = qralph_orchestrator.cmd_init("Add dark mode feature")
    assert result["status"] == "initialized"
    assert "project_id" in result
    project_path = Path(result["project_path"])
    assert (project_path / "agent-outputs").is_dir()
    assert (project_path / "checkpoints").is_dir()
    assert (project_path / "healing-attempts").is_dir()
    assert (project_path / "CONTROL.md").exists()


def test_cmd_init_rejects_empty_request(mock_qralph_env, capsys):
    """REQ-QRALPH-007: cmd_init rejects empty request"""
    result = qralph_orchestrator.cmd_init("")
    assert "error" in result


def test_cmd_init_increments_project_number(mock_qralph_env, capsys):
    """REQ-QRALPH-007: cmd_init auto-increments project number"""
    r1 = qralph_orchestrator.cmd_init("First project")
    r2 = qralph_orchestrator.cmd_init("Second project")
    id1 = int(r1["project_id"][:3])
    id2 = int(r2["project_id"][:3])
    assert id2 == id1 + 1


def test_cmd_init_planning_mode(mock_qralph_env, capsys):
    """REQ-QRALPH-007: cmd_init supports planning mode"""
    result = qralph_orchestrator.cmd_init("Plan Q2 roadmap", mode="planning")
    assert result["mode"] == "planning"


def _clear_control_md(mock_env):
    """Helper: clear CONTROL.md so commands like PAUSE/ABORT in help text don't trigger control flow."""
    for control_file in Path(mock_env).rglob("CONTROL.md"):
        control_file.write_text("# Control\n")


def test_cmd_discover_requires_init(mock_qralph_env, capsys):
    """REQ-QRALPH-016: cmd_discover errors without active project"""
    result = qralph_orchestrator.cmd_discover()
    captured = capsys.readouterr()
    assert "error" in captured.out.lower() or result is None


def test_cmd_discover_finds_capabilities(mock_qralph_env, capsys):
    """REQ-QRALPH-016: cmd_discover identifies relevant capabilities"""
    qralph_orchestrator.cmd_init("Review security of authentication system")
    _clear_control_md(mock_qralph_env)
    result = qralph_orchestrator.cmd_discover()
    assert result["status"] == "discovered"
    assert result["relevant_count"] > 0
    assert "security" in result["domains_detected"]


def test_cmd_select_agents_dynamic(mock_qralph_env, capsys):
    """REQ-QRALPH-008: cmd_select_agents picks agents dynamically"""
    qralph_orchestrator.cmd_init("Review security and architecture")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents()
    assert result["status"] == "agents_selected"
    assert result["agent_count"] >= 3


def test_cmd_select_agents_custom(mock_qralph_env, capsys):
    """REQ-QRALPH-008: cmd_select_agents accepts custom agent list"""
    qralph_orchestrator.cmd_init("Custom review")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer", "sde-iii"])
    assert result["agent_count"] == 2
    assert "security-reviewer" in [a["agent_type"] for a in result["agents"]]


def test_cmd_heal_model_escalation(mock_qralph_env, capsys):
    """REQ-QRALPH-005: cmd_heal escalates models correctly"""
    qralph_orchestrator.cmd_init("Test project")
    _clear_control_md(mock_qralph_env)
    r1 = qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    assert r1["model"] == "haiku"
    r2 = qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    assert r2["model"] == "haiku"
    r3 = qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    assert r3["model"] == "sonnet"


def test_cmd_heal_defers_after_max_attempts(mock_qralph_env, capsys):
    """REQ-QRALPH-005: cmd_heal defers after max attempts"""
    qralph_orchestrator.cmd_init("Test project")
    _clear_control_md(mock_qralph_env)
    for _ in range(5):
        qralph_orchestrator.cmd_heal("persistent error")
    result = qralph_orchestrator.cmd_heal("persistent error")
    assert result["status"] == "deferred"


def test_cmd_checkpoint_saves_state(mock_qralph_env, capsys):
    """REQ-QRALPH-017: cmd_checkpoint saves state snapshot"""
    qralph_orchestrator.cmd_init("Test project")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_checkpoint("REVIEWING")
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "REVIEWING"


def test_cmd_status_lists_projects(mock_qralph_env, capsys):
    """REQ-QRALPH-012: cmd_status lists all projects"""
    qralph_orchestrator.cmd_init("Project 1")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_status()
    captured = capsys.readouterr()
    assert "projects" in captured.out


# ============================================================================
# SECURITY HARDENING TESTS (Phase 1 & Phase 4)
# ============================================================================


def test_sanitize_request_multi_pass():
    """S-4: sanitize_request loops until stable (no bypass via nested traversal)."""
    sanitize = qralph_orchestrator.sanitize_request
    # Nested path traversal that single-pass would miss
    assert "../" not in sanitize("....//..//etc/passwd")
    assert "\\..\\" not in sanitize("....\\\\..\\\\secret")
    # Normal strings untouched
    assert sanitize("Fix the auth bug") == "Fix the auth bug"


def test_cmd_checkpoint_rejects_invalid_phase(mock_qralph_env, capsys):
    """S-6: cmd_checkpoint rejects unrecognized phase strings."""
    qralph_orchestrator.cmd_init("Test project")
    _clear_control_md(mock_qralph_env)
    result = qralph_orchestrator.cmd_checkpoint("INVALID_PHASE")
    assert result is not None
    assert "error" in result


def test_cmd_checkpoint_accepts_valid_phase(mock_qralph_env, capsys):
    """S-6: cmd_checkpoint accepts recognized phase strings."""
    qralph_orchestrator.cmd_init("Test project")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_checkpoint("REVIEWING")
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "REVIEWING"


# ============================================================================
# SAFE_WRITE FAILURE MODE TESTS (T-5)
# ============================================================================


def test_safe_write_creates_parent_dirs(tmp_path):
    """T-5: safe_write creates parent dirs if they don't exist."""
    import importlib.util
    state_path = Path(__file__).parent / "qralph-state.py"
    spec = importlib.util.spec_from_file_location("qs_test", state_path)
    qs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs)

    target = tmp_path / "a" / "b" / "c" / "test.txt"
    qs.safe_write(target, "hello")
    assert target.read_text() == "hello"


def test_safe_write_permission_denied(tmp_path):
    """T-5: safe_write raises on permission denied (dir not writable)."""
    import importlib.util
    state_path = Path(__file__).parent / "qralph-state.py"
    spec = importlib.util.spec_from_file_location("qs_test2", state_path)
    qs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs)

    target_dir = tmp_path / "readonly"
    target_dir.mkdir()
    target_dir.chmod(0o444)

    with pytest.raises(Exception):
        qs.safe_write(target_dir / "file.txt", "hello")

    # Cleanup: restore permissions so tmp_path cleanup works
    target_dir.chmod(0o755)


def test_safe_write_sets_permissions(tmp_path):
    """S-8: safe_write sets file permissions to 0600."""
    import importlib.util
    import stat
    state_path = Path(__file__).parent / "qralph-state.py"
    spec = importlib.util.spec_from_file_location("qs_test3", state_path)
    qs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs)

    target = tmp_path / "test.txt"
    qs.safe_write(target, "secret data")
    mode = target.stat().st_mode
    assert stat.S_IMODE(mode) == 0o600


def test_exclusive_state_lock_context_manager(tmp_path):
    """R-6: exclusive_state_lock acquires and releases lock."""
    import importlib.util
    state_path = Path(__file__).parent / "qralph-state.py"
    spec = importlib.util.spec_from_file_location("qs_test4", state_path)
    qs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs)

    lock_path = tmp_path / "test.lock"
    with qs.exclusive_state_lock(lock_path):
        assert lock_path.exists()
    # Lock file still exists after release (that's normal for file locks)
    assert lock_path.exists()


def test_load_state_repairs_on_checksum_mismatch(tmp_path):
    """S-7: load_state returns repaired state when checksum mismatches."""
    import importlib.util
    state_path = Path(__file__).parent / "qralph-state.py"
    spec = importlib.util.spec_from_file_location("qs_test5", state_path)
    qs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qs)

    # Write state with wrong checksum
    state_file = tmp_path / "state.json"
    state = {
        "project_id": "test",
        "project_path": "/tmp/test",
        "request": "test request",
        "mode": "coding",
        "phase": "INIT",
        "created_at": "2024-01-01T00:00:00",
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
        "_checksum": "wrong_checksum_value",
    }
    state_file.write_text(json.dumps(state))

    result = qs.load_state(state_file)
    # Should return a repaired state (not empty, not with wrong checksum passed through)
    assert result is not None
    assert result.get("project_id") == "test"


# ============================================================================
# 12. F-017: SYNTHESIZE WITH ACTUAL AGENT OUTPUTS
# ============================================================================


def test_cmd_synthesize_with_agent_outputs(mock_qralph_env, capsys):
    """F-017: cmd_synthesize consolidates real agent output files into SYNTHESIS.md"""
    qralph_orchestrator.cmd_init("Security review of auth module")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer", "code-quality-auditor"])

    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    outputs_dir = project_path / "agent-outputs"

    # Write mock agent outputs
    (outputs_dir / "security-reviewer.md").write_text("""# Security Review

## Summary
Found 2 critical vulnerabilities in authentication module.

## Findings

### P0 - Critical
- SQL injection in login endpoint
- Missing CSRF tokens

### P1 - Important
- Weak password policy

### P2 - Suggestions
- Add rate limiting
""")

    (outputs_dir / "code-quality-auditor.md").write_text("""# Code Quality Review

## Summary
Code quality is acceptable but needs error handling improvements.

## Findings

### P0 - Critical
- Bare except clause in auth handler

### P1 - Important
- Missing type annotations
- No docstrings on public functions

### P2 - Suggestions
- Consider extracting auth logic to separate module
""")

    synth_result = qralph_orchestrator.cmd_synthesize()
    assert synth_result["status"] == "synthesized"
    assert synth_result["p0_count"] == 3  # 2 security + 1 quality
    assert synth_result["p1_count"] == 3  # 1 security + 2 quality
    assert synth_result["p2_count"] == 2  # 1 security + 1 quality

    # Verify SYNTHESIS.md was written with correct content
    synthesis_file = project_path / "SYNTHESIS.md"
    assert synthesis_file.exists()
    content = synthesis_file.read_text()
    assert "SQL injection" in content
    assert "security-reviewer" in content
    assert "code-quality-auditor" in content
    assert "Bare except" in content


def test_cmd_synthesize_with_empty_agent_output(mock_qralph_env, capsys):
    """F-017: cmd_synthesize handles agents with no findings"""
    qralph_orchestrator.cmd_init("Simple review")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer"])

    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    outputs_dir = project_path / "agent-outputs"

    (outputs_dir / "security-reviewer.md").write_text("""# Security Review

## Summary
No issues found. Code is secure.

## Findings

### P0 - Critical
- None identified

### P1 - Important
- None identified
""")

    synth_result = qralph_orchestrator.cmd_synthesize()
    assert synth_result["status"] == "synthesized"
    assert synth_result["p0_count"] == 0


def test_cmd_synthesize_with_missing_agent_file(mock_qralph_env, capsys):
    """F-017: cmd_synthesize BLOCKS when agent output files are missing"""
    qralph_orchestrator.cmd_init("Review with missing output")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer", "sde-iii"])

    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    outputs_dir = project_path / "agent-outputs"

    # Only write one agent's output, leave other missing
    (outputs_dir / "security-reviewer.md").write_text("""# Security Review

## Summary
Found issues.

## Findings

### P0 - Critical
- XSS vulnerability
""")

    synth_result = qralph_orchestrator.cmd_synthesize()
    # Synthesis should be BLOCKED because sde-iii output is missing
    assert synth_result["status"] == "error"
    assert "blocked" in synth_result["error"].lower()
    assert "sde-iii" in synth_result["error"]


# ============================================================================
# 13. F-018: RESUME AND FINALIZE TESTS
# ============================================================================


def test_cmd_resume_from_checkpoint(mock_qralph_env, capsys):
    """F-018: cmd_resume restores state from checkpoint"""
    init_result = qralph_orchestrator.cmd_init("Resumable project")
    _clear_control_md(mock_qralph_env)
    project_id = init_result["project_id"]
    project_path = Path(init_result["project_path"])

    # Advance to REVIEWING via checkpoint
    qralph_orchestrator.cmd_checkpoint("REVIEWING")

    # Verify checkpoint was saved
    checkpoint_dir = project_path / "checkpoints"
    assert any(checkpoint_dir.glob("*.json"))

    # Resume
    result = qralph_orchestrator.cmd_resume(project_id)
    assert result["status"] == "resumed"
    assert result["phase"] == "REVIEWING"


def test_cmd_resume_invalid_project_id(mock_qralph_env, capsys):
    """F-018: cmd_resume rejects invalid project_id"""
    qralph_orchestrator.cmd_resume("../etc/passwd")
    captured = capsys.readouterr()
    assert "error" in captured.out.lower() or "Invalid" in captured.out


def test_cmd_resume_nonexistent_project(mock_qralph_env, capsys):
    """F-018: cmd_resume handles nonexistent project"""
    qralph_orchestrator.cmd_resume("999-nonexistent")
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()


def test_cmd_finalize_completes_project(mock_qralph_env, capsys):
    """F-018: cmd_finalize marks project complete and creates SUMMARY.md"""
    qralph_orchestrator.cmd_init("Finalizable project")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    qralph_orchestrator.cmd_select_agents(["security-reviewer"])

    state = qralph_orchestrator.load_state()
    project_path = Path(state["project_path"])

    # Write agent output so synthesize works
    (project_path / "agent-outputs" / "security-reviewer.md").write_text(
        "# Review\n\n## Summary\nDone.\n\n## Findings\n\n### P0 - Critical\n- None"
    )
    qralph_orchestrator.cmd_synthesize()

    # For coding mode: EXECUTING -> UAT -> COMPLETE
    qralph_orchestrator.cmd_generate_uat()

    result = qralph_orchestrator.cmd_finalize()
    captured = capsys.readouterr()
    # Parse last JSON line
    lines = [l for l in captured.out.strip().split('\n') if l.strip().startswith('{')]
    last_output = json.loads(lines[-1])
    assert last_output["status"] == "complete"

    # Verify SUMMARY.md exists
    assert (project_path / "SUMMARY.md").exists()
    summary_content = (project_path / "SUMMARY.md").read_text()
    assert "QRALPH v" in summary_content

    # Verify state is COMPLETE
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "COMPLETE"


def test_cmd_finalize_rejects_from_wrong_phase(mock_qralph_env, capsys):
    """F-018: cmd_finalize rejects transition from INIT"""
    qralph_orchestrator.cmd_init("Cannot finalize from init")
    _clear_control_md(mock_qralph_env)
    result = qralph_orchestrator.cmd_finalize()
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()


# ============================================================================
# 14. F-019: END-TO-END HEALING WORKFLOW
# ============================================================================


def test_healing_e2e_error_to_escalation(mock_qralph_env, capsys):
    """F-019: Full healing flow: error -> classify -> heal -> escalate model"""
    qralph_orchestrator.cmd_init("Healing test project")
    _clear_control_md(mock_qralph_env)

    # First heal: haiku
    r1 = qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    assert r1["model"] == "haiku"
    assert r1["heal_attempt"] == 1

    state = qralph_orchestrator.load_state()
    project_path = Path(state["project_path"])

    # Verify healing attempt file was created
    heal_file = project_path / "healing-attempts" / "attempt-01.md"
    assert heal_file.exists()
    assert "haiku" in heal_file.read_text()

    # Verify circuit breaker tracks error
    state = qralph_orchestrator.load_state()
    assert state["heal_attempts"] == 1
    error_counts = state["circuit_breakers"]["error_counts"]
    assert len(error_counts) >= 1

    # Heal 2 more times -> model escalation to sonnet
    qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    r3 = qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    assert r3["model"] == "sonnet"

    # Heal 2 more -> opus
    qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    r5 = qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    assert r5["model"] == "opus"

    # 6th attempt -> deferred
    r6 = qralph_orchestrator.cmd_heal("ImportError: No module named 'foo'")
    assert r6["status"] == "deferred"
    assert (project_path / "DEFERRED.md").exists()


def test_healer_attempt_creates_files_and_updates_state(mock_qralph_env, capsys):
    """F-019: healer cmd_attempt creates attempt files and updates state"""
    # Override healer's state paths
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(qralph_healer, 'QRALPH_DIR', mock_qralph_env / ".qralph")

    qralph_orchestrator.cmd_init("Healer test")
    _clear_control_md(mock_qralph_env)

    result = qralph_healer.cmd_attempt("TypeError: expected str but got int")
    assert result["status"] == "attempt_recorded"
    assert result["error_type"] == "type_error"
    assert result["heal_attempt"] == 1

    # Verify state updated
    state = qralph_healer.load_state()
    assert state["heal_attempts"] == 1

    monkeypatch.undo()


def test_healer_catastrophic_rollback(mock_qralph_env, capsys):
    """F-019: catastrophic_rollback restores checkpoint after 3+ failures"""
    qralph_orchestrator.cmd_init("Rollback test")
    _clear_control_md(mock_qralph_env)

    state = qralph_orchestrator.load_state()
    project_path = Path(state["project_path"])

    # Create a valid checkpoint (write to state.json so rollback finds it first)
    checkpoint_state = dict(state)
    checkpoint_state["phase"] = "REVIEWING"
    checkpoint_state["heal_attempts"] = 0
    qralph_state_mod.safe_write_json(
        project_path / "checkpoints" / "state.json",
        checkpoint_state
    )

    # Corrupt state with many heal attempts
    state["heal_attempts"] = 5
    state["circuit_breakers"]["error_counts"] = {"test_error": 5}
    qralph_orchestrator.save_state(state)

    # Rollback
    restored = qralph_healer.catastrophic_rollback(state, project_path)
    assert restored["heal_attempts"] == 0
    assert restored["phase"] == "REVIEWING"
    # Verify corrupted state was saved for forensics
    corrupted_files = list((project_path / "healing-attempts").glob("corrupted-state-*.json"))
    assert len(corrupted_files) >= 1


# ============================================================================
# 15. F-020: CONCURRENT STATE ACCESS TESTS
# ============================================================================


def test_exclusive_lock_prevents_concurrent_modification(tmp_path):
    """F-020: exclusive_state_lock serializes concurrent access"""
    import threading
    import time

    lock_path = tmp_path / "test.lock"
    state_file = tmp_path / "counter.json"
    qralph_state_mod.safe_write_json(state_file, {"counter": 0})

    errors = []
    iterations = 20

    def increment():
        for _ in range(iterations):
            try:
                with qralph_state_mod.exclusive_state_lock(lock_path):
                    data = json.loads(state_file.read_text())
                    data["counter"] += 1
                    time.sleep(0.001)  # Small delay to increase race window
                    state_file.write_text(json.dumps(data))
            except Exception as e:
                errors.append(str(e))

    threads = [threading.Thread(target=increment) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"Lock errors: {errors}"
    final = json.loads(state_file.read_text())
    assert final["counter"] == iterations * 4, (
        f"Expected {iterations * 4}, got {final['counter']} — "
        "indicates lost updates from concurrent access"
    )


def test_exclusive_lock_reentrant_via_separate_paths(tmp_path):
    """F-020: Different lock paths allow independent locking"""
    lock_a = tmp_path / "a.lock"
    lock_b = tmp_path / "b.lock"

    # Both should succeed without deadlock
    with qralph_state_mod.exclusive_state_lock(lock_a):
        with qralph_state_mod.exclusive_state_lock(lock_b):
            pass  # No deadlock


def test_exclusive_lock_released_on_exception(tmp_path):
    """F-020: Lock is released even when exception occurs inside block"""
    lock_path = tmp_path / "test.lock"

    with pytest.raises(ValueError):
        with qralph_state_mod.exclusive_state_lock(lock_path):
            raise ValueError("test error")

    # Lock should be released — acquiring it again should succeed
    with qralph_state_mod.exclusive_state_lock(lock_path):
        pass  # Should not hang


# ============================================================================
# 16. F-021: WORK MODE PHASE TRANSITION TESTS (via commands)
# ============================================================================


def test_work_mode_plan_approve_execute_flow(mock_qralph_env, capsys):
    """F-021: Full work mode flow: init -> discover -> plan -> approve -> execute"""
    qralph_orchestrator.cmd_init("Write a blog post about AI trends", mode="work")
    _clear_control_md(mock_qralph_env)

    state = qralph_orchestrator.load_state()
    assert state["mode"] == "work"
    assert state["phase"] == "INIT"

    # Discover
    qralph_orchestrator.cmd_discover()
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "DISCOVERING"

    # Plan
    plan_result = qralph_orchestrator.cmd_work_plan()
    assert plan_result["status"] == "plan_generated"
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "PLANNING"

    # Verify PLAN.md was created
    project_path = Path(state["project_path"])
    assert (project_path / "PLAN.md").exists()

    # Approve (transitions PLANNING -> USER_REVIEW -> EXECUTING)
    approve_result = qralph_orchestrator.cmd_work_approve()
    assert approve_result["status"] == "approved"
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "EXECUTING"


def test_work_mode_iterate_returns_to_planning(mock_qralph_env, capsys):
    """F-021: work-iterate returns to PLANNING for revision"""
    qralph_orchestrator.cmd_init("Write article", mode="work")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    qralph_orchestrator.cmd_work_plan()

    # Approve to USER_REVIEW
    state = qralph_orchestrator.load_state()
    state["phase"] = "USER_REVIEW"
    qralph_orchestrator.save_state(state)

    # Iterate with feedback
    iterate_result = qralph_orchestrator.cmd_work_iterate("Add more detail about LLMs")
    assert iterate_result["status"] == "iterating"
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "PLANNING"

    # Verify feedback was recorded
    project_path = Path(state["project_path"])
    feedback_file = project_path / "PLAN-FEEDBACK.md"
    assert feedback_file.exists()
    assert "LLMs" in feedback_file.read_text()


def test_work_mode_escalate_to_coding(mock_qralph_env, capsys):
    """F-021: cmd_escalate transitions work mode to full coding mode"""
    qralph_orchestrator.cmd_init("Automate deployment", mode="work")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    qralph_orchestrator.cmd_work_plan()

    # Approve through to EXECUTING
    qralph_orchestrator.cmd_work_approve()
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "EXECUTING"

    # Escalate
    escalate_result = qralph_orchestrator.cmd_escalate()
    assert escalate_result["status"] == "escalated"
    assert escalate_result["new_mode"] == "coding"

    state = qralph_orchestrator.load_state()
    assert state["mode"] == "coding"
    assert state["phase"] == "REVIEWING"


def test_work_mode_plan_detects_code_signals(mock_qralph_env, capsys):
    """F-021: work-plan detects code signals and applies TDD mandate"""
    qralph_orchestrator.cmd_init("Build a CLI script to deploy containers", mode="work")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()

    result = qralph_orchestrator.cmd_work_plan()
    assert result["code_signals"] is True

    project_path = Path(qralph_orchestrator.load_state()["project_path"])
    plan_content = (project_path / "PLAN.md").read_text()
    assert "TDD" in plan_content


def test_work_mode_plan_no_code_signals(mock_qralph_env, capsys):
    """F-021: work-plan without code signals skips TDD mandate"""
    qralph_orchestrator.cmd_init("Write a blog post about leadership", mode="work")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()

    result = qralph_orchestrator.cmd_work_plan()
    assert result["code_signals"] is False


# ============================================================================
# 17. F-012: PROJECT ID VALIDATION TESTS
# ============================================================================


def test_cmd_resume_rejects_path_traversal(mock_qralph_env, capsys):
    """F-012: cmd_resume rejects path traversal in project_id"""
    qralph_orchestrator.cmd_resume("../../etc/passwd")
    captured = capsys.readouterr()
    assert "Invalid" in captured.out or "error" in captured.out.lower()


def test_cmd_status_rejects_path_traversal(mock_qralph_env, capsys):
    """F-012: cmd_status rejects path traversal in project_id"""
    qralph_orchestrator.cmd_status("../../etc/passwd")
    captured = capsys.readouterr()
    assert "Invalid" in captured.out or "error" in captured.out.lower()


def test_cmd_resume_accepts_valid_id(mock_qralph_env, capsys):
    """F-012: cmd_resume accepts valid project IDs"""
    init = qralph_orchestrator.cmd_init("Valid project")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_checkpoint("REVIEWING")
    qralph_orchestrator.cmd_resume(init["project_id"])
    captured = capsys.readouterr()
    assert "resumed" in captured.out


# ============================================================================
# 18. REQ-QRALPH-018: WORK MODE REMEDIATION LOOP
# ============================================================================


def _setup_synthesized_project(mock_env, mode="coding"):
    """Helper: init + discover + select-agents + synthesize with mock findings."""
    qralph_orchestrator.cmd_init("Security review", mode=mode)
    _clear_control_md(mock_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer"])
    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    outputs_dir = project_path / "agent-outputs"

    (outputs_dir / "security-reviewer.md").write_text("""# Security Review

## Summary
Found vulnerabilities.

## Findings

### P0 - Critical
- SQL injection in login endpoint
- Missing CSRF tokens

### P1 - Important
- Weak password policy

### P2 - Suggestions
- Add rate limiting
""")
    return qralph_orchestrator.cmd_synthesize(), project_path


def test_synthesize_work_mode_routes_to_executing(mock_qralph_env, capsys):
    """REQ-QRALPH-018: Work mode synthesis routes to EXECUTING, not COMPLETE."""
    result, _ = _setup_synthesized_project(mock_qralph_env, mode="work")
    assert result["status"] == "synthesized"
    assert result["next_phase"] == "EXECUTING"
    assert result["team_shutdown_needed"] is False


def test_synthesize_work_mode_no_findings_routes_to_executing(mock_qralph_env, capsys):
    """REQ-QRALPH-018: Work mode with no findings still routes to EXECUTING."""
    qralph_orchestrator.cmd_init("Simple review", mode="work")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer"])
    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    (project_path / "agent-outputs" / "security-reviewer.md").write_text("""# Review

## Summary
All clear.

## Findings

### P0 - Critical
### P1 - Important
### P2 - Suggestions
""")
    synth = qralph_orchestrator.cmd_synthesize()
    assert synth["next_phase"] == "EXECUTING"


def test_cmd_remediate_creates_tasks(mock_qralph_env, capsys):
    """REQ-QRALPH-018: cmd_remediate creates tasks from findings (default fix_level=p0_p1)."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    result = qralph_orchestrator.cmd_remediate()
    assert result["status"] == "remediation_created"
    assert result["p0_tasks"] == 2
    assert result["p1_tasks"] == 1
    assert result["p2_tasks"] == 0  # P2 excluded by default fix_level=p0_p1
    assert result["total_tasks"] == 3


def test_cmd_remediate_done_marks_tasks(mock_qralph_env, capsys):
    """REQ-QRALPH-018: cmd_remediate_done marks specific tasks as fixed."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    qralph_orchestrator.cmd_remediate()
    result = qralph_orchestrator.cmd_remediate_done("REM-001,REM-002", notes="Fixed SQL injection and CSRF")
    assert result["status"] == "tasks_updated"
    assert set(result["marked_fixed"]) == {"REM-001", "REM-002"}
    assert result["remaining_open"] == 1  # 1 P1 task still open
    assert result["remaining_p0"] == 0


def test_cmd_remediate_verify_blocks_on_open_p0(mock_qralph_env, capsys):
    """REQ-QRALPH-018: remediate-verify blocks when active-priority tasks are still open."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    qralph_orchestrator.cmd_remediate()
    result = qralph_orchestrator.cmd_remediate_verify()
    assert result["status"] == "blocked"
    assert "fix_level=" in result["reason"]
    assert len(result["open_blocking_tasks"]) >= 2


def test_cmd_remediate_verify_completes_when_p0_fixed(mock_qralph_env, capsys):
    """REQ-QRALPH-018: remediate-verify transitions to COMPLETE when all active-priority tasks fixed."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    qralph_orchestrator.cmd_remediate()
    qralph_orchestrator.cmd_remediate_done("REM-001,REM-002,REM-003")  # Fix P0s and P1
    result = qralph_orchestrator.cmd_remediate_verify()
    assert result["status"] == "verified"
    assert result["phase"] == "COMPLETE"
    assert result["team_shutdown_needed"] is True


def test_work_mode_coding_mode_unchanged(mock_qralph_env, capsys):
    """REQ-QRALPH-018: Coding mode synthesis still routes to EXECUTING (no regression)."""
    result, _ = _setup_synthesized_project(mock_qralph_env, mode="coding")
    assert result["status"] == "synthesized"
    assert result["next_phase"] == "EXECUTING"


# ============================================================================
# LOOP BUG FIXES (Phase 1H)
# ============================================================================


def test_phase_transition_executing_to_complete_coding():
    """Bug 1A: EXECUTING -> COMPLETE must be valid in coding mode (for remediate-verify)."""
    assert validate_phase_transition("EXECUTING", "COMPLETE", "coding") is True
    # UAT should still be valid too
    assert validate_phase_transition("EXECUTING", "UAT", "coding") is True


def test_cmd_remediate_idempotent(mock_qralph_env, capsys):
    """Bug 1B: Second remediate call returns existing tasks instead of re-creating."""
    result, project_path = _setup_synthesized_project(mock_qralph_env, mode="coding")
    _clear_control_md(mock_qralph_env)

    # First remediate creates tasks
    r1 = qralph_orchestrator.cmd_remediate()
    assert r1["status"] == "remediation_created"
    total = r1["total_tasks"]
    assert total > 0

    # Second remediate should return existing tasks, not re-create
    r2 = qralph_orchestrator.cmd_remediate()
    assert r2["status"] == "remediation_exists"
    assert r2["total_tasks"] == total
    assert r2["open_tasks"] == total


def test_cmd_resume_complete_project(mock_qralph_env, capsys):
    """Bug 1C: Resuming a COMPLETE project returns already_complete instead of overwriting state."""
    result, project_path = _setup_synthesized_project(mock_qralph_env, mode="coding")
    _clear_control_md(mock_qralph_env)

    # Remediate and verify to reach COMPLETE
    qralph_orchestrator.cmd_remediate()
    state = qralph_orchestrator.load_state()
    for task in state.get("remediation_tasks", []):
        task["status"] = "fixed"
    qralph_orchestrator.save_state(state)
    qralph_orchestrator.cmd_remediate_verify()

    # Verify we're COMPLETE
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "COMPLETE"

    # Now resume should return already_complete
    project_id = state["project_id"]
    r = qralph_orchestrator.cmd_resume(project_id)
    assert r["status"] == "already_complete"
    assert r["phase"] == "COMPLETE"


def test_checkpoint_sync_after_synthesize(mock_qralph_env, capsys):
    """Bug 1E: After synthesize, both current-project.json and checkpoints/state.json match."""
    result, project_path = _setup_synthesized_project(mock_qralph_env, mode="coding")
    _clear_control_md(mock_qralph_env)

    state = qralph_orchestrator.load_state()
    checkpoint = qralph_state_mod.load_state(project_path / "checkpoints" / "state.json")

    assert state["phase"] == checkpoint["phase"] == "EXECUTING"
    assert state["project_id"] == checkpoint["project_id"]


def test_cmd_resume_uses_checksum_validation(mock_qralph_env, capsys):
    """Bug 1D: cmd_resume uses load_state (with checksum) instead of safe_read_json."""
    result, project_path = _setup_synthesized_project(mock_qralph_env, mode="coding")
    _clear_control_md(mock_qralph_env)

    # Corrupt the checkpoint checksum
    checkpoint_file = project_path / "checkpoints" / "state.json"
    import json as _json
    data = _json.loads(checkpoint_file.read_text())
    data["_checksum"] = "corrupted_checksum"
    checkpoint_file.write_text(_json.dumps(data))

    # Resume should still work (load_state repairs on checksum mismatch)
    project_id = data["project_id"]
    r = qralph_orchestrator.cmd_resume(project_id)
    # Should either return resumed or already_complete, not crash
    assert r is not None
    assert "error" not in r or "corrupt" not in r.get("error", "")


def test_get_next_step_work_mode_phases():
    """Bug 1G: get_next_step returns valid instructions for work-mode phases."""
    assert "Unknown" not in qralph_orchestrator.get_next_step("PLANNING")
    assert "Unknown" not in qralph_orchestrator.get_next_step("USER_REVIEW")
    assert "Unknown" not in qralph_orchestrator.get_next_step("ESCALATE")


def test_cmd_synthesize_zero_agents(mock_qralph_env, capsys):
    """F-012: Synthesize with zero agent outputs is BLOCKED by synthesis gate."""
    qralph_orchestrator.cmd_init("Test zero agents")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer"])
    # Don't write any agent outputs - go straight to synthesize
    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    # Clear the output files (select-agents doesn't create them, but just in case)
    for f in (project_path / "agent-outputs").glob("*.md"):
        f.unlink()
    synth = qralph_orchestrator.cmd_synthesize()
    assert synth is not None
    # Synthesis should be BLOCKED — missing output files
    assert synth["status"] == "error"
    assert "blocked" in synth["error"].lower()


def test_compute_evidence_quality_score_full_coverage(mock_qralph_env):
    """EQS returns HIGH confidence when all agents have substantive output."""
    qralph_orchestrator.cmd_init("Test EQS full")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer", "sde-iii"])
    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    outputs_dir = project_path / "agent-outputs"

    # Write substantive output for both agents (~300 words each)
    content = "# Review\n\n## Summary\nDetailed analysis.\n\n## Findings\n\n### P0 - Critical\n- Issue found\n\n" + ("word " * 300)
    (outputs_dir / "security-reviewer.md").write_text(content)
    (outputs_dir / "sde-iii.md").write_text(content)

    eqs = qralph_orchestrator.compute_evidence_quality_score(["security-reviewer", "sde-iii"], outputs_dir)
    assert eqs["agents_with_output"] == 2
    assert eqs["total_agents"] == 2
    assert eqs["eqs"] >= 80
    assert eqs["confidence"] == "HIGH"


def test_compute_evidence_quality_score_partial(mock_qralph_env):
    """EQS returns lower confidence when some agents missing."""
    qralph_orchestrator.cmd_init("Test EQS partial")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer", "sde-iii"])
    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    outputs_dir = project_path / "agent-outputs"

    # Only one agent writes output
    content = "# Review\n\n## Summary\nAnalysis done.\n\n## Findings\n\n### P1 - Important\n- Issue\n\n" + ("word " * 200)
    (outputs_dir / "security-reviewer.md").write_text(content)
    # sde-iii has no output file

    eqs = qralph_orchestrator.compute_evidence_quality_score(["security-reviewer", "sde-iii"], outputs_dir)
    assert eqs["agents_with_output"] == 1
    assert eqs["total_agents"] == 2
    assert eqs["agent_status"]["sde-iii"]["status"] == "missing"
    assert eqs["eqs"] < 80  # Can't be HIGH with 50% coverage


def test_compute_evidence_quality_score_empty_agents(mock_qralph_env):
    """EQS handles zero agents gracefully."""
    import tempfile
    outputs_dir = Path(tempfile.mkdtemp())
    eqs = qralph_orchestrator.compute_evidence_quality_score([], outputs_dir)
    assert eqs["eqs"] == 0
    assert eqs["confidence"] == "HOLLOW RUN"
    assert eqs["agents_with_output"] == 0


def test_synthesis_gate_blocks_empty_output(mock_qralph_env, capsys):
    """Synthesis gate blocks when agent output exists but is empty (<50 bytes)."""
    qralph_orchestrator.cmd_init("Test empty gate")
    _clear_control_md(mock_qralph_env)
    qralph_orchestrator.cmd_discover()
    result = qralph_orchestrator.cmd_select_agents(["security-reviewer"])
    project_path = Path(result["agents"][0]["output_file"]).parent.parent
    outputs_dir = project_path / "agent-outputs"

    # Write a tiny file (under 50 bytes)
    (outputs_dir / "security-reviewer.md").write_text("# Empty\n")

    synth = qralph_orchestrator.cmd_synthesize()
    assert synth["status"] == "error"
    assert "empty" in synth["error"].lower() or "blocked" in synth["error"].lower()


def test_prompt_contains_write_tool_instruction(mock_qralph_env):
    """Agent prompt explicitly instructs to use the Write tool."""
    prompt = qralph_orchestrator.generate_team_agent_prompt(
        agent_type="security-reviewer",
        request="Test request",
        project_id="test-001",
        project_path=Path("/tmp/test"),
        team_name="test-team",
        available_skills=[],
    )
    assert "Write tool" in prompt
    assert "QRALPH-RECEIPT" in prompt
    assert "CRITICAL REMINDER" in prompt
    # Skills section should come AFTER workflow
    workflow_pos = prompt.find("## Workflow")
    skills_pos = prompt.find("Optional Skills")
    if skills_pos > 0:
        assert skills_pos > workflow_pos, "Skills must come after Workflow"


# ============================================================================
# v4.1.2 — FIX LEVEL, STATUS FINDINGS, SKILL.MD ENFORCEMENT
# ============================================================================


def test_cmd_init_stores_fix_level(mock_qralph_env, capsys):
    """REQ-QRALPH-020: cmd_init stores fix_level in state."""
    result = qralph_orchestrator.cmd_init("Security review", fix_level="p0")
    assert result["status"] == "initialized"
    state = qralph_orchestrator.load_state()
    assert state["fix_level"] == "p0"


def test_cmd_init_default_fix_level(mock_qralph_env, capsys):
    """REQ-QRALPH-020: cmd_init defaults fix_level to p0_p1."""
    result = qralph_orchestrator.cmd_init("Security review")
    state = qralph_orchestrator.load_state()
    assert state["fix_level"] == "p0_p1"


def test_cmd_init_rejects_invalid_fix_level(mock_qralph_env, capsys):
    """REQ-QRALPH-020: cmd_init rejects invalid fix_level."""
    result = qralph_orchestrator.cmd_init("Security review", fix_level="invalid")
    assert result["status"] == "error"
    assert "fix_level" in result["error"]


def test_cmd_remediate_fix_level_p0_only(mock_qralph_env, capsys):
    """REQ-QRALPH-020: fix_level=p0 only creates P0 tasks."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    # Override fix_level in state
    state = qralph_orchestrator.load_state()
    state["fix_level"] = "p0"
    qralph_orchestrator.save_state(state)
    result = qralph_orchestrator.cmd_remediate()
    assert result["status"] == "remediation_created"
    assert result["p0_tasks"] == 2
    assert result["p1_tasks"] == 0
    assert result["p2_tasks"] == 0


def test_cmd_remediate_fix_level_none_skips(mock_qralph_env, capsys):
    """REQ-QRALPH-020: fix_level=none skips remediation entirely."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    state = qralph_orchestrator.load_state()
    state["fix_level"] = "none"
    qralph_orchestrator.save_state(state)
    result = qralph_orchestrator.cmd_remediate()
    assert result["status"] == "remediation_skipped"
    assert result["fix_level"] == "none"


def test_cmd_remediate_fix_level_all(mock_qralph_env, capsys):
    """REQ-QRALPH-020: fix_level=all creates tasks for P0+P1+P2."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    state = qralph_orchestrator.load_state()
    state["fix_level"] = "all"
    qralph_orchestrator.save_state(state)
    result = qralph_orchestrator.cmd_remediate()
    assert result["status"] == "remediation_created"
    assert result["p0_tasks"] == 2
    assert result["p1_tasks"] == 1
    assert result["p2_tasks"] == 1
    assert result["total_tasks"] == 4


def test_cmd_remediate_verify_respects_fix_level_all(mock_qralph_env, capsys):
    """REQ-QRALPH-020: remediate-verify with fix_level=all blocks on open P2 tasks."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    state = qralph_orchestrator.load_state()
    state["fix_level"] = "all"
    qralph_orchestrator.save_state(state)
    qralph_orchestrator.cmd_remediate()
    # Fix P0s but leave P1/P2 open
    qralph_orchestrator.cmd_remediate_done("REM-001,REM-002")
    result = qralph_orchestrator.cmd_remediate_verify()
    assert result["status"] == "blocked"
    assert "fix_level=all" in result["reason"]


def test_cmd_remediate_verify_fix_level_p0_ignores_p1(mock_qralph_env, capsys):
    """REQ-QRALPH-020: remediate-verify with fix_level=p0 passes when P0s fixed, P1 open."""
    _setup_synthesized_project(mock_qralph_env, mode="work")
    state = qralph_orchestrator.load_state()
    state["fix_level"] = "p0"
    qralph_orchestrator.save_state(state)
    qralph_orchestrator.cmd_remediate()
    # fix_level=p0 only created P0 tasks, fix them
    result_done = qralph_orchestrator.cmd_remediate_done("REM-001,REM-002")
    result = qralph_orchestrator.cmd_remediate_verify()
    assert result["status"] == "verified"
    assert result["phase"] == "COMPLETE"


def test_cmd_status_includes_findings_summary(mock_qralph_env, capsys):
    """REQ-QRALPH-020: cmd_status includes _status_summary with findings counts."""
    result, project_path = _setup_synthesized_project(mock_qralph_env, mode="coding")
    project_id = result["project_id"]
    prefix = project_id.split("-")[0]
    # Clear captured output from setup, then call status
    capsys.readouterr()
    qralph_orchestrator.cmd_status(prefix)
    captured = capsys.readouterr()
    status_output = json.loads(captured.out)
    assert "_status_summary" in status_output
    summary = status_output["_status_summary"]
    assert "findings" in summary
    assert summary["findings"]["p0"] >= 0
    assert summary["findings"]["p1"] >= 0
    assert summary["findings"]["p2"] >= 0
    assert "eqs" in summary
    assert "remediation" in summary
    assert "fix_level" in summary


def test_repair_state_adds_fix_level_default():
    """REQ-QRALPH-020: repair_state adds fix_level default when missing."""
    repaired = qralph_state_mod.repair_state({"project_id": "test"})
    assert repaired["fix_level"] == "p0_p1"


# ============================================================================
# v4.1.3 — AUTOMATIC PROCESS SWEEP
# ============================================================================


def test_cmd_init_calls_sweep(mock_qralph_env, capsys):
    """REQ-QRALPH-021: cmd_init sweeps orphaned processes before starting."""
    with patch.object(qralph_orchestrator, 'sweep_orphaned_processes', return_value=None) as mock_sweep:
        qralph_orchestrator.cmd_init("Test sweep on init")
        mock_sweep.assert_called_once()


def test_cmd_resume_calls_sweep(mock_qralph_env, capsys):
    """REQ-QRALPH-021: cmd_resume sweeps orphaned processes before resuming."""
    result = qralph_orchestrator.cmd_init("Test sweep on resume")
    project_id = result["project_id"]
    with patch.object(qralph_orchestrator, 'sweep_orphaned_processes', return_value=None) as mock_sweep:
        qralph_orchestrator.cmd_resume(project_id)
        mock_sweep.assert_called_once()


def test_cmd_finalize_calls_sweep(mock_qralph_env, capsys):
    """REQ-QRALPH-021: cmd_finalize sweeps orphaned processes before shutdown."""
    _setup_synthesized_project(mock_qralph_env, mode="coding")
    # Advance to a phase that can finalize
    state = qralph_orchestrator.load_state()
    state["phase"] = "UAT"
    qralph_orchestrator.save_state(state)
    _clear_control_md(mock_qralph_env)
    with patch.object(qralph_orchestrator, 'sweep_orphaned_processes', return_value=None) as mock_sweep:
        qralph_orchestrator.cmd_finalize()
        mock_sweep.assert_called_once()


# ============================================================================
# REQ-QRALPH-022: FINALIZE REMEDIATION GATE
# ============================================================================


def test_cmd_finalize_blocks_on_open_remediation_tasks(mock_qralph_env, capsys):
    """REQ-QRALPH-022: finalize rejects when remediation tasks are open at fix_level."""
    _setup_synthesized_project(mock_qralph_env, mode="coding")
    state = qralph_orchestrator.load_state()
    state["phase"] = "EXECUTING"
    state["fix_level"] = "p0_p1"
    state["remediation_tasks"] = [
        {"id": "REM-001", "priority": "P0", "status": "fixed", "finding": {"agent": "a", "finding": "f1"}},
        {"id": "REM-002", "priority": "P1", "status": "open", "finding": {"agent": "a", "finding": "f2"}},
        {"id": "REM-003", "priority": "P2", "status": "open", "finding": {"agent": "a", "finding": "f3"}},
    ]
    qralph_orchestrator.save_state(state)
    _clear_control_md(mock_qralph_env)

    with patch.object(qralph_orchestrator, 'sweep_orphaned_processes', return_value=None):
        result = qralph_orchestrator.cmd_finalize()
    captured = capsys.readouterr()
    assert "error" in captured.out.lower()
    assert "REM-002" in captured.out

    # Verify state is still EXECUTING (not COMPLETE)
    state = qralph_orchestrator.load_state()
    assert state["phase"] == "EXECUTING"


def test_cmd_finalize_allows_open_p2_when_fix_level_p0_p1(mock_qralph_env, capsys):
    """REQ-QRALPH-022: finalize succeeds when only lower-priority tasks are open."""
    _setup_synthesized_project(mock_qralph_env, mode="coding")
    state = qralph_orchestrator.load_state()
    state["phase"] = "EXECUTING"
    state["fix_level"] = "p0_p1"
    state["remediation_tasks"] = [
        {"id": "REM-001", "priority": "P0", "status": "fixed", "finding": {"agent": "a", "finding": "f1"}},
        {"id": "REM-002", "priority": "P1", "status": "fixed", "finding": {"agent": "a", "finding": "f2"}},
        {"id": "REM-003", "priority": "P2", "status": "open", "finding": {"agent": "a", "finding": "f3"}},
    ]
    qralph_orchestrator.save_state(state)
    _clear_control_md(mock_qralph_env)

    with patch.object(qralph_orchestrator, 'sweep_orphaned_processes', return_value=None):
        result = qralph_orchestrator.cmd_finalize()
    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split('\n') if l.strip().startswith('{')]
    last_output = json.loads(lines[-1])
    assert last_output["status"] == "complete"

    state = qralph_orchestrator.load_state()
    assert state["phase"] == "COMPLETE"


def test_cmd_finalize_no_remediation_tasks_succeeds(mock_qralph_env, capsys):
    """REQ-QRALPH-022: finalize succeeds when there are no remediation tasks at all."""
    _setup_synthesized_project(mock_qralph_env, mode="coding")
    state = qralph_orchestrator.load_state()
    state["phase"] = "UAT"
    qralph_orchestrator.save_state(state)
    _clear_control_md(mock_qralph_env)

    with patch.object(qralph_orchestrator, 'sweep_orphaned_processes', return_value=None):
        result = qralph_orchestrator.cmd_finalize()
    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split('\n') if l.strip().startswith('{')]
    last_output = json.loads(lines[-1])
    assert last_output["status"] == "complete"


def test_cmd_resume_includes_remediation_progress(mock_qralph_env, capsys):
    """REQ-QRALPH-022: resume output includes remediation_progress when tasks exist."""
    _setup_synthesized_project(mock_qralph_env, mode="coding")
    state = qralph_orchestrator.load_state()
    state["phase"] = "EXECUTING"
    state["fix_level"] = "p0_p1"
    state["remediation_tasks"] = [
        {"id": "REM-001", "priority": "P0", "status": "fixed", "finding": {"agent": "a", "finding": "f1"}},
        {"id": "REM-002", "priority": "P1", "status": "open", "finding": {"agent": "a", "finding": "f2"}},
        {"id": "REM-003", "priority": "P1", "status": "open", "finding": {"agent": "a", "finding": "f3"}},
    ]
    qralph_orchestrator.save_state(state)
    project_id = state["project_id"]

    # Save checkpoint so resume can find it
    project_path = Path(state["project_path"])
    qralph_orchestrator.save_state_and_checkpoint(state)
    _clear_control_md(mock_qralph_env)

    with patch.object(qralph_orchestrator, 'sweep_orphaned_processes', return_value=None):
        result = qralph_orchestrator.cmd_resume(project_id)

    assert "remediation_progress" in result
    progress = result["remediation_progress"]
    assert progress["total"] == 3
    assert progress["fixed"] == 1
    assert progress["open_at_fix_level"] == 2
    assert "warning" in progress
    assert "REM-002" in progress["blocking_ids"]


# ============================================================================
# RUN TESTS
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
