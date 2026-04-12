# coe-workflow

Structured COE (Correction of Errors) workflow with 5-Whys root cause analysis.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install coe-workflow@sparkry-claude-skills
```

## What's Included

**Skills:** QCOE

## Quick Reference

| Shortcut | Purpose |
|----------|---------|
| QCOE | Run a full COE — from incident description to publishable document |

## Usage

```
/qcoe "description of what went wrong"
/qcoe agent:agent-name run:run-id
/qcoe
/qcoe --resume docs/coe/2026-04-11-draft.md
```

## Documentation

**[Full User Guide →](../../docs/COE-WORKFLOW-GUIDE.md)**

## License

MIT
