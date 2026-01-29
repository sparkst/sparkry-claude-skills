# QRALPH Quick Start Guide

> **Multi-Agent Swarm Orchestration for Claude Code**
>
> Provided by [Sparkry.ai](https://sparkry.ai) \| [Support](https://sparkry.ai/support) \| [Docs](https://sparkry.ai/docs/qralph)

------------------------------------------------------------------------

## What is the Ralph Loop?

The "Ralph Loop" is a parallel review pattern where **5 specialist agents examine your request simultaneously** before any code is written. Instead of one AI making all decisions, you get perspectives from security, architecture, requirements, UX, and code quality experts—all at once.

**Why use it?**

| Without Ralph Loop | With Ralph Loop |
|--------------------------------------|----------------------------------|
| Single perspective | 5 expert perspectives |
| Discover issues during implementation | Discover issues before implementation |
| Fix → Break → Fix cycles | Comprehensive upfront review |
| "Works but has problems" | "Works and considered edge cases" |

The Ralph Loop is especially valuable when you want Claude to **build something amazing over hours**—a multi-file feature, a complex refactor, or a new subsystem. The upfront investment in parallel review pays off in fewer rewrites.

------------------------------------------------------------------------

## Installation Location

QRALPH can be installed at two levels:

| Level | Location | Best For |
|-------------------|---------------------------|---------------------------|
| **User** (default) | `~/.claude/skills/` | Personal projects, consistent across all repos |
| **Project** | `./.claude/skills/` | Team sharing, project-specific configuration |

The installer will ask which you prefer.

------------------------------------------------------------------------

## Quick Setup: 3 Common Use Cases

### Use Case 1: Feature Development (30 min - 2 hours)

**Scenario**: Add a new feature to an existing codebase.

```         
QRALPH "Add user profile page with avatar upload, bio editing, and privacy settings"
```

**What happens**: 1. QRALPH analyzes your codebase structure 2. 5 agents review in parallel (security for upload, UX for form design, etc.) 3. Findings synthesized into P0/P1/P2 priorities 4. Implementation proceeds with self-healing 5. UAT scenarios generated

**Human checkpoint**: Review SYNTHESIS.md before implementation starts.

------------------------------------------------------------------------

### Use Case 2: Security-Focused Review (1-3 hours)

**Scenario**: Add authentication or handle sensitive data.

```         
QRALPH "Implement OAuth2 login with Google and GitHub, store tokens securely" --agents security-reviewer,architecture-advisor,requirements-analyst,integration-specialist,pe-reviewer
```

**What happens**: 1. Security-heavy agent selection (you specified security-reviewer) 2. Detailed review of auth flows, token storage, session management 3. Vulnerability analysis before any code written 4. Implementation with extra validation

**Human checkpoint**: Review security findings in `reviews/security-reviewer.md` before proceeding.

------------------------------------------------------------------------

### Use Case 3: Research & Planning (No Code)

**Scenario**: Explore options before committing to an approach.

```         
QRALPH "Compare state management options: Redux vs Zustand vs Jotai for our React app" --mode planning
```

**What happens**: 1. Planning mode = no code changes 2. Agents research and analyze trade-offs 3. Recommendations synthesized 4. You decide the approach, then run a coding QRALPH

**Human checkpoint**: This IS the checkpoint—review recommendations and decide.

------------------------------------------------------------------------

## Medium Setup: Building Something Amazing Over Hours

For complex, multi-hour builds, use QRALPH with deliberate human-in-the-loop checkpoints.

### Example: Building a Dashboard System

**Phase 1: Architecture Review (30 min)**

```         
QRALPH "Design a real-time analytics dashboard with charts, filters, and data export" --mode planning
```

Review `SYNTHESIS.md`. Approve or adjust the approach.

**Phase 2: Core Implementation (1-2 hours)**

```         
QRALPH "Implement the dashboard foundation: data fetching, chart components, filter state"
```

**Human checkpoint at 50%**: Check `.qralph/projects/<id>/STATUS.md` - Are the right patterns being used? - Any P0 issues emerging? - Write `PAUSE` to `CONTROL.md` if needed

**Phase 3: Features & Polish (1-2 hours)**

```         
QRALPH resume <project-id>
```

Or start fresh for the next feature set:

```         
QRALPH "Add data export (CSV, PDF) and dashboard customization to the analytics system"
```

### Recommended Human-in-the-Loop Points

| Checkpoint | When | What to Review |
|------------------------|-----------------|--------------------------------|
| **After Planning** | Before any code | Does the approach match your vision? |
| **After Synthesis** | Before implementation | Are P0 issues acceptable? |
| **At 50% Progress** | Mid-implementation | Check STATUS.md for drift |
| **Before Finalize** | After UAT generated | Do test scenarios cover your needs? |

### Using CONTROL.md for Intervention

Write these commands to `.qralph/projects/<id>/CONTROL.md`:

``` markdown
PAUSE
# Stops after current step, waits for you

SKIP
# Skips current operation (use carefully)

ABORT
# Graceful shutdown, saves checkpoint

STATUS
# Forces a status dump to STATUS.md
```

------------------------------------------------------------------------

## How QRALPH Works

```         
                         Your Request
                              │
                              ▼
                    ┌──────────────────┐
                    │     INITIALIZE   │  Analyze request,
                    │                  │  select 5 agents
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │ Agent 1 │        │ Agent 2 │   ...  │ Agent 5 │   PARALLEL
    │Security │        │  Arch   │        │  Code   │   EXECUTION
    └────┬────┘        └────┬────┘        └────┬────┘
         │                  │                  │
         └───────────────────┼───────────────────┘
                             ▼
                    ┌──────────────────┐
                    │    SYNTHESIZE    │  Combine findings,
                    │                  │  prioritize P0/P1/P2
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │     EXECUTE      │  Implement with
                    │   + Self-Heal    │  auto-retry & escalation
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   UAT + FINALIZE │  Generate tests,
                    │                  │  complete project
                    └──────────────────┘
```

### Self-Healing

When errors occur, QRALPH automatically retries with model escalation:

| Attempt | Model  | Use Case                      |
|---------|--------|-------------------------------|
| 1-2     | haiku  | Simple fixes (imports, typos) |
| 3-4     | sonnet | Complex fixes (logic errors)  |
| 5       | opus   | Architectural issues          |
| 6+      | manual | Creates DEFERRED.md for you   |

### Circuit Breakers

Automatic safety limits:

| Limit         | Threshold | Action         |
|---------------|-----------|----------------|
| Tokens        | 500,000   | Halt execution |
| Cost          | \$40 USD  | Halt execution |
| Same Error    | 3x        | Halt execution |
| Heal Failures | 5x        | Defer to human |

------------------------------------------------------------------------

## Monitoring Progress

**Quick status check**:

```         
QRALPH status
```

**Watch mode** (updates every 5 seconds):

``` bash
python3 ~/${CLAUDE_PLUGIN_ROOT}/skills/orchestration/qralph/tools/qralph-status.py --watch
```

**Project files to review**:

```         
.qralph/projects/<id>/
├── STATUS.md       # Current phase, progress, issues
├── SYNTHESIS.md    # Combined findings (P0/P1/P2)
├── CONTROL.md      # Write intervention commands here
├── UAT.md          # Generated test scenarios
└── reviews/        # Individual agent outputs
```

------------------------------------------------------------------------

## Tips for Best Results

1.  **Be specific**: "Add logout button to navbar with confirmation modal" \> "add logout"

2.  **Use planning mode first** for complex features to validate approach before coding

3.  **Check SYNTHESIS.md** before implementation—this is your main decision point

4.  **Monitor long runs** with `--watch` mode or periodic STATUS.md checks

5.  **Use `--agents`** when you need specific expertise (security for auth, ux for forms)

6.  **Resume, don't restart**: Use `QRALPH resume <id>` after interruptions

------------------------------------------------------------------------

## Troubleshooting

**"Circuit breaker tripped"**

``` bash
python3 ~/${CLAUDE_PLUGIN_ROOT}/skills/orchestration/qralph/tools/qralph-healer.py clear
```

**"Invalid phase transition"** Check current phase with `QRALPH status`—phases must proceed in order.

**Agent failing repeatedly** Check `reviews/<agent>.md` for error details. Try different agents with `--agents`.

------------------------------------------------------------------------

## Getting Help

-   **Documentation**: [sparkry.ai/docs/qralph](https://sparkry.ai/docs/qralph)
-   **Support**: [sparkry.ai/support](https://sparkry.ai/support)
-   **Issues**: [github.com/sparkry/qralph/issues](https://github.com/sparkry/qralph/issues)

------------------------------------------------------------------------

*QRALPH v2.1.0 — Built with ❤️ by [Sparkry.ai](https://sparkry.ai)*