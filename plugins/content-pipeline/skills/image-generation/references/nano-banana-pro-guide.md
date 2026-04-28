# Nano Banana Pro Prompting Guide

> **Last Updated**: December 2025
> **Models**: Gemini 2.5 Flash Image (Nano Banana), Gemini 3 Pro Image (Nano Banana Pro)
> **API Model IDs**: `gemini-2.5-flash-image`, `gemini-3-pro-image-preview`

## Overview

**Nano Banana Pro** (Gemini 3 Pro Image) is Google DeepMind's state-of-the-art image generation and editing model. Unlike traditional diffusion models, it uses an autoregressive architecture with a "thinking" process for complex prompts.

### Model Selection

| Model | Best For | Resolution | Latency |
|-------|----------|------------|---------|
| **Nano Banana** (2.5 Flash) | High-volume, low-latency tasks | 1024px | Fast |
| **Nano Banana Pro** (3 Pro) | Professional assets, complex instructions | Up to 4K | Slower |

**Use Nano Banana Pro for**:
- Hero images with text rendering
- Infographics with multiple elements
- Brand-consistent marketing assets
- Complex multi-element compositions

---

## Core Prompting Principles

### 1. Describe Scenes, Don't List Keywords

**Bad**: `data engineer, whack-a-mole, 3D, cartoon, colorful`

**Good**: `3D cartoon illustration of a data engineer playing a whack-a-mole arcade game. She has short black hair, wears a purple hoodie, and grips an oversized red mallet mid-swing. Colorful moles pop up from holes, each holding small signs reading "BAD DATA", "MISSING", "LATE", "DUPLICATES". Pixar-style rendering, soft studio lighting, clean white background.`

### 2. Use Markdown Structure for Complex Prompts

The model's 32K token context understands markdown formatting. Structure rules as lists:

```markdown
Create a professional infographic about AI adoption.

MUST follow these EXACTLY:
- Title at top: "5 Pillars of AI Transformation"
- Each pillar as vertical column with icon
- Color scheme: navy (#1a1a2e), electric blue (#0f3460)
- Sans-serif typography (clean, modern)
- 16:9 aspect ratio
```

### 3. Capitalization Increases Adherence

`MUST`, `NEVER`, `ALWAYS`, `EXACTLY` in ALL CAPS improves compliance.

### 4. Specify Technical Details

**Photography prompts**:
- Camera: "Canon EOS R5 with 85mm f/1.4 lens"
- Lighting: "three-point softbox setup, golden hour backlight"
- Composition: "rule of thirds, shallow depth of field, bokeh background"

**Illustration prompts**:
- Style: "Pixar-style 3D render", "flat vector illustration", "isometric design"
- Quality: "clean outlines, cel-shading, 4K resolution"

### 5. Use Hex Colors for Precision

```
Primary: #1a1a2e (Sparkry navy)
Accent: #ff6b35 (Sparkry orange)
Background: #f8f9fa (light gray)
```

Natural language colors ("blue") are ambiguous. Hex codes are exact.

---

## Hero Image Prompts

### Template Structure

```
A [style] hero image for [topic].

Visual elements:
- [Main subject/visual metaphor]
- [Background treatment]
- [Color scheme with hex codes]

Text elements (if any):
- Title: "[exact title text]"
- Font style: [bold sans-serif, elegant serif, etc.]

Technical specs:
- Aspect ratio: [16:9 for web, 1:1 for social]
- Style: [photorealistic, 3D illustration, flat design]
- Mood: [professional, playful, dramatic]
```

### Click-Through Optimization

Research shows hero images that convert well have:

1. **Clear focal point** - One dominant visual element
2. **Negative space** - Room for text overlays (position text area)
3. **Emotion/curiosity** - Unusual angles, interesting subjects
4. **Brand consistency** - Recognizable color palette
5. **Simplicity** - Not overcrowded (mobile-first mindset)

### Example: Data Operations Article

```
3D cartoon illustration for a tech article about data operations.

Scene: A data engineer (young Asian woman with glasses, purple hoodie) plays a whack-a-mole arcade game. She grips an oversized red mallet mid-swing with a determined but frustrated expression.

Moles: Four colorful moles pop up from holes, each holding small signs:
- "BAD DATA" (red sign)
- "MISSING" (yellow sign)
- "LATE" (orange sign)
- "DUPLICATES" (blue sign)

One mole already bonked shows cartoon stars above its head.

Style: Pixar-style 3D render, soft studio lighting, playful colors
Background: Clean white, uncluttered
Composition: Centered, leaving space at top for title overlay
Aspect ratio: 16:9
```

### Variant Prompts (Generate 3 options)

For diversity, vary these elements while keeping core concept:

1. **Person variant**: Change demographics (Black man with beard, Latina woman with ponytail)
2. **Angle variant**: Change camera angle (side view, overhead view)
3. **Style variant**: Change visual style (flat 2D, claymation, pixel art)

---

## Infographic Prompts

### Key Capabilities

Nano Banana Pro excels at:
- **Text rendering**: Legible, correctly spelled text in images
- **Data visualization**: Charts, diagrams, process flows
- **Layout control**: Multi-panel compositions
- **Icon integration**: Consistent icon systems

### Template Structure

```
Create a [style] infographic explaining [topic].

Structure:
- Title: "[exact title]" at top
- [N] sections arranged as [layout: vertical flow, horizontal timeline, radial, etc.]
- Each section has: [icon + heading + 2-3 bullet points]

Visual style:
- Color palette: [primary], [secondary], [accent]
- Typography: [headline font], [body font]
- Icons: [flat, outlined, filled] style
- Background: [solid, gradient, textured]

Content (map exactly):
1. [Section 1 heading]: [key points]
2. [Section 2 heading]: [key points]
...

Technical:
- Dimensions: [1200x1600 for vertical, 1920x1080 for horizontal]
- WCAG AA contrast (4.5:1 minimum)
- Mobile-readable text sizes
```

### Layout Patterns

| Pattern | Best For | Element Count |
|---------|----------|---------------|
| Vertical flow | Sequential steps | 3-7 |
| Horizontal timeline | Chronological | 4-6 |
| Pillars/columns | Independent categories | 3-5 |
| Pyramid/hierarchy | Priority levels | 3-4 |
| Cycle/loop | Iterative processes | 4-6 |
| Radial/hub | Central concept + spokes | 3-6 |

### Example: Framework Infographic

```
Create a professional infographic titled "The Four Pillars of AI-Powered Data Operations"

Layout: Four vertical pillars side by side with connecting foundation bar at bottom

Each pillar:
- Icon at top (flat duotone style)
- Heading in bold sans-serif
- 2 bullet points below

Pillars (left to right):
1. "Data Application" - database icon
   - Self-service provisioning
   - Zero-ticket access

2. "Intelligent Analysis" - brain/AI icon
   - AI agents with confidence scoring
   - Built-in evaluation frameworks

3. "Proactive Intelligence" - bell/notification icon
   - Anomaly detection alerts
   - Auto-deprecation of unused assets

4. "Learning Flywheels" - circular arrows icon
   - Every interaction improves system
   - Compound intelligence over time

Colors:
- Background: #f8f9fa (light gray)
- Pillars: #1a1a2e (navy)
- Icons: #ff6b35 (orange accent)
- Text: #333333 (dark gray)

Typography: Poppins Bold headings, Inter Regular body
Aspect ratio: 16:9 (1920x1080)
```

---

## Technical Specifications

### Aspect Ratios

| Ratio | Resolution | Use Case |
|-------|------------|----------|
| 1:1 | 1024x1024 | Social media posts |
| 16:9 | 1344x768 (1K), 2752x1536 (2K) | Hero images, presentations |
| 9:16 | 768x1344 (1K), 1536x2752 (2K) | Stories, vertical content |
| 4:3 | 1184x864 | Traditional displays |
| 3:2 | 1248x832 | Photography standard |

### Resolution Options (Nano Banana Pro only)

- **1K**: Default, fastest generation
- **2K**: Recommended for hero images and infographics
- **4K**: Print-ready, longest generation time

### API Configuration

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",  # or gemini-2.5-flash-image
    contents=[prompt],
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE'],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",  # See ratios above
            image_size="2K"       # 1K, 2K, or 4K
        )
    )
)
```

---

## Advanced Techniques

### Google Search Grounding

Nano Banana Pro can access real-time information via Google Search:

```python
config=types.GenerateContentConfig(
    tools=[{"google_search": {}}],
    response_modalities=['TEXT', 'IMAGE']
)
```

Use for:
- Current statistics and data
- Recent events or news
- Verifiable facts in infographics

### Multi-Image Input (Up to 14 images)

For style transfer or character consistency:
- Up to 6 images of objects
- Up to 5 images of humans
- Reference images for pose, style, composition

```python
response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=[prompt, image1, image2, image3],
    ...
)
```

### Iterative Refinement (Chat Mode)

Use multi-turn conversation for editing:

```python
chat = client.chats.create(
    model="gemini-3-pro-image-preview",
    config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
    )
)

# Initial generation
response = chat.send_message("Create infographic about photosynthesis")

# Refinement
response = chat.send_message("Change the color scheme to blue and green")

# Translation
response = chat.send_message("Update all text to Spanish")
```

---

## Common Pitfalls

### What Doesn't Work Well

1. **Style transfer from existing images**: "Make this photo look like Studio Ghibli" produces poor results
2. **Perfect typography**: Still occasionally produces typos, especially with unusual words
3. **Complex multi-person scenes**: Character consistency degrades with many subjects
4. **Exact reproduction**: Cannot perfectly replicate reference images

### Mitigation Strategies

- **Text rendering**: Keep text short, common words; review and regenerate if typos
- **Character consistency**: Use multiple reference images (3-5) of same subject
- **Complex scenes**: Build up iteratively rather than one-shot generation
- **Brand compliance**: Always specify hex colors, font names, explicit style cues

---

## Integration with QVISUAL

When generating prompts for QVISUAL workflow:

1. **Extract article metadata** (title, key insight, framework)
2. **Select appropriate template** (hero image vs. infographic)
3. **Generate 2-3 variant prompts** with different:
   - Visual metaphors
   - Person demographics
   - Color treatments
4. **Include technical specs** (aspect ratio, resolution)
5. **Output as copy-paste ready prompts** for Gemini API or AI Studio

### Output Format

```markdown
## Nano Banana Pro Prompt 1 (Recommended)

[Full prompt text here]

---

## Nano Banana Pro Prompt 2 (Variant)

[Full prompt text here]

---

## Nano Banana Pro Prompt 3 (Variant)

[Full prompt text here]

---

**Technical Settings**:
- Model: gemini-3-pro-image-preview
- Aspect ratio: 16:9
- Resolution: 2K
- Google Search grounding: [Yes/No]
```

---

## Sources

- Google Official: https://blog.google/products/gemini/prompting-tips-nano-banana-pro/
- API Documentation: https://ai.google.dev/gemini-api/docs/image-generation
- Simon Willison's Testing: https://simonwillison.net/2025/Nov/20/nano-banana-pro/
- Max Woolf's Engineering: https://minimaxir.com/2025/11/nano-banana-prompts/
