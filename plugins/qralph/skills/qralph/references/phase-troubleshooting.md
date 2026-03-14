# Phase-Specific Troubleshooting

Read this when you encounter errors or unexpected behavior in specific pipeline phases. Most of the time the pipeline handles recovery automatically — this guide is for when you need to understand what's happening.

## Verification Phase (VERIFY)

The VERIFY phase is the most failure-prone phase because it asks a fresh-context agent to independently validate every acceptance criterion by reading source code. The common failure mode is "rubber-stamping" — the verifier writes generic evidence like "Verified in execution outputs" instead of actually reading files and citing specific locations.

The pipeline's validation layer catches this and returns an `error` action. The `message` field tells you exactly what failed — missing AC results, weak evidence, failed criteria, etc.

### When you receive a verification error

1. Read the `message` field to understand what specifically failed
2. Delete `verification/result.md` so the pipeline regenerates a fresh verification prompt
3. Call `next` — the pipeline re-enters VERIFY with a new verifier agent
4. The new verifier starts fresh with a prompt that incorporates the previous failure

### What the pipeline validates in verification output

- The verifier reads each source file directly (not just execution reports)
- Each acceptance criterion gets its own read-verify-record cycle
- Evidence must be `filename.ext:LINE — "quoted code snippet"`
- At least 80% of evidence entries must have `file:line` patterns
- All 6 fields per criterion: criterion_index, criterion, status, intent_match, ship_ready, evidence

### Retry limits

3 verification attempts maximum. After 3 failures, the pipeline escalates to the user with options: accept current state, go back for more fixes, or stop.

## Quality Loop (QUALITY_LOOP)

The quality loop has two sub-phases. The pipeline manages this logic — understanding it helps you interpret `quality_dashboard` actions.

### Discovery (expensive, capped)

- Agents review code in parallel, reporting P0/P1/P2 findings with confidence scores
- Agents that find nothing drop out (code-reviewer stays 1 extra round for thoroughness)
- Max rounds scale by complexity: 2 (simple), 3 (moderate/complex)
- Early exit on consensus: all agents high confidence + no P0s

### Fix+Verify (cheap, loops until clean)

- Each finding becomes a fix requirement with a REQ-ID
- TDD cycle: failing test first, then fix, then simplify
- Full test suite must stay green after each fix
- If a fix breaks other tests 3 times: backtrack to replan
- If a fix fails 3 times: escalate to user

### Replan limits

Maximum 2 replans per project. After that, the pipeline escalates to the user rather than going in circles.

## Smoke Tests (SMOKE)

After successful deployment, the pipeline generates parallel smoke test agents that hit the live URL:

- Categories: pages, API, security, SEO, errors
- All agents run simultaneously using haiku (fast and inexpensive)
- Agents use WebFetch/curl — no source code reading
- Each criterion: PASS (with evidence), FAIL (with details), or SKIP (needs browser JS)
- All PASS → advance to LEARN
- Any FAIL → shown to user with options
