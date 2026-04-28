---
name: tax-review
description: Review and validate US tax documents (W-2s, 1099s, 1098, K-1, 5498, charitable acknowledgments, Schwab/Fidelity/E*TRADE consolidated statements) for accuracy, IRS substantiation compliance, and proper tax treatment. Use this skill whenever the user shares tax documents for review, asks to validate tax inputs, wants to check their tax return before filing, mentions preparing taxes, asks about ESPP/RSU basis adjustments, stock donation valuation, rollover reporting, or any situation where tax documents need to be cross-checked against IRS rules and 2025 tax law. Dispatches parallel subagents (extractor, independent reconciler, math validator, IRS substantiation checker, FMV calculator) to catch errors a single pass would miss. Grounded in 2025 tax law including OBBBA changes. Not a substitute for a CPA but catches the mechanical errors that bite most taxpayers.
---

# Tax Review Skill

Review tax documents with a multi-agent validation workflow. Catches misreads, math errors, missing substantiation, and incorrect tax treatment that a single-pass read would miss.

## When to Use This Skill

- User shares tax documents for review (W-2s, 1099s, 1098, brokerage statements, donation acknowledgments, K-1s, 5498s)
- User asks "does this look right?" about a tax document
- User is preparing their return and wants validation before filing
- User mentions ESPP/ISO/RSU sales, stock donations, rollovers, or equity compensation
- User has questions about IRS substantiation (CWA, Form 8283, appraisals)
- User needs to verify 2025 tax law treatment of a specific item

## Core Principle

**Never trust a single-pass extraction of financial data.** Tax documents are full of rotated photos, unusual box codes, partial pretax adjustments, and IRS rules that change every few years. A single reader will get numbers wrong. Independent passes catch what one pass misses.

The validation pattern has empirically caught, in real sessions: W-2 withholding misreads of $500+, savings bond interest misreads of $490, ESPP double-tax traps worth ~$900, and false-positive filename-mismatch claims that would have caused unnecessary re-work.

## Workflow

### Step 1 — Inventory

List every file the user has shared, in a table. Note form type, date, recipient, and a one-line key-amount summary. Identify duplicates.

### Step 2 — Parallel Dispatch

Launch 3–5 subagents **in parallel** (same message, not sequential). Each should have enough context to work without seeing the others' output. See [references/multi-agent-pattern.md](references/multi-agent-pattern.md) for dispatch details.

**Standard roster:**
1. **Extractor** — Reads every document, extracts every field into a structured table
2. **Reconciler** — Independently re-reads the same files and verifies or refutes the extractor's findings with quoted text
3. **Math validator** — Checks box sums, totals, gain/loss math, withholding reconciliation
4. **IRS substantiation checker** — For each donation/income/deduction, confirms the documentation meets IRS requirements
5. **Optional specialists:**
   - FMV calculator (for stock donations) — pulls historical prices, applies IRS H+L/2 rule on delivery date
   - Tax strategist — identifies missed optimizations (HSA, 401(k), backdoor Roth pro-rata trap, DAF bunching)

### Step 3 — Error Log

Maintain an error log throughout the session. Every discrepancy, regardless of severity, gets logged with category and source. Treat all errors as errors — a $0.02 rounding gap often signals a systematic issue.

| ID | Item | Wrong Value | Right Value | Type | Caught By |
|----|------|-------------|-------------|------|-----------|
| E1 | W-2 Box 2 | $10.05 | $510.85 | Misread | Math Validator |

### Step 4 — Apply IRS Rules

For each finding, confirm the correct tax treatment against 2025 law. Use the reference files for specific rules.

### Step 5 — Present Findings

Give the user a structured report:
- Verified values (confirmed correct)
- Errors found and corrected
- Action items by priority (P0 must fix, P1 should verify, P2 planning)
- Open questions needing user input
- Tax strategy opportunities identified

### Round 2+ — Incremental Updates

When the user provides additional documents mid-session, dispatch a fresh extractor + reconciler pair for the new files. Update the master table. Show before/after and change log. Do not silently merge.

## Grounded in 2025 Tax Law

**Never rely on memorized tax law.** Tax law changes frequently. Always check the reference files for current figures and rules. For anything not in the reference files, use `WebSearch` or `WebFetch` to verify against authoritative sources (irs.gov, taxfoundation.org, Pub references).

**The 2025 return is affected by the One Big Beautiful Bill Act** signed 7/4/2025. Several 2025 figures changed retroactively — most notably the standard deduction ($15,750/$23,625/$31,500) and SALT cap ($40,000 with phaseout, not $10,000). See [references/2025-tax-law.md](references/2025-tax-law.md).

## Reference Files (Progressive Disclosure)

Read these on demand when the review task involves the relevant topic. Do not pre-load all of them — each is a full deep-dive.

| File | When to Read |
|------|--------------|
| [references/multi-agent-pattern.md](references/multi-agent-pattern.md) | At the start of every review, to set up the agent dispatch properly |
| [references/2025-tax-law.md](references/2025-tax-law.md) | For any 2025 numerical limit (brackets, standard deduction, retirement limits, SALT, AGI limits, OBBBA changes) |
| [references/w2-validation.md](references/w2-validation.md) | When reviewing W-2s — Box 12 codes, FICA reconciliation, dependent care, DQDIS, multi-W-2 cases |
| [references/1099-reconciliation.md](references/1099-reconciliation.md) | For any 1099 review (INT, DIV, B, R, G, Q, NEC, K, MISC), 1098, K-1, or 5498 |
| [references/form-8949-espp.md](references/form-8949-espp.md) | When the taxpayer has ESPP, ISO, NQSO, or RSU sales — the Form 8949 Code B basis adjustment and qualifying-disposition Schedule 1 Line 8k self-reporting |
| [references/charitable-form-8283.md](references/charitable-form-8283.md) | When reviewing charitable contributions — CWA requirements, FMV of stock donations, delivery-date rule, Form 8283 Section A vs B, AGI limits |

## Output Format

When presenting final findings, structure the output as:

```markdown
## Summary
One paragraph: what was reviewed, what was found, what needs action.

## Verified Values
Table of confirmed-correct items.

## Errors Corrected
Table of errors with original value, correct value, source.

## Action Items
- P0 — must fix before filing
- P1 — should verify
- P2 — tax planning / optimization

## Open Questions
Items needing user input before they can be resolved.

## Tax Strategy Observations
Missed opportunities (HSA undercontribution, backdoor Roth pro-rata trap, etc.)
```

## Anti-Patterns to Avoid

- **Silent fixes.** When you correct a number, always show the before and the after in an error log. Never quietly swap values.
- **Single-agent review of financial data.** Always dispatch the reconciler. The pattern has caught errors in every session where it's been used.
- **Trusting the charity's stated FMV.** Charities often use close price or the submission date. The IRS rule is H+L/2 on the delivery date. You compute.
- **Applying last year's SALT cap to a 2025 return.** SALT was $10,000 for 2018–2024 but is $40,000 (with phaseout) for 2025 under OBBBA.
- **Assuming ESPP basis on 1099-B is right.** It's almost always too low. Ask for the broker's supplemental stock plan detail.
- **Reporting ESPP qualifying-disposition income as "already on W-2."** Employers are NOT required to add this to W-2 (since 2009). The employee self-reports on Schedule 1 Line 8k.
- **Treating a rollover as taxable because you don't see the 1099-R.** If you see a 5498 rollover in Box 2, there must be a corresponding 1099-R. Find it before concluding the distribution is taxable.
- **Using Line 4 (IRA distributions) when the source is a 401(k).** 401(k) rollovers go on Line 5 (Pensions & annuities), not Line 4. Line determined by SOURCE, not destination.

## Important Disclaimers

This skill supports a **review** of tax inputs for mechanical accuracy and IRS compliance. It is not tax advice and does not replace a CPA, especially for:
- Complex business situations (multi-entity, partnerships, S-corps)
- International tax issues (FBAR, FATCA, foreign earned income)
- Estate and trust returns
- State tax review beyond federal pass-through
- Audits or examinations in progress

When the situation is complex enough that a CPA's judgment is needed, say so and flag the specific areas.
