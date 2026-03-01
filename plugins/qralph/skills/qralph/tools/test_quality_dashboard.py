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
