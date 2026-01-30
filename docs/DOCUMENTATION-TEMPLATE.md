# Documentation Template for Sparkry Claude Skills

This template standardizes documentation across all plugins in the marketplace.

---

## Document Types

### 1. Plugin User Guide (`docs/*-GUIDE.md`)

Primary user-facing documentation. Use this template:

```markdown
# [Plugin Name] - [One-Line Description]

## Overview

[2-3 sentences describing what this plugin does and who it's for.]

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

\```
/plugin marketplace add sparkst/sparkry-claude-skills
\```

### Step 2: Install [Plugin Name]

\```
/plugin install [plugin-id]@sparkry-claude-skills
\```

### Step 3: Verify Installation

\```
/plugin list
\```

------------------------------------------------------------------------

## Included Components

### Agents
| Agent | Role |
|-------|------|
| **[agent-name]** | [brief description] |

### Skills
| Skill | Purpose |
|-------|---------|
| **[skill-name]** | [brief description] |

------------------------------------------------------------------------

## Usage

### [Primary Use Case 1]

\```
[command example]
\```

**What it does:**
- [bullet 1]
- [bullet 2]

**Output:**
[description or code block]

------------------------------------------------------------------------

## [Workflow/Framework Section - if applicable]

[Describe the typical workflow or framework used by this plugin]

------------------------------------------------------------------------

## Related Plugins

- **[plugin-name]** - [brief description]

------------------------------------------------------------------------

## Troubleshooting

### [Common Issue 1]

[Solution]

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
```

---

### 2. Plugin README (`plugins/*/README.md`)

Brief technical reference. Keep under 100 lines. Use this template:

```markdown
# [Plugin Name]

[One-line description]

## Installation

\```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install [plugin-id]@sparkry-claude-skills
\```

## What's Included

**Agents:** [list]
**Skills:** [list]

## Quick Reference

| Component | Purpose |
|-----------|---------|
| [name] | [brief purpose] |

## Documentation

**[Full User Guide →](../../docs/[PLUGIN]-GUIDE.md)**

## License

MIT
```

---

### 3. Root README.md

Marketplace overview with:
- Quick start (3 steps)
- Plugin directory table with install commands
- Brief descriptions (2-3 sentences per plugin)
- Featured plugin highlight
- Troubleshooting section
- Support links

---

## Formatting Standards

### Horizontal Rules

Use 72 dashes for section breaks:
```
------------------------------------------------------------------------
```

### Tables

Always include header separators:
```
| Column 1 | Column 2 |
|----------|----------|
| data | data |
```

### Code Blocks

- Use triple backticks with language hints
- Use `bash` for shell commands
- Omit language for generic commands

### Headings

- H1: Document title only
- H2: Major sections
- H3: Subsections
- H4: Details (rare)

### Links

- Use relative paths within the repo
- Format: `[Link Text](./path/to/file.md)`

---

## Content Guidelines

### Do

- Be concise - users want to get started quickly
- Use tables for comparing options
- Include real examples with actual commands
- Show expected output when helpful
- Link to related plugins

### Don't

- Repeat installation steps in detail (link to guide)
- Include verbose technical specs in user guides
- Use different formatting across documents
- Create separate docs for things that can be a table

---

## File Naming

| Type | Pattern | Example |
|------|---------|---------|
| User Guide | `[PLUGIN-ID]-GUIDE.md` | `QSHORTCUTS-CORE-GUIDE.md` |
| Plugin README | `README.md` | `plugins/qshortcuts-core/README.md` |
| Template | `*-TEMPLATE.md` | `DOCUMENTATION-TEMPLATE.md` |

---

## Checklist for New Plugins

- [ ] Create `docs/[PLUGIN]-GUIDE.md` using User Guide template
- [ ] Create brief `plugins/[plugin]/README.md` linking to guide
- [ ] Add entry to root `README.md` plugin table
- [ ] Verify all links work
- [ ] Test install command

---

**Last Updated:** 2026-01-29
