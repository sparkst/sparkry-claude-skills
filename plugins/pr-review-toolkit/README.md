# PR Review Toolkit

Comprehensive PR review with 6 specialized agents, each focusing on a different aspect of code quality.

## Quick Start

```bash
/plugin install pr-review-toolkit@sparkry-claude-skills

# Full review
/pr-review-toolkit:review-pr

# Targeted review
/pr-review-toolkit:review-pr tests errors
```

## Agents

| Agent | Focus | When to Use |
|-------|-------|-------------|
| **code-reviewer** | CLAUDE.md compliance, bugs, code quality | After writing/modifying code, before commits |
| **silent-failure-hunter** | Silent failures, catch blocks, error handling | After implementing error handling |
| **pr-test-analyzer** | Test coverage, critical gaps, test quality | After creating/updating a PR |
| **comment-analyzer** | Comment accuracy, documentation, comment rot | After adding docs, before PRs |
| **type-design-analyzer** | Encapsulation, invariants, type quality (rated 1-10) | When introducing new types |
| **code-simplifier** | Clarity, complexity reduction, maintainability | After passing code review |

## Review Aspects

| Aspect | Agent | Description |
|--------|-------|-------------|
| `code` | code-reviewer | General quality and guideline compliance |
| `errors` | silent-failure-hunter | Error handling and silent failures |
| `tests` | pr-test-analyzer | Test coverage and quality |
| `comments` | comment-analyzer | Comment accuracy and maintainability |
| `types` | type-design-analyzer | Type design and invariants |
| `simplify` | code-simplifier | Code simplification |
| `all` | All applicable | Full review (default) |

## Confidence Scoring

- **code-reviewer**: 0-100 (only reports >= 80)
- **pr-test-analyzer**: 1-10 criticality rating
- **silent-failure-hunter**: CRITICAL / HIGH / MEDIUM severity
- **type-design-analyzer**: 4 dimensions rated 1-10
- **comment-analyzer**: Critical Issues / Improvements / Removals
- **code-simplifier**: Identifies complexity and suggests simplifications

## Recommended Workflow

1. Write code
2. `code-reviewer` + `silent-failure-hunter` (catch issues early)
3. Fix critical issues
4. `pr-test-analyzer` (verify test coverage)
5. `comment-analyzer` (if docs were added)
6. `type-design-analyzer` (if types were added)
7. `code-simplifier` (polish after review passes)
8. Create PR

## Version

1.0.0

## License

MIT
