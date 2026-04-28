---
name: Content Review Pipeline
description: Multi-lens content review that runs any document through 5 target reader personas, UX information architecture analysis, and fact-reference validation. Produces a findings report and a revised article with all fixes applied. Use this skill whenever the user says /qreview, QREVIEW, asks to "review this content", "check this article", "review before publishing", or wants comprehensive content quality analysis. Also trigger when user mentions "reader perspective", "target audience review", or "content readiness check".
version: 1.0.0
trigger: QREVIEW
tools: [fact-reference-validator.py]
mcp_tools: [ux-knowledge]
claude_tools: Read, Write, Edit, Bash, Grep, Glob, Agent
---

# QREVIEW — Multi-Lens Content Review Pipeline

## Purpose

Review any content through three parallel lenses and produce two deliverables:
1. **Findings Report** — structured review with all issues, organized by lens and priority
2. **Revised Article** — the original content with all findings applied as fixes

This skill works on any written content: articles, emails, training materials, deliverables, presentations, proposals, coaching documents.

## Invocation

```
/qreview <file_path>
```

If no file path is given, ask the user which file to review.

## Pipeline Overview

```
Input Content
    │
    ├──→ Lens 1: Target Reader Personas (5 simulated readers)
    │       → Each reader produces 0-5 findings
    │
    ├──→ Lens 2: Information Architecture & Readability (ux-knowledge MCP)
    │       → Structure, hierarchy, scanability, cognitive load
    │
    └──→ Lens 3: Fact-Reference Validation (fact-reference-validator.py)
            → Unreferenced claims, missing sources
    │
    ▼
Deduplicate & Prioritize Findings
    │
    ├──→ Output 1: Findings Report (markdown)
    └──→ Output 2: Revised Article (markdown with all fixes applied)
```

## Step 1: Read and Classify the Content

Read the input file. Determine:

- **Content type**: article, email, training material, deliverable, presentation, proposal, coaching doc, internal memo
- **Apparent audience**: who this was written for (executives, technical team, general public, trainees, clients)
- **Platform**: Substack, LinkedIn, internal doc, email, slide deck, handout
- **Length**: word count
- **Purpose**: inform, persuade, teach, report, propose

This classification drives persona selection in Step 2.

## Step 2: Generate 5 Target Reader Personas

Based on the content classification, generate 5 reader personas that represent the real audience for this specific piece. Each persona has a name, role, reading style, and what they care about.

The personas should create tension — they should NOT all agree. A good review panel has readers who want different things, because real audiences are diverse.

### Persona Generation Template

For each persona, define:

```
Name: [First name, memorable]
Role: [Job title or archetype]
Reading Style: [How they consume content — skims, reads deeply, jumps to conclusions, etc.]
Cares About: [What they're looking for — actionable takeaways, proof, entertainment, etc.]
Impatient With: [What makes them stop reading]
Review Focus: [The specific lens this reader brings]
```

### Persona Selection Heuristics

**For Substack articles / blog posts:**
1. The Skimmer — busy professional, reads headlines and bold text only, wants the takeaway in 10 seconds
2. The Skeptic — experienced practitioner, looking for proof and specificity, allergic to vague claims
3. The Newcomer — interested but unfamiliar with the domain, needs jargon explained, wants to feel smart not dumb
4. The Sharer — reads to find things worth reposting, looking for quotable lines and novel framings
5. The Deep Reader — reads every word, notices inconsistencies, cares about craft and flow

**For client deliverables / proposals:**
1. The Decision Maker — VP/Director, skims for bottom line and risk, wants clear recommendation
2. The Implementer — the person who has to actually do the work, looking for gaps and feasibility
3. The Skeptical Stakeholder — has been burned before, looking for what could go wrong
4. The Finance Reviewer — looking for ROI, cost, timeline, resource requirements
5. The Legal/Compliance Eye — scanning for risk language, commitments, regulatory exposure

**For training materials / handouts:**
1. The Eager Learner — excited, absorbs everything, wants depth and examples
2. The Reluctant Attendee — doesn't want to be here, needs to be convinced this matters
3. The Expert in the Room — already knows most of this, looking for what's new or wrong
4. The Note-Taker — wants structured, reference-friendly content they can use later
5. The Hands-On Learner — skips theory, jumps to exercises and examples

**For internal emails / memos:**
1. The Inbox Zero Person — 200 unread emails, gives you 5 seconds to prove relevance
2. The Action Finder — looking only for "what do I need to do"
3. The Context Builder — wants to understand why, not just what
4. The Forward-to-My-Team Person — evaluating whether this is worth sharing
5. The Detail Checker — reads carefully, catches inconsistencies and missing info

**For mixed or unclear content types**, select the 5 that best represent the likely readership. Always include at least one skeptic and one skimmer — every audience has both.

### How Each Persona Reviews

For each persona, read the content through their eyes and produce:

```markdown
### [Persona Name] — [Role]

**Overall Reaction**: [1-2 sentences — would they keep reading? Would they act on it?]

**Findings**:

1. **[P0/P1/P2]** [Location: paragraph/section] — [Issue description]
   - **Why it matters to this reader**: [explanation]
   - **Suggested fix**: [specific revision]

2. ...

**What Works Well**: [1-2 things this reader would appreciate]
```

Priority levels:
- **P0**: Reader stops reading, loses trust, or misunderstands something critical
- **P1**: Reader is confused, annoyed, or loses momentum
- **P2**: Reader notices something off but keeps going

Each persona should produce between 0-5 findings. Not every persona will find issues — that's fine. Don't force findings that aren't there.

## Step 3: UX Information Architecture Analysis

Use the `mcp__ux-knowledge__analyze_information_architecture` tool to evaluate the content's structure.

Call the tool with:
- `site_structure`: Describe the document's structure — heading hierarchy, section order, list usage, callout placement
- `user_goals`: Describe what readers are trying to accomplish with this content (derived from Step 1 classification)
- `issues`: Any structural problems already noticed by personas in Step 2

Then use `mcp__ux-knowledge__review_usability` with:
- `description`: Describe the content as a "reading experience" — flow, cognitive load, information density, scanability

From both tools, extract findings in this format:

```markdown
## Lens 2: Information Architecture & Readability

### Structure Analysis
[Summary of IA tool findings]

### Readability Analysis
[Summary of usability tool findings]

### Findings:

1. **[P0/P1/P2]** [Location] — [Issue]
   - **Impact**: [How this affects comprehension or usability]
   - **Suggested fix**: [Specific structural revision]
```

Focus the UX analysis on:
- **Heading hierarchy**: Do headings tell a story when read alone? Can you skim headings and get the point?
- **Paragraph length**: Walls of text? Paragraphs over 4 sentences?
- **List usage**: Should any prose be a list? Are lists too long (>7 items)?
- **Scanability**: Bold text, callouts, visual anchors — can a skimmer get value?
- **Cognitive load**: Too many concepts introduced at once? Missing transitions?
- **Front-loading**: Does each section lead with the key point or bury it?
- **Redundancy**: Same point made in multiple places?

## Step 4: Fact-Reference Validation

Run the fact-reference-validator tool:

```bash
python3 /Users/travis/SGDrive/dev/cardinal-health/.claude/skills/writing/tools/fact-reference-validator.py <input_file> --verbose
```

Parse the output and format findings:

```markdown
## Lens 3: Fact-Reference Validation

**Claims detected**: [N]
**Referenced**: [N]
**Unreferenced**: [N]
**P0 violations**: [N] (BLOCKING)
**P1 violations**: [N] (recommended)

### Findings:

1. **[P0]** Line [N] — [Claim text]
   - **Claim type**: [research_statistic / percentage_statistic / etc.]
   - **Suggested fix**: Add source link — search for "[search query]"

2. ...
```

If the validator is unavailable or errors, do a manual scan for:
- Statistics without sources (percentages, dollar amounts, "X% of Y")
- Attributed claims without links ("According to McKinsey...")
- Specific company results without references

## Step 5: Deduplicate & Prioritize

Multiple lenses may flag the same issue. Merge duplicates, keeping the highest priority and the most actionable fix suggestion.

Sort all findings:
1. P0 findings first (grouped)
2. P1 findings second
3. P2 findings last

Within each priority, order by location in the document (top to bottom).

## Step 6: Write the Findings Report

Save to: `<input_file_dir>/qreview-findings-<date>.md`

Use this structure:

```markdown
# QREVIEW Findings — [Article Title]

> **Reviewed**: [date]
> **Content**: [file path]
> **Type**: [content type]
> **Word Count**: [N]
> **Total Findings**: [N] (P0: [N], P1: [N], P2: [N])

---

## Executive Summary

[3-5 sentences: overall quality assessment, biggest issues, what works well]

---

## Findings by Priority

### P0 — Must Fix Before Publishing

1. **[Source: Persona Name / IA Analysis / Fact-Check]** [Location] — [Issue]
   - **Suggested fix**: [specific revision]

### P1 — Strongly Recommended

1. ...

### P2 — Nice to Have

1. ...

---

## Reader Persona Reactions

### [Persona 1 Name] — [Role]
**Overall Reaction**: [1-2 sentences]
**What Works**: [brief]

### [Persona 2 Name] — [Role]
...

[All 5 personas]

---

## Information Architecture Assessment

[Summary of structural analysis]

---

## Fact-Reference Validation

[Summary of claim validation]
```

## Step 7: Write the Revised Article

Save to: `<input_file_dir>/qreview-revised-<original_filename>`

Apply ALL P0 and P1 findings to produce a revised version. For P2 findings, apply only those that are quick wins (< 1 sentence change).

Rules for the revised article:
- Preserve the author's voice and style — fix issues without rewriting personality
- Mark significant changes with HTML comments so the author can review: `<!-- QREVIEW: [what changed and why] -->`
- For fact-reference P0 violations where you can't find the source URL, insert a placeholder: `[SOURCE NEEDED: search for "query"]`
- Do NOT add new content, sections, or arguments — only fix what was flagged
- Do NOT remove content unless it was flagged as redundant by multiple lenses

## Output Summary

After both files are written, present a summary to the user:

```
QREVIEW Complete — [Article Title]

Findings: [N] total (P0: [N], P1: [N], P2: [N])
Personas: [List 5 names and roles]

Top 3 Issues:
1. [Most critical finding]
2. [Second]
3. [Third]

Files:
- Findings: [path to findings file]
- Revised: [path to revised file]
```

## Edge Cases

- **Very short content** (<200 words): Skip IA analysis, reduce to 3 personas
- **Code-heavy content**: Skip fact-reference validation on code blocks
- **Content with no factual claims**: Note "No factual claims detected" in Lens 3, skip that section
- **Multiple files**: If user provides a directory or glob, ask them to pick one file. QREVIEW works on one document at a time.
- **Non-markdown content**: If the input is .docx, .txt, or .html, read it and work with the text content. Outputs are always markdown.
