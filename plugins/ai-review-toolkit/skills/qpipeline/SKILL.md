---
name: qpipeline
description: "This skill should be used when the user asks to \"run the full pipeline\", \"qpipeline\", \"end-to-end review\", \"thorough review\", or wants a composable multi-phase workflow. Presets: review (quick), thorough (full QRALPH-equivalent), content, code. Custom phase composition supported."
version: 0.1.0
---

# /qpipeline -- Composable Multi-Phase Pipeline Orchestrator

## Purpose

Orchestrate end-to-end workflows by composing review primitives into phased pipelines. The pipeline driver (`tools/pipeline-driver.py`) IS the orchestrator -- it manages state, enforces phase ordering, validates compositional integrity, and controls transitions. This is NOT skill-to-skill composition. The driver owns the lifecycle.

Ship with four presets. Accept custom phase lists. Checkpoint at every boundary. Gate on human approval where required. Never skip a phase.

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

### Step 3: Handle Gates

Gates use a two-call protocol:
1. `next` returns `{"action": "gate", ...}` -- present the gate message to the user.
2. User responds with approval or feedback.
3. Call `next --confirm` to advance past the gate.

If the user rejects at a gate, record the feedback and handle per phase type (demo allows 2 revision cycles, others escalate).

### Step 4: Pipeline Completion

When `next` returns `{"action": "complete"}`, the pipeline is done. Present the summary to the user.

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
