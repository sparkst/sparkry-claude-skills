---
name: Tenets Framework
description: Defines non-negotiable principles with rationale, examples, and pass/fail criteria. Use when establishing team operating model or decision-making guidelines.
version: 1.0.0
dependencies: none
---

# Tenets Framework

## Overview

Tenets are **non-negotiable principles** that guide decision-making and behavior. They are not aspirational values—they are specific, actionable statements that help teams resolve ambiguity and trade-offs.

**When to use this skill:**
- When establishing a new team or company culture
- When teams repeatedly face similar conflicts (tenets prevent re-litigation)
- When scaling requires consistent decision-making without central approval
- When you need to align distributed teams around core principles

## Amazon's Tenet Philosophy

**Key Insight:** Tenets are **not values**. Values are aspirational ("We value customer obsession"). Tenets are **decision rules** ("When in doubt, bias for the customer experience, even if it means short-term metrics suffer").

**Difference from Values:**

| Values | Tenets |
|--------|--------|
| Aspirational ("We care about quality") | Specific ("Every release must pass automated tests") |
| Hard to measure | Falsifiable (you can tell if violated) |
| Everyone agrees | May require trade-offs |
| Inspire | Guide decisions |

**Example (Amazon):**
- **Value:** "Customer obsession"
- **Tenet:** "We prioritize long-term customer trust over short-term profit. If a feature delights customers but hurts quarterly revenue, we ship it."

## Tenet Structure

Each tenet has:

1. **Pithy Statement** (1 sentence)
2. **Rationale** (Why this matters)
3. **Trade-Off Acknowledged** (What we sacrifice)
4. **Pass Examples** (Behavior that upholds tenet)
5. **Fail Examples** (Behavior that violates tenet)

### Template

```markdown
## Tenet: [Pithy Statement]

**Rationale:**
[Why this principle is non-negotiable. What problem does it solve? What happens if we violate it?]

**Trade-Off:**
[What are we willing to sacrifice to uphold this? Be honest about costs.]

**Pass Examples:**
1. [Specific scenario where team followed tenet]
2. [Another scenario]

**Fail Examples:**
1. [Specific scenario where tenet was violated]
2. [Consequence of violation]

**Measurement:**
[How do we know if we're upholding this? What metrics or signals indicate compliance?]
```

## Example Tenets

### Tenet 1: Proposal-First, Always

**Pithy Statement:**
> We write the proposal before building. Every feature starts with a 1-page summary and appendices for depth.

**Rationale:**
Writing forces clarity. If you can't explain why a feature matters in 1 page, you don't understand it well enough to build it. Proposals prevent wasted engineering effort on poorly-defined features.

**Trade-Off:**
We accept slower time-to-code in exchange for faster time-to-right-solution. Some engineers may resist writing before coding.

**Pass Examples:**
1. PM drafts PR-FAQ for AI support agent before any code is written. Engineering team reads it, identifies unclear assumptions, PM refines. Coding starts only after consensus.
2. Founder writes 1-page proposal for new pricing tier. Finance team spots unit economics problem before GTM launch.

**Fail Examples:**
1. Engineer builds prototype "to see if it works" without written spec. Prototype gains momentum, ships without PM review. Customer confusion results because UX was never designed.
2. Sales team requests feature. Engineering builds immediately to close deal. Feature doesn't generalize, becomes tech debt.

**Measurement:**
- 100% of features have written proposal before first commit
- Track "rework rate" (features rebuilt due to unclear spec)

---

### Tenet 2: Simple Before Clever

**Pithy Statement:**
> When faced with a choice between a simple solution and a clever one, we choose simple—even if clever is more "interesting."

**Rationale:**
Clever code is harder to maintain, harder to onboard new engineers, and fails in unpredictable ways. Simplicity compounds over time; cleverness creates debt.

**Trade-Off:**
We may ship features slower if clever shortcuts are available. Engineers may find work less intellectually stimulating.

**Pass Examples:**
1. Team debates: microservices vs monolith. Monolith is simpler for current scale. Team chooses monolith despite engineer preference for microservices.
2. Engineer proposes regex parser for markdown. Another engineer suggests simple string splits. Team chooses string splits.

**Fail Examples:**
1. Engineer implements custom caching layer instead of using Redis. Custom layer is "more efficient" but has subtle bugs. Team spends 3 weeks debugging.
2. Team uses functional programming patterns (monads, functors) in TypeScript. New hire takes 2 weeks to onboard vs 3 days for imperative code.

**Measurement:**
- Onboarding time for new engineers (target: <5 days to first commit)
- Code review feedback: "Can this be simpler?" count
- Bug density in "clever" vs "simple" code sections

---

### Tenet 3: Truth-Seeking Over Validation

**Pithy Statement:**
> We seek evidence that **challenges** our beliefs, not confirms them. The goal is to be right, not to win debates.

**Rationale:**
Confirmation bias is the default mode. If unchecked, teams build products for the wrong customers, ignore market shifts, and defend bad decisions. Truth-seeking requires active effort.

**Trade-Off:**
Debates take longer. Egos get bruised. Some team members may feel their ideas are "attacked" (even when feedback is idea-focused).

**Pass Examples:**
1. PM believes indie devs are the right target. Strategic advisor finds data suggesting enterprise is better TAM. PM abandons indie positioning despite personal attachment.
2. Founder believes feature X will drive growth. UX designer runs user tests showing X confuses users. Founder kills feature.

**Fail Examples:**
1. Team cherry-picks sources that support enterprise positioning, ignores contrary evidence. Product fails to gain traction.
2. Founder dismisses engineer's concerns about scalability because "we'll fix it later." Scalability issue causes outage.

**Measurement:**
- Dissent rate in position memos (target: ≥30% of specialists disagree on first pass)
- "Pivot rate" (% of proposals that change after research)
- Post-mortem on failed decisions: "Did we ignore warning signals?"

---

### Tenet 4: Best-of-Best Sources Only

**Pithy Statement:**
> We only cite Tier-1 and Tier-2 sources for high-stakes claims. If you can't find authoritative evidence, you haven't researched hard enough—or the claim is speculative.

**Rationale:**
The internet is 90% noise. SEO spam, AI-generated content, and marketing disguised as research pollute search results. Quality gates prevent bad data from driving bad decisions.

**Trade-Off:**
Research takes longer. Some claims may remain unsupported (which is valuable information). Engineers may find process "bureaucratic."

**Pass Examples:**
1. PM claims "TAM is $5.2B." Cites Gartner report (Tier-1) and IDC estimate (Tier-1). Both sources agree within 10%.
2. Legal expert claims "GDPR requires X." Cites official EU regulation text (Tier-1).

**Fail Examples:**
1. Strategic advisor claims "market is growing 40% annually." Cites Medium article (Tier-4). Source is unverified. Claim removed.
2. Finance consultant cites competitor revenue from TechCrunch rumor (Tier-3). Competitor later reports different numbers. Forecast was wrong.

**Measurement:**
- % of claims backed by Tier-1 sources (target: ≥80%)
- Source tier distribution in final deliverables
- Claim retraction rate (how often we correct claims due to bad sources)

---

### Tenet 5: Ship Fast, Learn Faster

**Pithy Statement:**
> Speed of learning beats perfection. We ship MVPs, collect feedback, and iterate—rather than spend months building the "perfect" v1.

**Rationale:**
Market feedback is the most valuable signal. Delaying launch to add features often results in building the wrong thing. Fast iteration compounds learning.

**Trade-Off:**
Early customers may encounter bugs or incomplete features. Brand perception risk if MVP is too rough.

**Pass Examples:**
1. Team launches AI agent with 70% accuracy, clearly labeled "beta." Collects user feedback, improves to 85% in 6 weeks.
2. Founder ships landing page with waitlist before building product. 500 signups validate demand.

**Fail Examples:**
1. Team spends 9 months building "perfect" product. Launch reveals customers wanted different features. 9 months wasted.
2. Engineer refuses to ship until code coverage is 100%. Delays launch by 2 months. Competitor ships first.

**Measurement:**
- Time from idea to first customer feedback (target: <30 days for new features)
- Iteration velocity (releases per month)
- Customer feedback incorporation rate (% of feedback acted on within 2 weeks)

---

## Creating Your Own Tenets

### Step 1: Identify Recurring Conflicts

Look for patterns:
- Debates that repeat (e.g., "Should we ship now or wait?")
- Trade-offs that cause paralysis (e.g., speed vs quality)
- Cultural violations that frustrate you (e.g., someone ships without tests)

### Step 2: Draft Pithy Statement

Make it:
- **Specific** ("We test before shipping" not "We value quality")
- **Actionable** (Can someone violate it? If no, it's not a tenet)
- **Opinionated** (Tenets pick a side; they're not universally agreeable)

### Step 3: Acknowledge the Trade-Off

Honest tenets admit costs:
- "We prioritize X **even though** it means sacrificing Y."
- If there's no trade-off, it's not a real tenet—it's a platitude.

### Step 4: Provide Pass/Fail Examples

**Concrete examples** make tenets actionable:
- Pass: "When [scenario], team did [action] because of tenet."
- Fail: "When [scenario], team violated tenet by [action], resulting in [consequence]."

### Step 5: Define Measurement

How do you know if the tenet is upheld?
- Quantitative: % of features with tests, time to MVP, source tier distribution
- Qualitative: Code review comments, retro themes, team survey

## Anti-Patterns

❌ **Too Many Tenets:** >7 tenets = no one remembers them
✅ **3-5 Core Tenets:** Focused, memorable, actionable

❌ **Vague Statements:** "We value collaboration"
✅ **Specific Rules:** "Decisions are made via written proposals, not hallway conversations"

❌ **No Trade-Offs Acknowledged:** "We ship fast AND perfect"
✅ **Honest Trade-Offs:** "We ship fast, accepting that early versions will be imperfect"

❌ **No Enforcement:** Tenets on a wall, ignored in practice
✅ **Measured & Reviewed:** Tenets are cited in code reviews, retros, performance reviews

## Output

Creates: `tenets.md`

**File structure:**
```markdown
# [Team/Company Name] Tenets

## Tenet 1: [Pithy Statement]

**Rationale:** ...
**Trade-Off:** ...
**Pass Examples:** ...
**Fail Examples:** ...
**Measurement:** ...

---

## Tenet 2: [Pithy Statement]

...

---

## Review & Evolution

Tenets are reviewed [quarterly/annually]. We ask:
1. Are these still relevant?
2. Are we upholding them? (Check metrics)
3. Do we need new tenets? (Identify new recurring conflicts)
```

## Quality Checklist

Before finalizing tenets:

- [ ] Each tenet is specific and actionable (not aspirational)
- [ ] Trade-offs are honestly acknowledged
- [ ] Pass/fail examples are concrete (not hypothetical)
- [ ] Measurement criteria are defined
- [ ] Team consensus: "We will uphold this even when inconvenient"
- [ ] Total tenets ≤7 (preferably 3-5)

## References

See Amazon's Leadership Principles for similar concept
See Stripe's Operating Principles for tech company examples
See Ray Dalio's *Principles* for systematizing decision-making
