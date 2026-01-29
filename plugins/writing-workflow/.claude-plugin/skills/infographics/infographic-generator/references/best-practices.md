# Infographic Design Best Practices

> **Purpose**: Design principles for creating effective, accessible, scannable infographics.
> **Load when**: Before rendering HTML (Agent 8) and during QA (Agent 9).

---

## Visual Hierarchy

### Size & Weight Hierarchy
1. **Largest**: Main title (3-4rem)
2. **Large**: Section headings (1.75-2rem)
3. **Medium**: Body text, bullets (1rem)
4. **Small**: Captions, footnotes (0.875rem)

**Rule**: Use size + weight + color together, not just one.

### Reading Patterns

**Z-Pattern** (for Western audiences):
```
Top-left → Top-right
   ↓         ↓
Bottom-left → Bottom-right
```

**F-Pattern** (for text-heavy infographics):
```
Left → Right (scan top)
Left ↓ (vertical scan)
Left → Right (scan middle)
```

**Application**:
- Place most important elements on reading path
- Use visual connectors (arrows, lines) to guide eye
- Number elements explicitly (Step 1, Step 2, etc.)

---

## Color Theory for Infographics

### Color Limits
- **1 base color**: Primary brand color
- **1 accent color**: For highlights, CTAs, stats
- **1-2 neutral colors**: Backgrounds, text

**More colors = more confusion**

### Color Usage Strategy
1. **Reserve accent color** for:
   - Important statistics
   - Call-to-action buttons
   - Key findings

2. **Group related data** in related colors:
   - All "positive" metrics → green family
   - All "negative" metrics → red family
   - Neutral metrics → gray family

3. **Avoid rainbow charts**:
   - 7+ colors in one chart is visual chaos
   - Use shades of 2-3 base colors instead

### Accessibility: WCAG AA Contrast

**Minimum contrast ratios**:
- **Normal text** (< 18pt): 4.5:1
- **Large text** (≥ 18pt): 3:1
- **UI components** (buttons, icons): 3:1

**Tools**:
- WebAIM Contrast Checker
- Chrome DevTools Lighthouse

**Rule**: Never use color alone to convey meaning. Always pair with:
- Icons
- Labels
- Patterns/textures

---

## Typography Best Practices

### Font Pairing
**Good combinations**:
- **Headings**: Sans-serif bold (Poppins, Montserrat, Inter)
- **Body**: Sans-serif regular (Inter, Open Sans, Roboto)

**Avoid**:
- More than 2 font families
- Decorative fonts for body text
- All-caps for long text (readability issues)

### Line Spacing
- **Body text**: 1.5-1.6 line-height
- **Headings**: 1.2-1.3 line-height
- **Bullets**: 1.6+ line-height

**Rule**: Generous white space improves readability.

### Text Length Limits
- **Title**: Max 10 words
- **Heading**: Max 7 words
- **Bullet point**: Max 15 words
- **Paragraph**: Max 3-4 sentences (infographics are not essays)

---

## Layout & Composition

### White Space (Negative Space)
**60-40 Rule**:
- 60% content
- 40% white space

**Why**: White space reduces cognitive load, improves focus.

### Alignment
**Prefer**:
- Left-aligned text (easier to scan)
- Centered titles and headings
- Grid-based layouts (consistent alignment)

**Avoid**:
- Justified text (creates uneven word spacing)
- Random alignment (looks unprofessional)

### Visual Balance
**Symmetry**: Formal, stable, professional
**Asymmetry**: Dynamic, modern, creative

**Rule**: Use asymmetry intentionally, not accidentally.

---

## Scannability

### Chunking Information
**Miller's Law**: People remember 7±2 items at once.

**Application**:
- Break long lists into groups (3-4 items per group)
- Use headings to create clear sections
- Add visual separators (lines, spacing)

### Bullet Points
**Best practices**:
- Keep bullets parallel (same grammatical structure)
- Start with action verbs where possible
- Use bullets for lists, not paragraphs

**Example**:
✅ Good:
- Build data foundation
- Train ML models
- Deploy to production

❌ Bad:
- Building a strong data foundation
- Models should be trained properly
- Deploy after testing

### Icons & Visual Cues
**Why icons work**:
- 60,000x faster to process than text
- Universal (cross-language)
- Improve recall

**Rules**:
- Use icons consistently (same style throughout)
- Pair icons with text labels (not icon alone)
- Icon size: 1.5-2x surrounding text size

---

## Accessibility Beyond Contrast

### Semantic HTML
**Required**:
- `<h1>` for main title
- `<h2>`, `<h3>` for section headings (proper hierarchy)
- `<ul>`, `<ol>` for lists
- `<strong>`, `<em>` for emphasis (not just `<b>`, `<i>`)

**Why**: Screen readers rely on semantic structure.

### Alt Text (for images within infographic)
**Format**: "Alt text describing what the image conveys"

**Example**:
- ❌ Bad: "Chart"
- ✅ Good: "Bar chart showing 40% increase in AI adoption from 2023 to 2024"

### Keyboard Navigation
If infographic has interactive elements:
- All interactive elements must be keyboard-accessible
- Tab order must be logical
- Focus indicators must be visible

---

## Creative Elements (Avoiding PowerPoint Aesthetics)

### Rich Visual Elements

**Use**:
1. **Gradients**: Smooth color transitions for depth
   ```css
   background: linear-gradient(135deg, #color1, #color2);
   ```

2. **Shadows**: Create depth and hierarchy
   ```css
   box-shadow: 0 10px 30px rgba(0,0,0,0.1);
   ```

3. **Custom shapes**: SVG paths, clip-paths
   ```css
   clip-path: polygon(0 0, 100% 0, 95% 100%, 0% 100%);
   ```

4. **Overlays**: Semi-transparent layers
   ```css
   background: rgba(255, 255, 255, 0.95);
   ```

5. **Decorative elements**: Corner brackets, progress rails, accent dots

**Avoid**:
- Simple rectangles with text (boring)
- Stock PowerPoint templates
- Clipart
- 3D effects (dated)

### Texture & Background
**Subtle patterns**:
- Dot grids
- Line grids
- Gradient overlays
- Noise textures (very subtle)

**Rule**: Background should enhance, not distract.

---

## Platform-Specific Considerations

### LinkedIn Carousel
- **Aspect ratio**: 1:1 (square)
- **Max panels**: 10
- **Density**: Medium (not too cluttered)
- **CTA**: On last panel

### Pinterest
- **Aspect ratio**: 2:3 (tall)
- **Max panels**: 15
- **Density**: High (Pinterest users expect detail)
- **Title**: Large, bold at top

### Blog Hero
- **Aspect ratio**: 16:9 (wide)
- **Max panels**: 8
- **Density**: Low (complement article text)
- **Integration**: Should match blog design

### Generic Vertical
- **Aspect ratio**: 9:16 (phone-friendly)
- **Max panels**: 12
- **Density**: Medium
- **Mobile-first**: Design for mobile, scale up

---

## Data Integrity (If Including Data Visualizations)

### Honest Axes
**Never**:
- Start Y-axis at non-zero to exaggerate differences
- Use logarithmic scale without labeling it
- Truncate axes to hide context

### Chart Selection
- **Bar chart**: Comparing quantities
- **Line chart**: Trends over time
- **Pie chart**: Parts of a whole (max 5-6 slices)
- **Scatter plot**: Relationships between variables

**Rule**: Choose chart type that accurately represents data.

### Data Source
**Always include**:
- Source: [Dataset/Report Name]
- Year: [YYYY]
- Sample size: [if survey/study]

**Placement**: Small text at bottom of infographic.

---

## Quality Checklist

Before finalizing infographic, verify:

### Content
- [ ] All framework elements present
- [ ] No fabricated stats or claims
- [ ] Title ≤ 10 words
- [ ] Headings ≤ 7 words
- [ ] Bullets ≤ 15 words

### Design
- [ ] WCAG AA contrast (4.5:1 minimum)
- [ ] Semantic HTML structure
- [ ] Icons paired with text labels
- [ ] Consistent font usage (≤ 2 families)
- [ ] Adequate white space (60-40 rule)

### Creativity
- [ ] Gradients used
- [ ] Shadows for depth
- [ ] Custom visual elements (not stock templates)
- [ ] Visual metaphor clear
- [ ] NOT PowerPoint aesthetic

### Accessibility
- [ ] Alt text on images
- [ ] Color not sole indicator
- [ ] Text readable at 100% zoom
- [ ] Mobile-responsive

### Technical
- [ ] Valid HTML
- [ ] CSS organized
- [ ] External fonts loaded correctly
- [ ] Icons render properly

---

## Anti-Patterns (What NOT to Do)

❌ **Avoid**:
1. **Walls of text**: Infographics are not blog posts
2. **Too many colors**: Stick to 3-4 max
3. **Tiny text**: Minimum 14px for body text
4. **Cluttered layouts**: White space is your friend
5. **Inconsistent styling**: Pick a style and stick with it
6. **Generic stock photos**: Use custom visuals or icons
7. **Comic Sans** (or similar): Never
8. **Gradient text on gradient background**: Readability nightmare
9. **Animation for the sake of animation**: Only if it adds value
10. **Ignoring mobile**: 60%+ of views are on mobile

---

## Resources

### Inspiration
- [Venngage Design Blog](https://venngage.com/blog/infographic-design/)
- [Column Five Media](https://www.columnfivemedia.com/)
- [Canva Infographic Examples](https://www.canva.com/infographics/)

### Tools
- **Contrast Checker**: WebAIM, Coolors
- **Font Pairing**: FontJoy, Google Fonts
- **Icons**: Font Awesome, Heroicons, Feather Icons
- **Color Palettes**: Coolors, Adobe Color

### Standards
- **WCAG 2.1 AA**: [W3C Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- **Responsive Design**: [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)

---

**Version**: 1.0.0
**Last Updated**: 2025-01-11
