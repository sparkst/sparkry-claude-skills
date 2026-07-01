# Requirements Lock — ai-review-toolkit tiered models + scorecard

Snapshot for the "Option 3" model-tiering + deterministic scorecard task.

## REQ-101: Sonnet-default reviewer model with deterministic Opus escalation
- Sonnet 5 is the default model for reviewer subagents.
- A reviewer escalates to Opus when ANY of:
  - its lens is **security** or **architecture** (reviewer name `security-reviewer` or `architecture-reviewer`), OR
  - the change spans **more than one file** (`file_count > 1`), OR
  - the review needs **more than two distinct tool-execution types** (`tool_types > 2`), OR
  - the artifact consumes **more than 20% of context** at start (`context_fraction > 0.20`).
- Acceptance: `resolve_reviewer_model(agent, complexity)` returns `"opus"`/`"sonnet"` per the rules above; security/architecture always `opus`; a single-file, low-tool, small-context, non-high-stakes reviewer returns `"sonnet"`.

## REQ-102: Complexity is computed deterministically and wired into team output
- A `Complexity` value carries `file_count`, `tool_types`, `context_fraction`.
- `context_fraction` can be derived from artifact byte size and a configurable context window (`est_tokens = bytes/4`).
- `select_team_with_scores(..., complexity=...)` returns team agents whose `model` field reflects the resolved model.
- team-selector CLI accepts `--files`, `--tool-types`, `--context-fraction`, `--context-window` and reflects resolved models in `--json` output.
- Acceptance: JSON `team[].model` shows `opus` for security/architecture and for escalating complexity; `sonnet` otherwise.

## REQ-103: Deterministic end-of-run scorecard
- `scorecard.py` emits a consistent report with four sections:
  1. **Process steps** — per step/round/phase status + counts (reviewers, tests pass/fail, findings).
  2. **Issues found** — totals by severity (P0/P1/P2/P3) and validation-dropped count.
  3. **Token costs** — per-model token breakdown (input, cache-read, cache-write, output) and USD via an overridable pricing table, plus grand total.
  4. **Model execution time** — sum of per-request `durationMs` per model and overall, labeled "model execution time (sum of request durations, not wall clock)".
- Acceptance: given a fixture state.json + transcript.jsonl, the tool prints all four sections with correct counts, costs, and summed durations; `--json` emits the same data structurally.

## REQ-104: Scorecard data sources and scoping
- Reads whichever state file exists among `.qreview/state.json`, `.qloop/state.json`, `.qpipeline/state.json` (or `--state PATH`).
- Reads a transcript JSONL (`--transcript PATH`, or autodetect newest under the cwd-derived project dir).
- Token/time aggregation groups every `message.usage` line by `message.model` (includes sidechain subagent lines).
- `--since <ISO>` bounds aggregation to lines with `timestamp >= since`; init records `started_at` in state for this purpose.
- Acceptance: `--since` excludes earlier lines; unknown model still aggregates under its raw id; missing transcript degrades to a stated "token/time unavailable" note without crashing.

## REQ-105: Skills instruct model-passing and the scorecard step
- qreview/qloop/qpipeline SKILL.md instruct spawning each reviewer/fixer with `model=<resolved model from team composition>`.
- Each skill ends with a mandatory deterministic scorecard step.
- Both the marketplace variant (relative `tools/X.py`) and the user-level fork (absolute `/Users/travis/.claude/ai-review-tools/X.py`) are updated consistently.
- Non-Goals: changing the finding schema, dedup, or convergence logic.

## REQ-106: Marketplace deploy hygiene
- Bump `ai-review-toolkit` version in `plugin.json` and `marketplace.json` (1.0.0 → 1.1.0).
- Full tool test suite green (299 baseline + new tests).
- Sync tools + SKILLs to the user-level fork after green.
