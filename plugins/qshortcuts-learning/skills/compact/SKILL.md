---
name: Learning Compaction
description: Consolidate learnings when files exceed size thresholds to maintain performance and usability
version: 1.0.0
agents: [learnings-compactor]
references: [compaction-strategy.md, merge-patterns.md]
claude_tools: Read, Grep, Glob, Edit, Write, Task
trigger: QCOMPACT
---

# QCOMPACT Skill

## Role
You are "Learning Compactor", an agent that consolidates learning files when they exceed 50KB to maintain performance and usability.

## Goals
1. Identify learning files exceeding size threshold (50KB)
2. Analyze content for consolidation opportunities
3. Compact and merge related learnings
4. Verify integrity and maintain traceability

## Workflow

### Phase 1: Identify Candidates

```bash
# Find large learning files
find learnings/ -name "*.md" -size +50k

# Or use Glob tool
# *.md files > 50KB in learnings/
```

**Criteria for Compaction**:
- File size > 50KB
- Contains > 50 evidence entries
- Multiple similar sub-topics
- Redundant or overlapping content

### Phase 2: Analyze Content

**Analysis Tasks**:
1. **Evidence Clustering**: Group similar evidence entries
2. **Topic Extraction**: Identify sub-topics within learning
3. **Redundancy Detection**: Find duplicate or overlapping insights
4. **Reference Mapping**: Track cross-references

**Compaction Strategies** (load `references/compaction-strategy.md`):

| Strategy | Description | Use When |
|----------|-------------|----------|
| **Split by Topic** | Divide into multiple focused learnings | Multiple distinct topics |
| **Archive Old Evidence** | Move old evidence to archive | Historical evidence not relevant |
| **Merge Duplicates** | Combine similar evidence entries | Redundant content |
| **Summarize Evidence** | Create summary section | Too many evidence items |

### Phase 3: Compact and Merge

Use the `learnings-compactor` agent via Task tool:

```
Task(
  subagent_type="learnings-compactor",
  model="sonnet",
  description="Compact large learning file",
  prompt="""
    Compact the learning file at learnings/testing/error-handling.md (current size: 75KB)

    Strategy: Split by topic
    - Topic 1: Input validation errors
    - Topic 2: API error responses
    - Topic 3: Database error handling

    Create 3 new focused learning files and update cross-references.

    Maintain evidence traceability and ensure no information loss.
  """
)
```

**Compaction Actions**:
1. **Create new files**: Split into focused learnings
2. **Update references**: Update all cross-references
3. **Archive original**: Move original to `learnings/.archive/`
4. **Generate index**: Create index file linking related learnings
5. **Verify integrity**: Check all references resolve

### Phase 4: Verify Integrity

**Verification Checklist**:
- [ ] All evidence preserved or archived
- [ ] Cross-references updated
- [ ] New files < 50KB
- [ ] No broken links
- [ ] Original archived with timestamp
- [ ] Index file created

## Compaction Strategies

### Strategy 1: Split by Topic

**When to Use**: Large file covers multiple distinct topics

**Steps**:
1. Identify distinct topics (minimum 3 topics)
2. Create new learning file for each topic
3. Move relevant evidence to each file
4. Update cross-references
5. Create index file linking topics

**Example**:

**Before**:
```
learnings/api/patterns.md (80KB)
- REST API patterns
- GraphQL patterns
- WebSocket patterns
- API security
- Rate limiting
```

**After**:
```
learnings/api/rest-patterns.md (25KB)
learnings/api/graphql-patterns.md (20KB)
learnings/api/websocket-patterns.md (18KB)
learnings/api/api-security.md (15KB)
learnings/api/index.md (5KB - links all)
learnings/.archive/api-patterns-2026-01-28.md
```

---

### Strategy 2: Archive Old Evidence

**When to Use**: Many historical evidence entries no longer relevant

**Steps**:
1. Identify evidence older than 6 months with no recent references
2. Move to archive section at bottom of file
3. Keep summary of archived evidence
4. Original evidence available but not in main view

**Example**:

```markdown
## Evidence

[Current evidence entries...]

---

## Archived Evidence (Pre-2025)

<details>
<summary>View archived evidence (25 entries)</summary>

[Older evidence entries...]

</details>
```

---

### Strategy 3: Merge Duplicates

**When to Use**: Multiple evidence entries saying the same thing

**Steps**:
1. Identify similar evidence entries
2. Merge into single comprehensive entry
3. List all sources in merged entry
4. Update insight if needed

**Example**:

**Before**:
```markdown
## Evidence
- [2026-01-15] [project-a]: Need better error messages
- [2026-01-20] [project-b]: Error messages should be user-friendly
- [2026-01-25] [project-c]: Improve error message clarity
```

**After**:
```markdown
## Evidence
- [Multiple sources: project-a, project-b, project-c] Error messages need to be user-friendly and clear. Consistent feedback across 3 projects (Jan 2026).
```

---

### Strategy 4: Summarize Evidence

**When to Use**: > 50 evidence entries making file hard to navigate

**Steps**:
1. Group evidence by theme
2. Create summary section with themes
3. Keep detailed evidence in expandable sections
4. Maintain traceability

**Example**:

```markdown
## Evidence Summary

**Input Validation** (12 entries): Consistently validate at API boundary, use branded types, return structured errors.

**Error Messages** (8 entries): User-friendly messages in UI, technical details in logs.

**Database Errors** (15 entries): Connection retry, transaction rollback, graceful degradation.

<details>
<summary>View detailed evidence (35 entries)</summary>

### Input Validation
- [2026-01-15] [project-a]: ...
- [2026-01-18] [project-b]: ...

### Error Messages
- [2026-01-20] [project-c]: ...

</details>
```

## Agents

### learnings-compactor Agent

**Role**: Autonomous agent that performs compaction operations

**Capabilities**:
- Parse learning files
- Identify compaction opportunities
- Execute compaction strategies
- Update cross-references
- Verify integrity

**Usage**:
```
@learnings-compactor Compact learnings/testing/error-handling.md using split-by-topic strategy
```

**Prompt Template**:
```
You are the learnings-compactor agent. Your task is to compact the learning file at {file_path}.

Current size: {file_size}
Strategy: {strategy}

Steps:
1. Analyze content and identify topics/themes
2. Create new focused learning files
3. Move evidence to appropriate files
4. Update all cross-references
5. Archive original file
6. Create index if needed
7. Verify integrity

Maintain evidence traceability. No information loss.

Output:
- List of new files created
- Archive location
- Updated references
- Integrity verification results
```

## References

### references/compaction-strategy.md

Detailed decision tree for choosing compaction strategy based on file characteristics.

### references/merge-patterns.md

Patterns for merging duplicate evidence and maintaining source attribution.

## Configuration

### .claude/compaction-config.json

```json
{
  "thresholds": {
    "file_size_kb": 50,
    "evidence_count": 50,
    "age_for_archive_days": 180
  },
  "strategies": {
    "prefer_split_over_archive": true,
    "min_topics_for_split": 3,
    "create_index_for_split": true
  },
  "archive": {
    "archive_directory": "learnings/.archive/",
    "include_timestamp": true,
    "keep_original": true
  },
  "verification": {
    "check_references": true,
    "verify_no_broken_links": true,
    "test_search_after_compact": true
  }
}
```

## Usage Examples

### Example 1: Compact Large Error Handling Learning

```bash
# Check file size
ls -lh learnings/testing/error-handling.md
# Output: 75K

# Analyze content
@learnings-compactor Analyze learnings/testing/error-handling.md

# Compact using split strategy
@learnings-compactor Compact learnings/testing/error-handling.md using split-by-topic

# Verify results
ls learnings/testing/
# error-handling-input-validation.md (20KB)
# error-handling-api-errors.md (25KB)
# error-handling-database.md (22KB)
# error-handling-index.md (5KB)

# Check archive
ls learnings/.archive/
# error-handling-2026-01-28.md
```

---

### Example 2: Archive Old Evidence

```bash
# Analyze evidence age
@learnings-compactor Analyze learnings/api/rest-patterns.md --show-age-distribution

# Archive evidence older than 6 months
@learnings-compactor Compact learnings/api/rest-patterns.md using archive-old-evidence

# Verify file size reduced
ls -lh learnings/api/rest-patterns.md
# Before: 65KB
# After: 35KB
```

---

### Example 3: Merge Duplicate Evidence

```bash
# Identify duplicates
@learnings-compactor Analyze learnings/security/auth-patterns.md --detect-duplicates

# Merge similar entries
@learnings-compactor Compact learnings/security/auth-patterns.md using merge-duplicates

# Review merged evidence
cat learnings/security/auth-patterns.md
```

## Story Point Estimation

Compaction work estimates:
- **Analyze file**: 0.05 SP
- **Simple compact** (archive old): 0.1 SP
- **Medium compact** (merge duplicates): 0.2 SP
- **Complex compact** (split by topic): 0.5 SP
- **Verify integrity**: 0.1 SP

**Full compaction workflow**: 0.3-0.8 SP depending on strategy

## Best Practices

1. **Regular Monitoring**: Check file sizes monthly
2. **Proactive Compaction**: Compact before reaching 75KB
3. **Preserve History**: Always archive originals with timestamps
4. **Update References**: Verify all cross-references after compaction
5. **Test Search**: Ensure compacted learnings still searchable
6. **Document Changes**: Log compaction actions in CHANGELOG

## Non-Destructive Rules

- NEVER delete original files (always archive)
- NEVER lose evidence or source attribution
- ALWAYS verify integrity after compaction
- ALWAYS update cross-references
- ALWAYS maintain traceability

## Output Schema

```json
{
  "compaction_result": {
    "original_file": "learnings/testing/error-handling.md",
    "original_size_kb": 75,
    "strategy": "split-by-topic",
    "new_files": [
      "learnings/testing/error-handling-input-validation.md",
      "learnings/testing/error-handling-api-errors.md",
      "learnings/testing/error-handling-database.md"
    ],
    "archive_location": "learnings/.archive/error-handling-2026-01-28.md",
    "index_file": "learnings/testing/error-handling-index.md",
    "total_size_kb": 72,
    "evidence_preserved": 45,
    "references_updated": 12,
    "integrity_checks": {
      "no_broken_links": true,
      "all_evidence_preserved": true,
      "search_verified": true
    }
  }
}
```
