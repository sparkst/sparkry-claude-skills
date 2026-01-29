# Advanced Query Strategies

## Search Operators by Tool

### Tavily Search

**Best For:** Deep research, canonical sources, structured data

**Parameters:**
```python
tavily_search(
    query="...",
    search_depth="basic" | "advanced",  # Use 'advanced' for comprehensive
    max_results=10,
    include_domains=["gartner.com", "idc.com"],  # Whitelist Tier-1
    exclude_domains=["medium.com"],  # Blacklist noise
    include_raw_content=True,  # Get full page content
    include_images=False,
    freshness="pw" | "pm" | "py"  # Past week/month/year
)
```

### Brave Search

**Best For:** Broad discovery, news, diverse perspectives

**Query Operators:**
- `"exact phrase"` - Match exact phrase
- `site:domain.com` - Restrict to domain
- `-term` - Exclude term
- `OR` - Logical OR
- `after:2024-01-01` - Date filtering

**Example:**
```
"AI coding agents" "market size" site:gartner.com OR site:idc.com after:2024-01-01
```

---

## Query Patterns by Research Type

### Market Sizing

**Goal:** Find TAM/SAM data from authoritative sources

**Queries:**
```
1. "market size" "TAM" [industry] [year] site:gartner.com OR site:idc.com
2. "analyst report" [technology] [year] revenue forecast
3. sec filing [company] "revenue" "segment" [product category]
4. [industry] "market forecast" "CAGR" site:forrester.com
```

**Example:**
```
"market size" "TAM" "AI developer tools" 2025 site:gartner.com
```

### Competitive Intelligence

**Goal:** Understand competitors' positioning, features, pricing

**Queries:**
```
1. [competitor] "pricing" OR "plans" -inurl:review -inurl:affiliate
2. [product A] vs [product B] comparison -inurl:affiliate
3. site:reddit.com [tool] "switching from" OR "migrating from"
4. [competitor] "features" site:docs.[vendor].com
5. [competitor] funding site:crunchbase.com OR site:pitchbook.com
```

**Example:**
```
"GitHub Copilot" vs "Cursor" comparison -inurl:review -inurl:affiliate after:2024-06-01
```

### Customer Sentiment

**Goal:** Discover pain points, unmet needs, switching reasons

**Queries:**
```
1. site:reddit.com/r/[community] [tool] "frustration" OR "pain point"
2. site:news.ycombinator.com [topic] "wish" OR "if only"
3. [tool] "alternatives" site:reddit.com OR site:news.ycombinator.com
4. "switching from" [tool] "because" OR "reason"
```

**Example:**
```
site:reddit.com/r/webdev "GitHub Copilot" frustration OR "pain point"
```

### Technical Documentation

**Goal:** Find official specs, APIs, architecture

**Queries:**
```
1. site:github.com [project] "official documentation"
2. site:docs.[vendor].com [feature] specification API
3. "RFC" [protocol] site:ietf.org
4. [technology] architecture "design document" site:github.com
```

**Example:**
```
site:docs.github.com "GitHub Copilot" API specification
```

### Pricing & Business Model

**Goal:** Understand monetization, willingness-to-pay

**Queries:**
```
1. [product] pricing tiers site:[vendor].com/pricing
2. [industry] "willingness to pay" survey
3. [product category] "pricing benchmark" [year]
4. [competitor] "business model" revenue site:sec.gov OR site:crunchbase.com
```

**Example:**
```
"developer tools" "willingness to pay" survey 2025 site:stackoverflow.com
```

---

## Canonical Source Targeting

### By Domain (Market Data)

**Tier-1 Domains:**
```python
market_research = [
    "gartner.com",
    "idc.com",
    "forrester.com",
    "mckinsey.com",
    "bcg.com",
    "census.gov",
    "bls.gov"
]
```

**Query Pattern:**
```
[topic] [year] forecast site:gartner.com OR site:idc.com
```

### By Domain (Cloud/DevOps)

**Tier-1 Domains:**
```python
cloud_devops = [
    "aws.amazon.com/blogs",
    "cloud.google.com/blog",
    "azure.microsoft.com/blog",
    "docs.aws.amazon.com",
    "kubernetes.io/docs"
]
```

**Query Pattern:**
```
[feature] architecture best practices site:aws.amazon.com/blogs
```

### By Domain (AI/ML Research)

**Tier-1 Domains:**
```python
ai_research = [
    "arxiv.org",
    "openai.com/research",
    "anthropic.com/research",
    "deepmind.google/research",
    "ai.meta.com/research"
]
```

**Query Pattern:**
```
[technique] "large language models" site:arxiv.org after:2024-01-01
```

---

## Noise Filtering Strategies

### Auto-Exclude Patterns

**AI Content Farms:**
```
-site:medium.com
-"powered by AI"
-"AI-generated content"
```

**Affiliate/Review Spam:**
```
-inurl:review
-inurl:best
-inurl:top10
-inurl:comparison
-inurl:affiliate
```

**Low-Authority Domains:**
```
-site:quora.com
-site:answers.yahoo.com
-site:*.blogspot.com
```

**Generic Tool Directories:**
```
-site:*aitools.com
-site:*developertools.net
-site:*productivityapps.io
```

### Combined Noise Filter

```
[your query] -inurl:review -inurl:best -site:quora.com -site:medium.com
```

---

## Temporal Strategies

### Recent Data (News, Launches)

**Tavily:**
```python
freshness="pw"  # Past week
freshness="pm"  # Past month
```

**Brave:**
```
after:2024-10-01
```

### Historical Context

**Year-Specific:**
```
[topic] 2023
[topic] 2024
[topic] 2025
```

**Range:**
```
[topic] 2020..2025
```

---

## Multi-Query Strategies

### Progressive Refinement

**Round 1: Broad Discovery**
```
AI coding agents market
```

**Round 2: Narrow to Canonical Sources**
```
"AI coding agents" market size site:gartner.com OR site:idc.com
```

**Round 3: Specific Claims**
```
"AI coding agents" TAM 2025 forecast
```

### Parallel Execution

**Execute simultaneously:**
```python
queries = [
    "AI coding agents market size 2025 site:gartner.com",
    "GitHub Copilot revenue 2024 site:sec.gov",
    "developer tools pricing benchmark 2025"
]

# Run in parallel via scripts/parallel_search.py
results = await execute_searches(queries, tools=["tavily", "brave_web"])
```

---

## Special Cases

### Finding Primary Data

**Government Sources:**
```
[topic] site:census.gov OR site:bls.gov OR site:sec.gov
```

**Academic Research:**
```
[topic] site:arxiv.org OR site:pubmed.gov
```

**Company Financials:**
```
[company] 10-K site:sec.gov/edgar
```

### Discovering Pain Points

**Reddit Strategy:**
```
site:reddit.com/r/[niche] [product] problem OR issue OR frustration
```

**Hacker News Strategy:**
```
site:news.ycombinator.com [product] "wish" OR "need" OR "missing"
```

### Verifying Claims

**Cross-Reference Pattern:**
```
1. Find initial claim (any source)
2. Search for corroboration: "[exact claim text]" site:tier1domain.com
3. If no Tier-1 match, flag as unverified
```

---

## Performance Optimization

### Reduce API Calls

**Use Caching:**
- Cache results for 24 hours
- Check cache before new search

**Batch Queries:**
```python
# Instead of 10 separate calls
for query in queries:
    search(query)

# Batch into 1-2 parallel calls
search_batch(queries)
```

### Rate Limit Handling

**Exponential Backoff (Tavily):**
```python
for i in range(max_retries):
    try:
        return tavily_search(query)
    except RateLimitError:
        wait = 2 ** i  # 1s, 2s, 4s, 8s
        time.sleep(wait)
```

**Linear Backoff (Brave):**
```python
for i in range(max_retries):
    try:
        return brave_search(query)
    except RateLimitError:
        wait = i + 1  # 1s, 2s, 3s
        time.sleep(wait)
```

---

## Quality Metrics

**Track per query:**
- Results returned
- Results after noise filtering
- Tier-1 sources found
- Cache hit rate
- Execution time

**Target Thresholds:**
- ≥50% noise filtered
- ≥2 Tier-1 sources per query
- <15 seconds execution time
