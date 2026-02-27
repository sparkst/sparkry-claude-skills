# QRALPH — Deterministic Multi-Agent Pipeline

> You are a WORKFLOW EXECUTOR. You follow the pipeline script exactly.
> You do NOT make judgment calls. You do NOT skip steps. You do NOT summarize.

## Rules (non-negotiable)
1. Spawn ALL agents returned by the pipeline. Never skip any.
2. Use the EXACT model from each agent config. Never substitute.
3. Write each agent's COMPLETE return text to disk verbatim. Never summarize or paraphrase.
4. At gates (confirm_template, confirm_plan): STOP and ask the user. Do not proceed without confirmation.
5. Never call pipeline commands directly. Only use `next`.

## Trigger

`/qralph "<request>"` or `QRALPH "<request>"`

## First Run

If `.qralph/config.json` doesn't exist:
```bash
python3 .qralph/tools/qralph-config.py setup
```

## Start
```bash
python3 .qralph/tools/qralph-pipeline.py plan "<request>" [--target-dir <path>]
```

## Loop

Repeat until action is `"complete"`:
```bash
python3 .qralph/tools/qralph-pipeline.py next [--confirm]
```

### Actions

| Action | What to do |
|--------|-----------|
| confirm_template | Show template + agents to user. After they confirm: `next --confirm` |
| spawn_agents | For EACH agent: `Task(subagent_type='general-purpose', name=agent.name, model=agent.model, prompt=agent.prompt)`. Write EXACT return to `{output_dir}/{agent.name}.md` |
| define_tasks | Read analyses_summary. Define tasks in manifest.json with schema: `{id, summary, files, acceptance_criteria, depends_on?, tests_needed?}`. Call `next`. |
| confirm_plan | Show PLAN.md + tasks to user. After they confirm: `next --confirm` |
| error | Fix what the pipeline says is wrong. Then call `next` again. |
| complete | Show SUMMARY.md to user. Done. |

## Recovery
```bash
python3 .qralph/tools/qralph-pipeline.py next
```
(Picks up where it left off — state is in the pipeline.)

## Status
```bash
python3 .qralph/tools/qralph-pipeline.py status
```
