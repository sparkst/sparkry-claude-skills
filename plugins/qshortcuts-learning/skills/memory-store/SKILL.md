# Memory Store - Cross-Project Learning

> SQLite + FTS5 memory store for learning from failures across QRALPH projects.

## Trigger

`QREMEMBER` shortcut or direct script invocation.

## Commands

| Command | Description |
|---------|-------------|
| `QREMEMBER "description"` | Store a memory (manual capture) |
| `QREMEMBER --failure "desc"` | Record a failed approach |
| `QREMEMBER --success "desc"` | Record a successful workaround |

## Tools

`.claude/skills/learning/memory-store/scripts/memory-store.py`
