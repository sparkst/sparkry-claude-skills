---
name: qloop
description: "This skill should be used when the user asks to \"review and fix\", \"iterative review\", \"review loop\", \"qloop\", \"fix all issues\", or wants an artifact reviewed, all issues fixed at all priorities, and re-reviewed until convergence. Enforces: minimum 2 rounds, fix-ALL gate, clean-context re-review, deterministic tests at every step."
version: 0.2.0
---

# /qloop -- Iterative Review-Fix-Verify Loop

Convergence loop: review → fix ALL findings in place → clean-context re-review,
repeated until the artifact converges (zero P0, zero P1, low-severity within
threshold) or the loop hard-stops. `/qloop` is `/qreview` plus a fixer and the
enforcement gates.

**This skill runs via the ai-review-toolkit ultracode Workflow**
(`review-loop.workflow.js`, run until-converged). The Workflow — not prose — owns
the state machine: parallel reviewers with resolved models, JS synthesis/dedup,
the fix-ALL gate, the min-2-rounds floor, stuck detection, and max-rounds
escalation. A single in-place fixer per round edits the artifact so the next
round's reviewers see the changes. Invoking `/qloop` **is** the explicit opt-in
to run that Workflow.

## Protocol

Follow in order.

### 1. Identify artifact + requirements

Accept a file path or inline content for each. Write inline content to a temp
file. If no requirements exist, ask the user what the artifact must accomplish
and record that as the requirements file.

### 2. Resolve the review team (deterministic, Python)

Same as `/qreview` step 2 — run the team selector and capture the resolved team
(models already tiered). Tools are under `tools/` in the plugin, or
`~/.claude/ai-review-tools/` in the local fork.

```
python3 <tools>/team-selector.py "<short artifact description>" \
  --artifact <artifact_path> --json \
  --files <N> --tool-types <N> --context-window 200000
```

Parse the JSON `team` array. Pass it straight into the Workflow — **do not
re-tier or override models by hand.**

### 3. Run the convergence Workflow

Resolve the workflow script path (`js/` beside `tools/`):
- plugin: `<plugin>/js/review-loop.workflow.js`
- fork: `~/.claude/ai-review-tools/js/review-loop.workflow.js`

Invoke the **Workflow** tool with that `scriptPath` and:

```json
{
  "artifact": "<artifact_path>",
  "requirements": "<requirements_path>",
  "team": <team array from step 2>,
  "threshold": 0,
  "maxRounds": 5
}
```

Omit `rounds` (or set > 1) so the loop runs until-converged. The Workflow runs
unattended to convergence, streaming per-round progress via `log()` (watchable
with `/workflows`). It hard-stops — max-rounds or stuck detection — and returns
the unresolved findings rather than spinning. Capture the **Run ID** and the
`workflows/<runId>.json` path from the tool result.

**The fixer edits files in place.** There is no worktree isolation — that is
deliberate, so each round's fixes persist for the next round's reviewers. Only
run `/qloop` on an artifact whose current state you are willing to have modified
(commit or stash first if you want a clean rollback point).

### 4. Present the outcome

The Workflow returns `{ outcome, rounds, final_findings, final_counts, history }`:
- `outcome.status === "converged"` — present the convergence summary and round count.
- `outcome.status === "escalated"` — present `outcome.reason` and `outcome.unresolved`
  (P0/P1 findings), then ask the user to choose: continue (raise `maxRounds` and
  re-run), accept current state, or abandon. Escalation happens on max-rounds,
  stuck detection (identical P0/P1 across two rounds), or a failed fix-ALL gate.

Show `history` (findings-per-round) so the convergence trajectory is visible.

### 5. Scorecard (mandatory final step)

Whenever the loop ends (converged OR escalated), run the deterministic scorecard
against the run and present it verbatim:

```
python3 <tools>/scorecard.py --workflow <session>/workflows/<runId>.json
```

Four sections in order: **Process**, **Issues Found**, **Token Cost** (per-model
USD), **Model Execution Time** (per-agent wall-clock rolled per model + the
workflow wall-clock total). Pass `--pricing PATH` to override USD rates.

## Hard rules (enforced in `review-loop.workflow.js`, not prose)

- **Minimum 2 rounds.** Round 1 finds; round 2 verifies fixes and catches
  regressions. The loop never reports `converged` before the floor.
- **Fix-ALL gate on significant findings.** Every P0/P1 — plus any P2/P3 a
  reviewer flags `significance:true` or that recurs across rounds — needs a
  `FIXED`/`ESCALATED` resolution with evidence (`checkFixCompleteness`). No
  WONTFIX/DEFERRED/OUT_OF_SCOPE. A failed gate escalates.
- **Trivial P2/P3 are spot-fixed, not looped.** First-seen, unflagged cosmetic
  nits get a cheap Haiku spot-fix + spot-check each round — they're still
  addressed, but they don't block convergence or reset the loop. Convergence is
  reached when the *significant* set is clear (P0/P1 always count as significant,
  so they stay 0-to-ship).
- **Max rounds → escalated, never converged.** A terminal state that blocks
  downstream work until the user decides.
- **Stuck detection.** Identical P0/P1 findings across two consecutive rounds
  auto-escalate — two failed fix attempts on the same issue means the approach
  is wrong.
- **Max-severity wins / clean context per reviewer per round / pre-existing
  issues are in-scope** — same as `/qreview`, enforced by the shared JS
  adjudication (drift-locked against the Python oracle in CI).

## Tools

- **`js/review-loop.workflow.js`** — the ultracode Workflow (the loop engine).
  Generated from `js/adjudication.mjs` + `js/prompts.mjs`; do not hand-edit.
- **`tools/team-selector.py`** — deterministic team selection + model tiering.
- **`tools/scorecard.py`** — deterministic end-of-run scorecard.

## Fallback

If the Workflow tool is unavailable, use the legacy hand-driven Python-driver
protocol in [`driver-fallback.md`](./driver-fallback.md) (retained for one
release; removed when the drivers are deleted in step 7).
