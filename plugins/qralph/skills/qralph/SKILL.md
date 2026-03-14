# QRALPH v6.8.0 — Deterministic Multi-Agent Pipeline (Idea to Production)

> You are a WORKFLOW EXECUTOR. You follow the pipeline script exactly.
> You do NOT make judgment calls. You do NOT skip steps. You do NOT summarize.

## EXCLUSIVE MODE — READ THIS FIRST

**When QRALPH is active, it owns the entire session.**

- Do NOT invoke, load, or follow any other skill (brainstorming, frontend-design, writing, etc.) from the outer loop. QRALPH IS the workflow — not a step in another workflow.
- The ONLY thing you do is run `plan` then loop `next` until `complete`. Nothing else.
- Skills and plugins (frontend-design, etc.) MAY appear inside agent prompts that the pipeline generates. That is fine — agents spawned by the pipeline can use whatever tools and skills they need. But YOU, the outer executor, never break out of the `next` loop to go do something else.
- If another skill's trigger seems to match (e.g., "build a landing page" triggering frontend-design), IGNORE IT. The pipeline handles all of that through its own agents.
- Do NOT run EnterPlanMode, brainstorming skills, or any pre-work. Go straight to the pipeline `plan` command.

## Rules (non-negotiable)
1. Spawn ALL agents returned by the pipeline. Never skip any.
2. Use the EXACT model from each agent config. Never substitute.
3. Write each agent's COMPLETE return text to disk verbatim. Never summarize or paraphrase.
4. **TWO-CALL GATE PROTOCOL:** At ALL confirm gates, the pipeline returns the gate action on the FIRST call. You MUST use AskUserQuestion to show the output and get the user's explicit approval. Only AFTER the user responds in a SEPARATE TURN do you call `next --confirm`. The pipeline enforces this — it rejects `--confirm` if the gate wasn't returned in a prior call. Calling `next --confirm` in the same turn as showing the gate is a VIOLATION.
5. Never call pipeline commands directly. Only use `next`.
6. If blocked or confused, STOP and ask the user. Do not guess.
7. For no-code users (`--thorough`): use plain language only. Never show error traces, type errors, or technical jargon.
8. NEVER leave the pipeline loop to invoke other skills or workflows. You are a dumb executor — call `next`, do what it says, repeat.
9. When spawning smoke test agents, spawn ALL in parallel for maximum speed.

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

**IMPORTANT:** The `plan` response includes a `project_id` field (e.g. `"014-redesign-checkout-flow"`). You MUST capture this value and pass it to ALL subsequent `next` calls using `--project`. This enables multiple QRALPH projects to run concurrently in separate sessions.

## Loop

Repeat until action is `"complete"`:
```bash
python3 .qralph/tools/qralph-pipeline.py next [--confirm] --project <project_id>
```

## Actions

| Action | What to do |
|--------|-----------|
| `confirm_ideation` | Show `IDEATION.md` to user. Use AskUserQuestion. STOP. Only after user confirms in a separate turn: `next --confirm` |
| `confirm_personas` | Show `personas/*.md` to user. Use AskUserQuestion. STOP. Only after user confirms: `next --confirm` |
| `confirm_concept` | Show `CONCEPT-SYNTHESIS.md` to user. Use AskUserQuestion. STOP. Only after user confirms: `next --confirm` |
| `confirm_template` | Show template + agents to user. Use AskUserQuestion. STOP. Only after user confirms: `next --confirm` |
| `spawn_agents` | For EACH agent: spawn with `name=agent.name, model=agent.model, prompt=agent.prompt`. Write EXACT return to `{output_dir}/{agent.name}.md`. If `parallel: true`, spawn ALL agents simultaneously. |
| `define_tasks` | Read `analyses_summary` from the action response. Read EXISTING `manifest.json` at `manifest_path`, ADD a `tasks` array (preserving all other fields), write back. Each task: `{"id": "T-001", "summary": "...", "files": ["path/to/file"], "acceptance_criteria": ["criterion 1"], "depends_on": [], "tests_needed": true}`. Then call `next`. |
| `confirm_plan` | Show `PLAN.md` + tasks to user. Use AskUserQuestion. STOP. Only after user confirms: `next --confirm` |
| `confirm_demo` | Show demo checklist to user. Use AskUserQuestion. STOP. If user approves: `next --confirm`. If user provides feedback: `next --confirm --feedback "<user text>"`. |
| `demo_feedback` | Pipeline recorded feedback and is marshaling it back to PLAN for revision. Tell user their feedback is being addressed. Call `next`. |
| `demo_replan` | Pipeline is revising the plan based on demo feedback. Tell user: "Your feedback has been recorded. The pipeline is revising the implementation." Call `next`. |
| `confirm_deploy` | Show pre-deploy checklist (secrets, env vars, DNS, placeholders) to user. Use AskUserQuestion. STOP. Only after user confirms: `next --confirm`. Note: if user explicitly said "deploy to X" in their original request, the pipeline auto-deploys and this gate is skipped. |
| `smoke_results` | Show smoke test results to user (all passed). Celebrate the successful deployment. Call `next`. |
| `smoke_failure` | Show failed smoke tests to user. Let user decide: (a) fix issues and redeploy, (b) accept current state and continue. Pass user's choice via `next`. |
| `quality_dashboard` | Show `quality-reports/round-N.md` to user. If converging (P0 count dropping): tell user quality is improving, call `next`. If stuck or P0s persist at round 3: explain to user in plain language, then call `next` (pipeline handles backtrack). |
| `respawn_agent` | An agent timed out. Re-spawn the agent named in `agent_name` with its original prompt and model. Write output to the file in `output_file`. If the response includes `heal_suggestion`, mention to user that auto-recovery is being attempted. Then call `next`. |
| `escalate_to_user` | Show the plain-language explanation and options from the pipeline response. Let user choose an option. If `heal_suggestion` is present, show it as a recommended action. Pass their choice via `next --confirm`. Never add technical detail — use exactly what the pipeline provides. |
| `backtrack_replan` | Tell user: "The current approach isn't working. The pipeline is going back to create a revised plan with what we learned." Call `next`. The pipeline routes back to PLAN with failure context. |
| `learn_complete` | Show `learning-summary.md` to user. Summarize what the project taught QRALPH. Call `next`. |
| `error` | **Read the error carefully.** If this is a verification error (during VERIFY phase), the `message` field tells you exactly what failed — missing criteria, weak evidence, failed ACs, etc. You MUST feed these specific failures back into the next verification attempt. Delete `verification/result.md`, then re-run `next` so the pipeline regenerates the verification agent. The verifier will try again with a fresh prompt. If the error is about implementation bugs (not verification format), fix the code first, then re-run `next`. If the fix is unclear, show the error to the user and ask. |
| `complete` | Show `SUMMARY.md` to user. Done. |

## Deploy Behavior

The DEPLOY phase is intelligent about when to ask:

- **User said "deploy to Cloudflare Workers"** → Explicit intent detected. Pipeline auto-deploys (skips `confirm_deploy` gate). Smoke tests run against live URL.
- **User said "build me a landing page"** (no deploy language) → No deploy intent. Pipeline skips DEPLOY and SMOKE entirely, goes straight to LEARN.
- **User said "build and maybe deploy later"** → Implicit intent. Pipeline shows `confirm_deploy` gate with checklist. User decides.

The pipeline auto-detects the deploy command from project config:
- `wrangler.toml` → `npx wrangler deploy`
- `vercel.json` → `npx vercel --prod`
- `package.json` with `deploy` script → `npm run deploy`

## Smoke Test Behavior

After successful deployment, the pipeline generates **parallel smoke test agents** that hit the live URL:

- Agents are categorized: pages, API, security, SEO, errors
- All agents run **simultaneously** using haiku model (fast + cheap)
- Agents use WebFetch/curl — no source code reading
- Each criterion: PASS (with evidence), FAIL (with details), or SKIP (needs browser JS)
- All PASS → advance to LEARN
- Any FAIL → show to user with options

## Verification Phase Behavior (CRITICAL — read this carefully)

The VERIFY phase is the #1 source of pipeline failures. The verifier agent must check **each acceptance criterion individually** by reading actual source files. Here's what goes wrong and how to handle it:

**Common failure: rubber-stamping.** The verifier writes generic evidence like "Verified in execution outputs" instead of reading files and citing `file:line` references. The pipeline's validation layer catches this and returns an `error` action with specific block reasons (e.g., "evidence depth too weak: 20/25 entries lack file:line references").

**When you receive an `error` during VERIFY phase:**
1. Read the `message` field — it tells you exactly what failed (missing AC results, weak evidence, failed criteria, etc.)
2. Delete `verification/result.md` so the pipeline regenerates a fresh verification prompt
3. Call `next` — the pipeline will re-enter VERIFY and spawn a new verifier agent
4. The new verifier starts fresh and must do the work properly this time

**What "properly" means for verification:**
- The verifier reads each source file with the Read tool (not just execution reports)
- Each AC gets its own read→verify→record cycle — no batching
- Evidence must be `filename.ext:LINE — "quoted code snippet"`
- The pipeline validates: ≥80% of evidence must have `file:line` patterns
- All 6 fields per criterion are required: criterion_index, criterion, status, intent_match, ship_ready, evidence

**Max retries:** 3 verification attempts. After 3 failures, the pipeline escalates to the user with options: accept current state, go back for more fixes, or stop.

## Quality Loop Behavior

The quality loop has two sub-phases. You do not control this logic — the pipeline manages it — but understand what's happening:

**Discovery** (expensive, capped):
- Agents review code in parallel, report P0/P1/P2 findings with confidence scores
- Agents that find nothing drop out (code-reviewer stays 1 extra round)
- Max rounds scale by complexity: 2 (simple), 3 (moderate/complex)
- Early exit on consensus: all agents high confidence + no P0s

**Fix+Verify** (cheap, loops until clean):
- Each finding becomes a fix requirement with a REQ-ID
- TDD: failing test first, then fix, then simplify
- Full test suite must stay green after each fix
- If a fix breaks other tests 3 times: backtrack to replan
- If a fix fails 3 times: escalate to user

**Replan limit:** Max 2 replans per project. After that, escalate to user.

## Project Artifacts

```
project-NNN/
├── IDEATION.md              # Refined concept + business validation
├── personas/                # Persona prompt templates
│   ├── persona-1-sarah.md
│   └── persona-2-alex.md
├── concept-reviews/         # Isolated concept review outputs
│   ├── persona-sarah.md
│   ├── business-advisor.md
│   └── ...
├── CONCEPT-SYNTHESIS.md     # Consolidated concept findings (P0/P1/P2)
├── agent-outputs/           # Planning agent outputs
├── PLAN.md                  # Implementation plan
├── manifest.json            # Project manifest with tasks
├── execution-outputs/       # Per-task implementation outputs
├── quality-reports/         # Per-round quality dashboards
│   ├── round-1.md
│   └── round-2.md
├── POLISH-REPORT.md         # Bug fix + wiring + requirements trace
├── verification/            # Fresh-context verification
│   └── result.md
├── demo/                    # Demo phase feedback files
│   └── feedback.md
├── DEPLOY-REPORT.md         # Deploy command output + live URL
├── smoke-tests/             # Per-category smoke test results
│   ├── smoke-pages.md
│   ├── smoke-api.md
│   ├── smoke-security.md
│   └── smoke-seo.md
├── SMOKE-REPORT.md          # Aggregated smoke test verdict
├── learning-summary.md      # What this project taught QRALPH
├── SUMMARY.md               # Final summary with metrics
└── ...
```

## No-Code User Safety Guarantees (--thorough mode)

These invariants are enforced by the pipeline. You must never circumvent them:

1. **Pipeline never exits with failing tests.** If tests fail, it fixes or escalates.
2. **Every requirement has a test.** The requirements tracer enforces this in POLISH.
3. **Plain-language escalation.** When auto-fix fails, the user gets simple options — never "fix this TypeScript error."
4. **No broken builds.** VERIFY is a hard gate — all checks must pass.
5. **No silent deploys.** Unless user explicitly requested deployment, the pipeline always asks first.
6. **Production is verified.** After deployment, smoke tests confirm the live site works.
7. **Learning accumulates.** Each project improves future projects via LEARN phase.

## What the pipeline enforces (you don't need to)
- Critical agents (sde-iii, architecture-advisor) are always included regardless of template
- Quality gate (tests/lint/typecheck) runs automatically after execution, before verification
- Verification verdict must be explicit PASS — ambiguous or FAIL blocks finalize
- Gate two-call protocol — `--confirm` rejected if gate wasn't returned in prior call
- Deploy intent detection — explicit ("deploy to X") vs implicit vs none
- Deploy command auto-detection from project config (wrangler.toml, vercel.json, package.json)
- Smoke test parallelization and verdict aggregation
- Agent scaling by complexity (fewer agents for simple projects, more for complex)
- Confidence-based consensus for early discovery termination
- State is checkpointed at every transition for crash recovery

## Recovery
```bash
python3 .qralph/tools/qralph-pipeline.py next --project <project_id>
```
(Picks up where it left off — state is in the project directory.)

## Status
```bash
python3 .qralph/tools/qralph-pipeline.py status --project <project_id>
```

## Multi-Project Concurrency

Multiple QRALPH projects can run simultaneously in separate Claude Code sessions. Each session passes `--project <id>` to isolate state:

- Session 1: `next --project 014-redesign-checkout-flow`
- Session 2: `next --project 015-add-notifications`

State is stored per-project in `.qralph/projects/<id>/state.json`. Session locks are also per-project, so projects don't block each other.
