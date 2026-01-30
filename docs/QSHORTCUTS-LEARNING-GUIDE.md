# QShortcuts Learning - Meta-Learning Shortcuts

## Overview

QShortcuts Learning provides meta-learning and improvement shortcuts: QFEEDBACK for extracting user feedback, QLEARN for retrieving relevant learnings, QCOMPACT for consolidating knowledge, and QSKILL for creating new skills.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install QShortcuts Learning

```
/plugin install qshortcuts-learning@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Available Shortcuts

| Shortcut | Purpose | When to Use |
|----------|---------|-------------|
| **QFEEDBACK** | Extract user feedback | After receiving feedback documents |
| **QLEARN** | Retrieve learnings | Before starting related tasks |
| **QCOMPACT** | Consolidate learnings | When learning files get large |
| **QSKILL** | Create new skill | Building new agent+skill complex |

------------------------------------------------------------------------

## Usage Examples

### QFEEDBACK - Extract User Feedback

```
QFEEDBACK Analyze feedback from docs/client-review.md
```

**What it does:**
- Reads feedback documents
- Categorizes insights (praise, criticism, suggestions)
- Extracts actionable items
- Integrates into learnings system
- Tracks feedback sources

**Output:**
- Categorized feedback summary
- Action items with priorities
- Updated learnings file

------------------------------------------------------------------------

### QLEARN - Retrieve Relevant Learnings

```
QLEARN
```

**What it does:**
- Analyzes current task context
- Searches learnings database
- Retrieves relevant past learnings
- Presents applicable insights
- Suggests patterns to follow

**Output:** Relevant learnings for current task

**Use before:**
- Starting similar tasks
- Making architecture decisions
- Repeating past work

------------------------------------------------------------------------

### QCOMPACT - Consolidate Learnings

```
QCOMPACT
```

**What it does:**
- Reviews learnings files for size
- Identifies redundant entries
- Merges similar learnings
- Archives old entries
- Maintains performance

**Triggers automatically when:**
- Learnings file exceeds size threshold
- Manual request

**Output:** Compacted learnings with summary of changes

------------------------------------------------------------------------

### QSKILL - Create New Skill

```
QSKILL Create a skill for API testing automation
```

**What it does:**
- Analyzes requirements
- Generates skill structure:
  - SKILL.md definition
  - Python tools
  - Reference materials
  - Test files
- Creates associated agent if needed
- Validates against skill schema

**Output:**
```
.claude/skills/<skill-name>/
├── SKILL.md           # Skill definition
├── tools/             # Python scripts
│   └── main-tool.py
├── references/        # Templates, examples
└── tests/             # Tool tests
```

------------------------------------------------------------------------

## Learning System Architecture

```
User Feedback → QFEEDBACK → Learnings DB
                                ↓
Current Task → QLEARN → Relevant Insights
                                ↓
                         Better Outcomes
                                ↓
                    QCOMPACT (maintenance)
```

------------------------------------------------------------------------

## Learnings File Format

Learnings are stored in structured format:

```yaml
learning:
  id: L-001
  date: 2026-01-29
  category: architecture
  context: "When designing RAG systems..."
  insight: "Always include a reranking step..."
  source: project-001
  confidence: high
```

------------------------------------------------------------------------

## Creating New Skills

QSKILL follows this structure:

### SKILL.md Template
```yaml
---
name: skill-name
version: 1.0.0
description: What this skill does
trigger: SHORTCUT_NAME
dependencies:
  agents: [agent-name]
tools: [tool-a.py, tool-b.py]
---

# Skill Name

## Role
What this skill does...

## Workflow
Step-by-step execution...

## Tools Usage
How to use each tool...
```

------------------------------------------------------------------------

## Workflow Integration

### Continuous Improvement Loop
```
1. Do work
2. Receive feedback
3. QFEEDBACK  →  Extract insights
4. Next task
5. QLEARN     →  Apply learnings
6. QCOMPACT   →  Maintain system (periodic)
```

### Creating Custom Workflows
```
1. QIDEA     →  Research approach
2. QSKILL    →  Create skill structure
3. QCODE     →  Implement tools
4. QCHECK    →  Validate skill
5. QDOC      →  Document skill
```

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-core** - Core TDD shortcuts
- **orchestration-workflow** - QRALPH for multi-agent tasks

------------------------------------------------------------------------

## Troubleshooting

### QLEARN returns nothing

- Check that learnings file exists
- Verify learnings are tagged with relevant categories
- Run QFEEDBACK to add more learnings

### QSKILL validation errors

Ensure skill definition includes:
- name, version, description in frontmatter
- trigger keyword
- At least one tool or agent dependency

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
