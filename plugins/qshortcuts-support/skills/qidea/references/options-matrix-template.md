# Options Matrix Template

Template for comparing multiple options in research analysis

## Basic Options Matrix

```markdown
| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| Cost | $ | $$ | $$$ |
| Ease of Use | High | Medium | Low |
| Performance | Excellent | Good | Excellent |
| Community Support | Large | Small | Medium |
| Learning Curve | Low | Medium | High |
| Best For | [Use case] | [Use case] | [Use case] |
```

---

## Weighted Options Matrix

When certain criteria are more important than others:

```markdown
| Criteria (Weight) | Option A | Option B | Option C |
|-------------------|----------|----------|----------|
| Cost (3x) | 8/10 | 6/10 | 4/10 |
| Ease of Use (2x) | 9/10 | 7/10 | 5/10 |
| Performance (1x) | 7/10 | 8/10 | 9/10 |
| **Weighted Score** | **8.1** | **6.9** | **5.5** |
```

**Calculation Example**:
- Option A: (8×3 + 9×2 + 7×1) / (3+2+1) = 49/6 = 8.1

---

## Technology Comparison Matrix

```markdown
| Criteria | React | Vue | Svelte |
|----------|-------|-----|--------|
| **Learning Curve** | Medium | Low | Medium |
| **Performance** | Good | Good | Excellent |
| **Ecosystem** | Huge | Large | Growing |
| **TypeScript Support** | Excellent | Good | Good |
| **Bundle Size** | 40KB | 33KB | 2KB |
| **Job Market** | Abundant | Moderate | Limited |
| **Corporate Backing** | Meta | Independent | Vercel |
| **Best For** | Large apps, teams | Solo devs, quick MVPs | Performance-critical |
```

---

## SaaS Tool Comparison Matrix

```markdown
| Criteria | Auth0 | Google OAuth | GitHub OAuth |
|----------|-------|--------------|--------------|
| **Free Tier** | 7,500 MAU | 50,000 MAU | Unlimited (public repos) |
| **Paid Tier** | $23/mo + usage | $0.0055/MAU | $4/user/mo |
| **Ease of Integration** | Medium | High | High |
| **Features** | Advanced (MFA, SAML) | Basic | Basic |
| **Reliability** | 99.95% SLA | 99.9% SLA | 99.5% SLA |
| **Support** | Email, chat | Forum | GitHub Issues |
| **Best For** | Enterprise | Consumer apps | Developer tools |
```

---

## Market Positioning Matrix

```markdown
| Dimension | Option A (Premium) | Option B (Mid-Market) | Option C (Budget) |
|-----------|-------------------|----------------------|-------------------|
| **Target Customer** | Enterprise | SMB | Solo devs |
| **Pricing** | $99/mo | $29/mo | $9/mo |
| **Features** | Full suite | Core features | Basic |
| **Support** | Dedicated | Email | Community |
| **Market Size** | 10k companies | 100k companies | 1M developers |
| **Competition** | Low | High | Very high |
| **Moat** | Enterprise relationships | Balanced offering | Price |
```

---

## Build vs Buy Matrix

```markdown
| Criteria | Build In-House | Buy SaaS | Open Source |
|----------|---------------|----------|-------------|
| **Upfront Cost** | High (dev time) | Low | Medium (setup) |
| **Ongoing Cost** | Medium (maintenance) | High (subscription) | Low |
| **Time to Market** | Slow (weeks) | Fast (hours) | Medium (days) |
| **Customization** | Full control | Limited | Moderate |
| **Maintenance** | You own it | Vendor manages | Community + You |
| **Risk** | Technical debt | Vendor lock-in | Support uncertainty |
| **Best For** | Unique needs | Standard needs | Budget-conscious |
```

---

## Decision Matrix with Scoring

```markdown
| Criteria | Weight | Option A | Option B | Option C |
|----------|--------|----------|----------|----------|
| Cost | 30% | 7/10 (2.1) | 9/10 (2.7) | 5/10 (1.5) |
| Ease of Use | 25% | 8/10 (2.0) | 6/10 (1.5) | 9/10 (2.25) |
| Performance | 20% | 9/10 (1.8) | 7/10 (1.4) | 8/10 (1.6) |
| Community | 15% | 8/10 (1.2) | 9/10 (1.35) | 6/10 (0.9) |
| Scalability | 10% | 9/10 (0.9) | 8/10 (0.8) | 7/10 (0.7) |
| **Total Score** | 100% | **8.0** | **7.75** | **6.95** |
| **Rank** | | **1** | **2** | **3** |
```

**Winner**: Option A (highest total score)

---

## Qualitative vs Quantitative Matrix

```markdown
| Criteria | Option A | Option B | Option C |
|----------|----------|----------|----------|
| **Quantitative** |
| Price | $10/mo | $20/mo | $30/mo |
| Users | 50k MAU | 100k MAU | Unlimited |
| Uptime SLA | 99.9% | 99.95% | 99.99% |
| API Rate Limit | 1k/min | 5k/min | 10k/min |
| **Qualitative** |
| Developer Experience | Good | Excellent | Good |
| Documentation | Fair | Excellent | Good |
| Community Vibe | Active | Very active | Small |
| Vendor Reputation | Established | New but strong | Established |
```

---

## Risk Assessment Matrix

```markdown
| Risk Category | Option A | Option B | Option C |
|---------------|----------|----------|----------|
| **Technical Risk** | Low | Medium | High |
| **Vendor Lock-in** | High | Medium | Low (open source) |
| **Support Risk** | Low (dedicated) | Medium (email) | High (community) |
| **Cost Escalation** | Medium | Low (flat rate) | High (usage-based) |
| **Data Privacy** | High (EU servers) | Medium (US servers) | High (self-hosted) |
| **Compliance** | SOC 2, GDPR | GDPR | None |
```

---

## Trade-Off Matrix

```markdown
| Trade-Off | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| **Speed vs Control** | Control | Balanced | Speed |
| **Cost vs Features** | Features | Balanced | Cost |
| **Ease vs Power** | Ease | Balanced | Power |
| **Vendor vs DIY** | Vendor | Vendor | DIY |
```

---

## Example: OAuth Provider Comparison

```markdown
| Criteria | Auth0 | Google OAuth | GitHub OAuth |
|----------|-------|--------------|--------------|
| **Pricing** |
| Free Tier | 7,500 MAU | 50,000 MAU | Unlimited (public) |
| Paid (per MAU) | $0.023 | $0.0055 | N/A (per seat) |
| Base Cost | $23/mo | $0 | $0 |
| **Features** |
| Social Login | ✅ All major | ✅ Google only | ✅ GitHub only |
| MFA | ✅ | ⚠️ Via Google Auth | ❌ |
| SAML | ✅ | ❌ | ❌ |
| Custom Domains | ✅ | ❌ | ❌ |
| **Developer Experience** |
| Documentation | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Setup Time | 2-4 hours | 30 minutes | 30 minutes |
| SDKs | All major languages | JS, Python, Go | All major |
| **Reliability** |
| Uptime SLA | 99.95% | 99.9% | 99.5% |
| Support | Email, chat | Forum | GitHub Issues |
| **Best For** | Enterprise SaaS | Consumer apps | Developer tools |
```

**Recommendation**: Google OAuth for early-stage consumer apps (generous free tier, fast setup). Auth0 for enterprise SaaS (MFA, SAML, compliance).

---

## Tips for Creating Effective Matrices

### 1. Choose Relevant Criteria

**❌ Don't**: Include irrelevant criteria
```markdown
| Logo Color | Option A | Option B |
```

**✅ Do**: Focus on decision-relevant criteria
```markdown
| Cost | Ease of Use | Performance |
```

---

### 2. Use Consistent Scales

**❌ Don't**: Mix scales
```markdown
| Cost | High | $50/mo | Expensive |
```

**✅ Do**: Use consistent scales
```markdown
| Cost | $10/mo | $50/mo | $100/mo |
```

---

### 3. Include Qualitative and Quantitative

**❌ Don't**: Only numbers
```markdown
| Price | $10 | $20 | $30 |
```

**✅ Do**: Mix data and insights
```markdown
| Price | $10 | $20 | $30 |
| Value | Basic | Balanced | Premium |
```

---

### 4. Add "Best For" Row

**✅ Always include**:
```markdown
| Best For | Solo devs | Teams | Enterprise |
```

---

## References

- Decision Matrix Analysis: https://www.mindtools.com/pages/article/newTED_03.htm
- Trade-Off Analysis: https://en.wikipedia.org/wiki/Trade-off
