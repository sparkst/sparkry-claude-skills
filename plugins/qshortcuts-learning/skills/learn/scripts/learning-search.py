#!/usr/bin/env python3
"""
Learning Search - Search and rank learnings by relevance

Search learnings based on context and rank by relevance.

Usage:
    python learning-search.py --domain <domain> --keywords <keywords>
    python learning-search.py --query "<natural language query>"
    python learning-search.py --recent --limit 10

Output (JSON):
    {
      "learnings": [
        {
          "file": "learnings/testing/error-handling.md",
          "title": "Error Handling Patterns",
          "score": 85,
          "domain": "testing",
          "insight": "...",
          "application": ["..."],
          "evidence_count": 5,
          "last_updated": "2026-01-28"
        }
      ],
      "search_context": {...},
      "summary": {...}
    }
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional


def search_learnings(
    learning_dir: Path = Path("learnings"),
    domain: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    activity: Optional[str] = None,
    technologies: Optional[List[str]] = None,
    recent_only: bool = False,
    limit: int = 5,
    min_score: int = 30
) -> Dict[str, Any]:
    """
    Search learnings with multiple filters and rank by relevance.

    Args:
        learning_dir: Root directory for learnings
        domain: Domain filter (testing, security, api, etc.)
        keywords: List of keywords to search for
        activity: Activity type (implementation, debugging, etc.)
        technologies: List of technologies
        recent_only: Only return learnings from last 30 days
        limit: Maximum number of results
        min_score: Minimum relevance score

    Returns:
        Search results with ranked learnings
    """
    if not learning_dir.exists():
        return {
            "learnings": [],
            "search_context": {},
            "summary": {"total_found": 0}
        }

    # Find all learning files
    learning_files = list(learning_dir.rglob("*.md"))

    # Filter by domain if specified
    if domain:
        learning_files = [
            f for f in learning_files
            if domain in str(f.parent.name)
        ]

    # Parse and score each learning
    scored_learnings = []

    for learning_file in learning_files:
        try:
            learning = parse_learning_file(learning_file, learning_dir)

            # Calculate relevance score
            score = calculate_relevance_score(
                learning,
                keywords=keywords,
                domain=domain,
                activity=activity,
                technologies=technologies,
                recent_only=recent_only
            )

            if score >= min_score:
                learning['score'] = score
                scored_learnings.append(learning)

        except Exception as e:
            print(f"Error parsing {learning_file}: {e}", file=sys.stderr)
            continue

    # Sort by score descending
    scored_learnings.sort(key=lambda x: x['score'], reverse=True)

    # Limit results
    top_learnings = scored_learnings[:limit]

    # Generate summary
    summary = generate_search_summary(scored_learnings)

    return {
        "learnings": top_learnings,
        "search_context": {
            "domain": domain,
            "keywords": keywords or [],
            "activity": activity,
            "technologies": technologies or [],
            "recent_only": recent_only
        },
        "summary": summary
    }


def parse_learning_file(file_path: Path, learning_dir: Path) -> Dict[str, Any]:
    """
    Parse a learning file and extract structured data.

    Args:
        file_path: Path to learning file
        learning_dir: Root learning directory

    Returns:
        Parsed learning data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract sections
    title = extract_title(content)
    context = extract_section(content, "Context")
    insight = extract_section(content, "Insight")
    evidence = extract_evidence_items(content)
    application = extract_application_items(content)
    related = extract_related_items(content)

    # Extract metadata
    file_stat = file_path.stat()
    last_updated = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d")

    # Determine domain from path
    domain = file_path.parent.name

    return {
        "file": str(file_path.relative_to(learning_dir.parent)),
        "title": title,
        "domain": domain,
        "context": context,
        "insight": insight,
        "application": application,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "related": related,
        "last_updated": last_updated,
        "full_content": content,
    }


def extract_title(content: str) -> str:
    """Extract title from markdown (first # heading)."""
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    return match.group(1).strip() if match else "Untitled"


def extract_section(content: str, section_name: str) -> str:
    """Extract content from a markdown section."""
    pattern = rf'##\s+{section_name}\s*\n(.*?)(?=\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_evidence_items(content: str) -> List[str]:
    """Extract evidence bullet points."""
    evidence_section = extract_section(content, "Evidence")
    items = re.findall(r'^-\s+(.+)$', evidence_section, re.MULTILINE)
    return items


def extract_application_items(content: str) -> List[str]:
    """Extract application bullet points."""
    application_section = extract_section(content, "Application")
    items = re.findall(r'^-\s+(.+)$', application_section, re.MULTILINE)
    return items


def extract_related_items(content: str) -> List[str]:
    """Extract related learning links."""
    related_section = extract_section(content, "Related")
    items = re.findall(r'^-\s+(.+)$', related_section, re.MULTILINE)
    return items


def calculate_relevance_score(
    learning: Dict[str, Any],
    keywords: Optional[List[str]] = None,
    domain: Optional[str] = None,
    activity: Optional[str] = None,
    technologies: Optional[List[str]] = None,
    recent_only: bool = False
) -> int:
    """
    Calculate relevance score for a learning.

    Score = keyword_match * 0.4 + domain_match * 0.3 + activity_match * 0.2 + recency * 0.1

    Returns:
        Score from 0-100
    """
    scores = {
        'keyword': 0,
        'domain': 0,
        'activity': 0,
        'recency': 0
    }

    content_lower = learning['full_content'].lower()

    # Keyword matching (0-100)
    if keywords:
        keyword_matches = sum(
            1 for keyword in keywords
            if keyword.lower() in content_lower
        )
        # Boost if keyword in title or insight
        title_matches = sum(
            1 for keyword in keywords
            if keyword.lower() in learning['title'].lower()
        )
        insight_matches = sum(
            1 for keyword in keywords
            if keyword.lower() in learning['insight'].lower()
        )

        scores['keyword'] = min(100, (
            keyword_matches * 20 +
            title_matches * 30 +
            insight_matches * 25
        ))

    # Domain matching (0-100)
    if domain:
        if learning['domain'] == domain:
            scores['domain'] = 100
        elif domain in content_lower:
            scores['domain'] = 50

    # Activity matching (0-100)
    if activity:
        if activity.lower() in content_lower:
            scores['activity'] = 100
        # Check for activity synonyms
        activity_synonyms = {
            'implementation': ['implement', 'code', 'build'],
            'debugging': ['debug', 'fix', 'troubleshoot'],
            'refactoring': ['refactor', 'restructure', 'redesign'],
            'review': ['review', 'audit', 'check'],
        }
        if activity in activity_synonyms:
            if any(syn in content_lower for syn in activity_synonyms[activity]):
                scores['activity'] = 75

    # Recency score (0-100)
    try:
        last_updated = datetime.strptime(learning['last_updated'], "%Y-%m-%d")
        days_old = (datetime.now() - last_updated).days

        if days_old <= 7:
            scores['recency'] = 100
        elif days_old <= 30:
            scores['recency'] = 80
        elif days_old <= 90:
            scores['recency'] = 60
        else:
            scores['recency'] = 40

        # Filter out old learnings if recent_only
        if recent_only and days_old > 30:
            return 0

    except Exception:
        scores['recency'] = 40

    # Calculate weighted total
    total_score = (
        scores['keyword'] * 0.4 +
        scores['domain'] * 0.3 +
        scores['activity'] * 0.2 +
        scores['recency'] * 0.1
    )

    # Boost by evidence count (more evidence = more validated)
    evidence_boost = min(20, learning['evidence_count'] * 2)

    final_score = min(100, int(total_score + evidence_boost))

    return final_score


def generate_search_summary(learnings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics for search results."""
    total = len(learnings)

    high_relevance = sum(1 for l in learnings if l['score'] >= 70)
    medium_relevance = sum(1 for l in learnings if 50 <= l['score'] < 70)
    low_relevance = sum(1 for l in learnings if 30 <= l['score'] < 50)

    avg_score = sum(l['score'] for l in learnings) / total if total > 0 else 0

    return {
        "total_found": total,
        "high_relevance": high_relevance,
        "medium_relevance": medium_relevance,
        "low_relevance": low_relevance,
        "avg_score": round(avg_score, 1)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Search learnings by context and relevance"
    )

    parser.add_argument("--domain", help="Domain filter (testing, security, etc.)")
    parser.add_argument("--keywords", help="Comma-separated keywords")
    parser.add_argument("--activity", help="Activity type (implementation, debugging, etc.)")
    parser.add_argument("--tech", help="Comma-separated technologies")
    parser.add_argument("--query", help="Natural language query")
    parser.add_argument("--recent", action="store_true", help="Recent learnings only (last 30 days)")
    parser.add_argument("--limit", type=int, default=5, help="Maximum results")
    parser.add_argument("--min-score", type=int, default=30, help="Minimum relevance score")
    parser.add_argument("--learning-dir", default="learnings", help="Learning directory")

    args = parser.parse_args()

    # Parse arguments
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(',')]
    elif args.query:
        # Extract keywords from natural language query
        keywords = extract_keywords_from_query(args.query)

    technologies = None
    if args.tech:
        technologies = [t.strip() for t in args.tech.split(',')]

    try:
        # Search learnings
        results = search_learnings(
            learning_dir=Path(args.learning_dir),
            domain=args.domain,
            keywords=keywords,
            activity=args.activity,
            technologies=technologies,
            recent_only=args.recent,
            limit=args.limit,
            min_score=args.min_score
        )

        # Clean up learnings for output (remove full_content)
        for learning in results['learnings']:
            learning.pop('full_content', None)

        print(json.dumps(results, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


def extract_keywords_from_query(query: str) -> List[str]:
    """Extract keywords from natural language query."""
    # Remove common stop words
    stop_words = {'how', 'to', 'the', 'a', 'an', 'is', 'are', 'in', 'on', 'for', 'with', 'do', 'i'}

    words = re.findall(r'\w+', query.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    return keywords


if __name__ == "__main__":
    main()
