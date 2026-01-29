# Writing Workflow Plugin

A comprehensive multi-agent content creation system for Claude Code that produces publication-ready content with authentic voice across platforms.

## Overview

This plugin provides a complete writing workflow system with:

- **Multi-agent orchestration** for research, drafting, editorial review, and platform transformation
- **Quality-driven iteration** with 5 metrics (Groundedness, Relevance, Readability, Voice, Originality)
- **Platform-specific optimization** for Substack, LinkedIn, Twitter, Instagram, Email, and Proposals
- **Visual content generation** including hero images, diagrams, and infographics
- **Publishing automation** to Google Docs and other platforms

## Features

### Core Writing System (QWRITE)

- **Persona layering**: Educational, strategic, and technical voice patterns
- **Template-based structure**: Pre-built frameworks for consistent quality
- **Quality scoring**: Automated 0-100 scoring on 5 dimensions
- **Platform transformation**: Structural adaptation (not truncation) for target platforms
- **Link validation**: Automated checking of all URLs (HTTP 200)
- **Token efficiency**: <20K tokens per workflow

### Visual Content (QVISUAL)

- **Hero image generation**: Branded hero images from article content
- **Diagram conversion**: ASCII art to visual diagrams
- **Framework detection**: Automatic identification of visual opportunities

### Infographics (QINFOGRAPHIC)

- **Framework extraction**: Detect 3-10 step frameworks in articles
- **Pattern-based design**: 10+ creative layout patterns
- **HTML generation**: Production-ready infographic HTML with embedded CSS
- **Creative orchestration**: Multiple design iterations with diversity tracking

### PowerPoint Carousels (QPPT)

- **LinkedIn carousel generation**: Brand-compliant PowerPoint slides
- **Slide optimization**: Content chunking and layout optimization
- **Brand validation**: Ensure consistency with brand guidelines

### Google Docs Publishing

- **Automated publishing**: Markdown to Google Docs via webhook
- **Registry management**: Prevent duplicate documents
- **Version tracking**: Update history and metadata

## Installation

### Prerequisites

- Python 3.9 or higher
- Claude Code CLI
- Optional: Google account for publishing features

### Install Plugin

1. Download the plugin bundle
2. Place in your `.claude/plugins/` directory:
   ```bash
   mkdir -p ~/.claude/plugins
   cp -r writing-workflow ~/.claude/plugins/
   ```

3. Install Python dependencies:
   ```bash
   cd ~/.claude/plugins/writing-workflow
   pip install -r requirements.txt
   ```

### Configuration

#### 1. Customize Personas (Required)

Edit persona files to match your voice:

```bash
cd .claude-plugin/skills/writing/references/personas/
```

Update these files with your patterns:
- `educational.md` - Teaching voice
- `strategic.md` - Business insights voice
- `tutorial.md` - Technical instruction voice

See `personas/README.md` for customization guide.

#### 2. Configure Publishing (Optional)

For Google Docs publishing:

1. Set up n8n webhook (or alternative publishing endpoint)
2. Configure webhook URL in skill settings
3. Test with sample content

See `skills/publishing/google-docs-publisher/SKILL.md` for details.

#### 3. Customize Templates (Optional)

Edit template files to match your content structure:

```bash
cd .claude-plugin/skills/writing/references/templates/
```

Available templates:
- `substack-educational.md`
- `linkedin-post.md`
- `email-template.md`
- And more...

## Usage

### Quick Start

Generate an educational article:

```bash
QWRITE: "Write educational article explaining RAG systems, 1500 words, Substack"
```

### Multi-Platform Content

Create content for multiple platforms:

```bash
QWRITE: "Announce new product feature for LinkedIn, Twitter, and Email"
```

### Strategic Content

Write business insights:

```bash
QWRITE: "Write strategic analysis of AI coding agents market positioning, 2000 words"
```

### Generate Infographic

Extract framework and create visual:

```bash
QINFOGRAPHIC: Create infographic from article-file.md
```

### Generate PowerPoint Carousel

Create LinkedIn carousel:

```bash
QPPT: Generate LinkedIn carousel from article-file.md
```

## Commands

### QWRITE

Multi-platform content creation with quality scoring.

**Inputs**:
- Topic/request
- Platform (Substack, LinkedIn, Twitter, Email, Proposal)
- Content type (Educational, Strategic, Tutorial)
- Length target (optional)

**Outputs**:
- Publication-ready markdown
- Quality score report
- Platform-specific versions
- Visual content (articles only)
- Google Docs URL (if configured)

### QINFOGRAPHIC

Transform article frameworks into HTML infographics.

**Inputs**:
- Article markdown file
- Framework type (optional: auto-detected)

**Outputs**:
- HTML infographic file
- Preview image
- Diversity report

### QVISUAL

Generate hero images and diagrams from articles.

**Inputs**:
- Article markdown file

**Outputs**:
- Hero image PNG
- Diagram PNGs (if detected)
- Opportunity analysis

### QPPT

Generate PowerPoint carousels for LinkedIn.

**Inputs**:
- Article markdown file
- Brand guidelines (optional)

**Outputs**:
- PowerPoint PPTX file
- Slide preview images

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Agent                            │
│  (Workflow coordination, token budgeting, quality gates)         │
└───────────────────┬─────────────────────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
┌──────────────┐        ┌─────────────────┐
│ Research     │        │ Portfolio RAG    │
│ Agent        │        │ (Voice Retrieval)│
└──────┬───────┘        └────────┬─────────┘
       │                         │
       ▼                         ▼
┌──────────────────────────┐
│ Writer Agent              │
│ (Persona + Template)      │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Editorial Agent           │
│ (5 Metrics, Max 3 passes) │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Platform Transform        │
│ (Parallel transforms)     │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Polish Agent              │
│ (Links, Visuals, Publish) │
└──────────────────────────┘
```

## Quality Framework

### 5 Metrics (0-100 scale)

1. **Groundedness** (90-100 target)
   - Claims supported by Tier-1 sources
   - Direct citations with links
   - Verifiable claims

2. **Relevance** (90-100 target)
   - Every paragraph addresses core question
   - No unnecessary tangents
   - Clear value proposition

3. **Readability** (90-100 target)
   - Hemingway grade ≤8 (general audience)
   - Scannable headers
   - Clear structure

4. **Voice Consistency** (90-100 target)
   - Matches persona patterns
   - No AI tells
   - Authentic tone

5. **Originality** (90-100 target)
   - Unique insights
   - Specific examples
   - Fresh perspective

**Target**: ≥85/100 average, minimum 80/100 per metric

### Iteration Policy

- **Max 3 passes** (diminishing returns)
- **Stop when**: ≥85/100 or max passes reached
- **Priority levels**: P0 (blocking), P1 (recommended), P2 (optional)

## Platform Requirements

### Substack
- **Length**: 800-3000 words (topic-dependent)
- **Opening**: BLUF (Bottom Line Up Front)
- **Structure**: Scannable headers, white space
- **CTA**: Subscribe at bottom only

### LinkedIn
- **Hook**: First 25 words (before "see more")
- **Length**: 1900-2000 words for articles
- **Tone**: Professional conversational
- **CTA**: Comment prompt

### Twitter/BlueSky
- **Optimal**: 40-80 characters
- **Max**: 280 characters
- **Hashtags**: 1-2 max
- **Tone**: Conversational

### Email
- **Subject**: <50 characters, compelling
- **Body**: Bullet points, single CTA
- **Length**: <300 words
- **Tone**: Conversational but purposeful

### Proposal
- **Opening**: Executive summary first page
- **Structure**: Data-driven, formal sections
- **Evidence**: Required for all claims
- **Length**: 5-15 pages

## Story Point Estimation

- **Quick social post**: 0.5-1 SP
- **Standard article**: 2-3 SP
- **Deep dive article**: 3-5 SP
- **Multi-platform content**: 5-8 SP
- **Proposal/strategic plan**: 8-13 SP

## Customization Guide

### 1. Voice Personalization

Study 5-10 of your best pieces and extract patterns:

1. **Sentence structure**: Length, complexity, rhythm
2. **Vocabulary**: Technical vs accessible, formal vs casual
3. **Transitions**: How you connect ideas
4. **Examples**: Types of analogies and stories

Document in `personas/*.md` files.

### 2. Template Customization

Adapt templates to your content structure:

1. Analyze successful content structure
2. Extract reusable patterns
3. Update template files
4. Test with new content

### 3. Brand Guidelines

For visual content:

1. Define color palette
2. Specify typography
3. Set layout preferences
4. Document in `references/` directories

## Troubleshooting

### Voice Doesn't Match

1. Run voice validator: `python tools/voice-validator.py content.md --persona educational`
2. Check flagged phrases
3. Update persona files with your patterns
4. Re-generate content

### Links Breaking

1. All links automatically validated (HTTP 200)
2. Check console output for broken link reports
3. Fix source links before re-running polish phase

### Quality Score Low

1. Review quality report output
2. Focus on P0 and P1 issues first
3. Check source tier quality
4. Verify persona match
5. Re-run editorial pass

### Token Budget Exceeded

1. Review token usage breakdown
2. Reduce research scope if needed
3. Simplify platform transform count
4. Optimize editorial passes (max 3)

## Contributing

Contributions welcome! Please:

1. Follow existing code style
2. Add tests for new tools
3. Update documentation
4. Submit PR with clear description

## License

MIT License - See LICENSE file for details

## Support

- **Documentation**: See `skills/*/SKILL.md` for detailed skill docs
- **Examples**: Check `examples/` directory
- **Issues**: File issues on GitHub
- **Community**: Join Claude Code community discussions

## Acknowledgments

This plugin builds on:
- Anthropic Claude Code framework
- Multi-agent orchestration patterns
- Quality-driven content workflows
- Platform-specific transformation strategies

---

**Version**: 1.0.0
**Last Updated**: 2026-01-28
**Compatibility**: Claude Code 1.0+
