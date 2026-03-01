"""Tests for learning-capture.py — extracts patterns from quality loop findings."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_extract_learnings_from_findings():
    """Should convert quality loop findings into learning entries."""
    from learning_capture import extract_learnings
    findings = [
        {"severity": "P0", "id": "SEC-001", "title": "SQL injection in user input", "agent": "security-reviewer", "fix_applied": "parameterized queries"},
        {"severity": "P1", "id": "PE-002", "title": "No connection pooling", "agent": "pe-architect", "fix_applied": "added pg pool config"},
    ]
    learnings = extract_learnings(findings, project_id="042-task-app")
    assert len(learnings) == 2
    assert learnings[0]["category"] == "error_pattern"
    assert learnings[0]["domain"] == "security"
    assert "SQL injection" in learnings[0]["description"]
    assert "parameterized" in learnings[0]["fix"]


def test_extract_learnings_skips_p2():
    """P2 findings should not be captured as learnings (noise)."""
    from learning_capture import extract_learnings
    findings = [
        {"severity": "P2", "id": "UX-003", "title": "Button contrast low", "agent": "usability", "fix_applied": "increased contrast"},
    ]
    learnings = extract_learnings(findings, project_id="042")
    assert len(learnings) == 0


def test_extract_learnings_with_empty_findings():
    """Should return empty list for no findings."""
    from learning_capture import extract_learnings
    assert extract_learnings([], project_id="042") == []


def test_detect_cross_project_patterns():
    """Should detect patterns appearing across 3+ projects."""
    from learning_capture import detect_cross_project_patterns
    memories = [
        {"project": "040", "domain": "security", "description": "SQL injection found"},
        {"project": "038", "domain": "security", "description": "SQL injection in search"},
        {"project": "035", "domain": "security", "description": "Unparameterized SQL query"},
    ]
    patterns = detect_cross_project_patterns(memories, threshold=3)
    assert len(patterns) >= 1
    assert any("sql" in p["pattern"].lower() for p in patterns)


def test_detect_patterns_below_threshold():
    """Should not detect patterns below threshold."""
    from learning_capture import detect_cross_project_patterns
    memories = [
        {"project": "040", "domain": "security", "description": "SQL injection found"},
        {"project": "038", "domain": "security", "description": "SQL injection in search"},
    ]
    patterns = detect_cross_project_patterns(memories, threshold=3)
    assert len(patterns) == 0


def test_generate_claude_md_proposal():
    """Should generate a CLAUDE.md update proposal when pattern is confirmed."""
    from learning_capture import generate_claude_md_proposal
    pattern = {
        "pattern": "SQL injection vulnerabilities in user input handlers",
        "frequency": 3,
        "domain": "security",
        "recommended_rule": "Always use parameterized queries for user input",
    }
    proposal = generate_claude_md_proposal(pattern)
    assert "parameterized" in proposal.lower()
    assert "security" in proposal.lower()


def test_generate_learning_summary():
    """Should produce a markdown summary of learnings for the project."""
    from learning_capture import generate_learning_summary
    learnings = [
        {"domain": "security", "description": "SQL injection found", "fix": "parameterized queries", "project_id": "042"},
        {"domain": "architecture", "description": "Missing connection pool", "fix": "added pool config", "project_id": "042"},
    ]
    summary = generate_learning_summary(learnings, project_id="042")
    assert "security" in summary.lower()
    assert "architecture" in summary.lower()
    assert "042" in summary
