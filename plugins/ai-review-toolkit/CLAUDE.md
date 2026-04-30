# AI Review Toolkit

Multi-agent review plugin for Claude Code. 281 tests, Python 3.12+.

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

```
tools/           <- All Python modules (hyphenated filenames)
  _loader.py     <- Shared importer for hyphenated modules
  finding-parser.py  <- P0-P3 finding validation, dedup, synthesis
  review-driver.py   <- Single-round review state machine
  loop-driver.py     <- Multi-round review-fix loop state machine
  pipeline-driver.py <- Multi-phase pipeline orchestrator
  team-selector.py   <- Domain classifier + reviewer team selection
  test-runner.py     <- Test discovery + execution
  test_*.py          <- Co-located tests (one per tool)
skills/          <- SKILL.md files for /qreview, /qloop, /qpipeline
agents/          <- Agent definitions (reviewer, fixer, verifier)
commands/        <- Slash command descriptions
```

## Conventions

- Tool filenames are hyphenated (`finding-parser.py`); import via `_loader.load_sibling("finding-parser.py")`
- Tests are co-located: `test_finding_parser.py` tests `finding-parser.py`
- Type hints everywhere; `from __future__ import annotations`
- State machines write to hidden dirs: `.qreview/`, `.qloop/`, `.qpipeline/`
- Finding severity: P0 (blocks ship) > P1 (must fix) > P2 (should fix) > P3 (nice to have)
- Convergence: P0==0 AND P1==0 AND (P2+P3) <= threshold

## Gotchas

- `shell=False` for auto-discovered tests; `shell=True` only for explicit `--test-cmd` with pipe/chain operators
- `record_phase_result` requires `phase_idx == current_idx` (strict current-phase-only)
- Review-loop results must have `converged=True` OR `status='escalated'/'failed'` to advance pipeline
- `project_id` validated against `^[0-9]{3}-[a-z0-9][a-z0-9-]{0,40}$`
- Dedup merges by normalized title; updates id prefix when severity upgrades
- Minimum 2 reviewers enforced at both tool and driver levels
- Artifact files capped at 512KB in review-driver
