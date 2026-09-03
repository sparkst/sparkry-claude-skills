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

## REQ-STOP-201: Deterministic checks precede agentic ones
- The per-round test/lint gate runs FIRST; a failing gate claims the round (fixer only, no reviewer fan-out).
- Bounded by `maxGateRounds` (default 2 consecutive); disabled in single-round (`/qreview`) mode.
- Acceptance: a fixture whose round-1 gate fails runs 0 reviewers and 1 fixer; a third consecutive failing gate runs the full fan-out anyway; `rounds:1` always fans out.

## REQ-STOP-202: Proportional rounds (a small contract-safe batch buys one delta verifier)
- `isDeltaEligible` (pure, `js/stopping-rules.mjs`) requires ALL of: zero P0 in the batch; <= 20 changed lines AND <= 5% of the artifact; no contract line touched (`REQ-<CLASS>-<n>`, a line starting `Acceptance`, an `sto:` line, any line inside `### Requirement classes` / `### Cross-repo design` / `### Story points` / `### Review receipt`).
- Bookends owned by `runLoop`: round 1 is always full; a delta round never follows a delta round; any finding in a delta round re-opens the full loop.
- The diff is MEASURED by a haiku probe and JUDGED in JS. Any missing/malformed measurement fails CLOSED to a full round.
- Acceptance: a 3-line prose batch runs round 3 as a single verifier and converges; the same edit on an `Acceptance:` line runs a full round; a 25-line edit runs a full round; delta,delta is impossible; a delta round returning one P3 re-opens a full round.

## REQ-STOP-203: Divergence halt
- After `warmup` (6) valid rounds, if each of the last `window` (3) surfaced >= 1 NEW P0/P1 and that sum did not decay against the prior `window`, the run escalates with a SPLIT recommendation and `outcome.divergence`.
- Checked BEFORE the round's fixer, so a diverging round does not also pay for a fix batch.
- Acceptance: replaying the 19-round shape halts at round 6 with `/SPLIT/` and no `fix:r6`; a decaying 3,3,3,1,1,1 run converges untouched.

## REQ-STOP-204: The round budget is spent in VALID rounds only
- Round reports carry `valid` (via the `validateRound` hook) and `reviewers_requested`/`reviewers_returned`; the quorum gate (#43) sets `valid`.
- Invalid rounds consume no budget and fill no divergence window; exhausting `maxInvalidRounds` escalates naming the ENVIRONMENT, not the artifact. An absolute `hardCap = maxRounds + maxInvalidRounds` bounds the loop.
- Acceptance: 2 invalid rounds leave 3 valid rounds owed against `maxRounds: 3`; an all-invalid run escalates with `/Environment/`; invalid rounds cannot fill the divergence window.

## REQ-STOP-205: Cost travels with the verdict
- `runLoop` returns `budget` (`maxRounds`, `roundsRun`, `validRounds`, `invalidRounds`, `fullRounds`, `deltaRounds`, `gateRounds`, `maxInvalidRounds`, `hardCap`, `wallClockMs`); `history` entries carry `kind`, `ms`, `delta_reason`, reviewer counts.
- `scorecard.py` renders a first-line `VERDICT: <status> - N of M rounds (x full, y delta, z gate) - tokens - $ - wall-clock`, plus the escalation reason; absent a workflow result no verdict is invented.
- Acceptance: the verdict section carries rounds/tokens/wall-clock and renders at the top; a pre-1.9.0 run with no `budget` still renders a verdict without a fabricated denominator.

## REQ-QRM-301: Every reviewer is attested, none is silently dropped
- The fan-out SETTLES each reviewer (`settleReviewer`): a reviewer that rejects is recorded `{name, ok:false, reason}` and never aborts the round; one that returns nothing, or a result with no `findings` array, is recorded missing with a named reason.
- `attestReviewers` (pure, `js/workflow-helpers.mjs`) returns `{requested, returned, quorum, quorumMet, missing:[{name,reason}], lists}`; only reviewers that genuinely reported contribute findings to synthesis.
- Acceptance: 2 reviewers dead on `Login expired` attest 0/2 with both reasons preserved; a `null` result and a `{}` result are missing (not clean); a reason that is multi-line or 400 chars collapses to one capped line.

## REQ-QRM-302: Quorum gates termination
- Quorum is a majority of the requested panel with a floor of 2 (`reviewerQuorum`: 1 -> 1, 2 -> 2, 4 -> 2, 32 -> 16). A round that requested no reviewers (the deterministic gate round) is exempt.
- A round below quorum is recorded `valid: false` and short-circuits BEFORE synthesis: no ledger adjudication, no fixer, no spot-fixer, no convergence. It spends no round budget, and the next round is a full re-read.
- The min-rounds floor counts VALID rounds, so a run cannot converge off a single valid round.
- The `validateRound` hook may only ADD invalidation; it can never validate a below-quorum round.
- Acceptance: all reviewers dead -> INVALID and escalated, never converged; 29 of 32 dead -> INVALID; 1 of 4 returning a P3 never reaches the spot-fixer; a healthy round converges exactly as before.

## REQ-QRM-303: The count and the reason ride in the verdict
- A converged `outcome.message` carries `reviewers <returned>/<requested> returned`, and `outcome.reviewers` carries `{requested, returned, quorum, missing}`.
- An environment escalation names every failed reviewer and its reason; `history` entries carry `reviewers_quorum` and `reviewers_missing`.
- `scorecard.py` renders `reviewers N/M returned` on the verdict line when the run reports it.
- A run that reaches the hard cap never returns a null outcome: it escalates, since a null outcome reads downstream as neither converged nor escalated.
- Acceptance: the Quark shape (0 of 2 reviewers, live spot-fixer) renders `VERDICT: ESCALATED ... reviewers 0/2 returned` with `Login expired` in the reason.

