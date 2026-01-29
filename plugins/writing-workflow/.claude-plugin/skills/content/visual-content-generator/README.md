# Visual Content Generator Skill

**Version**: 1.0.0
**Status**: ✅ Operational
**Trigger**: `QVISUAL`

## Overview

Generates professional hero images and framework diagrams from article content using HTML-to-image conversion with Playwright. Automatically detects visualizable content (ASCII diagrams, frameworks) and produces brand-compliant PNG images.

## Quick Start

### Installation

```bash
# Install Python dependencies
pip install playwright Pillow

# Install Playwright browser (Chromium, ~200MB)
playwright install chromium
```

### Usage Examples

**1. Detect visual opportunities in article:**
```bash
python3 tools/detect-visual-opportunities.py --file content/articles/week-02/article.md
```

**2. Generate hero image:**
```bash
python3 tools/generate-hero-image.py --file content/articles/week-02/article.md
```

**3. Convert ASCII art to diagram:**
```bash
python3 tools/convert-ascii-to-visual.py \
  --ascii-input "$(cat diagram.txt)" \
  --output diagram.png \
  --title "Permission Architecture"
```

**4. Via QVISUAL shortcut:**
```bash
QVISUAL: Generate visuals for content/articles/week-02/article.md
```

## Features

### 1. Hero Image Generation
- **Input**: Article markdown (H1 + first paragraph)
- **Output**: 1200×630px PNG (OpenGraph standard)
- **Styling**: Sparkry brand colors, Poppins/Inter fonts
- **Render time**: ~2 seconds

### 2. ASCII Diagram Conversion
- **Detects**: Box-drawing characters (┌─┐│└┘), arrows (→←↑↓), ASCII borders
- **Output**: 1200×800px PNG
- **Styling**: Professional layout with Sparkry branding
- **Render time**: ~1.5 seconds

### 3. Framework Visualization
- **Detects**: Numbered lists (3+ items), section headers with framework keywords
- **Output**: Structured diagram with visual hierarchy
- **Future**: Automatic generation from detected frameworks

### 4. Automatic Detection
- **Scans**: Articles for hero opportunities, ASCII art, frameworks
- **Output**: JSON manifest with all opportunities
- **Performance**: <1 second for 3000-word article

## Tool Reference

### detect-visual-opportunities.py
Scan article for visualizable content.

**Arguments**:
- `--file PATH` (required): Article markdown path
- `--suggest-only`: Only suggest, don't generate

**Output**: JSON with opportunities array

**Example**:
```bash
python3 tools/detect-visual-opportunities.py --file article.md
```

### generate-hero-image.py
Create branded hero image from article.

**Arguments**:
- `--file PATH` (required): Article markdown path
- `--output PATH` (optional): PNG output path (auto-generated if omitted)
- `--style {bold,minimal,gradient}` (default: gradient)
- `--width INT` (default: 1200)
- `--height INT` (default: 630)

**Output**: JSON with visual_path, title, subtitle, render_time

**Example**:
```bash
python3 tools/generate-hero-image.py \
  --file article.md \
  --style gradient \
  --output hero.png
```

### convert-ascii-to-visual.py
Transform ASCII art to professional diagram.

**Arguments**:
- `--ascii-input TEXT` (required): ASCII art content
- `--output PATH` (required): PNG output path
- `--style {framework,flowchart,tree}` (default: framework)
- `--title TEXT` (optional): Diagram title

**Output**: JSON with visual_path, detected_type, nodes, connections

**Example**:
```bash
python3 tools/convert-ascii-to-visual.py \
  --ascii-input "┌─────┐
│ Box │
└─────┘" \
  --output diagram.png \
  --title "Simple Box"
```

### render-html-to-image.py
Core rendering engine (HTML → PNG via Playwright).

**Arguments**:
- `--html-file PATH` (required): HTML template path
- `--output PATH` (required): PNG output path
- `--width INT` (default: 1200)
- `--height INT` (default: 630)
- `--scale FLOAT` (default: 2.0, retina DPI)
- `--variables JSON` (optional): Template variable substitution

**Output**: JSON with success, output_path, render_time, size

**Example**:
```bash
python3 tools/render-html-to-image.py \
  --html-file template.html \
  --output image.png \
  --width 1200 \
  --height 630
```

## Integration with QWRITE

The visual content generator is automatically invoked during the **Polish Phase** of QWRITE workflows for articles (not social posts).

### Workflow

1. **Drafting Phase**: Writer includes ASCII art for frameworks
2. **Editorial Phase**: Quality review (ASCII art preserved)
3. **Polish Phase**:
   - Link validation
   - **Visual content generation** ← New!
     - Detect opportunities
     - Generate hero image (always)
     - Convert ASCII diagrams (if present)
     - Generate framework visuals (if detected)
   - Google Docs publishing
4. **Output**: Article + visuals in `content/visuals/week-##/`

### Example Output

```markdown
### Visual Content
- **Hero Image**: content/visuals/week-02/W02-THU-article-hero.png
- **Diagrams**:
  - content/visuals/week-02/W02-THU-article-diagram-1.png (ASCII flowchart, 194KB)
  - content/visuals/week-02/W02-THU-article-diagram-2.png (Framework: Three Pillars, 218KB)
- **Opportunities Detected**: 3 (1 hero, 2 diagrams)
- **Generation Time**: 10.9 seconds
- **Total Size**: 699KB
```

## Directory Structure

```
.claude/skills/content/visual-content-generator/
├── SKILL.md                    # Skill definition
├── README.md                   # This file
├── TEST-ARTICLE.md             # Test article with ASCII art
├── tools/                      # Python tools (executable)
│   ├── detect-visual-opportunities.py
│   ├── generate-hero-image.py
│   ├── convert-ascii-to-visual.py
│   └── render-html-to-image.py
├── references/
│   ├── templates/              # HTML templates
│   │   ├── hero-image.html
│   │   └── framework-diagram.html
│   ├── examples/
│   │   └── ascii-patterns.md   # Detection patterns reference
│   └── brand-guidelines.json   # Symlink to ppt-carousel brand guidelines

Generated outputs:
content/visuals/
├── week-01/
│   ├── W01-TUE-article-hero.png
│   ├── W01-TUE-article-diagram-1.png
│   └── ...
├── week-02/
│   └── ...
```

## ASCII Art Patterns Detected

### Box-Drawing Characters
```
┌─────────────┐
│   Process   │
└─────────────┘
```

### ASCII Borders
```
+-------------------+
|   Component A     |
+-------------------+
```

### Tree Structures
```
Root
├── Branch 1
│   ├── Leaf 1
│   └── Leaf 2
└── Branch 2
```

### Flowcharts
```
[Start] → [Process] → [Decision]
                         ↓
                      [Action]
```

## HTML Templates

### Hero Image Template
**File**: `references/templates/hero-image.html`

**Variables**:
- `{{ title }}`: Article H1 title
- `{{ subtitle }}`: First paragraph or hook

**Styling**:
- 1200×630px (OpenGraph standard)
- Gradient background (Sparkry navy → electric blue)
- Poppins Bold (title), Inter Regular (subtitle)
- White text, high contrast

### Framework Diagram Template
**File**: `references/templates/framework-diagram.html`

**Variables**:
- `{{ title }}`: Diagram title
- `{{ diagram_html }}`: Injected diagram structure

**Styling**:
- 1200×800px (4:3 ratio)
- White background
- Sparkry color palette (navy, orange, blue)
- Professional box/arrow styling

## Performance Metrics

| Operation | Target | Actual (Test) |
|-----------|--------|---------------|
| Detect opportunities | <1s | ~0.5s |
| Generate hero image | <3s | ~2.2s |
| Convert ASCII diagram | <5s | ~1.6s |
| Full article (hero + 2 diagrams) | <10s | ~5.4s |

**File sizes**:
- Hero images: 200-400KB (target <500KB)
- Diagrams: 150-350KB (target <500KB)
- Total per article: <2MB

## Brand Compliance

All visuals use Sparkry brand guidelines:

- **Colors**:
  - Primary: Orange (#ff6b35)
  - Navy: #171d28
  - Electric Blue: #0ea5e9
  - White: #ffffff

- **Typography**:
  - Headings: Poppins (700, 800 weight)
  - Body: Inter (400, 500 weight)
  - Loaded from Google Fonts CDN

- **Logo**: "Sparkry.AI" in bottom-right corner

## Troubleshooting

### Issue: Playwright not installed
```bash
pip install playwright
playwright install chromium
```

### Issue: Screenshots show broken fonts
- Fonts load from Google Fonts CDN (internet required)
- Check internet connection during generation

### Issue: Playwright timeout
- Increase timeout in `render-html-to-image.py`: `page.wait_for_timeout(2000)`
- Or run with visible browser: `browser = p.chromium.launch(headless=False)`

### Issue: File size too large
- Reduce image dimensions
- Use PNG compression
- Target: <500KB per image

## Testing

### Run Detection Test
```bash
cd .claude/skills/content/visual-content-generator
python3 tools/detect-visual-opportunities.py --file TEST-ARTICLE.md
```

**Expected output**: 3 opportunities (1 hero, 2 ASCII diagrams)

### Run Hero Image Test
```bash
python3 tools/generate-hero-image.py --file TEST-ARTICLE.md --output test-hero.png
```

**Expected output**: `test-hero.png` (1200×630, ~200-400KB)

### Run ASCII Conversion Test
```bash
python3 tools/convert-ascii-to-visual.py \
  --ascii-input "[Start] → [Process] → [End]" \
  --output test-diagram.png \
  --title "Test Flow"
```

**Expected output**: `test-diagram.png` (1200×800, ~150-300KB)

### Verify Images
```bash
ls -lh test-*.png
```

## Story Point Estimates

- **Generate hero image**: 0.1 SP
- **Convert ASCII diagram**: 0.2 SP
- **Full article processing (hero + 2-3 diagrams)**: 0.5 SP
- **Batch processing (5 articles)**: 1 SP

## Future Enhancements

### Phase 2
- Advanced ASCII parsing (complex flowcharts, nested trees)
- Framework auto-generation from numbered lists
- Interactive diagram editing
- Batch processing optimization

### Phase 3
- Animation support (subtle transitions)
- Video generation from articles
- Social media size optimization (Instagram, Twitter)
- Analytics integration (track visual engagement)

## Dependencies

**Python**:
- playwright (Chromium headless browser)
- Pillow (image processing)

**System**:
- Python 3.8+
- 250MB disk space (Playwright Chromium)
- Internet connection (Google Fonts CDN)

## Related Skills

- **ppt-carousel**: Shares HTML-to-image approach and brand guidelines
- **writing**: Integrates into QWRITE polish phase
- **google-docs-publisher**: Sequential in polish phase

## Support

**Issues**: Report in `.claude/skills/content/visual-content-generator/` directory
**Skill Version**: 1.0.0
**Last Updated**: 2025-11-04

## Success Criteria

### MVP ✅
- [x] Generate hero images from article metadata
- [x] Detect ASCII art in articles
- [x] Convert simple ASCII diagrams to visuals
- [x] Integrate with QWRITE polish phase
- [x] Manual invocation via QVISUAL

### Phase 2 (Future)
- [ ] Advanced ASCII parsing
- [ ] Framework auto-generation
- [ ] Batch processing
- [ ] Performance optimization

### Phase 3 (Future)
- [ ] Animation support
- [ ] Video generation
- [ ] Analytics integration
