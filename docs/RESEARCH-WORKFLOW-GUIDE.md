# Research Workflow - Research & Analysis Agents

## Overview

Research Workflow provides a complete research team: Research Director for orchestration, Fact Checker for verification, Source Evaluator for credibility, Industry Scout for trends, and Synthesis Writer for deliverables.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install Research Workflow

```
/plugin install research-workflow@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Included Agents

| Agent | Role | Specialty |
|-------|------|-----------|
| **Research Director** | Orchestrator | Coordinates research agents |
| **Fact Checker** | Verification | Validates claims with sources |
| **Source Evaluator** | Credibility | Assesses source reliability |
| **Industry Scout** | Trends | Discovers emerging patterns |
| **Synthesis Writer** | Deliverables | Creates executive summaries |
| **Dissent Moderator** | Conflict Resolution | Synthesizes disagreements |

------------------------------------------------------------------------

## Included Skills

| Skill | Purpose |
|-------|---------|
| **research/plan** | Create research plans |
| **research/fact-check** | Verify claims |
| **research/source-policy** | Evaluate sources |
| **research/web-exec** | Execute web searches |
| **research/options-matrix** | Compare alternatives |
| **research/industry-scout** | Track industry trends |

------------------------------------------------------------------------

## Usage

### Invoke Agents Directly

```
@research-director Analyze the competitive landscape for AI coding assistants
```

```
@fact-checker Verify these claims about market size
```

```
@source-evaluator Rate the credibility of these sources
```

### Use Research Skills

```
/research-plan "Investigate B2B SaaS pricing strategies"
```

```
/fact-check "AI market will reach $500B by 2030"
```

------------------------------------------------------------------------

## Agent Details

### Research Director

**Purpose:** Orchestrate multi-agent research projects

**Capabilities:**
- Breaks down research questions
- Assigns subtasks to specialist agents
- Synthesizes findings
- Manages research timeline
- Resolves conflicting information

------------------------------------------------------------------------

### Fact Checker

**Purpose:** Verify claims with evidence

**Requirements:**
- 2+ independent Tier-1 sources per claim
- Recent sources (within 2 years for fast-moving topics)
- Primary sources preferred

**Output:**
```markdown
## Fact Check: [Claim]

**Verdict:** Supported / Partially Supported / Not Supported

**Sources:**
1. [Source] - Tier 1 - [Date]
2. [Source] - Tier 1 - [Date]

**Notes:** [Additional context]
```

------------------------------------------------------------------------

### Source Evaluator

**Purpose:** Assess source credibility

**4-Tier Framework:**

| Tier | Source Type | Trust Level |
|------|-------------|-------------|
| **Tier 1** | Primary sources, peer-reviewed | Highest |
| **Tier 2** | Established publications, official reports | High |
| **Tier 3** | Industry blogs, analyst reports | Medium |
| **Tier 4** | Social media, anonymous sources | Low |

------------------------------------------------------------------------

### Industry Scout

**Purpose:** Discover trends and signals

**Capabilities:**
- Tracks industry news
- Identifies emerging patterns
- Monitors competitor movements
- Filters signal from noise
- Prioritizes by relevance

------------------------------------------------------------------------

### Synthesis Writer

**Purpose:** Create executive-ready deliverables

**Output formats:**
- 1-page executive summary
- Options matrix with recommendations
- Competitive analysis report
- Market sizing document

------------------------------------------------------------------------

## Research Workflow

### Standard Research Project

```
1. Research Director receives question
   ↓
2. Creates research plan with subtasks
   ↓
3. Industry Scout gathers raw intelligence
   ↓
4. Source Evaluator assesses credibility
   ↓
5. Fact Checker verifies key claims
   ↓
6. Dissent Moderator resolves conflicts
   ↓
7. Synthesis Writer creates deliverable
```

------------------------------------------------------------------------

## Integration with QRALPH

Research agents are in QRALPH's pool for research tasks:

```
QRALPH "Compare cloud providers for our infrastructure" --mode planning
→ Spawns: research-director, fact-checker, source-evaluator,
          industry-scout, synthesis-writer
```

------------------------------------------------------------------------

## Use Cases

### Competitive Analysis
```
@research-director "Analyze top 5 competitors in [market]"
```

### Market Sizing
```
@research-director "Size the TAM/SAM/SOM for [product]"
```

### Due Diligence
```
@research-director "Research [company] for potential partnership"
```

### Trend Analysis
```
@industry-scout "What are emerging trends in [industry]?"
```

------------------------------------------------------------------------

## Options Matrix Output

For comparison research:

```markdown
## Options Matrix: [Decision]

| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Cost | $100/mo | $200/mo | $150/mo |
| Features | 8/10 | 9/10 | 7/10 |
| Support | 24/7 | Business hrs | 24/7 |
| Security | SOC2 | SOC2, HIPAA | SOC2 |

**Recommendation:** Option B for enterprises, Option A for startups

**Reasoning:** [Detailed analysis]
```

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-support** - QIDEA for quick research
- **strategy-workflow** - For strategic analysis

------------------------------------------------------------------------

## Troubleshooting

### Research too shallow

Specify depth:
- "Deep dive" for comprehensive analysis
- "Quick scan" for overview
- Specific questions to answer

### Sources not recent enough

Specify recency requirements:
- "Sources from 2025 or later"
- "Focus on last 6 months"

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
