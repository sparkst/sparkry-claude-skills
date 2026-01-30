# Dev Workflow

TDD-first development agents for code quality, testing, and releases.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install dev-workflow@sparkry-claude-skills
```

## What's Included

**Agents:** pe-reviewer, test-writer, planner, release-manager, requirements-analyst, debugger, code-quality-auditor, sde-iii

**Skills:** quality/pe-reviewer

## Quick Reference

| Agent | Purpose |
|-------|---------|
| pe-reviewer | Code quality, security, architecture review |
| test-writer | TDD test generation, coverage analysis |
| planner | Task breakdown, SP estimation |
| release-manager | Versioning, changelogs, quality gates |
| requirements-analyst | REQ-IDs, acceptance criteria |
| debugger | Root cause analysis, minimal fixes |
| code-quality-auditor | Patterns, anti-patterns, tech debt |
| sde-iii | Complexity analysis, implementation |

## TDD Workflow

```
QPLAN → QCODET → QCODE → QCHECK → QGIT
```

## Usage

```bash
@planner Create plan for user authentication
@test-writer Generate tests for requirements.lock.md
@sde-iii Implement feature to pass tests
@pe-reviewer Review authentication implementation
@release-manager Prepare release with all tests passing
```

## Documentation

**[Full User Guide →](../../docs/DEV-WORKFLOW-GUIDE.md)**

## License

MIT
