# COE Workflow - Structured Root Cause Analysis

## Overview

COE Workflow provides a guided Correction of Errors process for any Claude Code project. It walks you through 5-Whys root cause analysis and produces a complete, publishable COE Markdown document. Unlike generic post-mortem templates, QCOE actively rejects behavioral fixes, detects repeat patterns, and enforces structural preventive mechanisms.

Works in any project, any language, any team size. No project-specific dependencies required.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install COE Workflow

```
/plugin install coe-workflow@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Included Components

### Skills

| Skill | Purpose |
|-------|---------|
| **QCOE** | Full COE workflow — incident intake through publishable document |

------------------------------------------------------------------------

## Usage

### Mode 1: Free-Form Description

Describe what went wrong in plain text. QCOE extracts structured facts and guides you through analysis.

```
/qcoe "Standing orders were all dispatched to one agent for 2 weeks"
```

**What it does:**
- Scans for related prior COEs before starting
- Extracts: what happened, when, who noticed, what broke, impact
- Shows time estimate upfront (~5 minutes)
- Guides through 5-Whys, root cause synthesis, corrective actions
- Produces a complete COE document

**Output:** `docs/coe/YYYY-MM-DD-title.md`

------------------------------------------------------------------------

### Mode 2: Agent Failure Reference

For projects with an `agents/` directory, reference a specific agent and run.

```
/qcoe agent:social-post-daily-draft run:abc123
```

**What it does:**
- Reads `agents/social-post-daily-draft/agent.json` for context
- Checks for error logs in data/ or logs/ directories
- Scopes git log to the agent's directory
- Constructs the incident summary from structured data (~3 minutes)

------------------------------------------------------------------------

### Mode 3: Interactive (Step-by-Step)

No arguments — QCOE prompts for each field.

```
/qcoe
```

**What it does:**
- Asks: What happened? When? Who noticed? What broke? What was the impact?
- Best for complex incidents where context needs careful capture (~10 minutes)

------------------------------------------------------------------------

### Resume a Draft

If a session was interrupted after Phase 4, resume from where you left off.

```
/qcoe --resume docs/coe/2026-04-11-standing-orders-draft.md
```

------------------------------------------------------------------------

## Workflow

```
Phase 0: Pattern Scan        → Check for related prior COEs
Phase 1: Gather Context      → Incident facts (3 modes)
Phase 2: Classify Severity   → sev1/sev2/sev3/Process Failure/Near Miss
Phase 3: Build Timeline      → Git log + file dates + user timestamps
Phase 4: 5-Whys Analysis     → All 5 presented together for review
Phase 5: Root Cause          → One paragraph, always structural
Phase 6: Corrective Actions  → Table with owner + status
Phase 7: Preventive Mechanisms → Deterministic, automatic, testable only
Phase 8: Metrics to Watch    → 3-5 metrics with targets
Phase 9: Generate Document   → Sanitization check + write to docs/coe/
Phase 10: Save and Report    → Summary confirmation
```

------------------------------------------------------------------------

## Key Design Decisions

### All 5 Whys Presented Together

QCOE generates all 5 Whys from available context, then shows them together for review — not 5 separate prompts. You correct what's wrong and confirm in one step.

### Behavioral Fixes Rejected

If a preventive mechanism relies on human memory or behavior, QCOE rejects it:

```
Rejected: "Engineers will always check X before deploying"
Required: "CI pipeline check that fails if X condition is not met"
```

### Structural Root Cause Always

If the 5-Whys chain lands on "someone forgot," QCOE pushes one level deeper: "What mechanism should have prevented someone from needing to remember this?"

### External Root Causes Supported

If the root cause is external (cloud outage, third-party API), QCOE accepts it and pivots the preventive mechanisms to detection and mitigation speed — not prevention.

### Repeat Pattern Detection

Before starting, QCOE scans `docs/coe/` for keyword overlap with the current incident. If matches are found, it surfaces them and flags if this is a repeat pattern where a prior fix did not hold.

------------------------------------------------------------------------

## Troubleshooting

### "No prior COEs found" even though some exist

QCOE looks for `docs/coe/`, `coes/`, `post-mortems/`, and `.coe/` directories. If your COE files live elsewhere, specify the directory when prompted in Phase 0.

### Git log returns no results

QCOE scopes git searches to `docs/` and `agents/<name>/` only. If your incident involves other paths, provide timestamps and context directly — QCOE proceeds without git data.

### Output path rejected

QCOE rejects paths containing `..` segments or paths outside the project root. Use a relative path from the project root (e.g., `docs/coe/my-coe.md`) or accept the default.

### Draft auto-save location

After Phase 4, QCOE saves a draft to `docs/coe/YYYY-MM-DD-[slug]-draft.md`. If `docs/coe/` doesn't exist, it will be created. To resume: `/qcoe --resume [path]`.

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-core** — QCHECK to review corrective action code, QPLAN to break actions into sprint tasks
- **qshortcuts-support** — QGIT to commit the COE document with conventional commit message

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
