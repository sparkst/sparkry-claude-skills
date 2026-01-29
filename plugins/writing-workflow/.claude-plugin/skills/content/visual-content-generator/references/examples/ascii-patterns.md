# ASCII Art Patterns for Detection

> **Purpose**: Reference guide for detecting ASCII art in articles
> **Load when**: Running detect-visual-opportunities.py

## Box-Drawing Character Patterns

### Pattern 1: Unicode Box Drawing
```
┌─────────────┐
│   Process   │
└─────────────┘
      ↓
┌─────────────┐
│   Outcome   │
└─────────────┘
```

**Characters**: `┌─┐│└┘├┤┬┴┼╔╗╚╝║═╠╣╦╩╬`

**Detection Logic**:
- Scan for lines containing 2+ box-drawing characters
- Identify top borders: `┌─+┐` or `╔═+╗`
- Look for matching bottom borders within 10 lines
- Extract content between `│` or `║` characters

### Pattern 2: ASCII Borders
```
+-------------------+
|   Component A     |
+-------------------+
         |
         v
+-------------------+
|   Component B     |
+-------------------+
```

**Characters**: `+-|`

**Detection Logic**:
- Scan for lines starting with `+` followed by 3+ `-` characters
- Look for vertical bars `|` in subsequent lines
- Match closing `+---+` border
- Minimum 3 lines for valid box

### Pattern 3: Tree Structures
```
Root
├── Branch 1
│   ├── Leaf 1
│   └── Leaf 2
└── Branch 2
    └── Leaf 3
```

**Characters**: `├─└│`

**Detection Logic**:
- Scan for `├──` or `└──` branch indicators
- Vertical lines `│` indicate continuation
- Indentation shows hierarchy

### Pattern 4: Arrow Flowcharts
```
[Start] → [Process] → [Decision]
                         ↓ Yes
                      [Action]
```

**Characters**: `→ ← ↑ ↓ ▼ ▲ ► ◄ ⇒ ⇐`

**Detection Logic**:
- Detect arrow characters in lines
- Identify direction (right, left, up, down)
- Map flow between text blocks

### Pattern 5: Multi-Layer Frameworks
```
┌─────────────────────────────────────────────────────────────┐
│                  PERMISSION ARCHITECTURE                     │
│                  (System Design for AI Adoption)             │
└─────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────┐
    │     1. DECISION RIGHTS                    │
    │  ┌─────────────────────────────────┐      │
    │  │ Where can AI decide, suggest,   │      │
    │  │ or just research?               │      │
    │  └─────────────────────────────────┘      │
    └──────────────┬────────────────────────────┘
                   │
                   ▼
    ┌───────────────────────────────────────────┐
    │     2. QUALITY CONTRACTS                  │
    │  ┌─────────────────────────────────┐      │
    │  │ What does "good enough" mean?   │      │
    │  └─────────────────────────────────┘      │
    └──────────────┬────────────────────────────┘
                   │
                   ▼
    ┌───────────────────────────────────────────┐
    │     3. HANDOFF PROTOCOLS                  │
    │  ┌─────────────────────────────────┐      │
    │  │ APIs between AI & non-AI work   │      │
    │  └─────────────────────────────────┘      │
    └───────────────────────────────────────────┘
```

**Detection Logic**:
- Detect nested box structures
- Identify layer numbers (1., 2., 3.)
- Extract layer titles and descriptions
- Map vertical flow with arrows

## Indentation-Based Detection

### Code Block ASCII Art
````
```
┌─────┐
│ Box │
└─────┘
```
````

**Detection Logic**:
- Scan code blocks (triple backticks)
- Check for box-drawing or arrow characters
- Extract entire code block as ASCII art

### Indented ASCII (4 spaces or tab)
```
    ┌─────────┐
    │ Process │
    └─────────┘
         ↓
    ┌─────────┐
    │ Outcome │
    └─────────┘
```

**Detection Logic**:
- Scan lines starting with 4 spaces or tab
- Check for box-drawing characters
- Collect adjacent indented lines (up to 20 lines)
- Minimum 3 lines for valid diagram

## False Positives to Avoid

### Single Box (Not a Diagram)
```
┌─────┐
│ Box │
└─────┘
```
**Minimum 2 boxes or 1 box + arrows for valid diagram**

### Table Borders
```
| Column 1 | Column 2 |
|----------|----------|
| Data     | Data     |
```
**Skip markdown tables (detect by header separator line)**

### Horizontal Rules
```
---
```
**Skip markdown horizontal rules (standalone dashes)**

## Framework List Detection

### Numbered Lists (3+ Items)
```markdown
## The Three Pillars of AI Adoption

1. **Decision Rights**: Define where AI can decide, suggest, or research
2. **Quality Contracts**: Establish what "good enough" means
3. **Handoff Protocols**: Create APIs between AI and non-AI work
```

**Detection Logic**:
- Find section headers with framework keywords:
  - "Framework", "Pillars", "Layers", "Steps", "Principles", "Components"
- Extract numbered list below header (1., 2., 3.)
- Minimum 3 items to qualify as framework
- Extract item titles (bold text or first sentence)

### Bullet Lists (5+ Items)
```markdown
## Key Principles

- Principle A: Description
- Principle B: Description
- Principle C: Description
- Principle D: Description
- Principle E: Description
```

**Detection Logic**:
- Find section with 5+ bullet points
- Check for framework-related keywords in header
- Extract bullet point titles

## Output Format

### Detected ASCII Diagram
```json
{
  "type": "ascii_diagram",
  "location": "Line 145-160",
  "content": "┌─────┐\n│ Box │\n└─────┘",
  "suggested_style": "flowchart",
  "line_count": 15
}
```

### Detected Framework
```json
{
  "type": "framework",
  "location": "Section: The Three Pillars",
  "content": "1. Decision Rights\n2. Quality Contracts\n3. Handoff Protocols",
  "suggested_style": "framework",
  "item_count": 3,
  "title": "The Three Pillars of AI Adoption"
}
```

## Detection Priorities

1. **Hero Image**: Always suggest (highest priority)
2. **ASCII Diagrams**: Detect in code blocks and indented sections
3. **Framework Lists**: Detect numbered/bullet lists with framework keywords

## Performance Targets

- **Scan speed**: <1 second for 3000-word article
- **Accuracy**: 90%+ detection rate for valid diagrams
- **False positive rate**: <10%

## References

- **Box-drawing characters**: Unicode U+2500 to U+257F
- **Arrow characters**: Unicode U+2190 to U+21FF
- **Detection tools**: `detect-visual-opportunities.py`
