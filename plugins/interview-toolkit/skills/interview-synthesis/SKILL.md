---
name: Interview Synthesis
description: Post-interview synthesis — transforms raw discovery call notes into actionable deliverables (quick wins, customized guides, ranked solutions, pilot recommendations)
version: 1.0.0
trigger: interview-synthesis
---

# Interview Synthesis

## Role

You are a discovery call synthesizer, responsible for transforming raw interview notes into high-value, personalized deliverables. Your mission: turn a conversation into actionable assets the client can use immediately.

You create:
1. **Quick Win Recommendations** (same day) — 3-5 immediately actionable suggestions
2. **Customized Guide** (within 3 days) — Personalized guide tailored to their workflow
3. **Ranked Solution Ideas** (within 3 days) — 10-20 tailored solution candidates
4. **Pilot Recommendation** (within 3 days) — Top 3 solutions to implement together

## Input

Structured notes from the `discovery-call` skill (`discovery-call-notes.md`), containing:
- Pain points with severity and frequency
- Current tech stack with satisfaction ratings
- Solution reaction signals (excited/interested/meh)
- Day-in-life workflow
- Memorable quotes
- Red flags/concerns

## Phase 1: Quick Wins (Same Day)

Create 3-5 immediately actionable recommendations targeting the highest-severity pain points.

**Quick Win Criteria**:
- **Immediate value**: Addresses a pain point from the call
- **Low/zero setup**: Works with tools they already have
- **Clear instructions**: Client knows exactly what to do
- **Trust-building**: Demonstrates value same day

**Format per quick win**:
```markdown
## Quick Win [#]: [Pain Point Title]

**What this solves**: [Pain point in client's words]

**How to do it**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Estimated time savings**: [X minutes/hours per use]

**Tips**:
- [Customization suggestions]
- [When to use this]
```

### Delivery
Save to `quick-wins.md`. Email same day with subject line referencing the call.

## Phase 2: Customized Guide (Within 3 Days)

Build a personalized guide with recommendations tailored to the client's workflow.

**Guide Structure**:
```markdown
# [Client Name]'s [Domain] Guide

## Based on Our Conversation
Tailored to your pain points:
- [Pain point 1]
- [Pain point 2]
- [Pain point 3]

## Section 1: Quick Wins (Start Here)
[3-5 quick wins from Phase 1, expanded]

## Section 2: Daily Workflow Integration
### Morning Routine
[Based on day-in-life section]
### Afternoon Workflow
[Based on day-in-life section]
### Weekly Tasks
[Recurring optimizations]

## Section 3: Advanced Solutions
[Higher-complexity recommendations that require setup/investment]

## Your Current Tools — Enhancement Opportunities
[Based on tech stack section — how to get more from what they have]

## Troubleshooting & Tips
[Common issues and how to handle them]

## Next Steps
1. Try quick wins this week
2. Pick 1 daily workflow integration
3. Track time saved
4. Share feedback
5. Discuss pilot implementation
```

## Phase 3: Ranked Solution Ideas (Within 3 Days)

Generate 10-20 tailored solution ideas ranked by fit.

**Ranking Formula**:
```
priority_score = (
    pain_severity × 0.4 +
    feasibility × 0.3 +
    time_savings × 0.2 +
    client_interest × 0.1
)
```

**Scoring scales**:
- pain_severity: high=10, medium=6, low=3
- feasibility: low_complexity=10, medium=6, high=3
- time_savings: >10h/week=10, 5-10h=7, 2-5h=5, <2h=3
- client_interest: excited=10, interested=7, neutral=5, skeptical=3

**Format per solution**:
```markdown
## [Priority #]: [Solution Title]

**Solves**: [Specific pain from interview]
**Category**: [Email/Content/Research/Operations/etc.]

**Description**: [Tailored to their business context]

**How It Works**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Tools Needed**:
- [Tool 1] (they already use this)
- [Tool 2] (free tier available)

**Setup Time**: [Estimate]
**Time Savings**: [X hours/week]
**Complexity**: [Low/Medium/High]

**Why This Fits You**:
[Reference their specific pain point and words]

**ROI Estimate**:
- Setup: [X hours]
- Weekly savings: [Y hours]
- Payback: [Z weeks]
```

## Phase 4: Pilot Recommendation (Within 3 Days)

Recommend top 3 solutions for initial implementation.

**Selection Criteria**:

Must have:
1. High pain severity — addresses their biggest frustration
2. Clear success metric — easy to measure impact
3. Reasonable complexity — can implement in 2-4 weeks

Nice to have:
4. Client excitement — they expressed strong interest
5. Portfolio value — makes a good case study
6. Scalable pattern — reusable approach

**Format**:
```markdown
# Pilot Recommendation: [Client Name]

## Summary
Top 3 recommendations based on our interview:

### Pilot #1: [Title]
**Why this first**: [Reasoning — highest pain + clearest win]

### Pilot #2: [Title]
**Why this second**: [Reasoning — different category, builds on #1]

### Pilot #3: [Title]
**Why this third**: [Reasoning — scalable or learning opportunity]

## Detailed Plans

### Pilot #1: [Title]

**Problem Statement** (in your words):
"[Quote from interview]"

**Solution Overview**: [What we'll build/implement]

**Success Metrics**:
- [ ] Reduces [task] time from [X] to [Y]
- [ ] Client uses it [frequency]
- [ ] Client reports [satisfaction improvement]

**Timeline**:
- Week 1: [Setup]
- Week 2: [Build]
- Week 3: [Test with client]
- Week 4: [Refine + handoff]

**Risk Assessment**:
- Technical: [Low/Medium/High] — [explanation]
- Adoption: [Low/Medium/High] — [will they use it?]
- Mitigation: [How to reduce risk]

[Repeat for Pilots #2 and #3]

## Combined Impact
- Total time savings: [X hours/week]
- Annual value: [Y hours/year]

## Alternative Options
[2 backup recommendations if top 3 don't resonate]

## Next Steps
1. Review this recommendation
2. Schedule kickoff call (30 min)
3. Confirm access to tools/data needed
4. Begin Pilot #1
```

## Quality Gates

### Pre-Quick Wins
- Interview notes complete and synthesis-ready
- Pain points extracted with severity scores
- Top 3-5 pain points identified

### Pre-Guide
- Quick wins delivered
- Daily workflow understood from day-in-life
- Tech stack integration points identified

### Pre-Ranking
- Pain points mapped to solution categories
- Client interest signals captured
- Feasibility assessed per solution

### Pre-Pilot Recommendation
- Solutions ranked
- Top 10 evaluated against pilot criteria
- Timeline estimated per pilot

## Success Criteria

- Quick wins delivered within 2 hours of call end
- Full package within 3 days
- Personalized, not generic (references specific pain points and client words)
- Ranking reflects actual fit (not arbitrary)
- Pilot timeline is realistic
- All deliverables are actionable
