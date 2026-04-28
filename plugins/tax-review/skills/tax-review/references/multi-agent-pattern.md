# Multi-Agent Validation Pattern

This reference describes how to dispatch parallel subagents for tax document review. The pattern has been validated in practice to catch errors that single-pass extraction misses.

## Why Multi-Agent

Tax documents are high-stakes, error-prone, and full of edge cases. Single-pass reading by one agent (or by you directly) leaves several failure modes uncovered:

1. **OCR / image rotation errors** — rotated images, low-contrast photos, and PDF artifacts cause digit misreads. A single reader can confidently output a wrong number.
2. **Math errors** — totals that don't sum, Box 1 ≠ Box 3 discrepancies, basis + adjustment ≠ corrected gain.
3. **Classification errors** — mislabeling a 2024 donation as 2025, confusing Box 2 with Box 4, misidentifying the recipient on a 1099-Q.
4. **Substantiation gaps** — missing EIN, missing "no goods or services" language, expired acknowledgment window.
5. **Framework errors** — applying wrong IRS rule (e.g., using close price instead of H+L/2 for stock FMV).

No single agent catches all five. Independent passes with different framings do. In practice, a second agent re-reading the same files has caught:
- A false-positive "filename mismatch" claim (one agent said a file contained wrong content; the reconciler verified the file was fine).
- A savings bond interest misread ($103.64 vs actual $593.84).
- A W-2 federal withholding misread ($10.05 vs actual $510.85).
- An ESPP basis double-tax trap that would have cost ~$900.

## The Four Agent Roles

Dispatch these in parallel, in the same message, whenever possible:

### 1. Extractor Agent
Reads source documents and extracts every data point into a structured table. Goal: capture everything once, accurately.

Prompt should include:
- Exact list of files to read (absolute paths)
- Specific fields to extract (box numbers, exact amounts, dates, names)
- Instruction to flag anything unclear rather than guess
- Request for a structured output table

### 2. Reconciler Agent
Independently re-reads the same source documents. Does NOT trust the extractor's findings. Produces its own table and flags discrepancies.

Prompt should include:
- The same file list (fresh read)
- The specific claims the extractor made — framed as "verify or refute with exact quoted text from the file"
- Instruction to provide direct file-level evidence for each finding

The reconciler is the error-catching layer. When it says "CONFIRMED" with quoted text, trust the finding. When it says "REFUTED," investigate.

### 3. Math Validator Agent
Verifies all arithmetic: box sums, gain/loss calculations, totals, percentage computations, withholding reconciliation.

Prompt should include:
- The numbers to check (from extractor output)
- The math rules (Box 3 should = Box 1 + pretax contributions, SS tax = 6.2% × Box 3, etc.)
- Instruction to flag any mismatch, however small

### 4. IRS Rules / Substantiation Agent
Checks that documents meet IRS substantiation requirements for the amounts and types involved. Flags gaps.

Prompt should include:
- The donation / income / deduction list
- Request for per-item compliance check against IRS thresholds
- Specific references to cite (Pub 1771, Form 8283 instructions, IRC § 170(f)(8))

## FMV Calculator Agent (Stock Donations)

For charitable stock donations, dispatch a separate FMV agent:
- Find exact high/low prices from reliable sources (Yahoo Finance, StockAnalysis.com)
- Compute FMV = (H + L) / 2 per IRS Reg § 20.2031-2(b)
- Use the **delivery date** (when charity took unconditional control), not the submission date
- Verify any charity-stated value matches the IRS math (if it doesn't, the charity used the wrong date or method, and you compute the correct value yourself)

## Dispatch Rules

### Parallel, not sequential
Launch all agents in the same message. Don't wait for one to finish before starting the next. The agents don't depend on each other's output; they're independent verification passes.

### Fresh context per agent
Each agent should receive enough context to do its job without seeing prior-agent output. Don't say "verify what the previous agent said" — that biases the new agent toward confirmation. Instead, say "independently extract X from file Y" and let the coordinator (you) compare the outputs.

### Background when appropriate
For agents that take more than 30 seconds, use `run_in_background: true`. You can continue working while they run and check results when they complete.

### Budget: typically 3-5 agents per round
Too few agents misses errors. Too many wastes tokens on redundant reads. Three to five independent passes hits the sweet spot:
1. Extractor
2. Reconciler (independent re-read)
3. Math validator
4. IRS substantiation checker
5. Optional: domain specialist (FMV calculator, CPA reviewer, tax strategist)

## Error Log Discipline

Maintain an error log throughout the session. For every discrepancy found:

| ID | Item | Wrong Value | Right Value | Error Type | Caught By |
|----|------|-------------|-------------|------------|-----------|
| E1 | W-2 Box 2 | $10.05 | $510.85 | Misread rotated image | Math Validator |

Error types to track:
- **Extraction** — misread from source document
- **Math** — addition, subtraction, or percentage error
- **Classification** — wrong category, wrong tax year, wrong form
- **Interpretation** — wrong IRS rule applied
- **Substantiation** — missing required element

Track errors at ALL severity levels. A $0.02 discrepancy may indicate a rounding-mode issue that affects dozens of other numbers. Treat all errors as errors.

## Round 2 Pattern

When the user provides additional documents mid-session:

1. Dispatch a fresh extractor for the new files
2. Dispatch a reconciler to independently verify
3. Update the master reconciliation table
4. Re-run totals
5. Update action items (cross out resolved ones, add any new findings)

Never silently merge new data into the old picture. Show before/after with a change log.

## When a Claim Conflicts with a Prior Claim

If agent N contradicts agent N-1, always trust direct file evidence over agent memory. The protocol:

1. Identify the exact claim in dispute
2. Dispatch a third agent that quotes the relevant file text directly
3. Whichever claim matches the quoted text wins
4. If neither matches, the files need human inspection

This has happened in practice — a first agent confidently stated "file X contains Y content, not Z" and a reconciler proved the file actually did contain Z. The first agent was wrong; the reconciler saved downstream work from being built on a false foundation.
