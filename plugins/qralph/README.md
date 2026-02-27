# QRALPH v6.2.0

Deterministic multi-agent pipeline for Claude Code. Python does the orchestration. Claude does the thinking.

## What is QRALPH?

QRALPH orchestrates a 3-phase pipeline (PLAN → EXECUTE → VERIFY) with multiple specialist agents analyzing your request from different perspectives before implementation. A state machine controls every transition — Claude can't skip steps, summarize outputs, or bypass gates.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install qralph@sparkry-claude-skills
```

## Usage

```bash
/qralph "Add a logout button to the navbar"
/qralph "Audit the authentication flow for security issues"
/qralph "Create a hello world Node.js HTTP server with tests"
```

QRALPH handles everything: template selection, agent spawning, parallel execution groups, quality gates, fresh-context verification, and summary generation.

## Architecture (v6.x)

```
PLAN ──gate──> EXECUTE ──gate──> VERIFY
```

- **PLAN**: Template-based agent selection → specialist analysis → execution manifest
- **EXECUTE**: Parallel groups (file-overlap analysis) → implementation agents → quality gate
- **VERIFY**: Fresh-context verification agent → PASS/FAIL verdict → SUMMARY.md

### Enforcement Layers

1. **`cmd_next()` State Machine**: INIT → PLAN_WAITING → PLAN_REVIEW → EXEC_WAITING → VERIFY_WAIT → COMPLETE
2. **Thin SKILL.md**: 6 non-negotiable rules + simple action loop
3. **Enforcement Hooks**: SubagentStop, Stop, and PostToolUse/Write validation

## v6.2.0 — Security & Bug Fixes

- **Filename mismatches fixed** (F-13, F-18): Agent names now match expected output paths
- **Shell injection prevented** (F-01): Quality gate recomputed at runtime, never read from manifest
- **Verdict bypass prevented** (F-02): Structured JSON parsing with `_parse_verdict()`
- **Minimum output length** (F-03): Agent outputs < 100 chars rejected
- **Task schema validation** (F-06): Tasks validated for required fields before execution
- **Path safety** (F-15): Consistent `_safe_project_path()` across all commands
- **Pipeline phases** (F-05): `PLAN`, `EXECUTE`, `VERIFY` added to state validation

## Test Suite

119 tests:
```bash
python3 -m pytest skills/qralph/tools/test_qralph_pipeline.py -v
```

## License

MIT
