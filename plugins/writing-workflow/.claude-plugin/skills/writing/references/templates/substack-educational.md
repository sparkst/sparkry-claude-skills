# Substack Educational Article Template

## Structure

### 1. Title
- Clear, specific promise
- 8-12 words optimal
- Include key benefit or insight

Examples:
- "How RAG Actually Works: A Visual Guide"
- "The Three Pillars of Effective System Design"
- "Why Your API Tests Are Probably Wrong"

### 2. Opening (BLUF - Bottom Line Up Front)

**First sentence**: Hook with relatable scenario or key insight

**Paragraph 1-2**: The main point up front
- What you'll learn
- Why it matters to reader
- Quick preview of structure

Example:
```
You've probably used AI chatbots that "remember" context from earlier in
the conversation. That's RAG at work.

RAG (Retrieval-Augmented Generation) is how AI systems search through
documents to answer questions. Instead of memorizing everything, they
look it up just-in-time—like you searching Google before answering
a question.

In this guide, we'll break down exactly how RAG works, why it's better
than alternatives, and where it breaks down. No jargon, just clear
explanations with diagrams.
```

### 3. Core Content Structure

Use 3-5 main sections, each building on the last:

```markdown
## 1. [Core Concept Name]

[One-paragraph overview]

[Explanation with example]

[Visual/diagram if helpful]

[Key takeaway]

## 2. [Building on Concept 1]

[Continue pattern...]

## 3. [Advanced/Nuanced Point]

[Continue pattern...]
```

### 4. Section Pattern

Each section follows:
1. **Concept introduction**: What it is in plain language
2. **Why it matters**: Connection to reader's goals
3. **How it works**: Step-by-step or component breakdown
4. **Example**: Concrete illustration
5. **Transition**: Set up next section

### 5. Visual Elements

Include for each framework or multi-step process:
- ASCII art diagrams
- Box diagrams showing relationships
- Flow charts for processes

### 6. Application Section

Near the end, show practical usage:

```markdown
## How to Use This in Practice

Now that you understand [concept], here's how to apply it:

**Use case 1**: [Specific scenario]
- [Step or consideration]
- [Step or consideration]

**Use case 2**: [Another scenario]
- [Step or consideration]

**When NOT to use this**: [Limitations]
```

### 7. Closing

**Summary**: Key points in 2-3 bullets

**Hope/Encouragement**: End on uplifting note connected to reader's goals

**Call to action**: Soft ask (subscribe, comment, share)

Example:
```
## Key Takeaways

- RAG lets AI systems search documents instead of memorizing everything
- It works in three steps: retrieve, rank, generate
- Best for dynamic data; less useful for reasoning tasks

The next time you build an AI feature that needs access to documents,
you'll know exactly how to structure it. That's a superpower.

If this was helpful, subscribe for more AI explainers every Thursday.
```

## Length Targets

- **Quick explainer**: 800-1200 words
- **Standard educational**: 1200-2000 words
- **Deep dive**: 2000-3000 words

Optimize for clarity over length.

## Tone Checklist

- [ ] Empathetic and warm
- [ ] Technical terms explained simply
- [ ] Examples before abstractions
- [ ] Encouraging, not condescending
- [ ] BLUF structure (key point up front)
- [ ] Scannable with clear headers
- [ ] Ends on hopeful/empowering note

## Common Patterns

### Introducing Technical Terms

❌ "RAG utilizes vector embeddings for semantic search"
✅ "Think of RAG like a search engine for your documents—it finds relevant information using meaning, not just keywords"

### Explaining How Things Work

1. **Analogy first**: "It's like [familiar thing]..."
2. **Simple description**: "Here's what actually happens..."
3. **Technical detail**: "Under the hood, it works by..."

### Transitions Between Sections

- "Here's where it gets interesting..."
- "This brings us to the key question..."
- "Now that we understand X, let's look at Y..."
- "You might be wondering..."

## Full Example Outline

```markdown
# How RAG Actually Works: A Visual Guide

[BLUF opening: relatable hook + main insight + article preview]

## 1. The Problem RAG Solves

[Why AI systems need to look things up]
[Limitations of pure generation]
[Example: chatbot that needs current data]

## 2. How RAG Works (Three Steps)

[Step 1: Retrieve - Finding relevant documents]
[Step 2: Rank - Sorting by relevance]
[Step 3: Generate - Using context to answer]
[Diagram showing the flow]

## 3. When RAG Works Best (And When It Doesn't)

[Good use cases]
[Bad use cases]
[Tradeoffs to consider]

## 4. Building Your First RAG System

[Quick practical guide]
[Tools needed]
[Common pitfalls]

## Key Takeaways

[3 bullet summary]
[Hopeful closing]
[Soft CTA]
```
