"""Quality dashboard for QRALPH quality loop.

Parses review agent findings and generates convergence dashboards.
"""

import re


def parse_findings(output: str, agent_name: str = "") -> list[dict]:
    """Extract P0/P1/P2 findings from agent output.

    Parses lines matching ``[P0] ID-NNN: title`` and extracts confidence
    from ``**Confidence:** high`` patterns in the text following each finding.
    """
    pattern = re.compile(r"\[(P[012])\]\s+(\S+):\s+(.+)")
    confidence_pattern = re.compile(r"\*\*Confidence:\*\*\s+(high|medium|low)", re.IGNORECASE)

    findings: list[dict] = []
    lines = output.split("\n")

    for i, line in enumerate(lines):
        match = pattern.search(line)
        if not match:
            continue

        severity = match.group(1)
        finding_id = match.group(2)
        title = match.group(3).strip()

        # Look ahead for confidence until next finding or end
        confidence = "medium"
        for j in range(i + 1, len(lines)):
            if pattern.search(lines[j]):
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


def check_convergence(findings: list[dict]) -> dict:
    """Check if the quality loop has converged.

    Converged when there are zero P0 and zero P1 findings.
    """
    p0 = sum(1 for f in findings if f["severity"] == "P0")
    p1 = sum(1 for f in findings if f["severity"] == "P1")
    p2 = sum(1 for f in findings if f["severity"] == "P2")

    return {
        "converged": p0 == 0 and p1 == 0,
        "p0_count": p0,
        "p1_count": p1,
        "p2_count": p2,
        "total": len(findings),
    }


def should_agent_continue(agent_findings: list[dict]) -> bool:
    """Determine whether an agent should run another review round.

    Returns True if any finding is P0 or P1.
    """
    return any(f["severity"] in ("P0", "P1") for f in agent_findings)


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
