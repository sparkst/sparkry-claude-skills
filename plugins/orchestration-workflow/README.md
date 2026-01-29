# Orchestration Workflow (QRALPH)

Multi-agent swarm orchestration for Claude Code with parallel execution, self-healing, and checkpointing.

## What is QRALPH?

QRALPH spawns 5 parallel specialist agents to review your request from different perspectives (security, architecture, requirements, UX, code quality) before implementation.

## Installation

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
/plugin install orchestration-workflow@sparkry-claude-skills
```

## Usage

```bash
# Feature development
QRALPH "Add a logout button to the navbar"

# With specific agents
QRALPH "Review auth flow" --agents security,architecture,pm

# Planning mode (no code changes)
QRALPH "Compare auth providers" --mode planning

# Resume after interruption
QRALPH resume 001

# Check status
QRALPH status
```

## How It Works

```
     Your Request
          │
          ▼
   ┌─────────────┐
   │   QRALPH    │
   │ Orchestrator│
   └──────┬──────┘
          │
  ┌───┬───┼───┬───┐
  ▼   ▼   ▼   ▼   ▼
 Sec Arc Req  UX  Code    ← 5 PARALLEL AGENTS
  │   │   │   │   │
  └───┴───┼───┴───┘
          ▼
   ┌─────────────┐
   │  Synthesize │──→ P0/P1/P2 Findings
   │  & Execute  │──→ Self-healing
   └─────────────┘──→ UAT Generation
```

## Key Features

- **Parallel Execution**: 5 agents run simultaneously with fresh context windows
- **Self-Healing**: Auto-retry with model escalation (haiku → sonnet → opus)
- **Circuit Breakers**: $40 max, 500K tokens max, 3x error limits
- **Checkpointing**: Resume from any interruption
- **User Control**: Write PAUSE/SKIP/ABORT to CONTROL.md

## Model Tiering

| Tier | Model | Use For |
|------|-------|---------|
| Validation | haiku | Simple checks, formatting |
| Analysis | sonnet | Code review, architecture |
| Synthesis | opus | Complex reasoning |

## Cost

Typical run: $3-8 (optimized via model tiering)

## License

MIT
