# Changelog — ai-review-toolkit

## 1.6.1

### Added
- **`tools/fork-sync.py` — the concrete "help me upgrade" path for manual
  installs.** Copies the current marketplace source into a flat fork
  (`~/.claude/ai-review-tools`): runtime `tools/*.py` → the fork root (excluding
  tests, `gen-*` generators, and maintainer-only tools), `js/*.workflow.js` →
  `<fork>/js/`, and each `skills/<name>/SKILL.md` → the installed skills dir with
  `<plugin>` rewritten to the fork's absolute path (`<plugin>/tools` → the flat
  root; the `<tools>` runtime placeholder is left intact). Supports `--dry-run`.
  It also stamps a `VERSION` file into the fork so `version-check.py` can report
  the installed version there (the flat fork has no `plugin.json`).

### Fixed
- **`version-check.py` now works in a flat fork.** It falls back to a sibling
  `VERSION` file when there's no `.claude-plugin/plugin.json`, and the whole check
  is wrapped fail-open so it can never raise or slow a run. The fork upgrade notice
  now names `fork-sync.py` directly.

## 1.6.0

### Added
- **Version-bump enforcement (`tools/check-version-bump.py`).** Any change to
  shippable plugin source now requires a version bump in BOTH
  `.claude-plugin/plugin.json` AND the `ai-review-toolkit` entry of the root
  `.claude-plugin/marketplace.json`, and the two must agree (a stale
  `marketplace.json` makes `/plugin marketplace update` silently no-op). Enforced
  two ways: a CI step (`tests.yml`, on PRs — unbypassable) and a local
  `.githooks/pre-push` hook for the same catch seconds earlier
  (`git config core.hooksPath .githooks` to enable; `git push --no-verify` to
  bypass intentional WIP). CHANGELOG-only changes don't trigger it.
- **Skill self-version-check (`tools/version-check.py`).** `/qreview`, `/qloop`,
  and `/qpipeline` run a best-effort check at start: it compares the installed
  version against the latest published on the marketplace `main` and, when behind,
  prints a one-line upgrade notice with the right command for the install kind
  (`/plugin marketplace update` for a marketplace install; a fork-sync for a
  manual fork). Rate-limited to ~once/day via a cache stamp and fails
  silent-and-open, so it never blocks or slows a run.

## 1.5.2

### Fixed
- **`/qpipeline auto` TDD green gate no longer drops a slice for incidental
  lockfile/manifest drift.** The pre-integration tamper check flagged ANY file
  the implementer's worktree touched beyond the slice's declared files — but a
  test/build runner routinely rewrites lockfiles, package/project manifests, and
  caches (`package-lock.json`, `*.lock`, `pnpm-lock.yaml`, `.project/manifest.yaml`,
  `__pycache__/`, `*.pyc`, `node_modules/`) as a side effect. A correctly
  implemented, green, in-scope slice was being cleaned up and dropped purely on
  that drift (observed: a CLI slice whose `src/cli.js` passed every gate was
  discarded because running the suite rewrote a manifest). `tdd-harness.py`'s
  `check_tamper` now tolerates an `INCIDENTAL_DRIFT_GLOBS` allowlist (overridable
  via `ignore_globs`; a frozen **test** file is never excused), and the green-gate
  agent prompt codifies the same rule. The integrator already reverted such drift
  for slices that *reached* integration — this closes the gap for slices judged at
  the green gate first.

## 1.5.1

### Fixed
- **`/qpipeline auto` now commits the fixer's edits beyond the artifact
  (SMOKE-008).** When a convergence loop's fixer edited files other than the
  artifact itself (e.g. a test file, while fixing an integration-plan finding),
  the pipeline's pathspec-scoped commit captured only the artifact — leaving those
  edits uncommitted. Final `verify` then ran against a working tree the committed
  branch lacked (green on N tests while `main` had fewer). The fixer now declares
  every file it edited (`edited_files` in the resolutions schema); `runLoop`
  surfaces the union across rounds, and each converge commit pathspec-adds those
  paths alongside the artifact (still never `git add -A`, so leftover
  `.pipeline-wt/` worktree state is never swept in). `/qreview` and `/qloop` are
  unaffected — they don't commit, so the new field is returned and ignored.

### Added
- **`/qpipeline auto prod` — the autonomous production tail (Phase F2).** After the
  verified stop, `auto prod` (`prodAutonomous: true` + a declared `deployTarget`)
  runs: `DEPLOY-PLAN (qloop'd) → staging deploy → staging smoke → guardrail gate →
  qdecide(irreversible) → prod publish → prod smoke → PROMOTE | auto-rollback →
  re-smoke → escalate/hard-page`. Plain `/qpipeline auto` is unchanged: no
  `deployTarget` stops at verify (`status: verified`); with a `deployTarget` it
  staging-deploys + smokes then stops before prod (`status: staged`).
- **`deployTarget` is DECLARED, never inferred** — `{kind, stagingCmd, prodCmd,
  stagingUrl, prodUrl, rollbackCmd, stateful}`. `rollbackCmd` is mandatory for prod
  (the gate refuses prod without a present, dry-validated rollback); `stateful:true`
  downgrades a failed-smoke recovery to hard-page-only (code rollback can't undo
  data mutations).
- **Curated cumulative prod smoke suite** (`smoke/prod.suite.json`, `smokeContract`
  arg): one versioned regression net every feature appends its checks to (the gate
  fails a feature that ships no smoke check for its new behavior); the full suite
  runs against prod via parallel Haiku fan-out.
- The **guardrail-gate verdict now surfaces in the scorecard** (`scorecard.py`),
  with staging/prod smoke pass-rates and every blocker.

### Internal
- New `js/prod-prompts.mjs` (deploy/publish/smoke/rollback prompt builders +
  in-process `planSmokeBatches`/`aggregateSmoke` mirrors + `buildGateState`),
  inlined into `pipeline-auto.workflow.js`. `prod-tail.py` gains a `rollback` CLI
  subcommand (exit-coded so the workflow branches deterministically). All safety
  verdicts (`deploy_gate`, `rollback_decision`) stay single-source in `prod-tail.py`.

### Fixed
- **`/qpipeline auto` TDD worktree isolation (P0, #27).** Each slice's red/green
  gates and the integrator now share ONE named sibling worktree
  (`${ROOT}.pipeline-wt/<id>` + `pipeline/<id>` branch) instead of four anonymous
  per-agent worktrees — previously the red gate never saw the authored tests.
  Tamper checks are commit-based; the integrator merges the slice branches.
- **Wave-by-wave integration (P0, #33).** Each wave integrates before the next
  branches (a later wave can depend on an already-merged one); artifacts are
  committed on the working branch as they converge; a branch-history sanity gate
  plus full sweep guard against tests smuggled in via merge/resurrected commits.
  `collectBlockers` reports honest status.
- **Merge-order honors merged waves (#34).** `compute_merge_order` accepts
  `merged_ids` so already-integrated waves count as satisfied dependencies;
  blocked slices surface as `integration.failed` blockers, never silently dropped.

### Changed
- **Cost right-sizing — model tiering across the board (OPT batch, #28–#32).**
  Reviewers/fixer/TDD-writer/implementer/conflict-resolver run on `sonnet`,
  mechanical gates/spot-fix/smoke fan-out/CLI adapters on `haiku`, and `opus` is
  capped at 1–2 domain-scored seats (security + design-author). `scorecard.py`
  gains real fable/opus pricing, the `[1m]` tier, a model-leak banner, and
  per-lens yield; reviewer policy adds per-reviewer escalation with an N=3 team
  default; `loop-engine` does in-engine tiering, doc-artifact test-gate skips,
  proportional single-verifier rounds, and findings-history keyed by path;
  `pipeline-auto` decomposes the integrator (per-merge haiku gates + on-failure
  sonnet conflict-resolver + tamper re-gate), wires a runtime `budget` ceiling,
  adds a seam-test gate, and hardens the fallback team.
- **Hand-rolled Workflow scripts are banned in all SKILLs (#30).** `/qreview`,
  `/qloop`, and `/qpipeline` presets route through the canonical Workflow engine
  so agents inherit correct model tiering (no more session-opus leak). The Python
  drivers are retired — their oracle functions moved into `finding-parser.py`;
  cross-session checkpoint/resume is dropped (documented, accepted).

## 1.3.0

### Changed
- **`/qloop` now splits P2/P3 into significant vs. trivial.** P0/P1 and any P2/P3
  a reviewer flags `significance:true` (or that recurs across rounds) get the full
  fix-loop + fix-ALL gate as before. First-seen, unflagged cosmetic nits get a
  cheap **Haiku spot-fix + spot-check** each round instead — still addressed, but
  they no longer block convergence or reset the loop. Convergence is reached when
  the *significant* set is clear (P0/P1 always count as significant, so they stay
  0-to-ship). Cheaper trivial tail, faster convergence on cosmetic churn.
- Reviewer finding schema gains an optional additive `significance` boolean.

### Internal
- The convergence loop was extracted from `review-loop.template.js` into a
  shared, unit-tested `js/loop-engine.mjs` (`runLoop(config, ctx)` with Workflow
  globals injected). Both `review-loop.workflow.js` and the upcoming
  `pipeline-auto.workflow.js` inline the same drift-locked engine — no nesting,
  no fork. `adjudication.mjs` (the Python-oracle contract) is untouched; the
  `significance` flag is carried at the workflow layer (captured from raw
  reviewer findings before dedup strips it), so golden parity is preserved.
- `build-workflow.mjs` now strips multi-line imports when inlining.

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
