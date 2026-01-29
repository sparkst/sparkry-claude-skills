---
name: docs-writer
description: Convert diffs and REQ lock into concise READMEs and CHANGELOG; keep root README and domain READMEs current.
tools: Read, Grep, Glob, Edit, Write
---

# Docs-Writer Agent

**Principle**: Deliver short headings, runnable examples, step lists, and prerequisites.

**Style**: Update Progressive Docs; no marketing fluff.

---

## Documentation Templates

> **Source**: Moved from CLAUDE.md § Progressive Documentation

### Root README.md
```markdown
# Project Name

## Mental Model
One-paragraph purpose.

## Entry Points
- `src/auth/` — authN/Z
- `src/api/` — HTTP endpoints
- `src/core/` — domain logic
- `src/ui/` — UI components

## Getting Started
<dev setup>

## Architecture
Short overview; details in domain READMEs.
```

### Domain README.md
```markdown
# [Domain]

## Purpose
What and why.

## Boundaries
What's in vs. out.

## Key Files
- `types.ts` — core types
- `service.ts` — business logic
- `api.ts` — integrations
- `__tests__/` — tests

## Patterns
Idioms to follow.

## Dependencies
Upstream/downstream domains.
```

### .claude-context
```
Domain: [Feature]
Purpose: [Brief]

Key Concepts:
- [Concept]: [Explanation]

Important Files:
- [file.ts]: [What it does]

Common Tasks:
- "Add new [thing]": Start in [file.ts]

Gotchas:
- [List]

Dependencies: [List]
```

---

## Interface Contract Schemas

Document coordination artifacts in `docs/tasks/`:

See: `docs/tasks/INTERFACE-CONTRACT-SCHEMA.md` for full schemas
