# ai-review-toolkit — usage cheatsheet

When to reach for `/qreview` vs `/qloop` vs `/qpipeline` (and when not to).

> As of **1.2.0**, `/qreview` and `/qloop` run on the ultracode **Workflow** engine.
> `/qpipeline` is unchanged (still a Python driver — its human gates can't pause inside an autonomous Workflow).

## Pick a tool

| You want to… | Use | Edits files? | Cost |
| --- | --- | --- | --- |
| A second opinion / "is this ready?" — surface blind spots, no changes | **`/qreview`** | No (diagnose-only) | Cheapest (1 round) |
| Make it ship-ready — fix ALL findings and prove convergence | **`/qloop`** | **Yes, in place** | ~2–5× qreview |
| A multi-phase flow (execute → review-loop → verify), gate-free *or* with human checkpoints | **`/qpipeline`** | Depends on phases | Medium |
| Concept → deployed, greenfield build | **`/qralph`** | Yes | Heaviest |
| You already have a plan / a small edit | qcode · qcheck | — | — |

**Rule of thumb:** `/qreview` *is* `/qloop` round 1 without the fixer. If you'll act on the findings anyway,
start with `/qloop`. Use `/qreview` when you specifically want to look before touching anything.

## `/qreview` — single-pass multi-agent review

- N clean-context reviewers (each blind to the others) grade the artifact against its requirements, in parallel.
- Findings are validated, deduplicated by **max-severity** (a lone P0 is never downgraded), sorted P0→P3.
- **Diagnose-only** — never edits the artifact. Ends with a scorecard (tokens / USD / time).
- Best for: pre-PR gate, reviewing a spec/strategy doc, "did I miss anything?".

**Example prompts** (just type these — invoking the skill is the opt-in):
```
/qreview review src/auth/session.ts against requirements/current.md
/qreview second opinion on this PRD — docs/prd-billing.md, grade it against docs/prd-billing.rubric.md
/qreview review the changes on this branch against the acceptance criteria in REQ-101..REQ-108
/qreview review src/api/ for security and error handling before I open the PR
```

## `/qloop` — converge until ship-ready

- Loop: review → **fix ALL findings in place** → clean-context re-review, until converged or hard-stop.
- Enforced (in code, not prose): **min 2 rounds**, **fix-ALL gate** (every finding needs FIXED/ESCALATED +
  evidence — no WONTFIX/DEFERRED), **stuck detection** (identical P0/P1 two rounds running → escalate),
  **max-rounds → escalated** (never silently "converged").
- Runs unattended; watch live via `/workflows`. Returns a converged summary or an escalation naming exactly
  what's stuck. Ends with a scorecard.
- Best for: getting a module/doc you're willing to have edited to green.

**Example prompts** (commit or stash first — the fixer edits in place):
```
/qloop converge src/parser.py against requirements/parser.md — fix everything, maxRounds 3
/qloop get docs/strategy.md ship-ready against docs/strategy.rubric.md
/qloop fix all findings in src/checkout/ against requirements/checkout.md until it converges
```

## `/qpipeline` — composable multi-phase flow (unchanged)

- Composable presets that sequence phases; **only the gate phases (`ideate`, `plan`, `demo`, `deploy`)
  pause for you.** Pick a gate-free preset to run start-to-finish with no check-ins.

| Preset | Phases | Checks in? |
| --- | --- | --- |
| `review` | test-gate → review-loop → verify | **No — just goes** |
| `code` | review-loop → test-gate → verify | **No — just goes** |
| `content` | review-loop → verify | **No — just goes** |
| `thorough` | ideate → plan → execute → review-loop → test-gate → verify → demo | Yes (3 gates) |

**Example prompts:**
```
# no check-ins — runs the whole preset to completion:
/qpipeline run the code preset on src/feature/x against requirements/x.md
/qpipeline run the review preset on src/api/ against requirements/api.md

# gated — stops at ideate / plan / demo for your approval:
/qpipeline run the thorough preset to build the billing feature from requirements/billing.md

# your own no-checkin flow (custom phases, no gate phases):
/qpipeline run custom phases execute,review-loop,verify on src/feature/x against requirements/x.md
```

There's no global "auto-confirm all gates" flag — you go gate-free by choosing gate-free phases. Note
`/qpipeline` is still the Python-driver (agent-driven step by step), not the autonomous Workflow that
`/qloop` runs on. For unattended review+fix of a single artifact, prefer `/qloop`.

## Operating notes (the things that bite)

- **Invoking the skill is the opt-in** — just `/qreview` or `/qloop` on an artifact + requirements. No extra
  "ultracode" incantation.
- **`/qloop` edits files in place** (deliberate — fixes must persist across rounds; no worktree isolation).
  **Commit or stash first** so you have a clean rollback point.
- **Requirements matter.** These grade against *stated* requirements. Give a real `requirements/current.md`
  or REQ list — vague requirements produce vague findings.
- **Cost/tiering.** Reviewers default to Sonnet; auto-escalate to Opus for the security/architecture lens,
  or when the change is complex (>1 file, >2 tool-types, >20% of context). Bound `/qloop` cost with
  `maxRounds`. Every run prints a $ scorecard so you see the spend.
- **Type-agnostic.** Point them at code *or* a `.md` spec/strategy doc (with a rubric) — same machinery.
- **Prereq:** the machine's Claude Code must have the Workflow (ultracode) tool. Without it, the skills fall
  back to the legacy Python-driver protocol (`skills/*/driver-fallback.md`).

## Don't use these when…

- You already have a plan and just need to write the code → `qcode`/`qcodet`.
- One-line tweak → just edit it; the orchestrators are overkill.
- You need an interactive, human-gated build → `/qpipeline` or `/qralph`, not `/qloop`.
