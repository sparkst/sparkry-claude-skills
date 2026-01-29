# QShortcuts Content Plugin

> Content creation shortcuts for multi-platform publishing, LinkedIn carousels, infographics, and visual generation

## Overview

The QShortcuts Content plugin provides 4 powerful content creation commands optimized for rapid execution with quality scoring, platform transformation, and visual generation.

## Commands

### QWRITE
**Multi-Platform Content Creation**

Generate publication-ready content with persona layering, quality scoring, and platform-specific transformations.

```bash
QWRITE: Educational Substack article on RAG systems, 1500 words
QWRITE: LinkedIn post announcing new feature
QWRITE: Proposal for new coaching program, target: executives
```

**Features:**
- Persona layering (educational, strategic, tutorial)
- Quality scoring (5 metrics: groundedness, relevance, readability, voice, originality)
- Platform transforms (Substack, LinkedIn, Twitter, Email)
- Link validation (blocking)
- Special links integration
- ASCII art framework generation

**Tools:** quality-scorer.py, voice-validator.py, link-validator.py, platform-constraints.py

### QPPT
**LinkedIn Carousel Generator**

Generate brand-compliant PowerPoint carousels from markdown with HTML-first approach and automatic contrast detection.

```bash
QPPT: Generate carousel from W01-LI-post1.md
QPPT: Batch generate carousels for week-01/*.md (where format=Carousel)
```

**Features:**
- HTML-first approach (Playwright screenshots)
- Automatic contrast detection (WCAG AA)
- Text limit enforcement (30 words, 5 lines per slide)
- Brand compliance validation
- Icon integration (Lucide/Iconify)
- PNG export for LinkedIn

**Tools:** slide-optimizer.py, slide-html-generator.py, screenshot-generator.py, color-contrast-validator.py

### QVISUAL
**Hero Images & Diagram Generator**

Generate eye-catching hero images and convert ASCII diagrams to professional visuals using HTML-to-image conversion.

```bash
QVISUAL: Generate visuals for content/articles/article.md
QVISUAL: Convert this ASCII to diagram: [paste ASCII art]
QVISUAL: Generate hero image for article.md
```

**Features:**
- Hero image generation (1200×630 OpenGraph)
- ASCII art detection and conversion
- Framework visualization
- HTML templates with brand styling
- Automatic integration in QWRITE polish phase

**Tools:** generate-hero-image.py, convert-ascii-to-visual.py, detect-visual-opportunities.py, render-html-to-image.py

### QINFOGRAPHIC
**Article Framework Infographics**

Transform article frameworks (3-10 steps/pillars) into visually compelling single-page HTML infographics.

```bash
QINFOGRAPHIC: Create from https://substack.com/article/5-pillars
QINFOGRAPHIC: Create from article.txt with brand colors #1a1a2e, #0f3460
```

**Features:**
- 10-agent pipeline (extraction → validation → creativity → rendering → QA)
- Hallucination prevention (blocking gates)
- Creative diversity tracking (no repetition in last 5)
- Visual metaphor system
- Copy compression with length limits
- WCAG AA accessibility

**Tools:** framework-extractor.py, framework-validator.py, pattern-selector.py, creativity-orchestrator.py, copy-compressor.py, html-generator.py, content-qa.py, diversity-tracker.py

## Story Points

| Command | Typical Use Case | SP |
|---------|------------------|-----|
| QWRITE | Standard article (Substack educational) | 2-3 SP |
| QWRITE | Multi-platform content (base + 3 transforms) | 5-8 SP |
| QPPT | First carousel creation | 3 SP |
| QPPT | Subsequent carousels (cached icons) | 0.5 SP |
| QVISUAL | Full article processing (hero + 2-3 diagrams) | 0.5 SP |
| QINFOGRAPHIC | Standard framework (6-8 elements) | 3 SP |

## Installation

### Dependencies

```bash
# Python requirements
pip install playwright Pillow requests python-pptx

# Install Playwright browser (required for QPPT, QVISUAL)
playwright install chromium  # ~200MB download
```

### Optional Fonts (PowerPoint fallback)

```bash
# macOS
brew install --cask font-poppins font-inter

# Linux (Ubuntu/Debian)
sudo apt install fonts-inter fonts-poppins
```

## Usage Examples

### Example 1: Complete Article Workflow

```bash
# Generate article with visuals
QWRITE: Educational Substack article on Permission Architecture, 1500 words

# Automatic in polish phase:
# - Quality scoring (≥85/100)
# - Link validation (blocking)
# - Hero image generation
# - ASCII diagram conversion
# - Framework visual generation

# Output:
# - article.md (publication-ready)
# - hero.png (1200×630)
# - diagram-1.png (framework)
```

### Example 2: LinkedIn Carousel

```bash
# Write LinkedIn post
QWRITE: LinkedIn post on AI adoption challenges, format: Carousel (8 slides)

# Generate carousel
QPPT: Generate carousel from post.md using HTML approach

# Output:
# - post.md (text)
# - slide-1.png ... slide-8.png (ready for LinkedIn upload)
```

### Example 3: Infographic from Article

```bash
# Extract framework and generate infographic
QINFOGRAPHIC: Create from https://substack.com/article/permission-architecture

# Pipeline executes:
# 1. Extract "3 Layers" framework
# 2. Validate against article
# 3. Select "stacked_blocks" visual metaphor
# 4. Compress copy to infographic constraints
# 5. Generate single-page HTML
# 6. QA for hallucinations

# Output:
# - infographic.html (embeddable)
# - infographic.json (spec)
```

## Integration with Other Plugins

### With Writing Workflow Plugin
- QWRITE extends the base writing skill with quality scoring and platform transforms
- Automatic visual generation in polish phase

### With Strategy Workflow Plugin
- QINFOGRAPHIC can visualize strategic frameworks from PR/FAQs
- QPPT can create carousel presentations for strategic plans

### With Research Workflow Plugin
- QWRITE uses research agents for fact-checking
- QINFOGRAPHIC validates frameworks against source articles

## Quality Gates

All commands enforce quality gates:

### QWRITE
- Post-Research: Sources validated, independence confirmed
- Post-Draft: No critical missing info, ASCII art for frameworks
- Post-Editorial: ≥85/100 quality score
- Post-Transform: Platform constraints verified
- Post-Polish: All links valid (HTTP 200) - BLOCKING

### QPPT
- Post-Parsing: 6-10 slides, max 30 words per slide
- Post-HTML-Generation: All HTML files created with embedded fonts
- Post-Screenshot: All PNG images at 1080×1080
- Post-Validation: WCAG AA compliance, no black-on-black text

### QVISUAL
- Post-Detection: Opportunities identified
- Post-Generation: All files <500KB
- Post-Render: All dimensions correct

### QINFOGRAPHIC
- Framework Validation: All elements backed by article - BLOCKING
- Copy Compression: No missing elements, length limits - BLOCKING
- Content QA: No hallucinations - BLOCKING

## Performance Metrics

### QWRITE
- Latency: <5 minutes end-to-end
- Token Budget: <20K per workflow
- Quality Target: ≥85/100 average

### QPPT (HTML-First)
- First carousel: 30-45 seconds
- Subsequent (cached): 10-15 seconds
- File size: 2-3 MB (LinkedIn optimized)

### QVISUAL
- Hero image: <3 seconds
- ASCII diagram: <5 seconds
- Full article: <10 seconds

### QINFOGRAPHIC
- Token Budget: <25K per pipeline
- Latency: <3 minutes end-to-end
- Creativity Variation: No repetition in last 5

## Directory Structure

```
plugins/qshortcuts-content/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   ├── qwrite/
│   │   ├── SKILL.md
│   │   ├── tools/
│   │   │   ├── quality-scorer.py
│   │   │   ├── voice-validator.py
│   │   │   ├── link-validator.py
│   │   │   ├── special-links-matcher.py
│   │   │   ├── platform-constraints.py
│   │   │   └── template-selector.py
│   │   ├── references/
│   │   │   ├── personas/
│   │   │   ├── templates/
│   │   │   └── constraints/
│   │   └── agents/
│   │       └── synthesis-writer.md
│   ├── qppt/
│   │   ├── SKILL.md
│   │   ├── tools/
│   │   │   ├── slide-optimizer.py
│   │   │   ├── slide-html-generator.py
│   │   │   ├── screenshot-generator.py
│   │   │   ├── color-contrast-validator.py
│   │   │   ├── ppt-generator.py
│   │   │   ├── icon-fetcher.py
│   │   │   └── brand-validator.py
│   │   └── references/
│   │       ├── brand-guidelines.json
│   │       ├── slide-layouts.json
│   │       ├── icon-mappings.json
│   │       └── linkedin-carousel-best-practices.md
│   ├── qvisual/
│   │   ├── SKILL.md
│   │   ├── tools/
│   │   │   ├── generate-hero-image.py
│   │   │   ├── convert-ascii-to-visual.py
│   │   │   ├── detect-visual-opportunities.py
│   │   │   └── render-html-to-image.py
│   │   └── references/
│   │       ├── templates/
│   │       │   ├── hero-image.html
│   │       │   └── framework-diagram.html
│   │       ├── examples/
│   │       │   └── ascii-patterns.md
│   │       └── brand-guidelines.json
│   └── qinfographic/
│       ├── SKILL.md
│       ├── tools/
│       │   ├── framework-extractor.py
│       │   ├── framework-validator.py
│       │   ├── pattern-selector.py
│       │   ├── creativity-orchestrator.py
│       │   ├── copy-compressor.py
│       │   ├── html-generator.py
│       │   ├── content-qa.py
│       │   └── diversity-tracker.py
│       └── references/
│           ├── visual-metaphors.json
│           ├── headline-patterns.json
│           ├── layout-templates.json
│           ├── icon-mappings.json
│           └── best-practices.md
├── README.md
└── LICENSE
```

## Troubleshooting

### Playwright not installed
```bash
pip install playwright
playwright install chromium
```

### Screenshots show broken fonts
- Web fonts load from Google Fonts CDN (internet required)
- Check internet connection during generation

### Black-on-black text (QPPT)
- Fixed in v2.0 with automatic contrast detection
- Verify color-contrast-validator.py is callable

### Links validation fails (QWRITE)
- BLOCKING gate: All links must return HTTP 200
- Fix broken links before proceeding

### Hallucination detected (QINFOGRAPHIC)
- BLOCKING gate: Cannot proceed with fabricated content
- Review framework extraction and validation

## License

MIT

## Contributing

See CONTRIBUTING.md in the root of the repository.

## Version

1.0.0
