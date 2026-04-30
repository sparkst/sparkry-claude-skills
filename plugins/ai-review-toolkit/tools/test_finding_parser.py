"""Comprehensive tests for the P0-P3 finding parser."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Import via shared _loader.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

finding_parser = load_sibling("finding-parser.py")

validate_finding = finding_parser.validate_finding
deduplicate_findings = finding_parser.deduplicate_findings
count_by_severity = finding_parser.count_by_severity
check_convergence = finding_parser.check_convergence
synthesize_findings = finding_parser.synthesize_findings
format_findings = finding_parser.format_findings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_finding(**overrides: object) -> dict[str, object]:
    """Return a minimal valid finding, with optional overrides."""
    base: dict[str, object] = {
        "id": "P1-001",
        "severity": "P1",
        "title": "Example title",
        "requirement": "R1",
        "finding": "Something is wrong",
        "recommendation": "Fix it",
        "source": "reviewer-1",
        "evidence": "file.py:1",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_valid_finding_passes(self) -> None:
        valid, errors = validate_finding(_make_finding())
        assert valid is True
        assert errors == []

    def test_valid_finding_with_evidence(self) -> None:
        valid, errors = validate_finding(
            _make_finding(evidence="file.py:42")
        )
        assert valid is True
        assert errors == []

    def test_missing_required_field_id(self) -> None:
        f = _make_finding()
        del f["id"]
        valid, errors = validate_finding(f)
        assert valid is False
        assert any("id" in e for e in errors)

    def test_missing_required_field_severity(self) -> None:
        f = _make_finding()
        del f["severity"]
        valid, errors = validate_finding(f)
        assert valid is False
        assert any("severity" in e for e in errors)

    def test_missing_required_field_title(self) -> None:
        f = _make_finding()
        del f["title"]
        valid, errors = validate_finding(f)
        assert valid is False
        assert any("title" in e for e in errors)

    def test_missing_required_field_source(self) -> None:
        f = _make_finding()
        del f["source"]
        valid, errors = validate_finding(f)
        assert valid is False
        assert any("source" in e for e in errors)

    def test_missing_multiple_fields(self) -> None:
        f = _make_finding()
        del f["id"]
        del f["finding"]
        valid, errors = validate_finding(f)
        assert valid is False
        assert len(errors) == 2

    def test_invalid_severity(self) -> None:
        valid, errors = validate_finding(_make_finding(severity="P4"))
        assert valid is False
        assert any("severity" in e for e in errors)

    def test_invalid_severity_lowercase(self) -> None:
        valid, errors = validate_finding(_make_finding(severity="p0"))
        assert valid is False
        assert any("severity" in e for e in errors)

    def test_invalid_id_format(self) -> None:
        valid, errors = validate_finding(_make_finding(id="X-999"))
        assert valid is False
        assert any("id" in e for e in errors)

    def test_hex_id_format_accepted(self) -> None:
        """Relaxed regex accepts hex-style IDs like P1-a3f2b4c1."""
        valid, errors = validate_finding(_make_finding(id="P1-a3f2b4c1"))
        assert valid is True
        assert errors == []

    def test_id_severity_cross_validation_mismatch(self) -> None:
        """If id starts with P0 but severity is P1, that's an error."""
        valid, errors = validate_finding(
            _make_finding(id="P0-001", severity="P1")
        )
        assert valid is False
        assert any("mismatch" in e for e in errors)

    def test_id_severity_cross_validation_match(self) -> None:
        """Matching id prefix and severity passes."""
        valid, errors = validate_finding(
            _make_finding(id="P0-001", severity="P0")
        )
        assert valid is True
        assert errors == []

    def test_evidence_optional(self) -> None:
        """Evidence is an optional field — missing evidence still valid."""
        f = _make_finding()
        del f["evidence"]
        valid, errors = validate_finding(f)
        assert valid is True
        assert errors == []

    def test_none_field_treated_as_missing(self) -> None:
        valid, errors = validate_finding(_make_finding(title=None))
        assert valid is False
        assert any("title" in e for e in errors)

    def test_empty_string_evidence_still_valid(self) -> None:
        """Empty evidence is accepted (test-runner produces evidence='')."""
        valid, errors = validate_finding(_make_finding(evidence=""))
        assert valid is True
        assert errors == []

    def test_whitespace_only_evidence_still_valid(self) -> None:
        """Whitespace-only evidence is accepted (optional field)."""
        valid, errors = validate_finding(_make_finding(evidence="   "))
        assert valid is True
        assert errors == []

    def test_empty_string_title_treated_as_missing(self) -> None:
        valid, errors = validate_finding(_make_finding(title=""))
        assert valid is False
        assert any("title" in e for e in errors)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    def test_no_duplicates_unchanged(self) -> None:
        findings = [
            _make_finding(id="P1-001", title="Alpha"),
            _make_finding(id="P2-002", title="Beta", severity="P2"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 2

    def test_max_severity_p0_wins_over_p2(self) -> None:
        findings = [
            _make_finding(
                id="P2-001", severity="P2", title="Duplicate",
                source="reviewer-1",
            ),
            _make_finding(
                id="P0-001", severity="P0", title="Duplicate",
                source="reviewer-2",
            ),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0]["severity"] == "P0"

    def test_single_reviewer_p0_not_downgraded(self) -> None:
        """A single-reviewer P0 must never be downgraded by merge."""
        findings = [
            _make_finding(
                id="P0-001", severity="P0", title="Critical bug",
                source="reviewer-1",
            ),
            _make_finding(
                id="P3-002", severity="P3", title="Critical Bug",
                source="reviewer-2",
            ),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0]["severity"] == "P0"

    def test_sources_aggregated(self) -> None:
        findings = [
            _make_finding(
                id="P1-001", title="Issue", source="reviewer-1",
            ),
            _make_finding(
                id="P1-002", title="Issue", source="reviewer-2",
            ),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert set(result[0]["sources"]) == {"reviewer-1", "reviewer-2"}

    def test_evidence_aggregated(self) -> None:
        findings = [
            _make_finding(
                id="P1-001", title="Issue",
                source="r1", evidence="file.py:10",
            ),
            _make_finding(
                id="P1-002", title="Issue",
                source="r2", evidence="file.py:20",
            ),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert "file.py:10" in result[0]["evidence"]
        assert "file.py:20" in result[0]["evidence"]

    def test_fuzzy_title_case_insensitive(self) -> None:
        findings = [
            _make_finding(id="P1-001", title="Missing Auth Check"),
            _make_finding(id="P1-002", title="missing auth check"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1

    def test_fuzzy_title_whitespace_normalized(self) -> None:
        findings = [
            _make_finding(id="P1-001", title="Missing  Auth   Check"),
            _make_finding(id="P1-002", title="Missing Auth Check"),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1

    def test_empty_input(self) -> None:
        assert deduplicate_findings([]) == []

    def test_duplicate_source_not_repeated(self) -> None:
        findings = [
            _make_finding(id="P1-001", title="Dupe", source="r1"),
            _make_finding(id="P1-002", title="Dupe", source="r1"),
        ]
        result = deduplicate_findings(findings)
        assert result[0]["sources"] == ["r1"]

    def test_already_list_evidence_not_re_nested(self) -> None:
        """Re-processing deduplicated findings does not nest evidence lists."""
        first_pass = deduplicate_findings([
            _make_finding(id="P1-001", title="Issue", evidence="file.py:10"),
        ])
        second_pass = deduplicate_findings(first_pass)
        assert second_pass[0]["evidence"] == ["file.py:10"]

    def test_malformed_id_gets_synthetic_after_severity_upgrade(self) -> None:
        """A malformed ID like 'P1-P1-extra' gets a synthetic ID on upgrade."""
        findings = [
            _make_finding(
                id="P1-P1-extra", severity="P1", title="Malformed",
                source="r1",
            ),
            _make_finding(
                id="P0-001", severity="P0", title="Malformed",
                source="r2",
            ),
        ]
        result = deduplicate_findings(findings)
        assert len(result) == 1
        assert result[0]["severity"] == "P0"
        # The original id 'P1-P1-extra' → sub → 'P0-P1-extra' fails validation
        # (hyphen in suffix), so a synthetic dedup id is generated
        assert result[0]["id"] == "P0-dedup-000"

    def test_max_severity_unknown_severity_does_not_crash(self) -> None:
        """_max_severity with unknown severity falls back gracefully."""
        from tools._loader import load_sibling
        fp = load_sibling("finding-parser.py")
        result = fp._max_severity("P0", "UNKNOWN")
        assert result == "P0"


# ---------------------------------------------------------------------------
# Severity counting
# ---------------------------------------------------------------------------

class TestSeverityCounting:
    def test_basic_counts(self) -> None:
        findings = [
            _make_finding(severity="P0"),
            _make_finding(severity="P0"),
            _make_finding(severity="P1"),
            _make_finding(severity="P3"),
        ]
        counts = count_by_severity(findings)
        assert counts == {"P0": 2, "P1": 1, "P2": 0, "P3": 1}

    def test_empty_input(self) -> None:
        counts = count_by_severity([])
        assert counts == {"P0": 0, "P1": 0, "P2": 0, "P3": 0}


# ---------------------------------------------------------------------------
# Convergence
# ---------------------------------------------------------------------------

class TestConvergence:
    def test_p0_zero_p1_zero_p2_zero_converged(self) -> None:
        converged, reason = check_convergence([])
        assert converged is True
        assert reason == "converged"

    def test_p1_present_not_converged(self) -> None:
        findings = [_make_finding(severity="P1")]
        converged, reason = check_convergence(findings)
        assert converged is False
        assert "P1" in reason

    def test_p0_present_not_converged(self) -> None:
        findings = [_make_finding(severity="P0")]
        converged, reason = check_convergence(findings)
        assert converged is False
        assert "P0" in reason

    def test_p2_within_threshold_converged(self) -> None:
        findings = [
            _make_finding(severity="P2"),
            _make_finding(severity="P2"),
        ]
        converged, reason = check_convergence(findings, threshold=3)
        assert converged is True

    def test_p2_exceeds_threshold_not_converged(self) -> None:
        findings = [
            _make_finding(severity="P2"),
            _make_finding(severity="P2"),
        ]
        converged, reason = check_convergence(findings, threshold=0)
        assert converged is False
        assert "threshold" in reason

    def test_only_p3_within_threshold(self) -> None:
        findings = [_make_finding(severity="P3")]
        converged, reason = check_convergence(findings, threshold=1)
        assert converged is True

    def test_p2_plus_p3_combined_against_threshold(self) -> None:
        findings = [
            _make_finding(severity="P2"),
            _make_finding(severity="P3"),
            _make_finding(severity="P3"),
        ]
        converged, _ = check_convergence(findings, threshold=2)
        assert converged is False

    def test_min_findings_zero_default_preserves_behaviour(self) -> None:
        """Default min_findings=0 keeps existing callers working."""
        converged, reason = check_convergence([])
        assert converged is True
        assert reason == "converged"

    def test_min_findings_rejects_empty(self) -> None:
        """When min_findings > 0, empty findings is false-convergence."""
        converged, reason = check_convergence([], min_findings=1)
        assert converged is False
        assert "no valid findings" in reason

    def test_min_findings_rejects_too_few(self) -> None:
        converged, reason = check_convergence(
            [_make_finding(severity="P3")], min_findings=3,
        )
        assert converged is False
        assert "expected at least 3" in reason

    def test_min_findings_passes_when_met(self) -> None:
        findings = [_make_finding(severity="P3")]
        converged, reason = check_convergence(
            findings, threshold=1, min_findings=1,
        )
        assert converged is True
        assert reason == "converged"


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

class TestSynthesis:
    def test_three_reviewers_overlapping(self) -> None:
        r1 = [
            _make_finding(
                id="P0-001", severity="P0", title="SQL Injection",
                source="reviewer-1",
            ),
            _make_finding(
                id="P2-001", severity="P2", title="Typo in docs",
                source="reviewer-1",
            ),
        ]
        r2 = [
            _make_finding(
                id="P1-001", severity="P1", title="sql injection",
                source="reviewer-2",
            ),
            _make_finding(
                id="P3-001", severity="P3", title="Trailing whitespace",
                source="reviewer-2",
            ),
        ]
        r3 = [
            _make_finding(
                id="P2-002", severity="P2", title="SQL Injection",
                source="reviewer-3",
            ),
        ]

        result = synthesize_findings([r1, r2, r3])

        # "SQL Injection" deduped across all 3 → severity P0
        sql_findings = [
            f for f in result if "sql injection" in str(f["title"]).lower()
        ]
        assert len(sql_findings) == 1
        assert sql_findings[0]["severity"] == "P0"
        assert len(sql_findings[0]["sources"]) == 3

        # Total: SQL Injection (merged), Typo in docs, Trailing whitespace
        assert len(result) == 3

        # Sorted P0 first
        assert result[0]["severity"] == "P0"

    def test_invalid_findings_dropped(self) -> None:
        valid = [_make_finding(id="P1-001")]
        invalid = [{"severity": "P0"}]  # Missing most fields
        result = synthesize_findings([valid, invalid])
        assert len(result) == 1

    def test_empty_reviewer_lists(self) -> None:
        result = synthesize_findings([[], [], []])
        assert result == []

    def test_single_reviewer(self) -> None:
        r1 = [
            _make_finding(id="P2-001", severity="P2"),
            _make_finding(id="P0-001", severity="P0"),
        ]
        result = synthesize_findings([r1])
        assert result[0]["severity"] == "P0"  # Sorted P0 first

    def test_warnings_populated_for_invalid_findings(self) -> None:
        valid = [_make_finding(id="P1-001")]
        invalid = [{"severity": "P0"}]  # Missing most fields
        warnings: list[dict[str, object]] = []
        result = synthesize_findings([valid, invalid], warnings=warnings)
        assert len(result) == 1
        assert len(warnings) == 1
        assert "errors" in warnings[0]
        assert "finding" in warnings[0]

    def test_warnings_none_by_default(self) -> None:
        invalid = [{"severity": "P0"}]
        result = synthesize_findings([invalid])
        assert result == []  # No crash even without warnings param


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

class TestFormatting:
    def test_markdown_format(self) -> None:
        findings = [
            _make_finding(
                id="P0-001", severity="P0", title="Critical Bug",
                source="reviewer-1", evidence="main.py:42",
            ),
        ]
        # Dedup to populate sources list
        findings = deduplicate_findings(findings)
        md = format_findings(findings, fmt="markdown")
        assert "### P0-001: Critical Bug" in md
        assert "**Severity:** P0" in md
        assert "**Recommendation:**" in md
        assert "**Evidence:** main.py:42" in md
        assert "**Sources:** reviewer-1" in md

    def test_json_format(self) -> None:
        findings = [_make_finding(id="P1-001")]
        findings = deduplicate_findings(findings)
        output = format_findings(findings, fmt="json")
        parsed = json.loads(output)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["id"] == "P1-001"

    def test_empty_findings_markdown(self) -> None:
        md = format_findings([], fmt="markdown")
        assert md == "No findings."

    def test_empty_findings_json(self) -> None:
        output = format_findings([], fmt="json")
        assert json.loads(output) == []

    def test_multiple_findings_sorted_in_markdown(self) -> None:
        findings = deduplicate_findings([
            _make_finding(id="P3-001", severity="P3", title="Minor"),
            _make_finding(id="P0-001", severity="P0", title="Critical"),
        ])
        # Sort before formatting (synthesis does this)
        findings = sorted(
            findings,
            key=lambda f: finding_parser.SEVERITY_RANK.get(
                str(f["severity"]), 99
            ),
        )
        md = format_findings(findings, fmt="markdown")
        p0_pos = md.index("### P0-001")
        p3_pos = md.index("### P3-001")
        assert p0_pos < p3_pos

    def test_markdown_with_multiple_sources(self) -> None:
        findings = deduplicate_findings([
            _make_finding(id="P1-001", title="Issue", source="r1"),
            _make_finding(id="P1-002", title="Issue", source="r2"),
        ])
        md = format_findings(findings, fmt="markdown")
        assert "r1" in md
        assert "r2" in md
