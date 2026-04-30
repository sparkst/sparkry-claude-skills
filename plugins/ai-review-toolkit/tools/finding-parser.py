"""Deterministic finding parser for the P0-P3 review taxonomy.

Validates, deduplicates, synthesizes, and formats findings across
multiple reviewers. Pure functions, no side effects.
"""

from __future__ import annotations

import json
import re

SEVERITIES: list[str] = ["P0", "P1", "P2", "P3"]
SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(SEVERITIES)}

REQUIRED_FIELDS: list[str] = [
    "id",
    "severity",
    "title",
    "requirement",
    "finding",
    "recommendation",
    "source",
]

OPTIONAL_FIELDS: list[str] = [
    "evidence",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_finding(finding: dict[str, object]) -> tuple[bool, list[str]]:
    """Validate a single finding dict against the schema.

    Returns (valid, errors) where *errors* is empty when valid.
    """
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        val = finding.get(field)
        if val is None or (isinstance(val, str) and not val.strip()):
            errors.append(f"missing required field: {field}")

    severity = finding.get("severity")
    if severity is not None and severity not in SEVERITIES:
        errors.append(
            f"invalid severity '{severity}'; must be one of {SEVERITIES}"
        )

    fid = finding.get("id")
    if isinstance(fid, str) and not re.match(r"^P[0-3]-[a-zA-Z0-9]{3,}$", fid):
        errors.append(
            f"invalid id format '{fid}'; expected pattern P[0-3]-<alphanumeric 3+>"
        )

    # Cross-validate id prefix against severity
    if (
        isinstance(fid, str)
        and severity is not None
        and severity in SEVERITIES
        and re.match(r"^P[0-3]-", fid)
        and not fid.startswith(str(severity))
    ):
        errors.append(
            f"id/severity mismatch: id '{fid}' does not start with severity '{severity}'"
        )

    return (not errors, errors)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_title(title: str) -> str:
    """Lowercase, collapse whitespace for fuzzy title matching."""
    return re.sub(r"\s+", " ", title.strip().lower())


def _max_severity(a: str, b: str) -> str:
    """Return the higher severity (P0 > P1 > P2 > P3)."""
    return a if SEVERITY_RANK.get(a, 99) <= SEVERITY_RANK.get(b, 99) else b


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate_findings(findings: list[dict[str, object]]) -> list[dict[str, object]]:
    """Merge findings with fuzzy-matching titles, keeping max severity.

    Rules:
    - Normalized-lowercase title equality is the match key.
    - Merged finding gets the MAX severity (P0 beats everything).
    - All sources aggregated into a ``sources`` list.
    - All evidence aggregated into an ``evidence`` list.
    - A single-reviewer P0/P1 is NEVER downgraded by merge.
    """
    buckets: dict[str, dict[str, object]] = {}
    order: list[str] = []

    for f in findings:
        title_raw: str = str(f.get("title", ""))
        key = _normalize_title(title_raw)

        source: str = str(f.get("source", ""))
        raw_evidence = f.get("evidence")
        evidence_items: list[str] = []
        if isinstance(raw_evidence, list):
            evidence_items = [str(e) for e in raw_evidence if e]
        elif raw_evidence:
            evidence_items = [str(raw_evidence)]

        if key not in buckets:
            order.append(key)
            merged: dict[str, object] = {
                "id": f["id"],
                "severity": f["severity"],
                "title": title_raw,
                "requirement": f.get("requirement", ""),
                "finding": f.get("finding", ""),
                "recommendation": f.get("recommendation", ""),
                "source": source or "",
                "sources": [source] if source else [],
                "evidence": list(evidence_items),
            }
            buckets[key] = merged
        else:
            existing = buckets[key]
            new_sev = _max_severity(
                str(existing["severity"]), str(f["severity"])
            )
            if new_sev != existing["severity"]:
                existing["severity"] = new_sev
                old_id = str(existing["id"])
                candidate_id = re.sub(r"^P[0-3]", new_sev, old_id)
                if re.match(r"^P[0-3]-[a-zA-Z0-9]{3,}$", candidate_id):
                    existing["id"] = candidate_id
                else:
                    idx = order.index(key)
                    existing["id"] = f"{new_sev}-dedup-{idx:03d}"
            sources_list: list[str] = existing["sources"]  # type: ignore[assignment]
            if source and source not in sources_list:
                sources_list.append(source)
            evidence_list: list[str] = existing["evidence"]  # type: ignore[assignment]
            for ev in evidence_items:
                if ev not in evidence_list:
                    evidence_list.append(ev)

    return [buckets[k] for k in order]


# ---------------------------------------------------------------------------
# Severity counting
# ---------------------------------------------------------------------------

def count_by_severity(findings: list[dict[str, object]]) -> dict[str, int]:
    """Return counts keyed by severity level."""
    counts: dict[str, int] = {s: 0 for s in SEVERITIES}
    for f in findings:
        sev = str(f.get("severity", ""))
        if sev in counts:
            counts[sev] += 1
    return counts


# ---------------------------------------------------------------------------
# Convergence
# ---------------------------------------------------------------------------

def check_convergence(
    findings: list[dict[str, object]],
    threshold: int = 0,
    min_findings: int = 0,
) -> tuple[bool, str]:
    """Check whether findings converge (safe to ship).

    Converged when P0 == 0 AND P1 == 0 AND (P2 + P3) <= threshold.

    When *min_findings* > 0 and fewer valid findings are present,
    convergence fails — this guards against false-convergence when
    all reviewer outputs are invalid JSON and every finding is dropped.
    """
    if min_findings > 0 and len(findings) < min_findings:
        return (
            False,
            f"no valid findings to evaluate — expected at least "
            f"{min_findings}, got {len(findings)}",
        )

    counts = count_by_severity(findings)
    p0 = counts["P0"]
    p1 = counts["P1"]
    low = counts["P2"] + counts["P3"]

    if p0 > 0:
        return (False, f"{p0} P0 finding(s) remain")
    if p1 > 0:
        return (False, f"{p1} P1 finding(s) remain")
    if low > threshold:
        return (
            False,
            f"{low} low-severity finding(s) exceed threshold ({threshold})",
        )
    return (True, "converged")


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------

def _sort_findings(findings: list[dict[str, object]]) -> list[dict[str, object]]:
    """Sort findings by severity (P0 first), then by id."""
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_RANK.get(str(f.get("severity", "P3")), 99),
            str(f.get("id", "")),
        ),
    )


def synthesize_findings(
    reviewer_results: list[list[dict[str, object]]],
    warnings: list[dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Validate, merge, deduplicate, and sort findings from N reviewers.

    Invalid findings are dropped. When *warnings* is provided (a list),
    each dropped finding is appended as ``{"finding": ..., "errors": ...}``
    for observability.
    """
    all_valid: list[dict[str, object]] = []
    for reviewer_list in reviewer_results:
        for finding in reviewer_list:
            valid, errors = validate_finding(finding)
            if valid:
                all_valid.append(finding)
            elif warnings is not None:
                warnings.append({"finding": finding, "errors": errors})

    deduped = deduplicate_findings(all_valid)
    return _sort_findings(deduped)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_findings(
    findings: list[dict[str, object]],
    fmt: str = "markdown",
) -> str:
    """Format findings as markdown or JSON.

    Markdown uses ``### P0-001: Title`` heading style.
    """
    if fmt == "json":
        return json.dumps(findings, indent=2, default=str)

    if not findings:
        return "No findings."

    lines: list[str] = []
    for f in findings:
        fid = f.get("id", "?")
        title = f.get("title", "Untitled")
        severity = f.get("severity", "?")
        requirement = f.get("requirement", "")
        finding_text = f.get("finding", "")
        recommendation = f.get("recommendation", "")
        evidence_raw = f.get("evidence", "")
        if isinstance(evidence_raw, list):
            evidence = evidence_raw
        elif evidence_raw:
            evidence = [evidence_raw]
        else:
            evidence = []
        sources = f.get("sources", [f.get("source", "")])

        lines.append(f"### {fid}: {title}")
        lines.append(f"**Severity:** {severity}")
        lines.append(f"**Requirement:** {requirement}")
        lines.append(f"**Finding:** {finding_text}")
        lines.append(f"**Recommendation:** {recommendation}")

        if evidence:
            evidence_str = ", ".join(str(e) for e in evidence if e)
            if evidence_str:
                lines.append(f"**Evidence:** {evidence_str}")

        if isinstance(sources, list) and sources:
            lines.append(f"**Sources:** {', '.join(str(s) for s in sources)}")
        elif sources:
            lines.append(f"**Sources:** {sources}")

        lines.append("")

    return "\n".join(lines).rstrip()
