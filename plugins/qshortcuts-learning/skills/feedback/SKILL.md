---
name: Feedback Integration
description: Extract user feedback from documents, categorize insights, and integrate into learnings for continuous improvement
version: 1.0.0
tools: [comment-extractor.py, feedback-categorizer.py, learning-integrator.py, feedback-summarizer.py]
references: [feedback-taxonomy.md, integration-patterns.md, learning-formats.md]
claude_tools: Read, Grep, Glob, Edit, Write, Bash
trigger: QFEEDBACK
---

# QFEEDBACK Skill

## Role
You are "Feedback Integrator", an agent that extracts, categorizes, and integrates user feedback into learnings for continuous improvement.

## Goals
1. Extract feedback and comments from documents, PRs, and conversations
2. Categorize feedback by type, priority, and domain
3. Integrate insights into relevant learning files
4. Generate summaries of feedback trends and patterns

## Workflow

### Phase 1: Extract Feedback

```bash
# Extract comments from documents
python scripts/comment-extractor.py <file-or-directory>

# Output: JSON with {source, type, content, context, line}
```

**Extraction Sources:**
- Inline comments (TODO, FIXME, NOTE, FEEDBACK)
- PR review comments
- User conversation transcripts
- Meeting notes with feedback sections
- Bug reports and feature requests

### Phase 2: Categorize Feedback

```bash
# Categorize extracted feedback
python scripts/feedback-categorizer.py <extracted-feedback.json>

# Output: JSON with categories, priorities, domains
```

**Category Taxonomy** (load `references/feedback-taxonomy.md`):

| Category | Description | Example |
|----------|-------------|---------|
| **Enhancement** | Improvement to existing feature | "Add better error messages" |
| **Bug** | Something broken or incorrect | "Parser fails on edge case" |
| **UX** | User experience issue | "Workflow is confusing" |
| **Performance** | Speed or efficiency | "Takes too long to load" |
| **Documentation** | Missing or unclear docs | "Need example for API" |
| **Architecture** | Design or structure | "Should use event-driven" |

**Priority Levels:**
- **P0**: Critical - blocks work or major pain point
- **P1**: Important - significant impact on productivity
- **P2**: Nice to have - minor improvement
- **P3**: Future consideration - low impact

### Phase 3: Integrate into Learnings

```bash
# Integrate feedback into learning files
python scripts/learning-integrator.py <categorized-feedback.json>

# Output: Updated learning files with new insights
```

**Integration Patterns** (load `references/integration-patterns.md`):

1. **Append Pattern**: Add to existing learning section
2. **Update Pattern**: Modify existing learning with new context
3. **New Section Pattern**: Create new learning category
4. **Cross-Reference Pattern**: Link to related learnings

**Learning File Structure:**
```markdown
# Topic Learning

## Context
[When this learning applies]

## Insight
[What was learned]

## Evidence
- [Source 1]: [Feedback or observation]
- [Source 2]: [Supporting evidence]

## Application
[How to apply this learning]

## Related
- [Link to related learnings]
```

### Phase 4: Summarize Feedback

```bash
# Generate feedback summary report
python scripts/feedback-summarizer.py <learning-directory>

# Output: Markdown summary with trends and patterns
```

**Summary Sections:**
- Feedback volume by category
- Top priority insights
- Emerging patterns
- Action items
- Learning coverage gaps

## Tools Usage

### scripts/comment-extractor.py

```python
"""
Extract feedback comments from source files.

Patterns detected:
- // TODO: ...
- // FIXME: ...
- // NOTE: ...
- // FEEDBACK: ...
- <!-- COMMENT: ... -->
- # TODO: ...
"""

python scripts/comment-extractor.py path/to/file.ts
python scripts/comment-extractor.py projects/  # Recursive

# Output:
{
  "source": "path/to/file.ts:42",
  "type": "TODO",
  "content": "Add better error handling",
  "context": "function validateInput()",
  "timestamp": "2026-01-28T10:30:00Z"
}
```

### scripts/feedback-categorizer.py

```python
"""
Categorize feedback using taxonomy and priority rules.

Rules:
- Keywords → Category mapping
- Urgency indicators → Priority
- Domain detection → Area
"""

python scripts/feedback-categorizer.py extracted-feedback.json

# Output:
{
  "id": "FB-001",
  "category": "Enhancement",
  "priority": "P1",
  "domain": "testing",
  "content": "Add better error handling",
  "source": "projects/feature-x/src/validator.ts:42",
  "related_learnings": ["learnings/testing/error-handling.md"]
}
```

### scripts/learning-integrator.py

```python
"""
Integrate categorized feedback into learning files.

Actions:
- Create new learning if none exists
- Append to existing learning
- Update evidence sections
- Add cross-references
"""

python scripts/learning-integrator.py categorized-feedback.json

# Output:
{
  "learnings_updated": 3,
  "learnings_created": 1,
  "cross_references_added": 2,
  "files": [
    "learnings/testing/error-handling.md",
    "learnings/ux/feedback-patterns.md"
  ]
}
```

### scripts/feedback-summarizer.py

```python
"""
Generate summary report of feedback trends.

Analyzes:
- Category distribution
- Priority breakdown
- Domain coverage
- Trend over time
"""

python scripts/feedback-summarizer.py learnings/

# Output: feedback-summary.md with visualizations
```

## References

### references/feedback-taxonomy.md

Complete feedback categorization system with keywords and examples.

### references/integration-patterns.md

Patterns for integrating feedback into different learning types:
- Technical learnings
- Process improvements
- User insights
- Architectural decisions

### references/learning-formats.md

Standard formats for different types of learnings:
- Technical insights
- Process learnings
- Anti-patterns
- Best practices

## Usage Examples

### Example 1: Process PR Feedback

```bash
# Extract feedback from PR comments
python scripts/comment-extractor.py .git/pr-comments.txt

# Categorize
python scripts/feedback-categorizer.py extracted-feedback.json

# Integrate into learnings
python scripts/learning-integrator.py categorized-feedback.json

# Review updates
cat learnings/code-review/common-issues.md
```

### Example 2: Analyze Project Feedback

```bash
# Extract all TODO/FIXME comments from project
python scripts/comment-extractor.py projects/my-project/

# Categorize by domain
python scripts/feedback-categorizer.py extracted-feedback.json

# Generate summary
python scripts/feedback-summarizer.py learnings/

# Review top priorities
cat feedback-summary.md
```

### Example 3: Integrate Meeting Notes

```bash
# Extract feedback from meeting notes
python scripts/comment-extractor.py docs/meetings/2026-01-28-retro.md

# Categorize insights
python scripts/feedback-categorizer.py extracted-feedback.json

# Integrate process improvements
python scripts/learning-integrator.py categorized-feedback.json

# Check new learnings
git diff learnings/
```

## Output Schema

### Extracted Feedback JSON
```json
{
  "extractions": [
    {
      "id": "EXT-001",
      "source": "path/to/file:line",
      "type": "TODO|FIXME|NOTE|FEEDBACK",
      "content": "string",
      "context": "string",
      "timestamp": "ISO-8601"
    }
  ],
  "summary": {
    "total_extractions": "number",
    "by_type": {"TODO": 5, "FIXME": 2},
    "by_source": {"project-x": 3, "project-y": 4}
  }
}
```

### Categorized Feedback JSON
```json
{
  "feedback": [
    {
      "id": "FB-001",
      "category": "Enhancement|Bug|UX|Performance|Documentation|Architecture",
      "priority": "P0|P1|P2|P3",
      "domain": "string",
      "content": "string",
      "source": "string",
      "related_learnings": ["string"],
      "action_items": ["string"]
    }
  ],
  "summary": {
    "by_category": {},
    "by_priority": {},
    "by_domain": {}
  }
}
```

### Integration Result JSON
```json
{
  "learnings_updated": "number",
  "learnings_created": "number",
  "cross_references_added": "number",
  "files": ["string"],
  "integration_log": [
    {
      "feedback_id": "FB-001",
      "learning_file": "path/to/learning.md",
      "action": "append|update|create",
      "section": "string"
    }
  ]
}
```

## Configuration

### .claude/feedback-config.json

```json
{
  "extraction": {
    "patterns": ["TODO", "FIXME", "NOTE", "FEEDBACK"],
    "exclude_dirs": ["node_modules", ".git", "dist"],
    "file_types": [".ts", ".js", ".py", ".md"]
  },
  "categorization": {
    "priority_keywords": {
      "P0": ["critical", "blocker", "urgent"],
      "P1": ["important", "should", "needed"]
    }
  },
  "integration": {
    "learning_directory": "learnings/",
    "auto_create_learnings": true,
    "add_timestamps": true
  }
}
```

## Story Point Estimation

Feedback integration estimates:
- **Extract feedback** (small project): 0.05 SP
- **Extract feedback** (large codebase): 0.2 SP
- **Categorize feedback**: 0.1 SP
- **Integrate into learnings**: 0.2 SP per learning file
- **Generate summary**: 0.1 SP

**Full workflow**: 0.5-1 SP depending on volume

## Best Practices

1. **Regular Extraction**: Run weekly to capture feedback early
2. **Clear Categories**: Use consistent taxonomy for better analysis
3. **Link Context**: Always include source and context for feedback
4. **Prioritize Actions**: Focus on P0/P1 feedback first
5. **Review Patterns**: Look for recurring themes in summaries
6. **Update Learnings**: Keep learning files current and actionable

## Non-Destructive Rules

- Never delete existing feedback comments from source
- Preserve original learning content when integrating
- Create backups before bulk updates
- Log all integration actions for audit trail
