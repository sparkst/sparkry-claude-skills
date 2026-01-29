# Research Methodology

Structured approach to research and ideation

## Research Planning Framework

### 1. Parse User Request

Identify:
- **Core Topic**: What are we researching?
- **Purpose**: Why? (decision, comparison, validation, exploration)
- **Constraints**: Time, depth, scope limitations
- **Context**: Project context, stakeholder, use case

**Example**:
> User: "Research OAuth providers for SaaS app"

**Parsed**:
- Topic: OAuth providers
- Purpose: Comparison (choose one for implementation)
- Context: SaaS app (need reliability, pricing)
- Depth: Medium (40 minutes)

---

### 2. Decompose into Sub-Questions

Use **5W1H framework**:
- **What**: What is this? What does it do?
- **Who**: Who are the players? Who are the users?
- **Where**: Where is it used? Where is the market?
- **When**: When did it emerge? What's the timeline?
- **Why**: Why do people use it? Why now?
- **How**: How does it work? How do competitors do it?

**Example Sub-Questions**:
1. What OAuth providers exist? (Google, GitHub, Auth0, etc.)
2. What are the pricing models for each?
3. How easy is integration for each provider?
4. What features do they support? (MFA, SAML, etc.)
5. What is the reliability/uptime track record?

---

### 3. Define Search Strategy

For each sub-question, generate **2-3 targeted queries**:

**Best Practices**:
- Use specific terminology
- Include year for recency ("2026", "latest")
- Use comparison phrases ("vs", "compared to")
- Use negative sentiment for pain points ("problems with", "limitations")
- Use site-specific searches (`site:reddit.com`, `site:stackoverflow.com`)

**Example Queries**:
- "OAuth providers comparison 2026"
- "Auth0 vs Google OAuth pricing"
- "OAuth integration complexity Reddit"
- "SAML support OAuth providers"

---

### 4. Set Research Depth

| Depth | Duration | Sub-Questions | Queries | Claim Budget |
|-------|----------|---------------|---------|--------------|
| Quick | 10-15 min | 2-3 | 3-5 | 5 |
| Medium | 20-40 min | 4-5 | 8-12 | 10 |
| Deep | 60-120 min | 6-8 | 15-25 | 15 |

**Claim Budget**: Maximum number of load-bearing claims in final recommendation.

---

## Information Gathering

### Source Tiers

**Tier 1 (Highest Credibility)**:
- Official documentation
- Peer-reviewed papers
- Industry standards (OWASP, NIST, W3C)
- Government/academic institutions

**Tier 2 (Moderate Credibility)**:
- Reputable tech blogs (Google, Microsoft, Mozilla)
- Stack Overflow (high-vote answers)
- GitHub repos (>1k stars)
- Conference talks

**Tier 3 (Use with Caution)**:
- Reddit discussions
- Twitter threads
- Medium articles
- Personal blogs

**Rule**: High-stakes decisions require ≥2 Tier 1 sources per key claim.

---

### Data Collection

For each query:
1. **Search and scan**: Collect relevant sources
2. **Extract key points**: Highlight specific data (pricing, features, quotes)
3. **Record source**: Save URL and publication date
4. **Assess credibility**: Tier 1, 2, or 3?

**Example**:
```markdown
## Sub-Question 1: OAuth Provider Pricing

**Source 1**: Auth0 Pricing Page (Tier 1)
- URL: https://auth0.com/pricing
- Free tier: 7,500 MAU
- Paid: $23/month for 1,000 MAU + $0.023/MAU beyond

**Source 2**: Google Identity Platform Pricing (Tier 1)
- URL: https://cloud.google.com/identity-platform/pricing
- Free tier: 50,000 MAU
- Paid: $0.0055/MAU beyond 50k

**Source 3**: Reddit Discussion (Tier 3)
- URL: https://reddit.com/r/webdev/...
- User feedback: "Auth0 expensive for scale, Google free tier generous"
```

---

## Synthesis

### Organize Findings

Group findings by sub-question:

```markdown
## Sub-Question 1: OAuth Provider Pricing

**Key Findings**:
- Google has most generous free tier (50k MAU vs Auth0 7.5k)
- Auth0 is 4x more expensive than Google at scale
- GitHub free for public repos, $4/user/month for private

**Insights**:
- For early-stage SaaS, Google free tier sufficient
- For enterprise, Auth0 offers more features but higher cost
```

---

### Identify Patterns

Look for:
- **Trends**: What direction is the market moving?
- **Commonalities**: What do all options share?
- **Outliers**: What's unique about one option?
- **Contradictions**: Where do sources disagree?

---

## Options Analysis

### Options Matrix

Compare options across key criteria:

| Criteria | Google OAuth | GitHub OAuth | Auth0 |
|----------|--------------|--------------|-------|
| **Cost** | $ (free 50k MAU) | $ (free public) | $$$ ($23/mo base) |
| **Ease of Integration** | High | High | Medium |
| **Features** | Basic | Basic | Advanced (MFA, SAML) |
| **Reliability** | 99.9% uptime | 99.5% uptime | 99.95% uptime |
| **Best For** | Consumer apps | Developer tools | Enterprise SaaS |

---

### Trade-Off Analysis

For each option, analyze:

**Option: Auth0**

**Pros**:
- Advanced features (MFA, SAML, custom domains)
- Excellent documentation
- Strong enterprise support

**Cons**:
- Expensive at scale ($23/mo + usage)
- More complex setup
- Vendor lock-in risk

**Best For**: Enterprise SaaS with need for SAML, MFA, and compliance

---

## Recommendation

### Structure

```markdown
## Recommendation

**Recommended Option**: [Option X]

**Rationale**:
- [Reason 1 with supporting data]
- [Reason 2 with supporting data]
- [Reason 3 with supporting data]

**Next Steps**:
1. [Actionable step 1]
2. [Actionable step 2]
3. [Actionable step 3]

**Open Questions**:
- [Question 1 requiring further investigation]
- [Question 2 requiring further investigation]

**Estimated Implementation Effort**: [X SP or Y weeks]
```

---

### Example Recommendation

```markdown
## Recommendation

**Recommended Option**: Google OAuth

**Rationale**:
- Free tier (50k MAU) covers early-stage needs (Source: Google pricing)
- Simple integration (<1 hour setup) (Source: Google docs)
- 99.9% uptime meets reliability requirements (Source: Google SLA)
- Familiar to most users (reduces friction)

**Next Steps**:
1. Create Google Cloud project and OAuth credentials
2. Implement OAuth flow using `@auth/core` library
3. Test with test users
4. Deploy to staging

**Open Questions**:
- Do we need SAML support? (If yes, reconsider Auth0)
- What is projected MAU at 12 months? (May need to re-evaluate costs)

**Estimated Implementation Effort**: 2 SP (1-2 days)
```

---

## Quality Standards

### Before Finalizing Research

- [ ] All sub-questions answered
- [ ] ≥2 sources per key claim
- [ ] Sources are credible (Tier 1 or 2 for high-stakes)
- [ ] Contradictions acknowledged
- [ ] Options matrix covers relevant criteria
- [ ] Trade-offs explained
- [ ] Recommendation is clear and actionable
- [ ] Next steps are specific
- [ ] Open questions documented

---

## Common Research Patterns

### Pattern: Technology Evaluation

**Sub-Questions**:
1. What is the technology?
2. What are key use cases?
3. What are limitations?
4. Who are vendors/projects?
5. What are adoption trends?

**Sources**: Official docs, GitHub, Stack Overflow

---

### Pattern: Competitive Analysis

**Sub-Questions**:
1. Who are direct competitors?
2. What are their positioning strategies?
3. What are pricing models?
4. What do users complain about?
5. What are the gaps?

**Sources**: Company sites, reviews, Reddit, Twitter

---

### Pattern: Market Research

**Sub-Questions**:
1. What is TAM/SAM/SOM?
2. Who are top players?
3. What are growth trends?
4. What are market segments?
5. What regulatory factors exist?

**Sources**: Analyst reports (Gartner, Forrester), news articles

---

### Pattern: Best Practices

**Sub-Questions**:
1. What do industry leaders recommend?
2. What are current standards?
3. What are common pitfalls?
4. What are emerging trends?

**Sources**: OWASP, NIST, Mozilla, Google

---

## Anti-Patterns to Avoid

❌ **Too Broad**: "Research AI"
✅ **Focused**: "Research AI coding assistants for solo founders"

❌ **No Sources**: "Most developers prefer X"
✅ **Sourced**: "75% of developers prefer X (Stack Overflow Survey 2025)"

❌ **Just Listing Facts**: Bullet points without synthesis
✅ **Synthesized**: Insights, patterns, and implications

❌ **No Recommendation**: Leave decision to user
✅ **Actionable**: Clear recommendation with rationale

---

## References

- Research Planning Guide: [Internal]
- Source Tier Definitions: [Internal]
- Options Matrix Template: [Internal]
