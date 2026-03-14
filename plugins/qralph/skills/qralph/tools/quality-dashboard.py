"""Quality dashboard for QRALPH quality loop.

Parses review agent findings and generates convergence dashboards.
"""

from __future__ import annotations

import re


_GHOST_SEPARATOR_RE = re.compile(r"^-{2,}\s*$")

# Patterns tried in priority order — each captures (severity, id_or_empty, title).
# Groups: (1) severity digit, (2) optional finding-ID token, (3) title text.
_FINDING_PATTERNS: list[re.Pattern] = [
    # [P0] ID-NNN: title  (canonical bracket + ID format)
    re.compile(r"\[(P[012])\]\s+(\S+):\s+(.+)"),
    # [P0] title  (bracket format without ID)
    re.compile(r"\[(P[012])\]\s+()(.+)"),
    # **P0** — title  or  **P0**: title  (bold format)
    re.compile(r"\*\*(P[012])\*\*\s*[—:\-]\s*()(.+)"),
    # ### P0-1: title  or  ## P0: title  (heading format)
    re.compile(r"^#+\s+(P[012])[\s\-:]+()(.+)"),
    # P0: title  or  P0 - title  or  P0 — title  (plain format)
    re.compile(r"(?<!\[)(P[012])\s*[:\-—]\s*()(.+)"),
]


def parse_findings(output: str, agent_name: str = "") -> list[dict]:
    """Extract P0/P1/P2 findings from agent output.

    Accepts findings in multiple severity formats:
    - ``[P0] ID-NNN: title`` (canonical bracket + ID)
    - ``[P0] title`` (bracket without ID)
    - ``**P0** — title`` / ``**P0**: title`` (bold format)
    - ``### P0: title`` (heading format)
    - ``P0: title`` / ``P0 - title`` (plain format)

    Extracts confidence from ``**Confidence:** high`` patterns in the text
    following each finding.

    Lines that are pure markdown separators (``--``, ``---``, etc.) are
    discarded before pattern matching so they never inflate finding counts.
    """
    confidence_pattern = re.compile(r"\*\*Confidence:\*\*\s+(high|medium|low)", re.IGNORECASE)

    findings: list[dict] = []
    lines = output.split("\n")

    def _match_finding(line: str):
        """Return the first pattern match for a finding line, or None."""
        for pat in _FINDING_PATTERNS:
            m = pat.search(line)
            if m:
                return m
        return None

    for i, line in enumerate(lines):
        if _GHOST_SEPARATOR_RE.match(line.strip()):
            continue
        match = _match_finding(line)
        if not match:
            continue

        severity = match.group(1)
        finding_id = match.group(2)  # may be empty string for non-ID formats
        title = match.group(3).strip()

        # Look ahead for confidence until next finding or end
        confidence = "medium"
        for j in range(i + 1, len(lines)):
            if _match_finding(lines[j]):
                break
            conf_match = confidence_pattern.search(lines[j])
            if conf_match:
                confidence = conf_match.group(1).lower()
                break

        findings.append({
            "severity": severity,
            "id": finding_id,
            "title": title,
            "agent": agent_name,
            "confidence": confidence,
            "raw": line.strip(),
        })

    return findings


def check_convergence(findings: list[dict], prev_findings: list[dict] | None = None) -> dict:
    """Check if the quality loop has converged.

    Converged when zero P0 and zero P1 findings.
    Regressed when P0 count increased vs previous round with truly new P0s.
    """
    p0 = sum(1 for f in findings if f["severity"] == "P0")
    p1 = sum(1 for f in findings if f["severity"] == "P1")
    p2 = sum(1 for f in findings if f["severity"] == "P2")

    regressed = False
    if prev_findings is not None:
        prev_p0 = sum(1 for f in prev_findings if f["severity"] == "P0")
        if p0 > prev_p0:
            prev_p0_ids = {f["id"] for f in prev_findings if f.get("severity") == "P0" and "id" in f}
            curr_p0_ids = {f["id"] for f in findings if f.get("severity") == "P0" and "id" in f}
            new_p0s = curr_p0_ids - prev_p0_ids
            regressed = len(new_p0s) > 0

    # Stagnation: P0+P1 barely changed (delta <= 1) with 3+ issues remaining
    if prev_findings is not None:
        prev_p01 = sum(1 for f in prev_findings if f["severity"] in ("P0", "P1"))
        curr_p01 = p0 + p1
        delta = prev_p01 - curr_p01
        stagnant = (delta <= 1 and curr_p01 >= 3)
    else:
        stagnant = False

    return {
        "converged": p0 == 0 and p1 == 0,
        "p0_count": p0,
        "p1_count": p1,
        "p2_count": p2,
        "total": len(findings),
        "regressed": regressed,
        "stagnant": stagnant,
    }


def should_agent_continue(agent_findings: list[dict]) -> bool:
    """Determine whether an agent should run another review round.

    Returns True if any finding is P0 or P1.
    """
    return any(f["severity"] in ("P0", "P1") for f in agent_findings)


def deduplicate_findings(findings: list[dict]) -> list[dict]:
    """Collapse identical findings reported by multiple agents into one entry.

    Two findings are considered identical when their (severity, normalized_text)
    pair matches. Normalization: lowercase, strip punctuation, collapse whitespace.
    Different severities for the same title are kept separate per the AC.

    Each resulting entry gains a ``confirmed_by`` list of all agent names that
    reported the finding. The first occurrence in the input order is kept as the
    base record.

    Purely deterministic — no LLM calls, no embeddings.
    """
    _punct_re = re.compile(r"[^\w\s]")
    _ws_re = re.compile(r"\s+")

    def _normalize(text: str) -> str:
        text = text.lower()
        text = _punct_re.sub("", text)
        text = _ws_re.sub(" ", text).strip()
        return text

    seen: dict[tuple[str, str], int] = {}  # (severity, normalized_title) → index in result
    result: list[dict] = []

    for finding in findings:
        severity = finding.get("severity", "")
        title = finding.get("title", "")
        key = (severity, _normalize(title))

        if key in seen:
            idx = seen[key]
            agent = finding.get("agent", "")
            if agent and agent not in result[idx]["confirmed_by"]:
                result[idx]["confirmed_by"].append(agent)
        else:
            entry = dict(finding)
            agent = finding.get("agent", "")
            entry["confirmed_by"] = [agent] if agent else []
            seen[key] = len(result)
            result.append(entry)

    return result


def compute_finding_deltas(prev_findings: list[dict], curr_findings: list[dict]) -> dict[str, str]:
    """Compute disposition of each finding across two rounds.

    Returns dict mapping finding ID to: "NEW", "CARRY_FORWARD", or "FIXED".
    """
    prev_ids = {f["id"] for f in prev_findings if "id" in f}
    curr_ids = {f["id"] for f in curr_findings if "id" in f}

    deltas = {}
    for fid in curr_ids:
        deltas[fid] = "CARRY_FORWARD" if fid in prev_ids else "NEW"
    for fid in prev_ids:
        if fid not in curr_ids:
            deltas[fid] = "FIXED"
    return deltas


def generate_dashboard(
    round_num: int,
    max_rounds: int,
    rounds: list[dict],
    agents_active: list[str],
    agents_dropped: list[str],
    current_findings: list[dict] | None = None,
) -> str:
    """Generate a markdown quality convergence dashboard."""
    lines: list[str] = []
    lines.append(f"# Quality Dashboard - Round {round_num} of {max_rounds}")
    lines.append("")

    # Convergence history
    lines.append("## Convergence History")
    lines.append("")
    for r in rounds:
        findings = r["findings"]
        conv = check_convergence(findings)
        status = "CONVERGED" if conv["converged"] else "OPEN"
        lines.append(
            f"- Round {r['round']}: P0={conv['p0_count']} P1={conv['p1_count']} "
            f"P2={conv['p2_count']} [{status}]"
        )
    lines.append("")

    # Agents
    lines.append("## Agents")
    lines.append("")
    if agents_active:
        lines.append("**Active:**")
        for a in agents_active:
            lines.append(f"- {a}")
        lines.append("")
    if agents_dropped:
        lines.append("**Dropped:**")
        for a in agents_dropped:
            lines.append(f"- {a}")
        lines.append("")

    # Current findings detail
    if current_findings:
        lines.append("## Current Findings")
        lines.append("")
        for f in current_findings:
            fid = f.get("id", "???")
            title = f.get("title", "")
            sev = f.get("severity", "??")
            lines.append(f"- [{sev}] {fid}: {title}")
        lines.append("")

    return "\n".join(lines)
