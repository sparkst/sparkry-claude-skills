# Infographic Generator Skill

Transform Substack articles with frameworks (3-10 steps, pillars, layers) into visually compelling single-page HTML infographics.

## Quick Start

### Basic Usage

```bash
QINFOGRAPHIC: Create infographic from https://substack.com/article/5-pillars-ai
```

### With Options

```bash
QINFOGRAPHIC: Create infographic from article.txt
- Channel: linkedin_carousel
- Brand: Primary #1a1a2e, Accent #0f3460
- Emphasis: Highlight Pillar 3
```

## What This Skill Does

1. **Extracts frameworks** from articles (3-10 element structures)
2. **Validates content** to prevent hallucinations
3. **Generates creative visuals** avoiding PowerPoint aesthetics
4. **Produces HTML** with gradients, shadows, rich typography
5. **Ensures accessibility** (WCAG AA contrast, semantic HTML)
6. **Tracks diversity** to avoid repetitive designs

## 10-Agent Pipeline

```
Article → Extract Framework → Validate → Select Pattern →
Generate Creative Profile → Compress Copy → Design Brief →
Render HTML → QA Check → Package Output
```

**Quality Gates**: 3 blocking gates ensure accuracy
**Token Budget**: <25K per run (target: 15-20K)
**Latency**: <3 minutes end-to-end

## Tools

### Core Tools (8 Python scripts)

1. **framework-extractor.py**: Detect frameworks (steps, pillars, layers)
2. **framework-validator.py**: Validate against article (prevent hallucinations)
3. **pattern-selector.py**: Choose infographic pattern (timeline, process, pillars)
4. **creativity-orchestrator.py**: Generate visual metaphor + icon system
5. **copy-compressor.py**: Compress to infographic constraints (10/7/15 word limits)
6. **html-generator.py**: Render sophisticated HTML ⭐ CREATIVE CORE
7. **content-qa.py**: Validate content alignment + accessibility
8. **diversity-tracker.py**: Track creative profiles to avoid repetition

### References (5 files)

- **visual-metaphors.json**: Maps framework types → metaphor options
- **headline-patterns.json**: Title templates to rotate
- **layout-templates.json**: Structural patterns (timeline, pillars, etc.)
- **icon-mappings.json**: Concept keywords → Font Awesome icons
- **best-practices.md**: Design principles, accessibility guidelines

## Requirements

### Input Article Must Have

- **Framework**: 3-10 element structure (steps, pillars, layers, stages, loops, principles)
- **Clear labels**: Numbered or named elements
- **Supporting content**: At least 1-2 sentences per element
- **Length**: Minimum 500 characters

### Examples of Good Frameworks

✅ "The 5 Pillars of AI Transformation"
✅ "7 Steps to Product-Market Fit"
✅ "4 Layers of Data Infrastructure"
✅ "3 Stages of Team Growth"

❌ Not suitable:
- Generic listicles without clear structure
- More than 10 elements (too complex)
- Fewer than 3 elements (too simple)

## Output

### Files Generated

1. **HTML file**: Body content only (for Lovable integration)
   - Google Fonts (Poppins, Inter)
   - Font Awesome icons
   - Responsive CSS (mobile-first)
   - Rich visual elements (gradients, shadows, custom shapes)

2. **JSON spec**: Complete metadata
   - Framework data
   - Creative profile
   - Design brief
   - QA results

### HTML Features

✨ **Rich Visuals**:
- Gradient backgrounds
- Box shadows for depth
- Custom SVG shapes
- Icon integration
- Decorative motifs

✨ **Typography**:
- Multiple font weights (300, 400, 600, 700)
- Clear hierarchy (3.5rem title → 1rem body)
- Generous line spacing

✨ **Accessibility**:
- WCAG AA contrast (4.5:1 minimum)
- Semantic HTML (h1, h2, ul, etc.)
- Icon + text pairing
- Mobile-responsive

## Creative Excellence

### What Makes This Different from PowerPoint

❌ **PowerPoint**:
- Simple rectangles with text
- Stock templates
- Flat colors
- Generic layouts

✅ **This Skill**:
- Custom shapes with clip-paths
- Gradient overlays
- Strategic shadows
- Unique compositions per metaphor
- Creative asymmetry where appropriate

### Visual Metaphors

Framework types map to visual metaphors:

- **Steps** → roadmap, ladder, mountain_climb, staircase
- **Pillars** → columns, control_panel, foundation_blocks
- **Layers** → stacked_blocks, pyramid, elevation_chart
- **Loops** → orbit_model, circular_flow, feedback_cycle
- **Stages** → timeline_path, evolution_chart, maturity_model

## Diversity Tracking

### How It Works

Each infographic generates a **fingerprint**:
```
pattern+visual_metaphor+icon_system+shape_language+headline_pattern
```

Stored in: `~/.claude/data/infographic-history/{user_id}.json`

### Diversity Rules

1. **No identical pattern+metaphor** in last 5 infographics
2. **No headline pattern** used >2x in row
3. **Rotate icon systems** across infographics
4. **Vary shape language** every 2-3 infographics

**Novelty Score**: 0-1 (target: >0.6)
- 1.0 = Completely novel
- 0.6 = Good variation
- 0.3 = Warning (too repetitive)
- 0.0 = Identical to recent infographic

## Quality Gates

### Blocking Gates (Hard Fail)

1. **Framework Validation** (Agent 3):
   - Any element not backed by article text
   - Confidence score < 0.7

2. **Copy Compression** (Agent 6):
   - Missing framework element
   - Length limit violations (title>10w, heading>7w, bullet>15w)

3. **Content QA** (Agent 9):
   - Hallucinations detected
   - Missing elements in HTML
   - Content alignment < 0.8

### Warning Gates (Soft Fail)

1. **Article Ingestion**: Very long content
2. **Framework Detection**: Multiple candidates
3. **Creativity**: Low novelty score (<0.3)

## Troubleshooting

### "No framework detected"

**Cause**: Article doesn't have clear 3-10 element structure

**Solutions**:
- Provide framework hint: `--framework-hint "5 pillars"`
- Check article has numbered sections
- Ensure elements are explicitly labeled

### "Validation failed"

**Cause**: Extracted elements not supported by article text

**Solutions**:
- Review article structure
- Check element labels match article text
- Ensure summaries don't introduce new claims

### "QA hallucination detected"

**Cause**: Generated infographic contains fabricated content

**Solutions**:
- This is a hard fail (accuracy critical)
- Review copy compression output
- Check if article has ambiguous content

### "Low novelty score"

**Cause**: Creative profile too similar to recent infographics

**Solutions**:
- Request style variant: `QINFOGRAPHIC: New variant with different metaphor`
- Clears after 5 new infographics
- Not a blocker (infographic still generated)

## Examples

### Example 1: LinkedIn Carousel

```bash
QINFOGRAPHIC: Create infographic from https://substack.com/article/product-stages
- Channel: linkedin_carousel
- Brand: Primary #0066cc, Accent #ff6600

# Output:
# - Square aspect ratio (1:1)
# - 7 panels (hero + 5 stages + CTA)
# - Medium content density
# - Optimized for LinkedIn feed
```

### Example 2: Blog Hero

```bash
QINFOGRAPHIC: Create infographic from frameworks-article.txt
- Channel: blog_hero
- Tone: professional

# Output:
# - Wide aspect ratio (16:9)
# - 6 panels (hero + 4 pillars + summary)
# - Low content density (complement article)
# - Matches blog design aesthetic
```

### Example 3: Style Variant

```bash
# After generating first infographic:
QINFOGRAPHIC: New variant of last infographic with different visual metaphor

# Reuses:
# - Framework extraction
# - Validation
# - Strategy
# - Copy compression

# Regenerates:
# - Creative profile (new metaphor)
# - HTML rendering
# - QA check

# Time: ~1 minute (vs. 3 minutes full pipeline)
```

## Integration

### With QWRITE

```bash
# Write article with framework
QWRITE: Write article about "5 Pillars of AI Governance"

# Generate infographic
QINFOGRAPHIC: Create infographic from last article

# Embed in article
[Infographic HTML embedded automatically]
```

### With Google Docs Publisher

```bash
# Generate infographic
QINFOGRAPHIC: Create infographic from article.txt

# Publish to Google Docs
QWRITE: Publish infographic to Google Docs
```

### With Lovable

HTML output is **body content only** (no `<html>`, `<head>` tags).

**To integrate**:
1. Copy HTML from output file
2. Paste into Lovable component
3. Infographic renders with full styling

## Testing Tools Independently

### Test Framework Extraction
```bash
python scripts/framework-extractor.py test-article.txt

# Optional: provide hint
python scripts/framework-extractor.py test-article.txt --framework-hint "5 pillars"
```

### Test HTML Generation
```bash
# Create minimal design brief
cat > test-brief.json << EOF
{
  "infographic_copy": {
    "title": "Test Framework",
    "subtitle": "A test infographic",
    "panels": [
      {
        "panel_id": "test_1",
        "heading": "Step 1: Test",
        "body_bullets": ["Bullet point one", "Bullet point two"],
        "highlight_stat": ""
      }
    ]
  },
  "creative_profile": {
    "visual_metaphor": "roadmap",
    "icon_system": "flat_duotone",
    "shape_language": "rounded_cards",
    "divider_style": "dotted_line",
    "accent_motif": "subtle_dots"
  },
  "style": {
    "colors": {
      "primary": "#1a1a2e",
      "accent": "#0f3460"
    }
  }
}
EOF

python scripts/html-generator.py test-brief.json --output test-infographic.html
```

### Test Diversity Tracking
```bash
# Log new profile
cat > test-profile.json << EOF
{
  "creative_profile": {
    "pattern": "vertical_process",
    "visual_metaphor": "roadmap",
    "icon_system": "flat_duotone",
    "shape_language": "rounded_cards",
    "headline_pattern": "[FRAMEWORK_NAME]: [OUTCOME]"
  }
}
EOF

python scripts/diversity-tracker.py log test_user test-profile.json

# Check diversity
python scripts/diversity-tracker.py check test_user test-profile.json --window 5
```

## Performance

### Typical Execution Times

- **Simple framework** (3-5 elements): 90-120 seconds
- **Standard framework** (6-8 elements): 120-180 seconds
- **Complex framework** (9-10 elements): 180-240 seconds
- **Style variant**: 30-60 seconds

### Token Usage

- **Average**: 15-18K tokens
- **Maximum**: 25K tokens (budget)
- **Largest consumers**: HTML Rendering (5K), Framework Extraction (3K), Copy Compression (3K)

## Story Points

- **Simple framework** (3-5 elements, standard pattern): 2 SP
- **Standard framework** (6-8 elements, creative metaphor): 3 SP
- **Complex framework** (9-10 elements, custom layout): 5 SP
- **Style variant** (reuse extraction, new visuals): 1 SP

## Future Enhancements (Out of Scope v1)

- Multi-language support
- Animated infographics (CSS animations)
- Interactive elements (hover states)
- PDF export
- Batch processing
- A/B testing variants
- Social media auto-sizing

---

**Version**: 1.0.0
**Documentation**: See `SKILL.md` for complete pipeline details
**Agent**: `.claude/agents/infographic-generator.md`
**Trigger**: `QINFOGRAPHIC`
