# QRALPH State Machine v4.0

## Coding Mode States

```
INIT ──► DISCOVERING ──► REVIEWING ──► EXECUTING
                            │             │
                            │             ▼
                            │        SELF_HEAL
                            │             │
                            │    ◄────────┘
                            │    (retry ≤5)
                            ▼
                   ┌──► BLOCKED ──► FUTURE_REQ
                   │
              UAT ◄┘
               │
               ▼
           COMPLETE ──► TEAM_SHUTDOWN
```

## Work Mode States (v4.0)

```
INIT ──► DISCOVERING ──► PLANNING ──► USER_REVIEW ──► EXECUTING
                                          │  ▲            │
                                          │  │            │
                                          │  └────────────┘
                                          │  (iterate on feedback)
                                          │
                                          └──► ESCALATE ──► REVIEWING
                                                           (full team)
```

## State Definitions

### Coding Mode

| State | Entry | Exit | Key Action |
|-------|-------|------|------------|
| INIT | QRALPH invoked | Project created | Create project directory, initialize PID registry |
| DISCOVERING | Project ready | Plugins scanned | Scan agents, plugins, skills; query memory store |
| REVIEWING | Team composed | All agents complete | TeamCreate, spawn teammates |
| EXECUTING | Reviews synthesized | Implementation done | Fix P0/P1 issues |
| SELF_HEAL | Problem detected | Fixed or 5 attempts | Pattern match → model escalation → catastrophic rollback |
| BLOCKED | 5 attempts failed | User resolves | Create DEFERRED.md |
| UAT | Execution complete | Tests pass | Generate UAT scenarios |
| COMPLETE | UAT passes | Team shutdown | Finalize + cleanup + process sweep |

### Work Mode (v4.0)

| State | Entry | Exit | Key Action |
|-------|-------|------|------------|
| INIT | QWORK invoked | Project created | Create project, 1-3 agent selection |
| DISCOVERING | Project ready | Skills found | Discover relevant skills (writing, research, etc.) |
| PLANNING | Discovery done | Plan created | Generate PLAN.md with steps, skills, estimates |
| USER_REVIEW | Plan ready | User approves/iterates | Pause for user feedback |
| EXECUTING | Plan approved | Work complete | Execute plan with selected skills |
| ESCALATE | Complexity grew | Re-enters REVIEWING | Switch to full coding mode (3-7 agents) |

## Transitions

### INIT -> DISCOVERING
- Create project directory with `.qralph/` structure
- Initialize state.json, CONTROL.md, decisions.log, STATE.md
- Initialize PID registry (process monitor)
- Run `qralph-orchestrator.py discover`

### DISCOVERING -> REVIEWING (coding mode)
- Scan `.claude/agents/`, `.claude/plugins/`, skill registry
- Score all capabilities against request
- Query memory store for relevant past experience
- Save `discovered-plugins.json`
- Run `qralph-orchestrator.py select-agents`
- Select 3-7 best agents dynamically

### DISCOVERING -> PLANNING (work mode)
- Discover relevant skills (writing, research, etc.)
- Select 1-3 lightweight agents
- Generate PLAN.md with steps and estimates

### PLANNING -> USER_REVIEW (work mode)
- Plan ready for user review
- Pause execution until user approves or provides feedback

### USER_REVIEW -> EXECUTING (work mode)
- User approves plan
- Execute with selected skills

### USER_REVIEW -> PLANNING (work mode, iterate)
- User provides feedback
- Revise plan based on feedback

### EXECUTING -> ESCALATE (work mode)
- Complexity exceeded work mode capacity
- Domains > 3, P0 findings, heal_attempts >= 3, or ESCALATE in CONTROL.md

### ESCALATE -> REVIEWING (work mode -> coding mode)
- Re-enters full team flow with 3-7 agents

### REVIEWING (Team Phase)
This is the key team coordination phase:

```
1. TeamCreate(team_name="qralph-NNN-slug")
2. TaskCreate for each agent's review task
3. Spawn teammates:
   Task(subagent_type=..., team_name=..., name=...)
   process-monitor.py register --pid <PID>
4. Teammates:
   - Check TaskList for assigned work
   - Mark tasks in_progress
   - Use relevant skills (if matched)
   - Write findings to agent-outputs/
   - Mark tasks completed
   - SendMessage summary to team lead
5. Team lead monitors via TaskList
6. Watchdog checks agent health (stuck, empty, timeout)
7. When all tasks complete -> EXECUTING or COMPLETE
```

### REVIEWING -> EXECUTING
- All agent tasks complete
- Findings synthesized into SYNTHESIS.md
- Run `qralph-orchestrator.py synthesize`

### REVIEWING -> COMPLETE (planning mode)
- Non-coding mode skips execution
- Produces deliverables directly

### EXECUTING -> SELF_HEAL
- Test failure, type error, build failure detected
- Check healing patterns DB for known fixes
- Query memory store for prior resolutions

### SELF_HEAL -> EXECUTING
- Fix successful (tests pass)
- Record successful fix to patterns DB and memory store

### SELF_HEAL -> BLOCKED
- 5 attempts exhausted (or catastrophic rollback triggered at 3)
- Create DEFERRED.md entry

### EXECUTING -> UAT
- Implementation complete, tests passing

### UAT -> COMPLETE
- All UAT scenarios pass
- Generate SUMMARY.md

### COMPLETE -> TEAM_SHUTDOWN
- Send shutdown_request to each teammate
- Wait for acknowledgment
- Run process-monitor.py cleanup
- Update STATE.md with completion
- TeamDelete() to clean up

## Session Persistence (v4.0)

### STATE.md Lifecycle
- Created on `cmd_init`
- Updated at every phase transition
- Records execution progress, uncommitted work, session log
- Survives Claude Code session restarts

### Session Start
1. Read `current-project.json` for active project
2. Load STATE.md, output JSON summary (<2000 tokens)
3. Present next instructions, uncommitted work alerts
4. Detect stale PID registry, auto-sweep orphans

### Session End
1. Update STATE.md checkboxes, advance step
2. Populate uncommitted work from `git diff --stat`
3. Append session log row
4. Write next session instructions
5. Run process-monitor.py cleanup

### Crash Recovery
1. Detect stale PID registry (parent PID dead)
2. Auto-sweep orphaned processes
3. Reconstruct state from checkpoints + git log + git status
4. Mark uncertain items as `STATUS UNKNOWN`

## Self-Healing (v4.0 Enhanced)

```
Error occurs
     │
     v
┌─────────────────────────────────┐
│ 1. Check healing patterns DB    │
│    - Normalize error            │
│    - Hash signature (SHA-256)   │
│    - Lookup known fix           │
│    If found → apply with haiku  │
└────────────┬────────────────────┘
             │ (no match)
             v
┌─────────────────────────────────┐
│ 2. Query memory store           │
│    - Check for prior failures   │
│    - Skip known failed fixes    │
│    - Use known workarounds      │
└────────────┬────────────────────┘
             │
             v
┌─────────────────────────────────┐
│ 3. Check Circuit Breakers       │
│    - Token limit (500K)?        │
│    - Cost limit ($40)?          │
│    - Same error 3x?             │
│    - 3+ orphan processes?       │
└────────────┬────────────────────┘
             │
      ┌──────┴──────┐
      │ Breaker OK? │
      └──────┬──────┘
        NO   │   YES
        │    │
        v    v
   ┌────────┐    ┌─────────────────────────────┐
   │ DEFER  │    │  Model Escalation            │
   │ Issue  │    │                              │
   └────────┘    │  Attempt 1-2 ──> haiku       │
                 │  Attempt 3-4 ──> sonnet      │
                 │  Attempt 5   ──> opus        │
                 │                              │
                 │  On 3+ failures:             │
                 │  → Catastrophic rollback     │
                 │  → Restore last checkpoint   │
                 │  → Reset counters            │
                 └──────────────────────────────┘
```

## Team Lifecycle

```
TeamCreate("qralph-NNN")
    │
    ├── process-monitor.py init (PID registry)
    │
    ├── Spawn teammate 1 ──► register PID ──► works ──► SendMessage ──► idle
    ├── Spawn teammate 2 ──► register PID ──► works ──► SendMessage ──► idle
    ├── Spawn teammate 3 ──► register PID ──► works ──► SendMessage ──► idle
    │   ...
    │
    ├── Watchdog health checks (stuck, empty, timeout)
    │
    ├── [Optional: spawn more for fix tasks]
    │
    ├── shutdown_request to teammate 1 ──► ack
    ├── shutdown_request to teammate 2 ──► ack
    ├── shutdown_request to teammate 3 ──► ack
    │
    ├── process-monitor.py cleanup
    └── TeamDelete()
```

## Checkpointing

Checkpoint saved to `.qralph/projects/NNN/checkpoints/`:
- After each state transition
- After each self-healing attempt
- Includes full team composition for resume
- SHA-256 checksum for integrity validation

### Checkpoint Schema

```json
{
  "project_id": "001-feature-name",
  "project_path": "relative/path/to/project",
  "request": "Add dark mode toggle",
  "mode": "coding",
  "phase": "REVIEWING",
  "created_at": "2026-01-27T14:32:01Z",
  "team_name": "qralph-001-feature-name",
  "agents": ["architecture-advisor", "security-reviewer", "sde-iii"],
  "teammates": ["architecture-advisor-agent", "security-reviewer-agent", "sde-iii-agent"],
  "skills_for_agents": {
    "ux-designer": ["frontend-design"]
  },
  "domains": ["frontend", "architecture"],
  "findings": [],
  "heal_attempts": 0,
  "circuit_breakers": {
    "total_tokens": 0,
    "total_cost_usd": 0.0,
    "error_counts": {}
  },
  "_checksum": "sha256_of_state"
}
```

## Intervention

CONTROL.md commands:

| Command | Effect |
|---------|--------|
| PAUSE | Stop after current step, await input |
| SKIP | Skip current operation |
| ABORT | Graceful shutdown: checkpoint + process cleanup + team shutdown |
| STATUS | Force detailed status dump to STATUS.md |
| ESCALATE | Switch from work mode to full coding mode (v4.0) |
