#!/usr/bin/env python3
"""
Learning Integrator - Integrate feedback into learning files

Integrates categorized feedback into relevant learning files.

Usage:
    python learning-integrator.py <categorized-feedback.json>

Output (JSON):
    {
      "learnings_updated": 3,
      "learnings_created": 1,
      "cross_references_added": 2,
      "files": ["learnings/testing/error-handling.md"],
      "integration_log": [
        {
          "feedback_id": "FB-001",
          "learning_file": "learnings/testing/error-handling.md",
          "action": "append",
          "section": "Evidence"
        }
      ]
    }
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple


LEARNING_TEMPLATE = """# {title}

## Context
{context}

## Insight
{insight}

## Evidence
{evidence}

## Application
{application}

## Related
{related}
"""


def integrate_feedback(
    feedback_items: List[Dict[str, Any]],
    learning_dir: Path = Path("learnings")
) -> Dict[str, Any]:
    """
    Integrate feedback items into learning files.

    Args:
        feedback_items: List of categorized feedback
        learning_dir: Root directory for learnings

    Returns:
        Integration results with statistics
    """
    integration_log = []
    updated_files = set()
    created_files = set()
    cross_references = 0

    for item in feedback_items:
        # Determine target learning file
        learning_file = determine_learning_file(item, learning_dir)

        # Integrate into file
        action, added_refs = integrate_item(item, learning_file)

        # Log integration
        integration_log.append({
            "feedback_id": item['id'],
            "learning_file": str(learning_file),
            "action": action,
            "section": "Evidence",
        })

        # Track statistics
        if action == "create":
            created_files.add(str(learning_file))
        else:
            updated_files.add(str(learning_file))

        cross_references += added_refs

    return {
        "learnings_updated": len(updated_files),
        "learnings_created": len(created_files),
        "cross_references_added": cross_references,
        "files": sorted(updated_files | created_files),
        "integration_log": integration_log,
    }


def determine_learning_file(item: Dict[str, Any], learning_dir: Path) -> Path:
    """
    Determine the target learning file for a feedback item.

    Args:
        item: Feedback item
        learning_dir: Root directory for learnings

    Returns:
        Path to learning file
    """
    domain = item['domain']
    category = item['category'].lower()

    # Map category to learning file
    filename_map = {
        'bug': 'common-issues.md',
        'enhancement': 'improvements.md',
        'architecture': 'design-patterns.md',
        'performance': 'optimization.md',
        'documentation': 'docs-improvements.md',
        'ux': 'user-experience.md',
    }

    filename = filename_map.get(category, 'general.md')

    learning_file = learning_dir / domain / filename

    return learning_file


def integrate_item(item: Dict[str, Any], learning_file: Path) -> Tuple[str, int]:
    """
    Integrate a single feedback item into a learning file.

    Args:
        item: Feedback item
        learning_file: Target learning file

    Returns:
        Tuple of (action, cross_references_added)
    """
    # Ensure directory exists
    learning_file.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists
    if learning_file.exists():
        action = append_to_learning(item, learning_file)
        cross_refs = 0
    else:
        action = create_learning(item, learning_file)
        cross_refs = 0

    return action, cross_refs


def create_learning(item: Dict[str, Any], learning_file: Path) -> str:
    """
    Create a new learning file from feedback item.

    Args:
        item: Feedback item
        learning_file: Target learning file

    Returns:
        Action taken ("create")
    """
    title = f"{item['domain'].title()} - {item['category']}"

    context = f"Feedback from: {item['source']}\n{item.get('context', '')}"

    insight = item['content']

    evidence = f"- [{item['source']}]: {item['content']}"

    application = "\n".join(f"- {action}" for action in item['action_items'])

    related = "\n".join(f"- {path}" for path in item['related_learnings'])

    content = LEARNING_TEMPLATE.format(
        title=title,
        context=context,
        insight=insight,
        evidence=evidence,
        application=application,
        related=related,
    )

    with open(learning_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return "create"


def append_to_learning(item: Dict[str, Any], learning_file: Path) -> str:
    """
    Append feedback to existing learning file.

    Args:
        item: Feedback item
        learning_file: Target learning file

    Returns:
        Action taken ("append")
    """
    # Read existing content
    with open(learning_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create evidence entry
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    evidence_entry = f"\n- [{timestamp}] [{item['source']}]: {item['content']}"

    # Find Evidence section and append
    if "## Evidence" in content:
        # Insert after Evidence header
        parts = content.split("## Evidence")
        if len(parts) > 1:
            # Find next section
            next_section_idx = parts[1].find("\n## ")
            if next_section_idx != -1:
                # Insert before next section
                updated = (
                    parts[0] +
                    "## Evidence" +
                    parts[1][:next_section_idx] +
                    evidence_entry +
                    parts[1][next_section_idx:]
                )
            else:
                # Append at end of Evidence section
                updated = (
                    parts[0] +
                    "## Evidence" +
                    parts[1] +
                    evidence_entry
                )

            with open(learning_file, 'w', encoding='utf-8') as f:
                f.write(updated)

            return "append"

    # If no Evidence section, append at end
    with open(learning_file, 'a', encoding='utf-8') as f:
        f.write(f"\n\n## Evidence\n{evidence_entry}")

    return "append"


def main():
    if len(sys.argv) < 2:
        print("Usage: python learning-integrator.py <categorized-feedback.json>", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(json.dumps({
            "error": f"File not found: {input_file}"
        }))
        sys.exit(1)

    try:
        # Load categorized feedback
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        feedback_items = data.get('feedback', [])

        # Integrate feedback
        result = integrate_feedback(feedback_items)

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
