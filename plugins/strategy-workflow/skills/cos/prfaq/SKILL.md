---
name: Amazon PR-FAQ Generator
description: Generates Amazon-style PR-FAQ with press release, external FAQ, internal FAQ, and premortem. Use for new product/feature proposals.
version: 1.0.0
dependencies: none
---

# Amazon PR-FAQ Generator

## Overview

This skill embodies Amazon's "Working Backwards" methodology by generating a comprehensive PR-FAQ (Press Release + Frequently Asked Questions) document. It forces clarity on customer value before committing engineering resources.

**When to use this skill:**
- When proposing a new product or major feature
- Before significant engineering investment (>3 months, >$50K)
- When you need to align stakeholders around a vision

## The Working Backwards Philosophy

**Core Principle:** Start with the customer experience and work backwards to the technology.

Traditional product development: "We have this technology, what can we build?"
Working Backwards: "The customer needs this experience, what must we build?"

The PR-FAQ is the **forcing function** that makes this real. Writing the press release **first** (before coding) compels you to:
1. Articulate customer pain in their language
2. Describe the solution's benefit (not features)
3. Differentiate from existing alternatives
4. Address the hard questions upfront

## PR-FAQ Structure

### Part 1: Press Release (1 page)

The press release is written **as if** the product has launched. It's a future artifact from launch day.

**Components:**

**1. Heading**
- Product name
- Customer benefit (not feature list)

**Example:**
> **Acme Corp Launches AI Support Agent That Resolves 80% of Tickets Instantly**

**2. Sub-Heading** (1 sentence)
- Target customer + primary benefit

**Example:**
> *Solo founders and small teams get enterprise-grade support automation for $99/month*

**3. Summary Paragraph** (2-4 sentences)
- Dateline (city, date)
- Product announcement
- Core benefit
- Availability

**Example:**
> **PR Newswire, San Francisco, CA, November 15, 2025** – Acme Corp today announced its AI Support Agent, an intelligent automation tool that instantly resolves 80% of customer support tickets for small businesses. Unlike traditional chatbots that frustrate customers, the AI Support Agent understands context, learns from your documentation, and escalates complex issues to humans. Available today for $99/month at acmecorp.com.

**4. Problem Paragraph** (3-4 sentences)
- Customer pain point
- Current alternatives and why they fail
- Impact of the problem

**Example:**
> Small teams with fewer than 10 employees receive hundreds of support tickets per month, but can't afford to hire dedicated support staff. Current solutions either require expensive human agents ($3,000+/month) or deploy generic chatbots that deliver robotic responses and frustrate customers. As a result, founders spend 20+ hours per week answering repetitive questions instead of building their product.

**5. Solution Paragraph** (3-4 sentences)
- How the product solves the problem
- Key differentiator vs alternatives
- Customer outcome

**Example:**
> The AI Support Agent is trained on your existing documentation, help articles, and past support tickets to deliver personalized, accurate responses in your brand's voice. Unlike generic chatbots, it understands customer intent, handles multi-step conversations, and knows when to escalate to a human. Founders report getting their evenings back while maintaining 4.5+ star support ratings.

**6. Company Spokesperson Quote** (2-3 sentences)
- Strategic "why" from founder/CEO
- Vision for impact

**Example:**
> "We built this product because we lived this pain as founders," said Jane Smith, CEO of Acme Corp. "Support is critical to customer success, but it shouldn't consume your life. Our AI agent handles the repetitive 80% so founders can focus on the interesting 20% that requires human judgment."

**7. Customer Quote** (2-3 sentences)
- Hypothetical but believable
- Emotional impact + specific outcome

**Example:**
> "I was spending 3 hours every evening answering the same questions about password resets and billing," said Sarah Chen, founder of TechStartup. "The AI agent now handles all of that. My response time went from 6 hours to 30 seconds, and I got my evenings back."

**8. Call to Action** (1-2 sentences)
- How to get started

**Example:**
> Get started with the AI Support Agent today at acmecorp.com. The first 100 tickets are free.

### Part 2: External FAQ

Customer-facing questions about the product:

**Common Questions:**
1. **What exactly does it do?**
   - Clear, jargon-free explanation

2. **How much does it cost?**
   - Pricing + rationale

3. **When and where can I get it?**
   - Availability (now? beta? waitlist?)

4. **How do I set it up?**
   - Installation/onboarding process

5. **What about my data privacy?**
   - Security and compliance

6. **What if it gives the wrong answer?**
   - Accuracy guarantees, escalation process

7. **Who do I contact for support?**
   - Support channels

**Example:**

**Q: How does the AI Support Agent learn about my business?**
A: You connect it to your help docs, Notion pages, or past support emails. The AI reads and understands your content in about 5 minutes. You can also manually teach it new information through a simple interface.

**Q: What happens if it doesn't know the answer?**
A: The agent will say "I'm not sure about this—let me connect you with the team" and create a ticket for human review. You can also set custom rules for when to escalate (e.g., always escalate refund requests).

**Q: How much does it cost?**
A: $99/month for up to 1,000 tickets. After that, it's $0.10 per additional ticket. We believe support automation should be accessible to small teams, not just enterprises.

### Part 3: Internal FAQ

Rigorous internal analysis for stakeholders:

**Categories:**

**A. Strategy & Market**
1. **What is the Total Addressable Market (TAM)?**
   - Market sizing with sources
   - Serviceable market (SAM)

2. **Why is this strategically important?**
   - Alignment with company vision
   - Competitive positioning

3. **How does this differentiate from competitors?**
   - Competitive landscape (top 3-5 competitors)
   - Our unique advantage (moat)

4. **What are the biggest risks?**
   - Market risk, execution risk, competitive risk
   - Mitigation strategies

**B. Business & Financials**
5. **What are the unit economics?**
   - Revenue per customer
   - Cost of goods sold (COGS)
   - Gross profit margin

6. **What is the upfront investment required?**
   - Engineering time
   - Marketing/sales
   - Infrastructure

7. **When do we expect profitability?**
   - Break-even timeline
   - Path to $1M ARR, $10M ARR

8. **What is the go-to-market plan?**
   - Customer acquisition channels
   - Pricing strategy
   - Launch plan

**C. Technical & Feasibility**
9. **What are the hardest engineering problems?**
   - Technical risks
   - Dependencies

10. **What are the key UI/UX challenges?**
    - User experience risks

11. **What external dependencies exist?**
    - Third-party APIs, vendors
    - Risks if they fail

**D. Operational & Legal**
12. **Are there legal/compliance risks?**
    - Regulatory requirements
    - Data privacy (GDPR, CCPA)

13. **How will we measure success?**
    - Key metrics (North Star, KPIs)
    - Success thresholds

14. **What is the impact on other teams?**
    - Support, ops, sales
    - Resource requirements

**Example (abbreviated):**

**Q: What is the TAM for AI-powered customer support for small businesses?**
A: The global SMB customer support software market is $12B (Gartner, 2025). Within that, the AI-powered support segment is projected at $3.2B by 2026 (IDC). Our serviceable addressable market (SAM) is tech-savvy SMBs with 1-50 employees who already use SaaS tools—approximately 500K businesses in North America. At $99/month, that represents a $600M SAM.

**Q: What are our unit economics?**
A:
- Revenue: $99/month/customer
- COGS: $15/month (LLM API costs, hosting)
- Gross Profit: $84/month (85% margin)
- CAC target: $300 (via content marketing, Product Hunt)
- Payback: 3.6 months
- LTV (assuming 24-month retention): $2,016
- LTV:CAC = 6.7:1 (healthy)

**Q: What's the biggest risk and how do we mitigate it?**
A: **Risk:** The AI doesn't achieve 80% resolution rate, leading to customer churn.
**Mitigation:**
1. Beta with 20 customers to validate accuracy before GA
2. Build confidence scoring (agent only answers when >90% confident)
3. Human-in-the-loop for first 30 days with each customer (manual review)
4. Money-back guarantee if resolution rate <70%

### Part 4: Premortem

Imagine it's 12 months post-launch and the product **failed**. Why?

**Purpose:** Identify failure modes upfront to pressure-test assumptions.

**Example:**

**Scenario: The product failed. Here's why...**

1. **Accuracy wasn't good enough.** Customers churned after 2 months because the AI gave wrong answers 30% of the time. We underestimated how domain-specific support knowledge is.

2. **Customers didn't trust AI with their brand.** Small businesses care deeply about customer relationships. They feared the AI would be too robotic and damage their brand voice.

3. **We couldn't compete on price.** Incumbents (Intercom, Zendesk) launched AI features for $50/month. Our $99 price point was too high for budget-conscious SMBs.

4. **Setup was too complex.** Customers expected 5-minute setup but it took 2 hours to configure properly. They churned before seeing value.

5. **We targeted the wrong customer.** SMBs with <10 employees don't have enough ticket volume to justify $99/month. We should have targeted 20-50 employee companies.

**How these insights inform the plan:**
- Must hit 80% accuracy in beta (non-negotiable)
- Build "brand voice training" feature (teach AI to match tone)
- Aggressive pricing ($99 with first 1,000 tickets free)
- 5-minute setup goal (pre-built integrations)
- Target SMBs with 10-50 employees, not <10

### Part 5: Success Metrics (SLOs)

Define how you'll measure success:

```
North Star Metric: 80% ticket resolution rate without human intervention

KPIs:
- Activation: 70% of trials resolve >100 tickets in first 30 days
- Retention: 60% of customers active after 6 months
- NPS: >40 (for AI support category)
- Response Time: <5 seconds (95th percentile)
- Accuracy: <5% customers request human escalation

Lagging Indicators:
- Monthly Recurring Revenue (MRR)
- Customer Acquisition Cost (CAC)
- Lifetime Value (LTV)
```

## Template Files

The skill provides these templates:

1. **`templates/pr-faq-template.md`** - Full template with instructions
2. **`templates/pr-release-only.md`** - Just the press release part
3. **`templates/internal-faq-template.md`** - Question bank for internal FAQ

## Quality Checklist

**Press Release:**
- [ ] Headline is customer-benefit focused (not feature-focused)
- [ ] Problem paragraph resonates emotionally
- [ ] Solution paragraph differentiates from alternatives
- [ ] Customer quote sounds believable and enthusiastic
- [ ] Total length ≤ 1 page

**External FAQ:**
- [ ] Answers in customer language (no jargon)
- [ ] Addresses price, privacy, setup
- [ ] Proactively addresses objections

**Internal FAQ:**
- [ ] TAM sizing with Tier-1 sources
- [ ] Unit economics calculated (revenue, COGS, margin)
- [ ] Top 3 risks identified with mitigations
- [ ] Success metrics defined (North Star + KPIs)

**Premortem:**
- [ ] At least 5 failure scenarios
- [ ] Scenarios are specific (not generic)
- [ ] Insights inform the plan

## Output

Creates: `product/pr-faq.md`

**File structure:**
```markdown
# [Product Name] PR-FAQ

## Press Release

[Full press release text]

---

## External FAQ

### Q: [Customer question]
A: [Answer]

---

## Internal FAQ

### Strategy & Market
[Questions and answers]

### Business & Financials
[Questions and answers]

### Technical & Feasibility
[Questions and answers]

---

## Premortem

[Failure scenarios]

---

## Success Metrics

[North Star + KPIs]
```

## References

See `resources/prfaq-examples.md` for real examples (AWS Techpreneur, Commoncog Case Library)
See Amazon's "Working Backwards" book for methodology deep-dive
See `templates/pr-faq-template.md` for editable template
