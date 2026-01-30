# Starter Pack

Essential agents for getting started with Claude Code plugins.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install starter-pack@sparkry-claude-skills
```

## What's Included

**Agents:** planner, sde-iii, pe-reviewer

## Quick Reference

| Agent | Purpose |
|-------|---------|
| planner | Task breakdown, requirements, SP estimates |
| sde-iii | Implementation, complexity analysis |
| pe-reviewer | Code quality, security review |

## Basic Workflow

```
@planner → Implement → @pe-reviewer → Iterate
```

## Usage

```bash
@planner Help me plan a user authentication feature
@sde-iii Analyze complexity of adding notifications
@pe-reviewer Review my authentication implementation
```

## Ready for More?

After mastering Starter Pack, upgrade to full workflows:

```bash
/plugin install dev-workflow@sparkry-claude-skills     # TDD workflow
/plugin install qshortcuts-core@sparkry-claude-skills  # QNEW, QPLAN, QCODE, etc.
```

## Documentation

**[Full User Guide →](../../docs/STARTER-PACK-GUIDE.md)**

## License

MIT
