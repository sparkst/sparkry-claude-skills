---
name: qreview
description: "This skill should be used when the user asks to \"review an artifact\", \"get multiple perspectives on\", \"multi-agent review\", \"qreview\", or wants N independent reviewers to evaluate any output (code, content, strategy, design) against requirements. Spawns 2-5 clean-context agents in parallel with max-severity deduplication."
version: 0.1.0
---

# /qreview -- Multi-Agent Artifact Review

## Purpose

Spawn N clean-context reviewer agents in parallel to evaluate any artifact (code, content, strategy document, design spec) against stated requirements. Each reviewer operates with zero knowledge of other reviewers' findings. After all reviewers complete, findings are validated, deduplicated using max-severity merge, and presented sorted by severity.

This skill replaces single-pass review with a multi-perspective protocol that surfaces blind spots no single reviewer catches. Dissent is the default mode: every finding surfaces, nothing is suppressed, and a single reviewer's P0/P1 is never downgraded by majority opinion.

## Review Protocol

Follow these steps in order. Do not skip steps. Do not combine steps.

### Step 1: Identify the Artifact and Requirements

Determine the artifact to review. Accept either a file path or inline content. If the user provides a file path, read the file. If the user provides inline content, write it to a temporary file so tools can reference it.

Determine the requirements to review against. Accept either a file path to a requirements document, inline requirements, or REQ-IDs referencing a requirements lock file. If no explicit requirements exist, ask the user what the artifact should accomplish and record that as the requirements.

### Step 2: Initialize the Review

Run `tools/review-driver.py init` to set up review state. This:
- Creates the `.qreview/state.json` state file
- Runs `tools/test-runner.py` to discover and execute co-located deterministic tests
- Runs `tools/team-selector.py` to select the optimal review team based on artifact domains
- Returns the team composition and test results

Inspect the team composition. If the team does not cover a domain the user cares about, override by adjusting the `--reviewers` count or providing a custom catalog.

### Step 3: Execute Deterministic Tests

Test execution happens during init (Step 2). Review the test results before spawning reviewers. If all tests pass, proceed. If tests fail, those failures are auto-classified as findings:
- **P0 (regression)**: a test that passed in a prior round now fails
- **P1 (new failure)**: any test failure in the first round

Test failure findings are included in the final synthesis alongside reviewer findings. They are not double-counted -- the deduplication step merges them with any reviewer-reported findings about the same issue.

### Step 4: Spawn Reviewer Agents in Parallel

For each reviewer on the team, construct the reviewer prompt using the template below (see "Reviewer Agent Prompt Template") with the reviewer's name, lens, artifact content, requirements, and test results. Then spawn each reviewer as a subagent using the Agent tool, all in parallel.

Each reviewer agent receives ONLY:
1. The artifact content (full text)
2. The requirements (full text)
3. Test results summary (pass/fail counts and failure details)
4. Their specific review lens (e.g., "security vulnerabilities, auth, data protection")
5. The finding output schema (id, severity, title, requirement, finding, recommendation, evidence, source)

Each reviewer agent does NOT receive:
- Other reviewers' findings
- Implementation context beyond the artifact itself
- Prior review rounds' findings
- The team composition or other reviewers' lenses

Instruct each reviewer to output findings as a JSON array of finding objects.

### Step 5: Collect and Record Findings

As each reviewer completes, record their findings via `tools/review-driver.py record-findings --reviewer INDEX --findings-file PATH`. The driver parses and validates each finding against the schema. Invalid findings (missing required fields, bad severity values, malformed IDs) are dropped and counted. The `validation_dropped` field in state tracks per-reviewer drop counts. If any findings were dropped, report the count in the results presentation -- this signals a reviewer producing malformed output.

### Step 6: Synthesize Findings

Run `tools/review-driver.py synthesize` to:
1. Collect all validated findings from all reviewers
2. Run `tools/finding-parser.py synthesize_findings` which validates, deduplicates by normalized title (max-severity wins), and sorts P0-first
3. Run `tools/finding-parser.py check_convergence` to determine if the artifact is safe to ship
4. Run `tools/finding-parser.py count_by_severity` for the summary counts

### Step 7: Present Results

Present the synthesized findings to the user sorted by severity (P0 first, then P1, P2, P3). For each finding, show:
- ID and severity
- Title
- Requirement it traces to
- The finding (what is wrong)
- Recommendation (how to fix it)
- Evidence (file:line if available)
- Sources (which reviewers flagged it)

If the synthesis `dropped_count` is non-zero, report: "N findings were dropped due to schema validation errors."

End with the convergence assessment:
- **Converged (safe to ship)**: zero P0, zero P1, low-severity count within threshold
- **Not converged**: state how many P0/P1 remain and what must be fixed

## Severity Taxonomy

| Severity | Meaning | Action |
|----------|---------|--------|
| P0 | Blocks shipping. Correctness failure, security vulnerability, data loss risk, requirement violation. | Must fix before any release. |
| P1 | Must fix before v1. Significant quality issue, missing error handling, incomplete requirement coverage. | Fix before declaring feature complete. |
| P2 | Should fix. Code smell, suboptimal pattern, minor UX issue, documentation gap. | Fix in next iteration. |
| P3 | Nice to have. Style nit, optional optimization, cosmetic improvement. | Fix if time permits. |

## Key Rules

### Dissent Mode is Default

All findings surface. No finding is suppressed because a majority of reviewers did not flag it. One reviewer's P0 is worth the same as five reviewers' P0.

### Single-Reviewer P0/P1 is Never Downgraded

If one reviewer classifies an issue as P0 and three others classify it as P2, the merged finding is P0. Max-severity always wins. This is enforced by `tools/finding-parser.py deduplicate_findings`.

### Pre-Existing Issues are In-Scope

Reviewers do not classify issues as "out of scope" or "pre-existing." If the artifact contains a problem, it is a finding. The user decides what to fix now versus later.

### Test Failures are Auto-Classified

Failed deterministic tests become findings automatically. They do not require a reviewer to notice them. The classification is P0 for regressions (round > 1) and P1 for new failures (round 1).

### Clean Context Per Reviewer

Each reviewer operates in a fresh context. No reviewer sees another reviewer's output. No reviewer sees the team composition. This prevents anchoring bias and groupthink.

## Tools Reference

All tools live in the `tools/` directory relative to the plugin root:

- **`tools/finding-parser.py`** -- Validates, deduplicates (max-severity), counts, checks convergence, synthesizes, and formats findings. Pure functions, no side effects.
- **`tools/test-runner.py`** -- Discovers co-located tests (pytest, vitest, Makefile, scripts, rubrics) and executes them. Converts failures to findings.
- **`tools/team-selector.py`** -- Classifies artifact domains via keyword/pattern matching and selects the optimal review team from an agent catalog.
- **`tools/review-driver.py`** -- State machine driver for the review lifecycle. Manages `.qreview/state.json`, generates reviewer prompts, records findings, runs synthesis.

## Reviewer Agent Prompt Template

Each reviewer agent receives a prompt structured as follows:

```
You are a {reviewer_name} reviewing an artifact.

Your review lens: {review_lens}

## Artifact

{artifact_content}

## Requirements

{requirements_content}

## Test Results

{test_results_summary}

## Instructions

Review the artifact against the requirements through your lens of {review_lens}.

Use Grep to find relevant sections rather than reading entire files.

Output your findings as a JSON array. Each finding must have these fields:
- id: string matching pattern P[0-3]-NNN (e.g., P0-001, P1-002)
- severity: one of P0, P1, P2, P3
- title: concise description of the issue
- requirement: which requirement this relates to
- finding: detailed description of the problem
- recommendation: how to fix it
- source: "{reviewer_name}"
- evidence: file path and line number if applicable

Severity guide:
- P0: Blocks shipping (correctness, security, data loss, requirement violation)
- P1: Must fix before v1 (quality, error handling, incomplete coverage)
- P2: Should fix (code smell, suboptimal pattern, minor UX, doc gap)
- P3: Nice to have (style, optional optimization, cosmetic)

Output ONLY the JSON array. No other text.
```

## State Management

Review state lives in `.qreview/state.json` relative to the working directory. The state file tracks:
- Artifact and requirements paths
- Selected team composition
- Test results and auto-generated findings
- Per-reviewer raw outputs
- Synthesis results
- Current status (initialized, reviewing, synthesized)

Use `tools/review-driver.py reset` to clear state between reviews. Use `tools/review-driver.py status` to inspect current state.
