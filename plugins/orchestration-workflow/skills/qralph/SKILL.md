# QRALPH v4.1.7 - Hierarchical Team Orchestration Skill

> Sr. SDM orchestrator with hierarchical sub-teams, quality gates, fresh-context validation, and cross-session persistence. Builds on v4.0's native teams, plugin discovery, session persistence, process monitoring, long-term memory, and work mode.

## Trigger

Invoke with `/qralph <request>` or use the `QRALPH` shortcut.
For lightweight tasks: `QWORK "<request>"` (work mode with 1-3 agents).

## Execution Rules (MANDATORY)

These rules are NON-NEGOTIABLE. Violating them produces incorrect results.

1. **Use the orchestrator for ALL state transitions.** Run `python3 .qralph/tools/qralph-orchestrator.py <command>` for every phase change. Do NOT manually write STATE.md, current-project.json, or checkpoints.

2. **Execute every phase in order.** The phase sequence is:
   - `init` -> `discover` -> `select-agents` -> TeamCreate + spawn agents -> `synthesize` -> (human approval if --human) -> EXECUTING -> VALIDATING -> `finalize`
   - Do NOT skip phases. Do NOT collapse multiple phases into one step.

3. **Use TeamCreate for agent coordination.** Always create a native team. Do NOT use bare Task calls to build deliverables directly.

4. **Agents MUST use subagent_type='general-purpose'.** Other agent types may lack the Write tool and cannot produce output files.

5. **Verify artifacts exist before advancing.** After REVIEWING: `agent-outputs/*.md` must exist. After synthesize: `SYNTHESIS.md` must exist. After VALIDATING: `phase-outputs/VALIDATING-result.json` must exist.

6. **Log every phase transition.** Append to `decisions.log` at every phase change via the orchestrator tools.

7. **If a Python tool fails, attempt self-healing first.** Run `python3 .qralph/tools/qralph-healer.py heal "<error>"` to auto-fix. If healing succeeds, continue. If healing fails after 3 attempts, report the error to the user. Do NOT silently bypass the orchestrator — falling back to manual orchestration is never acceptable.

8. **Respect fix_level.** The `--fix-level` flag (none|p0|p0_p1|all) controls which findings get remediated. Default is p0_p1.

9. **Process cleanup is automatic.** The orchestrator sweeps orphaned processes on `init`, `resume`, and `finalize`. You do NOT need to run `process-monitor.py sweep` manually — it happens automatically. If you need to check process status mid-run, use `python3 .qralph/tools/process-monitor.py status`.

10. **EXECUTING phase MUST complete before finalize.** During EXECUTING: run `remediate` to create tasks, fix all tasks within `fix_level`, then run `remediate-verify`. You MUST NOT call `finalize` until `remediate-verify` returns `"status": "verified"`. The orchestrator will reject `finalize` if remediation tasks are still open at the active fix_level. If you cannot fix a task, explain why and ask the user — do NOT skip it silently.

11. **Session boundary discipline.** If you detect context compression, are running low on turns, or the user interrupts, immediately checkpoint via `python3 .qralph/tools/session-state.py save` and tell the user: "EXECUTING incomplete — N tasks remain. Resume with `/qralph resume <project-id>`." On resume, the orchestrator includes `remediation_progress` showing exactly which tasks are still open — continue from where you left off.

12. **TDD enforcement during EXECUTING (self-contained).** QRALPH does NOT rely on the host project's CLAUDE.md for development methodology. During `discover`, the orchestrator auto-detects test infrastructure (package.json scripts, pytest, cargo, go test, Makefile). During `remediate`, each task includes `tdd_steps` when test infra is detected. During `remediate-verify`, the orchestrator **re-runs detection** (to catch test infra created by agents during EXECUTING — critical for greenfield projects) and then runs the quality gate command (typecheck + lint + test), blocking verification if it fails. For each remediation task, you MUST:
    - Write a failing test that reproduces the finding BEFORE implementing the fix
    - Implement the minimal change to make the test pass
    - Run the quality gate command shown in `REMEDIATION.md`
    - Only mark the task as fixed (`remediate-done`) after the quality gate passes
    If no test infrastructure is detected at either discovery or verify time, log a warning but do not block.

## Version Check

On first run, check `.qralph/VERSION`. Compare against `current-project.json` `last_seen_version`. If different, announce: "QRALPH updated to v4.1.7 — see CHANGELOG.md for changes." Update `last_seen_version`.

## Tools

All orchestrator tools live at `.qralph/tools/`:

```
.qralph/tools/
├── qralph-orchestrator.py   # Main orchestrator (state, discovery, agents, work mode, sub-teams)
├── qralph-subteam.py        # Sub-team lifecycle (create, check, collect, resume, teardown, quality-gate)
├── qralph-healer.py         # Self-healing with pattern matching & catastrophic rollback
├── qralph-watchdog.py       # Health checks, agent monitoring, preconditions, sub-team health
├── qralph-status.py         # Status monitor (terminal UI)
├── qralph-state.py          # Shared state module (atomic writes, checksums, locking)
├── session-state.py         # Session persistence (STATE.md lifecycle, sub-team recovery)
├── process-monitor.py       # PID registry and orphan cleanup
└── test_*.py                # Test suites (440+ tests)
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

## Architecture: Hierarchical Sub-Teams (v4.1)

```
QRALPH v4.1 (main session — "Sr. SDM")
  │
  │  Persists: STATE.md, current-project.json, checkpoints/, phase-outputs/
  │  Manages: phases, healing, circuit breakers, audit trail, version
  │
  ├── INIT + DISCOVERING (direct, no sub-team)
  │
  ├── REVIEWING (sub-team)
  │     ├── Sub-team lead (Sonnet) spawns N review agents
  │     ├── Agents write agent-outputs/*.md to disk
  │     ├── Lead writes phase-outputs/REVIEWING-result.json
  │     ├── QRALPH runs 95% confidence quality gate
  │     └── If --human: pause for user approval. If --auto: continue.
  │
  ├── EXECUTING (TDD remediation loop)
  │     ├── `remediate` creates tasks with tdd_steps from detected test infra
  │     ├── For each task: write failing test → fix → run quality gate
  │     ├── `remediate-done` marks tasks fixed after quality gate passes
  │     └── `remediate-verify` runs full quality gate before allowing COMPLETE
  │
  ├── VALIDATING (fresh sub-team)
  │     ├── Fresh context — no knowledge of implementation details
  │     ├── Given: requirements + built artifacts + mini-UAT scenarios
  │     └── If fails: back to EXECUTING with failure details
  │
  └── COMPLETE (direct, no sub-team)
```

### Sub-Team Lifecycle

```bash
# Create sub-team for a phase
python3 .qralph/tools/qralph-subteam.py create-subteam --phase REVIEWING

# Monitor progress
python3 .qralph/tools/qralph-subteam.py check-subteam --phase REVIEWING

# Run 95% confidence quality gate
python3 .qralph/tools/qralph-subteam.py quality-gate --phase REVIEWING

# Collect results into QRALPH state
python3 .qralph/tools/qralph-subteam.py collect-results --phase REVIEWING

# Resume after compaction/crash
python3 .qralph/tools/qralph-subteam.py resume-subteam --phase REVIEWING

# Clean up
python3 .qralph/tools/qralph-subteam.py teardown-subteam --phase REVIEWING
```

### Quality Gate (95% Confidence)

The quality gate checks 5 criteria:
1. All critical agents completed (security-reviewer, architecture-advisor, sde-iii)
2. Every domain from the request covered by at least one finding
3. No unresolved contradictions between agents
4. Execution plan has testable acceptance criteria
5. PE risk assessment present (complexity, coverage, maintainability)

### Execution Modes

```bash
QRALPH "<request>" --human   # Default: pause after REVIEWING for approval
QRALPH "<request>" --auto    # Auto-continue after quality gate passes
QRALPH "<request>" --fix-level p0       # Remediate P0 only
QRALPH "<request>" --fix-level all      # Remediate P0+P1+P2
QRALPH "<request>" --fix-level none     # Skip remediation entirely
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
├── phase-outputs/           # Sub-team result files (v4.1)
│   ├── REVIEWING-result.json
│   ├── EXECUTING-result.json
│   └── VALIDATING-result.json
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
2. `discover` - scans plugins/skills/agents + detects test infrastructure
3. `select-agents` - picks best 3-7 agents
4. TeamCreate + TaskCreate + spawn teammates
5. Monitor via TaskList + receive messages
6. `synthesize` - consolidates into SYNTHESIS.md
7. `remediate` - creates TDD-enforced remediation tasks
8. For each task: write failing test → implement fix → run quality gate → `remediate-done`
9. `remediate-verify` - runs quality gate, blocks if tests/lint/typecheck fail
10. `generate-uat` - UAT scenarios
11. `finalize` - SUMMARY.md + team shutdown

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
