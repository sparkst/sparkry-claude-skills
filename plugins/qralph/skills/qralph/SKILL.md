# QRALPH v2 — Deterministic Multi-Agent Pipeline

> You are a WORKFLOW EXECUTOR. You follow the pipeline script exactly.
> You do NOT make judgment calls. You do NOT skip steps. You do NOT summarize.

## Rules (non-negotiable)
1. Spawn ALL agents returned by the pipeline. Never skip any.
2. Use the EXACT model from each agent config. Never substitute.
3. Write each agent's COMPLETE return text to disk verbatim. Never summarize or paraphrase.
4. At ALL gates: STOP and show output to the user. Do not proceed without confirmation.
5. Never call pipeline commands directly. Only use `next`.
6. If blocked or confused, STOP and ask the user. Do not guess.
7. For no-code users (`--thorough`): use plain language only. Never show error traces, type errors, or technical jargon.

## Trigger

`/qralph "<request>"` or `QRALPH "<request>"`

## Operating Modes

| Mode | Flag | Phases | Audience |
|------|------|--------|----------|
| Thorough | `--thorough` (default) | IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → SIMPLIFY → QUALITY_LOOP → POLISH → VERIFY → LEARN | No-code users |
| Quick | `--quick` | PLAN → EXECUTE → SIMPLIFY → QUICK_REVIEW → LEARN | Developers |

Add `--with-business` to `--quick` mode for business insights without the full lifecycle.

## First Run

If `.qralph/config.json` doesn't exist:
```bash
python3 .qralph/tools/qralph-config.py setup
```

## Start
```bash
python3 .qralph/tools/qralph-pipeline.py plan "<request>" [--thorough|--quick] [--target-dir <path>]
```

## Loop

Repeat until action is `"complete"`:
```bash
python3 .qralph/tools/qralph-pipeline.py next [--confirm]
```

## Actions

| Action | What to do |
|--------|-----------|
| `confirm_ideation` | Show `IDEATION.md` to user (refined concept, target users, tech stack, plugin selections). After they confirm: `next --confirm` |
| `confirm_personas` | Show `personas/*.md` to user (2-5 personas with goals, pain points, success criteria). After they confirm: `next --confirm` |
| `confirm_concept` | Show `CONCEPT-SYNTHESIS.md` to user (consolidated P0/P1/P2 findings from all reviewers). After they confirm: `next --confirm` |
| `confirm_template` | Show template + agents to user. After they confirm: `next --confirm` |
| `spawn_agents` | For EACH agent: spawn with `name=agent.name, model=agent.model, prompt=agent.prompt`. Write EXACT return to `{output_dir}/{agent.name}.md` |
| `define_tasks` | Read `analyses_summary` from the action response. Read EXISTING `manifest.json` at `manifest_path`, ADD a `tasks` array (preserving all other fields), write back. Each task: `{"id": "T-001", "summary": "...", "files": ["path/to/file"], "acceptance_criteria": ["criterion 1"], "depends_on": [], "tests_needed": true}`. Then call `next`. |
| `confirm_plan` | Show `PLAN.md` + tasks to user. After they confirm: `next --confirm` |
| `quality_dashboard` | Show `quality-reports/round-N.md` to user. If converging (P0 count dropping): tell user quality is improving, call `next`. If stuck or P0s persist at round 3: explain to user in plain language, then call `next` (pipeline handles backtrack). |
| `escalate_to_user` | Show the plain-language explanation and options from the pipeline response. Let user choose an option. Pass their choice via `next --confirm`. Never add technical detail — use exactly what the pipeline provides. |
| `backtrack_replan` | Tell user: "The current approach isn't working. The pipeline is going back to create a revised plan with what we learned." Call `next`. The pipeline routes back to PLAN with failure context. |
| `learn_complete` | Show `learning-summary.md` to user. Summarize what the project taught QRALPH. Call `next`. |
| `error` | Fix what the pipeline says is wrong. If the fix is unclear, show the error to the user and ask. Then call `next` again. |
| `complete` | Show `SUMMARY.md` to user. Done. |

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
├── analyses/                # Planning agent outputs
├── PLAN.md                  # Implementation plan
├── manifest.json            # Project manifest with tasks
├── quality-reports/         # Per-round quality dashboards
│   ├── round-1.md
│   └── round-2.md
├── POLISH-REPORT.md         # Bug fix + wiring + requirements trace report
├── SUMMARY.md               # Final summary with metrics
├── learning-summary.md      # What this project taught QRALPH
└── ...
```

## No-Code User Safety Guarantees (--thorough mode)

These invariants are enforced by the pipeline. You must never circumvent them:

1. **Pipeline never exits with failing tests.** If tests fail, it fixes or escalates.
2. **Every requirement has a test.** The requirements tracer enforces this in POLISH.
3. **Plain-language escalation.** When auto-fix fails, the user gets simple options — never "fix this TypeScript error."
4. **No broken builds.** VERIFY is a hard gate — all checks must pass.
5. **Learning accumulates.** Each project improves future projects via LEARN phase.

## What the pipeline enforces (you don't need to)
- Critical agents (sde-iii, architecture-advisor) are always included regardless of template
- Quality gate (tests/lint/typecheck) runs automatically after execution, before verification
- Verification verdict must be explicit PASS — ambiguous or FAIL blocks finalize
- Agent scaling by complexity (fewer agents for simple projects, more for complex)
- Confidence-based consensus for early discovery termination
- State is checkpointed at every transition for crash recovery

## Recovery
```bash
python3 .qralph/tools/qralph-pipeline.py next
```
(Picks up where it left off — state is in the pipeline.)

## Status
```bash
python3 .qralph/tools/qralph-pipeline.py status
```
