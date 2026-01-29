#!/usr/bin/env python3
"""
Skill Generator - Generate complete skill structure with SKILL.md

Generate a new skill with SKILL.md, directory structure, and scaffolding.

Usage:
    python skill-generator.py --name "Skill Name" --domain testing --trigger QTEST

Output:
    Creates complete skill directory with SKILL.md and subdirectories
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List


SKILL_TEMPLATE = """---
name: {name}
description: {description}
version: 1.0.0
tools: [{tools}]
references: [{references}]
claude_tools: Read, Grep, Glob, Edit, Write, Bash
trigger: {trigger}
---

# {name}

## Role
You are "{agent_name}", an agent that {purpose}.

## Goals
1. [Goal 1]
2. [Goal 2]
3. [Goal 3]

## Workflow

### Phase 1: [Phase Name]

[Description of phase]

### Phase 2: [Phase Name]

[Description of phase]

## Tools Usage

### scripts/{first_tool}

```bash
python scripts/{first_tool} <input>

# Output: JSON with result
```

## References

### references/{first_reference}

[When to load this reference]

## Usage Examples

### Example 1: [Use Case]

```bash
# Step 1
# Step 2
# Step 3
```

## Configuration

### .claude/{config_file}

```json
{{
  "option": "value"
}}
```

## Story Point Estimation

- **Task 1**: 0.1 SP
- **Task 2**: 0.2 SP

## Best Practices

1. Practice 1
2. Practice 2
3. Practice 3
"""


def generate_skill(
    name: str,
    description: str,
    domain: str,
    tools: List[str],
    references: List[str],
    trigger: str,
    output_path: Path
) -> dict:
    """
    Generate a new skill with complete structure.

    Args:
        name: Skill name
        description: Brief description
        domain: Domain category
        tools: List of tool filenames
        references: List of reference filenames
        trigger: QShortcut trigger command
        output_path: Path to output SKILL.md

    Returns:
        Generation result
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    scripts_dir = output_path.parent / "scripts"
    references_dir = output_path.parent / "references"
    tests_dir = output_path.parent / "tests"

    scripts_dir.mkdir(exist_ok=True)
    references_dir.mkdir(exist_ok=True)
    tests_dir.mkdir(exist_ok=True)

    # Format tools and references for YAML
    tools_yaml = ", ".join(tools) if tools else ""
    references_yaml = ", ".join(references) if references else ""

    # Generate agent name from skill name
    agent_name = name.title().replace(" ", " ")

    # Determine purpose from description
    purpose = description.lower()

    # Get first tool and reference for examples
    first_tool = tools[0] if tools else "tool.py"
    first_reference = references[0] if references else "reference.md"

    # Config file name from trigger
    config_file = f"{trigger.lower()}-config.json"

    # Render template
    content = SKILL_TEMPLATE.format(
        name=name,
        description=description,
        tools=tools_yaml,
        references=references_yaml,
        trigger=trigger,
        agent_name=agent_name,
        purpose=purpose,
        first_tool=first_tool,
        first_reference=first_reference,
        config_file=config_file
    )

    # Write SKILL.md
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Create empty __init__.py in scripts
    (scripts_dir / "__init__.py").touch()

    return {
        "skill_created": {
            "name": name,
            "location": str(output_path.parent),
            "files": [
                str(output_path.relative_to(output_path.parent.parent)),
                "scripts/",
                "references/",
                "tests/"
            ]
        },
        "next_steps": [
            f"Generate tool stubs with tool-stub-generator.py",
            f"Create reference documentation in {references_dir}",
            f"Implement tool logic in {scripts_dir}",
            f"Add tests in {tests_dir}"
        ]
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate new skill structure"
    )

    parser.add_argument("--name", required=True, help="Skill name")
    parser.add_argument("--description", required=True, help="Brief description")
    parser.add_argument("--domain", required=True, help="Domain (testing, content, etc.)")
    parser.add_argument("--tools", help="Comma-separated tool filenames")
    parser.add_argument("--references", help="Comma-separated reference filenames")
    parser.add_argument("--trigger", required=True, help="QShortcut trigger (e.g., QTEST)")
    parser.add_argument("--output", required=True, help="Output path for SKILL.md")

    args = parser.parse_args()

    # Parse tools and references
    tools = [t.strip() for t in args.tools.split(',')] if args.tools else []
    references = [r.strip() for r in args.references.split(',')] if args.references else []

    try:
        result = generate_skill(
            name=args.name,
            description=args.description,
            domain=args.domain,
            tools=tools,
            references=references,
            trigger=args.trigger,
            output_path=Path(args.output)
        )

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
