# QRALPH Agent Selection v4.0

## Selection Priority

1. **User-specified**: `--agents security,architecture,pm` (max 7)
2. **Discovery-driven**: Based on plugin/skill/agent scanning + request analysis
3. **Fallback defaults**: Hardcoded sets when discovery unavailable

## Modes

### Coding Mode: 3-7 Agents
Full team for feature development, code review, and complex tasks.

### Work Mode: 1-3 Agents (v4.0)
Lightweight team for writing, research, and business tasks.

## Dynamic Selection Algorithm

### Step 1: Classify Request Domains

The orchestrator classifies the request into one or more domains:

| Domain | Keywords |
|--------|----------|
| security | auth, encrypt, token, vulnerability, owasp, injection |
| frontend | ui, ux, page, component, form, react, css, mobile |
| backend | api, endpoint, database, query, graphql, middleware |
| architecture | system design, scalability, refactor, pattern, dependency |
| testing | test, qa, validation, coverage, e2e, mock |
| devops | deploy, ci, docker, kubernetes, infrastructure |
| content | write, article, blog, documentation, guide |
| research | research, analyze, compare, investigate, benchmark |
| strategy | strategy, plan, roadmap, business, market, growth |
| data | analytics, metrics, dashboard, chart, visualization |
| performance | optimize, speed, latency, profiling, bottleneck |
| compliance | gdpr, ccpa, regulation, privacy, audit, legal |

### Step 2: Discover Available Capabilities

Scan the environment for all available resources:

```
.claude/agents/*.md       → Custom agent definitions
.claude/plugins/*/        → Installed plugins
Task tool subagent_types  → Built-in agents
System prompt skills      → Available skills
```

### Step 3: Score & Rank

Each capability gets a relevance score (0.0 - 1.0):

```python
score = (
    domain_overlap * 0.6 +      # How many domains match
    name_keyword_match * 0.25 +  # Agent name words in request
    description_match * 0.15     # Description words in request
)
```

### Step 4: Select with Constraints

#### Coding Mode (3-7 agents)

```python
# Complexity determines team size
complexity = estimate_complexity(request, domains)
target_count = 3 to 7 agents

# Diversity constraint: max 2 per category
for candidate in ranked_candidates:
    if candidate.relevance < 0.1:
        break  # Below threshold
    if category_count[candidate.category] < 2:
        select(candidate)
    if len(selected) >= target_count:
        break

# Ensure minimum of 3
if len(selected) < 3:
    fill_from_top_candidates()
```

#### Work Mode (1-3 agents, v4.0)

```python
def estimate_work_complexity(request, domains):
    words = len(request.split())
    score = len(domains) + (1 if words > 50 else 0) + (1 if words > 100 else 0)
    return min(max(score // 2, 1), 3)  # clamp to 1-3
```

Work mode uses lighter agent selection focused on the task type:
- Writing tasks: synthesis-writer, docs-writer
- Research tasks: research-director, fact-checker
- Strategy tasks: strategic-advisor, pm
- Mixed tasks: pm + domain specialist

### Step 5: Match Skills to Agents

For each selected agent, find skills with overlapping domains:

```python
for agent in selected:
    agent.skills = [
        skill for skill in relevant_skills
        if set(agent.domains) & set(skill.domains)
    ]
```

### Step 6: Discover Work Skills (Work Mode, v4.0)

```python
WORK_SKILL_KEYWORDS = {
    "write": ["QWRITE"],
    "research": ["web-exec"],
    "automate": [],
    "scan": [],
    "feedback": ["QFEEDBACK"],
    "presentation": ["QPPT"]
}
```

### Step 7: Code Signal Detection (Work Mode, v4.0)

If work mode detects code signals, TDD mandate is included in agent prompt:

```python
CODE_SIGNAL_KEYWORDS = {
    "script", "function", "api", "automate", "endpoint",
    "database", "query", "component", "module", "class",
    "import", "deploy", "test", "debug", "refactor"
}

def contains_code_signals(request):
    words = set(re.findall(r'\b\w+\b', request.lower()))
    return bool(words & CODE_SIGNAL_KEYWORDS)
```

## Complexity Estimation (Coding Mode)

| Signal | Score Impact |
|--------|-------------|
| 1-2 domains | +1-2 |
| 3+ domains | +3+ |
| Request > 15 words | +1 |
| Request > 30 words | +2 |
| "and", "with", "also" keywords | +1 each |
| "integrate", "migrate", "refactor" | +1 each |
| "comprehensive", "full-stack" | +1 each |

| Total Score | Agent Count |
|-------------|-------------|
| 0-2 | 3 agents |
| 3-4 | 4 agents |
| 5-6 | 5 agents |
| 7-8 | 6 agents |
| 9+ | 7 agents |

## Escalation Triggers (Work Mode -> Coding Mode, v4.0)

Work mode automatically escalates to full coding mode when:

| Trigger | Detection |
|---------|-----------|
| Multi-domain complexity | domains > 3 |
| Critical findings | P0 findings in synthesis |
| Healing failures | heal_attempts >= 3 |
| User request | ESCALATE in CONTROL.md |

## Agent Registry

### Core Development
| Agent | Domains | Model | Category |
|-------|---------|-------|----------|
| security-reviewer | security, compliance | sonnet | security |
| architecture-advisor | architecture, backend, performance | sonnet | architecture |
| sde-iii | backend, architecture, testing | sonnet | implementation |
| code-quality-auditor | testing, architecture | haiku | quality |
| pe-reviewer | architecture, security, performance | sonnet | quality |
| pe-designer | architecture, backend | sonnet | architecture |
| test-writer | testing | sonnet | testing |
| debugger | backend, testing, performance | sonnet | implementation |
| perf-optimizer | performance, backend | sonnet | performance |
| integration-specialist | backend, devops, architecture | sonnet | integration |

### Design & UX
| Agent | Domains | Model | Category |
|-------|---------|-------|----------|
| ux-designer | frontend, data | sonnet | design |
| ux-tester | frontend, testing | sonnet | testing |
| validation-specialist | testing, quality | sonnet | testing |

### Planning & Strategy
| Agent | Domains | Model | Category |
|-------|---------|-------|----------|
| pm | strategy, research | sonnet | planning |
| requirements-analyst | strategy, architecture | sonnet | planning |
| strategic-advisor | strategy, research | sonnet | strategy |
| finance-consultant | strategy, data | haiku | strategy |
| legal-expert | compliance, strategy | sonnet | compliance |
| cos | strategy | opus | strategy |

### Research & Content
| Agent | Domains | Model | Category |
|-------|---------|-------|----------|
| research-director | research | sonnet | research |
| fact-checker | research, content | haiku | research |
| source-evaluator | research | haiku | research |
| industry-signal-scout | research, strategy | sonnet | research |
| dissent-moderator | research, strategy | opus | research |
| synthesis-writer | content, research | opus | content |
| docs-writer | content | haiku | content |

## Skill Registry

| Skill | Domains | When Used |
|-------|---------|-----------|
| frontend-design | frontend | UI/component work |
| writing | content | Articles, copy, documentation |
| feature-dev | backend, architecture, testing | Feature implementation |
| code-review | security, quality, architecture | Code review tasks |
| pr-review-toolkit | security, quality, testing | PR review |
| research-workflow | research | Research tasks |

## Model Tiering

| Tier | Model | Cost/1M tokens | Used For |
|------|-------|----------------|----------|
| Validation | haiku | $0.25 | Simple checks, formatting, known pattern fixes |
| Analysis | sonnet | $3.00 | Code review, architecture, security |
| Synthesis | opus | $15.00 | Final synthesis, complex reasoning |

## Default Agent Sets (Fallback)

Used when discovery is unavailable:

### Coding Mode
| Request Type | Agents |
|-------------|--------|
| Code Review | security-reviewer, code-quality-auditor, architecture-advisor |
| Feature Dev | architecture-advisor, security-reviewer, sde-iii |
| Frontend | ux-designer, security-reviewer, sde-iii |
| Planning | pm, pe-designer, requirements-analyst, strategic-advisor |
| Research | research-director, fact-checker, source-evaluator |
| Content | synthesis-writer, pm, ux-designer |
| Testing | test-writer, ux-tester, validation-specialist |

### Work Mode (v4.0)
| Request Type | Agents |
|-------------|--------|
| Writing | synthesis-writer |
| Research | research-director, fact-checker |
| Strategy | strategic-advisor, pm |
| Mixed | pm + domain specialist |
