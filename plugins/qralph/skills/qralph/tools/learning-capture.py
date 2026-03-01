#!/usr/bin/env python3
"""
Learning Capture - Extracts patterns from quality loop findings for cross-project intelligence.

Converts quality review findings into learning entries, detects recurring patterns
across projects, and generates CLAUDE.md update proposals.
"""

import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional


# Agent name to domain mapping
AGENT_DOMAIN_MAP = {
    "security-reviewer": "security",
    "security": "security",
    "pe-architect": "architecture",
    "pe-reviewer": "architecture",
    "failure-analyst": "reliability",
    "usability": "usability",
    "usability-reviewer": "usability",
    "business-advisor": "business",
    "code-reviewer": "code_quality",
}


def extract_learnings(findings: List[Dict], project_id: str) -> List[Dict]:
    """
    Convert quality loop findings into learning entries.

    Only captures P0 and P1 findings (P2 is noise for learning purposes).

    Args:
        findings: List of finding dicts with severity, id, title, agent, fix_applied
        project_id: Project identifier

    Returns:
        List of learning entry dicts
    """
    learnings = []
    for finding in findings:
        severity = finding.get("severity", "")
        if severity not in ("P0", "P1"):
            continue

        agent = finding.get("agent", "unknown")
        domain = AGENT_DOMAIN_MAP.get(agent, "general")

        learnings.append({
            "category": "error_pattern",
            "domain": domain,
            "description": finding.get("title", ""),
            "fix": finding.get("fix_applied", ""),
            "severity": severity,
            "finding_id": finding.get("id", ""),
            "project_id": project_id,
        })

    return learnings


def detect_cross_project_patterns(memories: List[Dict], threshold: int = 3) -> List[Dict]:
    """
    Detect patterns appearing across multiple projects.

    Groups memories by domain and uses keyword overlap to find recurring issues.

    Args:
        memories: List of memory dicts with project, domain, description
        threshold: Minimum number of distinct projects for a pattern

    Returns:
        List of pattern dicts with pattern, frequency, domain, projects
    """
    # Group by domain
    by_domain = defaultdict(list)
    for mem in memories:
        by_domain[mem.get("domain", "general")].append(mem)

    patterns = []
    for domain, mems in by_domain.items():
        # Extract keywords from descriptions
        all_keywords = []
        for mem in mems:
            desc = mem.get("description", "").lower()
            words = re.findall(r'\b[a-z]{3,}\b', desc)
            all_keywords.extend(words)

        # Find common keywords
        keyword_counts = Counter(all_keywords)
        common = [kw for kw, count in keyword_counts.items() if count >= threshold]

        if not common:
            continue

        # Check distinct project count
        projects = {mem.get("project", "") for mem in mems}
        if len(projects) < threshold:
            continue

        # Build pattern description from common keywords
        pattern_desc = f"{domain}: recurring issues with {', '.join(common[:5])}"
        patterns.append({
            "pattern": pattern_desc,
            "frequency": len(projects),
            "domain": domain,
            "projects": sorted(projects),
            "keywords": common[:10],
        })

    return patterns


def generate_claude_md_proposal(pattern: Dict) -> str:
    """
    Generate a CLAUDE.md update proposal for a confirmed cross-project pattern.

    Args:
        pattern: Pattern dict with pattern, frequency, domain, recommended_rule

    Returns:
        Markdown string with proposed CLAUDE.md addition
    """
    domain = pattern.get("domain", "general")
    rule = pattern.get("recommended_rule", pattern.get("pattern", ""))
    freq = pattern.get("frequency", 0)

    return (
        f"## Proposed CLAUDE.md Update — {domain.title()}\n\n"
        f"**Pattern detected across {freq} projects:** {pattern.get('pattern', '')}\n\n"
        f"**Proposed rule:**\n"
        f"- {rule}\n\n"
        f"**Domain:** {domain}\n"
        f"**Confidence:** Confirmed across {freq} projects\n"
    )


def generate_learning_summary(learnings: List[Dict], project_id: str) -> str:
    """
    Generate a markdown summary of learnings captured from a project.

    Args:
        learnings: List of learning entry dicts
        project_id: Project identifier

    Returns:
        Markdown summary string
    """
    if not learnings:
        return f"# Learning Summary — {project_id}\n\nNo significant learnings captured.\n"

    by_domain = defaultdict(list)
    for learning in learnings:
        by_domain[learning.get("domain", "general")].append(learning)

    lines = [f"# Learning Summary — {project_id}\n"]
    lines.append(f"**Total learnings captured:** {len(learnings)}\n")

    for domain in sorted(by_domain.keys()):
        domain_learnings = by_domain[domain]
        lines.append(f"\n## {domain.title()}\n")
        for learning in domain_learnings:
            lines.append(f"- **{learning.get('description', '')}**")
            if learning.get("fix"):
                lines.append(f"  - Fix: {learning['fix']}")

    return "\n".join(lines)
