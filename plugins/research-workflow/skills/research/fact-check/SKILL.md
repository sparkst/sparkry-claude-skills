---
name: Fact Checking Protocol
description: Validates load-bearing claims require ≥2 independent Tier-1 sources. Flags stale/mismatched dates. Use before marking claims as validated.
version: 1.0.0
dependencies: python>=3.8
---

# Fact Checking Protocol

## Overview

This skill enforces rigorous claim validation to ensure research deliverables are grounded in high-quality, independently corroborated evidence.

**When to use this skill:**
- After source evaluation is complete
- Before finalizing research deliverables
- When validating load-bearing claims that will drive decisions

## Core Principle: The Claim Budget

Every research deliverable has a **claim budget** (default: ≤10 load-bearing claims). This forces prioritization of the most important assertions and ensures each claim receives proper validation.

**Load-Bearing Claim:** A statement that, if wrong, would invalidate the recommendation or materially change the decision.

**Examples:**
- ✅ Load-bearing: "The TAM for AI coding agents is $5B" (drives go/no-go decision)
- ❌ Not load-bearing: "GitHub Copilot was released in 2021" (historical context, not decision-critical)

## Claim Validation Requirements

### High-Stakes Research (Investment, Strategy, Compliance)
- **Minimum:** 2 independent Tier-1 sources
- **Acceptable fallback:** 1 Tier-1 + 1 Tier-2 (if Tier-1 coverage limited)
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

## Date Checking Logic

The `scripts/date_checker.py` script validates temporal alignment:

```python
def check_date_alignment(claim, sources):
    """
    Returns: "ok", "stale", "mismatch", "unknown"
    """
    claim_timeframe = extract_timeframe(claim.text)  # e.g., "2025", "current", "Q1 2024"

    for source in sources:
        pub_date = source.publication_date
        event_date = source.event_date or pub_date

        # Check 1: Stale source
        if claim_timeframe == "current" or "2025" in claim_timeframe:
            if days_between(event_date, today()) > 180:
                return "stale"

        # Check 2: Timeframe mismatch
        if claim_timeframe and claim_timeframe not in ["current", "recent"]:
            claim_year = extract_year(claim_timeframe)
            source_year = extract_year(event_date)
            if abs(claim_year - source_year) > 1:
                return "mismatch"

    return "ok"
```

### Date Check Examples

**OK:**
- Claim: "The 2024 AI market was $150B"
- Source: "Published Jan 2025, data from 2024" → `date_check: "ok"`

**Stale:**
- Claim: "The current AI market is $150B"
- Source: "Published 2020" → `date_check: "stale"`

**Mismatch:**
- Claim: "The 2025 AI market will be $150B"
- Source: "Published 2022, 2020 data" → `date_check: "mismatch"`

## Claims JSON Schema

```json
{
  "claim_budget": 10,
  "claims": [
    {
      "id": "c1",
      "text": "The total addressable market for AI coding agents is $5.2B in 2025",
      "type": "market_size",
      "stakes": "high",
      "support": [
        {
          "source_id": "src_001",
          "url": "https://gartner.com/...",
          "tier": 1,
          "excerpt": "We forecast the AI developer tools market at $5.2B for 2025",
          "relevance": "direct"
        },
        {
          "source_id": "src_005",
          "url": "https://idc.com/...",
          "tier": 1,
          "excerpt": "IDC estimates AI coding assistance market size of $4.8-5.5B in 2025",
          "relevance": "direct"
        }
      ],
      "independent": true,
      "independence_notes": "Gartner and IDC use different methodologies and data sources",
      "tier1_count": 2,
      "tier2_count": 0,
      "date_check": "ok",
      "date_check_notes": "Both sources published Q2 2025 with 2025 projections",
      "confidence": "high",
      "validation_status": "approved",
      "concerns": []
    },
    {
      "id": "c2",
      "text": "Cursor has 500K active users",
      "type": "competitive_metric",
      "stakes": "medium",
      "support": [
        {
          "source_id": "src_010",
          "url": "https://techcrunch.com/...",
          "tier": 2,
          "excerpt": "Cursor announced 500K active users in May 2025",
          "relevance": "direct"
        }
      ],
      "independent": true,
      "tier1_count": 0,
      "tier2_count": 1,
      "date_check": "ok",
      "confidence": "medium",
      "validation_status": "warning",
      "concerns": ["Only 1 source; ideally need 1 more Tier-2 for corroboration"]
    },
    {
      "id": "c3",
      "text": "Solo developers want AI tools that are fast and don't require configuration",
      "type": "customer_need",
      "stakes": "medium",
      "support": [
        {
          "source_id": "src_015",
          "url": "https://reddit.com/r/programming/...",
          "tier": 3,
          "excerpt": "45 upvoted comments expressing frustration with slow, config-heavy AI tools",
          "relevance": "direct"
        },
        {
          "source_id": "src_016",
          "url": "https://news.ycombinator.com/...",
          "tier": 3,
          "excerpt": "HN thread with 120+ comments: top pain points are latency and setup complexity",
          "relevance": "direct"
        }
      ],
      "independent": true,
      "tier1_count": 0,
      "tier2_count": 0,
      "tier3_count": 2,
      "date_check": "ok",
      "confidence": "medium",
      "validation_status": "supplemental",
      "concerns": ["Tier-3 sources only; acceptable for qualitative customer insights"]
    }
  ],
  "summary": {
    "total_claims": 3,
    "approved": 1,
    "warning": 1,
    "supplemental": 1,
    "rejected": 0,
    "avg_tier1_sources_per_claim": 0.67,
    "claims_meeting_tier1_requirement": 1,
    "quality_score": 0.67
  },
  "overall_assessment": "Moderate quality. 1/3 claims have ≥2 Tier-1 sources. Consider strengthening c2 with additional source."
}
```

## Soft Gate Behavior

When a claim lacks sufficient Tier-1 sources:

1. **Flag the claim** with `validation_status: "warning"` or `"supplemental"`
2. **Add to concerns array**: Clear explanation of the gap
3. **Surface to user**: "3 claims lack Tier-1 corroboration. Proceed or request more research?"
4. **Allow override**: User can acknowledge and proceed if acceptable for the decision stakes

**DO NOT block delivery** - this is a soft gate. The goal is informed choice, not rigid enforcement.

## Claim Type Taxonomy

| Type | Description | Typical Stakes | Tier-1 Requirement |
|------|-------------|----------------|-------------------|
| `market_size` | TAM, SAM, SOM figures | High | Yes |
| `financial_metric` | Revenue, pricing, costs | High | Yes |
| `competitive_metric` | User counts, market share | Medium | Preferred |
| `customer_need` | Pain points, JTBD | Medium | No (Tier-3 acceptable) |
| `trend` | Growth rates, adoption | Medium-High | Yes |
| `technical_spec` | Performance, capabilities | Medium | Yes (official docs) |
| `qualitative_insight` | Opinions, sentiment | Low-Medium | No |
| `historical_fact` | Timeline, events | Low | Tier-2 acceptable |

## Validation Checklist

Before marking claims as validated:

- [ ] All claims within budget (≤10 load-bearing)
- [ ] Each claim has `type` and `stakes` assigned
- [ ] High-stakes claims have ≥2 Tier-1 sources (or flagged)
- [ ] All sources are independent (no circular citations)
- [ ] Date alignment checked (`date_check` field populated)
- [ ] Concerns documented for any gaps
- [ ] Overall quality assessment provided

## Output

Creates `research/claims.json` following the schema above.

If soft gate warnings exist, also output a summary:

```
⚠️ Claim Validation Warnings:

- c2 (Cursor user count): Only 1 Tier-2 source; recommend adding 1 more for corroboration
- c5 (Pricing model): Source is 12 months old; may not reflect current pricing

Quality Score: 7/10 claims meet Tier-1 requirement (70%)

Proceed with delivery? [Y/n]
```

## Integration with Scripts

The `scripts/date_checker.py` script is automatically invoked for each claim:

```bash
python scripts/date_checker.py --claims research/claims.json --sources research/source_review.json
```

Output updates `claims.json` with `date_check` and `date_check_notes` fields.

## References

See `resources/claim-types.md` for detailed taxonomy
See `scripts/date_checker.py` for date validation logic
