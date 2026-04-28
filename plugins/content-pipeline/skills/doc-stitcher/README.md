# Doc-Stitcher Skill

**Status**: ✅ Complete
**Created**: 2025-10-20
**Purpose**: Token-efficient document concatenation using bash commands

---

## Quick Start

### Basic Usage
```bash
# Stitch 4 files in order
./scripts/stitch-docs.sh \
  --files "part1.md part2.md part3.md part4.md" \
  --output combined.md
```

### With Header Removal
```bash
# Remove first 2 lines from parts 2-4
./scripts/stitch-docs.sh \
  --files "part1.md part2.md part3.md part4.md" \
  --output combined.md \
  --remove-headers
```

### With Section Breaks & Verification
```bash
# Add dividers and verify output
./scripts/stitch-docs.sh \
  --files "part1.md part2.md part3.md part4.md" \
  --output combined.md \
  --remove-headers \
  --section-breaks \
  --verify
```

---

## Files

### Core
- `SKILL.md` - Complete skill documentation
- `scripts/stitch-docs.sh` - Main stitching script
- `scripts/verify-stitch.sh` - Verification script

### Examples
- `examples/pr-faq-stitch.sh` - PR-FAQ concatenation example

### References
- `references/bash-concat-patterns.md` - Bash best practices
- `references/markdown-best-practices.md` - Markdown preservation guide

---

## Common Use Cases

### 1. PR-FAQ Consolidation
```bash
cd .claude/skills/content/doc-stitcher
./scripts/stitch-docs.sh \
  --files "../../../requirements/pr-faq-01-press-release.md ../../../requirements/pr-faq-02-external-faq.md ../../../requirements/pr-faq-03-internal-faq.md ../../../requirements/pr-faq-04-appendices.md" \
  --output "../../../requirements/productization-pr-faq-STITCHED.md" \
  --remove-headers \
  --section-breaks \
  --verify
```

### 2. Requirements Consolidation
```bash
./scripts/stitch-docs.sh \
  --files "requirements/req-401-410.md requirements/req-411-420.md requirements/req-421-430.md" \
  --output requirements/requirements-complete.md
```

### 3. Multi-Chapter Report
```bash
./scripts/stitch-docs.sh \
  --files "chapter1.md chapter2.md chapter3.md" \
  --output report.md \
  --section-breaks
```

---

## Integration

### CLAUDE.md Entry
Add to QShortcuts section:
```markdown
- **QSTITCH**: Concatenate markdown documents using bash to save tokens → **skills/content/doc-stitcher** (tools: stitch-docs.sh, verify-stitch.sh)
```

### Agent Invocation
```
User: "I have 4 PR-FAQ parts. Can you stitch them into a single document?"

Agent: "I'll use the doc-stitcher skill to concatenate the 4 PR-FAQ parts efficiently."

[Uses Bash to execute ./scripts/stitch-docs.sh with appropriate flags]

Agent: "Stitched 4 files into productization-pr-faq-STITCHED.md (1,330 lines). File ready for review."
```

---

## Benefits

1. **Token Efficiency**: Single Read invocation instead of multiple
2. **Context Coherence**: All content in unified context for analysis
3. **Automation**: Repeatable process for multi-part documents
4. **Verification**: Built-in checks for integrity and structure
5. **Flexibility**: Options for header removal, section breaks, validation

---

## Limitations

- Not a replacement for selective reading (if you only need part 2, read it directly)
- Still costs tokens (just better context organization)
- Very large files (>50KB) may hit tool limits
- Complex markdown (nested tables) may require manual review after stitching

---

## Maintenance

**Last Updated**: 2025-10-20
**Dependencies**: bash, cat, tail, grep, wc, sed, awk (standard Unix tools)
**Testing**: Verified with PR-FAQ consolidation (4 parts, 1,330 lines)

---

## See Also

- `.claude/skills/content/` - Other content manipulation skills
- `docs/tasks/INTERFACE-CONTRACT-SCHEMA.md` - Interface contracts for multi-agent work
- `requirements/` - Example multi-part documents (PR-FAQs)
