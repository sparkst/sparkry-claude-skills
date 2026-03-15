# QRALPH v6.10.1 — Installation and Usage Guide

## What is QRALPH?

QRALPH is a deterministic 14-phase multi-agent pipeline for Claude Code (v6.10.1). It enforces proper software design process on every run — requirements decomposition, TDD, quality gates, and independent verification — so you stop babysitting AI and start shipping verified software.

**The problem it solves:** AI coding assistants skip steps. They write code without tests. They validate their own work by saying "looks good" instead of actually checking. They forget requirements mid-run. On complex tasks, you end up doing manual follow-ups for every step the AI skipped. QRALPH eliminates this by wrapping Claude Code's capabilities in a pipeline that blocks progression until each phase is genuinely complete.

---

## Installation

### Step 1: Add the Sparkry Marketplace

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install QRALPH

```bash
/plugin install qralph@sparkry-claude-skills
```

### Step 3: Verify Installation

```bash
/plugin list
```

You should see `qralph` in your installed plugins.

---

## Usage

### Basic

```bash
QRALPH "Add user authentication with OAuth2 and session management"
```

### With Mode

```bash
# Full 14-phase pipeline (default) — for production features (includes DEMO)
QRALPH "Build a payment processing system" --thorough

# Quick mode (7 phases) — for developer tasks
QRALPH "Add rate limiting to the API" --quick
```

### With Target Directory

```bash
QRALPH "Build a landing page" --target-dir projects/my-site
```

---

## What Happens When You Run QRALPH

### Thorough Mode (13 phases)

| Phase | What Happens | Why It Matters |
|-------|-------------|----------------|
| **IDEATE** | Brainstorms and validates the concept | Catches bad ideas before any code is written |
| **PERSONA** | Generates 2-3 user archetypes | Pressure-tests the feature from real user perspectives |
| **CONCEPT_REVIEW** | Multi-agent review (architect, PM, developer) | Surfaces P0/P1/P2 issues in the design, not in production |
| **PLAN** | Creates tasks with indexed acceptance criteria | Every AC gets a tracking number (AC-1, AC-2, ...) |
| **EXECUTE** | Parallel agent groups implement with TDD | Tests are written first, code makes them pass |
| **SIMPLIFY** | Reviews implementation for unnecessary complexity | Prevents over-engineering while the code is fresh |
| **QUALITY_LOOP** | Discovery finds issues, fix rounds address them | Automated code review with real fixes, not just comments |
| **POLISH** | Bug fixes, wiring checks, requirements trace | Confirms every requirement has a test and implementation |
| **VERIFY** | Fresh-context agent checks every AC against source files | Independent verification with file:line evidence — no rubber-stamping |
| **DEMO** | Present completed work to user with feedback loop (max 2 cycles) | User sees and approves the result before deployment |
| **DEPLOY** | Preflight checklist, deploy command, verify URL | Only deploys when you explicitly asked for it |
| **SMOKE** | Parallel HTTP tests hit the live site | Confirms the deployed version actually works |
| **LEARN** | Captures learnings for future projects | Each project makes the next one better |
| **COMPLETE** | Final summary with metrics | Clean wrap-up with everything documented |

### Quick Mode (7 phases)

Skips IDEATE, PERSONA, CONCEPT_REVIEW, QUALITY_LOOP, POLISH. Goes straight from PLAN to EXECUTE to VERIFY.

---

## Key Guarantees

**Requirements are never silently dropped.** Your request is decomposed into atomic fragments (REQ-F-1, REQ-F-2, ...) at plan time. The verifier must account for every fragment.

**Every AC is individually verified.** The verification agent reads actual source files with the Read tool and records `file:line — "quoted code"` evidence for each criterion. Generic evidence like "verified in execution outputs" is rejected by the pipeline.

**Quality gates are hard blocks.** Tests, lint, and typecheck must pass before the pipeline advances. Failures trigger automatic fix attempts with retry limits.

**Verification is independent.** The verifier has zero knowledge of how the implementation was done. It validates from source code alone.

**Nothing deploys without consent.** Unless you explicitly said "deploy to X" in your request, the pipeline asks first.

---

## Multi-Project Concurrency (v6.7.0)

Run multiple QRALPH projects simultaneously in separate Claude Code sessions:

```bash
# Terminal 1
QRALPH "Redesign the checkout flow"

# Terminal 2 (separate Claude Code session)
QRALPH "Add notification system"
```

Each session tracks its own project state. Projects with non-overlapping files can run in parallel without conflicts.

---

## Project Outputs

After completion, find your outputs at:

```
.qralph/projects/<project-id>/
├── IDEATION.md              # Refined concept
├── personas/                # User archetypes
├── CONCEPT-SYNTHESIS.md     # Consolidated concept review
├── PLAN.md                  # Implementation plan
├── manifest.json            # Tasks with acceptance criteria
├── execution-outputs/       # Per-task implementation results
├── quality-reports/         # Per-round quality dashboards
├── POLISH-REPORT.md         # Bug fixes and requirements trace
├── verification/
│   └── result.md            # Per-AC verification with evidence
├── DEMO-REPORT.md           # Demo presentation and user feedback
├── DEPLOY-REPORT.md         # Deploy output and live URL
├── smoke-tests/             # Per-category smoke test results
├── SMOKE-REPORT.md          # Aggregated smoke verdict
├── learning-summary.md      # What this project taught QRALPH
├── SUMMARY.md               # Final summary with metrics
├── decisions.log            # Full decision audit trail
└── state.json               # Pipeline state (for recovery)
```

---

## Recovery

If a session crashes or you close the terminal mid-run:

```bash
# Resume from where you left off
python3 .qralph/tools/qralph-pipeline.py next --project <project-id>
```

The pipeline checkpoints at every phase transition. You never lose more than the current step.

---

## Escalation

When auto-fix fails (after retry limits), QRALPH escalates to you with plain-language options:

- **Fix and retry** — You fix the issue, pipeline retries
- **Accept current state** — Move forward with what's done
- **Go back for more fixes** — Return to an earlier phase
- **Stop here** — End the pipeline

You never see raw error traces or TypeScript stack dumps. QRALPH translates everything into decisions you can make.

---

## Cost

QRALPH uses model tiering to minimize cost:
- **Haiku** — Smoke tests, simple validation
- **Sonnet** — Analysis, review, verification, implementation
- **Opus** — Complex synthesis (concept review, planning)

Typical cost: $3-12 per project depending on complexity and mode.

---

## Troubleshooting

### Update to Latest Version

```bash
/plugin marketplace update sparkry-claude-skills
```

### Stale Session Lock

If you see "Another QRALPH session is already running":

```bash
# Check if the PID is actually alive
cat .qralph/projects/<id>/session.lock

# If the process is dead, delete the lock
rm .qralph/projects/<id>/session.lock
rm .qralph/active-session.lock  # legacy global lock
```

### Reset and Reinstall

```bash
/plugin uninstall qralph@sparkry-claude-skills
/plugin marketplace update sparkry-claude-skills
/plugin install qralph@sparkry-claude-skills
```

---

## Questions?

- **Issues:** [GitHub Issues](https://github.com/sparkst/sparkry-claude-skills/issues)
- **Email:** support@sparkry.ai
