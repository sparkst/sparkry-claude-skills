# QDESIGN — UX Design Pipeline

Full end-to-end UX design pipeline: wireframe → critique → revise → implement → browser test with recursive fix loop.

## Usage

```
/qdesign "Activity dashboard for project managers, 35-55, laptop users"
```

## Pipeline Phases

| Phase | Tool | Action |
|-------|------|--------|
| 0. Preflight | — | Verify 6 MCP servers connected |
| 1. Requirements | — | Extract flows, audience, constraints |
| 2. Wireframe | Stitch | Generate mockups → PAUSE |
| 3. Critique | UX Knowledge, UI Expert, UI-UX Pro | 3-critic review → P0-P3 severity |
| 4. Revise | Stitch | Apply fixes → PAUSE |
| 5. Implement | Magic (21st.dev) | Production components → PAUSE |
| 6. Test/Fix | Playwright + Critics | Recursive fix loop (≤4 rounds) |

## Required MCP Servers

- **stitch** — Wireframing and mockup generation
- **ux-knowledge** — Nielsen heuristics, WCAG, accessibility
- **ui-expert** — Audience-specific UI analysis
- **ui-ux-pro** — Validated UX patterns and components
- **magic** — Production component generation (21st.dev)
- **playwright** — Browser automation testing
