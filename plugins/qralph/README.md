# QRALPH v6.12.1

Deterministic multi-agent pipeline for Claude Code. Python enforces the process. Claude does the creative work.

## What is QRALPH?

QRALPH orchestrates a 14-phase pipeline (IDEATE through COMPLETE) with multiple specialist agents analyzing your request from different perspectives before implementation. A state machine controls every transition — Claude can't skip steps, summarize outputs, or bypass gates.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install qralph@sparkry-claude-skills
```

## Usage

```bash
QRALPH "Add user authentication with OAuth2 and session management"
QRALPH "Audit the authentication flow for security issues"
QRALPH --quick "Create a hello world Node.js HTTP server with tests"
```

QRALPH handles everything: requirements decomposition, template selection, agent spawning, parallel execution groups, quality gates, fresh-context verification, user demo, deployment, and smoke testing.

## Architecture (v6.12.1)

### 14-Phase Pipeline

```
IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → SIMPLIFY →
QUALITY_LOOP → POLISH → VERIFY → DEMO → DEPLOY → SMOKE → LEARN → COMPLETE
```

### Two Operating Modes

- **`--thorough`** (default): All 14 phases with adaptive quality loops and cross-project learning
- **`--quick`**: Streamlined path skipping PERSONA, CONCEPT_REVIEW, SIMPLIFY, and LEARN phases

### Key Features

| Feature | Description |
|---------|-------------|
| **DEMO phase** (v6.12.1) | Present completed work to user with feedback loop (max 2 cycles) before deploy |
| **Domain personas** (v6.12.1) | Auto-suggest persona archetypes based on project keywords (SaaS, ecommerce, CLI, etc.) |
| **Evidence hardening** (v6.12.1) | Source file extension whitelist prevents URLs/IPs from bypassing evidence gate |
| **Requirements fragmentation** | Atomic REQ-F-N fragments tracked from plan to verification |
| **3-dimension verification** | Every AC graded on IMPLEMENTED + INTENT_MATCH + SHIP_READY |
| **Deploy + smoke** | Preflight → deploy → parallel HTTP smoke tests on live URL |
| **Quality re-verification** | Haiku verifier per P0/P1 finding before dashboard |
| **Anti-bulk-stamp** | Rejects mass remediation without `--batch` flag |

### Enforcement Layers

1. **`cmd_next()` State Machine**: 14 phases with gate transitions and backtrack-to-replan
2. **Thin SKILL.md**: Non-negotiable rules + simple action loop
3. **Enforcement Hooks**: SubagentStop, Stop, and PostToolUse/Write validation

## Test Suite

547 tests:
```bash
python3 -m pytest plugins/qralph/skills/qralph/tools/ -v
```

## License

MIT
