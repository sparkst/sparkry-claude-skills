# QRALPH Quick Start Guide

> **Team-Based Orchestration for Claude Code**
>
> Provided by [Sparkry.ai](https://sparkry.ai) | [Support](https://sparkry.ai/support) | [Docs](https://sparkry.ai/docs/qralph)

------------------------------------------------------------------------

## What is the Ralph Loop?

The "Ralph Loop" is a team-based review pattern where **specialist agents coordinate through shared task lists and messaging** to examine your request before any code is written. Instead of one AI making all decisions, you get a real team of 3-7 experts working together — and they automatically discover and use your installed plugins and skills.

**Why use it?**

| Without Ralph Loop | With Ralph Loop |
|--------------------------------------|----------------------------------|
| Single perspective | 3-7 coordinated expert perspectives |
| Discover issues during implementation | Discover issues before implementation |
| Fix -> Break -> Fix cycles | Comprehensive upfront review |
| Ignores installed plugins | Uses your plugins contextually |
| Loses context between sessions | STATE.md persists across sessions |
| Orphaned processes after crashes | Automatic process cleanup |
| Same errors repeated | Learns from past failures |

The Ralph Loop is especially valuable when you want Claude to **build something amazing over hours** — a multi-file feature, a complex refactor, or a new subsystem.

------------------------------------------------------------------------

## What's New in v4.0

- **Session Persistence**: STATE.md survives Claude Code restarts — resume exactly where you left off
- **Work Mode**: Lightweight 1-3 agent teams for writing, research, and business tasks via `QWORK`
- **Process Monitor**: PID registry tracks spawned processes, auto-sweeps orphans on crash recovery
- **Long-term Memory**: SQLite + FTS5 memory store learns from healing successes/failures across projects
- **Enhanced Self-Healing**: Pattern matching skips known failures, catastrophic rollback on 3+ consecutive fails
- **Watchdog**: Agent health checks with configurable timeouts and escalation paths
- **ESCALATE Command**: Work mode auto-escalates to full coding mode when complexity grows

------------------------------------------------------------------------

## Quick Setup: 4 Common Use Cases

### Use Case 1: Feature Development (30 min - 2 hours)

**Scenario**: Add a new feature to an existing codebase.

```
QRALPH "Add user profile page with avatar upload, bio editing, and privacy settings"
```

**What happens**:
1. QRALPH discovers your installed plugins (e.g., `frontend-design` for UI work)
2. Selects 5 best agents: architecture, security, ux (with frontend-design skill), sde-iii, requirements
3. Creates a team, spawns teammates, registers PIDs with process monitor
4. Teammates coordinate, use relevant skills, report findings
5. Findings synthesized into P0/P1/P2 priorities
6. Implementation proceeds with self-healing (pattern matching + memory store)
7. STATE.md tracks progress — safe to resume after interruption
8. Team shuts down cleanly, orphan sweep runs

**Human checkpoint**: Review SYNTHESIS.md before implementation starts.

------------------------------------------------------------------------

### Use Case 2: Lightweight Work Tasks (10-30 min)

**Scenario**: Writing, research, or business tasks that don't need a full 7-agent team.

```
QWORK "Write a proposal for the client about our AI consulting services"
QWORK "Research market trends in pharma AI for Q2 planning"
QWORK "Create a presentation on our product roadmap"
```

**What happens**:
1. QRALPH enters work mode (1-3 agents)
2. Discovers relevant skills (QWRITE, research-workflow, QPPT)
3. Creates PLAN.md with steps and estimates
4. Pauses at USER_REVIEW for your approval
5. Executes after approval — iterates on feedback
6. Auto-escalates to full coding mode if complexity grows

**Human checkpoint**: Review PLAN.md before execution starts.

------------------------------------------------------------------------

### Use Case 3: Security-Focused Review (1-3 hours)

**Scenario**: Add authentication or handle sensitive data.

```
QRALPH "Implement OAuth2 login with Google and GitHub, store tokens securely" --agents security-reviewer,architecture-advisor,requirements-analyst,integration-specialist,pe-reviewer
```

**What happens**:
1. Security-heavy team (you specified the agents)
2. Each agent reviews from their specialty via shared task list
3. `security-reviewer` gets `code-review` skill if installed
4. Memory store checks for prior auth-related healing patterns
5. Detailed review of auth flows, token storage, session management

**Human checkpoint**: Review security findings in `agent-outputs/security-reviewer.md`.

------------------------------------------------------------------------

### Use Case 4: Research & Planning (No Code)

**Scenario**: Explore options before committing to an approach.

```
QRALPH "Compare state management options: Redux vs Zustand vs Jotai for our React app" --mode planning
```

**What happens**:
1. Planning mode = no code changes
2. Discovers `research-workflow` agents if installed
3. Team of 4 agents: research-director, pm, strategic-advisor, fact-checker
4. Recommendations synthesized

**Human checkpoint**: This IS the checkpoint — review recommendations and decide.

------------------------------------------------------------------------

## How QRALPH Works

```
                         Your Request
                              |
                              v
                    +------------------+
                    |   INITIALIZE     |  Create project, STATE.md,
                    |                  |  PID registry, scan plugins
                    +--------+---------+
                             |
                    +--------v---------+
                    |    DISCOVER      |  Find agents, plugins, skills
                    |                  |  Query memory store
                    +--------+---------+
                             |
                    +--------v---------+
                    |  CREATE TEAM     |  TeamCreate + TaskCreate
                    |                  |  + spawn 3-7 teammates
                    +--------+---------+  + register PIDs
                             |
         +-------------------+-------------------+
         v                   v                   v
    +---------+        +---------+        +---------+
    | Agent 1 |        | Agent 2 |   ...  | Agent N |   COORDINATED
    |Security |<------>|  Arch   |<------>|  Code   |   via TaskList
    +---------+        +---------+        +---------+   + SendMessage
         |                  |                  |
         +-------------------+-------------------+
                             |
                    +--------v---------+
                    |    SYNTHESIZE    |  Combine findings,
                    |                  |  prioritize P0/P1/P2
                    +--------+---------+
                             |
                    +--------v---------+
                    |     EXECUTE      |  Implement with pattern-aware
                    |   + Self-Heal    |  healing + memory store
                    +--------+---------+
                             |
                    +--------v---------+
                    | UAT + FINALIZE   |  Generate tests,
                    |                  |  cleanup processes,
                    +------------------+  shutdown team
```

### Session Persistence

STATE.md tracks your project across Claude Code sessions:

```
.qralph/projects/<id>/STATE.md
├── Meta (project ID, request, mode, created)
├── Execution Plan (checkboxes for each phase)
├── Current Step Detail
├── Uncommitted Work (from git diff)
├── Session Log (timestamps, phases, notes)
└── Next Session Instructions
```

Resume after interruption:
```
QRALPH resume <id>
```

### Process Monitor

Automatic orphan prevention:
- PID registry tracks all spawned processes (node, vitest, claude)
- Grace periods per process type (node: 30min, claude: 60min)
- Auto-sweep on session start (catches crashes)
- Circuit breaker on 3+ orphans (writes PAUSE to CONTROL.md)

### Long-term Memory

Cross-project learning via SQLite + FTS5:
- Auto-captures healing successes/failures
- Queries past experience before retrying errors
- Manual capture: `QREMEMBER "lesson learned"`
- Porter stemming for fuzzy matching
- 30-day half-life recency decay

### Self-Healing

When errors occur, QRALPH uses a tiered approach:

| Step | Strategy | Model |
|------|----------|-------|
| 1 | Check healing patterns DB | haiku (cheapest) |
| 2 | Query memory store for known fixes | haiku |
| 3 | Simple fix attempt | haiku |
| 4 | Context-aware fix | sonnet |
| 5 | Deep analysis | opus |
| 6+ | Catastrophic rollback or defer | manual |

### Circuit Breakers

| Limit         | Threshold | Action         |
|---------------|-----------|----------------|
| Tokens        | 500,000   | Halt execution |
| Cost          | \$40 USD  | Halt execution |
| Same Error    | 3x        | Halt execution |
| Heal Failures | 5x        | Defer to human |
| Orphan Procs  | 3+        | Write PAUSE    |

------------------------------------------------------------------------

## Monitoring Progress

**Quick status check**:

```
QRALPH status
```

**Project files to review**:

```
.qralph/projects/<id>/
├── STATE.md                # Session-persistent progress tracking
├── STATUS.md               # Current phase, progress
├── SYNTHESIS.md            # Combined findings (P0/P1/P2)
├── PLAN.md                 # Work mode plan (work mode only)
├── CONTROL.md              # Write intervention commands here
├── discovered-plugins.json # What plugins/skills were found
├── team-config.json        # Team composition
├── UAT.md                  # Generated test scenarios
├── healing-attempts/       # Self-healing audit trail
│   └── healing-patterns.json  # Known error patterns
└── agent-outputs/          # Individual agent reviews
```

### Using CONTROL.md for Intervention

Write commands to `.qralph/projects/<id>/CONTROL.md`:

```
PAUSE    # Stops after current step
SKIP     # Skips current operation
ABORT    # Graceful shutdown (saves checkpoint, cleans processes, shuts down team)
STATUS   # Forces a status dump
ESCALATE # Switch from work mode to full coding mode
```

------------------------------------------------------------------------

## Tips for Best Results

1. **Be specific**: "Add logout button to navbar with confirmation modal" > "add logout"
2. **Use QWORK for lightweight tasks**: writing, research, business tasks don't need 7 agents
3. **Use planning mode first** for complex features
4. **Check SYNTHESIS.md** before implementation
5. **Install relevant plugins** — QRALPH will discover and use them automatically
6. **Use `--agents`** when you need specific expertise
7. **Resume, don't restart**: Use `QRALPH resume <id>` after interruptions
8. **Use QREMEMBER**: Capture lessons learned for future projects

------------------------------------------------------------------------

## Troubleshooting

**"Circuit breaker tripped"**

```
python3 ${SKILL_DIR}/tools/qralph-healer.py clear
```

**"Invalid phase transition"**
Check current phase with `QRALPH status` — phases must proceed in order.

**Agent failing repeatedly**
Check `agent-outputs/<agent>.md` for error details. Try different agents with `--agents`.

**Team not shutting down**
Manually send shutdown requests or use `ABORT` in CONTROL.md.

**Orphaned processes after crash**
```
python3 ${SKILL_DIR}/tools/process-monitor.py sweep
```

**Check memory store for known fixes**
```
python3 ${SKILL_DIR}/../../../qshortcuts-learning/skills/memory-store/scripts/memory-store.py query "error description"
```

------------------------------------------------------------------------

## Getting Help

- **Documentation**: [sparkry.ai/docs/qralph](https://sparkry.ai/docs/qralph)
- **Support**: [sparkry.ai/support](https://sparkry.ai/support)
- **Issues**: [github.com/sparkst/sparkry-claude-skills/issues](https://github.com/sparkst/sparkry-claude-skills/issues)

------------------------------------------------------------------------

*QRALPH v4.0.0 -- Built by [Sparkry.ai](https://sparkry.ai)*
