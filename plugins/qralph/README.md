# Orchestration Workflow (QRALPH v5.1.0)

Hierarchical sub-team orchestration for Claude Code with **enforced** PE overlay, quality gates, COE/5-Whys root cause analysis, pattern sweeps, ADR management, fresh-context validation, session persistence, self-healing, process monitoring, long-term memory, and work mode.

## What is QRALPH?

QRALPH creates a Claude Code native team to analyze requests from multiple specialist perspectives (security, architecture, requirements, UX, code quality) before implementation. It dynamically discovers installed plugins and selects the best 3-7 agents for your request.

**v5.1** makes all PE overlay features **enforced** (blocking) — PE gates block phase transitions, COE analysis is required before marking tasks fixed, pattern sweeps are required before marking tasks fixed, and the VALIDATING phase is mandatory before finalize.

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

# Fix level control
QRALPH "Audit security" --fix-level p0       # P0 only
QRALPH "Audit security" --fix-level all      # P0+P1+P2
QRALPH "Audit security" --fix-level none     # Skip remediation
```

### Work Mode (1-3 agents)
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

### Architecture (v5.1 — Enforced PE Overlay)

```
QRALPH v5.1 (main session — "Sr. SDM")
  │
  │  PE Overlay: ENFORCED gate checks at every phase transition
  │
  ├── INIT + DISCOVERING (direct, no sub-team)
  │     └── PE gate (BLOCKING): load ADRs, infer requirements, select DoD template
  │
  ├── REVIEWING (sub-team)
  │     ├── Sub-team lead (Sonnet) spawns N review agents
  │     ├── Agents write agent-outputs/*.md to disk
  │     ├── Lead writes phase-outputs/REVIEWING-result.json
  │     ├── QRALPH runs 95% confidence quality gate (7 criteria)
  │     ├── PE gate (BLOCKING): check ADR consistency, propose new ADRs, validate DoD
  │     └── If --human: pause for user approval
  │
  ├── EXECUTING (TDD remediation loop + COE/5-Whys — all enforced)
  │     ├── For each task: COE analysis → failing test → fix → pattern sweep → quality gate
  │     ├── `remediate-done` BLOCKED without COE + pattern sweep
  │     └── `remediate-verify` runs full quality gate before allowing VALIDATING
  │
  ├── VALIDATING (fresh sub-team — MANDATORY before finalize)
  │     ├── Fresh context — no knowledge of implementation details
  │     ├── Must produce phase-outputs/VALIDATING-result.json
  │     └── If fails: back to EXECUTING with failure details
  │
  └── COMPLETE (requires VALIDATING-result.json)
```

### Work Mode
```
INIT → DISCOVERING → PLANNING → USER_REVIEW → EXECUTING → COMPLETE
                                     ^              │
                                     |______________|  (iterate)
                                                    │
                                              ESCALATE → full team
```

## v5.1 Features (Breaking Change)

### Enforced PE Overlay
All PE overlay features from v5.0 are now **blocking** — sessions cannot bypass them:
- **PE gates block phase transitions** — if `run_gate()` returns blockers, checkpoint fails
- **COE required before `remediate-done`** — cannot mark tasks fixed without COE analysis
- **Pattern sweep required before `remediate-done`** — cannot mark tasks fixed without sweep
- **VALIDATING phase mandatory** — `finalize` requires `VALIDATING-result.json`
- **Phase transitions tightened** — only path to COMPLETE is through VALIDATING
- **PE gate import failure is a blocker** — no silent fallback

### COE / 5-Whys Root Cause Analysis
Before marking any remediation task as fixed:
1. `coe-analyze --task REM-NNN` — creates 5-Whys template
2. Fill in root cause analysis
3. `coe-analyze --task REM-NNN --validate` — validates structure
4. `pattern-sweep --task REM-NNN` — searches codebase for same pattern

### ADR Lifecycle
- ADRs loaded from `docs/adrs/` during INIT
- New ADRs proposed during REVIEWING
- Agent findings checked against existing ADRs for consistency
- Approve proposed ADRs: `adr-check --approve NNN`

### Quality Gate (7 Criteria)
1. All critical agents completed (includes pe-reviewer)
2. Every domain covered by findings
3. No unresolved contradictions
4. Testable acceptance criteria present
5. PE risk assessment (structured validation)
6. ADR consistency
7. DoD template compliance

## v5.0 Features

### PE Overlay Gate System
- Phase transition gates with ADR compliance, DoD completeness, requirements inference
- Codebase navigation strategy auto-detection (ts-aware, polyglot, grep-enhanced)
- Definition of Done templates (webapp, API, library)

## v4.1 Features

### Hierarchical Sub-Teams
- Each phase runs in its own sub-team with a dedicated lead
- Main orchestrator stays lean — delegates heavy work to sub-teams
- Sub-team recovery: resume from where a crashed sub-team left off

### Sub-Team Recovery
- Sub-teams write phase-outputs/*.json to disk before teardown
- QRALPH can resume crashed sub-teams from the last checkpoint

## v4.0 Features

### Session Persistence
- **STATE.md** persists across Claude Code sessions
- Crash recovery reconstructs state from checkpoints + git

### Process Monitor
- PID registry tracks spawned processes
- Automatic orphan sweep on session start/end

### Long-term Memory
- SQLite + FTS5 full-text search across projects
- `QREMEMBER "lesson learned"` for manual capture

### Enhanced Self-Healing
- Pattern matching with known fix lookup
- Catastrophic rollback on 3+ consecutive failures
- Model escalation: haiku → sonnet → opus → manual

### Work Mode
- 1-3 agents for lightweight business tasks
- Plan-first workflow with user review loop
- Auto-escalation when complexity grows

## Control Commands

Write to `CONTROL.md` in your project directory:

| Command | Action |
|---------|--------|
| PAUSE | Stop after current step |
| SKIP | Skip current operation |
| ABORT | Graceful shutdown with checkpoint |
| STATUS | Force status dump |
| ESCALATE | Switch to full coding mode (work mode) |

## Test Suite

600+ tests across 11 test files:
```bash
python3 -m pytest tools/ -q
```

## License

MIT
