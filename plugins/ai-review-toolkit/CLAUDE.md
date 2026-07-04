# AI Review Toolkit

Multi-agent review plugin for Claude Code. 252 tests, Python 3.12+.

## Commands

```bash
# Run all tests
python3 -m pytest tools/ -v

# Run a single test file
python3 -m pytest tools/test_finding_parser.py -v

# Lint (when available)
ruff check tools/
```

## Architecture

`/qreview`, `/qloop`, and `/qpipeline`'s gated presets all run on the same
**ultracode Workflow engine** (`js/review-loop.workflow.js`) rather than a
hand-driven Python state machine -- see `js/README.md` for how it's built and
drift-locked against the Python oracle below. `/qpipeline auto` runs the
separate `js/pipeline-auto.workflow.js`. The Python drivers that used to own
per-round/per-phase state (`review-driver.py`, `loop-driver.py`,
`pipeline-driver.py`) have been retired; their pure oracle functions
(`check_fix_completeness`, `get_reviewer_prompt`, `get_fixer_prompt`) now live
in `finding-parser.py`.

```
tools/           <- All Python modules (hyphenated filenames)
  _loader.py     <- Shared importer for hyphenated modules
  finding-parser.py  <- P0-P3 finding validation, dedup, synthesis, prompt oracle
  team-selector.py   <- Domain classifier + reviewer team selection + model tiering
  test-runner.py     <- Test discovery + execution
  scorecard.py       <- Deterministic end-of-run scorecard
  test_*.py          <- Co-located tests (one per tool)
js/              <- JS port of the deterministic hot-loop + the Workflow scripts
skills/          <- SKILL.md files for /qreview, /qloop, /qpipeline
agents/          <- Agent definitions (reviewer, fixer, verifier)
commands/        <- Slash command descriptions
```

## Conventions

- Tool filenames are hyphenated (`finding-parser.py`); import via `_loader.load_sibling("finding-parser.py")`
- Tests are co-located: `test_finding_parser.py` tests `finding-parser.py`
- Type hints everywhere; `from __future__ import annotations`
- Finding severity: P0 (blocks ship) > P1 (must fix) > P2 (should fix) > P3 (nice to have)
- Convergence: P0==0 AND P1==0 AND (P2+P3) <= threshold

## Gotchas

- `shell=False` for auto-discovered tests; `shell=True` only for explicit `--test-cmd` with pipe/chain operators
- Dedup merges by normalized title; updates id prefix when severity upgrades
- Minimum 2 reviewers enforced by `team-selector.py`
- Never hand-write a review/pipeline workflow script -- the only sanctioned paths are
  `review-loop.workflow.js` and `pipeline-auto.workflow.js`; a hand-rolled script has
  no `model:` tiering and silently inherits the invoking session's model

## Release discipline

- **Any change to shippable plugin source requires a version bump in BOTH**
  `.claude-plugin/plugin.json` AND the `ai-review-toolkit` entry of the root
  `.claude-plugin/marketplace.json`, kept equal. A stale `marketplace.json` makes
  `/plugin marketplace update` silently no-op. CHANGELOG-only edits are exempt.
- Enforced by `tools/check-version-bump.py` — the CI step (`.github/workflows/tests.yml`,
  on PRs) is the unbypassable gate; the local `.githooks/pre-push` hook is the fast
  local catch. **Enable the hook once per clone:** `git config core.hooksPath .githooks`.
  Bypass an intentional WIP push with `git push --no-verify` (CI still enforces it).
- `tools/version-check.py` is the runtime self-check the SKILLs run at start.
