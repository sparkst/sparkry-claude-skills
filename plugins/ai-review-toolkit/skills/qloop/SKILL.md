---
name: qloop
description: "This skill should be used when the user asks to \"review and fix\", \"iterative review\", \"review loop\", \"qloop\", \"fix all issues\", or wants an artifact reviewed, all issues fixed at all priorities, and re-reviewed until convergence. Enforces: minimum 2 rounds, fix-ALL gate, clean-context re-review, deterministic tests at every step."
version: 0.1.0
---

# /qloop -- Iterative Review-Fix-Verify Loop

## Purpose

Orchestrate multiple rounds of multi-agent review, fix-all, and clean-context re-review until the artifact converges (zero P0, zero P1, low-severity within threshold). Every round spawns fresh reviewer agents with no memory of prior rounds. Every fix cycle must address ALL findings at ALL priorities -- no WONTFIX, no DEFERRED, no OUT_OF_SCOPE. If an issue is genuinely unfixable, escalate to the user instead of skipping it.

This skill wraps the single-round `/qreview` protocol into a convergence loop with hard enforcement gates. The loop driver (`tools/loop-driver.py`) is the state machine -- it decides what happens next, not the instructions. The minimum is 2 rounds. The maximum is configurable (default 5). Reaching max rounds without convergence produces an ESCALATED status that blocks downstream work.

## The Core Loop

Follow these steps in order. Do not skip steps. Do not combine steps. The loop driver controls transitions.

### Step 1: Initialize

Run `tools/loop-driver.py init` with the artifact path, requirements path, and optional overrides for reviewer count, convergence threshold, and max rounds. This:

- Creates `.qloop/state.json` with full loop configuration
- Runs `tools/team-selector.py` to select the optimal review team based on artifact domains
- Sets `current_round = 1` and `status = "initialized"`
- Returns the initial state including team composition

Inspect the team. If coverage is wrong, re-init with different parameters.

### Step 2: Run Deterministic Tests

Run `tools/loop-driver.py next` to get the next action. On a fresh round, this returns `{"action": "run_tests"}`.

Execute `tools/test-runner.py` against the artifact. Test failures are auto-classified as findings:
- **P0 (regression)**: a test that passed in a prior round now fails (round > 1)
- **P1 (new failure)**: any test failure in the first round or first-time discovery

Record test results via `tools/loop-driver.py record-tests --round N --results-file PATH`. This transitions the round from `initialized` to `tests_done`. **This step is mandatory** — the state machine will not advance to reviewer spawning until test results are recorded. If tests produce findings, they feed into the review synthesis.

### Step 3: Spawn Reviewer Agents (Round N)

After tests, `tools/loop-driver.py next` returns `{"action": "spawn_reviewers", "prompts": [...]}`.

For each reviewer on the team, spawn a subagent using the Agent tool. All reviewers run in parallel.

**Round 1 reviewers receive ONLY:**
1. The artifact content (full text)
2. The requirements (full text)
3. Test results summary (pass/fail counts and failure details)
4. Their specific review lens
5. The finding output schema

**Round 2+ reviewers receive ALL of the above PLUS:**
6. All findings from the previous round with fix recommendations
7. A diff or change summary showing what was modified since last round
8. Explicit instruction to verify prior fixes AND look for new issues introduced by fixes

Each reviewer operates in a fresh Agent context. No reviewer sees another reviewer's output. No reviewer sees the team composition. The reviewer prompts are provided in the `prompts` array of the `spawn_reviewers` action dict returned by `tools/loop-driver.py next`.

Instruct each reviewer to output findings as a JSON array of finding objects.

### Step 4: Collect and Synthesize Findings

As each reviewer completes, record their findings via `tools/loop-driver.py record-review --round N --reviewer INDEX --findings-file PATH`.

After all reviewers for the round have reported, `tools/loop-driver.py next` triggers synthesis via `tools/finding-parser.py synthesize_findings`. This validates, deduplicates by normalized title (max-severity wins), and sorts P0-first. The synthesis result is stored in the round's state.

Present the synthesized findings to the user sorted by severity.

### Step 5: Fix ALL Findings

After synthesis, `tools/loop-driver.py next` returns `{"action": "spawn_fixer", "prompt": "..."}`.

Spawn a fixer agent with the full synthesized finding list. The fixer prompt is provided in the `prompt` field of the `spawn_fixer` action dict. It includes:
- Every finding at every severity level (P0 through P3)
- The artifact content
- The requirements
- The test results
- Explicit instruction: every finding must be addressed with status FIXED and evidence of the fix

The fixer produces a resolution checklist. Each entry must include:
- `finding_id`: which finding this resolves
- `status`: MUST be "FIXED" -- no WONTFIX, DEFERRED, or OUT_OF_SCOPE allowed
- `evidence`: what changed and where (file:line for code, section:quote for content)
- `description`: brief explanation of the fix

If the fixer determines a finding is genuinely unfixable (e.g., requires external dependency change, architectural constraint, user decision), it must set status to "ESCALATED" with justification. The loop driver treats ESCALATED findings as requiring user input -- it pauses and asks the user to decide.

### Step 6: Fix-ALL Enforcement Gate

After receiving the fixer's resolution checklist, run `tools/loop-driver.py record-fixes --round N --resolutions-file PATH`.

The loop driver runs `check_fix_completeness` which validates:
- Every finding from the round has a corresponding resolution entry
- No resolution has a missing or empty `finding_id`
- No resolution uses WONTFIX, DEFERRED, or OUT_OF_SCOPE status

If completeness check fails, `tools/loop-driver.py next` returns `{"action": "validate_fixes", "required_findings": [...]}`. The fixer must address the listed finding IDs before the loop can advance. Re-run the fixer with the missing findings, then call `record-fixes` again. Do not proceed to re-review with unaddressed findings.

If any resolutions have status ESCALATED, `tools/loop-driver.py next` returns `{"action": "escalation_review", "escalated_resolutions": [...]}`. Present these to the user with the fixer's justification. The user can either:
- Accept the escalations: run `tools/loop-driver.py next --confirm` to advance past the gate
- Override: have the fixer re-resolve the findings with status FIXED, then call `record-fixes` again

After fixes are validated (and any escalations resolved), run `tools/test-runner.py` again. Any new test failure re-enters the fix cycle -- the fixer must fix the regression before re-review begins.

### Step 7: Re-Review (Round N+1)

After fixes pass the completeness gate and tests pass, `tools/loop-driver.py next` advances to the next round and returns `{"action": "spawn_reviewers", "prompts": [...]}`.

Spawn the SAME team of reviewers as round 1, but each in a FRESH Agent context. Round 2+ reviewer prompts include prior findings and fix summaries so reviewers can verify fixes and detect new issues.

Repeat Steps 3-6 for each subsequent round.

### Step 8: Convergence Check

After each round's synthesis, `tools/loop-driver.py next` checks convergence via `tools/finding-parser.py check_convergence`:
- **Converged**: P0 = 0 AND P1 = 0 AND (P2 + P3) <= threshold (default 0)
- **Not converged**: continue to next fix-review cycle

If converged AND `current_round >= min_rounds` (hard minimum of 2), the loop returns `{"action": "converged", "summary": "..."}`. Present the final summary to the user.

If `current_round >= max_rounds` and not converged, the loop returns `{"action": "escalated", "reason": "...", "unresolved": [...]}`. Present the unresolved findings and ask the user to choose: continue (raise max_rounds), accept current state, or abandon.

### Step 9: Stuck Detection

If the same P0/P1 findings persist across 2 consecutive fix-review cycles with zero improvement (same count, same titles), the loop auto-escalates. This prevents infinite loops where fixes fail to address root causes.

The escalation message includes:
- The stuck findings with their persistence count
- The fix attempts from both rounds
- A recommendation to the user (manual fix, architectural change, or accept)

## Hard Rules

### Minimum 2 Rounds -- Enforced by loop-driver.py

Round 1 always finds things. Round 2 verifies fixes and catches regressions. Even if round 1 finds zero issues (unlikely), round 2 still runs. This is enforced in `tools/loop-driver.py next_action` -- the state machine refuses to transition to "converged" before `current_round >= min_rounds`. This is not a suggestion.

### Max Rounds Produces ESCALATED, Never CONVERGED

Reaching `max_rounds` without convergence sets status to "escalated". This is a terminal state that blocks downstream. The user must explicitly choose to continue, accept, or abandon. The loop driver never silently declares convergence when findings remain.

### Fix-ALL is Literal

Every finding at every priority must have a resolution. P3 style nits get fixed, not waved away. The only escape hatch is ESCALATED (requires user decision). This prevents the common failure mode where "low priority" issues accumulate across rounds and never get addressed.

### Prior Findings are Mandatory Input to Re-Review

Round 2+ reviewers must receive the findings from round N-1 with the corresponding fix resolutions. This lets reviewers verify that fixes actually address the reported issues rather than just making changes. The `tools/loop-driver.py next` action dict automatically includes prior-round context in the `prompts` array for round > 1.

### Pre-Existing Failures are In-Scope

Per Rule R7: "we are the dev working on it now." If the artifact has a pre-existing bug, broken test, or quality issue, it is a finding. The user decides what to fix -- the reviewers do not self-censor.

### Clean Context Per Reviewer Per Round

Every reviewer in every round gets a fresh Agent spawn. No reviewer carries memory from a prior round. No reviewer sees another reviewer's output within the same round. This prevents anchoring bias and ensures each round is an independent evaluation.

### Auto-Backtrack on Stuck

If the same P0/P1 findings appear in rounds N and N-1 with zero severity reduction, the loop escalates immediately rather than burning another round. Two consecutive failed fix attempts on the same issue means the fix approach is wrong -- automation cannot solve it.

## Type-Agnostic Adaptation

The loop works on any artifact type. The tools handle adaptation:

- **Code artifacts**: `tools/test-runner.py` discovers pytest/vitest/Makefile tests. Evidence format is `file:line`. Fixer produces code changes.
- **Content/documents**: `tools/test-runner.py` discovers rubric files (`.rubric.md`, `.rubric.json`). Evidence format is `section:quote`. Fixer produces content edits.
- **Strategy/design**: `tools/test-runner.py` discovers structured criteria. Evidence format is `section:quote`. Fixer produces document revisions.

The finding schema, severity taxonomy, deduplication logic, and convergence check are identical regardless of artifact type.

## Severity Taxonomy

| Severity | Meaning | Action |
|----------|---------|--------|
| P0 | Blocks shipping. Correctness failure, security vulnerability, data loss risk, requirement violation. | Must fix immediately. |
| P1 | Must fix before v1. Significant quality issue, missing error handling, incomplete requirement coverage. | Fix before declaring complete. |
| P2 | Should fix. Code smell, suboptimal pattern, minor UX issue, documentation gap. | Fix in this loop. |
| P3 | Nice to have. Style nit, optional optimization, cosmetic improvement. | Fix in this loop. |

Note: In qloop, ALL severities are fixed in every round. The taxonomy determines priority order within the fixer, not whether the issue gets addressed.

## Tools Reference

All tools live in the `tools/` directory relative to the plugin root:

- **`tools/loop-driver.py`** -- State machine driver for the iterative loop. Manages `.qloop/state.json`, enforces min/max rounds, generates round-aware reviewer and fixer prompts, validates fix completeness, checks convergence, detects stuck loops.
- **`tools/finding-parser.py`** -- Validates, deduplicates (max-severity), counts, checks convergence, synthesizes, and formats findings. Pure functions, no side effects.
- **`tools/test-runner.py`** -- Discovers co-located tests (pytest, vitest, Makefile, scripts, rubrics) and executes them. Converts failures to findings.
- **`tools/team-selector.py`** -- Classifies artifact domains via keyword/pattern matching and selects the optimal review team from an agent catalog.

## State Management

Loop state lives in `.qloop/state.json` relative to the working directory. The state file tracks:
- Artifact and requirements paths
- Selected team composition
- Convergence threshold and round limits
- Per-round: findings, test results, fix resolutions, synthesis, phase
- Overall loop status (initialized, reviewing, fixing, converged, escalated)

Use `tools/loop-driver.py status` to inspect current state at any time. Use `tools/loop-driver.py reset` to clear state and start fresh.
