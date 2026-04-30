# AI Review Toolkit — Plan v2

> Decomposition of QRALPH into composable, type-agnostic review primitives.
> Round 1 review: 4 clean-context agents, 70 raw findings → 59 deduplicated. All addressed below.

---

## Architectural Foundation

Every stateful skill ships with a **Python driver script** (like QRALPH's `qralph-pipeline.py`). The SKILL.md contains instructions; the driver manages state, loops, and phase transitions. Skills are NOT composed by invoking other skills — they are composed by the pipeline driver spawning agents via the Agent tool, each agent's prompt informed by the relevant skill's instructions.

```
ai-review-toolkit/
  .claude-plugin/plugin.json
  skills/
    qreview/          # Multi-agent review (the core primitive)
    qloop/            # Iterative review-fix cycle
    qpipeline/        # Orchestrator with presets
  agents/
    reviewer.md       # Clean-context reviewer agent
    verifier.md       # Fresh-context acceptance verifier
    fixer.md          # Issue resolution agent
  tools/
    review-driver.py  # State machine for qreview
    loop-driver.py    # State machine for qloop
    pipeline-driver.py # Orchestrator state machine
    finding-parser.py # P0-P3 finding taxonomy (shared)
    test-runner.py    # Deterministic test execution (shared)
    team-selector.py  # Agent selection algorithm (extracted from QRALPH)
  commands/
    qreview.md        # /qreview slash command
    qloop.md          # /qloop slash command
    qpipeline.md      # /qpipeline slash command
  docs/
    plan-v2.md        # This file
```

---

## User-Facing Surface: 3 Slash Commands

| Command | Skill | What It Does |
|---------|-------|-------------|
| `/qreview` | qreview | Spawn N clean-context agents to review any artifact against requirements. P0-P3 findings. |
| `/qloop` | qloop | Iterative review-fix cycle. Review → fix ALL → re-review (fresh context) → repeat until clean. |
| `/qpipeline` | qpipeline | Composable pipeline orchestrator with presets. End-to-end workflows. |

Everything else (self-healing, checkpointing, gates, agent selection, verification) is internal machinery invoked by the drivers.

---

## Skill 1: `/qreview` — Multi-Agent Review

### Purpose

Spawn N (2-5) clean-context agents in parallel to review any artifact against stated requirements. Each reviewer operates in a fresh Agent context with zero shared state. Synthesize findings using **max-severity deduplication** (if reviewer A says P0 and reviewer B says P2, synthesized = P0). Four severity levels: P0, P1, P2, P3.

### Clean Context Enforcement

Each reviewer is spawned via the Agent tool (separate context window). The only inputs are:
1. The artifact
2. The requirements
3. The review lens/domain

No implementation context, no prior round findings, no fix history leaks in. This is structural isolation, not instructional.

### Deterministic Test Gate

Before spawning reviewers, `test-runner.py` discovers and executes all co-located tests (`*_test.py`, `*.spec.ts`, `Makefile test`, validation scripts). Test results are included as a mandatory input to every reviewer. Test failures are auto-classified as findings (P0 if regression, P1 if new failure). A review round where tests fail cannot produce a PASS verdict regardless of reviewer opinions.

### Severity Synthesis

- **Dissent mode is the DEFAULT** — all findings surface, none suppressed
- Convergence (K-of-M elevation) is opt-in and can only ELEVATE severity, never reduce it
- Any single reviewer flagging P0/P1 is sufficient — no voting can override
- When two reviewers flag same issue at different severities → max-severity wins

### Pre-Existing Failures

Reviewer prompt explicitly instructs: "Flag ALL issues found in the artifact, regardless of origin. Pre-existing issues are in-scope." No "out of scope" classification available.

### Token Budget

Each reviewer gets a model assignment based on review domain (haiku for style/format, sonnet for logic/architecture). Total cost ceiling configurable, default $20/round.

### Acceptance Criteria

1. Spawns exactly N agents with zero shared conversation context
2. Each agent reviews independently — no cross-contamination
3. Findings synthesized with P0-P3 max-severity deduplication
4. Deterministic tests executed before reviewer spawn; failures auto-classified
5. Pre-existing issues treated identically to new issues
6. Single-reviewer P0/P1 preserved — no majority-vote downgrade

---

## Skill 2: `/qloop` — Iterative Review-Fix Cycle

### Purpose

The core engine. Runs: Review (via qreview agents) → Fix ALL findings → Re-review (fresh context, same N agents, receives prior findings) → repeat until convergence.

### State Management

`loop-driver.py` persists round state to `.qloop/state.json`:

```json
{
  "round": 2,
  "artifact_path": "...",
  "requirements_path": "...",
  "reviewer_count": 3,
  "rounds": [
    {
      "round_num": 1,
      "findings": [],
      "test_results": {},
      "fix_resolutions": [],
      "timestamp": "..."
    }
  ],
  "status": "reviewing|fixing|converged|escalated"
}
```

### Convergence Criterion

```
P0 == 0 AND P1 == 0 AND (P2_count + P3_count <= significance_threshold)
```

Where `significance_threshold` defaults to **0** (fix everything). The user's R6 says "fix ALL priorities" so default is zero tolerance.

### No Unauthorized Escape Hatches

Max-round limit (default: 5) does NOT silently exit. When reached:

1. Status set to `escalated` (not `converged`)
2. Full finding list with unresolved items presented to user
3. Output explicitly labeled `INCOMPLETE — ESCALATED`
4. Downstream pipeline stages BLOCKED — cannot proceed
5. User must explicitly choose: continue rounds, accept as-is with explicit acknowledgment, or abandon

### Prior Fix Recommendations Fed to Round 2+

Each re-review round receives:

1. The revised artifact
2. The original requirements
3. Complete findings from round N-1 with fix recommendations
4. Diff/change summary showing what was modified
5. The fix resolution checklist

These four inputs are mandatory and enforced by `loop-driver.py` — it refuses to spawn reviewers without them.

### Fix-ALL Enforcement Gate

After the fix step and BEFORE re-review, mandatory issue-resolution checklist:

```json
{
  "finding_id": "P0-001",
  "status": "FIXED",
  "evidence": "path/to/file:line — description of change",
  "diff_reference": "..."
}
```

Every finding MUST have status `FIXED` with evidence. There is no `WONTFIX`, `DEFERRED`, or `OUT_OF_SCOPE` status. If a finding genuinely cannot be fixed, the loop escalates to the user — it does not silently skip. `loop-driver.py` validates this checklist before allowing re-review to proceed.

### Deterministic Test Execution at Every Step

`test-runner.py` runs at:
- Start of each review round
- After fix step, before re-review
- As part of convergence check

Any test failure at any point re-enters the fix cycle.

### Minimum Rounds

Hard minimum of 2 rounds. Round 1 always finds things. Round 2 verifies fixes. The AI cannot declare convergence after round 1 regardless of confidence. This is enforced by `loop-driver.py`, not by instructions.

### Auto-Backtrack

Triggered when: same P0/P1 findings persist across 2 consecutive fix-review cycles with zero measurable improvement. Backtrack carries forward full finding history. Backtrack count bounded at 2 — after 2 backtracks, escalate to user.

### Type-Agnostic Adaptation

For non-code artifacts:
- Deterministic tests → structured rubric evaluation (rubric provided as requirement)
- file:line references → section:quote references
- Fix verification → diff-based section comparison
- Same minimum-round and all-priorities-fixed requirements apply

### Acceptance Criteria

1. Minimum 2 review rounds enforced by driver (not instructions)
2. Convergence requires P0=0, P1=0, P2+P3 ≤ threshold (default 0)
3. Max-round exits as ESCALATED, not converged; blocks downstream
4. Every fix has FIXED status with evidence — no silent skips
5. Prior findings + fix recommendations fed to each re-review round
6. Deterministic tests run at every phase transition
7. Pre-existing failures treated as in-scope at assessed priority

---

## Skill 3: `/qpipeline` — Composable Pipeline Orchestrator

### Purpose

Python-driven pipeline that composes the review primitives into end-to-end workflows. Ships with presets. Users define custom pipelines.

### How It Works

`pipeline-driver.py` defines phases, each phase maps to agent spawns with specific prompts. NOT skill-to-skill composition. The driver IS the orchestrator.

### Presets

```python
PRESETS = {
    "review": ["test-gate", "review-loop", "verify"],
    "thorough": ["ideate", "plan", "execute", "review-loop", "test-gate", "verify", "demo"],
    "content": ["review-loop", "verify"],
    "code": ["review-loop", "test-gate", "verify"],
}
```

- `/qpipeline review <artifact>` — zero-config, runs the review preset (which internally uses qloop logic)
- `/qpipeline thorough <description>` — full QRALPH-equivalent pipeline (7 phases mapping all 14 original QRALPH stages)
- `/qpipeline --phases "review-loop,verify" <artifact>` — custom composition

### Compositional Integrity

Any pipeline containing a "fix" or "implement" phase MUST also contain a `review-loop` phase. The driver validates this at pipeline creation time. Skills that modify artifacts cannot bypass the review cycle.

### Step-Skip Prevention

`pipeline-driver.py` tracks phase execution in state. Every mandatory phase must complete before the next begins. There is no `--skip` flag. The AI following instructions cannot bypass a phase because the driver controls transitions. The driver is deterministic code, not LLM instructions.

### State & Checkpointing

Automatic checkpoints at every phase transition. State includes:
- Artifact snapshot
- All findings from all rounds
- Fix resolution history
- Test results
- Round count

Stored as JSON on disk. Git provides content integrity for anything committed. Resume via `/qpipeline resume <project-id>`.

### Gate Protocol

Uses the proven two-call protocol from QRALPH: driver returns a `confirm_*` action → Claude presents to user → user responds → Claude calls `next --confirm`. Gates are pipeline phases, not a separate skill.

### Status Visibility

`/qpipeline status` and `/qloop status` subcommands read state from disk and report: current round, findings by severity, convergence trend, time elapsed.

### Acceptance Criteria

1. Ships with 4+ presets covering common workflows
2. Custom phase composition with validation
3. Compositional integrity: fix phases require review phases
4. Automatic checkpointing at every phase boundary
5. Resume from checkpoint after session restart
6. Two-call gate protocol at all approval points
7. No `--skip` flag; all phases mandatory once defined

---

## Agent Definitions

These live in `agents/`, NOT as top-level skills. They are spawned by the driver scripts. No slash commands.

### `agents/reviewer.md`

Clean-context artifact reviewer. Receives: artifact, requirements, review lens. Produces: P0-P3 findings with evidence. Model: sonnet (default) or haiku (for format/style).

### `agents/verifier.md`

Fresh-context acceptance verifier. Receives: artifact, acceptance criteria. Produces: per-criterion PASS/FAIL with file:line or section:quote evidence. Model: sonnet.

### `agents/fixer.md`

Issue resolution agent. Receives: artifact, findings, fix recommendations. Produces: modified artifact + resolution checklist. Model: sonnet (default), opus for complex fixes.

---

## Shared Tools

### `tools/finding-parser.py`

P0-P3 taxonomy, deduplication with max-severity, finding schema validation.

### `tools/test-runner.py`

Discovers and runs co-located tests. Supports: pytest, vitest, make test, custom scripts. Returns structured results. Auto-classifies failures as findings.

### `tools/team-selector.py`

Extracted from QRALPH's `qralph-orchestrator.py`. Accepts `--catalog <path>` for custom agent registries. Ships with sensible defaults. Not user-facing — called by pipeline-driver when it needs to select reviewers.

---

## Internal Capabilities (Not Top-Level Skills)

| Originally Proposed | Disposition | Reason |
|---|---|---|
| `/heal` (self-healer) | Internal capability of `loop-driver.py` | Self-healing should be invisible |
| `/checkpoint` | Automatic in `pipeline-driver.py` | Infrastructure, not user action |
| `/gate` | Phase type in pipeline driver | Duplicates built-in approval UX |
| `/pick-team` | Internal call in pipeline driver | Should be automatic |
| `/verify` | Agent definition (`verifier.md`) | Unnecessary indirection as skill |
| `/smoke` | Phase type in pipeline presets | Pattern, not standalone skill |
| `/ideate` | Phase type in `thorough` preset | Only meaningful in pipeline context |
| `/pe` | Agent definition | Cryptic name, internal use |
| `/learn` | Phase type in pipeline | Only meaningful post-pipeline |

---

## QRALPH Phase Coverage

| QRALPH Phase | Mapped To | Type |
|---|---|---|
| IDEATE | `qpipeline` thorough preset, ideate phase | Pipeline phase |
| PERSONA | Out of scope — persona selection handled by `tools/team-selector.py` at init time | Not a pipeline phase |
| CONCEPT_REVIEW | `qreview` agents | Agent spawn |
| PLAN | `qpipeline` plan phase | Pipeline phase |
| EXECUTE | `qpipeline` execute phase | Pipeline phase + agents |
| SIMPLIFY | Post-fix step in `qloop` | Integrated into fix |
| QUALITY_LOOP | `/qloop` | Standalone skill |
| POLISH | Fix step within `qloop` | Integrated |
| VERIFY | `verifier.md` agent, spawned by pipeline | Agent |
| DEMO | `qpipeline` demo phase with gate | Pipeline phase |
| DEPLOY | `qpipeline` deploy phase | Pipeline phase |
| SMOKE | `qpipeline` smoke phase | Pipeline phase |
| LEARN | `qpipeline` learn phase | Pipeline phase |
| COMPLETE | `qpipeline` complete phase | Pipeline phase |

All 14 phases covered. 3 as standalone skills, 3 as agent definitions, 8 as pipeline phases.

---

## Existing Skill Deduplication

| Existing Skill | This Plugin's Equivalent | Resolution |
|---|---|---|
| `superpowers:brainstorming` | ideate phase | Pipeline calls brainstorming skill if installed; falls back to own ideation agent |
| `qshortcuts-support:qidea` | ideate phase | Same — prefer existing if installed |
| `qshortcuts-learning:learn` | learn phase | Pipeline calls existing learn skill if installed |
| `qshortcuts-core:qfull-review` | `/qreview` | `/qreview` is the successor; migration documented |

No parallel capabilities shipped. Extend existing where possible.

---

## Test Strategy

```
tools/
  test_finding_parser.py    # Unit tests for P0-P3 taxonomy
  test_test_runner.py       # Tests for test discovery/execution
  test_team_selector.py     # Tests for agent selection
  test_loop_driver.py       # Integration: loop state machine
  test_pipeline_driver.py   # Integration: pipeline phases
  test_review_driver.py     # Integration: reviewer spawn + synthesis
agents/
  test_prompts/             # Known-input/expected-output for each agent
```

`make test-skills` runs all. Per-skill tests co-located.

---

## Build Order

### Phase 0 (parallel)
Shared tools — `finding-parser.py`, `test-runner.py`, `team-selector.py` + their tests.

### Phase 1 (parallel)
`/qreview` (skill + driver + agents) AND `/qpipeline` minimal preset (`review` preset only). Ships together so day-1 users get both standalone review AND pipeline.

### Phase 2
`/qloop` (skill + driver). Extends `/qpipeline` with `review-loop` phase type.

### Phase 3
Additional pipeline presets (`thorough`, `content`, `code`). Additional agents for non-review phases.

---

## Operational Details

### Concurrent Invocation (v2 enhancement)

Not yet implemented. Future: lightweight lock (`.qloop/session.lock` with PID) to warn when concurrent `/qloop` runs target the same artifact.

### Context Window Budgeting

All agent prompts include: "Read only files relevant to your review domain. Use Grep to find relevant sections rather than reading entire files. Budget: stay under 100K input tokens."

### Naming Convention

All commands use `q`-prefix per project convention (`qreview`, `qloop`, `qpipeline`). Avoids collision with built-in `/review` skill. All verb-oriented for consistency.

---

## Round 1 Review Summary

70 raw findings from 4 clean-context reviewers → 59 deduplicated (12 P0, 18 P1, 19 P2, 10 P3). All addressed in this v2 plan.

### Key Fixes Applied

| Theme | Finding Count | Resolution |
|---|---|---|
| Convergence criterion wrong | 4 reviewers flagged | Fixed: P0=0 AND P1=0 AND P2+P3 ≤ threshold (default 0) |
| Execution model mismatch | 3 reviewers flagged | Fixed: Python driver scripts, not skill-to-skill composition |
| Fix-ALL not enforced | 4 reviewers flagged | Fixed: Mandatory resolution checklist, no WONTFIX status |
| No deterministic tests in cycle | 3 reviewers flagged | Fixed: test-runner.py at every phase transition |
| Step-skipping undefended | 3 reviewers flagged | Fixed: Driver controls transitions, min 2 rounds, no --skip |
| No zero-config entry point | 2 reviewers flagged | Fixed: 3 commands total, /qpipeline review for zero-config |
| 12 skills cognitive overload | 2 reviewers flagged | Fixed: 3 user-facing, rest internal |
| Namespace collision | 2 reviewers flagged | Fixed: q-prefix on all commands |
| Max-rounds escape hatch | 2 reviewers flagged | Fixed: Exits as ESCALATED, blocks downstream |
| K-of-M suppresses findings | 2 reviewers flagged | Fixed: Dissent default, max-severity dedup, no vote-down |
