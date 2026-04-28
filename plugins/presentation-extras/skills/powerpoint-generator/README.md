# PowerPoint Generator Skill - Quick Start

## What Was Created

✅ **PowerPoint Generation Skill** - Complete skill for creating branded presentations from markdown
✅ **Session 1 Presentation** - 15 slides with Sparkry branding and full speaker notes
✅ **Session 1 Handout** - 1-page PDF reference with frameworks and key statistics

## Files Generated

```
output/
├── session_01_ai_fundamentals_business_value.pptx  (72 KB, 15 slides)
└── session_01_handout.pdf  (2.3 KB, 1 page)
```

## Quick Usage

### Generate Presentations

```bash
# Session 1 (already generated)
python3 .claude/skills/presentation/powerpoint-generator/tools/generate-presentation.py \
  --input training/session_01_ai_fundamentals_business_value.md \
  --output output/session_01.pptx

# For future sessions (2-5)
python3 .claude/skills/presentation/powerpoint-generator/tools/generate-presentation.py \
  --input training/session_02_*.md \
  --output output/session_02.pptx
```

### Generate Handouts

```bash
python3 .claude/skills/presentation/powerpoint-generator/tools/create-handout.py \
  --input training/session_01_ai_fundamentals_business_value.md \
  --output output/session_01_handout.pdf
```

## Presentation Features

**Branding:**
- Sparkry Orange (#ff6b35) and Navy (#171d28) colors
- Inter typography for body text
- Professional, minimal design

**Slide Design:**
- Maximum 1 key point per slide
- Large text (48pt+ headlines, 72pt+ numbers)
- Statistics displayed prominently on Navy backgrounds
- Section headers with Orange accents

**Speaker Notes:**
- Full script embedded in each slide
- Travis's voice maintained (direct, results-focused)
- Amazon/Microsoft/GSK credibility anchors included

## Handout Features

- 1-page PDF format
- Key frameworks extracted and formatted
- Essential statistics with context
- Sparkry brand colors (Orange header bar, Navy accents)

## Next Steps

To generate remaining sessions (2-5):

1. Create markdown files for Sessions 2-5 in `/training/` directory
2. Use same format as Session 1 (### SLIDE N: Title, **SPEAKER NOTES:** sections)
3. Run generation scripts for each session

## Dependencies

All dependencies installed:
- python-pptx (1.0.2) - PowerPoint generation
- reportlab (4.4.4) - PDF generation
- Pillow (11.3.0) - Image handling

## Session 1 Details

**Title:** AI 101 Training Series - Session 1: AI Fundamentals & Business Value

**Slides:**
1. Title slide
2. Why We're Here
3. The Reality Check (statistics slide)
4. Why Most AI Fails
5. What Actually Works
6. Quick Wins Framework
7. How to Define Success
8. Success vs Failure Metrics
9. Pharma-Specific Context
10. Regulatory Considerations
11. The 70/20/10 Rule
12. Common Pitfalls
13. Your Action Plan
14. Questions & Discussion

**Duration:** 1 hour (with buffer for pharma-specific examples)

**Handout Contains:**
- Gartner 3-Tier ROI Framework
- 70/20/10 Rule for AI Success
- 6 key statistics (adoption rates, failure rates, market growth)

## Validation Checklist

✅ Presentation opens successfully (tested)
✅ 15 slides generated (1 title + 14 content)
✅ Speaker notes embedded in all slides
✅ Sparkry brand colors applied correctly
✅ Handout fits on 1 page
✅ Minimal text philosophy maintained
✅ Navy backgrounds for statistics slides
✅ Orange accents throughout
