# PR Review Toolkit - Installation Guide

## Install

```bash
# Add the marketplace (if not already added)
/plugin marketplace add sparkst/sparkry-claude-skills

# Install the plugin
/plugin install pr-review-toolkit@sparkry-claude-skills
```

## What You Get

**1 skill:**
- `review-pr` - Orchestrates all agents for comprehensive PR review

**6 agents:**
- `code-reviewer` - CLAUDE.md compliance, bug detection, code quality (confidence scoring 0-100)
- `silent-failure-hunter` - Silent failures, catch blocks, error handling (CRITICAL/HIGH/MEDIUM)
- `pr-test-analyzer` - Test coverage quality and gaps (criticality 1-10)
- `comment-analyzer` - Comment accuracy and rot detection
- `type-design-analyzer` - Type encapsulation and invariant quality (4 dimensions, 1-10 each)
- `code-simplifier` - Code clarity and maintainability (preserves functionality)

## Usage

### Full Review

```
/pr-review-toolkit:review-pr
```

Runs all applicable agents based on what changed in your git diff.

### Targeted Review

```
/pr-review-toolkit:review-pr code errors
/pr-review-toolkit:review-pr tests
/pr-review-toolkit:review-pr comments types
/pr-review-toolkit:review-pr simplify
```

### Parallel Review

```
/pr-review-toolkit:review-pr all parallel
```

### Agents Auto-trigger

Agents trigger proactively based on context:
- Finished writing code? `code-reviewer` runs
- Added try/catch blocks? `silent-failure-hunter` runs
- About to create a PR? Multiple agents run
- Added documentation? `comment-analyzer` runs
- Introduced new types? `type-design-analyzer` runs

## Recommended Workflow

```
1. Write code
2. /pr-review-toolkit:review-pr code errors    (catch issues early)
3. Fix critical issues
4. /pr-review-toolkit:review-pr tests           (verify coverage)
5. /pr-review-toolkit:review-pr comments types  (if applicable)
6. /pr-review-toolkit:review-pr simplify        (polish)
7. Create PR
```

## Output Format

The review produces a structured summary:

```
# PR Review Summary

## Critical Issues (X found)
- [agent-name]: Issue description [file:line]

## Important Issues (X found)
- [agent-name]: Issue description [file:line]

## Suggestions (X found)
- [agent-name]: Suggestion [file:line]

## Strengths
- What's well-done in this PR
```

## Update

```bash
/plugin marketplace update sparkry-claude-skills
```

## Uninstall

```bash
/plugin uninstall pr-review-toolkit@sparkry-claude-skills
```
