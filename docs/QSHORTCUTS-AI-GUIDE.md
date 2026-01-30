# QShortcuts AI - AI & Architecture Shortcuts

## Overview

QShortcuts AI provides shortcuts for AI system design and prompt engineering: QARCH for designing learning AI systems, QPROMPT for optimizing prompts, and QTRANSFORM for content transformation.

------------------------------------------------------------------------

## Installation

### Step 1: Add the Sparkry Marketplace

```
/plugin marketplace add sparkst/sparkry-claude-skills
```

### Step 2: Install QShortcuts AI

```
/plugin install qshortcuts-ai@sparkry-claude-skills
```

### Step 3: Verify Installation

```
/plugin list
```

------------------------------------------------------------------------

## Available Shortcuts

| Shortcut | Purpose | When to Use |
|----------|---------|-------------|
| **QARCH** | Design AI systems | Architecting LLM/RAG/RLHF systems |
| **QPROMPT** | Optimize prompts | Improving prompt effectiveness |
| **QTRANSFORM** | Transform content | Converting between formats |

------------------------------------------------------------------------

## Usage Examples

### QARCH - Design Learning AI Systems

```
QARCH Design a RAG system for customer support documentation
```

**What it does:**
- Analyzes requirements for AI system
- Designs architecture (embeddings, retrieval, generation)
- Creates ADR (Architecture Decision Record)
- Documents trade-offs and alternatives
- Produces implementation roadmap

**Output:**
- `design/adr.md` - Architecture decision record
- `design/architecture.md` - System design document
- Sequence diagrams and data flows

**Example architectures:**
- RAG (Retrieval-Augmented Generation)
- Fine-tuning pipelines
- RLHF feedback loops
- Multi-agent orchestration
- Evaluation frameworks

------------------------------------------------------------------------

### QPROMPT - Optimize Prompts

```
QPROMPT Improve this prompt for better code review feedback
```

**What it does:**
- Analyzes current prompt structure
- Identifies weaknesses and ambiguities
- Applies prompt engineering best practices
- Tests variations for effectiveness
- Documents the optimization rationale

**Techniques applied:**
- Chain-of-thought prompting
- Few-shot examples
- Role specification
- Output formatting
- Constraint clarity

**Output:** Optimized prompt with explanation

------------------------------------------------------------------------

### QTRANSFORM - Transform Content

```
QTRANSFORM Convert this technical spec into user documentation
```

**What it does:**
- Analyzes source content structure
- Applies transformation rules
- Maintains key information
- Adapts tone and format for target audience

**Common transformations:**
- Technical → User-friendly
- Markdown → HTML/PDF
- Verbose → Concise
- English → Other languages
- Code → Documentation

**Output:** Transformed content in target format

------------------------------------------------------------------------

## Architecture Patterns

QARCH understands these AI patterns:

### RAG (Retrieval-Augmented Generation)
```
Documents → Embeddings → Vector DB → Retrieval → LLM → Response
```

### Fine-Tuning Pipeline
```
Base Model → Training Data → Fine-Tune → Evaluation → Deploy
```

### Multi-Agent System
```
Orchestrator → [Agent 1, Agent 2, ...] → Synthesis → Output
```

------------------------------------------------------------------------

## Prompt Engineering Framework

QPROMPT uses this evaluation framework:

| Dimension | What It Measures |
|-----------|------------------|
| **Clarity** | Is the task unambiguous? |
| **Specificity** | Are constraints well-defined? |
| **Structure** | Is output format specified? |
| **Context** | Is relevant background provided? |
| **Examples** | Are good/bad examples included? |

------------------------------------------------------------------------

## Related Plugins

- **orchestration-workflow** - QRALPH for multi-agent orchestration
- **research-workflow** - For AI research and analysis

------------------------------------------------------------------------

## Use Cases

### Building a Chatbot
```
1. QARCH    →  Design the RAG architecture
2. QPLAN    →  Plan implementation phases
3. QPROMPT  →  Optimize system prompts
4. QCODE    →  Implement components
```

### Improving an AI Feature
```
1. QPROMPT  →  Analyze and optimize prompts
2. QCHECK   →  Verify improvements
3. QDOC     →  Document changes
```

------------------------------------------------------------------------

## Troubleshooting

### QARCH output too generic

Provide more specific requirements:
- Scale expectations (users, queries/day)
- Latency requirements
- Cost constraints
- Data characteristics

### QPROMPT not improving results

Include:
- Current prompt
- Example inputs
- Expected vs actual outputs
- Specific failure cases

------------------------------------------------------------------------

## Questions?

Contact Sparkry.AI support at [sparkry.ai/docs](https://sparkry.ai/docs)
