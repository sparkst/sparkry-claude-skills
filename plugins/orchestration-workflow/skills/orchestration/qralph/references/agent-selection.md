# QRALPH Agent Selection

## Selection Priority

1. **User-specified**: `--agents security,architecture,pm`
2. **Auto-selected**: Based on request keywords
3. **Custom personas**: Generated when no matches

## Auto-Selection Algorithm

```python
def select_agents(request: str) -> list[str]:
    # 1. Parse request for domain keywords
    keywords = extract_keywords(request)

    # 2. Score each agent by keyword match
    scores = {}
    for agent in registry.agents:
        score = len(set(keywords) & set(agent.keywords))
        scores[agent.id] = score

    # 3. Sort by score, select top 5
    ranked = sorted(scores.items(), key=lambda x: -x[1])

    # 4. Ensure diversity (max 2 per category)
    selected = []
    category_counts = {}
    for agent_id, score in ranked:
        agent = registry.get(agent_id)
        if category_counts.get(agent.category, 0) < 2:
            selected.append(agent_id)
            category_counts[agent.category] = category_counts.get(agent.category, 0) + 1
        if len(selected) == 5:
            break

    return selected
```

## Default Agent Sets

| Request Type | Detection Keywords | Agents |
|--------------|-------------------|--------|
| **Code Review** | review, audit, check, security | security-reviewer, code-quality-auditor, architecture-advisor, requirements-analyst, pe-reviewer |
| **Feature Dev** | add, implement, build, create, feature | architecture-advisor, security-reviewer, ux-designer, requirements-analyst, sde-iii |
| **Planning** | plan, design, strategy, roadmap | pm, pe-designer, requirements-analyst, finance-consultant, strategic-advisor |
| **Research** | research, analyze, compare, investigate | research-director, fact-checker, source-evaluator, industry-signal-scout, synthesis-writer |
| **Content** | write, article, content, blog | synthesis-writer, ux-designer, pm, strategic-advisor, research-director |
| **Testing** | test, qa, validation, coverage | test-writer, ux-tester, validation-specialist, security-reviewer, code-quality-auditor |
| **Operations** | deploy, release, ci, infra | release-manager, ci-executor, integration-specialist, security-reviewer, pe-reviewer |

## Model Tiering by Agent

| Tier | Model | Agents |
|------|-------|--------|
| **Validation** | Haiku | code-quality-auditor, ci-executor, docs-writer, release-manager, api-schema, fact-checker, source-evaluator, finance-consultant |
| **Analysis** | Sonnet | architecture-advisor, security-reviewer, requirements-analyst, pe-reviewer, ux-designer, sde-iii, pm, pe-designer, test-writer, debugger, perf-optimizer, integration-specialist, research-director, planner |
| **Synthesis** | Opus | synthesis-writer, dissent-moderator, cos |

## Custom Persona Generation

When no agents match (all scores = 0):

```markdown
## Persona Template

### {{PERSONA_NAME}}
**Role**: {{ROLE_DESCRIPTION}}
**Expertise**: {{DOMAIN_EXPERTISE}}
**Perspective**: {{UNIQUE_VIEWPOINT}}
**Critique Focus**: {{WHAT_TO_LOOK_FOR}}

### Review Instructions
1. Analyze request from your perspective
2. Identify P0/P1/P2 issues
3. Provide specific, actionable recommendations
4. Flag anything requiring human decision
```

Save to: `projects/NNN-name/.qralph/custom-personas/`

## Agent Registry Location

`.claude/agents/registry.json`

Contains for each agent:
- `id`: Agent identifier
- `name`: Display name
- `category`: design, security, quality, planning, etc.
- `model_tier`: haiku, sonnet, opus
- `capabilities`: What the agent can do
- `keywords`: Trigger words for selection
