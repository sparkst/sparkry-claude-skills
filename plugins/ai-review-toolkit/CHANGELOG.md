# Changelog — ai-review-toolkit

## 1.2.0

### Changed
- **`/qreview` and `/qloop` now run on the ultracode Workflow engine.** Both
  SKILLs are thin wrappers that resolve the review team via `team-selector.py`
  (deterministic model tiering, unchanged) and invoke `js/review-loop.workflow.js`
  — one Workflow script that owns parallel reviewer fan-out, JS synthesis/dedup,
  the fix-ALL gate, the min-2-rounds floor, stuck detection, and max-rounds
  escalation. `/qreview` = `rounds:1` (diagnose-only); `/qloop` = until-converged
  with a single in-place fixer per round. Invoking the skill is the explicit
  opt-in to run the Workflow.
- The deterministic adjudication is now the JS port (`js/adjudication.mjs`),
  drift-locked byte-for-byte against the Python oracle in CI; `scorecard.py`
  reads Workflow runs via `--workflow`.

### Deprecated
- The hand-driven Python drivers (`review-driver.py`, `loop-driver.py`) are
  retained for one release as a fallback (`skills/*/driver-fallback.md`) and
  will be removed once the Workflow path is proven (step 7).

## 1.1.0

### Added
- **Reviewer model tiering (Sonnet 5 default, deterministic Opus escalation).**
  `team-selector.py` now resolves each reviewer's model from a `Complexity`
  signal. Sonnet 5 is the default; a reviewer escalates to Opus when its lens
  is high-stakes (`security-reviewer`, `architecture-reviewer`) or the change
  is complex — spans more than one file, needs more than two distinct
  tool-execution types, or exceeds 20% of context at start.
- **`scorecard.py` — deterministic end-of-run report.** Pure aggregation over
  the run's `state.json` plus the session transcript JSONL. Reports four
  sections: Process (per-step status), Issues Found (by severity), Token Cost
  (per-model tokens + USD via an overridable pricing table), and Model
  Execution Time (sum of per-request durations — model execution time, not
  wall clock).

### Changed
- `review-driver.py init` and `loop-driver.py init` accept `--files`,
  `--tool-types`, and `--context-window` to feed the tiering policy; the
  resolved per-reviewer model is persisted in the team composition.
- `loop-driver.py next` now returns a `models` array parallel to `prompts` in
  the `spawn_reviewers` action so the orchestrator spawns each reviewer on the
  right model.
- Default catalog reviewers now base on `sonnet` (previously `haiku` for
  ux/code-quality); escalation lifts to `opus` where warranted.
- `qreview` / `qloop` / `qpipeline` SKILLs instruct spawning each
  reviewer/fixer with its resolved `model` and always end with the scorecard.
