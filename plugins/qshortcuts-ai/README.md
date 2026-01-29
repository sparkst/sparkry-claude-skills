# qshortcuts-ai Plugin

AI architecture and prompt engineering skills for Claude Code - design learning systems, optimize prompts, and transform content.

## What's Included

### Skills

- **qarch** - Design learning AI systems (personas, RLHF, RAG)
  - RAG validator
  - Feedback loop checker
  - Persona schema generator
  - Agents: architecture-advisor, pe-designer

- **qprompt** - Optimize prompts for token efficiency and persona consistency
  - Token counter
  - Prompt optimizer
  - Persona validator

- **qtransform** - Design content transformation for platforms
  - Platform validator
  - Tone analyzer
  - Feedback learner

## Installation

### Via Claude Code CLI

```bash
claude plugins install qshortcuts-ai
```

### Manual Installation

1. Clone or download this plugin
2. Copy to your Claude plugins directory:
   ```bash
   cp -r qshortcuts-ai ~/.claude/plugins/qshortcuts-ai
   ```
3. Reload Claude Code

## Quick Start

### QARCH: Design Learning AI Systems

Design AI systems with RAG, RLHF, or persona-based architectures:

```
QARCH: Design a RAG system for product documentation with feedback loops
```

The QARCH workflow will:
- Analyze requirements for learning AI systems
- Design RAG/RLHF architecture with retrieval strategies
- Generate persona schemas for multi-agent systems
- Validate feedback loops for continuous improvement
- Output: Architecture docs, persona schemas, validation reports

**Tools**:
- `rag-validator.py` - Validate RAG retrieval quality and coverage
- `feedback-loop-checker.py` - Verify RLHF feedback loops are complete
- `persona-schema-gen.py` - Generate persona schemas from requirements

**Agents**:
- **architecture-advisor** - System design, scalability, patterns
- **pe-designer** - Architecture options, trade-offs, feasibility

### QPROMPT: Optimize Prompts

Optimize prompts for token efficiency and persona consistency:

```
QPROMPT: Analyze and optimize this prompt for token efficiency
```

The QPROMPT workflow will:
- Count tokens in prompt and expected output
- Identify redundancy and verbose patterns
- Optimize for efficiency while preserving intent
- Validate persona alignment
- Output: Optimized prompt, token savings report, persona score

**Tools**:
- `token-counter.py` - Count tokens in text (Claude tokenizer)
- `prompt-optimizer.py` - Reduce tokens while preserving meaning
- `persona-validator.py` - Check prompt alignment with persona patterns

### QTRANSFORM: Transform Content for Platforms

Design content transformations for multiple platforms:

```
QTRANSFORM: Transform this article for LinkedIn, Twitter, and email
```

The QTRANSFORM workflow will:
- Analyze source content structure and tone
- Apply platform-specific constraints (length, formatting)
- Transform tone for target audience
- Learn from feedback for future transformations
- Output: Platform-optimized versions, transformation report

**Tools**:
- `platform-validator.py` - Validate platform requirements (LinkedIn, Twitter, etc.)
- `tone-analyzer.py` - Analyze tone consistency across transformations
- `feedback-learner.py` - Learn from feedback to improve future transformations

## Workflow Integration

### QARCH Use Cases

- Designing RAG systems for knowledge bases
- Building RLHF pipelines for model fine-tuning
- Creating multi-persona agent systems
- Architecting feedback loops for learning systems

### QPROMPT Use Cases

- Reducing token costs in production prompts
- Optimizing system prompts for Claude models
- Ensuring persona consistency in agent prompts
- Refactoring verbose prompts

### QTRANSFORM Use Cases

- Multi-platform content distribution
- Adapting tone for different audiences
- Structural transformation (not just truncation)
- Learning optimal transformation patterns

## Story Point Estimation

- **QARCH (simple RAG)**: 3-5 SP
- **QARCH (complex RLHF pipeline)**: 8-13 SP
- **QPROMPT (single prompt)**: 0.5-1 SP
- **QPROMPT (system-wide optimization)**: 3-5 SP
- **QTRANSFORM (2-3 platforms)**: 2-3 SP
- **QTRANSFORM (5+ platforms with learning)**: 5-8 SP

**Reference**: `docs/project/PLANNING-POKER.md`

## Best Practices

### 1. QARCH: Start with Requirements

**❌ Don't**:
```bash
QARCH: Build a RAG system  # Too vague
```

**✅ Do**:
```bash
QARCH: Design RAG system for 10K docs, <500ms retrieval, semantic + keyword hybrid search
```

### 2. QPROMPT: Measure Token Savings

**❌ Don't**:
```bash
QPROMPT: Make this prompt shorter  # No target
```

**✅ Do**:
```bash
QPROMPT: Optimize this 1500 token prompt to <1000 tokens while preserving intent
```

### 3. QTRANSFORM: Specify Platform Constraints

**❌ Don't**:
```bash
QTRANSFORM: Post this everywhere  # No constraints
```

**✅ Do**:
```bash
QTRANSFORM: Transform for LinkedIn (25-word hook), Twitter (280 char), Email (single CTA)
```

## Usage Examples

### Example 1: RAG System Design (QARCH)

**Task**: Design a RAG system for technical documentation

```bash
QARCH: Design RAG system for 50K technical docs, support semantic + keyword search, <500ms p95 latency, feedback loop for relevance scoring

# Workflow executes:
# 1. Analyze requirements (corpus size, latency, search types)
# 2. Design retrieval architecture (embedding model, vector DB, hybrid search)
# 3. Design feedback loop (user ratings, click-through, dwell time)
# 4. Generate validation criteria
# 5. Output: Architecture diagram, persona schemas, validation plan
```

**Estimated effort**: 5-8 SP (2-3 days)

### Example 2: Prompt Optimization (QPROMPT)

**Task**: Optimize verbose system prompt

```bash
QPROMPT: Optimize this 2000 token system prompt to <1200 tokens

# Workflow executes:
# 1. Count tokens (input: 2000 tokens)
# 2. Identify redundancy (repeated instructions, verbose examples)
# 3. Optimize (condense examples, remove redundancy, tighten language)
# 4. Validate persona alignment (ensure voice preserved)
# 5. Output: Optimized prompt (1150 tokens), savings report (42.5% reduction)
```

**Estimated effort**: 1-2 SP (1-2 hours)

### Example 3: Multi-Platform Transformation (QTRANSFORM)

**Task**: Transform long-form article for social media

```bash
QTRANSFORM: Transform 2000-word Substack article for LinkedIn, Twitter, BlueSky

# Workflow executes:
# 1. Analyze source (structure, key points, tone)
# 2. Apply platform constraints:
#    - LinkedIn: 25-word hook, professional tone, 1900 words
#    - Twitter: 280 char, conversational, lead with insight
#    - BlueSky: 300 char, casual, thread format
# 3. Transform tone (maintain core message, adapt style)
# 4. Validate constraints (length, formatting, tone)
# 5. Output: 3 platform-optimized versions, transformation report
```

**Estimated effort**: 2-3 SP (2-3 hours)

## Advanced Usage

### QARCH: Multi-Agent Persona Systems

Design complex multi-agent systems with persona hierarchies:

```bash
QARCH: Design 3-layer persona system (base voice → content type → platform) for writing assistant
```

Output:
- Persona schema (YAML)
- Layering logic
- Fallback strategies
- Validation criteria

### QPROMPT: Persona Consistency Analysis

Analyze prompt consistency across agent fleet:

```bash
QPROMPT: Analyze persona consistency across 10 agent prompts in .claude/agents/
```

Output:
- Consistency scores per agent
- Divergence patterns
- Recommendations for alignment

### QTRANSFORM: Feedback-Driven Learning

Use feedback to improve transformation quality:

```bash
QTRANSFORM: Transform content for LinkedIn, learn from engagement metrics in feedback.json
```

Output:
- Transformation with learned patterns
- Engagement prediction
- Recommended adjustments

## Configuration

### CLAUDE.md Integration

This plugin works with the CLAUDE.md guidelines for:
- Requirements discipline (REQ IDs)
- Story point estimation
- Quality gates

### Tool Dependencies

All Python tools require:
- Python 3.8+
- Standard library only (no external dependencies for portability)

## Contributing

This plugin is part of the Sparkry.ai Claude Code ecosystem. For issues, enhancements, or questions:

- **Email**: skills@sparkry.ai
- **License**: MIT

## Changelog

### v1.0.0 (2026-01-28)

- Initial release
- 3 skills: QARCH, QPROMPT, QTRANSFORM
- 9 Python tools
- 2 agents (architecture-advisor, pe-designer)
- Story point estimation guide
- Best practices and usage examples

## License

MIT License - see LICENSE file for details.

---

**Design smarter AI systems with QARCH, QPROMPT, and QTRANSFORM!**
