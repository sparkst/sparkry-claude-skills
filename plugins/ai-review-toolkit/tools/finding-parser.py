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

REVIEWER_OUTPUT_INSTRUCTIONS: str = """\
Output your findings as a JSON array. Each finding must have these fields:
- id: string matching pattern P[0-3]-NNN (e.g., P0-001, P1-002)
- severity: one of P0, P1, P2, P3
- title: concise description of the issue
- requirement: which requirement this relates to
- finding: detailed description of the problem
- recommendation: how to fix it
- source: "{reviewer_name}"
- evidence: file path and line number if applicable

Severity guide:
- P0: Blocks shipping (correctness, security, data loss, requirement violation)
- P1: Must fix before v1 (quality, error handling, incomplete coverage)
- P2: Should fix (code smell, suboptimal pattern, minor UX, doc gap)
- P3: Nice to have (style, optional optimization, cosmetic)

Output ONLY the JSON array. No other text.\
"""


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
    key_index: dict[str, int] = {}

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
            idx = len(order)
            order.append(key)
            key_index[key] = idx
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
                    existing["id"] = f"{new_sev}-dedup-{key_index[key]:03d}"
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


# ---------------------------------------------------------------------------
# Fix-completeness gate
# ---------------------------------------------------------------------------

ALLOWED_STATUSES: set[str] = {"FIXED", "ESCALATED"}
PROHIBITED_STATUSES: set[str] = {"WONTFIX", "DEFERRED", "OUT_OF_SCOPE"}


def check_fix_completeness(
    findings: list[dict[str, object]],
    resolutions: list[dict[str, object]],
) -> tuple[bool, list[str]]:
    """Returns (complete, missing_or_invalid_finding_ids).

    Every finding must have a corresponding resolution whose status is
    FIXED or ESCALATED.  Prohibited statuses (WONTFIX, DEFERRED,
    OUT_OF_SCOPE) are treated as invalid.
    """
    finding_ids: set[str] = {str(f["id"]) for f in findings if f.get("id")}

    valid_resolved_ids: set[str] = set()
    invalid_ids: list[str] = []
    for r in resolutions:
        fid = r.get("finding_id")
        if not fid:
            continue
        status = str(r.get("status", ""))
        if status not in ALLOWED_STATUSES:
            invalid_ids.append(str(fid))
        else:
            evidence = r.get("evidence")
            if not evidence or (isinstance(evidence, str) and not evidence.strip()):
                invalid_ids.append(str(fid))
            else:
                valid_resolved_ids.add(str(fid))

    missing = sorted((finding_ids - valid_resolved_ids) | (set(invalid_ids) - valid_resolved_ids))
    return (not missing, missing)


# ---------------------------------------------------------------------------
# Reviewer / fixer prompt construction
#
# Oracle for the JS port (js/prompts.mjs), locked via gen-prompt-fixtures.py +
# test_prompt_parity.py against fixtures/prompts.json. These read a loop-state
# dict shaped like {team, artifact_path, requirements_path, rounds: [...]} --
# the same shape review-loop.workflow.js keeps in-memory during a run.
# ---------------------------------------------------------------------------

def _get_round(state: dict[str, object], num: int) -> dict[str, object] | None:
    """Return the round dict for the given round number, or None."""
    for r in state.get("rounds", []):  # type: ignore[union-attr]
        if r["round_num"] == num:
            return r
    return None


def get_reviewer_prompt(
    state: dict[str, object],
    reviewer_index: int,
    round_num: int,
) -> str:
    """Generate reviewer prompt. Round 2+ includes prior findings + diff summary."""
    team = state.get("team", [])
    if reviewer_index < 0 or reviewer_index >= len(team):  # type: ignore[arg-type]
        raise ValueError(f"Reviewer index {reviewer_index} out of range (team size {len(team)}).")  # type: ignore[arg-type]

    agent = team[reviewer_index]  # type: ignore[index]
    artifact_path = state.get("artifact_path", "")
    requirements_path = state.get("requirements_path", "")

    try:
        with open(artifact_path, "r", encoding="utf-8", errors="replace") as fh:  # type: ignore[arg-type]
            artifact_content = fh.read()
    except OSError:
        artifact_content = f"[Could not read artifact at {artifact_path}]"

    try:
        with open(requirements_path, "r", encoding="utf-8", errors="replace") as fh:  # type: ignore[arg-type]
            requirements_content = fh.read()
    except OSError:
        requirements_content = f"[Could not read requirements at {requirements_path}]"

    current_round = _get_round(state, round_num)
    test_summary = "No test results available."
    if current_round:
        tr = current_round.get("test_results", {})
        if tr:
            test_summary = tr.get("summary", "No test results available.")

    reviewer_name = agent["name"]
    review_lens = agent["review_lens"]

    prompt_parts = [
        f"You are a {reviewer_name} reviewing an artifact.",
        "",
        f"Your review lens: {review_lens}",
        "",
        "## Artifact",
        "",
        artifact_content,
        "",
        "## Requirements",
        "",
        requirements_content,
        "",
        "## Test Results",
        "",
        test_summary,
    ]

    # Round 2+ additions
    if round_num > 1:
        prev_round = _get_round(state, round_num - 1)
        if prev_round:
            prev_findings = prev_round.get("findings", [])
            if prev_findings:
                findings_text = format_findings(prev_findings, fmt="markdown")
                prompt_parts.extend([
                    "",
                    f"## Prior Round Findings (Round {round_num - 1})",
                    "",
                    findings_text,
                ])

            prev_resolutions = prev_round.get("fix_resolutions", [])
            if prev_resolutions:
                res_lines = []
                for res in prev_resolutions:
                    fid = res.get("finding_id", "?")
                    status = res.get("status", "?")
                    desc = res.get("description", "")
                    evidence = res.get("evidence", "")
                    res_lines.append(f"- **{fid}**: {status} -- {desc}")
                    if evidence:
                        res_lines.append(f"  Evidence: {evidence}")
                prompt_parts.extend([
                    "",
                    "## Fix Resolutions Applied",
                    "",
                    "\n".join(res_lines),
                ])

            prompt_parts.extend([
                "",
                "## Verification Instructions",
                "",
                f"The artifact content above is the POST-FIX version (after round {round_num - 1} fixes). "
                "For each fix resolution listed above, navigate to the cited evidence location "
                "in the artifact and verify the fix is correct. Also check for NEW issues "
                "introduced by the fixes — regressions, broken logic, incomplete changes.",
            ])

    output_instructions = REVIEWER_OUTPUT_INSTRUCTIONS.format(reviewer_name=reviewer_name)
    prompt_parts.extend([
        "",
        "## Instructions",
        "",
        f"Review the artifact against the requirements through your lens of {review_lens}.",
        "",
        output_instructions,
    ])

    return "\n".join(prompt_parts)


def get_fixer_prompt(state: dict[str, object], round_num: int) -> str:
    """Generate fixer prompt with all findings and recommendations."""
    artifact_path = state.get("artifact_path", "")
    requirements_path = state.get("requirements_path", "")

    try:
        with open(artifact_path, "r", encoding="utf-8", errors="replace") as fh:  # type: ignore[arg-type]
            artifact_content = fh.read()
    except OSError:
        artifact_content = f"[Could not read artifact at {artifact_path}]"

    try:
        with open(requirements_path, "r", encoding="utf-8", errors="replace") as fh:  # type: ignore[arg-type]
            requirements_content = fh.read()
    except OSError:
        requirements_content = f"[Could not read requirements at {requirements_path}]"

    current_round = _get_round(state, round_num)
    findings: list[dict[str, object]] = []
    test_summary = ""
    if current_round:
        findings = current_round.get("findings", [])
        tr = current_round.get("test_results", {})
        test_summary = tr.get("summary", "") if tr else ""

    findings_text = format_findings(findings, fmt="markdown")

    prompt = f"""You are a fixer agent. Your job is to fix ALL findings from the review.

## Artifact

{artifact_content}

## Requirements

{requirements_content}

## Test Results

{test_summary}

## Findings to Fix (ALL must be addressed)

{findings_text}

## Instructions

Fix EVERY finding listed above. Every single one, regardless of severity (P0 through P3).

For each finding, produce a resolution with these fields:
- finding_id: the ID of the finding being resolved (e.g., P0-001)
- status: MUST be "FIXED" with evidence of the fix. No WONTFIX, DEFERRED, or OUT_OF_SCOPE.
- evidence: what changed and where (file:line for code, section:quote for content)
- description: brief explanation of the fix

If a finding is genuinely unfixable (requires external dependency, architectural constraint, or user decision), set status to "ESCALATED" with justification.

Output a JSON array of resolution objects. No other text."""

    return prompt
