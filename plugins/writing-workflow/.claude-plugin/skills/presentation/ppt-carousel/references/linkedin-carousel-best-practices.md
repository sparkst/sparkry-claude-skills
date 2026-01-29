# LinkedIn Carousel Best Practices (2024-2025)

> **Purpose**: Evidence-based best practices for high-performing LinkedIn carousels
> **Load when**: Generating carousel slides, optimizing content, validating design

## Text Limits (Mobile-First Design)

### Word Counts
- **Title**: Max 8 words (1 line)
- **Body**: Max 20 words (2-3 lines)
- **Total per slide**: Max 30 words, 5 lines

**Why**: 70% of LinkedIn engagement happens on mobile. Long text becomes unreadable.

### Font Sizes (1080×1080 canvas)
- **Super headline**: 72px (hook slides)
- **Headline**: 48-56px (titles)
- **Subheadline**: 36-40px (subtitles)
- **Body**: 32-38px (content)
- **Small**: 24-28px (captions)
- **Label**: 16px (uppercase labels like "REAL EXAMPLE")

**Why**: Smaller fonts become illegible on mobile screens.

## Visual Hierarchy

### 60/40 Rule
- **Visual elements**: 30% (icons, shapes, whitespace)
- **Text**: 40%
- **Whitespace**: 30%

**Why**: Overcrowded slides get scrolled past. Whitespace = professionalism.

### Margins
- **Slide margins**: 80-100px on all sides
- **Text block spacing**: 40px between sections
- **Line height**: 1.4-1.5 for readability

**Why**: Content touching edges looks amateur and hard to read.

## Color Contrast

### WCAG Standards
- **AA (Minimum)**: 4.5:1 contrast ratio
- **AAA (Enhanced)**: 7:0:1 contrast ratio

**How to calculate**:
```python
# Use color-contrast-validator.py
python3 scripts/color-contrast-validator.py --background "#171d28"

# Output tells you white or black text
```

### Common Mistakes
- ❌ Black text on dark blue background
- ❌ White text on yellow background
- ❌ Gray text on gray background

**Fix**: Always use color-contrast-validator.py before finalizing design.

## Slide Structure (8-10 Slides Optimal)

### Slide 1: Hook
**Purpose**: Stop the scroll

**Format**:
- Icon (100px)
- Title (1 line, <8 words)
- Subtitle (1-2 lines, <15 words)

**Examples**:
- "Your team is split on AI adoption"
- "You're shipping features. Not learning."
- "AI adoption theater vs. real infrastructure"

### Slides 2-4: Framework/Value
**Purpose**: Deliver core insight

**Format**:
- Icon (80px)
- Title (framework name)
- 3-5 bullets (max 15 words each)

**Progressive disclosure**:
- Slide 2: Layer 1 of framework
- Slide 3: Layer 2 of framework
- Slide 4: Layer 3 of framework

### Slides 5-6: Examples
**Purpose**: Proof points

**Format**:
- Label: "REAL EXAMPLE" (16px uppercase)
- Icon (60px, top-right)
- Story (2-3 sentences, <30 words)

**Pattern**: "One team did X. Result: Y."

### Slide 7: Diagnostic
**Purpose**: Engagement (make reader think)

**Format**:
- Question or "If/then" statement
- Center-aligned
- No icon (focus on words)

**Examples**:
- "If doubling AI usage would break your system, you don't have adoption infrastructure."
- "What's breaking in your AI rollout?"

### Slide 8: CTA
**Purpose**: Next action

**Format**:
- Question (related to post)
- CTA: "Drop it in comments ↓"
- Optional: "Link in comments"

**Examples**:
- "What's breaking in your AI adoption? Drop it in comments ↓"
- "Book a free 30-min session. Link in comments."

## Engagement Patterns

### High-Performing Patterns (LinkedIn 2024 Data)
1. **Problem → Framework → Example → CTA** (8 slides)
2. **Hook → 3-Layer Framework → 2 Examples → Diagnostic → CTA** (9 slides)
3. **Contrarian Hook → Why It's Wrong → Better Way → Proof → CTA** (7 slides)

### Low-Performing Patterns
- ❌ Text-heavy slides (>50 words per slide)
- ❌ Too many slides (>12 slides = drop-off)
- ❌ No clear narrative (random tips)
- ❌ Generic CTA ("Follow for more")

## Typography

### Font Pairing
- **Headings**: Poppins (Bold/Extra Bold)
- **Body**: Inter (Regular/Medium)
- **Fallback**: Arial/Helvetica

**Why**: Poppins = modern, bold, attention-grabbing. Inter = readable, clean body text.

### Font Weights
- **Super bold**: 800 (hook titles)
- **Bold**: 700 (headings)
- **Semi-bold**: 600 (diagnostic quotes)
- **Medium**: 500 (body text)
- **Regular**: 400 (captions)

## Color Psychology

### Sparkry Brand Colors
- **Primary (Orange #ff6b35)**: Action, energy, CTA
- **Navy (#171d28)**: Trust, professionalism, authority
- **Electric Blue (#0ea5e9)**: Innovation, technology, accent
- **White (#ffffff)**: Clarity, openness

### Color Usage
- **Hook slides**: Navy + Electric Blue gradient (trust + innovation)
- **Framework slides**: White background + Electric Blue bullets (clarity + structure)
- **Example slides**: Muted gray background (#f1f5f9) (softer, story mode)
- **Diagnostic slides**: Navy solid (serious, reflective)
- **CTA slides**: Gradient (energy, action)

## Content Chunking

### Progressive Disclosure
**Bad**: Dump entire framework on slide 2
**Good**: Reveal framework layer-by-layer (3 slides)

**Example**:
- Slide 2: "Layer 1: Decision Rights"
- Slide 3: "Layer 2: Quality Contracts"
- Slide 4: "Layer 3: Handoff Protocols"

**Why**: Each slide = new insight. Keeps reader engaged.

### Sentence Length
- **Short sentences**: 8-12 words (ideal for slides)
- **Medium sentences**: 12-18 words (acceptable)
- **Long sentences**: >18 words (split into 2 slides)

### Bullet Points
- Max 5 bullets per slide
- Max 15 words per bullet
- Parallel structure (all start with verb, or all nouns)

## Mobile Optimization

### Test on Mobile
**Critical**: 70% of LinkedIn users on mobile

**Checklist**:
- [ ] Text readable without zooming
- [ ] Icons clear at small size
- [ ] Tap targets >44px (for interactive elements)
- [ ] No text in images (use HTML text for accessibility)

### Portrait vs. Square
- **Square (1080×1080)**: Best for mobile feed (recommended)
- **Portrait (1080×1350)**: More screen real estate, but awkward on desktop

## Accessibility

### WCAG Compliance
- [ ] Contrast ratio ≥4.5:1 (AA standard)
- [ ] Font size ≥32px for body text
- [ ] Alt text for icons (if needed)
- [ ] No reliance on color alone (use icons + text)

### Screen Reader Friendly
- Use semantic HTML (h1, h2, p tags)
- Descriptive alt text for images
- Logical reading order

## Performance Metrics

### Engagement Benchmarks (LinkedIn 2024)
- **High-performing carousels**: 8-10 slides, 60/40 visual/text ratio
- **Average swipe-through rate**: 45-60% (slides 1-8)
- **Drop-off point**: Slide 9-10 (keep critical content before this)

### A/B Testing Insights
- **Hook slides with icons**: +25% engagement vs. text-only
- **3-layer frameworks**: +40% save rate vs. single-slide frameworks
- **"REAL EXAMPLE" label**: +30% credibility vs. generic examples
- **Specific CTAs**: +50% comments vs. "Follow for more"

## Common Mistakes

### Mistake 1: Text Walls
**Problem**: >50 words per slide
**Fix**: Max 30 words, 5 lines

### Mistake 2: Low Contrast
**Problem**: Black text on dark background
**Fix**: Use color-contrast-validator.py

### Mistake 3: Tiny Fonts
**Problem**: 18-24px body text (unreadable on mobile)
**Fix**: Min 32px for body text

### Mistake 4: No Narrative
**Problem**: Random tips with no flow
**Fix**: Hook → Framework → Example → CTA

### Mistake 5: Generic CTA
**Problem**: "Follow for more" (low engagement)
**Fix**: "What's breaking in your X? Drop it in comments ↓"

## Slide-by-Slide Checklist

### Every Slide
- [ ] Max 30 words
- [ ] Max 5 lines
- [ ] Min 32px body text
- [ ] Contrast ratio ≥4.5:1
- [ ] 80-100px margins
- [ ] Logo zone clear (bottom-right 200×130px)

### Hook Slide
- [ ] Icon present (100px)
- [ ] Title <8 words
- [ ] Subtitle <15 words
- [ ] Gradient background (engaging)

### Framework Slide
- [ ] Icon (80px)
- [ ] Max 5 bullets
- [ ] Bullets <15 words each
- [ ] Electric Blue bullets

### Example Slide
- [ ] "REAL EXAMPLE" label
- [ ] Story <30 words
- [ ] Muted background
- [ ] Icon (60px, top-right)

### Diagnostic Slide
- [ ] Question or "If/then"
- [ ] Center-aligned
- [ ] Navy background
- [ ] No icon (focus on words)

### CTA Slide
- [ ] Question related to post
- [ ] Clear action ("Drop it in comments")
- [ ] Gradient background
- [ ] Icon (80px)

## References

- **LinkedIn Marketing Labs**: Carousel engagement data (Q4 2024)
- **CarouselPost.com**: Best practices analysis (2024)
- **SocialInsider**: LinkedIn carousel benchmarks (2024)
- **WCAG 2.1**: Accessibility guidelines

## Example High-Performing Carousel

**Topic**: "AI Adoption Theater vs. Real Infrastructure"

1. **Hook**: "Your team is split on AI adoption" (icon: users-2)
2. **Framework Layer 1**: "Decision Rights" (icon: layers)
3. **Framework Layer 2**: "Quality Contracts" (icon: shield-check)
4. **Framework Layer 3**: "Handoff Protocols" (icon: arrow-right-left)
5. **Example 1**: Team made AI "decision-capable" for internal docs (icon: sparkles)
6. **Example 2**: Quality contract: "Good enough = passes tests" (icon: check-circle)
7. **Diagnostic**: "If doubling AI usage would break your system..." (no icon)
8. **CTA**: "What's breaking in your AI adoption? Drop it in comments ↓" (icon: message-circle)

**Results**: 8 slides, 240 total words (30/slide avg), 60/40 visual/text ratio, WCAG AA compliant
