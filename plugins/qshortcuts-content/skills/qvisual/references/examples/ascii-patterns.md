# ASCII Art Patterns

## Pattern 1: Box-Drawing Characters

```
┌─────────────┐
│   Process   │
└─────────────┘
      ↓
┌─────────────┐
│   Outcome   │
└─────────────┘
```

**Detection**: Unicode box-drawing characters (┌─┐│└┘├┤┬┴┼)
**Type**: Flowchart
**Suggested Style**: framework

## Pattern 2: ASCII Borders

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

**Detection**: ASCII borders (+, |, -, v, ^)
**Type**: Flowchart
**Suggested Style**: flowchart

## Pattern 3: Tree Structures

```
Root
├── Branch 1
│   ├── Leaf 1
│   └── Leaf 2
└── Branch 2
    └── Leaf 3
```

**Detection**: Tree characters (├──┤│└)
**Type**: Hierarchy
**Suggested Style**: tree

## Pattern 4: Flowcharts with Arrows

```
[Start] → [Process] → [Decision]
                         ↓ Yes
                      [Action]
                         ↓ No
                      [End]
```

**Detection**: Arrows (→ ← ↑ ↓) with labels
**Type**: Process flow
**Suggested Style**: flowchart

## Pattern 5: Multi-Layer Framework

```
┌─────────────────────────────────────────┐
│         FRAMEWORK NAME                  │
└─────────────────────────────────────────┘
    ┌───────────────────────────────┐
    │     1. LAYER NAME             │
    │  ┌─────────────────────┐      │
    │  │ Key point           │      │
    │  └─────────────────────┘      │
    └──────────────┬────────────────┘
                   ▼
    ┌───────────────────────────────┐
    │     2. LAYER NAME             │
    │  ┌─────────────────────┐      │
    │  │ Key point           │      │
    │  └─────────────────────┘      │
    └───────────────────────────────┘
```

**Detection**: Nested boxes with connecting arrows
**Type**: Framework
**Suggested Style**: framework

## Detection Logic

### Step 1: Scan for box-drawing characters
- If found: Pattern 1 (box-drawing) or Pattern 5 (framework)

### Step 2: Scan for ASCII borders
- If found: Pattern 2 (ASCII borders)

### Step 3: Scan for tree characters
- If found: Pattern 3 (tree structure)

### Step 4: Scan for arrows with labels
- If found: Pattern 4 (flowchart)

### Step 5: Context analysis
- Check surrounding text for "framework", "layers", "steps"
- Determine if framework or flowchart type

## Conversion Rules

### Boxes → HTML
```html
<div class="box">
  <div class="box-content">Process</div>
</div>
```

### Arrows → CSS/SVG
```html
<div class="arrow arrow-down"></div>
<!-- OR -->
<svg class="arrow"><path d="M..."/></svg>
```

### Tree → Flexbox/Grid
```html
<div class="tree">
  <div class="tree-root">Root</div>
  <div class="tree-children">
    <div class="tree-branch">Branch 1</div>
  </div>
</div>
```

## Styling Guidelines

- **Boxes**: Border radius 8px, padding 20px
- **Arrows**: 3px width, brand color
- **Text**: Poppins (headings), Inter (body)
- **Colors**: Sparkry palette (navy, orange, electric blue)
- **Spacing**: 40px between elements
- **Background**: White or muted gray
