---
name: qloop
description: "Iterative review-fix cycle. Review -> fix ALL -> re-review (fresh context) -> repeat until no P0, P1, or significant P2/P3 remain."
---

# qloop command

Parse arguments: `<artifact_path> [--requirements PATH] [--reviewers N] [--threshold N] [--max-rounds N]`

## Argument handling

1. `artifact_path` (required) - Path to the artifact to review and fix iteratively
2. `--requirements PATH` (optional) - Path to requirements file
3. `--reviewers N` (optional) - Number of reviewers per round (default: 2-5, domain-adaptive via team-selector)
4. `--threshold N` (optional) - Maximum allowed count of P2+P3 findings for convergence (default: 0)
5. `--max-rounds N` (optional) - Maximum number of review-fix rounds (default: 5)

## Execution flow

1. If no requirements path given, ask the user for requirements (inline text or file path)
2. Validate that the artifact path exists and is readable
3. Invoke the `qloop` skill to execute the iterative review-fix cycle
4. Each round: review (fresh context) -> fix ALL findings -> re-review
5. Converge when: no P0, no P1, and no significant P2/P3 remain, or max rounds reached
6. Present round-by-round progress and final convergence status
