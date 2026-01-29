# qshortcuts-support Plugin Manifest

Development support skills for QShortcuts workflow.

## Plugin Metadata

- **Name**: qshortcuts-support
- **Version**: 1.0.0
- **Author**: Travis Kaufman <travis@sparkry.ai>
- **License**: MIT
- **Category**: Development
- **Created**: 2026-01-28

## Skills Included

### 1. QUX - UX Test Scenarios

**Location**: `skills/qux/`

**Purpose**: Generate comprehensive UX test scenarios for UI components

**Agents**: ux-tester

**Tools**: None (uses Claude tools: Read, Grep, Glob, Write)

**References**:
- `wcag-checklist.md` - WCAG 2.1 quick reference
- `aria-patterns.md` - Common ARIA patterns

**Trigger**: `QUX`

**Workflow**:
1. Analyze UI components
2. Generate test scenarios (happy path, edge cases, error states)
3. Check accessibility compliance (WCAG 2.1)
4. Document test matrix

**Output**: `docs/tasks/<task-id>/ux-test-scenarios.md`

---

### 2. QDOC - Progressive Documentation

**Location**: `skills/qdoc/`

**Purpose**: Generate and update documentation following Progressive Docs pattern

**Agents**: docs-writer

**Tools**: None (uses Claude tools: Read, Grep, Glob, Edit, Write, Bash)

**References**:
- `progressive-docs-templates.md` - Templates for all doc types

**Trigger**: `QDOC`

**Workflow**:
1. Analyze changes (git diff)
2. Generate/update documentation (root README, domain READMEs, .claude-context)
3. Update CHANGELOG with version entry
4. Verify documentation quality

**Output**: Updated READMEs, CHANGELOG.md

---

### 3. QIDEA - Research and Ideation

**Location**: `skills/qidea/`

**Purpose**: Research topics, generate options matrix, provide recommendations (no code)

**Agents**: general-purpose (Explore mode)

**Tools**: None (uses Claude tools: Read, Grep, Glob, Write, Bash)

**References**:
- `research-methodology.md` - Research planning and execution guide
- `options-matrix-template.md` - Template for options comparison

**Trigger**: `QIDEA <topic>`

**Workflow**:
1. Plan research (sub-questions, queries)
2. Gather information (web search)
3. Synthesize findings
4. Generate options matrix
5. Provide recommendation

**Output**: `research/<topic-slug>/analysis.md`

---

### 4. QGIT - Git Release Management

**Location**: `skills/qgit/`

**Purpose**: Run quality gates, stage changes, commit (Conventional Commits), push

**Agents**: release-manager

**Tools**:
- `quality-gate-checker.py` - Python script to run quality gates and report results

**References**:
- `conventional-commits.md` - Conventional Commits specification
- `quality-gates.md` - Quality gate configuration and troubleshooting

**Trigger**: `QGIT`

**Workflow**:
1. Run quality gates (lint, typecheck, test)
2. Analyze changes (git status, git diff)
3. Generate Conventional Commit message
4. Stage and commit
5. Push to remote

**Output**: Git commit and push

---

## Agents Included

### 1. ux-tester

**Location**: `agents/ux-tester.md`

**Role**: Generate UX test scenarios and accessibility checks

**Expertise**: User experience, accessibility, edge case analysis, UI testing

**Tools**: Read, Grep, Glob, Write

---

### 2. docs-writer

**Location**: `agents/docs-writer.md`

**Role**: Progressive documentation writer

**Expertise**: Technical writing, documentation architecture, markdown

**Tools**: Read, Grep, Glob, Edit, Write

---

### 3. release-manager

**Location**: `agents/release-manager.md`

**Role**: Quality gate enforcement and git operations

**Expertise**: Release management, git workflows, Conventional Commits

**Tools**: Read, Grep, Glob, Edit, Write, Bash

---

## Directory Structure

```
qshortcuts-support/
├── plugin.json                 # Plugin metadata
├── README.md                   # Plugin documentation
├── MANIFEST.md                 # This file
├── .claude-plugin/             # Claude plugin marker
├── agents/                     # Agent definitions
│   ├── ux-tester.md
│   ├── docs-writer.md
│   └── release-manager.md
└── skills/                     # Skill bundles
    ├── qux/                    # UX test scenarios
    │   ├── SKILL.md
    │   ├── tools/
    │   └── references/
    │       ├── wcag-checklist.md
    │       └── aria-patterns.md
    ├── qdoc/                   # Documentation
    │   ├── SKILL.md
    │   ├── tools/
    │   └── references/
    │       └── progressive-docs-templates.md
    ├── qidea/                  # Research and ideation
    │   ├── SKILL.md
    │   ├── tools/
    │   └── references/
    │       ├── research-methodology.md
    │       └── options-matrix-template.md
    └── qgit/                   # Git release management
        ├── SKILL.md
        ├── tools/
        │   └── quality-gate-checker.py
        └── references/
            ├── conventional-commits.md
            └── quality-gates.md
```

---

## Installation

### Via Claude Code CLI

```bash
claude plugins install qshortcuts-support
```

### Manual Installation

```bash
cp -r qshortcuts-support ~/.claude/plugins/qshortcuts-support
```

---

## Usage

### QUX - Generate UX Test Scenarios

```bash
QUX [component-path]
```

**Example**:
```bash
QUX src/components/LoginForm.tsx
```

**Output**: Test scenarios with accessibility checks

---

### QDOC - Update Documentation

```bash
QDOC [--depth=root|domain|all] [--version=major|minor|patch]
```

**Example**:
```bash
QDOC --version=minor
```

**Output**: Updated READMEs and CHANGELOG

---

### QIDEA - Research Topic

```bash
QIDEA <research topic> [--depth=quick|medium|deep]
```

**Example**:
```bash
QIDEA OAuth providers comparison
```

**Output**: Research analysis with recommendations

---

### QGIT - Commit and Push

```bash
QGIT [--message="custom message"] [--dry-run]
```

**Example**:
```bash
QGIT
```

**Output**: Quality gate report, commit, and push

---

## Integration with Other QShortcuts

### Development Workflow

```
QCODE (implement)
  ↓
QUX (generate UX tests)
  ↓
QCODET (implement tests)
  ↓
QDOC (update docs)
  ↓
QGIT (commit and push)
```

### Research Workflow

```
QIDEA (research options)
  ↓
QPLAN (plan implementation)
  ↓
QCODE (implement)
  ↓
QGIT (commit)
```

---

## Dependencies

### Required

- Node.js 18+ (for npm scripts)
- Git (for QGIT)
- Python 3.8+ (for quality-gate-checker.py)

### Optional

- TypeScript (for typecheck gate)
- ESLint (for lint gate)
- Jest/Vitest (for test gate)

---

## Configuration Files

### .qgit.json

Optional configuration for QGIT quality gates:

```json
{
  "quality_gates": [
    {
      "name": "Lint",
      "command": "npm run lint",
      "required": true
    },
    {
      "name": "Typecheck",
      "command": "npm run typecheck",
      "required": true
    },
    {
      "name": "Test",
      "command": "npm run test",
      "required": true
    }
  ],
  "auto_stage": true,
  "auto_push": true,
  "exclude_patterns": [".env", "*.key", "credentials.json"]
}
```

### .qux.json

Optional configuration for QUX:

```json
{
  "wcag_level": "AA",
  "browsers": ["chrome", "safari", "firefox"],
  "devices": ["desktop", "mobile"],
  "assistive_tech": ["keyboard", "nvda", "voiceover"],
  "output_dir": "docs/ux-scenarios"
}
```

### .qdoc.json

Optional configuration for QDOC:

```json
{
  "depth": "all",
  "changelog_format": "keepachangelog",
  "include_req_ids": true,
  "max_root_readme_words": 200,
  "max_domain_readme_words": 500
}
```

### .qidea.json

Optional configuration for QIDEA:

```json
{
  "depth": "medium",
  "max_duration_minutes": 40,
  "output_dir": "research",
  "options_matrix": true,
  "recommendation_required": true
}
```

---

## Story Point Estimates

| Skill | Typical Effort | Notes |
|-------|----------------|-------|
| QUX | 0.2-0.5 SP | Depends on UI complexity |
| QDOC | 0.1-0.3 SP | Incremental doc updates |
| QIDEA | 0.5-2 SP | Varies with research depth |
| QGIT | 0.05-0.1 SP | Automated, gates must pass |

---

## Troubleshooting

### QUX: No UI Components Found

**Solution**: Specify component path explicitly
```bash
QUX src/components/MyComponent.tsx
```

---

### QDOC: Documentation Out of Sync

**Solution**: Run QDOC after every feature
```bash
QDOC
```

---

### QIDEA: Research Too Broad

**Solution**: Narrow the query
```bash
QIDEA OAuth vs JWT for API authentication
```

---

### QGIT: Quality Gates Failing

**Solution**: Fix issues before committing
```bash
npm run lint:fix
npm run test
QGIT
```

---

## Contributing

For issues or enhancements:
- **Email**: skills@sparkry.ai
- **License**: MIT

---

## Changelog

### v1.0.0 (2026-01-28)

- Initial release
- 4 core skills (QUX, QDOC, QIDEA, QGIT)
- 3 agents (ux-tester, docs-writer, release-manager)
- Quality gate integration
- Progressive documentation support
- Conventional Commits enforcement
- UX testing with accessibility checks
- Research and ideation framework

---

## License

MIT License - Copyright (c) 2026 Travis Kaufman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
