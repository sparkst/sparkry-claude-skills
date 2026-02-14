# Orchestration Workflow (QRALPH v4.0)

Multi-agent swarm orchestration for Claude Code with session persistence, self-healing, process monitoring, long-term memory, and work mode.

## What is QRALPH?

QRALPH creates a Claude Code native team to analyze requests from multiple specialist perspectives (security, architecture, requirements, UX, code quality) before implementation. It dynamically discovers installed plugins and selects the best 3-7 agents for your request.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install orchestration-workflow@sparkry-claude-skills
```

## Usage

### Coding Mode (3-7 agents)
```bash
# Feature development
QRALPH "Add a logout button to the navbar"

# With specific agents
QRALPH "Review auth flow" --agents security,architecture,pm

# Planning mode (no code changes)
QRALPH "Compare auth providers" --mode planning
```

### Work Mode (1-3 agents, new in v4.0)
```bash
# Lightweight tasks: writing, research, business
QWORK "Write a proposal for the client"
QWORK "Research market trends in pharma AI"

# Equivalent to:
QRALPH "Write a proposal" --mode work
```

### Session Management
```bash
# Resume after interruption (STATE.md preserves context)
QRALPH resume 001

# Check status
QRALPH status
```

## How It Works

### Coding Mode
```
     Your Request
          │
          ▼
   ┌─────────────┐
   │   QRALPH    │──→ Discover plugins & skills
   │ Orchestrator│──→ Select 3-7 best agents
   └──────┬──────┘
          │
  ┌───┬───┼───┬───┐
  ▼   ▼   ▼   ▼   ▼
 Sec Arc Req  UX  Code    ← PARALLEL AGENTS (native teams)
  │   │   │   │   │
  └───┴───┼───┴───┘
          ▼
   ┌─────────────┐
   │  Synthesize │──→ P0/P1/P2 Findings
   │  & Execute  │──→ Self-healing
   └─────────────┘──→ UAT Generation
```

### Work Mode
```
INIT → DISCOVERING → PLANNING → USER_REVIEW → EXECUTING → COMPLETE
                                     ^              │
                                     |______________|  (iterate)
                                                    │
                                              ESCALATE → full team
```

## v4.0 Features

### Session Persistence
- **STATE.md** persists across Claude Code sessions
- Tracks execution progress, uncommitted work, session log
- Crash recovery reconstructs state from checkpoints + git

### Process Monitor
- PID registry tracks spawned processes (node, vitest, claude)
- Automatic orphan sweep on session start/end
- Grace periods per process type, circuit breaker on 3+ orphans

### Long-term Memory
- SQLite + FTS5 full-text search across projects
- Auto-captures healing successes/failures, circuit breaker trips
- `QREMEMBER "lesson learned"` for manual capture
- Queries past experience before retrying known errors

### Enhanced Self-Healing
- Pattern matching: normalizes errors, hashes signatures, looks up known fixes
- Catastrophic rollback: 3+ consecutive failures restores last valid checkpoint
- Failed fix avoidance: never retries what already failed
- Model escalation: haiku → sonnet → opus → manual

### Watchdog
- Agent health checks (stuck, empty, missing outputs)
- Phase precondition validation before transitions
- Configurable timeouts per model tier

### Work Mode
- 1-3 agents for lightweight business tasks
- Plan-first workflow with user review loop
- Skill discovery (writing, research, etc.)
- Auto-escalation to full coding mode when complexity grows

## Control Commands

Write to `CONTROL.md` in your project directory:

| Command | Action |
|---------|--------|
| PAUSE | Stop after current step |
| SKIP | Skip current operation |
| ABORT | Graceful shutdown with checkpoint |
| STATUS | Force status dump |
| ESCALATE | Switch to full coding mode (work mode) |

## Model Tiering

| Tier | Model | Use For |
|------|-------|---------|
| Validation | haiku | Simple checks, formatting |
| Analysis | sonnet | Code review, architecture |
| Synthesis | opus | Complex reasoning |

## Cost

Typical coding run: $3-8 (optimized via model tiering)
Typical work run: $1-3 (fewer agents)

## Test Suite

300 tests across 7 test files:
```bash
python3 -m pytest tools/ -q
```

## License

MIT
