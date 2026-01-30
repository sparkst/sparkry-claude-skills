# Sparkry Claude Skills Marketplace

Production-ready Claude Code plugins for TDD workflows, research orchestration, content creation, and strategic planning.

## Quick Start

### Step 1: Add the Marketplace

```bash
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install Plugins

```bash
# Install individual plugins
/plugin install <plugin-name>@sparkry-claude-skills

# Example: Install the orchestration workflow (QRALPH)
/plugin install orchestration-workflow@sparkry-claude-skills
```

### Step 3: Verify Installation

```bash
/plugin list
```

---

## Available Plugins (11)

### QShortcuts - Development Workflow

| Plugin | Command | Skills Included |
|--------|---------|-----------------|
| **qshortcuts-core** | `/plugin install qshortcuts-core@sparkry-claude-skills` | QNEW, QPLAN, QCODET, QCODE, QCHECK, QCHECKF, QCHECKT |
| **qshortcuts-support** | `/plugin install qshortcuts-support@sparkry-claude-skills` | QUX, QDOC, QIDEA, QGIT |
| **qshortcuts-ai** | `/plugin install qshortcuts-ai@sparkry-claude-skills` | QARCH, QPROMPT, QTRANSFORM |
| **qshortcuts-content** | `/plugin install qshortcuts-content@sparkry-claude-skills` | QWRITE, QPPT, QVISUAL, QINFOGRAPHIC |
| **qshortcuts-learning** | `/plugin install qshortcuts-learning@sparkry-claude-skills` | QFEEDBACK, QLEARN, QCOMPACT, QSKILL |

### Workflow Bundles

| Plugin | Command | Description |
|--------|---------|-------------|
| **orchestration-workflow** | `/plugin install orchestration-workflow@sparkry-claude-skills` | QRALPH multi-agent swarm (5 parallel agents, self-healing, checkpointing) |
| **dev-workflow** | `/plugin install dev-workflow@sparkry-claude-skills` | TDD workflow with PE reviewer, test writer, planner agents |
| **research-workflow** | `/plugin install research-workflow@sparkry-claude-skills` | Fact-checking, source evaluation, synthesis agents |
| **writing-workflow** | `/plugin install writing-workflow@sparkry-claude-skills` | Multi-platform content, infographics, Google Docs publishing |
| **strategy-workflow** | `/plugin install strategy-workflow@sparkry-claude-skills` | COS, PR-FAQ, buy-vs-build, PMF validation skills |
| **starter-pack** | `/plugin install starter-pack@sparkry-claude-skills` | Essential agents: planner, sde-iii, pe-reviewer |

---

## Install All Plugins

```bash
/plugin install qshortcuts-core@sparkry-claude-skills qshortcuts-support@sparkry-claude-skills qshortcuts-ai@sparkry-claude-skills qshortcuts-content@sparkry-claude-skills qshortcuts-learning@sparkry-claude-skills dev-workflow@sparkry-claude-skills research-workflow@sparkry-claude-skills writing-workflow@sparkry-claude-skills strategy-workflow@sparkry-claude-skills orchestration-workflow@sparkry-claude-skills starter-pack@sparkry-claude-skills
```

---

## Featured: QRALPH Multi-Agent Orchestration

QRALPH spawns 5 parallel specialist agents to review your requests before implementation. Includes self-healing, checkpointing, and UAT validation.

```bash
# Install
/plugin install orchestration-workflow@sparkry-claude-skills

# Use
qralph( Add dark mode toggle to settings page )
```

**[Full QRALPH Installation Guide →](./docs/QRALPH-INSTALLATION-GUIDE.md)**

---

## Plugin Details

### 1. Orchestration Workflow (QRALPH)

Multi-agent swarm orchestration with parallel execution.

**Features:**
- 5 parallel specialist agents (security, architecture, UX, requirements, code quality)
- Self-healing with model tiering (Haiku → Sonnet → Opus)
- Automatic checkpointing and recovery
- UAT scenario generation
- Cost-optimized execution ($3-8/run)

**Use Cases:** Feature development, code review, research, planning

---

### 2. Research Workflow

Comprehensive research orchestration for competitive analysis and strategic intelligence.

**Agents:**
- Research Director (multi-agent coordinator)
- Fact Checker & Source Evaluator
- Industry Scout & Synthesis Writer
- Dissent Moderator

**Use Cases:** Competitive analysis, market research, due diligence

---

### 3. Writing Workflow

Multi-platform content creation with voice consistency and quality scoring.

**Skills:**
- Multi-platform transformation (LinkedIn, Twitter, Email, Substack)
- Google Docs publishing integration
- Infographic generation
- Quality scoring and voice validation

**Use Cases:** Content marketing, thought leadership, social media

---

### 4. Strategy Workflow

Strategic decision-making framework for executive planning.

**Skills:**
- PR-FAQ generator
- Buy-vs-Build analyzer
- PMF validation framework
- Tenets documentation
- Security review

**Use Cases:** Strategic planning, product decisions, executive briefings

---

### 5. Dev Workflow

TDD-first development acceleration.

**Agents:**
- PE Reviewer (code quality)
- Test Writer (TDD)
- Planner (requirements)
- Release Manager

**Use Cases:** Feature development, code reviews, refactoring

---

### 6. QShortcuts Core

Core TDD development shortcuts.

| Shortcut | Purpose |
|----------|---------|
| QNEW | Start new feature with requirements |
| QPLAN | Analyze codebase, create implementation plan |
| QCODET | Write failing tests (TDD red phase) |
| QCODE | Implement to pass tests (TDD green phase) |
| QCHECK | Full quality review |
| QCHECKF | Fast quality check |
| QCHECKT | Test-only check |

---

### 7. QShortcuts Support

Development support shortcuts.

| Shortcut | Purpose |
|----------|---------|
| QUX | UX testing and accessibility check |
| QDOC | Generate/update documentation |
| QIDEA | Research and ideation (no code) |
| QGIT | Git commit with conventional commits |

---

### 8. QShortcuts AI

AI and architecture shortcuts.

| Shortcut | Purpose |
|----------|---------|
| QARCH | Design learning AI systems |
| QPROMPT | Optimize prompts |
| QTRANSFORM | Transform content formats |

---

### 9. QShortcuts Content

Content creation shortcuts.

| Shortcut | Purpose |
|----------|---------|
| QWRITE | Multi-platform content creation |
| QPPT | Generate presentation slides |
| QVISUAL | Create visual content |
| QINFOGRAPHIC | Generate infographics |

---

### 10. QShortcuts Learning

Meta-learning and improvement shortcuts.

| Shortcut | Purpose |
|----------|---------|
| QFEEDBACK | Extract and integrate user feedback |
| QLEARN | Retrieve relevant learnings |
| QCOMPACT | Consolidate learnings |
| QSKILL | Create new agent+skill complex |

---

### 11. Starter Pack

Essential agents for getting started.

**Agents:**
- Planner - Requirements and task breakdown
- SDE-III - Implementation complexity analysis
- PE Reviewer - Code quality review

---

## Documentation

Each plugin has a detailed user guide in the `docs/` folder:

| Plugin | User Guide |
|--------|------------|
| qshortcuts-core | [QSHORTCUTS-CORE-GUIDE.md](./docs/QSHORTCUTS-CORE-GUIDE.md) |
| qshortcuts-support | [QSHORTCUTS-SUPPORT-GUIDE.md](./docs/QSHORTCUTS-SUPPORT-GUIDE.md) |
| qshortcuts-ai | [QSHORTCUTS-AI-GUIDE.md](./docs/QSHORTCUTS-AI-GUIDE.md) |
| qshortcuts-content | [QSHORTCUTS-CONTENT-GUIDE.md](./docs/QSHORTCUTS-CONTENT-GUIDE.md) |
| qshortcuts-learning | [QSHORTCUTS-LEARNING-GUIDE.md](./docs/QSHORTCUTS-LEARNING-GUIDE.md) |
| orchestration-workflow | [QRALPH-INSTALLATION-GUIDE.md](./docs/QRALPH-INSTALLATION-GUIDE.md) |
| dev-workflow | [DEV-WORKFLOW-GUIDE.md](./docs/DEV-WORKFLOW-GUIDE.md) |
| research-workflow | [RESEARCH-WORKFLOW-GUIDE.md](./docs/RESEARCH-WORKFLOW-GUIDE.md) |
| writing-workflow | [WRITING-WORKFLOW-GUIDE.md](./docs/WRITING-WORKFLOW-GUIDE.md) |
| strategy-workflow | [STRATEGY-WORKFLOW-GUIDE.md](./docs/STRATEGY-WORKFLOW-GUIDE.md) |
| starter-pack | [STARTER-PACK-GUIDE.md](./docs/STARTER-PACK-GUIDE.md) |

For contributors, see [DOCUMENTATION-TEMPLATE.md](./docs/DOCUMENTATION-TEMPLATE.md) for documentation standards.

---

## Troubleshooting

### Update Marketplace

```bash
/plugin marketplace update sparkry-claude-skills
```

### Remove and Re-add Marketplace

```bash
/plugin marketplace remove sparkry-claude-skills
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Uninstall a Plugin

```bash
/plugin uninstall <plugin-name>@sparkry-claude-skills
```

---

## Support

- **Documentation:** [sparkry.ai/docs](https://sparkry.ai/docs)
- **Issues:** [GitHub Issues](https://github.com/sparkst/sparkry-claude-skills/issues)
- **Email:** support@sparkry.ai

---

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

**Made with care by [Sparkry.ai](https://sparkry.ai)**
