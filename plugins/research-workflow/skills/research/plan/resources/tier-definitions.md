# Source Tier Definitions

## Tier-1: Primary & Authoritative Sources

**Criteria:**
- Original research or primary data collection
- Transparent methodology
- Peer-reviewed or industry-recognized authority
- Independent (not citing other sources in chain)

**Examples:**

### Government & Regulatory
- U.S. Census Bureau (census.gov)
- SEC EDGAR filings (sec.gov)
- Federal Reserve economic data (federalreserve.gov)
- Bureau of Labor Statistics (bls.gov)
- European Commission reports (ec.europa.eu)

### Research Firms (Top-Tier)
- Gartner (gartner.com)
- McKinsey & Company (mckinsey.com)
- Boston Consulting Group (bcg.com)
- IDC (idc.com)
- Forrester Research (forrester.com)

### Academic & Peer-Reviewed
- Nature, Science, Cell (journals)
- arXiv.org (preprints, especially CS/AI)
- IEEE Xplore (technical standards)
- NBER Working Papers (economics)
- PubMed (medical/health)

### Technical Standards & Documentation
- W3C specifications (w3.org)
- IETF RFCs (ietf.org)
- ISO standards (iso.org)
- Official vendor documentation (docs.aws.amazon.com, developer.mozilla.org)

### Primary Company Data
- Annual reports (10-K filings via SEC)
- Investor relations pages
- Official product documentation
- Company earnings calls (transcripts)

---

## Tier-2: Reputable Secondary Sources

**Criteria:**
- Established editorial standards
- Named authors with expertise
- Fact-checking processes
- Cites primary sources

**Examples:**

### Business Publications
- Wall Street Journal (wsj.com)
- Bloomberg (bloomberg.com)
- Financial Times (ft.com)
- The Economist (economist.com)
- Harvard Business Review (hbr.org)

### Technology Publications
- Ars Technica (arstechnica.com)
- TechCrunch (techcrunch.com) - for news, not analysis
- The Verge (theverge.com)
- Wired (wired.com)
- MIT Technology Review (technologyreview.com)

### Industry Analysts
- CB Insights (cbinsights.com)
- PitchBook (pitchbook.com)
- Statista (statista.com) - with original data
- eMarketer (emarketer.com)

### Technical Books
- O'Reilly Media
- Manning Publications
- Pragmatic Bookshelf
- No Starch Press

### Reputable News
- Associated Press (ap.org)
- Reuters (reuters.com)
- BBC News (bbc.com)
- NPR (npr.org)

---

## Tier-3: Community & Practitioner Sources

**Criteria:**
- Named authors (not anonymous)
- Community validation (upvotes, engagement)
- Practical experience (not theoretical)
- Useful for sentiment/anecdotes, not primary claims

**Examples:**

### Developer Communities
- Stack Overflow (stackoverflow.com) - accepted answers
- GitHub Discussions (github.com)
- Hacker News (news.ycombinator.com) - highly upvoted
- Dev.to (dev.to) - established authors

### Community Forums
- Reddit (reddit.com) - subreddits with strong moderation
- Indie Hackers (indiehackers.com)
- Product Hunt (producthunt.com)
- Designer News (designernews.co)

### Practitioner Blogs
- Personal blogs with named authors
- Substack newsletters from experts
- Medium articles from verified authors
- Company engineering blogs (e.g., Netflix Tech Blog)

---

## Tier-4: Unverified & Low-Quality

**Criteria:**
- Anonymous or AI-generated
- No editorial standards
- Marketing disguised as content
- SEO-optimized content farms

**Examples:**

### Content Farms
- Generic domains (bestaitools.com, top10developertools.net)
- Listicles with affiliate links
- "Ultimate guide" posts with no original research
- Sites with "Powered by AI" disclaimers

### Marketing Materials
- Vendor white papers (unless citing primary data)
- Case studies without independent verification
- Press releases (use as leads, verify independently)
- Promotional blog posts

### Low-Quality Community
- Quora (quora.com) - often unreliable
- Yahoo Answers (answers.yahoo.com) - defunct but sometimes indexed
- Anonymous forum posts
- Social media posts (Twitter/X threads without sources)

### AI-Generated Content
- No author attribution
- Generic writing style
- Obvious hallucinations
- Contradicts known facts

---

## Special Cases

### Wikipedia
- **Tier:** 2-3 (use as starting point, verify sources)
- **Use Case:** Follow citations to primary sources
- **Don't cite Wikipedia directly for high-stakes claims**

### Company Blogs
- **Tier:** 1-2 if official product documentation
- **Tier:** 3-4 if marketing content
- **Examples:** 
  - Tier-1: AWS Architecture Blog (technical, detailed)
  - Tier-4: Generic "Why you should use our product" posts

### Podcasts & Videos
- **Tier:** 2-3 if expert interview with transcripts
- **Tier:** 4 if opinion-based, no citations
- **Best Practice:** Use as leads, find written sources to cite

### Social Media
- **Tier:** 1 if primary announcement (e.g., CEO announcing funding)
- **Tier:** 3-4 for most other content
- **Verify:** Always cross-reference with independent sources

---

## Decision Tree

```
Is the source a government agency, peer-reviewed journal, or top-tier research firm?
    YES → Tier-1
    NO ↓

Does the source have editorial standards, named authors, and cite primary sources?
    YES → Tier-2
    NO ↓

Is the source a community/practitioner with validation (upvotes, reputation)?
    YES → Tier-3
    NO ↓

Is the source anonymous, AI-generated, or marketing content?
    YES → Tier-4
```

---

## Usage Guidelines

**For High-Stakes Claims (market size, revenue, regulatory):**
- Require ≥2 independent Tier-1 sources
- Tier-2 can supplement but not replace Tier-1

**For Medium-Stakes Claims (features, pricing, sentiment):**
- Require ≥1 Tier-1 or ≥2 Tier-2 sources

**For Low-Stakes Claims (historical context, general trends):**
- Tier-2 or Tier-3 acceptable

**For Anecdotes/Sentiment:**
- Tier-3 (Reddit, HN) is useful for discovering pain points
- Don't use for quantitative claims
