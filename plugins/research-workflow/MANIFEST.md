# Research Workflow Plugin - File Manifest

## Plugin Metadata
- **File:** `.claude-plugin/plugin.json`
- **Description:** Plugin configuration and metadata

## Documentation
- **File:** `README.md`
- **Description:** Complete plugin documentation with usage examples

## Agents (5 files)

### 1. research-director.md
- **Role:** Orchestrates the complete research workflow
- **Tools:** Read, Grep, Glob, Edit, Write, WebSearch, WebFetch
- **Key Features:**
  - Intake and planning
  - Specialist coordination
  - Dissent management
  - Synthesis coordination
  - Telemetry logging

### 2. fact-checker.md
- **Role:** Validates claims with evidence requirements
- **Tools:** Read, Grep, Glob, WebSearch, WebFetch
- **Key Features:**
  - Claim extraction
  - Evidence validation (≥2 Tier-1 sources)
  - Date alignment checking
  - Soft quality gates
  - Claims JSON output

### 3. source-evaluator.md
- **Role:** Evaluates source credibility using 4-tier framework
- **Tools:** Read, Grep, Glob, WebSearch, WebFetch
- **Key Features:**
  - Tier classification (1-4)
  - Independence checking
  - Recency validation
  - Source review JSON output

### 4. dissent-moderator.md
- **Role:** Synthesizes disagreements into decision-ready options
- **Tools:** Read, Grep, Glob, Edit, Write
- **Key Features:**
  - Position memo collection
  - Options matrix creation (2-3 options)
  - Risk and reversibility assessment
  - Cost and time-to-impact analysis
  - Decision framework generation

### 5. synthesis-writer.md
- **Role:** Creates proposal-first deliverables
- **Tools:** Read, Grep, Glob, Edit, Write
- **Key Features:**
  - Executive summary (1 page)
  - Appendices (sources, claims, dissent)
  - Claim validation integration
  - Proposal markdown output

## Skills (6 skills with resources)

### 1. research/plan/
- **File:** `SKILL.md`
- **Description:** Creates structured research plans
- **Resources:**
  - `resources/query-strategies.md` - Advanced search query patterns
  - `resources/tier-definitions.md` - Complete tier classification guide
  - `templates/research-plan-template.json` - JSON schema for plans

### 2. research/fact-check/
- **File:** `SKILL.md`
- **Description:** Validates load-bearing claims
- **Scripts:**
  - `scripts/date_checker.py` - Date alignment validation tool

### 3. research/industry-scout/
- **File:** `SKILL.md`
- **Description:** Searches for best-of-best sources
- **Features:**
  - Noise filtering (SEO spam, AI content)
  - Canonical source mapping
  - Multi-tool orchestration

### 4. research/options-matrix/
- **File:** `SKILL.md`
- **Description:** Builds decision-ready options matrices
- **Features:**
  - Pros/cons analysis
  - Risk assessment
  - Reversibility evaluation
  - Cost estimation

### 5. research/source-policy/
- **File:** `SKILL.md`
- **Description:** Source quality evaluation framework
- **Features:**
  - 4-tier classification system
  - Independence checks
  - Recency validation
  - Quality gates

### 6. research/web-exec/
- **File:** `SKILL.md`
- **Description:** Parallel web search orchestration
- **Scripts:**
  - `scripts/parallel_search.py` - Async search executor
- **Features:**
  - Parallel execution
  - Rate limiting
  - Caching
  - Deduplication

## Complete File Tree

```
research-workflow/
├── .claude-plugin/
│   └── plugin.json
├── README.md
├── MANIFEST.md
├── agents/
│   ├── research-director.md
│   ├── fact-checker.md
│   ├── source-evaluator.md
│   ├── dissent-moderator.md
│   └── synthesis-writer.md
└── skills/
    └── research/
        ├── plan/
        │   ├── SKILL.md
        │   ├── resources/
        │   │   ├── query-strategies.md
        │   │   └── tier-definitions.md
        │   └── templates/
        │       └── research-plan-template.json
        ├── fact-check/
        │   ├── SKILL.md
        │   └── scripts/
        │       └── date_checker.py
        ├── industry-scout/
        │   └── SKILL.md
        ├── options-matrix/
        │   └── SKILL.md
        ├── source-policy/
        │   └── SKILL.md
        └── web-exec/
            ├── SKILL.md
            └── scripts/
                └── parallel_search.py
```

## File Counts
- **Total Files:** 18
- **Agents:** 5
- **Skills:** 6
- **Python Scripts:** 2
- **Resource Files:** 2
- **Templates:** 1
- **Documentation:** 2 (README.md, MANIFEST.md)
- **Configuration:** 1 (plugin.json)

## Dependencies

### Python Scripts
- **Python Version:** >=3.8
- **Standard Library:** asyncio, json, hashlib, datetime, pathlib, urllib, argparse, re, time

### Network Access
- **Required for:**
  - research/industry-scout (web searches)
  - research/web-exec (parallel search execution)

### External APIs (Optional)
- Tavily Search API (for advanced web research)
- Brave Search API (for broad discovery)

## Version
- **Current:** 1.0.0
- **License:** MIT
- **Author:** Example.ai (skills@example.com)

## Validation Checklist

- [x] All agents have frontmatter (name, description, tools)
- [x] All skills have SKILL.md with metadata
- [x] Python scripts are executable and documented
- [x] Resource files provide actionable guidance
- [x] Templates include JSON schemas
- [x] README.md provides complete documentation
- [x] plugin.json follows schema
- [x] No sensitive data (paths scrubbed to ${PROJECT_ROOT})
- [x] No personal emails (changed to skills@sparkry.ai)
- [x] File tree is complete and organized
