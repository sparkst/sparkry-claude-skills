# Writing Workflow - Content Creation System

## Overview

Writing Workflow provides a complete content creation system with multi-platform publishing, infographic generation, quality scoring, and voice consistency. Create content once, publish everywhere.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install Writing Workflow

```
/plugin install writing-workflow@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Included Components

### Agents
| Agent | Role |
|-------|------|
| **Synthesis Writer** | Long-form content creation |
| **Docs Writer** | Technical documentation |

### Skills
| Skill | Purpose |
|-------|---------|
| **writing** | Multi-platform content with voice consistency |
| **infographics** | Visual content generation |
| **publishing** | Google Docs integration |
| **presentation** | Carousel and slide creation |
| **visual-content** | Diagrams and illustrations |

------------------------------------------------------------------------

## Usage

### Multi-Platform Content

```
/write "Article about AI productivity tools" --platform substack
```

```
/write "Product launch announcement" --platform linkedin,twitter,email
```

### With Quality Scoring

```
/write "Thought leadership piece on AI trends" --score
```

Output includes quality score (0-100) with breakdown.

------------------------------------------------------------------------

## Platform Support

| Platform | Format | Optimization |
|----------|--------|--------------|
| **Substack** | Long-form article | SEO, email preview |
| **LinkedIn** | Professional post | Hook, engagement |
| **Twitter/X** | Thread | Character limits, hooks |
| **Email** | Newsletter | Subject lines, preview text |
| **Blog** | Article | SEO, readability |
| **Medium** | Story | Tags, formatting |

------------------------------------------------------------------------

## Quality Scoring

Content is scored on multiple dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Voice** | 25% | Consistency with brand voice |
| **Structure** | 20% | Logical flow, formatting |
| **Engagement** | 20% | Hooks, readability |
| **Platform Fit** | 20% | Platform-specific optimization |
| **CTA Clarity** | 15% | Clear next steps |

### Score Interpretation
- **90-100:** Publish-ready
- **80-89:** Minor tweaks needed
- **70-79:** Review recommended
- **<70:** Significant revision needed

------------------------------------------------------------------------

## Voice Consistency

Define your voice profile:

```yaml
voice:
  tone: professional yet approachable
  perspective: first person
  vocabulary: technical but accessible
  avoid: jargon, buzzwords, passive voice
  include: examples, analogies, questions
```

The system maintains consistency across all platforms.

------------------------------------------------------------------------

## Infographic Generation

```
/infographic "The 5-step AI adoption framework"
```

**Output includes:**
- Layout specifications
- Color scheme
- Typography recommendations
- Icon suggestions
- Data visualization specs
- Production-ready design brief

------------------------------------------------------------------------

## Presentation/Carousel

```
/carousel "7 habits of effective AI teams" --platform linkedin
```

**Output:**
- Slide-by-slide content
- Visual direction per slide
- Hook slide
- CTA slide
- Optimal slide count

------------------------------------------------------------------------

## Publishing Integration

### Google Docs

```
/publish-to-docs "My Article Title"
```

Publishes content directly to Google Docs with formatting preserved.

------------------------------------------------------------------------

## Content Workflow

### Full Content Campaign

```
1. /write "Main article" --platform substack
   → Long-form foundation piece

2. /write "LinkedIn version" --platform linkedin
   → Professional summary

3. /write "Twitter thread" --platform twitter
   → Bite-sized highlights

4. /carousel "Key takeaways"
   → Visual carousel

5. /infographic "Framework summary"
   → Shareable visual

6. /publish-to-docs
   → Archive in Google Docs
```

------------------------------------------------------------------------

## Templates

### Substack Article
```
- Hook (first 2 lines visible in email)
- The Problem
- The Solution
- Framework/Steps
- Examples
- Conclusion
- CTA
```

### LinkedIn Post
```
- Hook line (stops the scroll)
- Empty line
- Body (3-5 short paragraphs)
- Empty line
- CTA or question
```

### Twitter Thread
```
Tweet 1: Hook + promise
Tweets 2-N: One point each
Final Tweet: Summary + CTA
```

------------------------------------------------------------------------

## Voice Profiles (Examples)

### Educational
- Clear explanations
- Step-by-step guidance
- Examples and analogies
- Encouraging tone

### Strategic
- Executive-level language
- Data-driven insights
- Business impact focus
- Confident tone

### Technical
- Precise terminology
- Code examples
- Architecture details
- Objective tone

------------------------------------------------------------------------

## Integration with QShortcuts

```
QWRITE "Article about microservices best practices"
```

Uses writing-workflow under the hood.

------------------------------------------------------------------------

## Related Plugins

- **qshortcuts-content** - QWRITE, QPPT shortcuts
- **research-workflow** - For research-backed content

------------------------------------------------------------------------

## Troubleshooting

### Voice inconsistent

Provide voice examples or define voice profile explicitly.

### Content too long for platform

Specify word count limits or use platform-specific commands.

### Quality score too low

Review the dimension breakdown and address specific weaknesses.

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
