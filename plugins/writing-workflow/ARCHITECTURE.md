# Writing Workflow Plugin - Architecture

## Overview

Multi-agent content creation system orchestrating research, drafting, editorial review, platform transformation, and publishing into a cohesive workflow.

## Core Principles

1. **Quality over speed**: 5-metric evaluation system with iterative improvement
2. **Voice authenticity**: Persona layering system for consistent, recognizable voice
3. **Platform-native**: Structural transformation, not truncation
4. **Token efficiency**: <20K tokens per workflow with budgeting
5. **Fail-safe**: Graceful degradation with quality gates

## System Architecture

### High-Level Flow

```
User Request → Orchestrator → Research (parallel) → Planning
                           → Portfolio RAG ────┘
                                    │
                                    ▼
                            Writer (Draft)
                                    │
                                    ▼
                     Editorial (Max 3 passes)
                                    │
                                    ▼
                Platform Transform (Parallel)
                                    │
                                    ▼
                Polish (Links, Visuals, Publish)
                                    │
                                    ▼
                            Final Output
```

### Agent Responsibilities

#### Orchestrator Agent
**Role**: Workflow coordination, token budgeting, quality gates

**Responsibilities**:
- Parse user request and determine workflow
- Allocate token budget across phases
- Coordinate parallel work (research + RAG)
- Enforce quality gates between phases
- Monitor diminishing returns in editorial passes

**Tools**: All Claude tools (Read, Grep, Glob, Edit, Write, Bash)

#### Research Agent
**Role**: Source validation and fact-checking

**Responsibilities**:
- Find ≥2 independent sources for major claims
- Validate source tier quality (Tier-1 preferred)
- Extract relevant evidence
- Flag unsupported claims

**Tools**: Grep, Read, Bash (web search if available)

#### Portfolio RAG
**Role**: Voice pattern retrieval

**Responsibilities**:
- Semantic search through past content
- Retrieve voice pattern examples
- Provide sentence structure samples
- Extract transitional phrases

**Current state**: Uses persona docs directly (Phase 1)
**Future**: Vector database with semantic search (Phase 2)

#### Writer Agent
**Role**: Content drafting with persona + template

**Responsibilities**:
- Apply persona voice patterns
- Follow template structure
- Integrate research findings
- Insert [AUTHOR: ...] for missing context
- Generate ASCII art for frameworks

**Tools**: quality-scorer.py (preview), template-selector.py

#### Editorial Agent
**Role**: Quality evaluation and improvement

**Responsibilities**:
- Score on 5 metrics (0-100 scale)
- Identify P0/P1/P2 issues with specifics
- Re-evaluate after fixes
- Stop at ≥85/100 or 3 passes (diminishing returns)
- Track improvement trajectory

**Tools**: quality-scorer.py, voice-validator.py

#### Platform Transform Agent
**Role**: Platform-specific adaptation

**Responsibilities**:
- Parallel transforms for multi-platform
- Structural transformation (not truncation)
- Tone/formality adjustment per platform
- Validate platform constraints

**Tools**: platform-constraints.py

#### Polish Agent
**Role**: Final validation and publishing

**Responsibilities**:
- Validate all links (HTTP 200) - **BLOCKING**
- Integrate special_links naturally
- Generate visual content (articles only)
- Publish to Google Docs (if configured)
- Remove [AUTHOR: ...] comments
- Final formatting

**Tools**: link-validator.py, special-links-matcher.py, visual generators, publishing tools

## Data Flow

### Input Schema

```typescript
interface WriteRequest {
  topic: string;
  platform: Platform[];
  contentType: ContentType;
  depth: "quick" | "moderate" | "comprehensive";
  audience: Audience;
  lengthTarget?: number; // words
}

type Platform = "substack" | "linkedin" | "twitter" | "instagram" | "email" | "proposal";
type ContentType = "strategic" | "tutorial" | "educational" | "social";
type Audience = "technical" | "business" | "general" | "internal";
```

### Output Schema

```typescript
interface WriteOutput {
  qualityMetrics: QualityMetrics;
  content: {
    [platform: string]: string; // markdown
  };
  visualContent?: VisualContent; // articles only
  publishedDocs?: PublishedDoc[]; // if configured
  recommendations: string[];
  tokenUsage: TokenUsage;
}

interface QualityMetrics {
  overall: number; // 0-100
  scores: {
    groundedness: number;
    relevance: number;
    readability: number;
    voice: number;
    originality: number;
  };
  passes: number;
  status: "publish" | "revise" | "major_revision";
}

interface VisualContent {
  heroImage: string; // path
  diagrams: {
    path: string;
    title: string;
    size: string; // e.g., "1200×800"
    fileSize: string; // e.g., "194KB"
  }[];
  generationTime: number; // seconds
  totalSize: string; // e.g., "699KB"
}
```

## Persona Layering System

### Layer Stack

```
┌──────────────────────────────────────┐
│ Base Voice Layer (Core patterns)     │  ← Always present
├──────────────────────────────────────┤
│ Content Type Layer                   │  ← Strategic/Tutorial/Educational
├──────────────────────────────────────┤
│ Platform Layer                       │  ← Substack/LinkedIn/Twitter/etc
├──────────────────────────────────────┤
│ Audience Layer                       │  ← Technical/Business/General
└──────────────────────────────────────┘
```

### Persona Resolution

Given request: "Educational article for technical audience on LinkedIn"

**Resolution path**:
1. Load base voice patterns (core vocabulary, sentence structure)
2. Apply educational persona (empathy-first, BLUF, progressive complexity)
3. Apply LinkedIn platform constraints (hook ≤25 words, professional tone)
4. Adjust for technical audience (allow higher Hemingway grade)

**Result**: Educational voice + LinkedIn format + technical depth

### Persona Files

Located in `skills/writing/references/personas/`:

- `educational.md`: Teaching voice, accessible explanations
- `strategic.md`: Business insights, systems thinking
- `tutorial.md`: Technical instruction, step-by-step precision

Each file defines:
- Sentence structure patterns
- Vocabulary preferences
- Transition phrases
- Example openings/closings
- Voice characteristics

## Quality Framework

### 5 Metrics (0-100 scale)

#### 1. Groundedness
**What**: Claims supported by credible sources

**Scoring**:
- 90-100: Tier-1 sources, direct citations
- 80-89: Mix Tier-1/2, most claims supported
- 70-79: Mostly Tier-2, some unsupported
- <70: Weak or missing sources

**Tools**: Research agent validates source tier

#### 2. Relevance
**What**: Content serves reader's goal

**Scoring**:
- 90-100: Every paragraph addresses core question
- 80-89: Mostly on-topic, minor tangents
- 70-79: Some drift
- <70: Significant irrelevance

**Tools**: Editorial agent checks alignment

#### 3. Readability
**What**: Clear, scannable, appropriate for audience

**Scoring**:
- 90-100: Hemingway ≤8, scannable, clear
- 80-89: Good readability
- 70-79: Readable but could improve
- <70: Dense or confusing

**Tools**: quality-scorer.py (textstat integration)

#### 4. Voice Consistency
**What**: Matches persona, sounds authentic

**Scoring**:
- 90-100: Perfect persona match, no AI tells
- 80-89: Mostly matches, minor AI tells
- 70-79: Voice present but inconsistent
- <70: Generic AI voice

**Tools**: voice-validator.py checks patterns

#### 5. Originality
**What**: Unique insights, specific examples

**Scoring**:
- 90-100: Unique insights, fresh perspective
- 80-89: Some originality
- 70-79: Mostly original
- <70: Clichéd, generic

**Tools**: Editorial agent evaluates

### Iteration Policy

- **Max 3 passes**: Diminishing returns after 3
- **Stop conditions**:
  - Overall ≥85/100
  - All metrics ≥80/100
  - 3 passes completed
  - No P0 issues
- **Priority levels**:
  - P0: Blocking (must fix)
  - P1: Strongly recommended
  - P2: Optional

## Token Budget

| Phase | Target | Max | Notes |
|-------|--------|-----|-------|
| Research | 2-5K | 7K | Parallel with RAG |
| Planning | 1-2K | 3K | Persona + template selection |
| Drafting | 3-6K | 8K | First draft with ASCII art |
| Editorial (3 passes) | 6-12K | 12K | Max 3 iterations |
| Transform | 1-2K per platform | 3K | Parallel transforms |
| Polish | 1-2K | 3K | Links, visuals, publish |
| **Total** | **10-20K** | **25K** | Hard cap |

**Monitoring**: Flag if >25K, optimize next run

## Platform Requirements

### Substack (Long-Form)

```json
{
  "length": "800-3000 words",
  "opening": "BLUF (Bottom Line Up Front)",
  "structure": "Scannable headers, white space",
  "links": "Inline",
  "cta": "Subscribe at bottom only"
}
```

### LinkedIn (Professional Network)

```json
{
  "hook": "First 25 words (before 'see more')",
  "length": "1900-2000 words for articles",
  "tone": "Professional but conversational",
  "structure": "Clear section breaks",
  "cta": "Comment prompt or connection request"
}
```

### Twitter/BlueSky (Microblogging)

```json
{
  "optimal": "40-80 characters",
  "max": "280 characters",
  "hashtags": "1-2 max",
  "tone": "Conversational",
  "structure": "Lead with insight, context second"
}
```

### Email (Direct Communication)

```json
{
  "subject": "<50 characters, compelling",
  "body": "Bullet points, single CTA",
  "length": "<300 words",
  "tone": "Conversational but purposeful"
}
```

### Proposal (Formal Document)

```json
{
  "opening": "Executive summary first page",
  "structure": "Data-driven, formal sections",
  "evidence": "Required for all claims",
  "length": "5-15 pages"
}
```

## Error Handling

### Graceful Degradation

| Failure | Fallback | Impact |
|---------|----------|--------|
| Research fails | Use cached knowledge | Flag limited sources |
| RAG retrieval low | Use persona docs directly | Slightly weaker voice match |
| Quality not improving | Cap at 3 passes | Flag for human review |
| Link validation fails | Flag broken links | Proceed with warning |
| Token budget exceeded | Complete workflow | Log for optimization |

### Retry Strategies

- **Network failures**: 3 retries with exponential backoff (1s, 2s, 4s)
- **API rate limits**: Exponential backoff up to 60s
- **Validation failures**: Return error, no retries

## Extension Points

### Adding New Platforms

1. Define constraints in `constraints/platform-requirements.json`
2. Create template in `templates/[platform].md`
3. Update transform agent with platform logic
4. Add platform validation in polish phase

### Adding New Personas

1. Study target voice (5-10 examples)
2. Extract patterns (sentence structure, vocabulary, transitions)
3. Document in `personas/[name].md`
4. Test with voice-validator.py
5. Iterate until ≥80 consistency score

### Adding New Content Types

1. Analyze successful content structure
2. Create template in `templates/[type].md`
3. Define quality rubric adjustments (if needed)
4. Test workflow end-to-end
5. Document in README

## Performance Monitoring

### Operational Metrics

- **Latency**: Target <5 minutes end-to-end
- **Token efficiency**: Target <20K tokens
- **Success rate**: Target ≥80% complete without human intervention

### Quality Metrics

- **Voice attribution**: Target ≥70% (blind test)
- **Quality score**: Target ≥85/100 average
- **Human edit rate**: Target <20% post-generation

### Business Metrics

- **Time savings**: Hours saved vs manual writing
- **Content volume**: Articles per week
- **Engagement**: Performance of generated content

## Security Considerations

### Content Safety

- No fabrication: Insert [AUTHOR: ...] when context missing
- Source validation: Tier-1 preferred, flag Tier-3/4
- Link validation: All URLs checked (HTTP 200)

### Data Privacy

- No PII in persona files (use generic examples)
- No API keys in skill files (use environment variables)
- No personal voice samples in public bundle

### Publishing Safety

- Registry prevents duplicate document creation
- Backup registry before writes
- Validate file exists before publishing
- Log errors without updating registry on failures

## Future Enhancements

### Phase 2: Portfolio RAG
- Vector database for voice examples
- Semantic search through past content
- Continuous voice learning

### Phase 3: Visual Intelligence
- Automatic diagram generation from ASCII art
- Brand-compliant infographic templates
- Image optimization for platforms

### Phase 4: Multi-Modal
- Video script generation
- Podcast outline creation
- Presentation deck generation

---

**Version**: 1.0.0
**Last Updated**: 2026-01-28
