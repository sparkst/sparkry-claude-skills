# Research Workflow Plugin

Multi-agent research orchestration with fact-checking, source evaluation, and synthesis.

## Overview

The Research Workflow plugin provides a complete system for conducting rigorous, evidence-based research. It orchestrates multiple specialist agents to discover sources, validate claims, manage dissent, and produce proposal-first deliverables with executive summaries.

## Key Features

- **Multi-Agent Orchestration**: Coordinate specialists (fact-checker, source-evaluator, dissent-moderator, synthesis-writer) in parallel
- **Tiered Source System**: 4-tier source classification (Tier-1: authoritative, Tier-2: reputable, Tier-3: community, Tier-4: unverified)
- **Claim Validation**: Soft quality gates requiring ≥2 independent Tier-1 sources for load-bearing claims
- **Dissent Management**: Options matrix builder for synthesizing disagreements into decision-ready alternatives
- **Proposal-First Output**: Executive summaries (1 page) with appendices for depth
- **Date Alignment**: Automatic validation that sources match claim timeframes

## Agents Included

### 1. research-director
Orchestrates the complete research workflow from intake to final deliverable.

**Responsibilities:**
- Parse research requests
- Create research plans with sub-questions and claim budgets
- Fan out to specialist agents in parallel
- Manage dissent through options matrices
- Synthesize findings into deliverables

### 2. fact-checker
Validates that all load-bearing claims have sufficient evidence.

**Responsibilities:**
- Extract claims from deliverables
- Validate ≥2 independent Tier-1 sources per claim
- Check date alignment between claims and sources
- Issue soft-gate warnings for insufficient evidence
- Output `research/claims.json`

### 3. source-evaluator
Evaluates source credibility using the 4-tier framework.

**Responsibilities:**
- Classify sources (Tier 1-4)
- Check independence (no circular citations)
- Verify recency (publication dates align with claims)
- Output `research/source_review.json`

### 4. dissent-moderator
Synthesizes specialist disagreements into decision-ready options.

**Responsibilities:**
- Collect position memos from specialists
- Identify conflicting recommendations
- Create 2-3 viable options with pros/cons/risks
- Assess reversibility, cost, time-to-impact
- Output `research/options_matrix.json`

### 5. synthesis-writer
Creates proposal-first deliverables with executive summaries.

**Responsibilities:**
- Transform validated research into polished deliverable
- Create 1-page executive summary
- Compile appendices (sources, claims, dissent, debate)
- Output `research/proposal.md`

## Skills Included

### research/plan
Creates structured research plans with sub-questions, query strategy, claim budgets, and source tier rules.

**Use when:** Starting any research request

**Outputs:** `research/plan.json`

### research/fact-check
Validates load-bearing claims require ≥2 independent Tier-1 sources. Flags stale/mismatched dates.

**Use when:** Before marking claims as validated

**Tools:** `scripts/date_checker.py`

**Outputs:** `research/claims.json`

### research/industry-scout
Searches for best-of-best sources using web search tools. Filters out noise, SEO spam, AI-generated content.

**Use when:** Finding canonical, primary, independent evidence

**Network access:** Required

**Outputs:** `research/sources.json`

### research/options-matrix
Synthesizes disagreements into 2-3 viable options with pros/cons, risk, reversibility, confidence, cost, time-to-impact.

**Use when:** Specialists disagree

**Outputs:** `research/options_matrix.json`

### research/source-policy
Evaluates source credibility using tier system (Tier-1 to Tier-4) with independence and recency checks.

**Use when:** Rating sources

**Outputs:** `research/source_review.json`

### research/web-exec
Orchestrates parallel web searches. Handles rate limiting, deduplication, source extraction.

**Use when:** Executing queries from research plan

**Network access:** Required

**Tools:** `scripts/parallel_search.py`

**Outputs:** `research/sources.json`

## Installation

1. Download the plugin bundle
2. Place in your Claude Code plugins directory
3. Enable in Claude Code settings

## Usage

### Basic Research Workflow

```
User: "Research the market positioning for an AI coding agent targeting solo developers."

research-director:
  1. Loads research-plan skill
  2. Creates research/plan.json with:
     - Sub-questions (TAM, competitors, unmet needs, etc.)
     - Claim budget (≤10)
     - Tier requirements (Tier-1 required: true)

  3. Fans out to specialists:
     - industry-signal-scout → discovers sources
     - source-evaluator → tiers sources
     - fact-checker → validates claims

  4. If dissent exists:
     - dissent-moderator → creates options matrix

  5. synthesis-writer → produces final deliverable

  6. Output: research/proposal.md
```

### Research Artifacts

After completion, you'll have:
- `research/plan.json` - Research plan with sub-questions
- `research/sources.json` - Discovered sources with metadata
- `research/source_review.json` - Source tier ratings
- `research/claims.json` - Claim validation results
- `research/options_matrix.json` - Options matrix (if dissent exists)
- `research/proposal.md` - Final deliverable

## The Four-Tier Source System

### Tier-1: Primary & Authoritative
- Government agencies (Census, SEC)
- Peer-reviewed journals
- Top-tier research firms (Gartner, McKinsey)
- Official technical documentation

**Use for:** Market sizing, technical specs, regulatory requirements, financial data

### Tier-2: Reputable Secondary
- Major publications (WSJ, Bloomberg, NYT)
- Industry analyst reports (Forrester, IDC)
- Technical books from recognized publishers

**Use for:** Competitive analysis, trend identification, qualitative insights

### Tier-3: Community & Practitioner
- Reddit, Hacker News discussions
- Stack Overflow insights
- Indie blog posts
- Product reviews

**Use for:** Customer pain points, unmet needs, real-world usage patterns

### Tier-4: Unverified or Promotional
- Marketing materials
- AI-generated content
- Anonymous sources
- Press releases without corroboration

**Use with caution:** Only as directional signals; require Tier-1 or Tier-2 corroboration

## Claim Validation Rules

### High-Stakes Research (Investment, Strategy, Compliance)
- **Minimum:** 2 independent Tier-1 sources
- **Acceptable fallback:** 1 Tier-1 + 1 Tier-2
- **Recency:** Publication date within 180 days for market/trend claims
- **Independence:** No citation relationship between sources

### Medium-Stakes Research (Product decisions, Feature prioritization)
- **Minimum:** 1 Tier-1 + 1 Tier-2, OR 2 Tier-2 sources
- **Recency:** Publication date within 365 days
- **Independence:** Required

### Low-Stakes Research (Exploration, Brainstorming)
- **Minimum:** 2 Tier-2 sources
- **Recency:** Best effort
- **Independence:** Preferred but not required

## Soft Quality Gates

The plugin uses soft gates (warn but don't block) when:
- <80% of claims have ≥2 Tier-1 sources
- Source dates are stale (>180 days for current claims)
- Sources lack independence (circular citations)

**Philosophy:** Informed choice over rigid enforcement. The user can acknowledge warnings and proceed if acceptable for the decision stakes.

## Success Criteria

- **G1 (Token Efficiency):** Achieve ≥30% reduction vs baseline
- **G2 (Cycle Time):** Complete research in ≤8 minutes
- **G3 (Determinism):** ≥95% success on scripted steps
- **G4 (Quality):** ≥90% claims with ≥2 Tier-1 sources
- **G5 (Governance):** 100% skills loaded are trusted

## Examples

### Market Research
**Request:** "What is the TAM for AI coding agents in 2025?"

**Research Plan:**
- Sub-questions: TAM size, growth trends, key segments, competitors
- Claim budget: 5
- Tier-1 required: Yes

**Sources Found:**
- Gartner market guide (Tier-1)
- IDC forecast (Tier-1)
- Bloomberg article (Tier-2)

**Claims Validated:**
- "TAM is $5.2B in 2025" → 2 Tier-1 sources (approved)
- "Growing 18% YoY" → 1 Tier-1 source (warning)

### Competitive Analysis with Dissent
**Request:** "How should we position our AI coding agent for solo developers?"

**Specialists:**
- PM recommends: Indie developer positioning
- Strategic-advisor recommends: Enterprise positioning

**Dissent Resolution:**
- dissent-moderator creates options matrix
- Option A: Enterprise (higher TAM, longer sales cycles, low reversibility)
- Option B: Indie (faster MVP, high reversibility, lower WTP)

**Recommendation:** Option B (indie) based on highest confidence + best reversibility

## Best Practices

1. **Set Clear Claim Budgets:** Limit to ≤10 load-bearing claims per deliverable
2. **Define Tier Requirements Upfront:** High-stakes = Tier-1 required
3. **Use Parallel Execution:** Fan out to specialists concurrently
4. **Preserve Dissent:** Don't force consensus; structure disagreement
5. **Check Date Alignment:** Verify sources match claim timeframes
6. **Validate Independence:** Ensure sources aren't citing each other

## Anti-Patterns to Avoid

- Too broad requests ("Research everything about AI")
- Vague sub-questions ("What about competitors?")
- Generic search queries ("AI tools")
- No claim budget ("Find all the facts")
- No tier rules ("Just get whatever you find")
- Forcing consensus when specialists disagree

## License

MIT

## Support

For issues, questions, or contributions, contact skills@sparkry.ai

## Version History

### 1.0.0 (Initial Release)
- Multi-agent research orchestration
- 4-tier source classification
- Claim validation with soft gates
- Dissent management via options matrices
- Proposal-first deliverables
- Date alignment checking
- Web search orchestration with rate limiting
