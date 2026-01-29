---
name: Research Planning
description: Creates structured research plans with sub-questions, query strategy, claim budgets, and source tier rules. Use when starting any research request.
version: 1.0.0
dependencies: none
---

# Research Planning Skill

## Overview

This skill provides a systematic framework for planning research requests. It ensures every research effort begins with a clear structure: breaking down the topic into sub-questions, defining search queries, setting claim budgets, and establishing source quality rules.

**When to use this skill:**
- At the start of any research request
- When the user asks to "research," "investigate," or "analyze" a topic
- Before any web searches or data gathering begins

## Core Principles

1. **Claim Budget**: Limit load-bearing claims to ≤10 per deliverable to maintain signal-over-noise
2. **Tiered Sources**: Establish tier requirements upfront (Tier-1 for high-stakes claims)
3. **Sub-Questions**: Break complex topics into 3-7 focused sub-questions
4. **Query Strategy**: Define search approach before execution

## The Research Plan Template

Every research request should produce a `research/plan.json` file with the following structure:

```json
{
  "topic": "AI coding agents market positioning",
  "objective": "Recommend positioning strategy based on market analysis",
  "claim_budget": 10,
  "sub_questions": [
    "What is the total addressable market (TAM) for AI coding agents?",
    "Who are the top 5 competitors and what are their positioning strategies?",
    "What unmet needs exist in the current market?",
    "What are the key differentiation opportunities?",
    "What pricing models are most common?"
  ],
  "queries": [
    "AI coding agents market size 2025",
    "Claude Code vs Cursor vs GitHub Copilot comparison",
    "AI coding tools unmet needs survey",
    "AI pair programming pricing models",
    "Cursor user complaints Reddit",
    "GitHub Copilot limitations"
  ],
  "tier_rules": {
    "tier1_required": true,
    "independence_required": true,
    "minimum_tier1_sources_per_claim": 2,
    "acceptable_tier2_as_supplement": true
  },
  "success_criteria": {
    "min_sources_per_sub_question": 3,
    "max_claim_staleness_days": 180,
    "required_claim_types": ["market_size", "competitive_landscape", "customer_needs"]
  },
  "estimated_depth": "medium",
  "estimated_duration_minutes": 30
}
```

### Field Definitions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `topic` | string | High-level research subject | "AI coding agents market" |
| `objective` | string | What decision/output the research supports | "Recommend positioning" |
| `claim_budget` | number | Max load-bearing claims (≤10 recommended) | 10 |
| `sub_questions` | array | 3-7 focused questions that decompose the topic | See template |
| `queries` | array | Specific search strings for web tools | See template |
| `tier_rules` | object | Source quality requirements | See template |
| `success_criteria` | object | Minimum standards for completion | See template |
| `estimated_depth` | string | "quick", "medium", "deep" | "medium" |
| `estimated_duration_minutes` | number | Expected time to complete | 30 |

## How to Create a Research Plan

### Step 1: Understand the User's Request

Parse the user's request to identify:
- **Core topic**: What are we researching?
- **Purpose**: Why are we researching it? (decision, comparison, validation, exploration)
- **Constraints**: Are there time, depth, or scope limitations?

**Example User Request:**
> "Research AI coding agents market and recommend positioning for a solo founder product"

**Parsed:**
- Topic: AI coding agents market
- Purpose: Positioning recommendation
- Context: Solo founder (implies: budget-constrained, need for differentiation, focus on niche)

### Step 2: Decompose into Sub-Questions

Break the topic into 3-7 specific, answerable questions using the "5W1H" framework:

- **What**: What is this? What does it do?
- **Who**: Who are the players? Who are the customers?
- **Where**: Where is the market concentrated?
- **When**: When did this emerge? What's the timeline?
- **Why**: Why do customers use this? Why now?
- **How**: How does it work? How do competitors position?

**Example Sub-Questions:**
1. What is the TAM for AI coding agents?
2. Who are the top competitors and how do they position?
3. What unmet customer needs exist?
4. What differentiation opportunities are available for a solo founder?
5. What pricing models are most viable for indie products?

### Step 3: Define Search Queries

For each sub-question, generate 2-3 specific search queries that will yield high-quality results.

**Best Practices:**
- Use specific terminology (not just generic terms)
- Include year for recency ("2025" for current data)
- Use comparison phrases ("vs", "compared to")
- Use negative sentiment queries to find pain points ("complaints", "limitations", "problems with")

**Example Queries:**
- "AI coding agents market size 2025" → TAM data
- "Cursor vs GitHub Copilot comparison" → competitive intel
- "AI coding tools frustrations Reddit" → unmet needs
- "solo developer AI tools pricing" → pricing models

### Step 4: Set Claim Budget and Tier Rules

**Claim Budget:**
- Default: 10 load-bearing claims maximum
- Quick research: 5 claims
- Deep research: 10-15 claims (only if justified)

**Tier Rules:**
Default for high-stakes research:
```json
{
  "tier1_required": true,
  "independence_required": true,
  "minimum_tier1_sources_per_claim": 2
}
```

For exploratory/low-stakes research:
```json
{
  "tier1_required": false,
  "minimum_tier2_sources_per_claim": 2
}
```

### Step 5: Define Success Criteria

Set clear exit criteria so you know when research is "done":

```json
{
  "min_sources_per_sub_question": 3,
  "max_claim_staleness_days": 180,
  "required_claim_types": ["market_size", "competitive_landscape", "customer_needs"]
}
```

### Step 6: Estimate Depth and Duration

| Depth | Duration | Sub-Questions | Queries | Claim Budget |
|-------|----------|---------------|---------|--------------|
| Quick | 10-15 min | 3 | 3-5 | 5 |
| Medium | 20-40 min | 5 | 8-12 | 10 |
| Deep | 60-120 min | 7 | 15-25 | 15 |

## Common Patterns

### Pattern: Market Research
**Sub-Questions:**
1. What is the TAM/SAM/SOM?
2. Who are the top 5-10 players?
3. What are the growth trends (YoY, CAGR)?
4. What are the key market segments?
5. What regulatory/macro factors affect the market?

**Tier Rules:** Tier-1 required (market sizing needs authoritative sources)

### Pattern: Competitive Analysis
**Sub-Questions:**
1. Who are the direct competitors?
2. What are their positioning strategies?
3. What are their pricing models?
4. What do users complain about? (pain points)
5. What are the gaps in their offerings?

**Tier Rules:** Tier-1 + Tier-2 acceptable (mix of analyst reports and user feedback)

### Pattern: Technology Evaluation
**Sub-Questions:**
1. What is the technology and how does it work?
2. What are the key use cases?
3. What are the limitations/trade-offs?
4. Who are the vendors/open-source projects?
5. What are the adoption trends?

**Tier Rules:** Tier-1 for technical accuracy (official docs, peer-reviewed papers)

### Pattern: Customer Discovery
**Sub-Questions:**
1. Who is the target customer (persona)?
2. What job are they trying to do (JTBD)?
3. What are their current alternatives/workarounds?
4. What are the pain points with current solutions?
5. What would they be willing to pay (WTP)?

**Tier Rules:** Tier-2 acceptable (surveys, interviews, community discussions)

## Anti-Patterns to Avoid

❌ **Too Broad**: "Research everything about AI"
✅ **Focused**: "Research AI coding agents market for solo dev positioning"

❌ **Vague Sub-Questions**: "What about competitors?"
✅ **Specific**: "Who are the top 5 competitors and what are their pricing models?"

❌ **Generic Queries**: "AI tools"
✅ **Targeted**: "AI coding tools limitations site:reddit.com"

❌ **No Claim Budget**: "Find all the facts"
✅ **Constrained**: "Identify the 10 most important claims"

❌ **No Tier Rules**: "Just get whatever you find"
✅ **Quality Gated**: "Tier-1 sources required for market size claims"

## Quality Checklist

Before proceeding with research execution, verify:

- [ ] Topic and objective are crystal clear
- [ ] Sub-questions are specific and answerable
- [ ] Queries are targeted (not generic)
- [ ] Claim budget is set (≤10 for most cases)
- [ ] Tier rules match the stakes of the decision
- [ ] Success criteria define "done"
- [ ] Estimated depth/duration are realistic

## Output

After using this skill, the research-director agent should create `research/plan.json` following the template above and share it with the user for confirmation before proceeding with web searches.

**Example Confirmation Prompt:**
> "I've created a research plan for '{topic}'. It includes {n} sub-questions and will target {m} queries. Claim budget is set to {budget}. Estimated duration: {duration} minutes. Shall I proceed with the web research phase?"

## References

- See `resources/tier-definitions.md` for source tier taxonomy
- See `resources/query-strategies.md` for advanced search techniques
- See `templates/research-plan-template.json` for the JSON schema
