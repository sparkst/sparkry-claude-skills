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
