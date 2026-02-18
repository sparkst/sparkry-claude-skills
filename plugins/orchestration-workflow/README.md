# Orchestration Workflow (QRALPH v4.1)

Hierarchical sub-team orchestration for Claude Code with quality gates, fresh-context validation, session persistence, self-healing, process monitoring, long-term memory, and work mode.

## What is QRALPH?

QRALPH creates a Claude Code native team to analyze requests from multiple specialist perspectives (security, architecture, requirements, UX, code quality) before implementation. It dynamically discovers installed plugins and selects the best 3-7 agents for your request. v4.1 introduces hierarchical sub-teams with quality gates and a dedicated VALIDATING phase for fresh-context verification.

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

# Execution modes
QRALPH "Add dark mode" --human   # Default: pause after review for approval
QRALPH "Add dark mode" --auto    # Auto-continue after quality gate passes
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

### Hierarchical Sub-Teams (v4.1)

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
  ├── EXECUTING (sub-team per context window)
  │     ├── Sub-team 1: implement + run automated tests
  │     ├── Sub-team 2: continue from where sub-team 1 left off (if needed)
  │     └── Repeats until all automated tests pass
  │
  ├── VALIDATING (fresh sub-team)
  │     ├── Fresh context — no knowledge of implementation details
  │     ├── Given: requirements + built artifacts + mini-UAT scenarios
  │     └── If fails: back to EXECUTING with failure details
  │
  └── COMPLETE (direct, no sub-team)
```

### Work Mode
```
INIT → DISCOVERING → PLANNING → USER_REVIEW → EXECUTING → COMPLETE
                                     ^              │
                                     |______________|  (iterate)
                                                    │
                                              ESCALATE → full team
```

## v4.1 Features

### Hierarchical Sub-Teams
- Each phase (REVIEWING, EXECUTING, VALIDATING) runs in its own sub-team
- Sub-team leads manage agent coordination within their phase
- Main orchestrator stays lean — delegates heavy work to sub-teams
- Sub-team recovery: resume from where a crashed sub-team left off

### Quality Gate (95% Confidence)
- Runs after REVIEWING phase completes
- Checks 5 criteria: critical agents completed, domain coverage, no contradictions, testable acceptance criteria, PE risk assessment
- Blocks progression until all criteria pass

### VALIDATING Phase
- Fresh-context sub-team with no knowledge of implementation details
- Given only requirements, built artifacts, and mini-UAT scenarios
- If validation fails, loops back to EXECUTING with failure details
- Ensures implementation matches requirements without confirmation bias

### Execution Modes
- `--human` (default): pauses after REVIEWING for user approval before EXECUTING
- `--auto`: auto-continues after quality gate passes — fully autonomous end-to-end

### Sub-Team Recovery
- Sub-teams write phase-outputs/*.json to disk before teardown
- If a sub-team crashes, QRALPH can resume it from the last checkpoint
- Orphan process cleanup sweeps sub-team processes on recovery

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

429 tests across 9 test files:
```bash
python3 -m pytest tools/ -q
```

## License

MIT
