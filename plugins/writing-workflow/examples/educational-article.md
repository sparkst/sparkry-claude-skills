# Example: Educational Article Generation

## Input Request

```
QWRITE: "Write educational article explaining RAG (Retrieval-Augmented Generation) for non-technical audience, 1500 words, Substack platform"
```

## Workflow Execution

### 1. Research Phase
- Query RAG concept from knowledge base
- Validate 2+ Tier-1 sources (academic papers, official docs)
- Load portfolio for voice examples

### 2. Planning Phase
- Persona selected: `educational.md`
- Template selected: `substack-educational.md`
- Quality target: ≥85/100

### 3. Drafting Phase
- Apply BLUF structure (Bottom Line Up Front)
- Use accessible language for technical concepts
- Include ASCII art framework diagram
- Insert [AUTHOR: ...] for missing context

### 4. Editorial Phase (3 passes max)

**Pass 1 Results**:
```json
{
  "overall": 82,
  "scores": {
    "groundedness": 85,
    "relevance": 88,
    "readability": 80,
    "voice": 78,
    "originality": 79
  },
  "issues": [
    {
      "metric": "voice",
      "priority": "P1",
      "location": "paragraph 3",
      "issue": "Generic AI phrase: 'it's important to note'",
      "fix": "Remove hedge or replace with direct statement"
    },
    {
      "metric": "readability",
      "priority": "P1",
      "location": "section 2",
      "issue": "Paragraph too long (8 sentences)",
      "fix": "Break into 2 paragraphs"
    }
  ],
  "recommendation": "revise"
}
```

**Pass 2 Results** (after P1 fixes):
```json
{
  "overall": 87,
  "scores": {
    "groundedness": 85,
    "relevance": 88,
    "readability": 90,
    "voice": 87,
    "originality": 85
  },
  "recommendation": "publish"
}
```

### 5. Transform Phase
- Substack format validation
- Platform constraints checked
- All metrics pass

### 6. Polish Phase
- Links validated (all HTTP 200)
- Special links integrated naturally
- [AUTHOR: ...] comments removed
- Final formatting applied

## Output

### Quality Metrics
```
Overall Score: 87/100
- Groundedness: 85/100
- Relevance: 88/100
- Readability: 90/100
- Voice: 87/100
- Originality: 85/100

Status: Ready for publication
Passes: 2 of 3
Token Usage: 14,200 tokens
```

### Content Preview

```markdown
# How RAG Actually Works: A Visual Guide

You've probably used AI chatbots that "remember" context from earlier in
the conversation. That's RAG at work.

RAG (Retrieval-Augmented Generation) is how AI systems search through
documents to answer questions. Instead of memorizing everything, they
look it up just-in-time—like you searching Google before answering
a question.

In this guide, we'll break down exactly how RAG works, why it's better
than alternatives, and where it breaks down. No jargon, just clear
explanations with diagrams.

## 1. The Problem RAG Solves

...
```

### Files Generated
- `content/articles/rag-guide.md` (publication-ready markdown)
- `content/visuals/rag-guide-hero.png` (hero image)
- `content/visuals/rag-diagram.png` (framework diagram)

### Google Docs (if configured)
- **URL**: https://docs.google.com/document/d/...
- **Operation**: created
- **Category**: Substack

## Key Learnings

### What Worked Well
1. BLUF structure made content immediately valuable
2. Accessible analogies (search engine comparison)
3. Visual diagrams enhanced understanding
4. Quality iteration improved voice consistency

### Improvements Made
1. Removed hedging language ("it's important to note")
2. Split long paragraphs for scannability
3. Added concrete examples for abstract concepts
4. Strengthened transitions between sections

## Estimated Time Savings

- **Manual writing**: 3-4 hours
- **Automated workflow**: 4-5 minutes
- **Time savings**: ~95%

## Next Steps

To improve future educational content:
1. Add more industry-specific examples
2. Expand visual diagram patterns
3. Build portfolio RAG for better voice matching
4. Test with blind voice attribution
