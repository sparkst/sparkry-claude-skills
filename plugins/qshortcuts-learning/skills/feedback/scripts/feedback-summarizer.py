#!/usr/bin/env python3
"""
Feedback Summarizer - Generate summary report of feedback trends

Analyzes feedback patterns and generates summary report.

Usage:
    python feedback-summarizer.py <learning-directory>

Output: feedback-summary.md with visualizations and trends
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any


def analyze_learnings(learning_dir: Path) -> Dict[str, Any]:
    """
    Analyze learning files to extract feedback trends.

    Args:
        learning_dir: Root directory for learnings

    Returns:
        Analysis results
    """
    analysis = {
        "total_learnings": 0,
        "total_evidence": 0,
        "by_domain": defaultdict(int),
        "by_category": defaultdict(int),
        "recent_feedback": [],
        "top_sources": defaultdict(int),
    }

    if not learning_dir.exists():
        return analysis

    # Scan all learning files
    for learning_file in learning_dir.rglob("*.md"):
        if learning_file.is_file():
            analysis["total_learnings"] += 1

            # Extract domain from path
            domain = learning_file.parent.name

            # Parse learning file
            with open(learning_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Count evidence entries
            evidence_entries = extract_evidence_entries(content)
            analysis["total_evidence"] += len(evidence_entries)

            # Categorize
            category = learning_file.stem.replace('-', ' ').title()
            analysis["by_category"][category] += len(evidence_entries)
            analysis["by_domain"][domain] += len(evidence_entries)

            # Track recent feedback
            for entry in evidence_entries:
                analysis["recent_feedback"].append({
                    "date": entry.get("date", "unknown"),
                    "source": entry.get("source", "unknown"),
                    "content": entry.get("content", ""),
                    "learning": str(learning_file.relative_to(learning_dir)),
                })

                # Track source frequency
                source = entry.get("source", "unknown")
                analysis["top_sources"][source] += 1

    # Sort recent feedback by date
    analysis["recent_feedback"].sort(
        key=lambda x: x["date"],
        reverse=True
    )

    # Keep only top 10 recent
    analysis["recent_feedback"] = analysis["recent_feedback"][:10]

    # Convert defaultdicts to regular dicts
    analysis["by_domain"] = dict(analysis["by_domain"])
    analysis["by_category"] = dict(analysis["by_category"])
    analysis["top_sources"] = dict(sorted(
        analysis["top_sources"].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10])

    return analysis


def extract_evidence_entries(content: str) -> List[Dict[str, Any]]:
    """
    Extract evidence entries from learning file content.

    Args:
        content: Learning file content

    Returns:
        List of evidence entries
    """
    entries = []

    # Find Evidence section
    if "## Evidence" not in content:
        return entries

    # Extract Evidence section
    parts = content.split("## Evidence")
    if len(parts) < 2:
        return entries

    evidence_section = parts[1].split("\n## ")[0]

    # Parse bullet points
    lines = evidence_section.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('-'):
            # Parse format: - [date] [source]: content
            entry = parse_evidence_line(line)
            if entry:
                entries.append(entry)

    return entries


def parse_evidence_line(line: str) -> Dict[str, Any]:
    """
    Parse an evidence line into structured data.

    Args:
        line: Evidence line (e.g., "- [2026-01-28] [file.ts:42]: content")

    Returns:
        Parsed entry or None
    """
    import re

    # Pattern: - [date] [source]: content
    # Or: - [source]: content (without date)
    pattern = r'-\s*(?:\[([^\]]+)\]\s*)?\[([^\]]+)\]:\s*(.+)'

    match = re.match(pattern, line)
    if match:
        date = match.group(1) or "unknown"
        source = match.group(2)
        content = match.group(3)

        return {
            "date": date,
            "source": source,
            "content": content,
        }

    return None


def generate_summary_markdown(analysis: Dict[str, Any]) -> str:
    """
    Generate markdown summary report.

    Args:
        analysis: Analysis results

    Returns:
        Markdown content
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"""# Feedback Summary Report

Generated: {timestamp}

## Overview

- **Total Learning Files**: {analysis['total_learnings']}
- **Total Evidence Entries**: {analysis['total_evidence']}
- **Active Domains**: {len(analysis['by_domain'])}

## Feedback by Domain

| Domain | Count | Percentage |
|--------|-------|------------|
"""

    total = analysis['total_evidence']
    for domain, count in sorted(analysis['by_domain'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        md += f"| {domain} | {count} | {percentage:.1f}% |\n"

    md += "\n## Feedback by Category\n\n"
    md += "| Category | Count | Percentage |\n"
    md += "|----------|-------|------------|\n"

    for category, count in sorted(analysis['by_category'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total * 100) if total > 0 else 0
        md += f"| {category} | {count} | {percentage:.1f}% |\n"

    md += "\n## Recent Feedback (Last 10)\n\n"

    for entry in analysis['recent_feedback']:
        md += f"### {entry['date']}\n"
        md += f"- **Source**: `{entry['source']}`\n"
        md += f"- **Learning**: `{entry['learning']}`\n"
        md += f"- **Content**: {entry['content']}\n\n"

    md += "## Top Feedback Sources\n\n"
    md += "| Source | Count |\n"
    md += "|--------|-------|\n"

    for source, count in analysis['top_sources'].items():
        md += f"| `{source}` | {count} |\n"

    md += "\n## Trends & Insights\n\n"

    # Generate insights
    if analysis['by_domain']:
        top_domain = max(analysis['by_domain'].items(), key=lambda x: x[1])
        md += f"- **Most Active Domain**: `{top_domain[0]}` ({top_domain[1]} items)\n"

    if analysis['by_category']:
        top_category = max(analysis['by_category'].items(), key=lambda x: x[1])
        md += f"- **Most Common Category**: `{top_category[0]}` ({top_category[1]} items)\n"

    if analysis['recent_feedback']:
        md += f"- **Recent Activity**: {len(analysis['recent_feedback'])} feedback items in recent period\n"

    md += "\n## Action Items\n\n"
    md += "Based on the feedback analysis:\n\n"
    md += "1. Review high-frequency feedback sources for systematic issues\n"
    md += "2. Address feedback in most active domains\n"
    md += "3. Update documentation for common categories\n"
    md += "4. Consider creating new learnings for emerging patterns\n"

    md += "\n---\n\n"
    md += "*Generated by feedback-summarizer.py*\n"

    return md


def main():
    if len(sys.argv) < 2:
        print("Usage: python feedback-summarizer.py <learning-directory>", file=sys.stderr)
        sys.exit(1)

    learning_dir = Path(sys.argv[1])

    if not learning_dir.exists():
        print(f"Error: Directory not found: {learning_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        # Analyze learnings
        analysis = analyze_learnings(learning_dir)

        # Generate summary markdown
        summary_md = generate_summary_markdown(analysis)

        # Write to file
        output_file = Path("feedback-summary.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(summary_md)

        print(f"Summary generated: {output_file}")

        # Also output JSON for programmatic use
        print(json.dumps(analysis, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
