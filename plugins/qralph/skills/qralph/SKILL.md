---
name: qralph
description: Deterministic multi-agent pipeline that takes ideas from concept to deployed production code. Handles the full lifecycle — ideation, persona generation, concept review, planning, parallel execution, quality loops, verification, demo, deployment, and smoke testing. Use this whenever the user says /qralph, QRALPH, asks to "run the pipeline", or wants end-to-end multi-agent project execution. Also use when the user references pipeline phases, project orchestration, or wants to build something from scratch with automated quality gates.
---

# QRALPH v6.8.1 — Deterministic Multi-Agent Pipeline

## How This Works (read this first)

QRALPH is a **state machine**. The pipeline script (`qralph-pipeline.py`) has already encoded all the decision-making — which agents to spawn, in what order, with what prompts, and what quality gates to enforce. Your job is to be the **faithful executor**: call `next`, do exactly what the pipeline tells you, relay results to the user, repeat.

This matters because QRALPH spawns many agents in parallel. If you improvise — reordering steps, skipping a gate, adding your own analysis, or invoking external skills — the downstream agents receive stale or incorrect context. We've seen this waste thousands of tokens: 5 agents complete work based on assumptions that were invalid because the executor deviated from the pipeline's instructions. The pipeline prevents this by managing state transitions, so trust it.

**Your role in one sentence:** Call the pipeline, do what it says, show results to the user at gates, and never freelance.

## Why Determinism Matters

The pipeline's phases build on each other. Each phase produces artifacts that downstream phases consume. When the executor skips ahead, adds its own interpretation, or calls external skills:

- Agents spawn with prompts built from the wrong state
- Parallel agent groups do work that has to be thrown away
- Quality gates can't validate work that didn't follow the expected path
- The user pays for wasted tokens and gets a worse result

The pipeline already handles complexity, error recovery, and backtracking internally. It will escalate to the user when it genuinely needs human judgment. Your restraint is what makes the system reliable.

## Session Ownership

When QRALPH is active, it orchestrates everything — brainstorming, frontend design, code review, deployment — through its own pipeline phases and spawned agents. Those agents can use whatever tools and skills they need. But the executor (you) stays in the `plan` → `next` loop.

If another skill's trigger seems to match the user's request (e.g., "build a landing page" triggering frontend-design), the pipeline already handles that domain through its own agents. Invoking external skills would create parallel, conflicting work streams. Skip pre-work like EnterPlanMode or brainstorming skills — go straight to `plan`.

## Executor Guidelines

1. **Spawn every agent the pipeline returns.** The pipeline has already decided which agents are needed based on project complexity. Skipping one means downstream phases get incomplete inputs.
2. **Use the exact model from each agent config.** Model selection is intentional — haiku for fast checks, opus for deep analysis. Substituting changes cost and quality characteristics the pipeline planned around.
3. **Write each agent's complete return text to disk verbatim.** Later phases read these files. Summarizing or paraphrasing loses the detail that verification and quality loops depend on.
4. **Two-call gate protocol:** At confirm gates, the pipeline returns the gate action on the first call. Show the output to the user via AskUserQuestion and stop. Only after the user responds in a separate turn do you call `next --confirm`. The pipeline enforces this — it rejects `--confirm` if the gate wasn't returned in a prior call. This prevents accidentally auto-confirming past the user.
5. **Only use `next` to advance.** The pipeline manages phase transitions internally. Calling other pipeline commands directly can corrupt state or skip gates.
6. **If blocked or confused, ask the user.** Guessing at the right action risks sending agents down the wrong path, which compounds into wasted work.
7. **For `--thorough` mode users:** Use plain language only. These are non-technical users — never show error traces, type errors, or jargon.
8. **Spawn smoke test agents in parallel** for maximum speed (they're independent and use haiku).

## Trigger

`/qralph "<request>"` or `QRALPH "<request>"`

## Operating Modes

| Mode | Flag | Phases | Audience |
|------|------|--------|----------|
| Thorough | `--thorough` (default) | IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → SIMPLIFY → QUALITY_LOOP → POLISH → VERIFY → DEMO → DEPLOY → SMOKE → LEARN | No-code users |
| Quick | `--quick` | PLAN → EXECUTE → SIMPLIFY → VERIFY → DEMO → DEPLOY → SMOKE → LEARN | Developers |

Add `--with-business` to `--quick` mode for business insights without the full lifecycle.

## Pipeline Flow

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│  IDEATE  │────▶│ PERSONA  │────▶│CONCEPT_REVIEW│────▶│   PLAN   │
│          │     │          │     │              │     │          │
│brainstorm│     │ generate │     │  multi-agent │     │ template │
│ + review │     │ + review │     │   review +   │     │+ agents  │
│          │     │          │     │  synthesis   │     │+ tasks   │
└──────────┘     └──────────┘     └──────────────┘     └──────────┘
     │                │                  │                   │
  [GATE:           [GATE:            [GATE:             [GATE:
confirm_         confirm_          confirm_           confirm_
ideation]        personas]         concept]           template]
                                                         │
                                                     [GATE:
                                                    confirm_
                                                      plan]
                                                         │
                                                         ▼
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ QUALITY  │◀────│ SIMPLIFY │◀────│   EXECUTE    │◀────┘
│   LOOP   │     │          │     │              │
│          │     │complexity│     │parallel agent│
│discovery │     │reduction │     │   groups     │
│ + fix    │     │          │     │              │
│ + dash   │     │          │     │+ quality gate│
└──────────┘     └──────────┘     └──────────────┘
     │
     │ (converge / early_terminate / max_rounds)
     │  backtrack ──▶ PLAN (max 2x)
     ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  POLISH  │────▶│  VERIFY  │────▶│   DEMO   │────▶│  DEPLOY  │────▶│  SMOKE   │
│          │     │          │     │          │     │          │     │          │
│bug_fixer │     │fresh-ctx │     │present + │     │preflight │     │parallel  │
│wiring    │     │verifier  │     │feedback  │     │checklist │     │HTTP tests│
│req_tracer│     │all ACs   │     │marshal   │     │wrangler  │     │hit live  │
│          │     │          │     │→ PLAN    │     │deploy    │     │URL       │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                │                │                │
                   FAIL ──▶        [GATE:            [GATE:           FAIL ──▶
                   block          confirm_          confirm_          show to
                                   demo]             deploy]           user
                                  feedback            OR auto if
                                  → PLAN             explicit]
                                                        │
                                                        ▼
                                  ┌──────────┐     ┌──────────┐
                                  │  LEARN   │────▶│ COMPLETE │
                                  │          │     │          │
                                  │ capture  │     │ SUMMARY  │
                                  │learnings │     │  .md     │
                                  └──────────┘     └──────────┘
```

## First Run

If `.qralph/config.json` doesn't exist:
```bash
python3 .qralph/tools/qralph-config.py setup
```

## Start
```bash
python3 .qralph/tools/qralph-pipeline.py plan "<request>" [--thorough|--quick] [--target-dir <path>]
```

The `plan` response includes a `project_id` field (e.g. `"014-redesign-checkout-flow"`). Capture this and pass it to all subsequent `next` calls via `--project`. This is how QRALPH isolates state when multiple projects run concurrently.

## Loop

Repeat until action is `"complete"`:
```bash
python3 .qralph/tools/qralph-pipeline.py next [--confirm] --project <project_id>
```

## Action Reference

| Action | What to do |
|--------|-----------|
| `confirm_ideation` | Show `IDEATION.md` to user via AskUserQuestion. Stop. After user confirms in a separate turn: `next --confirm` |
| `confirm_personas` | Show `personas/*.md` to user via AskUserQuestion. Stop. After user confirms: `next --confirm` |
| `confirm_concept` | Show `CONCEPT-SYNTHESIS.md` to user via AskUserQuestion. Stop. After user confirms: `next --confirm` |
| `confirm_template` | Show template + agents to user via AskUserQuestion. Stop. After user confirms: `next --confirm` |
| `spawn_agents` | For each agent: spawn with `name=agent.name, model=agent.model, prompt=agent.prompt`. Write the complete return text to `{output_dir}/{agent.name}.md`. If `parallel: true`, spawn all agents simultaneously. |
| `define_tasks` | Read `analyses_summary` from the action response. Read existing `manifest.json` at `manifest_path`, add a `tasks` array (preserving all other fields), write back. Each task: `{"id": "T-001", "summary": "...", "files": ["path/to/file"], "acceptance_criteria": ["criterion 1"], "depends_on": [], "tests_needed": true}`. Then call `next`. |
| `confirm_plan` | Show `PLAN.md` + tasks to user via AskUserQuestion. Stop. After user confirms: `next --confirm` |
| `confirm_demo` | Show demo checklist to user via AskUserQuestion. Stop. If user approves: `next --confirm`. If user provides feedback: `next --confirm --feedback "<user text>"`. |
| `demo_feedback` | Pipeline recorded feedback and is routing it back to PLAN for revision. Tell the user their feedback is being addressed. Call `next`. |
| `demo_replan` | Pipeline is revising the plan based on demo feedback. Tell user their feedback has been recorded and the implementation is being revised. Call `next`. |
| `confirm_deploy` | Show pre-deploy checklist to user via AskUserQuestion. Stop. After user confirms: `next --confirm`. (If user explicitly said "deploy to X" in their original request, the pipeline auto-deploys and skips this gate.) |
| `smoke_results` | Show smoke test results to user (all passed). Call `next`. |
| `smoke_failure` | Show failed smoke tests to user. Let user decide: (a) fix issues and redeploy, (b) accept current state. Pass choice via `next`. |
| `quality_dashboard` | Show `quality-reports/round-N.md` to user. If P0 count is dropping, note quality is improving and call `next`. If stuck at round 3, explain in plain language and call `next` (pipeline handles backtrack). |
| `respawn_agent` | An agent timed out. Re-spawn the agent named in `agent_name` with its original prompt and model. Write output to `output_file`. If `heal_suggestion` is present, mention auto-recovery is being attempted. Call `next`. |
| `escalate_to_user` | Show the plain-language explanation and options from the pipeline response. Let user choose. If `heal_suggestion` is present, show it as a recommendation. Pass choice via `next --confirm`. Use exactly what the pipeline provides — don't add technical detail. |
| `backtrack_replan` | Tell user the current approach isn't working and the pipeline is revising the plan with lessons learned. Call `next`. |
| `learn_complete` | Show `learning-summary.md` to user. Summarize what the project taught QRALPH. Call `next`. |
| `error` | Read the error `message` carefully. For verification errors: delete `verification/result.md` and call `next` so the pipeline regenerates the verifier. For implementation bugs: fix the code, then call `next`. If unclear: show the error to the user and ask. See `references/phase-troubleshooting.md` for detailed guidance. |
| `complete` | Show `SUMMARY.md` to user. Done. |

## Deploy Behavior

The pipeline is intelligent about when to ask:

- **"deploy to Cloudflare Workers"** → Explicit intent. Auto-deploys, skips `confirm_deploy`. Smoke tests run against live URL.
- **"build me a landing page"** → No deploy language. Skips DEPLOY and SMOKE entirely, goes to LEARN.
- **"build and maybe deploy later"** → Implicit intent. Shows `confirm_deploy` gate with checklist.

Deploy command auto-detection: `wrangler.toml` → wrangler, `vercel.json` → vercel, `package.json` deploy script → npm.

## Safety Guarantees (--thorough mode)

These invariants are enforced by the pipeline:

1. **Pipeline never exits with failing tests.** It fixes or escalates.
2. **Every requirement has a test.** The requirements tracer enforces this in POLISH.
3. **Plain-language escalation.** When auto-fix fails, the user gets simple options, not technical error messages.
4. **No broken builds.** VERIFY is a hard gate — all checks pass before proceeding.
5. **No silent deploys.** Unless the user explicitly requested deployment, the pipeline asks first.
6. **Production is verified.** Smoke tests confirm the live site works after deployment.
7. **Learning accumulates.** Each project captures lessons for future projects.

## What the Pipeline Handles (so you don't need to)

- Critical agents (sde-iii, architecture-advisor) are included regardless of template
- Quality gate (tests/lint/typecheck) runs automatically after execution
- Verification verdict must be explicit PASS — ambiguous or FAIL blocks finalization
- Gate two-call protocol enforcement
- Deploy intent detection and command auto-detection
- Smoke test parallelization and verdict aggregation
- Agent scaling by complexity
- Confidence-based consensus for early discovery termination
- State checkpointing at every transition for crash recovery

## Project Artifacts

```
project-NNN/
├── IDEATION.md              # Refined concept + business validation
├── personas/                # Persona prompt templates
├── concept-reviews/         # Isolated concept review outputs
├── CONCEPT-SYNTHESIS.md     # Consolidated concept findings (P0/P1/P2)
├── agent-outputs/           # Planning agent outputs
├── PLAN.md                  # Implementation plan
├── manifest.json            # Project manifest with tasks
├── execution-outputs/       # Per-task implementation outputs
├── quality-reports/         # Per-round quality dashboards
├── POLISH-REPORT.md         # Bug fix + wiring + requirements trace
├── verification/result.md   # Fresh-context verification
├── demo/feedback.md         # Demo phase feedback
├── DEPLOY-REPORT.md         # Deploy output + live URL
├── smoke-tests/             # Per-category smoke test results
├── SMOKE-REPORT.md          # Aggregated smoke test verdict
├── learning-summary.md      # What this project taught QRALPH
└── SUMMARY.md               # Final summary with metrics
```

## Recovery

```bash
python3 .qralph/tools/qralph-pipeline.py next --project <project_id>
```
State is checkpointed — this picks up where it left off.

## Status

```bash
python3 .qralph/tools/qralph-pipeline.py status --project <project_id>
```

## Multi-Project Concurrency

Multiple QRALPH projects can run simultaneously in separate Claude Code sessions. Each session passes `--project <id>` to isolate state. State is stored per-project in `.qralph/projects/<id>/state.json`.
