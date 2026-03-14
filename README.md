# Sparkry Claude Skills Marketplace

Production-ready Claude Code plugins for deterministic software delivery, research orchestration, content creation, and strategic planning.

## QRALPH — Deterministic Multi-Agent Software Delivery

**The problem:** Claude Code is powerful, but it cuts corners. It skips tests. It rubber-stamps its own validation. It forgets requirements mid-run. It says "done" when it's not. On long runs you end up babysitting — manually checking that tests were written, that they actually ran, that acceptance criteria were verified one-by-one against real files instead of bulk-approved with "looks good."

**QRALPH fixes this.** It wraps Claude Code in a deterministic 14-phase pipeline that enforces every step of proper software design — from requirements decomposition through fresh-context verification and user demo. Every acceptance criterion gets individually checked against actual source files with file:line evidence. Every requirement fragment gets tracked from plan to implementation to proof. Tests must be written, must run, must pass. The quality gate is a hard block, not a suggestion.

**Why not just use Claude Code with plugins?** Plugins give Claude better tools. QRALPH gives it a process. Without QRALPH, Claude decides what steps to follow, what to skip, and when "good enough" is good enough. With QRALPH, the pipeline decides. Claude does the creative work — architecture, coding, problem-solving — but the pipeline enforces that every deliverable goes through ideation, planning, implementation, simplification, quality review, polish, independent verification, and a user demo before it ships. It still uses Claude's latest capabilities (Superpowers skills, MCP tools, parallel agents) — it just makes sure they're applied in the right order with the right gates.

### What QRALPH Enforces

- Requirements are decomposed into atomic fragments (REQ-F-1, REQ-F-2, ...) at plan time — nothing gets silently dropped
- Acceptance criteria are indexed (AC-1, AC-2, ...) and tracked through execution to verification
- Tests are written before implementation (TDD), executed, and must pass
- Quality gates (lint, typecheck, test suite) run automatically and block progression on failure
- A fresh-context verifier — with zero knowledge of implementation — independently checks every AC against actual source files
- Verification requires `file:line — "quoted code"` evidence for each criterion (no "verified in execution outputs" rubber-stamping)
- Deploy only happens with explicit user intent; smoke tests hit the live URL after deployment

### The 14-Phase Pipeline

```
IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → SIMPLIFY →
QUALITY_LOOP → POLISH → VERIFY → DEMO → DEPLOY → SMOKE → LEARN → COMPLETE
```

| Phase | What Happens |
|-------|-------------|
| IDEATE | Brainstorm and validate the concept |
| PERSONA | Generate domain-specific user archetypes to pressure-test the idea |
| CONCEPT_REVIEW | Multi-agent review from architect, PM, and developer perspectives |
| PLAN | Create implementation plan with tasks, ACs, and acceptance criteria |
| EXECUTE | Parallel agent groups implement tasks with TDD |
| SIMPLIFY | Reduce unnecessary complexity |
| QUALITY_LOOP | Discovery rounds find P0/P1/P2 issues, fix rounds address them |
| POLISH | Bug fixes, wiring checks, requirements traceability |
| VERIFY | Fresh-context agent verifies every AC with file:line evidence |
| DEMO | Present completed work to user with feedback loop (max 2 cycles) |
| DEPLOY | Preflight checklist, deploy command, verify live URL |
| SMOKE | Parallel HTTP tests hit the deployed site |
| LEARN | Capture learnings for future projects |
| COMPLETE | Final summary with metrics |

### Quick Start

```bash
# Add the marketplace
/plugin marketplace add sparkst/sparkry-claude-skills

# Install QRALPH
/plugin install qralph@sparkry-claude-skills

# Run it
QRALPH "Add user authentication with OAuth2 and session management"
```

### What's New in v6.8.0

- **DEMO phase**: New 14th pipeline phase between VERIFY and DEPLOY. Presents completed work to the user with a feedback loop (max 2 cycles) before deploying.
- **Domain persona archetypes**: `suggest_archetypes()` maps project keywords to pre-built persona sets (SaaS, ecommerce, CLI, API, mobile, security, content) for automatic generation in the PERSONA phase.
- **Evidence hardening**: Source file extension whitelist prevents URLs and IP:port pairs from bypassing the evidence gate.
- **547 tests passing.**

### Multi-Project Concurrency (v6.7.0)

Run multiple projects simultaneously in separate Claude Code sessions:

```bash
# Session 1
QRALPH "Redesign the checkout flow"
# Pipeline returns project_id, all next calls use --project <id>

# Session 2 (separate terminal)
QRALPH "Add notification system"
```

**[Full QRALPH Installation Guide](./docs/QRALPH-INSTALLATION-GUIDE.md)**

---

## All Plugins (12)

### QShortcuts — Development Workflow

| Plugin | Install | Skills |
|--------|---------|--------|
| **qshortcuts-core** | `/plugin install qshortcuts-core@sparkry-claude-skills` | QNEW, QPLAN, QCODET, QCODE, QCHECK, QCHECKF, QCHECKT |
| **qshortcuts-support** | `/plugin install qshortcuts-support@sparkry-claude-skills` | QUX, QDOC, QIDEA, QGIT |
| **qshortcuts-ai** | `/plugin install qshortcuts-ai@sparkry-claude-skills` | QARCH, QPROMPT, QTRANSFORM |
| **qshortcuts-content** | `/plugin install qshortcuts-content@sparkry-claude-skills` | QWRITE, QPPT, QVISUAL, QINFOGRAPHIC |
| **qshortcuts-learning** | `/plugin install qshortcuts-learning@sparkry-claude-skills` | QFEEDBACK, QLEARN, QCOMPACT, QSKILL |

### Workflow Bundles

| Plugin | Install | Description |
|--------|---------|-------------|
| **qralph** | `/plugin install qralph@sparkry-claude-skills` | Deterministic 14-phase multi-agent pipeline (v6.8.0) |
| **dev-workflow** | `/plugin install dev-workflow@sparkry-claude-skills` | TDD workflow with PE reviewer, test writer, planner agents |
| **research-workflow** | `/plugin install research-workflow@sparkry-claude-skills` | Fact-checking, source evaluation, synthesis agents |
| **writing-workflow** | `/plugin install writing-workflow@sparkry-claude-skills` | Multi-platform content, infographics, quality scoring |
| **strategy-workflow** | `/plugin install strategy-workflow@sparkry-claude-skills` | COS, PR-FAQ, buy-vs-build, PMF validation |
| **starter-pack** | `/plugin install starter-pack@sparkry-claude-skills` | Essential agents: planner, sde-iii, pe-reviewer |
| **integrations-trello** | `/plugin install integrations-trello@sparkry-claude-skills` | Trello card management with QRALPH project sync |

---

## Install All Plugins

```bash
/plugin install qshortcuts-core@sparkry-claude-skills qshortcuts-support@sparkry-claude-skills qshortcuts-ai@sparkry-claude-skills qshortcuts-content@sparkry-claude-skills qshortcuts-learning@sparkry-claude-skills dev-workflow@sparkry-claude-skills research-workflow@sparkry-claude-skills writing-workflow@sparkry-claude-skills strategy-workflow@sparkry-claude-skills qralph@sparkry-claude-skills starter-pack@sparkry-claude-skills integrations-trello@sparkry-claude-skills
```

---

## Documentation

| Plugin | Guide |
|--------|-------|
| **qralph** | [QRALPH-INSTALLATION-GUIDE.md](./docs/QRALPH-INSTALLATION-GUIDE.md) |
| qshortcuts-core | [QSHORTCUTS-CORE-GUIDE.md](./docs/QSHORTCUTS-CORE-GUIDE.md) |
| qshortcuts-support | [QSHORTCUTS-SUPPORT-GUIDE.md](./docs/QSHORTCUTS-SUPPORT-GUIDE.md) |
| qshortcuts-ai | [QSHORTCUTS-AI-GUIDE.md](./docs/QSHORTCUTS-AI-GUIDE.md) |
| qshortcuts-content | [QSHORTCUTS-CONTENT-GUIDE.md](./docs/QSHORTCUTS-CONTENT-GUIDE.md) |
| qshortcuts-learning | [QSHORTCUTS-LEARNING-GUIDE.md](./docs/QSHORTCUTS-LEARNING-GUIDE.md) |
| dev-workflow | [DEV-WORKFLOW-GUIDE.md](./docs/DEV-WORKFLOW-GUIDE.md) |
| research-workflow | [RESEARCH-WORKFLOW-GUIDE.md](./docs/RESEARCH-WORKFLOW-GUIDE.md) |
| writing-workflow | [WRITING-WORKFLOW-GUIDE.md](./docs/WRITING-WORKFLOW-GUIDE.md) |
| strategy-workflow | [STRATEGY-WORKFLOW-GUIDE.md](./docs/STRATEGY-WORKFLOW-GUIDE.md) |
| starter-pack | [STARTER-PACK-GUIDE.md](./docs/STARTER-PACK-GUIDE.md) |
| integrations-trello | [INTEGRATIONS-TRELLO-GUIDE.md](./docs/INTEGRATIONS-TRELLO-GUIDE.md) |

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

- **Issues:** [GitHub Issues](https://github.com/sparkst/sparkry-claude-skills/issues)
- **Email:** support@sparkry.ai

---

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

**Made by [Sparkry.ai](https://sparkry.ai)**
