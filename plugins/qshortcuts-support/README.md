# qshortcuts-support Plugin

Development support skills for QShortcuts workflow in Claude Code.

## What's Included

### Skills

- **QUX** (`skills/qux/`) - Generate UX test scenarios with accessibility checks
- **QDOC** (`skills/qdoc/`) - Document per Progressive Docs pattern
- **QIDEA** (`skills/qidea/`) - Research and ideation, no code
- **QGIT** (`skills/qgit/`) - Stage, commit (Conventional Commits), push with quality gates

### Agents

- **ux-tester** - Generates UX test scenarios and accessibility checks
- **docs-writer** - Progressive documentation writer
- **release-manager** - Quality gate enforcement and git operations

## Installation

### Via Claude Code CLI

```bash
claude plugins install qshortcuts-support
```

### Manual Installation

1. Clone or download this plugin
2. Copy to your Claude plugins directory:
   ```bash
   cp -r qshortcuts-support ~/.claude/plugins/qshortcuts-support
   ```
3. Reload Claude Code

## Quick Start

### QUX - UX Test Scenarios

Generate comprehensive UX test scenarios for UI components:

```
QUX
```

The skill will:
- Analyze UI components in the codebase
- Generate test scenarios (happy path, edge cases, error states)
- Check accessibility compliance
- Identify edge cases and boundary conditions

**Output**: `docs/tasks/<task-id>/ux-test-scenarios.md`

### QDOC - Progressive Documentation

Update documentation following Progressive Docs pattern:

```
QDOC
```

The skill will:
- Analyze recent code changes
- Generate/update READMEs
- Follow progressive disclosure (root → domain → component)
- Update CHANGELOG

**Output**: Updated READMEs and CHANGELOG

### QIDEA - Research and Ideation

Research topics without writing code:

```
QIDEA <research topic>
```

The skill will:
- Research the query across multiple sources
- Synthesize findings
- Generate options matrix
- Provide recommendations

**Output**: `research/<topic>/analysis.md`

### QGIT - Git Release Management

Stage, commit, and push with quality gates:

```
QGIT
```

The skill will:
- Run quality gates (lint, typecheck, test)
- Stage changes
- Generate Conventional Commit message
- Commit and push

**Blockers**: Any test failure, type error, or linting issue

## Workflow Integration

### Documentation Flow

```
QCODE (implement feature)
  ↓
QDOC (update docs)
  ↓
QGIT (commit and push)
```

### Research Flow

```
QIDEA (research topic)
  ↓
QPLAN (plan implementation)
  ↓
QCODE (implement)
```

### UX Testing Flow

```
QCODE (implement UI)
  ↓
QUX (generate test scenarios)
  ↓
QCODET (implement tests)
  ↓
QGIT (commit)
```

## Configuration

### Quality Gates (QGIT)

The following gates must pass before commit:

```bash
npm run lint           # ESLint
npm run typecheck      # TypeScript
npm run test           # All tests
```

For edge functions:
```bash
# Verify dependency versions
grep -r "@supabase/supabase-js@" supabase/functions/*/index.ts | sort -u
# Must show ONLY: @supabase/supabase-js@2.50.2
```

### Progressive Docs Pattern (QDOC)

Documentation follows a three-tier structure:

1. **Root README.md** - Mental model, entry points, getting started
2. **Domain README.md** - Purpose, boundaries, key files, patterns
3. **Component .claude-context** - Domain-specific context

See skill documentation for templates.

## Best Practices

### 1. Always Run Quality Gates Before Push

**❌ Don't**:
```bash
git add . && git commit -m "Quick fix" && git push  # Skip gates
```

**✅ Do**:
```bash
QGIT  # Runs all gates automatically
```

### 2. Document As You Go

**❌ Don't**:
```bash
# Implement feature, ship it, forget docs
```

**✅ Do**:
```bash
QCODE    # Implement
QDOC     # Document
QGIT     # Commit
```

### 3. Research Before Building

**❌ Don't**:
```bash
QCODE implement OAuth without researching providers
```

**✅ Do**:
```bash
QIDEA OAuth providers comparison
QPLAN implement OAuth with <chosen provider>
QCODE
```

### 4. Generate UX Tests for UI Changes

**❌ Don't**:
```bash
# Build UI, ship without UX testing
```

**✅ Do**:
```bash
QCODE implement login form
QUX
QCODET implement UX test scenarios
```

## Troubleshooting

### QGIT: Quality Gates Failing

**Problem**: `npm run test` fails

**Solution**: Fix failing tests before proceeding
```bash
npm run test  # See specific failures
# Fix issues
npm run test  # Verify green
QGIT          # Retry commit
```

### QDOC: Documentation Out of Sync

**Problem**: READMEs don't reflect recent changes

**Solution**: Run QDOC explicitly
```bash
QDOC  # Analyzes git diff and updates docs
```

### QUX: No UI Components Found

**Problem**: QUX reports "no UI components found"

**Solution**: Specify component path
```bash
QUX src/components/LoginForm.tsx
```

### QIDEA: Research Too Broad

**Problem**: QIDEA takes too long or returns unfocused results

**Solution**: Narrow the research query
```bash
# Instead of: QIDEA AI tools
# Use: QIDEA AI coding assistants pricing models comparison
```

## Advanced Usage

### Custom Commit Messages (QGIT)

QGIT generates Conventional Commit messages automatically. To customize:

1. Review proposed commit message
2. Edit if needed
3. Proceed with commit

**Conventional Commit Format**:
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### Parallel Research (QIDEA)

For multi-faceted research, use multiple QIDEA calls:

```bash
QIDEA market sizing for AI coding tools
QIDEA competitive landscape AI pair programming
QIDEA pricing models SaaS dev tools
```

Then synthesize findings manually or with QWRITE.

### Progressive Docs Depth (QDOC)

Control documentation depth:

```bash
QDOC --depth=root        # Update root README only
QDOC --depth=domain      # Update domain READMEs
QDOC --depth=component   # Update component .claude-context files
QDOC                     # Update all levels (default)
```

## Story Point Estimates

| Skill | Typical Effort | Notes |
|-------|----------------|-------|
| QUX | 0.2-0.5 SP | Depends on UI complexity |
| QDOC | 0.1-0.3 SP | Incremental doc updates |
| QIDEA | 0.5-2 SP | Varies with research depth |
| QGIT | 0.05-0.1 SP | Automated, gates must pass |

## Contributing

This plugin is part of the Sparkry.ai Claude Code ecosystem. For issues, enhancements, or questions:

- **Email**: skills@sparkry.ai
- **License**: MIT

## Changelog

### v1.0.0 (2026-01-28)

- Initial release
- 4 core skills (QUX, QDOC, QIDEA, QGIT)
- 3 agents (ux-tester, docs-writer, release-manager)
- Quality gate integration
- Progressive documentation support
- Conventional Commits enforcement

## License

MIT License - see LICENSE file for details.

---

**Happy shipping with quality and documentation!**
