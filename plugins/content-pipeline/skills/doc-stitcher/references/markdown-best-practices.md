# Markdown Preservation Best Practices

Guidelines for maintaining markdown structure when concatenating documents.

---

## Structure Preservation

### Headers
```markdown
# Top-level headers should remain unique
## Sub-headers can repeat across parts
### Sub-sub-headers preserve hierarchy
```

**When Stitching**:
- Keep Part 1 header intact: `# Universal LLM Router - Product Launch PR-FAQ`
- Remove redundant part headers: `# Part 2: External FAQ` → delete
- Preserve section headers: `## General Questions` → keep

### Code Blocks
```markdown
Ensure opening and closing ``` match:

```python
def example():
    pass
```

# Next section (not inside code block)
```

**Common Issue**: Unclosed code blocks
```markdown
# ❌ BAD: Part 1 ends with unclosed ```
```python
code here

# Part 2 starts (now inside code block!)
## External FAQ
```

**Solution**: Verify each part has balanced ``` before stitching.

### Lists
```markdown
- Ordered lists preserve numbering
- Unordered lists use consistent markers (-, *, or +)
  - Nested lists maintain indentation (2 spaces)
    - Third level (4 spaces)
```

**When Stitching**: Ensure blank lines between parts don't break list continuity.

### Tables
```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Row 1    | Data     | More     |
| Row 2    | Data     | More     |
```

**When Stitching**: Tables are fragile—avoid splitting mid-table.

---

## Section Breaks

### Visual Dividers
```markdown
Use horizontal rules to separate major sections:

---

# New Section

Content here...
```

**Best Practice**: Add blank lines around dividers:
```markdown
Part 1 content

---

Part 2 content
```

### Page Breaks (PDF)
```markdown
<div style="page-break-after: always;"></div>

# Next Section
```

**When**: Use for print-ready documents, not web content.

---

## Link Preservation

### Internal Links
```markdown
[See FAQ](#q1-how-much-can-i-save)

...later in document...

<a name="q1-how-much-can-i-save"></a>
## Q1: How much can I save?
```

**When Stitching**: Verify anchor targets exist in final document.

### External Links
```markdown
[Sparkry AI](https://sparkryai.com)
```

**Best Practice**: Test links after stitching (relative paths may break).

---

## Metadata Preservation

### Front Matter (YAML)
```markdown
---
title: Universal LLM Router PR-FAQ
version: 3.0
date: 2025-10-20
---

# Document starts here
```

**When Stitching**: Only include front matter from Part 1 (remove from subsequent parts).

### Document Control
```markdown
At the end of stitched document:

---

# Document Control

- **Version**: FINAL v3
- **Status**: APPROVED
- **Files**:
  - pr-faq-01-press-release.md
  - pr-faq-02-external-faq.md
  - pr-faq-03-internal-faq.md
  - pr-faq-04-appendices.md
```

---

## Common Issues & Fixes

### Issue 1: Duplicate Headers
```markdown
# ❌ BAD: Duplicate top-level headers
# Universal LLM Router PR-FAQ
...Part 1 content...
# Universal LLM Router PR-FAQ  ← duplicate
...Part 2 content...

# ✅ GOOD: Remove duplicate
# Universal LLM Router PR-FAQ
...Part 1 content...
---
## External FAQ  ← demoted to H2
...Part 2 content...
```

### Issue 2: Broken Code Blocks
```markdown
# ❌ BAD: Unclosed block at part boundary
```python
def example():
    pass
← missing closing ```
---
# Part 2
```

**Fix**: Verify balanced ``` before stitching:
```bash
CODE_START=$(grep -c '^```' part1.md)
if [ $((CODE_START % 2)) -ne 0 ]; then
  echo "Warning: Unclosed code blocks in part1.md"
fi
```

### Issue 3: List Continuity
```markdown
# ❌ BAD: Broken list
1. Item from Part 1

---  ← breaks list

2. Item from Part 2  ← renumbers to 1

# ✅ GOOD: Continuous list or new list
1. Item from Part 1

---

1. New list from Part 2  ← explicitly restart
```

### Issue 4: Table Splitting
```markdown
# ❌ BAD: Table split across parts
| Column 1 | Column 2 |
|----------|----------|
| Row 1    | Data     |
---  ← splits table
| Row 2    | Data     |  ← broken

# ✅ GOOD: Keep tables whole
| Column 1 | Column 2 |
|----------|----------|
| Row 1    | Data     |
| Row 2    | Data     |
---
Next section...
```

---

## Validation Checklist

After stitching, verify:

- [ ] **Headers**: No duplicate H1s, hierarchy preserved
- [ ] **Code Blocks**: Balanced ``` (even count)
- [ ] **Lists**: Proper indentation, no broken continuity
- [ ] **Tables**: No mid-table splits
- [ ] **Links**: Internal anchors exist, external links work
- [ ] **Metadata**: Only one front matter block (from Part 1)
- [ ] **Section Breaks**: Consistent divider style (`---`)
- [ ] **Blank Lines**: Proper spacing around headers, blocks
- [ ] **Encoding**: UTF-8 throughout, no binary characters
- [ ] **Line Endings**: Consistent (Unix LF, not Windows CRLF)

---

## Tools for Validation

### Markdown Linter
```bash
# Install markdownlint
npm install -g markdownlint-cli

# Lint stitched document
markdownlint combined.md

# Common warnings after stitching:
# - MD012: Multiple consecutive blank lines
# - MD022: Headers should be surrounded by blank lines
# - MD025: Multiple top-level headers (remove duplicates)
```

### Pandoc (Convert to HTML/PDF)
```bash
# Convert to HTML to check structure
pandoc combined.md -o combined.html

# Open in browser to verify
open combined.html
```

### Manual Checks
```bash
# Check code block balance
CODE_BLOCKS=$(grep -c '^```' combined.md)
echo "Code blocks: $CODE_BLOCKS (should be even)"

# Check for duplicate H1s
H1_COUNT=$(grep -c '^# ' combined.md)
echo "H1 headers: $H1_COUNT (should be 1 or 2 max)"

# Check link targets
grep -o '\[.*\](#.*' combined.md | sed 's/.*#//' | sort -u > targets.txt
grep -o '<a name=".*">' combined.md | sed 's/<a name="//; s/">//' | sort -u > anchors.txt
diff targets.txt anchors.txt  # Should have no output (all targets exist)
```

---

## References

- Markdown Guide: https://www.markdownguide.org/
- CommonMark Spec: https://commonmark.org/
- Markdownlint Rules: https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md
- Pandoc Manual: https://pandoc.org/MANUAL.html
