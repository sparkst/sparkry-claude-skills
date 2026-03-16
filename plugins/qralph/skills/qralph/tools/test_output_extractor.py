"""Tests for output-extractor.py — deterministic LLM output parsing.

TDD: all tests written before implementation. Each test cites its REQ-ID.
"""

import pytest
import sys
import os
import importlib.util
from pathlib import Path

# Import from output-extractor.py (hyphenated filename requires importlib)
sys.path.insert(0, os.path.dirname(__file__))
_mod_path = Path(__file__).parent / "output-extractor.py"
_spec = importlib.util.spec_from_file_location("output_extractor", _mod_path)
output_extractor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(output_extractor)

extract_verdict = output_extractor.extract_verdict
extract_criteria_results = output_extractor.extract_criteria_results
extract_request_satisfaction = output_extractor.extract_request_satisfaction
extract_reverify_verdicts = output_extractor.extract_reverify_verdicts
extract_smoke_results = output_extractor.extract_smoke_results
extract_polish_issues = output_extractor.extract_polish_issues


# ─── extract_verdict ─────────────────────────────────────────────────────────

class TestExtractVerdict:

    def test_json_code_block(self):
        """REQ-OE-001: JSON code block with verdict → returns with source json_block."""
        content = '```json\n{"verdict": "PASS", "summary": "All good"}\n```'
        result = extract_verdict(content)
        assert result["verdict"] == "PASS"
        assert result["source"] == "json_block"

    def test_raw_json(self):
        """REQ-OE-002: Raw JSON (no fences) → returns verdict with source raw_json."""
        content = '{"verdict": "FAIL", "reason": "missing auth"}'
        result = extract_verdict(content)
        assert result["verdict"] == "FAIL"
        assert result["source"] == "raw_json"

    def test_broken_json_regex_fallback(self):
        """REQ-OE-003: Broken JSON with verdict key → regex fallback works."""
        content = '{"verdict": "FAIL", summary: unquoted stuff here'
        result = extract_verdict(content)
        assert result["verdict"] == "FAIL"
        assert result["source"] == "regex"

    def test_natural_language_pass(self):
        """REQ-OE-004: Natural language 'All criteria are met' → PASS with low confidence."""
        content = "After thorough review, all criteria are met and the implementation is solid."
        result = extract_verdict(content)
        assert result["verdict"] == "PASS"
        assert result["source"] == "natural_language"
        assert result["confidence"] == "low"

    def test_natural_language_fail(self):
        """REQ-OE-005: Natural language 'Does not satisfy requirements' → FAIL."""
        content = "The implementation does not satisfy requirements for authentication."
        result = extract_verdict(content)
        assert result["verdict"] == "FAIL"

    def test_ambiguous_both_signals(self):
        """REQ-OE-006: Ambiguous text (both pass/fail signals) → verdict None."""
        content = "All criteria are met but the implementation fails on security."
        result = extract_verdict(content)
        assert result["verdict"] is None

    def test_empty_input(self):
        """REQ-OE-007: Empty input → verdict None."""
        result = extract_verdict("")
        assert result["verdict"] is None

    def test_garbage_input(self):
        """REQ-OE-007: Garbage input → verdict None."""
        result = extract_verdict("asdf1234!@#$ random noise zzz")
        assert result["verdict"] is None

    def test_json_block_fail(self):
        """REQ-OE-001: JSON code block with FAIL verdict."""
        content = 'Some text before\n```json\n{"verdict": "FAIL"}\n```\nSome text after'
        result = extract_verdict(content)
        assert result["verdict"] == "FAIL"
        assert result["source"] == "json_block"

    def test_case_insensitive_json(self):
        """REQ-OE-001: JSON verdict values should be normalized to uppercase."""
        content = '{"verdict": "pass"}'
        result = extract_verdict(content)
        assert result["verdict"] == "PASS"

    def test_natural_language_verification_passed(self):
        """REQ-OE-004: 'verification passed' phrase → PASS."""
        content = "The verification passed with no issues found."
        result = extract_verdict(content)
        assert result["verdict"] == "PASS"

    def test_natural_language_fully_satisfies(self):
        """REQ-OE-004: 'fully satisfies' phrase → PASS."""
        content = "This implementation fully satisfies all stated requirements."
        result = extract_verdict(content)
        assert result["verdict"] == "PASS"

    def test_natural_language_reject(self):
        """REQ-OE-005: 'reject' in context → FAIL."""
        content = "I must reject this implementation due to missing error handling."
        result = extract_verdict(content)
        assert result["verdict"] == "FAIL"

    def test_natural_language_blocked(self):
        """REQ-OE-005: 'blocked' in context → FAIL."""
        content = "The deployment is blocked by failing security checks."
        result = extract_verdict(content)
        assert result["verdict"] == "FAIL"

    def test_json_confidence_high(self):
        """REQ-OE-001: JSON sources should have high confidence."""
        content = '```json\n{"verdict": "PASS"}\n```'
        result = extract_verdict(content)
        assert result["confidence"] == "high"


# ─── extract_criteria_results ────────────────────────────────────────────────

class TestExtractCriteriaResults:

    def test_json_code_block(self):
        """REQ-OE-010: JSON code block with criteria_results array → returns list."""
        content = '```json\n{"criteria_results": [{"criterion": "AC-1", "status": "pass"}]}\n```'
        result = extract_criteria_results(content)
        assert len(result) == 1
        assert result[0]["criterion"] == "AC-1"
        assert result[0]["status"] == "pass"

    def test_markdown_table(self):
        """REQ-OE-011: Markdown table with AC-N | desc | PASS | evidence → structured list."""
        content = """
| Criterion | Description | Status | Evidence |
|-----------|-------------|--------|----------|
| AC-1 | User can login | PASS | auth.ts:42 |
| AC-2 | Error handling | FAIL | Missing try/catch |
| AC-3 | Logging works | PARTIAL | Only stdout |
"""
        result = extract_criteria_results(content)
        assert len(result) == 3
        assert result[0]["criterion"] == "AC-1"
        assert result[0]["status"] == "pass"
        assert result[1]["criterion"] == "AC-2"
        assert result[1]["status"] == "fail"
        assert result[2]["criterion"] == "AC-3"
        assert result[2]["status"] == "partial"

    def test_section_headers(self):
        """REQ-OE-012: Section headers ### AC-1: Description with pass/fail in body."""
        content = """
### AC-1: User authentication
The authentication module is correctly implemented and all login flows work.
Status: PASS

### AC-2: Rate limiting
Rate limiting is not implemented. This criterion is not met.
"""
        result = extract_criteria_results(content)
        assert len(result) == 2
        assert result[0]["criterion"] == "AC-1"
        assert result[0]["status"] == "pass"
        assert result[1]["criterion"] == "AC-2"
        assert result[1]["status"] == "fail"

    def test_numbered_list(self):
        """REQ-OE-013: Numbered list 1. AC-1: ... with status keywords."""
        content = """
1. AC-1: User can login — PASS — auth.ts:42
2. AC-2: Error handling — FAIL — no try/catch found
3. AC-3: Logs are structured — PASS — logger.ts:10
"""
        result = extract_criteria_results(content)
        assert len(result) == 3
        assert result[0]["criterion"] == "AC-1"
        assert result[0]["status"] == "pass"
        assert result[1]["status"] == "fail"
        assert result[2]["status"] == "pass"

    def test_mixed_format(self):
        """REQ-OE-014: Mixed format (some JSON, some prose) → extracts all."""
        content = """
```json
{"criteria_results": [{"criterion": "AC-1", "status": "pass"}]}
```

Also reviewed:
### AC-2: Error handling
This is not met — missing error boundaries.
"""
        result = extract_criteria_results(content)
        # Should get at least AC-1 from JSON and AC-2 from section
        criteria = {r["criterion"] for r in result}
        assert "AC-1" in criteria
        assert "AC-2" in criteria

    def test_no_criteria_content(self):
        """REQ-OE-015: No criteria content → returns empty list (not None)."""
        content = "This is a general review with no specific criteria mentioned."
        result = extract_criteria_results(content)
        assert result == []
        assert result is not None

    def test_raw_json_no_fences(self):
        """REQ-OE-010: Raw JSON without fences also works."""
        content = '{"criteria_results": [{"criterion": "AC-1", "status": "pass", "evidence": "file.ts:10"}]}'
        result = extract_criteria_results(content)
        assert len(result) == 1

    def test_table_case_insensitive_status(self):
        """REQ-OE-011: Table status matching is case-insensitive."""
        content = """
| Criterion | Description | Status | Evidence |
|-----------|-------------|--------|----------|
| AC-1 | Login | Pass | auth.ts:42 |
| AC-2 | Error | fail | none |
"""
        result = extract_criteria_results(content)
        assert len(result) == 2
        assert result[0]["status"] == "pass"
        assert result[1]["status"] == "fail"


# ─── extract_request_satisfaction ────────────────────────────────────────────

class TestExtractRequestSatisfaction:

    def test_json_extraction(self):
        """REQ-OE-020: JSON extraction backward compat."""
        content = '```json\n{"request_satisfaction": [{"fragment": "REQ-F-1", "status": "satisfied"}]}\n```'
        result = extract_request_satisfaction(content, ["REQ-F-1"])
        assert len(result) == 1
        assert result[0]["fragment"] == "REQ-F-1"
        assert result[0]["status"] == "satisfied"

    def test_fragment_satisfied_in_prose(self):
        """REQ-OE-021: Fragment ID mentioned with 'satisfied'/'fully met' → satisfied."""
        content = "REQ-F-1 is fully met — the login flow works correctly."
        result = extract_request_satisfaction(content, ["REQ-F-1"])
        assert len(result) == 1
        assert result[0]["fragment"] == "REQ-F-1"
        assert result[0]["status"] == "satisfied"

    def test_fragment_missing_from_text(self):
        """REQ-OE-022: Fragment ID not found in text → missing."""
        content = "The implementation looks good overall."
        result = extract_request_satisfaction(content, ["REQ-F-1", "REQ-F-2"])
        assert len(result) == 2
        assert all(r["status"] == "missing" for r in result)

    def test_fragment_partial(self):
        """REQ-OE-023: Fragment ID with 'partial' context → partial."""
        content = "REQ-F-1 is only partially addressed — the login works but OAuth is missing."
        result = extract_request_satisfaction(content, ["REQ-F-1"])
        assert len(result) == 1
        assert result[0]["status"] == "partial"

    def test_mixed_fragments(self):
        """REQ-OE-021/022: Multiple fragments with different statuses."""
        content = """
REQ-F-1 is fully satisfied — all authentication tests pass.
REQ-F-3 has partial coverage — only happy path tested.
"""
        result = extract_request_satisfaction(content, ["REQ-F-1", "REQ-F-2", "REQ-F-3"])
        status_map = {r["fragment"]: r["status"] for r in result}
        assert status_map["REQ-F-1"] == "satisfied"
        assert status_map["REQ-F-2"] == "missing"
        assert status_map["REQ-F-3"] == "partial"


# ─── extract_reverify_verdicts ───────────────────────────────────────────────

class TestExtractReverifyVerdicts:

    def test_exact_resolved_unresolved_lines(self):
        """REQ-OE-030: Exact RESOLVED: ID / UNRESOLVED: ID lines."""
        content = """
RESOLVED: SEC-001
  Evidence: auth.ts:42 — added parameterized query
UNRESOLVED: PE-002
  Still no connection pooling
"""
        result = extract_reverify_verdicts(content, ["SEC-001", "PE-002"])
        assert result["SEC-001"] == "resolved"
        assert result["PE-002"] == "unresolved"

    def test_natural_language_resolved(self):
        """REQ-OE-031: 'Fixed'/'addressed'/'no longer present' near finding ID → resolved."""
        content = """
SEC-001 has been fixed — the parameterized query is now at auth.ts:42.
PE-002 is no longer present after adding the connection pool at db.ts:15.
"""
        result = extract_reverify_verdicts(content, ["SEC-001", "PE-002"])
        assert result["SEC-001"] == "resolved"
        assert result["PE-002"] == "resolved"

    def test_resolved_without_evidence_downgraded(self):
        """REQ-OE-032: Resolved without file:line evidence → downgraded to unresolved."""
        content = """
SEC-001 has been fixed — I checked and it looks good now.
"""
        result = extract_reverify_verdicts(content, ["SEC-001"])
        assert result["SEC-001"] == "unresolved"

    def test_finding_not_mentioned_defaults_unresolved(self):
        """REQ-OE-033: Finding ID not mentioned → defaults to unresolved."""
        content = "Everything looks great, no issues found."
        result = extract_reverify_verdicts(content, ["SEC-001", "PE-002"])
        assert result["SEC-001"] == "unresolved"
        assert result["PE-002"] == "unresolved"

    def test_mixed_explicit_and_natural(self):
        """REQ-OE-030/031: Mix of explicit and natural language verdicts."""
        content = """
RESOLVED: SEC-001
  auth.ts:42 — fixed

PE-002 has been addressed — connection pool added at db.ts:15.
"""
        result = extract_reverify_verdicts(content, ["SEC-001", "PE-002", "UX-003"])
        assert result["SEC-001"] == "resolved"
        assert result["PE-002"] == "resolved"
        assert result["UX-003"] == "unresolved"


# ─── extract_smoke_results ───────────────────────────────────────────────────

class TestExtractSmokeResults:

    def test_bold_markers(self):
        """REQ-OE-040: Bold **PASS** markers counted (backward compat)."""
        content = """
- Homepage loads: **PASS**
- Login flow: **PASS**
- API health: **FAIL**
- Dark mode: **SKIP**
"""
        result = extract_smoke_results(content)
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["skipped"] == 1

    def test_plain_markers(self):
        """REQ-OE-041: Plain PASS/FAIL/SKIP (no bold) → counted."""
        content = """
- Homepage loads: PASS
- Login flow: PASS
- API health: FAIL
- Dark mode: SKIP
"""
        result = extract_smoke_results(content)
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["skipped"] == 1

    def test_checkbox_format(self):
        """REQ-OE-042: Checkbox format [x]/[ ] → counted."""
        content = """
- [x] Homepage loads correctly
- [x] Login flow works
- [ ] API health check
- [x] Responsive design
"""
        result = extract_smoke_results(content)
        assert result["passed"] == 3
        assert result["failed"] == 1

    def test_summary_line_fallback(self):
        """REQ-OE-043: Summary line '3 passed, 1 failed' as fallback."""
        content = """
All smoke tests complete.

Results: 3 passed, 1 failed, 2 skipped
"""
        result = extract_smoke_results(content)
        assert result["passed"] == 3
        assert result["failed"] == 1
        assert result["skipped"] == 2

    def test_failure_lines_captured(self):
        """REQ-OE-040: Failure details captured in failures list."""
        content = """
- Homepage: **PASS**
- Login: **FAIL** — returns 500
- API: **FAIL** — timeout
"""
        result = extract_smoke_results(content)
        assert len(result["failures"]) == 2

    def test_empty_content(self):
        """REQ-OE-040: Empty content returns zeros."""
        result = extract_smoke_results("")
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 0
        assert result["failures"] == []

    def test_bold_markers_preferred_over_summary(self):
        """REQ-OE-040/043: Individual markers take priority over summary line."""
        content = """
- Homepage: **PASS**
- Login: **PASS**
Summary: 5 passed, 0 failed
"""
        result = extract_smoke_results(content)
        # Individual markers found, so those are used (2 not 5)
        assert result["passed"] == 2


# ─── extract_polish_issues ───────────────────────────────────────────────────

class TestExtractPolishIssues:

    def test_findings_extraction(self):
        """REQ-OE-050: Reuse parse_findings for P0/P1/P2 extraction."""
        content = """
[P0] SEC-001: SQL injection in login handler
**Confidence:** high

[P1] PE-002: No connection pooling
"""
        result = extract_polish_issues(content)
        assert result["has_issues"] is True
        assert len(result["findings"]) == 2

    def test_no_false_positive_from_mentions(self):
        """REQ-OE-051: 'I reviewed the P0 requirements' should NOT trigger has_issues."""
        content = "I reviewed the P0 requirements and confirmed everything is in order. No issues found."
        result = extract_polish_issues(content)
        assert result["has_issues"] is False

    def test_gap_patterns_anchored(self):
        """REQ-OE-052: Gap patterns anchored to line beginnings."""
        content = """
- Missing test coverage for authentication module
- Missing tests for error handling paths
"""
        result = extract_polish_issues(content)
        assert result["has_issues"] is True
        assert len(result["gaps"]) > 0

    def test_no_findings_no_gaps_clean(self):
        """REQ-OE-053: No findings and no gaps → has_issues: False."""
        content = "Everything looks great. The code is clean and well-tested."
        result = extract_polish_issues(content)
        assert result["has_issues"] is False
        assert result["findings"] == []
        assert result["gaps"] == []

    def test_p1_finding_triggers_issues(self):
        """REQ-OE-050: P1 findings trigger has_issues."""
        content = "[P1] BUG-001: Missing null check in parser"
        result = extract_polish_issues(content)
        assert result["has_issues"] is True

    def test_p2_only_no_issues(self):
        """REQ-OE-050: P2-only findings do NOT trigger has_issues."""
        content = "[P2] STYLE-001: Variable naming could be improved"
        result = extract_polish_issues(content)
        assert result["has_issues"] is False

    def test_gap_critical_at_line_start(self):
        """REQ-OE-052: 'Critical' at line start is a gap, inline mention is not."""
        content = """
The code handles the critical path correctly.
"""
        result = extract_polish_issues(content)
        # "critical" appears inline, not at line start as a gap marker
        assert result["has_issues"] is False

    def test_gap_missing_coverage(self):
        """REQ-OE-052: 'Missing coverage' as a gap."""
        content = """
- Missing coverage for edge cases in auth module
- Not covered: error handling for network timeouts
"""
        result = extract_polish_issues(content)
        assert result["has_issues"] is True
        assert any("coverage" in g.lower() or "not covered" in g.lower() for g in result["gaps"])
