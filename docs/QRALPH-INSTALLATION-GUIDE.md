# How to Install and Use the QRALPH Multi-Agent Skill

## Overview

QRALPH is a multi-agent swarm orchestration skill that spawns 5 parallel specialist agents to review and execute your requests. It includes self-healing, checkpointing, and UAT validation.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

You should see:

```
Successfully added marketplace: sparkry-claude-skills
```

### Step 2: Install the Orchestration Workflow Skill

```
/plugin install orchestration-workflow@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

You should see `orchestration-workflow` in your installed skills.

------------------------------------------------------------------------

## Usage

### Basic Syntax

```
qralph( <your request here> )
```

### Examples

**Feature Development:**

```
qralph( Add dark mode toggle to settings page )
```

**Research/Planning (non-coding):**

```
qralph( Compare auth providers for B2B SaaS --mode planning )
```

**Creative Tasks:**

```
qralph( write a haiku )
```

------------------------------------------------------------------------

## What Happens When You Run QRALPH

1.  **Project Initialization** - Creates a project directory at `.qralph/projects/<id>-<slug>/`

2.  **Agent Selection** - Automatically selects 5 specialist agents based on your request type:

    | Request Type | Agents Selected |
    |--------------|-----------------|
    | Feature Dev | architecture, security, UX, requirements, sde-iii |
    | Code Review | security, code-quality, architecture, requirements, pe-reviewer |
    | Research | research-director, fact-checker, source-evaluator, industry-scout, synthesis-writer |
    | Content | synthesis-writer, UX, PM, strategic-advisor, research-director |
    | Planning | PM, pe-designer, requirements, finance, strategic-advisor |

3.  **Parallel Review** - All 5 agents run simultaneously, each analyzing your request from their specialty

4.  **Synthesis** - Findings are consolidated into a unified report with P0/P1/P2 priorities

5.  **Execution** - For coding tasks, implements fixes based on findings

6.  **UAT** - Generates and validates acceptance test scenarios

7.  **Finalize** - Creates summary and archives the project

------------------------------------------------------------------------

## Project Outputs

After completion, find your outputs at:

```
.qralph/projects/<project-id>/
├── SUMMARY.md           # Final summary
├── SYNTHESIS.md         # Consolidated findings
├── UAT.md               # Acceptance test scenarios
├── CONTROL.md           # Intervention commands (if needed)
├── decisions.log        # Decision audit trail
├── agent-outputs/       # Individual agent reviews
│   ├── security-reviewer.md
│   ├── architecture-advisor.md
│   └── ...
├── checkpoints/         # Recovery checkpoints
└── healing-attempts/    # Self-heal logs (if errors occurred)
```

------------------------------------------------------------------------

## Advanced Commands

### Resume a Paused Project

```
qralph resume 001
```

### Check Project Status

```
qralph status
```

### Specify Custom Agents

```
qralph( review my API --agents security,architecture,pm )
```

------------------------------------------------------------------------

## Intervention (While Running)

Edit `.qralph/projects/<id>/CONTROL.md` and add one of:

| Command  | Effect                        |
|----------|-------------------------------|
| `PAUSE`  | Stop after current step       |
| `SKIP`   | Skip current operation        |
| `ABORT`  | Graceful shutdown, save state |
| `STATUS` | Force status dump             |

------------------------------------------------------------------------

## Troubleshooting

### "Marketplace already installed"

```
/plugin marketplace remove sparkry-claude-skills
/plugin marketplace add sparkst/sparkry-claude-skills
```

### PAUSE detected unexpectedly

Check that your `CONTROL.md` file doesn't contain the word "PAUSE" in its instructions. Clear the file contents if needed.

### Resume after crash

```
qralph resume <project-id>
```

The system checkpoints at every phase, so you can recover from where you left off.

------------------------------------------------------------------------

## Cost Optimization

QRALPH uses model tiering to minimize costs:
- **Haiku** - Simple validation tasks
- **Sonnet** - Analysis and review tasks
- **Opus** - Complex synthesis only

Typical run cost: $3-8 depending on complexity.

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support or visit our documentation at [sparkry.ai/docs](https://sparkry.ai/docs).
