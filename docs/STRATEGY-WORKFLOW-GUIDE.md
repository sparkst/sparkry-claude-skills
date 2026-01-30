# Strategy Workflow - Strategic Planning System

## Overview

Strategy Workflow provides executive-level strategic planning tools: COS (Chief of Staff) orchestration, PR-FAQ generation, Buy-vs-Build analysis, PMF validation, and Tenets documentation.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install Strategy Workflow

```
/plugin install strategy-workflow@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Included Components

### Agents
| Agent | Role |
|-------|------|
| **COS** | Chief of Staff - orchestrates strategy |
| **Strategic Advisor** | Market positioning, GTM |
| **PM** | Product management, JTBD |
| **Finance Consultant** | Unit economics, pricing |
| **Legal Expert** | Compliance, contracts |

### Skills
| Skill | Purpose |
|-------|---------|
| **cos/intake** | Strategic request intake |
| **cos/prfaq** | PR-FAQ document generation |
| **cos/buy-vs-build** | Build vs buy analysis |
| **cos/pmf-validation** | Product-market fit assessment |
| **cos/tenets** | Organizational principles |
| **cos/security-review** | Security posture assessment |

------------------------------------------------------------------------

## Usage

### PR-FAQ Generation

```
/prfaq "Launch AI-powered code review tool"
```

Creates Amazon-style PR-FAQ document with:
- Press Release (the vision)
- FAQ (anticipated questions)
- Internal FAQ (implementation details)

------------------------------------------------------------------------

### Buy vs Build Analysis

```
/buy-vs-build "Customer support chatbot"
```

**Output includes:**
- 3-year TCO comparison
- Build effort estimation
- Vendor evaluation matrix
- Risk analysis
- Recommendation with rationale

------------------------------------------------------------------------

### PMF Validation

```
/pmf-validate "Our new analytics dashboard"
```

**Assesses:**
- Problem-solution fit
- Target market clarity
- Value proposition strength
- Competitive differentiation
- Growth indicators

------------------------------------------------------------------------

### Tenets Documentation

```
/tenets "Engineering organization principles"
```

Creates Amazon-style tenets:
- Clear principles
- Prioritization guidance ("X over Y")
- Application examples
- Anti-patterns

------------------------------------------------------------------------

## PR-FAQ Structure

### Press Release Section
```markdown
# [Product Name] Launches [Value Proposition]

[City, Date] — [Company] today announced...

## The Problem
[Customer pain point]

## The Solution
[How product solves it]

## Quote from Leadership
"[Vision statement]" — [Executive]

## Customer Quote
"[Testimonial]" — [Customer]

## Getting Started
[Call to action]
```

### FAQ Section
```markdown
## Frequently Asked Questions

### For Customers
Q: How much does it cost?
A: [Pricing]

Q: How is this different from [competitor]?
A: [Differentiation]

### For Internal Teams
Q: What's the technical architecture?
A: [Architecture overview]

Q: What's the go-to-market strategy?
A: [GTM plan]
```

------------------------------------------------------------------------

## Buy vs Build Framework

### Evaluation Criteria

| Criteria | Weight | Build | Buy |
|----------|--------|-------|-----|
| Time to market | 25% | 6 months | 2 weeks |
| Total cost (3yr) | 25% | $500K | $300K |
| Customization | 20% | Full | Limited |
| Maintenance | 15% | Internal | Vendor |
| Strategic value | 15% | High | Medium |

### TCO Calculator

Includes:
- Development costs
- Infrastructure costs
- Maintenance/ops costs
- Opportunity costs
- Vendor licensing
- Integration costs

------------------------------------------------------------------------

## PMF Validation Framework

### Signals Assessed

| Signal | What It Measures |
|--------|------------------|
| **Pull** | Organic demand, word of mouth |
| **Retention** | Users coming back |
| **Willingness to Pay** | Price sensitivity |
| **Referral** | NPS, recommendations |
| **Usage** | Engagement depth |

### PMF Score

- **Strong PMF:** Score 80+, scale aggressively
- **Emerging PMF:** Score 60-79, iterate and test
- **Weak PMF:** Score <60, pivot or refocus

------------------------------------------------------------------------

## COS Orchestration

The COS agent coordinates strategic work:

```
@cos "Evaluate entering the European market"
```

COS will:
1. Break down into research questions
2. Assign to appropriate agents
3. Coordinate deliverables
4. Synthesize into executive brief

------------------------------------------------------------------------

## Strategic Deliverables

### One-Pager
- Executive summary
- Key metrics
- Decision requested
- Timeline

### Options Matrix
- Alternatives compared
- Criteria weighted
- Recommendation highlighted

### Business Case
- Problem statement
- Proposed solution
- Financial analysis
- Risk assessment
- Implementation plan

------------------------------------------------------------------------

## Integration with QRALPH

Strategy agents are in QRALPH's pool:

```
QRALPH "Should we build or buy a CRM?" --mode planning
→ Spawns: strategic-advisor, pm, finance-consultant,
          architecture-advisor, requirements-analyst
```

------------------------------------------------------------------------

## Use Cases

### Product Launch
```
/prfaq "New product launch"
→ Creates vision document
```

### Investment Decision
```
/buy-vs-build "Data pipeline solution"
→ Creates financial analysis
```

### Organizational Change
```
/tenets "New team principles"
→ Creates guiding tenets
```

### Market Entry
```
@strategic-advisor "Evaluate APAC expansion"
→ Creates market analysis
```

------------------------------------------------------------------------

## Related Plugins

- **research-workflow** - Deep research for strategy
- **qshortcuts-ai** - QARCH for technical strategy

------------------------------------------------------------------------

## Troubleshooting

### Analysis too generic

Provide specific context:
- Company size/stage
- Budget constraints
- Timeline requirements
- Strategic priorities

### Missing financial data

Provide estimates or ranges for:
- Revenue targets
- Budget constraints
- Team size/cost

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
