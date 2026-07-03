---
name: qpipeline
description: "This skill should be used when the user asks to \"run the full pipeline\", \"qpipeline\", \"end-to-end review\", \"thorough review\", \"qpipeline auto\", an autonomous build, or wants a composable multi-phase workflow. Presets: review (quick), thorough (full QRALPH-equivalent), content, code. `auto` = autonomous end-to-end SDLC Workflow. Custom phase composition supported."
version: 0.3.0
---

# /qpipeline -- Composable Multi-Phase Pipeline Orchestrator

## Purpose

Orchestrate end-to-end workflows by composing review primitives into phased pipelines. The pipeline driver (`tools/pipeline-driver.py`) IS the orchestrator -- it manages state, enforces phase ordering, validates compositional integrity, and controls transitions. This is NOT skill-to-skill composition. The driver owns the lifecycle.

Ship with four presets. Accept custom phase lists. Checkpoint at every boundary. Gate on human approval where required. Never skip a phase.

The presets above are the **gated, human-in-the-loop** pipeline (Python driver). `/qpipeline auto` is a **separate, autonomous** mode — see below.

## Autonomous mode: `/qpipeline auto`

When the user asks for `/qpipeline auto` (or "build this autonomously end-to-end"), run the **`pipeline-auto` ultracode Workflow** — NOT the Python driver. The driver exists to pause at human gates; `auto` is the opposite (no stopping). This mode drives a full SDLC from a one-line goal to a verified stop:

`requirements → design → separate-context TDD (per-slice worktrees, by wave) → serialized integration → unit/integration verify → stop-at-verify`

Every emitted artifact converges through the **same** engine that powers `/qloop` (run in-process per artifact), and every "need a human" moment routes through **`/qdecide` first** — a `decline` hard-stops, a `draft` on reversible-internal work proceeds-and-stages, and anything irreversible/external/spend is human-gated (qdecide can never authorize it). The whole run stays on a feature branch.

### Run it

Resolve the workflow script path (`js/` beside `tools/`):
- plugin: `<plugin>/js/pipeline-auto.workflow.js`
- fork: `~/.claude/ai-review-tools/js/pipeline-auto.workflow.js`

Invoke the **Workflow** tool with that `scriptPath` and:

```json
{
  "goal": "<the one-line goal to build>",
  "requirements": "requirements/current.md",
  "design": "DESIGN.md",
  "toolsDir": "<plugin>/tools  (or ~/.claude/ai-review-tools in the fork)",
  "threshold": 0,
  "maxRounds": 4,
  "maxParallel": 5
}
```

Optional args: `deployTarget` (declared, never inferred — see §6 of the design and the `auto prod` section below), `prodAutonomous: true` (opt-in prod deploy — set by `auto prod`), `smokeContract` (path to the cumulative smoke suite, default `smoke/prod.suite.json`), `stopAfter` (`requirements`|`design`|`tdd`|`integration`, for staged/bounded runs), `planOnly: true` (a zero-spend parser/plan check), and `team` (pre-resolved; otherwise phase 0 resolves it via `team-selector.py`). The Workflow streams per-phase progress via `log()` (watch with `/workflows`) and returns a `report` with each artifact's convergence outcome. On a hard-stop / human-gate it returns `{status:"halted", at, decision, report}` — surface the decision and stop.

**Return `status` values:** `verified` (no deployTarget — stopped at verify), `staged` (deployTarget given, staging deployed + smoked green, stopped before prod), `promoted` (`auto prod` — prod deployed + smoked green), `rolled-back` (prod smoke failed, auto-rollback restored prod), `hard-page` (prod smoke failed and a human must be paged — stateful target or rollback failed to restore), `halted` (a gate refused; see `decision`).

**This mutates the working tree** (it authors requirements/design and, in the TDD phase, builds code in git worktrees). Run it in the target project on a branch you're willing to have modified.

### `/qpipeline auto prod`

`/qpipeline auto prod` is the explicit opt-in that, after the verified stop, runs the **production tail**: `DEPLOY-PLAN (qloop'd) → staging deploy → staging smoke → guardrail gate → qdecide(irreversible) → prod publish → prod smoke → PROMOTE | auto-rollback → re-smoke → escalate/hard-page`. Invoke the Workflow with `prodAutonomous: true` plus a declared `deployTarget`. Plain `/qpipeline auto` (no `prodAutonomous`) never publishes to prod: with a `deployTarget` it staging-deploys + smokes then stops (`status: staged`); with no `deployTarget` it stops at verify (`status: verified`).

**`deployTarget` is DECLARED, never inferred** (auto-detect may only *suggest* commands):

```json
{
  "kind": "cloudflare-worker | vercel | npm | ...",
  "stagingCmd": "wrangler deploy --env staging",
  "prodCmd": "wrangler deploy --env production",
  "stagingUrl": "https://staging.example.dev",
  "prodUrl": "https://example.dev",
  "rollbackCmd": "wrangler rollback --env production",
  "stateful": false
}
```

- **`rollbackCmd` is mandatory for prod** — the guardrail gate REFUSES prod without a present, dry-validated rollback.
- **`stateful: true`** downgrades a failed-smoke recovery from auto-rollback to **hard-page-only** (code rollback can't undo DB/KV/R2 mutations).

**The guardrail gate** (`prod-tail.py deploy_gate`, surfaced in the scorecard) must be fully green before prod: every artifact 0 P0/P1, unit + integration green, staging smoke 100%, rollback present + dry-validated, prod smoke assertions reviewed up front, this feature added its new smoke checks, `prodAutonomous` set, and **qdecide ≠ decline** (a `decline` hard-blocks; qdecide can never *authorize* an irreversible deploy — H-010).

**The curated, cumulative prod smoke suite** (`smoke/prod.suite.json`, `smokeContract` arg) is ONE maintained, versioned artifact — a growing regression net, not per-run-ephemeral. **Every feature MUST append its checks** (the gate fails a feature that ships no smoke check for its new behavior). Post-deploy the FULL suite runs against prod via parallel Haiku fan-out (batched by `plan_smoke_batches`, target 200+ checks, sub-linear wall-clock). Any check fails → auto-rollback (stateless) or hard-page (stateful) → re-smoke to prove restored.

> **Validation status:** phases 0–2 (requirements → design → slice validation) are behaviorally verified end-to-end; the full inlined Workflow (incl. the phase 7–8 prod tail) parses/links in the sandbox and the prod-tail safety cores are unit-tested. Phases 3–8 (per-slice TDD worktrees, serialized integration, verify, deploy tail) are structurally complete and parser-verified but await a full end-to-end behavioral run before production reliance. **Always dry-run `auto prod` against a throwaway staging target first.**

### Scorecard (mandatory final step)

When the Workflow ends, run the deterministic scorecard against the run and present it verbatim (same as `/qloop` step 5):

```
python3 <tools>/scorecard.py --workflow <session>/workflows/<runId>.json
```

## Presets

### `review` (default)

Quick review cycle. Use when the artifact exists and needs a quality pass.

Phases: `test-gate` -> `review-loop` -> `verify`

### `thorough`

Full QRALPH-equivalent pipeline. Use for greenfield features or anything Travis wants buttoned up end-to-end.

Phases: `ideate` -> `plan` -> `execute` -> `review-loop` -> `test-gate` -> `verify` -> `demo`

### `content`

Content and documentation review. Use for articles, proposals, strategy docs.

Phases: `review-loop` -> `verify`

### `code`

Code with test emphasis. Use for implementation work where test coverage matters.

Phases: `review-loop` -> `test-gate` -> `verify`

## Phase Types

Execute each phase type as described. Do not improvise phase behavior.

### `ideate`

Brainstorm and refine the concept. Read the artifact (if provided) and requirements. Produce `IDEATION.md` with concept options, tradeoffs, and a recommendation. **Gate:** present options to the user; user confirms the concept before proceeding.

### `plan`

Create an implementation plan. Produce `PLAN.md` with numbered tasks, dependencies, and SP estimates. Each task must be independently executable. **Gate:** present the plan to the user; user confirms before proceeding.

### `execute`

Execute plan tasks. For each task in PLAN.md, perform the implementation. Record results per task. This phase MUST be followed by a review phase -- the driver enforces this via compositional integrity validation.

### `review`

Single-round multi-agent review. Execute the /qreview protocol as defined in `skills/qreview/SKILL.md`. Record the synthesis output as the phase result.

### `review-loop`

Iterative review-fix cycle. This is the core phase. Execute rounds of: review -> fix -> re-review until convergence (zero P0, zero P1) or the round limit (default 5) is reached. Each round:

1. Run multi-agent review (same protocol as `review` phase).
2. If converged, record convergence and advance.
3. If not converged, fix all findings at all severity levels (P0 through P3).
4. Re-review the fixed artifact.
5. If round limit reached without convergence, escalate to user.

Use `tools/loop-driver.py` for each review round. Track round count and finding trends in the phase result.

### `test-gate`

Run deterministic tests via `tools/test-runner.py`. Discover co-located tests for the artifact and execute them. **Hard gate:** all tests must pass. If any test fails, the pipeline blocks. Fix failures and re-run. Do not advance past this phase with failing tests.

### `verify`

Fresh-context acceptance verification. Spawn a verifier agent with NO knowledge of the review history. The verifier receives only the artifact, requirements, and a clean review prompt. The verifier produces an independent pass/fail assessment. If the verifier fails the artifact, return to the review-loop or escalate.

### `demo`

Present the completed work to the user. Show what changed, what was reviewed, what findings were addressed, and the final convergence status. **Gate:** user approves or provides feedback. Maximum 2 revision cycles -- if the user rejects twice, escalate rather than looping indefinitely.

### `deploy`

Pre-deployment checks. Validate that the artifact is in a deployable state: tests pass, no P0/P1 findings remain, all gates cleared. **Gate:** user confirms deployment.

### `smoke`

Live validation of the deployed artifact. Run the artifact in its production context and verify it produces correct output. Record evidence of success or failure. If smoke fails, roll back and return to the fix phase.

### `learn`

Extract learnings from the completed pipeline. Record what worked, what surprised, what the review caught that manual inspection would have missed. Store learnings for future pipeline runs.

## Pipeline Protocol

Follow these steps in order. Do not skip steps. Do not combine steps.

### Step 1: Initialize the Pipeline

Run `tools/pipeline-driver.py init` with the chosen preset (or custom phases), artifact path, and requirements path. The driver:
- Validates the phase list for compositional integrity
- Generates a project ID (NNN-slug from artifact name)
- Creates the state directory `.qpipeline/projects/{project_id}/`
- Returns the initial state with phase list and first action

### Step 2: Execute Phases

Call `tools/pipeline-driver.py next` to get the next action. The driver returns an action dict describing what to do:

- `{"action": "run_tests", "phase": "test-gate"}` -- Execute test-runner on the artifact.
- `{"action": "spawn_reviewers", "phase": "review"}` -- Run a single-round review via qreview protocol.
- `{"action": "run_loop", "phase": "review-loop"}` -- Run iterative review-fix cycles.
- `{"action": "execute_plan", "phase": "execute"}` -- Execute implementation tasks.
- `{"action": "spawn_verifier", "phase": "verify"}` -- Spawn a fresh-context verifier.
- `{"action": "gate", "phase": "...", "message": "..."}` -- Present a gate to the user and wait.
- `{"action": "complete", "summary": "..."}` -- Pipeline finished.

After completing each action, call `tools/pipeline-driver.py record-result` with the phase outcome, then call `next` again.

**Model tiering (Sonnet 5 by default).** Agent-spawning phases follow the same policy as `/qreview` and `/qloop`: default to **Sonnet 5**, escalate to **Opus** for high-stakes lenses (`security-reviewer`, `architecture-reviewer`) or complex work (change spans more than one file, needs more than two distinct tool-execution types, or exceeds ~20% of context).
- `spawn_reviewers` / `run_loop` — pass the complexity flags (`--files`, `--tool-types`) into the underlying `review-driver.py` / `loop-driver.py init`, and spawn each reviewer with its resolved `model` (surfaced in the team composition / `models` array).
- `spawn_verifier` — a fresh-context verifier is a reviewer: default Sonnet 5, escalate to Opus by the same rule.
- `execute_plan` — implementation typically touches multiple files, so it usually runs on **Opus**; a single-file, low-tool task stays on Sonnet 5.

### Step 3: Handle Gates

Gates use a two-call protocol:
1. `next` returns `{"action": "gate", ...}` -- present the gate message to the user.
2. User responds with approval or feedback.
3. Call `next --confirm` to advance past the gate.

If the user rejects at a gate, record the feedback and handle per phase type (demo allows 2 revision cycles, others escalate).

### Step 4: Pipeline Completion

When `next` returns `{"action": "complete"}`, the pipeline is done. Present the summary to the user.

Then ALWAYS emit the deterministic scorecard as the final output (pure, reproducible, no LLM):

```
tools/scorecard.py --state <the review-loop's .qloop/state.json (or the phase state richest in findings)> --transcript <this session's transcript JSONL>
```

Point `--state` at the sub-protocol state that carries the findings (usually the review-loop's `.qloop/state.json`; a single `review` phase writes `.qreview/state.json`). The scorecard reports **Process**, **Issues Found** (by severity), **Token Cost** (per-model tokens + USD, plus total), and **Model Execution Time** (sum of per-request durations — model execution time, **not** wall clock). Token/time cover this session's model activity; scope with `--since <ISO>` and override rates with `--pricing PATH`.

## Compositional Integrity

The driver validates every phase list at init time. Rules:

- Any pipeline containing `execute` or `fix` MUST also contain `review-loop`. Code changes without review are not permitted.
- The driver rejects invalid compositions with an error message explaining what is missing.
- There is no `--skip` flag. Phase skipping is not supported at any level.

## Step-Skip Prevention

The driver tracks phase execution in state. Every mandatory phase must record a result before the driver advances to the next phase. The AI cannot bypass a phase -- the driver controls transitions by checking state before returning the next action.

## Checkpointing

The driver auto-checkpoints at every phase transition. The checkpoint includes:
- Current artifact state
- All findings from all rounds
- Fix history
- Test results
- Round count and convergence trend
- Gate decisions

Resume a checkpointed pipeline: `/qpipeline resume <project-id>`

## Status

Check pipeline status: `/qpipeline status`

Returns current phase, phase index, total phases, findings summary, and convergence trend.

## Reset

Clear pipeline state: `/qpipeline reset`

Removes all state for the current project.

## Tools Reference

All tools live in the `tools/` directory relative to the plugin root:

- **`tools/pipeline-driver.py`** -- Pipeline state machine. Manages `.qpipeline/projects/`, validates phase composition, controls transitions, auto-checkpoints.
- **`tools/review-driver.py`** -- Single-round review state machine for /qreview. Used by `review` phase.
- **`tools/loop-driver.py`** -- Iterative review-fix loop state machine for /qloop. Used by `review-loop` phase.
- **`tools/finding-parser.py`** -- Finding validation, deduplication, convergence, formatting. Pure functions.
- **`tools/test-runner.py`** -- Test discovery and execution. Used by `test-gate` phase.
- **`tools/team-selector.py`** -- Domain classification and team selection. Used during review phases.

## Key Rules

### No Skip Flag

There is no mechanism to skip a phase. The driver does not accept a `--skip` parameter. If a phase is in the pipeline, it executes.

### Compositional Integrity is Enforced at Init

Invalid phase compositions are rejected before any work begins. The driver does not allow creation of a pipeline that violates integrity rules.

### Gates Block Until Confirmed

Gate phases return the gate action repeatedly until `--confirm` is passed. There is no timeout. There is no auto-approve.

### Checkpoints are Automatic

Every phase transition triggers a checkpoint write. The user does not need to request checkpoints. Resume always picks up from the last completed phase.

### Phase Results are Required

The driver will not advance to the next phase until the current phase has a recorded result. Calling `next` without recording a result for the current phase returns the same action again.
