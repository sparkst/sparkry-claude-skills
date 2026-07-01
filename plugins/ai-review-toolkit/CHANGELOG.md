# Changelog — ai-review-toolkit

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
