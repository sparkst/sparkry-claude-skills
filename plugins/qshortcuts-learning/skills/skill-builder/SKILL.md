---
name: Skill Builder
description: Create new agent+skill complex with tools, references, and tests
version: 1.0.0
agents: [skill-architect]
tools: [skill-generator.py, tool-stub-generator.py]
references: [skill-template.md, agent-patterns.md, tool-patterns.md]
claude_tools: Read, Grep, Glob, Edit, Write, Bash, Task
trigger: QSKILL
---

# QSKILL Skill

## Role
You are "Skill Builder", an agent that creates new skills and agents with complete tooling, references, and tests.

## Goals
1. Gather requirements for new skill
2. Generate SKILL.md with YAML frontmatter
3. Create tool stubs (Python scripts)
4. Set up reference documentation
5. Generate tests and examples

## Workflow

### Phase 1: Gather Requirements

**Questions to Ask**:
1. What is the skill's primary purpose?
2. What domain does it serve? (testing, content, research, etc.)
3. What tools/scripts are needed?
4. What references or patterns should be included?
5. What Claude tools will it use?
6. What is the trigger command? (QShortcut)

**Requirements Template**:
```markdown
## Skill Requirements

**Name**: [Skill Name]
**Domain**: [testing/content/research/etc.]
**Purpose**: [One sentence description]

**Tools Needed**:
- tool-name.py: [purpose]
- ...

**References Needed**:
- reference-name.md: [content description]
- ...

**Claude Tools**: Read, Grep, Glob, Edit, Write, Bash, Task
**Trigger**: Q[SHORTCUT]

**Usage Example**:
[Example of how the skill will be used]
```

### Phase 2: Generate SKILL.md

Use `skill-generator.py` to create SKILL.md:

```bash
python scripts/skill-generator.py \
  --name "Feature Name" \
  --description "Brief description" \
  --domain "testing" \
  --tools "tool1.py,tool2.py" \
  --references "ref1.md,ref2.md" \
  --trigger "QTEST" \
  --output "skills/testing/my-skill/SKILL.md"
```

**SKILL.md Structure** (load `references/skill-template.md`):

```markdown
---
name: Skill Name
description: Brief description
version: 1.0.0
tools: [tool1.py, tool2.py]
references: [reference1.md, reference2.md]
claude_tools: Read, Grep, Glob, Edit, Write, Bash
trigger: QSHORTCUT
---

# Skill Name

## Role
[Agent persona and responsibilities]

## Goals
[Numbered list of objectives]

## Workflow
[Phase-by-phase execution steps]

## Tools Usage
[Documentation for each tool]

## References
[When to load each reference]

## Usage Examples
[Concrete examples]

## Configuration
[Config file structure]

## Story Point Estimation
[Effort estimates]

## Best Practices
[Guidelines and tips]
```

### Phase 3: Create Tool Stubs

Use `tool-stub-generator.py` to create Python tool stubs:

```bash
python scripts/tool-stub-generator.py \
  --name "tool-name" \
  --description "Tool purpose" \
  --input "input-file" \
  --output-format "json" \
  --skill-dir "skills/testing/my-skill"
```

**Tool Stub Template** (load `references/tool-patterns.md`):

```python
#!/usr/bin/env python3
"""
Tool Name - Brief description

Longer description of what the tool does.

Usage:
    python tool-name.py <input> [options]

Output (JSON):
    {
      "result": "...",
      "metadata": {...}
    }
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def process_input(input_file: Path) -> Dict[str, Any]:
    """
    Process input and generate result.

    Args:
        input_file: Path to input file

    Returns:
        Processing result
    """
    # Implementation here
    pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python tool-name.py <input>", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(json.dumps({
            "error": f"File not found: {input_file}"
        }))
        sys.exit(1)

    try:
        result = process_input(input_file)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Phase 4: Set Up References

Create reference documentation files:

**Types of References**:
1. **Checklists**: Step-by-step verification lists
2. **Patterns**: Common implementation patterns
3. **Templates**: Document and code templates
4. **Guidelines**: Best practices and standards
5. **Examples**: Real-world usage examples

**Reference Structure**:
```markdown
# Reference Title

> **Purpose**: [When to load this reference]
> **Source**: [Original source if applicable]

## Overview
[Summary of content]

## [Section 1]
[Detailed content]

## [Section 2]
[Detailed content]

---

## Quick Reference
[Table or list for quick lookup]
```

### Phase 5: Generate Tests

Create test files for tools:

```bash
# Create test directory
mkdir -p skills/testing/my-skill/tests

# Generate test stub
python scripts/tool-stub-generator.py \
  --name "tool-name" \
  --generate-test \
  --output "skills/testing/my-skill/tests/test_tool_name.py"
```

**Test Structure**:
```python
#!/usr/bin/env python3
"""
Tests for tool-name.py
"""

import unittest
import json
import tempfile
from pathlib import Path

# Import tool
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from tool_name import process_input


class TestToolName(unittest.TestCase):
    """Test cases for tool-name."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        # Create temp input file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test input")
            temp_file = Path(f.name)

        try:
            result = process_input(temp_file)
            self.assertIsNotNone(result)
            # Add assertions
        finally:
            temp_file.unlink()

    def test_error_handling(self):
        """Test error handling."""
        # Test with invalid input
        pass


if __name__ == '__main__':
    unittest.main()
```

## Tools Usage

### scripts/skill-generator.py

```bash
# Generate complete skill structure
python scripts/skill-generator.py \
  --name "Test Reporter" \
  --description "Generate test reports with coverage and trends" \
  --domain "testing" \
  --tools "coverage-analyzer.py,report-generator.py" \
  --references "report-template.md,metrics-guide.md" \
  --trigger "QREPORT" \
  --output "skills/testing/test-reporter/SKILL.md"

# Output:
# Created: skills/testing/test-reporter/SKILL.md
# Created: skills/testing/test-reporter/scripts/ (directory)
# Created: skills/testing/test-reporter/references/ (directory)
# Next: Generate tool stubs with tool-stub-generator.py
```

### scripts/tool-stub-generator.py

```bash
# Generate Python tool stub
python scripts/tool-stub-generator.py \
  --name "coverage-analyzer" \
  --description "Analyze test coverage from coverage reports" \
  --input "coverage-report.json" \
  --output-format "json" \
  --skill-dir "skills/testing/test-reporter"

# Generate with test file
python scripts/tool-stub-generator.py \
  --name "report-generator" \
  --description "Generate HTML test report" \
  --input "test-results.json" \
  --output-format "html" \
  --skill-dir "skills/testing/test-reporter" \
  --generate-test

# Output:
# Created: skills/testing/test-reporter/scripts/coverage-analyzer.py
# Created: skills/testing/test-reporter/scripts/report-generator.py
# Created: skills/testing/test-reporter/tests/test_report_generator.py
```

## Agents

### skill-architect Agent

**Role**: High-level skill design and architecture

**Usage**:
```
@skill-architect Design a skill for automated code review with quality scoring
```

**Capabilities**:
- Requirements elicitation
- Tool identification
- Reference selection
- Workflow design
- Integration planning

**Prompt Template**:
```
You are the skill-architect agent. Design a new skill based on these requirements:

{requirements}

Provide:
1. Skill name and description
2. List of tools needed with purposes
3. References to include
4. Workflow phases
5. Usage examples
6. Integration points with existing skills

Output structured design document.
```

## Skill Patterns

### Pattern 1: Data Processing Skill

**Structure**:
- Input: Data file (JSON, CSV, etc.)
- Tools: Parser, analyzer, transformer, reporter
- Output: Processed data or report

**Example**: Test coverage analysis, log analysis, metrics aggregation

---

### Pattern 2: Content Generation Skill

**Structure**:
- Input: Template + data
- Tools: Template renderer, formatter, validator
- Output: Generated content

**Example**: Documentation generation, report creation, code scaffolding

---

### Pattern 3: Integration Skill

**Structure**:
- Input: Configuration + request
- Tools: API client, auth handler, data mapper
- Output: Integration result

**Example**: Google Docs publisher, Slack notifier, GitHub PR creator

---

### Pattern 4: Analysis Skill

**Structure**:
- Input: Codebase or documents
- Tools: Scanner, analyzer, scorer, reporter
- Output: Analysis report

**Example**: Code quality auditor, security scanner, complexity analyzer

---

### Pattern 5: Orchestration Skill

**Structure**:
- Input: Task description
- Agents: Multiple specialized agents
- Output: Coordinated result

**Example**: QRALPH multi-agent swarm, content workflow coordinator

## Usage Examples

### Example 1: Create Test Reporter Skill

```bash
# Step 1: Design skill
@skill-architect Design skill for generating test reports with coverage

# Step 2: Generate SKILL.md
python scripts/skill-generator.py \
  --name "Test Reporter" \
  --description "Generate test reports with coverage and trends" \
  --domain "testing" \
  --tools "coverage-analyzer.py,trend-analyzer.py,report-generator.py" \
  --references "report-template.md,metrics-guide.md" \
  --trigger "QREPORT" \
  --output "skills/testing/test-reporter/SKILL.md"

# Step 3: Generate tool stubs
python scripts/tool-stub-generator.py \
  --name "coverage-analyzer" \
  --description "Analyze test coverage" \
  --input "coverage.json" \
  --skill-dir "skills/testing/test-reporter"

python scripts/tool-stub-generator.py \
  --name "trend-analyzer" \
  --description "Analyze coverage trends" \
  --input "historical-coverage.json" \
  --skill-dir "skills/testing/test-reporter"

python scripts/tool-stub-generator.py \
  --name "report-generator" \
  --description "Generate HTML report" \
  --input "analysis-result.json" \
  --output-format "html" \
  --skill-dir "skills/testing/test-reporter" \
  --generate-test

# Step 4: Create references
# Manually create report-template.md and metrics-guide.md

# Step 5: Implement tools
# Add logic to tool stubs

# Step 6: Test
python skills/testing/test-reporter/tests/test_report_generator.py
```

---

### Example 2: Create API Integration Skill

```bash
# Design
@skill-architect Design skill for integrating with Notion API

# Generate
python scripts/skill-generator.py \
  --name "Notion Integration" \
  --description "Publish content to Notion databases and pages" \
  --domain "integrations" \
  --tools "notion-client.py,page-creator.py,database-updater.py" \
  --references "notion-api-guide.md,auth-setup.md" \
  --trigger "QNOTION" \
  --output "skills/integrations/notion/SKILL.md"

# Generate tools
for tool in notion-client page-creator database-updater; do
  python scripts/tool-stub-generator.py \
    --name "$tool" \
    --skill-dir "skills/integrations/notion" \
    --generate-test
done

# Implement and test
```

## Configuration

### .claude/skill-builder-config.json

```json
{
  "defaults": {
    "version": "1.0.0",
    "claude_tools": ["Read", "Grep", "Glob", "Edit", "Write", "Bash"],
    "python_version": "3.8+"
  },
  "templates": {
    "skill_template": "references/skill-template.md",
    "tool_template": "references/tool-patterns.md",
    "test_template": "references/test-template.py"
  },
  "directories": {
    "skills_root": "skills/",
    "tools_subdir": "scripts/",
    "references_subdir": "references/",
    "tests_subdir": "tests/"
  },
  "generation": {
    "auto_create_directories": true,
    "generate_readme": true,
    "include_examples": true
  }
}
```

## Story Point Estimation

Skill building estimates:
- **Design skill** (requirements + architecture): 0.3 SP
- **Generate SKILL.md**: 0.1 SP
- **Create tool stubs** (per tool): 0.05 SP
- **Implement tool** (per tool): 0.2-1 SP depending on complexity
- **Create references** (per reference): 0.1 SP
- **Write tests** (per tool): 0.1 SP

**Full skill creation**: 1-3 SP depending on complexity

## Best Practices

1. **Start with Design**: Use skill-architect to design before generating
2. **Follow Patterns**: Use existing skills as examples
3. **Include Examples**: Add concrete usage examples
4. **Write Tests**: Generate test stubs and implement tests
5. **Document Tools**: Clear docstrings and usage examples
6. **Reference Standards**: Follow skill template structure
7. **Version Control**: Commit skill incrementally as you build

## References

### references/skill-template.md

Complete template for SKILL.md with all sections and formatting.

### references/agent-patterns.md

Common agent patterns and persona examples.

### references/tool-patterns.md

Python tool patterns for different use cases (parsers, analyzers, generators, etc.).

## Output Schema

### Skill Generation Result

```json
{
  "skill_created": {
    "name": "Test Reporter",
    "location": "skills/testing/test-reporter/",
    "files": [
      "SKILL.md",
      "scripts/coverage-analyzer.py",
      "scripts/report-generator.py",
      "references/report-template.md",
      "tests/test_report_generator.py"
    ]
  },
  "next_steps": [
    "Implement tool logic in scripts/",
    "Populate reference documentation",
    "Run tests to verify functionality",
    "Add usage examples to SKILL.md"
  ]
}
```
