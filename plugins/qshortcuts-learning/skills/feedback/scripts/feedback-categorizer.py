#!/usr/bin/env python3
"""
Feedback Categorizer - Categorize feedback using taxonomy and priority rules

Categorizes extracted feedback by type, priority, and domain.

Usage:
    python feedback-categorizer.py <extracted-feedback.json>

Output (JSON):
    {
      "feedback": [
        {
          "id": "FB-001",
          "category": "Enhancement",
          "priority": "P1",
          "domain": "testing",
          "content": "Add better error handling",
          "source": "projects/feature-x/src/validator.ts:42",
          "related_learnings": ["learnings/testing/error-handling.md"],
          "action_items": ["Implement error handling strategy"]
        }
      ],
      "summary": {
        "by_category": {"Enhancement": 3, "Bug": 2},
        "by_priority": {"P0": 1, "P1": 4},
        "by_domain": {"testing": 2, "ux": 3}
      }
    }
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any


# Category keywords
CATEGORY_KEYWORDS = {
    'Enhancement': ['add', 'improve', 'enhance', 'better', 'optimize', 'refactor'],
    'Bug': ['fix', 'bug', 'broken', 'error', 'crash', 'issue', 'wrong'],
    'UX': ['ux', 'user', 'confusing', 'unclear', 'interface', 'workflow'],
    'Performance': ['slow', 'performance', 'optimize', 'speed', 'efficient', 'cache'],
    'Documentation': ['docs', 'document', 'readme', 'comment', 'explain', 'example'],
    'Architecture': ['architecture', 'design', 'structure', 'pattern', 'refactor', 'decouple'],
}

# Priority keywords
PRIORITY_KEYWORDS = {
    'P0': ['critical', 'blocker', 'urgent', 'asap', 'immediately', 'breaking'],
    'P1': ['important', 'should', 'needed', 'high', 'must'],
    'P2': ['nice', 'would', 'could', 'consider', 'maybe'],
    'P3': ['future', 'someday', 'low', 'minor', 'eventually'],
}

# Domain keywords
DOMAIN_KEYWORDS = {
    'testing': ['test', 'spec', 'coverage', 'assert', 'mock'],
    'security': ['security', 'auth', 'permission', 'vulnerability', 'encrypt'],
    'api': ['api', 'endpoint', 'route', 'request', 'response'],
    'database': ['database', 'query', 'sql', 'schema', 'migration'],
    'frontend': ['ui', 'component', 'render', 'view', 'page'],
    'backend': ['server', 'service', 'handler', 'controller', 'middleware'],
    'devops': ['deploy', 'ci', 'cd', 'build', 'pipeline', 'docker'],
}


def categorize_feedback(extraction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Categorize a single feedback extraction.

    Args:
        extraction: Extracted comment with metadata

    Returns:
        Categorized feedback item
    """
    content_lower = extraction['content'].lower()
    source_lower = extraction['source'].lower()

    # Determine category
    category = determine_category(content_lower)

    # Determine priority
    priority = determine_priority(content_lower, extraction['type'])

    # Determine domain
    domain = determine_domain(content_lower, source_lower)

    # Find related learnings
    related_learnings = find_related_learnings(domain, category)

    # Generate action items
    action_items = generate_action_items(category, extraction['content'])

    return {
        "id": f"FB-{extraction['id'].split('-')[1]}",
        "category": category,
        "priority": priority,
        "domain": domain,
        "content": extraction['content'],
        "source": extraction['source'],
        "context": extraction.get('context', ''),
        "related_learnings": related_learnings,
        "action_items": action_items,
    }


def determine_category(content: str) -> str:
    """
    Determine feedback category based on keywords.

    Args:
        content: Feedback content (lowercase)

    Returns:
        Category name
    """
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in content)
        if score > 0:
            scores[category] = score

    # Return highest scoring category, or 'Enhancement' as default
    if scores:
        return max(scores, key=scores.get)

    return 'Enhancement'


def determine_priority(content: str, comment_type: str) -> str:
    """
    Determine feedback priority based on keywords and type.

    Args:
        content: Feedback content (lowercase)
        comment_type: Comment type (TODO, FIXME, etc.)

    Returns:
        Priority level (P0-P3)
    """
    # FIXME is usually higher priority
    if comment_type == 'FIXME':
        base_priority = 'P1'
    else:
        base_priority = 'P2'

    # Check for priority keywords
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(keyword in content for keyword in keywords):
            return priority

    return base_priority


def determine_domain(content: str, source: str) -> str:
    """
    Determine feedback domain based on content and source.

    Args:
        content: Feedback content (lowercase)
        source: Source file path (lowercase)

    Returns:
        Domain name
    """
    scores = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        # Score from content
        content_score = sum(1 for keyword in keywords if keyword in content)

        # Score from source path
        source_score = sum(1 for keyword in keywords if keyword in source)

        total_score = content_score + (source_score * 2)  # Weight source higher

        if total_score > 0:
            scores[domain] = total_score

    # Return highest scoring domain, or 'general' as default
    if scores:
        return max(scores, key=scores.get)

    return 'general'


def find_related_learnings(domain: str, category: str) -> List[str]:
    """
    Find related learning files based on domain and category.

    Args:
        domain: Feedback domain
        category: Feedback category

    Returns:
        List of related learning file paths
    """
    # This is a stub - would scan learnings directory in real implementation
    learning_paths = []

    # Example patterns
    if domain != 'general':
        learning_paths.append(f"learnings/{domain}/overview.md")

    if category == 'Bug':
        learning_paths.append(f"learnings/{domain}/common-issues.md")
    elif category == 'Architecture':
        learning_paths.append(f"learnings/{domain}/design-patterns.md")

    return learning_paths


def generate_action_items(category: str, content: str) -> List[str]:
    """
    Generate action items based on feedback.

    Args:
        category: Feedback category
        content: Feedback content

    Returns:
        List of action items
    """
    actions = []

    if category == 'Bug':
        actions.append(f"Fix: {content}")
        actions.append("Add test to prevent regression")
    elif category == 'Enhancement':
        actions.append(f"Implement: {content}")
        actions.append("Update documentation")
    elif category == 'Documentation':
        actions.append(f"Document: {content}")
    elif category == 'Architecture':
        actions.append(f"Design review: {content}")
        actions.append("Create ADR if significant")

    return actions


def generate_summary(feedback_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for categorized feedback.

    Args:
        feedback_items: List of categorized feedback

    Returns:
        Summary dictionary
    """
    summary = {
        "by_category": {},
        "by_priority": {},
        "by_domain": {},
    }

    for item in feedback_items:
        # Count by category
        category = item['category']
        summary['by_category'][category] = summary['by_category'].get(category, 0) + 1

        # Count by priority
        priority = item['priority']
        summary['by_priority'][priority] = summary['by_priority'].get(priority, 0) + 1

        # Count by domain
        domain = item['domain']
        summary['by_domain'][domain] = summary['by_domain'].get(domain, 0) + 1

    return summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python feedback-categorizer.py <extracted-feedback.json>", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(json.dumps({
            "error": f"File not found: {input_file}"
        }))
        sys.exit(1)

    try:
        # Load extracted feedback
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        extractions = data.get('extractions', [])

        # Categorize each extraction
        feedback_items = [categorize_feedback(ext) for ext in extractions]

        # Generate summary
        summary = generate_summary(feedback_items)

        # Output result
        result = {
            "feedback": feedback_items,
            "summary": summary
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
