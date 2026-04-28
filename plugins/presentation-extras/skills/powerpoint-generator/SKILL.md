# PowerPoint Generator Skill

**Domain**: Presentation
**Skill**: powerpoint-generator
**Version**: 1.0.0

## Purpose

Generate professional PowerPoint presentations (.pptx) and matching handouts from markdown training content, applying Sparkry brand guidelines and Travis's "minimal text on slides" philosophy.

## Philosophy

**Slides are reinforcement, not documentation.**

- Maximum 1 key point per slide
- Large text and numbers (headlines 48pt+, statistics 72pt+)
- Visuals over text (diagrams, icons, charts)
- Navy backgrounds with Orange accents
- No "Docutations" - slide reinforces what speaker says, doesn't duplicate it

**Speaker notes contain the full script.**

**Handouts provide reference materials** - frameworks, statistics, action items.

## Tools

### 1. generate-presentation.py

**Purpose**: Convert markdown training content to branded .pptx file

**Inputs**:
- Markdown file path (with slide structure: `### SLIDE N: Title`)
- Output .pptx file path
- Brand config (optional, defaults to Sparkry guidelines)

**Outputs**:
- .pptx file with branded slides and embedded speaker notes

**Usage**:
```bash
python tools/generate-presentation.py \
  --input training/session_01_ai_fundamentals_business_value.md \
  --output output/session_01.pptx
```

**Slide Parsing Rules**:
- `# Session Title` → Title slide
- `## Section: Name` → Section header slide
- `### SLIDE N: Title` → Content slide
- Bullet points → Minimal text (max 3 bullets, < 10 words each)
- `**SPEAKER NOTES:**` section → Embedded as speaker notes
- Numbers/statistics → Large text display (72pt)

**Brand Application**:
- Master template: Sparkry Navy (#171d28) backgrounds
- Accent color: Sparkry Orange (#ff6b35) for highlights
- Typography: Inter for body, Crimson Text for hero headlines
- Layout: Generous white space, asymmetric layouts

### 2. create-handout.py

**Purpose**: Generate 1-page PDF handout with key frameworks and takeaways

**Inputs**:
- Markdown file path
- Output PDF file path

**Outputs**:
- PDF handout with frameworks, statistics, action items

**Usage**:
```bash
python tools/create-handout.py \
  --input training/session_01_ai_fundamentals_business_value.md \
  --output output/session_01_handout.pdf
```

**Extraction Rules**:
- Extract frameworks from `**Framework:**` sections
- Extract statistics from slides (numbers with context)
- Extract action items from `**ACTION ITEMS:**` sections
- Format as 1-page reference sheet

### 3. install-deps.sh

**Purpose**: Install required Python dependencies

**Usage**:
```bash
bash tools/install-deps.sh
```

**Dependencies**:
- python-pptx (PowerPoint generation)
- reportlab (PDF generation)
- Pillow (image handling)

## References

### Brand Guidelines
- `/brand-and-style/03-color-system.md` - Sparkry Orange, Navy, semantic colors
- `/brand-and-style/04-typography.md` - Inter, Crimson Text, type scales
- `/brand-and-style/11-voice-messaging.md` - Voice and messaging guidelines

### python-pptx Documentation
- Slide layouts: https://python-pptx.readthedocs.io/en/latest/user/slides.html
- Text formatting: https://python-pptx.readthedocs.io/en/latest/user/text.html
- Colors and themes: https://python-pptx.readthedocs.io/en/latest/user/understanding-shapes.html

## Examples

### Input Markdown Structure

```markdown
# Session 1: AI Fundamentals & Business Value

## Section: The Reality Check

### SLIDE 3: Current State of AI Adoption

**What's on the slide:**
- 78% of organizations use AI
- 65% use generative AI
- But 95% show no P&L impact

**SPEAKER NOTES:**

"Let's start with a reality check. If you read the headlines, AI is everywhere...

[Full script here - 2-3 minutes of content]
```

### Output Slide Design

**Slide 3 Layout:**
```
┌─────────────────────────────────────┐
│  [Navy background #171d28]          │
│                                      │
│  78%  of orgs use AI                │
│  [Orange #ff6b35, 72pt]             │
│                                      │
│  65%  use generative AI             │
│  [Orange, 72pt]                     │
│                                      │
│  95%  show no P&L impact            │
│  [White, 72pt, emphasized]          │
│                                      │
└─────────────────────────────────────┘

Speaker Notes: [Full 2-3 minute script embedded]
```

### Output Handout Design

**Session 1 Handout (1 page):**
```
Session 1: AI Fundamentals & Business Value

KEY FRAMEWORKS
─────────────────────────────────────────
Gartner 3-Tier ROI Framework
  • Quick Wins (0-12 months): Efficiency gains
  • Differentiating (1-2 years): Competitive advantage
  • Transformational (2+ years): Business model change

70/20/10 Rule for AI Success
  • 70% People & Process
  • 20% Technology & Infrastructure
  • 10% Algorithms & Models

KEY STATISTICS
─────────────────────────────────────────
• 78% of organizations use AI (2024)
• 95% of GenAI has no P&L impact
• 42% abandoned most AI initiatives in 2025

ACTION ITEMS
─────────────────────────────────────────
□ Audit current AI initiatives for measurable ROI
□ Define success metrics before starting pilots
□ Identify one Quick Win opportunity
```

## Usage Workflow

### Generating a Single Session

```bash
# 1. Install dependencies (first time only)
bash .claude/skills/presentation/powerpoint-generator/tools/install-deps.sh

# 2. Generate PowerPoint
python .claude/skills/presentation/powerpoint-generator/tools/generate-presentation.py \
  --input training/session_01_ai_fundamentals_business_value.md \
  --output output/session_01_ai_fundamentals_business_value.pptx

# 3. Generate handout
python .claude/skills/presentation/powerpoint-generator/tools/create-handout.py \
  --input training/session_01_ai_fundamentals_business_value.md \
  --output output/session_01_handout.pdf
```

### Batch Processing All Sessions

```bash
# Generate all 5 training sessions
for i in {1..5}; do
  python tools/generate-presentation.py \
    --input training/session_0${i}_*.md \
    --output output/session_0${i}.pptx

  python tools/create-handout.py \
    --input training/session_0${i}_*.md \
    --output output/session_0${i}_handout.pdf
done
```

## Quality Standards

### Slides Must:
- ✅ Use Sparkry brand colors (Navy, Orange, white)
- ✅ Apply Inter typography (body) and Crimson Text (headlines, sparingly)
- ✅ Display maximum 1 key point per slide
- ✅ Use large text (48pt+ headlines, 72pt+ numbers)
- ✅ Include full speaker notes embedded
- ✅ Open successfully in PowerPoint and Keynote

### Handouts Must:
- ✅ Fit on 1 page (front and back if necessary)
- ✅ Extract key frameworks with visual hierarchy
- ✅ List essential statistics with context
- ✅ Provide actionable takeaways
- ✅ Use consistent formatting across all sessions

### Voice Must:
- ✅ Maintain Travis's direct, results-focused tone
- ✅ Use numbers over adjectives
- ✅ Avoid forbidden phrases ("leverage synergies", "cutting-edge", etc.)
- ✅ Include credibility anchors (Amazon/Microsoft/GSK examples)

## Constraints

- Slide text: Maximum 3 bullet points, < 10 words each
- Headline text: 48pt minimum (Inter Bold)
- Statistics: 72pt minimum (Inter Bold, Orange)
- Speaker notes: No length limit (full script)
- Handout: 1 page maximum per session
- File format: .pptx (PowerPoint 2016+), PDF/A for handouts

## Story Point Estimates

- Generate single session presentation: 3 SP
- Generate single session handout: 1 SP
- Batch process all 5 sessions: 5 SP
- Update brand templates: 2 SP
- Add new slide layout variant: 1 SP

## Success Metrics

**Measurable:**
- Presentation opens without errors in PowerPoint/Keynote
- Speaker notes readable and formatted correctly
- Handout fits on 1 page with all key content
- Brand colors match specifications (Navy #171d28, Orange #ff6b35)

**Qualitative:**
- Slides follow "minimal text" philosophy (Travis approval)
- Voice maintains authoritative but accessible tone
- Handouts provide useful reference without duplicating slides
- Presentation flows logically for 1-hour training session

## Version History

**1.0.0** (2025-01-XX)
- Initial skill creation
- Support for AI training session markdown format
- Sparkry brand application
- PDF handout generation
