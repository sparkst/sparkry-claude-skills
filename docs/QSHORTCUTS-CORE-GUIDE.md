# QShortcuts Core - TDD Development Shortcuts

## Overview

QShortcuts Core provides the essential TDD (Test-Driven Development) workflow shortcuts: QNEW, QPLAN, QCODET, QCODE, QCHECK, QCHECKF, and QCHECKT. These shortcuts guide you through planning, testing, and implementing features with best practices built in.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install QShortcuts Core

```
/plugin install qshortcuts-core@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Available Shortcuts

| Shortcut | Purpose | When to Use |
|----------|---------|-------------|
| **QNEW** | Start new feature | Beginning a new feature from scratch |
| **QPLAN** | Create implementation plan | Planning how to build something |
| **QCODET** | Write failing tests | TDD red phase - tests before code |
| **QCODE** | Implement functionality | TDD green phase - make tests pass |
| **QCHECK** | Full quality review | Complete code review before merge |
| **QCHECKF** | Fast quality check | Quick sanity check |
| **QCHECKT** | Test-only check | Verify tests pass |

------------------------------------------------------------------------

## Usage Examples

### QNEW - Start a New Feature

```
QNEW Add user authentication with OAuth2
```

**What it does:**
- Creates requirements document
- Generates requirements.lock.md snapshot
- Sets up initial plan structure
- Identifies acceptance criteria

**Output:** `requirements/current.md`, `requirements/requirements.lock.md`

------------------------------------------------------------------------

### QPLAN - Create Implementation Plan

```
QPLAN Refactor the payment processing module
```

**What it does:**
- Analyzes existing codebase for patterns
- Identifies reusable components
- Creates task breakdown with story points
- Defines interface contracts
- Documents dependencies and risks

**Output:** `plan.md` with SP estimates and task sequence

------------------------------------------------------------------------

### QCODET - Write Failing Tests (TDD Red Phase)

```
QCODET
```

**What it does:**
- Reads requirements from `requirements/requirements.lock.md`
- Generates test cases for each requirement
- Creates test files with REQ-ID citations
- Tests should FAIL initially (red phase)

**Output:** `*.spec.ts` files with failing tests

------------------------------------------------------------------------

### QCODE - Implement Functionality (TDD Green Phase)

```
QCODE
```

**What it does:**
- Reads the plan and failing tests
- Implements minimal code to pass tests
- Follows existing codebase patterns
- Validates against requirements

**Output:** Implementation files that make tests pass

------------------------------------------------------------------------

### QCHECK - Full Quality Review

```
QCHECK
```

**What it does:**
- Runs all quality checks (lint, typecheck, tests)
- Reviews code against requirements
- Checks for security issues
- Validates architecture patterns
- Ensures documentation is updated

**Output:** Quality report with P0/P1/P2 issues

------------------------------------------------------------------------

### QCHECKF - Fast Quality Check

```
QCHECKF
```

**What it does:**
- Quick subset of QCHECK
- Runs lint and typecheck
- Verifies tests pass
- Skips deep analysis

**Output:** Pass/fail status with basic issues

------------------------------------------------------------------------

### QCHECKT - Test-Only Check

```
QCHECKT
```

**What it does:**
- Runs test suite only
- Reports coverage
- Identifies failing tests

**Output:** Test results and coverage report

------------------------------------------------------------------------

## TDD Workflow

The recommended flow:

```
1. QNEW/QPLAN  →  Define what to build
2. QCODET      →  Write failing tests (RED)
3. QCODE       →  Implement to pass (GREEN)
4. QCHECK      →  Review and refactor
5. QGIT        →  Commit (from qshortcuts-support)
```

------------------------------------------------------------------------

## Story Point Reference

All shortcuts use this baseline:

| SP | Meaning |
|----|---------|
| 1 | Simple authenticated API (secured, tested, deployed, documented) |
| 2-3 | Small feature |
| 5-8 | Medium feature |
| 13+ | Large feature (should break down) |

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-support** - QDOC, QGIT for documentation and commits
- **dev-workflow** - Full agent suite for development

------------------------------------------------------------------------

## Troubleshooting

### "No requirements found"

Run `QNEW` or `QPLAN` first to create requirements.

### Tests not generating

Ensure `requirements/requirements.lock.md` exists and has REQ-IDs.

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
