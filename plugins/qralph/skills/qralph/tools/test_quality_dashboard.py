import pytest
import sys
import os
import importlib.util
from pathlib import Path

# Import from quality-dashboard.py (hyphenated filename requires importlib)
sys.path.insert(0, os.path.dirname(__file__))
_mod_path = Path(__file__).parent / "quality-dashboard.py"
_spec = importlib.util.spec_from_file_location("quality_dashboard", _mod_path)
quality_dashboard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(quality_dashboard)

parse_findings = quality_dashboard.parse_findings
check_convergence = quality_dashboard.check_convergence
should_agent_continue = quality_dashboard.should_agent_continue
generate_dashboard = quality_dashboard.generate_dashboard
deduplicate_findings = quality_dashboard.deduplicate_findings


def test_parse_findings_extracts_all_severities():
    output = """
[P0] SEC-001: SQL injection in user input handler
As a security reviewer, I found an unparameterized query.
**Confidence:** high

[P1] PE-002: No connection pooling configured
**Confidence:** medium

[P2] UX-003: Button contrast too low
**Confidence:** low
"""
    findings = parse_findings(output, agent_name="security-reviewer")
    assert len(findings) == 3
    assert findings[0]["severity"] == "P0"
    assert findings[0]["id"] == "SEC-001"
    assert findings[0]["confidence"] == "high"
    assert findings[0]["agent"] == "security-reviewer"
    assert findings[1]["severity"] == "P1"
    assert findings[2]["severity"] == "P2"
    assert findings[2]["confidence"] == "low"


def test_parse_findings_default_confidence():
    output = "[P1] BUG-001: Missing null check\nSome description without confidence."
    findings = parse_findings(output)
    assert len(findings) == 1
    assert findings[0]["confidence"] == "medium"  # Default


def test_parse_findings_empty_output():
    findings = parse_findings("No issues found. Everything looks great!")
    assert len(findings) == 0


def test_check_convergence_clean():
    findings = [{"severity": "P2"}, {"severity": "P2"}]
    result = check_convergence(findings)
    assert result["converged"] is True
    assert result["p0_count"] == 0
    assert result["p1_count"] == 0
    assert result["p2_count"] == 2


def test_check_convergence_empty():
    result = check_convergence([])
    assert result["converged"] is True
    assert result["total"] == 0


def test_check_convergence_not_clean():
    findings = [{"severity": "P1"}, {"severity": "P2"}]
    result = check_convergence(findings)
    assert result["converged"] is False
    assert result["p1_count"] == 1


def test_should_agent_continue_with_p0():
    findings = [{"severity": "P0"}]
    assert should_agent_continue(findings) is True


def test_should_agent_continue_only_p2():
    findings = [{"severity": "P2"}, {"severity": "P2"}]
    assert should_agent_continue(findings) is False


def test_should_agent_continue_empty():
    assert should_agent_continue([]) is False


def test_generate_dashboard():
    rounds = [
        {"round": 1, "findings": [{"severity": "P0"}, {"severity": "P0"}, {"severity": "P1"}]},
        {"round": 2, "findings": [{"severity": "P1"}]},
    ]
    md = generate_dashboard(
        round_num=2, max_rounds=3, rounds=rounds,
        agents_active=["PE Architect", "Code Reviewer"],
        agents_dropped=["Security Reviewer"],
    )
    assert "Round 2 of 3" in md
    assert "Round 1:" in md
    assert "Round 2:" in md
    assert "PE Architect" in md
    assert "Security Reviewer" in md
    assert "dropped" in md.lower()


def test_generate_dashboard_with_current_findings():
    rounds = [{"round": 1, "findings": [{"severity": "P1", "id": "BUG-001", "title": "Missing check"}]}]
    current = [{"severity": "P1", "id": "BUG-001", "title": "Missing check"}]
    md = generate_dashboard(
        round_num=1, max_rounds=3, rounds=rounds,
        agents_active=["Code Reviewer"], agents_dropped=[],
        current_findings=current,
    )
    assert "BUG-001" in md
    assert "Missing check" in md


# ─── Ghost Finding Filter Tests (T-001) ─────────────────────────────────────

def test_parse_findings_ignores_double_dash_separator():
    """REQ-T001 — Lines containing only '--' must not produce findings."""
    output = "--\n--\n---\n----\n"
    findings = parse_findings(output)
    assert findings == []


def test_parse_findings_ignores_dash_only_lines_with_whitespace():
    """REQ-T001 — Dash-only lines with surrounding whitespace are still ghost lines."""
    output = "  --  \n\t---\t\n   ----   \n"
    findings = parse_findings(output)
    assert findings == []


def test_parse_findings_ignores_long_dash_separators():
    """REQ-T001 — Horizontal rules of any length (2+ dashes) produce no findings."""
    output = "----------\n-----------\n"
    findings = parse_findings(output)
    assert findings == []


def test_parse_findings_real_findings_survive_ghost_filter():
    """REQ-T001 — Ghost filter must not suppress valid [P0]/[P1]/[P2] findings."""
    output = """--
---
[P0] SEC-001: SQL injection in user input handler
**Confidence:** high
--
[P1] PE-002: No connection pooling configured
---
"""
    findings = parse_findings(output, agent_name="security-reviewer")
    assert len(findings) == 2
    assert findings[0]["id"] == "SEC-001"
    assert findings[0]["severity"] == "P0"
    assert findings[1]["id"] == "PE-002"
    assert findings[1]["severity"] == "P1"


def test_parse_findings_mixed_content_no_ghost_inflation():
    """REQ-T001 — A realistic agent output with 14 separators produces zero ghost findings."""
    separators = "\n".join(["--"] * 14)
    real_findings = """[P0] BUG-001: Critical null dereference
**Confidence:** high
[P1] BUG-002: Unhandled error path"""
    output = f"{separators}\n{real_findings}\n{separators}\n"
    findings = parse_findings(output)
    assert len(findings) == 2
    assert all(f["id"].startswith("BUG-") for f in findings)


# ─── Multi-Format Severity Parsing Tests ─────────────────────────────────────

def test_parse_findings_bold_dash_format():
    """REQ-SYNTH-001b: **P0** — Title format is extracted by parse_findings."""
    output = "**P0** — SQL injection in login handler\n**Confidence:** high"
    findings = parse_findings(output, agent_name="security-reviewer")
    assert len(findings) == 1
    assert findings[0]["severity"] == "P0"
    assert "SQL injection" in findings[0]["title"]
    assert findings[0]["confidence"] == "high"


def test_parse_findings_bold_colon_format():
    """REQ-SYNTH-001b: **P1**: Title format is extracted by parse_findings."""
    output = "**P1**: Missing rate limiting on /api/login"
    findings = parse_findings(output)
    assert len(findings) == 1
    assert findings[0]["severity"] == "P1"
    assert "rate limiting" in findings[0]["title"]


def test_parse_findings_plain_colon_format():
    """REQ-SYNTH-001c: P2: Title format is extracted by parse_findings."""
    output = "P2: Button contrast ratio is too low for WCAG AA"
    findings = parse_findings(output)
    assert len(findings) == 1
    assert findings[0]["severity"] == "P2"
    assert "contrast" in findings[0]["title"]


def test_parse_findings_plain_dash_format():
    """REQ-SYNTH-001c: P1 - Title format is extracted by parse_findings."""
    output = "P1 - No CSRF token on state-changing endpoints"
    findings = parse_findings(output)
    assert len(findings) == 1
    assert findings[0]["severity"] == "P1"


def test_parse_findings_heading_format():
    """REQ-SYNTH-001d: ### P0-1: Title heading format is extracted by parse_findings."""
    output = "### P0-1: Path traversal via filename parameter"
    findings = parse_findings(output)
    assert len(findings) == 1
    assert findings[0]["severity"] == "P0"
    assert "Path traversal" in findings[0]["title"]


def test_parse_findings_mixed_severity_formats():
    """REQ-SYNTH-001e: Mixed severity formats all produce findings."""
    output = "\n".join([
        "[P0] SEC-001: SQL injection in user input handler",
        "**Confidence:** high",
        "**P1** — No CSRF token on state-changing routes",
        "P2: Weak error messages expose stack traces",
        "### P0-2: Path traversal via filename parameter",
    ])
    findings = parse_findings(output, agent_name="multi-reviewer")
    severities = {f["severity"] for f in findings}
    assert "P0" in severities
    assert "P1" in severities
    assert "P2" in severities
    # At least 4 findings: 2 P0, 1 P1, 1 P2
    assert len(findings) >= 4


def test_parse_findings_ghost_separators_stripped_with_multi_format():
    """REQ-SYNTH-002: Ghost separators don't inflate counts alongside multi-format findings."""
    output = "\n".join([
        "--",
        "**P0** — Critical vulnerability found",
        "---",
        "P1: Secondary issue noted",
        "----",
    ])
    findings = parse_findings(output)
    # Only the real findings survive
    assert all(f["severity"] in ("P0", "P1", "P2") for f in findings)
    assert len(findings) >= 2


# ─── Finding Deduplication Tests ─────────────────────────────────────────────

class TestFindingDeduplication:
    """REQ-DEDUP-001: Deterministic deduplication of identical findings across agents."""

    def _make_finding(self, severity: str, title: str, agent: str) -> dict:
        return {"severity": severity, "title": title, "agent": agent, "id": "", "confidence": "medium", "raw": ""}

    def test_two_agents_same_p0_finding_collapses_to_one(self):
        """REQ-DEDUP-001 — Two agents reporting the same P0 finding produce 1 deduplicated entry."""
        findings = [
            self._make_finding("P0", "SQL injection in login handler", "agent-security"),
            self._make_finding("P0", "SQL injection in login handler", "agent-code"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0]["severity"] == "P0"
        assert set(result[0]["confirmed_by"]) == {"agent-security", "agent-code"}

    def test_same_title_different_severity_kept_separate(self):
        """REQ-DEDUP-001 — Same title but different severity levels are NOT merged."""
        findings = [
            self._make_finding("P0", "Missing input validation", "agent-security"),
            self._make_finding("P1", "Missing input validation", "agent-code"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 2
        severities = {f["severity"] for f in result}
        assert severities == {"P0", "P1"}

    def test_completely_different_findings_all_kept(self):
        """REQ-DEDUP-001 — Completely distinct findings are all preserved."""
        findings = [
            self._make_finding("P0", "SQL injection in login handler", "agent-security"),
            self._make_finding("P1", "No connection pooling configured", "agent-pe"),
            self._make_finding("P2", "Button contrast ratio too low", "agent-ux"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 3

    def test_dedup_is_deterministic(self):
        """REQ-DEDUP-001 — Same input always produces the same output."""
        findings = [
            self._make_finding("P0", "SQL injection in login handler", "agent-1"),
            self._make_finding("P0", "SQL injection in login handler", "agent-2"),
            self._make_finding("P1", "Missing rate limiting", "agent-3"),
        ]
        result_a = deduplicate_findings(findings)
        result_b = deduplicate_findings(findings)
        assert result_a == result_b

    def test_confirmed_by_lists_all_contributing_agents(self):
        """REQ-DEDUP-001 — confirmed_by field includes all agents that reported the finding."""
        findings = [
            self._make_finding("P0", "Path traversal via filename", "agent-1"),
            self._make_finding("P0", "Path traversal via filename", "agent-2"),
            self._make_finding("P0", "Path traversal via filename", "agent-3"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert set(result[0]["confirmed_by"]) == {"agent-1", "agent-2", "agent-3"}

    def test_normalization_ignores_punctuation_and_case(self):
        """REQ-DEDUP-001 — Normalization collapses punctuation/case differences."""
        findings = [
            self._make_finding("P0", "SQL Injection In Login Handler!", "agent-1"),
            self._make_finding("P0", "sql injection in login handler", "agent-2"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert set(result[0]["confirmed_by"]) == {"agent-1", "agent-2"}

    def test_normalization_collapses_whitespace(self):
        """REQ-DEDUP-001 — Extra whitespace is collapsed during normalization."""
        findings = [
            self._make_finding("P0", "Missing  input   validation", "agent-1"),
            self._make_finding("P0", "Missing input validation", "agent-2"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1

    def test_single_agent_finding_has_confirmed_by_with_one_entry(self):
        """REQ-DEDUP-001 — Single-agent findings still get confirmed_by populated."""
        findings = [self._make_finding("P0", "Unique finding", "agent-solo")]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0]["confirmed_by"] == ["agent-solo"]

    def test_empty_findings_list_returns_empty(self):
        """REQ-DEDUP-001 — Empty input produces empty output."""
        assert deduplicate_findings([]) == []
