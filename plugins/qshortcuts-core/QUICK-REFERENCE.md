# QShortcuts Core - Quick Reference Card

## TDD Workflow (Linear)

```
QNEW → QPLAN → QCODET → QCODE → QCHECK
```

## Skills at a Glance

| Skill | Purpose | Input | Output | Agents |
|-------|---------|-------|--------|--------|
| **QNEW** | Initialize feature | User request | requirements.lock.md | planner, docs-writer |
| **QPLAN** | Create plan | Requirements | Task breakdown + SP | planner, requirements-analyst |
| **QCODET** | Write tests | REQ-IDs | Failing tests (RED) | test-writer |
| **QCODE** | Implement | Failing tests | Passing tests (GREEN) | sde-iii, implementation-coordinator |
| **QCHECK** | Full review | Implementation | P0/P1/P2 findings | pe-reviewer, code-quality-auditor, security-reviewer |
| **QCHECKF** | Review functions | Functions | Quality issues | pe-reviewer, code-quality-auditor |
| **QCHECKT** | Review tests | Test suite | Coverage + quality | pe-reviewer, test-writer |

## When to Use What

| Situation | Use This |
|-----------|----------|
| Starting new feature | QNEW → QPLAN |
| Need detailed plan | QPLAN |
| Ready to write tests | QCODET |
| Tests are failing | QCODE |
| Pre-merge review | QCHECK |
| Quick function check | QCHECKF |
| Check test quality | QCHECKT |
| Small refactor | QCHECKF only |
| Adding edge case tests | QCODET → QCHECKT |

## Story Points

### Planning: Fibonacci
1, 2, 3, 5, 8, 13, 21... (break >13)

### Coding: Finer Scale
0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1, 2, 3, 5 (break >5)

### Baseline
**1 SP** = Simple authenticated API (secured, tested, deployed, documented)

## Quality Gates

All skills enforce:
- ✓ Prettier formatting
- ✓ TypeScript checking
- ✓ ESLint compliance
- ✓ Tests passing (except QCODET)

## Priority Levels

- **P0:** Blocking - fix before merge
- **P1:** Important - fix within 1 sprint
- **P2:** Nice-to-have - backlog

## Tools Quick Reference

| Tool | Command | Used By |
|------|---------|---------|
| planning-poker-calc.py | `--files-count 3 --complexity moderate` | QPLAN |
| interface-validator.py | `--interface-file x.ts --codebase-path ./src` | QPLAN |
| req-id-extractor.py | `--lock-file requirements.lock.md` | QCODET, QCHECKT |
| test-scaffolder.py | `--requirements x.json --implementation-file y.ts` | QCODET |
| coverage-analyzer.py | `--test-results coverage.json --threshold 80` | QCODET, QCHECKT |
| cyclomatic-complexity.py | `--file x.ts --threshold 10` | QCHECK, QCHECKF |
| dependency-risk.py | `--package-json package.json --check-vulnerabilities` | QCHECK, QCHECKF |
| supabase-rls-checker.py | `--schema-file schema.sql --check-tables users` | QCHECK |
| secret-scanner.py | `--path src/` | QCHECK |

## File Structure Convention

```
requirements/
  current.md              # Editable requirements
  requirements.lock.md    # Frozen snapshot

src/
  feature/
    service.ts           # Implementation
    service.spec.ts      # Co-located tests
    model.ts
    model.spec.ts
```

## Common Workflows

### Full Feature
```
QNEW → QPLAN → QCODET → QCODE → QCHECK
```

### Quick Fix
```
QCODET → QCODE → QCHECKF
```

### Test Addition
```
QCODET → QCHECKT
```

### Refactoring
```
QPLAN → QCODE → QCHECKF
```

## Best Practices Checklist

### Code
- [ ] Functions <50 lines
- [ ] Complexity <10
- [ ] Domain vocabulary
- [ ] Branded types for IDs
- [ ] No comments (code explains itself)

### Tests
- [ ] Co-located (*.spec.ts)
- [ ] Cite REQ-IDs
- [ ] Coverage ≥80%
- [ ] Arrange-Act-Assert
- [ ] Independent tests

### Requirements
- [ ] REQ-IDs assigned
- [ ] Acceptance criteria clear
- [ ] Edge cases documented
- [ ] Locked in requirements.lock.md

## Keyboard Shortcuts (Claude Code)

```bash
# Trigger skills
User: QNEW - [description]
User: QPLAN - [description]
User: QCODET - [description]
User: QCODE - [description]
User: QCHECK - [description]
User: QCHECKF - [description]
User: QCHECKT - [description]
```

## Example Commands

```bash
# Initialize
QNEW - Add user authentication

# Plan
QPLAN - Implement email verification

# Write tests
QCODET - Write tests for password reset

# Implement
QCODE - Implement password reset

# Review
QCHECK - Review authentication module

# Quick function review
QCHECKF - Review validatePassword function

# Test review
QCHECKT - Review auth test suite
```

## Installation

```bash
# Copy plugin
cp -r qshortcuts-core ~/.claude/plugins/

# Verify
cat ~/.claude/plugins/qshortcuts-core/.claude-plugin/plugin.json
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Tests won't pass | QCHECKT to analyze |
| Complexity too high | QCHECKF to identify |
| Coverage below 80% | coverage-analyzer.py |
| Security concerns | QCHECK (full review) |
| Slow iteration | Use QCHECKF instead of QCHECK |

## Support

- README.md - Full documentation
- SKILL.md files - Detailed workflows
- Tool --help - Command usage

---

**Version:** 1.0.0 | **Author:** Sparkry.ai | **License:** MIT
