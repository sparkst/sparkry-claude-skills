# QRALPH State Machine

## States

```
INIT ──► CLARIFYING ──► PLANNING ──► REVIEWING ──► EXECUTING
          │                              │             │
          │ (answered)                   │             ▼
          ▼                              │        SELF_HEAL
     [10m timeout]                       │             │
     use safe default                    │    ◄────────┘
                                         │    (retry ≤5)
                                         ▼
                                ┌──► BLOCKED ──► FUTURE_REQ
                                │
                           UAT ◄┘
                            │
                            ▼
                        COMPLETE
```

## State Definitions

| State | Entry | Exit | Timeout |
|-------|-------|------|---------|
| INIT | QRALPH invoked | Project created | - |
| CLARIFYING | Questions needed | All answered | 10m → safe default |
| PLANNING | Questions done | Plan approved | - |
| REVIEWING | Plan ready | 5 agents complete | - |
| EXECUTING | Reviews synthesized | Implementation done | - |
| SELF_HEAL | Problem detected | Fixed or 5 attempts | - |
| BLOCKED | 5 attempts failed | User resolves | - |
| UAT | Execution complete | Tests pass | - |
| COMPLETE | UAT passes | - | - |

## Transitions

### INIT → CLARIFYING
- Create project directory
- Initialize .qralph/ structure
- Git commit: "QRALPH: Start NNN-name"

### CLARIFYING → PLANNING
- All questions answered OR
- 10m timeout (use safe defaults, log to ASSUMPTIONS.md)

### PLANNING → REVIEWING
- Agents selected (user-specified or auto)
- Plan documented

### REVIEWING → EXECUTING
- All 5 agents complete
- Findings synthesized
- Git commit: "QRALPH: Reviews complete"

### EXECUTING → SELF_HEAL
- Test failure detected
- Type error detected
- Build failure detected

### SELF_HEAL → EXECUTING
- Fix successful (tests pass)

### SELF_HEAL → BLOCKED
- 5 attempts exhausted
- Create DEFERRED.md entry

### EXECUTING → UAT
- Implementation complete
- All tests passing

### UAT → COMPLETE
- All UAT scenarios pass
- Generate SUMMARY.md
- Git commit: "QRALPH: Complete"
- Send completion webhook

## Checkpointing

Checkpoint saved to `.qralph/checkpoints/latest.json`:
- Every 2 minutes during processing
- After each state transition
- After each self-healing attempt

### Checkpoint Schema

```json
{
  "version": "1.0",
  "project_id": "001-feature-name",
  "state": "REVIEWING",
  "timestamp": "2026-01-27T14:32:01Z",
  "request": "Add dark mode toggle",
  "mode": "coding",
  "agents": {
    "architecture-advisor": {"status": "complete", "findings": 3},
    "security-reviewer": {"status": "running", "progress": 0.6}
  },
  "self_heal": {
    "current_problem": null,
    "attempt": 0,
    "history": []
  },
  "files_modified": ["src/UserService.ts"],
  "git_commits": ["abc123"]
}
```

## Intervention

CONTROL.md commands (polled every 30s):

| Command | Effect |
|---------|--------|
| PAUSE | Stop after current step, await input |
| SKIP | Skip current self-healing attempt |
| ABORT | Graceful shutdown, save all state |
| STATUS | Force detailed status dump |
| RETRY | Retry current failed operation |
