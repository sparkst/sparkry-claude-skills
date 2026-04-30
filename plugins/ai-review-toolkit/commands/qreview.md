---
name: qreview
description: "Multi-agent review of any artifact against requirements. Spawns 2-5 clean-context reviewers in parallel."
---

# qreview command

Parse arguments: `<artifact_path> [--requirements PATH] [--reviewers N] [--catalog PATH]`

## Argument handling

1. `artifact_path` (required) - Path to the artifact to review
2. `--requirements PATH` (optional) - Path to requirements file
3. `--reviewers N` (optional) - Number of reviewers to spawn (default: 2-5, domain-adaptive via team-selector)
4. `--catalog PATH` (optional) - Path to finding catalog for dedup/learning

## Execution flow

1. If no requirements path given, ask the user for requirements (inline text or file path)
2. Validate that the artifact path exists and is readable
3. Invoke the `qreview` skill to execute the review with the parsed arguments
4. Wait for all reviewer agents to complete
5. Present synthesized findings at the end, grouped by severity (P0 > P1 > P2 > P3)
