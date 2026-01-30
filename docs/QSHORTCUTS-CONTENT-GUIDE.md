# QShortcuts Content - Content Creation Shortcuts

## Overview

QShortcuts Content provides shortcuts for content creation: QWRITE for multi-platform writing, QPPT for presentations, QVISUAL for visual content, and QINFOGRAPHIC for infographics.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install QShortcuts Content

```
/plugin install qshortcuts-content@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Available Shortcuts

| Shortcut | Purpose | When to Use |
|----------|---------|-------------|
| **QWRITE** | Multi-platform writing | Blog posts, social media, newsletters |
| **QPPT** | Presentation slides | LinkedIn carousels, pitch decks |
| **QVISUAL** | Visual content | Diagrams, illustrations |
| **QINFOGRAPHIC** | Infographics | Data visualization, frameworks |

------------------------------------------------------------------------

## Usage Examples

### QWRITE - Multi-Platform Content

```
QWRITE Article about AI in healthcare for Substack
```

**What it does:**
- Creates content for specified platform
- Applies voice consistency
- Optimizes for platform requirements
- Includes quality scoring
- Generates multi-platform variants

**Supported platforms:**
- Substack (long-form articles)
- LinkedIn (professional posts)
- Twitter/X (threads)
- Email newsletters
- Blog posts

**Output:** Platform-optimized content with quality score

------------------------------------------------------------------------

### QPPT - Presentation Slides

```
QPPT LinkedIn carousel about 5 AI productivity tips
```

**What it does:**
- Creates slide-by-slide content
- Designs visual layout suggestions
- Optimizes for platform (LinkedIn carousel format)
- Includes speaker notes
- Generates headline + supporting points

**Output:** Slide deck content with visual directions

**Slide structure:**
```
Slide 1: Hook/Title
Slides 2-N: Key points with visuals
Final Slide: CTA/Summary
```

------------------------------------------------------------------------

### QVISUAL - Visual Content

```
QVISUAL Create a diagram showing our microservices architecture
```

**What it does:**
- Analyzes content for visual opportunities
- Creates diagram specifications
- Generates ASCII/Mermaid representations
- Provides design direction for graphics

**Visual types:**
- Architecture diagrams
- Flow charts
- Comparison tables
- Process illustrations
- Concept maps

**Output:** Visual specifications and ASCII/Mermaid code

------------------------------------------------------------------------

### QINFOGRAPHIC - Infographics

```
QINFOGRAPHIC Turn this framework into a visual infographic
```

**What it does:**
- Extracts key data points
- Designs information hierarchy
- Creates visual layout
- Applies brand guidelines (if provided)
- Generates production-ready specs

**Output:** Infographic design with:
- Layout specifications
- Color scheme
- Typography
- Icon suggestions
- Data visualizations

------------------------------------------------------------------------

## Content Quality Scoring

QWRITE includes quality scoring:

| Score | Meaning |
|-------|---------|
| 90-100 | Excellent - ready to publish |
| 80-89 | Good - minor tweaks needed |
| 70-79 | Acceptable - review recommended |
| <70 | Needs work - revise before publishing |

**Scoring dimensions:**
- Voice consistency
- Platform optimization
- Engagement hooks
- Call-to-action clarity
- SEO (where applicable)

------------------------------------------------------------------------

## Platform Requirements

### LinkedIn Posts
- 1,300 character limit (expanded)
- Hook in first 2 lines
- Use line breaks for readability
- End with engagement question

### LinkedIn Carousels
- 10 slides max recommended
- Square format (1080x1080)
- Bold headlines
- Minimal text per slide

### Substack
- Long-form friendly
- Support for images
- Email preview optimization
- SEO title/description

### Twitter/X
- 280 characters per tweet
- Thread structure
- Media attachments
- Hashtag strategy

------------------------------------------------------------------------

## Workflow Integration

### Content Campaign
```
1. QIDEA     →  Research topic
2. QWRITE    →  Create main content
3. QPPT      →  Create carousel version
4. QVISUAL   →  Add diagrams
5. QINFOGRAPHIC → Create shareable graphic
```

### Repurposing Content
```
1. QWRITE    →  Long-form article
2. QWRITE    →  LinkedIn summary
3. QWRITE    →  Twitter thread
4. QPPT      →  Carousel highlights
```

------------------------------------------------------------------------

## Related Plugins

- **writing-workflow** - Full writing system with agents
- **qshortcuts-support** - QDOC for documentation

------------------------------------------------------------------------

## Troubleshooting

### Content doesn't match my voice

Provide voice guidelines or examples of your previous content.

### Slides too text-heavy

Specify "minimal text" or "visual-first" in your request.

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
