# QRALPH v6.6.0

Full-lifecycle multi-agent pipeline for Claude Code. Python does the orchestration. Claude does the thinking.

## What is QRALPH?

QRALPH orchestrates a 10-phase pipeline (IDEATE through LEARN) with multiple specialist agents analyzing your request from different perspectives before implementation. A state machine controls every transition -- Claude can't skip steps, summarize outputs, or bypass gates.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install qralph@sparkry-claude-skills
```

## Usage

```bash
/qralph "Add a logout button to the navbar"
/qralph "Audit the authentication flow for security issues"
/qralph --quick "Create a hello world Node.js HTTP server with tests"
```

QRALPH handles everything: template selection, agent spawning, parallel execution groups, quality gates, fresh-context verification, and summary generation.

## Architecture (v6.6.0)

### 10-Phase Pipeline

```
IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → SIMPLIFY → QUALITY_LOOP → POLISH → VERIFY → LEARN
```

### Two Operating Modes

- **`--thorough`** (default): All 10 phases with adaptive quality loops and cross-project learning
- **`--quick`**: Streamlined path skipping PERSONA, CONCEPT_REVIEW, SIMPLIFY, and LEARN phases

### 6 New Tools (v6.5.0+)

| Tool | Purpose |
|------|---------|
| `plugin-detector` | Auto-discovers installed Claude Code plugins and MCP servers |
| `persona-generator` | Creates synthetic user personas for concept review |
| `quality-dashboard` | Aggregates quality metrics into a unified dashboard |
| `confidence-scorer` | Scores agent output confidence with calibrated thresholds |
| `requirements-tracer` | Traces requirements through plan, execution, and verification |
| `learning-capture` | Captures cross-project learnings for reuse |

### Enforcement Layers

1. **`cmd_next()` State Machine**: 10 phases with gate transitions and backtrack-to-replan
2. **Thin SKILL.md**: Non-negotiable rules + simple action loop
3. **Enforcement Hooks**: SubagentStop, Stop, and PostToolUse/Write validation

### Adaptive Quality Loop

- Discovery/fix separation: first pass identifies issues, second pass fixes them
- Backtrack-to-replan: architectural issues trigger pipeline backtrack to PLAN
- Configurable iteration limits with diminishing-returns detection

### Cross-Project Learning

- Patterns and anti-patterns persist across QRALPH runs
- Learnings injected into PLAN and EXECUTE phases
- Automatic relevance scoring ensures only applicable learnings surface

## v6.6.0 Highlights

- **Exclusive mode enforcement**: QRALPH owns the session — Claude cannot invoke other skills from the outer loop
- Rule #8: never leave the pipeline loop to invoke other workflows
- Enforcement hooks wired into Claude Code settings (previously defined but not loaded)

## v6.5.0 Highlights

- Full-lifecycle 10-phase pipeline (up from 3 phases)
- Two operating modes: `--thorough` (default) and `--quick`
- 6 new specialist tools
- Adaptive quality loop with discovery/fix separation
- Backtrack-to-replan mechanism for architectural issues
- Cross-project learning system
- 350 tests (up from ~160)

## Test Suite

350 tests:
```bash
python3 -m pytest skills/qralph/tools/ -v
```

## License

MIT
