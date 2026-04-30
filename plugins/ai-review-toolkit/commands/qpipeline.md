---
name: qpipeline
description: "Composable pipeline orchestrator. Presets: review, thorough, content, code. Custom phase composition supported."
---

# qpipeline command

Parse arguments: `[preset|--phases LIST] <artifact_or_description> [--requirements PATH]`

Subcommands: `status`, `resume <project-id>`

## Argument handling

1. `preset` (optional) - One of: review, thorough, content, code (default: review)
2. `--phases LIST` (optional) - Custom comma-separated phase list for composition
3. `artifact_or_description` (required) - Path to artifact or text description of what to build/review
4. `--requirements PATH` (optional) - Path to requirements file
5. Subcommand `status` - Show status of all active pipelines
6. Subcommand `resume <project-id>` - Resume a paused or interrupted pipeline

## Execution flow

1. If no preset given, default to "review"
2. Resolve preset to phase list or use custom --phases
3. Invoke the `qpipeline` skill to execute the pipeline
4. Execute phases sequentially, passing outputs forward
5. Present phase-by-phase progress with status indicators
