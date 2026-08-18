# QShortcuts Content

Content creation shortcuts for writing, presentations, and visuals.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install qshortcuts-content@sparkry-claude-skills
```

## What's Included

**Skills:** QWRITE, QPPT, QVISUAL, QINFOGRAPHIC

## Quick Reference

| Shortcut | Purpose |
|----------|---------|
| QWRITE | Multi-platform content with quality scoring (defers to an installed global `writing` skill v1.5.0+ when present; see skills/qwrite/SKILL.md "Lineage / routing") |
| QPPT | LinkedIn carousel generator |
| QVISUAL | Hero images and diagram generator |
| QINFOGRAPHIC | Framework-to-infographic pipeline |

## Usage

```bash
QWRITE: Substack article on AI tools, 1500 words
QPPT: Generate carousel from post.md
QVISUAL: Generate hero image for article.md
QINFOGRAPHIC: Create from https://substack.com/article
```

## Documentation

**[Full User Guide →](../../docs/QSHORTCUTS-CONTENT-GUIDE.md)**

## Changelog

- 1.1.0 (2026-08-18): QWRITE routes to the installed global `writing` skill when present (single lineage); generic pipeline unchanged as fallback.
- 1.0.0: initial release.

## License

MIT
