# ai-review-toolkit — JS adjudication library

JavaScript port of the deterministic review hot-loop. The future
`review-loop.workflow.js` (ultracode Workflow, step 4 of the refactor) imports
these modules so orchestration — fan-out, the convergence loop, the fix-ALL gate,
model tiering — stays deterministic in-code rather than relying on an LLM agent.

## Modules

- **`adjudication.mjs`** — the 7 drift-locked adjudication functions:
  `validateFinding`, `deduplicateFindings`, `countBySeverity`, `checkConvergence`,
  `synthesizeFindings`, `resolveReviewerModel`, `checkFixCompleteness`.
- **`prompts.mjs`** — reviewer/fixer prompt construction:
  `formatFindings`, `buildReviewerPrompt`, `buildFixerPrompt` (pure; the workflow
  reads files and passes content in).

## The Workflow script

- **`review-loop.workflow.js`** — the ultracode Workflow that runs the
  review→synthesize→gate→fix convergence loop (qreview = `rounds:1`, qloop =
  until-converged). **Generated, not hand-edited.**
- **`review-loop.template.js`** — the orchestration source (meta + loop) with a
  `// @@INLINE@@` marker.
- **`build-workflow.mjs`** — assembles `review-loop.workflow.js` by inlining
  `adjudication.mjs` + `prompts.mjs` into the template (`--write`/`--check`).

The Workflow sandbox can't `import` sibling modules at runtime, so the
deterministic JS is **inlined** into one self-contained script. `adjudication.mjs`
stays the single, node-tested source of truth; `build-workflow.test.mjs` runs
`--check` in CI to forbid drift. To change the loop's adjudication, edit
`adjudication.mjs`/`prompts.mjs` (or the template) then `node build-workflow.mjs --write`.

Design constraints the workflow works within:
- **Team via `args`.** `team-selector.py` stays Python (the oracle), so the skill
  resolves reviewer models upstream and passes `args.team` in.
- **Path-based prompts.** The sandboxed script can't read files; reviewer/fixer
  agents `Read`/`Edit` the artifact themselves. Prior-round findings (held in
  memory by the script) are still embedded via `formatFindings`.
- **In-place fixer, no worktree isolation.** Fixes persist so the next round's
  reviewers see them.
- Loop semantics (min-2-rounds floor, fix-ALL gate, stuck detection, max-rounds
  escalation) live in `loop-engine.mjs` itself now -- the Python `loop-driver.py`
  state machine they used to mirror has been retired.

## Drift lock (Python is the oracle)

The Python in `../tools/` remains the source of truth. Each JS module is validated
byte-for-byte against a committed golden corpus generated from the Python oracle:

| JS module          | Golden corpus                      | Python lock                  | JS lock              |
| ------------------ | ---------------------------------- | ---------------------------- | -------------------- |
| `adjudication.mjs` | `../tools/fixtures/adjudication.json` | `test_golden_parity.py`   | `adjudication.test.mjs` |
| `prompts.mjs`      | `../tools/fixtures/prompts.json`      | `test_prompt_parity.py`   | `prompts.test.mjs`      |

Any divergence on either side fails CI. To regenerate after an intentional Python
change: `python3 ../tools/gen-golden-fixtures.py --write` and/or
`python3 ../tools/gen-prompt-fixtures.py --write`, then commit.

## Running the tests

```sh
node --test 'plugins/ai-review-toolkit/js/**/*.test.mjs'
```

Requires Node ≥ 21 (native test runner + glob). No dependencies, no framework.
