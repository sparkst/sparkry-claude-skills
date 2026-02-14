# QRALPH v4.0 - Team Orchestration Skill

> Team-based orchestrator using Claude Code native teams with dynamic plugin discovery, session persistence, process monitoring, long-term memory, and work mode.

## Trigger

Invoke with `/qralph <request>` or use the `QRALPH` shortcut.
For lightweight tasks: `QWORK "<request>"` (work mode with 1-3 agents).

## Tools

All orchestrator tools live at `.qralph/tools/`:

```
.qralph/tools/
├── qralph-orchestrator.py   # Main orchestrator (state, discovery, agents, work mode)
├── qralph-healer.py         # Self-healing with pattern matching & catastrophic rollback
├── qralph-watchdog.py       # Health checks, agent monitoring, preconditions
├── qralph-status.py         # Status monitor (terminal UI)
├── qralph-state.py          # Shared state module (atomic writes, checksums, locking)
├── session-state.py         # Session persistence (STATE.md lifecycle)
├── process-monitor.py       # PID registry and orphan cleanup
└── test_*.py                # Test suites (300+ tests)
```

Long-term memory:
```
.claude/skills/learning/memory-store/
├── scripts/memory-store.py       # SQLite + FTS5 memory store
├── scripts/test_memory_store.py  # Memory store tests
└── SKILL.md                      # QREMEMBER skill definition
```

## Overview

QRALPH creates a Claude Code native team to analyze requests and produce consolidated findings. It dynamically discovers installed plugins and skills, selects the best agents, and coordinates them through shared task lists and messaging.

## Architecture: Native Teams (v3.0+)

```
┌────────────────────────────────────────────────────────┐
│  TEAM LEAD (You)                                       │
│  1. Analyze request                                    │
│  2. Discover relevant plugins & skills                 │
│  3. Select agents dynamically                          │
│  4. TeamCreate + TaskCreate + spawn teammates          │
│  5. Monitor via TaskList + receive messages             │
│  6. Synthesize findings                                │
│  7. Shutdown team + cleanup                            │
└────────────────┬───────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
┌────────┐ ┌────────┐ ┌────────┐
│Agent 1 │ │Agent 2 │ │Agent N │  TEAM: shared TaskList
│        │ │        │ │        │  + SendMessage + skills
└────────┘ └────────┘ └────────┘
```

## Project Structure

Projects are created in: `.qralph/projects/`

```
.qralph/projects/NNN-project-slug/
├── STATE.md                 # Session state (persists across sessions)
├── PLAN.md                  # Work plan (work mode only)
├── PLAN-FEEDBACK.md         # User feedback on plan (work mode)
├── CONTROL.md               # User intervention commands
├── SYNTHESIS.md             # Consolidated findings (P0/P1/P2)
├── UAT.md                   # User acceptance test scenarios
├── SUMMARY.md               # Final summary
├── decisions.log            # Audit trail
├── discovered-plugins.json  # Plugin discovery results
├── team-config.json         # Team composition snapshot
├── agent-outputs/           # Individual agent reports
├── healing-attempts/        # Self-healing audit trail + patterns DB
│   └── healing-patterns.json
└── checkpoints/             # Resumable state snapshots
```

## Modes

### `coding` (default)
Dynamic agent selection (3-7 agents) for code analysis, implementation, and review.

### `planning`
Non-coding mode for research, design, and strategy.

### `work` (new in v4.0)
Lightweight mode (1-3 agents) for business tasks, writing, research.

**Work mode state machine:**
```
INIT -> DISCOVERING -> PLANNING -> USER_REVIEW -> EXECUTING -> COMPLETE
                                       ^              |
                                       |______________|  (iterate)
                                                      |
                                                ESCALATE -> REVIEWING (full team)
```

**Escalation triggers:**
- Domains > 3
- P0 findings emerge
- 3+ healing failures
- User writes ESCALATE in CONTROL.md

## Workflow

### Coding Mode

```bash
QRALPH "<request>" [--mode coding]
```

1. `init` - creates project, STATE.md
2. `discover` - scans plugins/skills/agents
3. `select-agents` - picks best 3-7 agents
4. TeamCreate + TaskCreate + spawn teammates
5. Monitor via TaskList + receive messages
6. `synthesize` - consolidates into SYNTHESIS.md
7. `generate-uat` - UAT scenarios
8. `finalize` - SUMMARY.md + team shutdown

### Work Mode

```bash
QWORK "<request>"
# or: QRALPH "<request>" --mode work
```

1. `init --mode work` - creates project
2. `discover` - scans for relevant skills
3. `work-plan` - generates PLAN.md
4. User reviews plan
5. `work-approve` - proceeds to execution (or `work-iterate` to revise)
6. `select-agents` - picks 1-3 agents
7. Execute + `finalize`

## Session Persistence (v4.0)

### STATE.md

Created on project init, updated on every phase transition and session boundary:

```markdown
## Meta
- Project: NNN-slug
- Request: ...
- Mode: coding|work

## Execution Plan
- [x] INIT
- [x] DISCOVERING
- [ ] REVIEWING (current)
- [ ] EXECUTING
- [ ] UAT
- [ ] COMPLETE

## Current Step Detail
...

## Uncommitted Work
(git diff --stat output)

## Session Log
| # | Started | Ended | Phase | Notes |
|---|---------|-------|-------|-------|
| 1 | ... | ... | REVIEWING | Completed discovery |

## Next Session Instructions
Read STATE.md, continue from REVIEWING phase...
```

### Session Commands

```bash
session-state.py create-state <project-id>     # Create STATE.md
session-state.py session-start                  # Read state, output context
session-state.py session-end <project-id>       # Update state, capture uncommitted
session-state.py recover <project-id>           # Crash recovery
session-state.py inject-claude-md [path]        # Append state pointer to CLAUDE.md
```

## Process Monitor (v4.0)

Prevents orphaned processes (node, vitest, claude) from accumulating after crashes.

```bash
process-monitor.py register --pid <PID> --type <node|vitest|claude> --purpose <desc>
process-monitor.py sweep [--dry-run] [--force]
process-monitor.py cleanup --project-id <id>
process-monitor.py status
```

**Safety**: Only kills processes in the PID registry. Unregistered processes get warnings, never killed.

## Long-term Memory (v4.0)

SQLite + FTS5 full-text search for learning from past errors and successes.

```bash
memory-store.py init
memory-store.py store --description "..." --domain "..." --category "..."
memory-store.py query "search terms" [--domain X] [--limit N]
memory-store.py check "has this been tried before?"
memory-store.py stats
```

**Auto-capture hooks**: Healing success/failure, circuit breaker trips, P0 findings.

**QREMEMBER shortcut**:
```
QREMEMBER "FTS4 is too slow, use FTS5 instead"
QREMEMBER --failure "Tried embedding API but adds 2s latency"
```

## Watchdog (v4.0)

Health checks and phase precondition validation.

```bash
qralph-watchdog.py check                         # All health checks
qralph-watchdog.py check-agents                  # Agent output status
qralph-watchdog.py check-state                   # State integrity
qralph-watchdog.py check-preconditions <phase>   # Pre-transition validation
```

**Agent criticality**: security-reviewer, architecture-advisor, sde-iii are critical (never auto-skip).

## Self-Healing (Enhanced in v4.0)

- **Pattern matching**: Normalizes errors, hashes signatures, looks up known fixes before escalating
- **Failed fix avoidance**: Never retries a fix that already failed for the same error
- **Catastrophic rollback**: 3+ consecutive failures triggers restore from last valid checkpoint
- **Memory integration**: Queries long-term memory for known resolutions
- **Model escalation**: haiku (1-2) -> sonnet (3-4) -> opus (5) -> manual (6+)

## Commands Reference

| Command | Description |
|---------|-------------|
| `QRALPH "<request>"` | Create new project (coding mode) |
| `QWORK "<request>"` | Create new project (work mode) |
| `QRALPH --resume` | Resume current project |
| `QRALPH --status` | Show current project status |
| `QRALPH --list` | List recent projects |
| `QRALPH --complete` | Mark current project complete |

## Control Commands (CONTROL.md)

| Command | Action |
|---------|--------|
| PAUSE | Stop after current step |
| SKIP | Skip current operation |
| ABORT | Graceful shutdown with checkpoint |
| STATUS | Force status dump |
| ESCALATE | Switch to full coding mode (work mode only) |

## Current Project Tracking

**File**: `.qralph/current-project.json`

Points to the active QRALPH project with full state including phase, agents, circuit breakers, and session metadata.
