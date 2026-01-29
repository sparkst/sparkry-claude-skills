# qshortcuts-learning Plugin

Meta-learning and feedback integration tools for continuous improvement and knowledge management in Claude Code.

## What's Included

### Skills

#### 1. **feedback** - Feedback Integration (QFEEDBACK)
Extract user feedback from documents, categorize insights, and integrate into learnings.

**Tools**:
- `comment-extractor.py` - Extract TODO/FIXME/FEEDBACK comments from code
- `feedback-categorizer.py` - Categorize feedback by type and priority
- `learning-integrator.py` - Integrate feedback into learning files
- `feedback-summarizer.py` - Generate feedback summary reports

**References**:
- `feedback-taxonomy.md` - Complete categorization system
- `integration-patterns.md` - Patterns for integrating feedback
- `learning-formats.md` - Standard learning file formats

---

#### 2. **learn** - Learning Retrieval (QLEARN)
Retrieve relevant learnings for active task based on context analysis.

**Tools**:
- `learning-search.py` - Search and rank learnings by relevance

**References**:
- `search-strategies.md` - Search algorithms and strategies
- `relevance-scoring.md` - Relevance scoring formulas

---

#### 3. **compact** - Learning Compaction (QCOMPACT)
Consolidate learnings when files exceed 50KB threshold.

**Agents**:
- `learnings-compactor` - Autonomous compaction agent

**References**:
- `compaction-strategy.md` - Decision tree for compaction strategies
- `merge-patterns.md` - Patterns for merging duplicate evidence

---

#### 4. **skill-builder** - Skill Builder (QSKILL)
Create new agent+skill complex with tools and references.

**Agents**:
- `skill-architect` - High-level skill design agent

**Tools**:
- `skill-generator.py` - Generate complete skill structure
- `tool-stub-generator.py` - Generate Python tool stubs

**References**:
- `skill-template.md` - Complete SKILL.md template
- `agent-patterns.md` - Common agent patterns
- `tool-patterns.md` - Python tool patterns

## Installation

### Via Claude Code CLI

```bash
claude plugins install qshortcuts-learning
```

### Manual Installation

1. Clone or download this plugin
2. Copy to your Claude plugins directory:
   ```bash
   cp -r qshortcuts-learning ~/.claude/plugins/qshortcuts-learning
   ```
3. Reload Claude Code

## Quick Start

### QFEEDBACK - Extract and Integrate Feedback

Process feedback from code comments and integrate into learnings:

```bash
# Extract feedback from project
python skills/feedback/scripts/comment-extractor.py projects/my-project/

# Categorize feedback
python skills/feedback/scripts/feedback-categorizer.py extracted-feedback.json

# Integrate into learnings
python skills/feedback/scripts/learning-integrator.py categorized-feedback.json

# Generate summary
python skills/feedback/scripts/feedback-summarizer.py learnings/
```

**Use Cases**:
- Process PR review comments
- Extract TODO/FIXME from codebase
- Integrate meeting feedback
- Track improvement patterns

---

### QLEARN - Retrieve Relevant Learnings

Find learnings relevant to your current task:

```bash
# Keyword search
python skills/learn/scripts/learning-search.py \
  --keywords "error handling,validation" \
  --domain testing \
  --limit 5

# Natural language query
python skills/learn/scripts/learning-search.py \
  --query "How to handle database connection errors?"

# Recent learnings
python skills/learn/scripts/learning-search.py --recent --limit 10
```

**Use Cases**:
- Find patterns before implementing
- Retrieve debugging strategies
- Check for known anti-patterns
- Discover related learnings

---

### QCOMPACT - Consolidate Large Learnings

Compact learning files exceeding 50KB:

```bash
# Analyze large file
@learnings-compactor Analyze learnings/testing/error-handling.md

# Compact using split strategy
@learnings-compactor Compact learnings/testing/error-handling.md using split-by-topic

# Archive old evidence
@learnings-compactor Compact learnings/api/patterns.md using archive-old-evidence
```

**Use Cases**:
- Split large files by topic
- Archive historical evidence
- Merge duplicate entries
- Optimize for searchability

---

### QSKILL - Create New Skills

Build new skills with complete tooling:

```bash
# Design skill
@skill-architect Design skill for automated test reporting

# Generate skill structure
python skills/skill-builder/scripts/skill-generator.py \
  --name "Test Reporter" \
  --description "Generate test reports with coverage" \
  --domain testing \
  --tools "coverage-analyzer.py,report-generator.py" \
  --references "report-template.md" \
  --trigger QREPORT \
  --output skills/testing/test-reporter/SKILL.md

# Generate tool stubs
python skills/skill-builder/scripts/tool-stub-generator.py \
  --name "coverage-analyzer" \
  --description "Analyze test coverage" \
  --skill-dir skills/testing/test-reporter \
  --generate-test
```

**Use Cases**:
- Create custom skills
- Scaffold new agents
- Generate tool templates
- Build skill libraries

## Workflow Integration

### Continuous Learning Loop

```
┌─────────────────────────────────────────────────────┐
│                 LEARNING LOOP                        │
│                                                      │
│  1. WORK                                            │
│     ├─ Write code                                   │
│     ├─ Add TODO/FIXME comments                      │
│     └─ Receive feedback                             │
│                                                      │
│  2. QFEEDBACK (Weekly)                              │
│     ├─ Extract feedback from codebase               │
│     ├─ Categorize by priority and domain            │
│     └─ Integrate into learnings                     │
│                                                      │
│  3. QLEARN (Before Tasks)                           │
│     ├─ Search relevant learnings                    │
│     ├─ Review patterns and anti-patterns            │
│     └─ Apply learnings to implementation            │
│                                                      │
│  4. QCOMPACT (Monthly)                              │
│     ├─ Identify large learning files                │
│     ├─ Compact using appropriate strategy           │
│     └─ Verify integrity and searchability           │
│                                                      │
│  5. QSKILL (As Needed)                              │
│     ├─ Identify skill gaps                          │
│     ├─ Design new skills                            │
│     └─ Generate and implement                       │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Configuration

### Learning Directory Structure

```
learnings/
├── testing/
│   ├── error-handling.md
│   ├── test-patterns.md
│   └── coverage-strategies.md
├── security/
│   ├── auth-patterns.md
│   └── vulnerability-prevention.md
├── api/
│   ├── rest-patterns.md
│   └── error-responses.md
└── .archive/
    └── [archived learnings]
```

### Feedback Configuration

`.claude/feedback-config.json`:

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

### Learning Search Configuration

`.claude/learning-config.json`:

```json
{
  "search": {
    "learning_directory": "learnings/",
    "default_limit": 5,
    "min_relevance_score": 30,
    "boost_recent_days": 30
  },
  "scoring": {
    "keyword_weight": 0.4,
    "domain_weight": 0.3,
    "activity_weight": 0.2,
    "recency_weight": 0.1
  }
}
```

## Usage Examples

### Example 1: Weekly Feedback Processing

```bash
# Monday morning: Process last week's feedback

# Extract from entire codebase
python skills/feedback/scripts/comment-extractor.py projects/ > feedback-raw.json

# Categorize
python skills/feedback/scripts/feedback-categorizer.py feedback-raw.json > feedback-categorized.json

# Integrate
python skills/feedback/scripts/learning-integrator.py feedback-categorized.json

# Review summary
python skills/feedback/scripts/feedback-summarizer.py learnings/
cat feedback-summary.md

# Commit updated learnings
git add learnings/
git commit -m "chore: integrate weekly feedback into learnings"
```

---

### Example 2: Pre-Implementation Learning Check

```bash
# Before implementing API error handling

# Search relevant learnings
python skills/learn/scripts/learning-search.py \
  --domain api \
  --keywords "error,handling,response" \
  --activity implementation \
  --limit 5 > relevant-learnings.json

# Review top learnings
cat relevant-learnings.json | jq '.learnings[] | {title, score, insight}'

# Read detailed learnings
cat learnings/api/error-responses.md

# Apply patterns to implementation
```

---

### Example 3: Monthly Learning Maintenance

```bash
# Check for large files
find learnings/ -name "*.md" -size +50k

# Compact each large file
for file in $(find learnings/ -name "*.md" -size +50k); do
  echo "Analyzing $file..."
  @learnings-compactor Analyze "$file"
  # Review suggestions and apply appropriate strategy
done

# Verify integrity
@learnings-compactor Verify all compacted learnings

# Commit changes
git add learnings/ learnings/.archive/
git commit -m "chore: monthly learning compaction"
```

---

### Example 4: Create Custom Skill

```bash
# Need a skill for analyzing API performance

# Design
@skill-architect Design skill for API performance analysis

# Generate structure
python skills/skill-builder/scripts/skill-generator.py \
  --name "API Performance Analyzer" \
  --description "Analyze API endpoint performance and identify bottlenecks" \
  --domain performance \
  --tools "latency-analyzer.py,bottleneck-detector.py,report-generator.py" \
  --references "performance-patterns.md,optimization-guide.md" \
  --trigger QPERF \
  --output skills/performance/api-analyzer/SKILL.md

# Generate tools
for tool in latency-analyzer bottleneck-detector report-generator; do
  python skills/skill-builder/scripts/tool-stub-generator.py \
    --name "$tool" \
    --skill-dir skills/performance/api-analyzer \
    --generate-test
done

# Implement tool logic
# vim skills/performance/api-analyzer/scripts/latency-analyzer.py

# Test
python skills/performance/api-analyzer/tests/test_latency_analyzer.py

# Document and commit
git add skills/performance/api-analyzer/
git commit -m "feat: add API performance analyzer skill"
```

## Best Practices

### Feedback Integration
1. **Regular Extraction**: Run weekly to capture feedback early
2. **Clear Categories**: Use consistent taxonomy for better analysis
3. **Link Context**: Always include source and context
4. **Prioritize Actions**: Focus on P0/P1 feedback first
5. **Review Patterns**: Look for recurring themes

### Learning Retrieval
1. **Search Before Implementing**: Always check learnings before starting
2. **Use Specific Keywords**: More specific yields better results
3. **Combine Strategies**: Use multiple search dimensions
4. **Update Learnings**: Update if learning is outdated
5. **Add Evidence**: When applying learning, add evidence

### Learning Compaction
1. **Regular Monitoring**: Check file sizes monthly
2. **Proactive Compaction**: Compact before reaching 75KB
3. **Preserve History**: Always archive originals
4. **Update References**: Verify cross-references after compaction
5. **Test Search**: Ensure compacted learnings still searchable

### Skill Building
1. **Start with Design**: Use skill-architect before generating
2. **Follow Patterns**: Use existing skills as examples
3. **Include Examples**: Add concrete usage examples
4. **Write Tests**: Generate and implement tests
5. **Document Tools**: Clear docstrings and usage

## Story Point Estimation

### QFEEDBACK
- Extract feedback (small project): 0.05 SP
- Categorize feedback: 0.1 SP
- Integrate into learnings: 0.2 SP per file
- Generate summary: 0.1 SP
- **Full workflow**: 0.5-1 SP

### QLEARN
- Simple search: 0.05 SP
- Complex search: 0.1 SP
- Review and apply: 0.1-0.2 SP per learning
- **Typical workflow**: 0.2-0.5 SP

### QCOMPACT
- Analyze file: 0.05 SP
- Simple compact (archive): 0.1 SP
- Medium compact (merge): 0.2 SP
- Complex compact (split): 0.5 SP
- **Full workflow**: 0.3-0.8 SP

### QSKILL
- Design skill: 0.3 SP
- Generate structure: 0.1 SP
- Implement tools: 0.2-1 SP per tool
- Create references: 0.1 SP per reference
- **Full skill creation**: 1-3 SP

## Troubleshooting

### QFEEDBACK Issues

**Problem**: No feedback extracted from codebase

**Solution**: Check file types and patterns in config:
```bash
# Verify patterns
cat .claude/feedback-config.json

# Try specific file
python skills/feedback/scripts/comment-extractor.py path/to/file.ts
```

---

**Problem**: Feedback categorized incorrectly

**Solution**: Review and adjust category keywords in taxonomy:
```bash
# Review taxonomy
cat skills/feedback/references/feedback-taxonomy.md

# Recategorize with adjusted keywords
python skills/feedback/scripts/feedback-categorizer.py feedback.json
```

### QLEARN Issues

**Problem**: Search returns no results

**Solution**: Lower minimum score or broaden search:
```bash
# Lower threshold
python skills/learn/scripts/learning-search.py \
  --keywords "error" \
  --min-score 20

# Broaden domain
python skills/learn/scripts/learning-search.py \
  --keywords "error" \
  # without --domain filter
```

---

**Problem**: Search results not relevant

**Solution**: Use more specific keywords or add domain filter:
```bash
# More specific
python skills/learn/scripts/learning-search.py \
  --keywords "database connection error retry" \
  --domain database
```

### QCOMPACT Issues

**Problem**: Compaction creates broken references

**Solution**: Run verification and fix manually:
```bash
# Verify compaction
@learnings-compactor Verify learnings/testing/error-handling-*.md

# Check for broken links
grep -r "learnings/testing/error-handling.md" learnings/
```

### QSKILL Issues

**Problem**: Generated tool stub missing functionality

**Solution**: Tool stubs are templates - implement logic:
```bash
# Review tool stub
cat skills/my-skill/scripts/my-tool.py

# Implement process() function
vim skills/my-skill/scripts/my-tool.py
```

## Contributing

This plugin is part of the Sparkry.ai Claude Code ecosystem. For issues, enhancements, or questions:

- **Email**: skills@sparkry.ai
- **License**: MIT

## Changelog

### v1.0.0 (2026-01-28)

- Initial release
- 4 core skills (feedback, learn, compact, skill-builder)
- Feedback extraction and integration workflow
- Learning search and retrieval
- Learning compaction strategies
- Skill generation tools

## License

MIT License - see LICENSE file for details.

---

**Build learning systems that get smarter over time!**
