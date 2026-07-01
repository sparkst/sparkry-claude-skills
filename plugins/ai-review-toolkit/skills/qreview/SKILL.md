---
name: qreview
description: "This skill should be used when the user asks to \"review an artifact\", \"get multiple perspectives on\", \"multi-agent review\", \"qreview\", or wants N independent reviewers to evaluate any output (code, content, strategy, design) against requirements. Spawns 2-5 clean-context agents in parallel with max-severity deduplication."
version: 0.2.0
---

# /qreview -- Multi-Agent Artifact Review

Single-pass, multi-perspective review: N clean-context reviewers evaluate an
artifact against its requirements, in parallel, each blind to the others.
Findings are validated, deduplicated by max-severity, and sorted P0-first.
Diagnose-only — `/qreview` never edits the artifact (use `/qloop` to converge).

**This skill runs via the ai-review-toolkit ultracode Workflow**
(`review-loop.workflow.js` with `rounds: 1`). The Workflow owns the deterministic
loop — parallel reviewer fan-out with resolved models, JS synthesis/dedup, and
convergence checking. Invoking `/qreview` **is** the explicit opt-in to run that
Workflow. The deterministic adjudication is the Python library's JS port, drift-
locked against it in CI, so verdicts match the Python oracle exactly.

## Protocol

Follow in order.

### 1. Identify artifact + requirements

Accept a file path or inline content for each. Write inline content to a temp
file so agents can `Read` it. If no requirements exist, ask the user what the
artifact must accomplish and record that as the requirements file.

### 2. Resolve the review team (deterministic, Python)

Run the team selector and capture the resolved team (each reviewer carries its
tiered `model`). From the plugin, tools are under `tools/`; in the local fork
they are at `~/.claude/ai-review-tools/`.

```
python3 <tools>/team-selector.py "<short artifact description>" \
  --artifact <artifact_path> --json \
  --files <N> --tool-types <N> --context-window 200000
```

- `--files N` — files the change spans (escalates every reviewer to Opus if `> 1`).
- `--tool-types N` — distinct tool-execution types the review needs (escalates if `> 2`).
- The artifact's byte size drives the ">20% of context" rule automatically.

Parse the JSON `team` array — objects of `{name, model, review_lens, ...}`. This
is passed straight into the Workflow; **do not re-tier or override models by
hand** — the escalation policy already ran.

### 3. Run the review Workflow

Resolve the workflow script path (it sits in `js/` beside `tools/`):
- plugin: `<plugin>/js/review-loop.workflow.js`
- fork: `~/.claude/ai-review-tools/js/review-loop.workflow.js`

Invoke the **Workflow** tool with that `scriptPath` and:

```json
{
  "artifact": "<artifact_path>",
  "requirements": "<requirements_path>",
  "team": <team array from step 2>,
  "rounds": 1,
  "threshold": 0
}
```

`rounds: 1` means single-pass, diagnose-only — the workflow reviews and
synthesizes but runs no fixer (it returns an `escalated` outcome listing any
unresolved P0/P1, which for `/qreview` is simply "here is what to fix"). Capture
the **Run ID** and the `workflows/<runId>.json` path from the tool result.

### 4. Present findings

The Workflow returns `{ outcome, rounds, final_findings, final_counts, history }`.
Present `final_findings` sorted by severity (P0 first). For each: id + severity,
title, requirement, finding, recommendation, evidence (file:line), sources
(which reviewers flagged it). Then the convergence line: **converged (safe to
ship)** = zero P0, zero P1, low-severity within threshold; otherwise state how
many P0/P1 remain.

### 5. Scorecard (mandatory)

Always end by running the deterministic scorecard against the run and showing it
verbatim (pure, reproducible, no LLM):

```
python3 <tools>/scorecard.py --workflow <session>/workflows/<runId>.json
```

It reports Process, Issues Found, Token Cost (per-model USD), and Model
Execution Time (per-agent wall-clock rolled per model + the workflow wall-clock
total).

## Severity taxonomy

| Severity | Meaning | Action |
|----------|---------|--------|
| P0 | Blocks shipping (correctness, security, data loss, requirement violation). | Fix before any release. |
| P1 | Must fix before v1 (quality, error handling, incomplete coverage). | Fix before feature-complete. |
| P2 | Should fix (code smell, suboptimal pattern, minor UX, doc gap). | Next iteration. |
| P3 | Nice to have (style, optional optimization, cosmetic). | If time permits. |

## Key rules (enforced in code, not prose)

- **Dissent is default / max-severity wins.** One reviewer's P0 is never
  downgraded by majority — `deduplicateFindings` merges by normalized title and
  keeps the max severity.
- **Clean context per reviewer.** Each runs in a fresh agent, blind to the others
  and to the team composition.
- **Pre-existing issues are in-scope.** Reviewers do not self-censor as "out of
  scope."

## Tools

- **`js/review-loop.workflow.js`** — the ultracode Workflow (the loop engine).
  Generated from `js/adjudication.mjs` + `js/prompts.mjs`; do not hand-edit.
- **`tools/team-selector.py`** — deterministic domain classification + team
  selection + model tiering (Python oracle).
- **`tools/scorecard.py`** — deterministic end-of-run scorecard.

## Fallback

If the Workflow tool is unavailable, use the legacy hand-driven Python-driver
protocol in [`driver-fallback.md`](./driver-fallback.md) (retained for one
release; removed when the drivers are deleted in step 7).
