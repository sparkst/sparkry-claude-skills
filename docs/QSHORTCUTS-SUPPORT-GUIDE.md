# QShortcuts Support - Development Support Shortcuts

## Overview

QShortcuts Support provides development support shortcuts: QUX for UX testing, QDOC for documentation, QIDEA for research/ideation, and QGIT for git operations with conventional commits.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install QShortcuts Support

```
/plugin install qshortcuts-support@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Available Shortcuts

| Shortcut | Purpose | When to Use |
|----------|---------|-------------|
| **QUX** | UX testing & accessibility | Before shipping UI changes |
| **QDOC** | Generate documentation | After implementing features |
| **QIDEA** | Research & ideation | Exploring ideas (no code) |
| **QGIT** | Git commit & push | Ready to commit changes |

------------------------------------------------------------------------

## Usage Examples

### QUX - UX Testing & Accessibility

```
QUX Review the checkout flow
```

**What it does:**
- Analyzes UI components for usability
- Checks accessibility (WCAG compliance)
- Identifies edge cases and empty states
- Reviews error handling UX
- Tests responsive behavior

**Output:** UX test scenarios with priority ranking

------------------------------------------------------------------------

### QDOC - Generate Documentation

```
QDOC
```

**What it does:**
- Reads recent changes (git diff)
- Updates README files
- Generates API documentation
- Updates CHANGELOG
- Ensures docs match implementation

**Output:** Updated documentation files

------------------------------------------------------------------------

### QIDEA - Research & Ideation

```
QIDEA How should we implement real-time notifications?
```

**What it does:**
- Researches approaches and patterns
- Compares options (WebSockets vs SSE vs polling)
- Identifies trade-offs
- Produces recommendation
- **Does NOT write code**

**Output:** Research document with options matrix

------------------------------------------------------------------------

### QGIT - Git Commit & Push

```
QGIT
```

**What it does:**
- Reviews staged changes
- Generates conventional commit message
- Follows repository commit style
- Creates commit with co-author
- Optionally pushes to remote

**Commit format:**
```
feat(auth): add OAuth2 login flow

- Implement Google OAuth provider
- Add session management
- Create login/logout endpoints

Co-Authored-By: Claude <noreply@anthropic.com>
```

------------------------------------------------------------------------

## Workflow Integration

These shortcuts complement the core TDD flow:

```
QPLAN → QCODET → QCODE → QCHECK → QDOC → QGIT
                                    ↑       ↑
                              Support shortcuts
```

### After Implementation
```
1. QCHECK   →  Verify quality
2. QUX      →  Test UX (if UI changes)
3. QDOC     →  Update documentation
4. QGIT     →  Commit changes
```

### For Research Tasks
```
1. QIDEA    →  Research without coding
2. QPLAN    →  Plan implementation (if proceeding)
```

------------------------------------------------------------------------

## Conventional Commit Types

QGIT uses these commit types:

| Type | Use For |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring |
| `test` | Adding tests |
| `chore` | Maintenance tasks |

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-core** - QNEW, QPLAN, QCODE, QCHECK for core TDD
- **qshortcuts-content** - QWRITE for content creation

------------------------------------------------------------------------

## Troubleshooting

### QGIT shows "nothing to commit"

Stage your changes first with `git add`.

### QDOC not finding changes

Ensure you have recent commits or staged changes to document.

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
