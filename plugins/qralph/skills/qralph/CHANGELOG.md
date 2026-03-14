# QRALPH Changelog

## v6.9.0 (2026-03-14)

### Fixed — Silent Quality Loop Degradation
- **Hard dependency on `quality-dashboard.py`**: Previously, if `quality-dashboard.py` was missing, the pipeline silently set `parse_findings`, `check_convergence`, `should_agent_continue`, `generate_dashboard`, and `deduplicate_findings` to `None`. This caused the quality loop to auto-converge with zero structured findings — all P1s and P2s were silently dropped. Now raises `FileNotFoundError` at startup with a clear message to update the QRALPH plugin.
- **Incident**: Jarvis project 025 ran a quality review that surfaced 12 P0s but silently lost 20+ P1s and 10+ P2s due to the missing module.

## v6.8.1 (2026-03-14)

### Improved — Skill Quality and Model Guidance
- **YAML frontmatter**: Added `name` and `description` fields for proper skill auto-triggering. Previously the skill could only be invoked via explicit `/qralph` command.
- **Explanatory tone**: Replaced commanding language ("You are a dumb executor", "non-negotiable") with reasoning that explains *why* determinism matters — specifically how freelancing wastes tokens when 5+ parallel agents receive invalid context from a deviated executor.
- **Progressive disclosure**: Extracted verification troubleshooting, quality loop internals, and smoke test details into `references/phase-troubleshooting.md`. SKILL.md reduced from 286 to 231 lines while preserving all functionality.
- **Deduplicated instructions**: "Don't leave the pipeline loop" was stated 3 times; consolidated into single "Session Ownership" section with architectural reasoning.
- **Test fix**: `test_version_in_title` now handles YAML frontmatter by searching for the first `# ` heading instead of checking `first_line`.

## v6.8.0 (2026-03-14)

### Added — DEMO Phase, Domain Personas, Evidence Hardening
- **DEMO phase**: New 14th pipeline phase between VERIFY and DEPLOY. Presents completed work to user with feedback loop (max 2 cycles). Sub-phases: DEMO_PRESENT → DEMO_FEEDBACK → DEMO_MARSHAL.
- **Domain persona archetypes**: `suggest_archetypes()` maps project keywords to pre-built persona sets (SaaS, ecommerce, CLI, API, mobile, security, content). Used in PERSONA phase for automatic generation.
- **Evidence pattern hardening**: `_EVIDENCE_PATTERN` now uses a whitelist of source file extensions, preventing URLs (`example.com:443`) and IP:port pairs from bypassing the evidence gate.
- **QUALITY_REVERIFY sub-phases**: Added to `VALID_SUB_PHASES` — state machine no longer rejects reverify transitions.
- **Idempotent lock release**: `_release_session_lock()` uses a guard flag to prevent double-release anti-pattern from atexit + explicit calls.
- **Convergence fallback completeness**: Fallback dict when `check_convergence` is unavailable now includes `stagnant` and `regressed` keys, preventing silent skip of stagnation detection.
- **CLI keyword specificity**: Replaced generic "tool" with "cli-tool", "shell", "argv" in persona archetype matching to reduce false positives.
- **Persona shim documentation**: Import shim for hyphenated filename now explains why it exists and how degradation works.
- **547 tests passing** (8 new: 3 evidence false-positive, 1 VALID_SUB_PHASES, 1 lock idempotency, 2 CLI keyword, 1 convergence fallback).

## v6.6.3 (2026-03-06)

### Added — Quality Bar Enforcement (Project 045)
- **QUALITY_STANDARD constant**: Module-level production quality bar injected into every agent prompt (6 points: execution, verify, quality loop, 3 POLISH agents). Includes anti-shortcut patterns preventing AI from assuming speed over quality.
- **Request fragmentation**: `_fragment_request()` splits user requests into numbered REQ-F-N tuples at sentence/clause boundaries, numbered lists, semicolons. Stored in pipeline state at plan time so dropped requirements cannot escape detection.
- **3-dimension verification**: Every AC graded on IMPLEMENTED + INTENT_MATCH + SHIP_READY. Verifier must ask: "Did we deliver what this person wanted, or what was convenient?"
- **Hard structural enforcement**: `intent_match=false` or `ship_ready=false` is a hard FAIL. Evidence depth must be 80%+ strong (file:line references). Missing/partial request fragments block finalization.
- **POLISH retry enforcement**: NEEDS_ATTENTION verdict triggers retry (cap: 2) with gap logging to decisions.log. After cap, escalates to user with plain-language explanation instead of silently advancing.
- **12 canonical tests** proving the quality bar cannot be bypassed. 469 total tests passing.

## v6.6.2 (2026-03-05)

### Fixed — Pipeline Determinism (COE from Project 019)
- **Quality re-verification**: New QUALITY_REVERIFY sub-phase spawns haiku verifier per P0/P1 finding before advancing to dashboard. Conservative default: findings without evidence remain unresolved.
- **P0 escalation at max rounds**: When quality rounds exhausted with P0s still open, pipeline escalates to user with plain-language options instead of silently advancing to POLISH.
- **Evidence metrics**: `_compute_evidence_metrics()` scans agent-outputs/ for real word counts and EQS. No more `?/?` placeholders in SUMMARY.md. Orchestrator recomputes EQS at finalize time.
- **Deterministic shutdown**: `_pipeline_shutdown()` releases session lock, records timestamp, clears agents. SUMMARY.md includes Lifecycle section confirming cleanup.
- **Anti-bulk-stamp**: `MAX_BULK_REMEDIATE = 5` rejects mass remediation without `--batch` flag. Suspicious timing (all tasks fixed within 60s window) detected and logged to decisions.log.
- **Test coverage**: 20 new tests covering all 5 determinism fixes. 603 total tests passing.

### Fixed (COE from Project 041)
- **Agent watchdog**: Per-agent timeout detection with model-tier thresholds (opus=900s, sonnet=400s, haiku=180s). First timeout re-spawns with `.hung.md` preservation; second escalates to user.
- **Quality gate CWD**: Containment check on all CWD paths (manifest and auto-detected). Symlink resolution in subdirectory scan. `site_dir` parameter for explicit project targeting.
- **Gate effectiveness**: `detect_quality_gate()` returns `effective` field. Missing linter config logged as `[WARN]` (excluded from convergence).
- **Convergence tracking**: `compute_finding_deltas()` pure function classifies findings as NEW/CARRY_FORWARD/FIXED. Regression detection (P0 increase at round >= 3). Stagnation detection with configurable threshold.
- **Self-healing**: Python constant rulebook with action enum allowlist. 60-minute heal cooldown. LEARN phase restricted to counter updates only.
- **Session lock safety**: try/finally + atexit.register for lock release on exceptions.
- **VALID_PHASES**: Added DEPLOY and SMOKE (was causing checkpoint corruption on resume).
- **should_backtrack**: Fires at round >= 2 for SP <= 2 tasks (was round >= 3 unconditionally).

## v6.6.1 (2026-03-01)

### Idea to Production — DEPLOY + SMOKE Phases

v6.6.1 closes the loop from idea to production-verified. Two new phases after VERIFY:

#### 13-Phase Pipeline
```
IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → SIMPLIFY →
QUALITY_LOOP → POLISH → VERIFY → DEPLOY → SMOKE → LEARN → COMPLETE
```

#### DEPLOY Phase (3 sub-phases)
- **DEPLOY_PREFLIGHT**: Detect deploy intent from request, find deploy command from project config (wrangler.toml, vercel.json, package.json), generate pre-deploy checklist
- **DEPLOY_GATE**: Confirmation gate — skipped if user explicitly said "deploy to X", shown if implicit
- **DEPLOY_RUN**: Execute deploy command, capture output, extract live URL, write DEPLOY-REPORT.md

#### SMOKE Phase (3 sub-phases)
- **SMOKE_GENERATE**: Generate parallel smoke test agents from manifest ACs, categorized (pages, API, security, SEO, errors), all using haiku for speed
- **SMOKE_WAIT**: Validate all smoke agent outputs collected
- **SMOKE_VERDICT**: Aggregate PASS/FAIL/SKIP results, write SMOKE-REPORT.md, advance or show failures

#### Two-Call Gate Enforcement (COE fix)
All 6 confirmation gates now use a two-call protocol:
1. First `next` → pipeline returns gate action, sets `awaiting_confirmation` in state
2. Only a subsequent `next --confirm` is accepted — same-turn `--confirm` is rejected with error

This prevents the orchestrator from skipping gates. The pipeline itself enforces the round-trip.

#### Deploy Intent Detection
- **Explicit** ("deploy to Cloudflare Workers") → auto-deploy, skip gate
- **Implicit** ("deploy", "ship it", "go live") → show `confirm_deploy` gate
- **None** ("build me a page") → skip DEPLOY and SMOKE entirely

### Breaking Changes
- PHASES list expanded from 11 to 13 entries
- `cmd_finalize` now accepts phases VERIFY, DEPLOY, SMOKE, or LEARN (was VERIFY only)
- `_next_verify_wait` advances to DEPLOY instead of calling `cmd_finalize`
- All confirm gates now require two-call protocol (existing `--confirm` without prior gate return will error)

## v6.6.0 (2026-03-01)

### Exclusive Mode Enforcement

- Add EXCLUSIVE MODE directive to SKILL.md — when QRALPH is active, Claude must not invoke other skills from the outer loop. Skills/plugins inside pipeline-spawned agents remain available.
- Add Rule #8: never leave the pipeline loop to invoke other skills or workflows.
- Wire enforcement hooks (stop-blocker, write-validator, agent-validator) into `.claude/settings.local.json` — hooks were previously defined but never loaded.

## v6.5.0 (2026-03-01)

### Full-Lifecycle 10-Phase Pipeline

v6.5.0 replaces the 3-phase pipeline (PLAN/EXECUTE/VERIFY) with a full-lifecycle 10-phase pipeline that covers ideation through learning.

#### 10-Phase Pipeline
```
IDEATE → PERSONA → CONCEPT_REVIEW → PLAN → EXECUTE → SIMPLIFY → QUALITY_LOOP → POLISH → VERIFY → LEARN
```

#### Two Operating Modes
- **`--thorough`** (default): All 10 phases with adaptive quality loops and cross-project learning
- **`--quick`**: Streamlined path skipping PERSONA, CONCEPT_REVIEW, SIMPLIFY, and LEARN phases

#### 6 New Tools
- **`plugin-detector`**: Auto-discovers installed Claude Code plugins and available MCP servers
- **`persona-generator`**: Creates synthetic user personas for concept review and usability testing
- **`quality-dashboard`**: Aggregates quality metrics across pipeline phases into a unified dashboard
- **`confidence-scorer`**: Scores agent output confidence with calibrated thresholds per phase
- **`requirements-tracer`**: Traces requirements through plan tasks, execution outputs, and verification
- **`learning-capture`**: Captures cross-project learnings (patterns, anti-patterns, heuristics) for reuse

#### Adaptive Quality Loop
- Discovery/fix separation: first pass identifies all issues, second pass fixes them
- Backtrack-to-replan mechanism: if quality loop discovers architectural issues, pipeline backtracks to PLAN
- Configurable iteration limits with diminishing-returns detection

#### Cross-Project Learning
- `learning-capture` persists patterns and anti-patterns across QRALPH runs
- Learnings are injected into PLAN and EXECUTE phases for subsequent projects
- Automatic relevance scoring ensures only applicable learnings surface

#### Test Suite
- **350 tests** (up from ~160 in v6.2.0)
- New test files: `test_confidence_scorer.py`, `test_learning_capture.py`, `test_persona_generator.py`, `test_plugin_detector.py`, `test_quality_dashboard.py`, `test_requirements_tracer.py`
- Heavily expanded `test_qralph_pipeline.py` covering all 10 phases and mode switching

#### Modified Files
- `qralph-pipeline.py` — Complete rewrite: 10-phase state machine, --thorough/--quick modes, backtrack-to-replan
- `qralph-state.py` — New phases added to VALID_PHASES
- `test_qralph_pipeline.py` — Heavily expanded with 10-phase coverage
- `SKILL.md` — Updated for 10-phase pipeline and new tool documentation

#### New Files
- `confidence-scorer.py` + `confidence_scorer.py` (import shim)
- `learning-capture.py` + `learning_capture.py` (import shim)
- `persona-generator.py` + `persona_generator.py` (import shim)
- `plugin-detector.py` + `plugin_detector.py` (import shim)
- `quality-dashboard.py` (no import shim)
- `requirements-tracer.py` + `requirements_tracer.py` (import shim)

---

## v6.2.0 (2026-02-27)

### Security & Bug Fixes from PE Review

v6.1.1 was reviewed by a clean-context PE agent that found 23 issues (3 P0, 11 P1, 9 P2). v6.2.0 fixes the critical ones.

#### Active Bugs Fixed (F-13, F-18)
- **Filename mismatches**: Pipeline expected `verification/result.md` but agent was named `verifier` (wrote `verifier.md`). Fixed: `"name": "verifier"` → `"name": "result"`. Same issue for execution agents: `"name": "impl-T1"` → `"name": "T1"` to match `execution-outputs/{tid}.md`.
- **Hook updated**: `hook-validate-agent.py` now expects `"result"` instead of `"verifier"` during VERIFY_WAIT.

#### Security (F-01, F-02)
- **Shell injection (F-01)**: Quality gate command was read from `manifest.json` (written by Claude) and passed to `subprocess.run(shell=True)`. Fixed: `detect_quality_gate()` is now recomputed at runtime from project structure, never read from manifest.
- **Verdict regex bypass (F-02)**: The regex `"verdict"\s*:\s*"PASS"` could match anywhere in prose. New `_parse_verdict()` function: extracts JSON code blocks → `json.loads()` → checks `data["verdict"]`, with raw JSON and regex fallback. Used in both `_next_verify_wait` and `cmd_finalize`.

#### Validation (F-03, F-06)
- **Minimum output length (F-03)**: Agent outputs shorter than 100 chars are rejected with a named error. Checked in both `_next_plan_waiting` and `_next_exec_waiting`.
- **Task schema validation (F-06)**: `_validate_tasks()` checks each task has `id`, `summary`, `files` (list), `acceptance_criteria` (non-empty list). Called in `cmd_plan_finalize`.

#### Path Safety (F-15)
- **Consistent `_safe_project_path()`**: Replaced 7 raw `Path(state["project_path"])` calls with `_safe_project_path(state)` wrapped in `try/except ValueError`. Functions: `cmd_plan_finalize`, `cmd_execute`, `cmd_execute_collect`, `cmd_verify`, `cmd_finalize`, `cmd_resume`, `cmd_status`.

#### State (F-05, F-21)
- **Pipeline phases in VALID_PHASES (F-05)**: Added `"PLAN"`, `"EXECUTE"`, `"VERIFY"` to `qralph-state.py` `VALID_PHASES`.
- **Module `__version__` (F-21)**: Added `__version__ = "6.2.0"` at module level. Used in `_init_project` and CLI description.

#### SKILL.md Improvements
- **Rule 6**: "If blocked or confused, STOP and ask the user. Do not guess."
- **define_tasks**: "Read EXISTING manifest.json, ADD tasks array (preserving all other fields), write back."
- **error**: "If fix is unclear, show the error to the user and ask."

#### Tests (~15 new)
- `TestMinimumOutputLength` (3): Short output rejected, long output accepted (plan + exec)
- `TestTaskValidation` (4): Missing id/summary/files/criteria rejected, valid passes
- `TestVerdictParsing` (5): JSON block, raw JSON, no verdict, regex fallback, prose bypass
- `TestQualityGateRecomputation` (1): Gate recomputed at runtime, not read from manifest

#### Modified Files
- `qralph-pipeline.py` — All 6 batches
- `test_qralph_pipeline.py` — Batch 1 refs + Batch 6 new tests
- `qralph-state.py` — VALID_PHASES
- `hook-validate-agent.py` — verifier → result
- `SKILL.md` — Rule 6, define_tasks, error improvements
- `VERSION` — 6.2.0

---

## v6.1.0 (2026-02-26)

### Pipeline-Driven Deterministic Workflow

v6.0 had detailed orchestration instructions in SKILL.md that Claude consistently freelanced on — skipping agents, wrong models, summarizing outputs, blowing through gates. Root cause: Claude is a conversational agent making judgment calls, but QRALPH needs a dumb workflow executor. v6.1 fixes this with three enforcement layers.

#### Layer 1: `cmd_next()` State Machine

New `next [--confirm]` command returns exactly one action at a time. The pipeline validates the previous step completed correctly before advancing.

- **Sub-phase state machine**: INIT → PLAN_WAITING → PLAN_REVIEW → EXEC_WAITING → VERIFY_WAIT → COMPLETE
- **Gate confirmation**: `--confirm` flag required at INIT and PLAN_REVIEW gates
- **Output validation**: `check_outputs` validates files exist and are non-empty before advancing
- **Auto-advance**: PLAN_COLLECT, PLAN_FINAL, EXEC_NEXT, FINALIZE run internally
- **Error recovery**: Returns `{"action": "error", "message": "..."}` on missing outputs

#### Layer 2: Thin SKILL.md (~50 lines)

Replaced the ~100 line SKILL.md with a stern preamble + simple loop: call `next`, do exactly what it says. Five non-negotiable rules prevent deviation.

#### Layer 3: Enforcement Hooks

- **`hook-validate-agent.py`** (SubagentStop): Validates spawned agents match pipeline expectations
- **`hook-validate-stop.py`** (Stop): Blocks session exit if pipeline is mid-phase
- **`hook-validate-write.py`** (PostToolUse/Write): Validates output file paths match expected directories
- **`hooks.json`**: Hook configuration for plugin deployment

#### Model Selection

- Plan agents: `opus` (thinking work needs the best model, was `sonnet`)
- Execute agents: `sonnet` (implementation, unchanged)
- Verifier: `sonnet` (unchanged)

#### New Files
- `.qralph/tools/hook-validate-agent.py` — SubagentStop validation
- `.qralph/tools/hook-validate-stop.py` — Stop validation
- `.qralph/tools/hook-validate-write.py` — Write path validation
- `.qralph/tools/hooks.json` — Hook configuration

#### Modified Files
- `qralph-pipeline.py` — `cmd_next()` state machine, `next` CLI subcommand, plan agents → opus
- `test_qralph_pipeline.py` — 15 new tests for state machine transitions and model verification
- `SKILL.md` — Rewritten to thin deterministic loop
- `VERSION` — 6.0.0 → 6.1.0

---

## v6.0.0 (2026-02-26)

### Breaking Change — Full Rewrite to Deterministic Pipeline

v5.1 had a ~28% success rate. Root cause: the Python tools output JSON instructions but Claude had to interpret and execute 7+ non-deterministic steps between each Python call. v6.0 rewrites the entire system so Python does orchestration and Claude does thinking.

#### Architecture: 3-Phase Pipeline

```
PLAN ──gate──> EXECUTE ──gate──> VERIFY
```

- **PLAN**: Script suggests template, generates agent prompts. Claude spawns agents mechanically, writes outputs, script computes execution manifest.
- **EXECUTE**: Script computes parallel groups (file-overlap analysis). Claude spawns implementation agents per group.
- **VERIFY**: Script generates verification prompt. One fresh-context agent validates all acceptance criteria.

#### New Files
- `qralph-pipeline.py` — Single entry point for all pipeline commands (~550 lines)
- `qralph-config.py` — First-run setup, research tool detection (~130 lines)
- `test_qralph_pipeline.py` — 62 tests covering templates, parallel groups, prompts, phase gating, resume

#### Deleted (~9,600 lines removed)
- `qralph-orchestrator.py` (3,163 lines) — replaced by qralph-pipeline.py
- `qralph-subteam.py` (752 lines) — sub-team lead layer eliminated
- `qralph-healer.py` (1,124 lines) — pipeline handles errors directly
- `qralph-watchdog.py` (608 lines) — pipeline does its own checks
- `pe-overlay.py` (1,229 lines) — PE ceremony removed
- `codebase-nav.py` (533 lines) — not needed
- `qralph-status.py` (387 lines) — pipeline has built-in status
- All corresponding test files (~3,700 lines)
- `qralph-team-lead.md`, `qralph-validator.md` agents
- `.qralph/templates/` (DoD templates)

#### Kept (with simplification)
- `qralph-state.py` — Atomic writes, checksums, locking (updated phases)
- `session-state.py` — Simplified for 3-phase model
- `process-monitor.py` — Orphan cleanup (unchanged)
- `qralph-version-check.py` — Version sync (unchanged)

#### Key Improvements
- **Template-based agent selection** replaces non-deterministic keyword matching
- **Deterministic parallel groups** computed from file-overlap analysis
- **Research tool detection** from `~/.claude/settings.json` enabled plugins
- **Phase gating** enforced by script (can't execute without plan, can't verify without execute)
- **Session recovery** via checkpoint files and `resume` command
- **Quality gate detection** for npm, pytest, cargo, go, make projects

---

## v5.1.0 (2026-02-24)

### Breaking Change — All PE Overlay Features Now Enforced

v5.0 introduced PE overlay features as advisory. v5.1 makes them **blocking**. Sessions can no longer ignore gates, skip COE, bypass pattern sweeps, or finalize without validation.

#### Enforcement Changes
- **PE gates block phase transitions**: If `run_gate()` returns blockers, the `checkpoint` command fails with an error. No bypass.
- **COE required before `remediate-done`**: Cannot mark tasks fixed without a COE analysis file. Returns error listing missing COE task IDs.
- **Pattern sweep required before `remediate-done`**: Cannot mark tasks fixed without a pattern sweep result file. Returns error listing missing sweep task IDs.
- **VALIDATING phase mandatory before `finalize`**: Coding-mode projects must produce `phase-outputs/VALIDATING-result.json` before finalize is allowed.
- **Phase transitions tightened**: REVIEWING can only go to EXECUTING (not directly to COMPLETE). EXECUTING can only go to VALIDATING (not directly to COMPLETE). UAT goes to VALIDATING (not directly to COMPLETE).
- **PE gate import failure is a blocker**: If `pe_overlay.py` can't be imported, `run_pe_gate()` returns a blocker instead of silently passing.

#### New Artifacts
- `pattern-sweeps/<task_id>.json` — persisted sweep results (checked by `remediate-done`)
- `coe-analyses/<task_id>.json` — COE analysis files (checked by `remediate-done`)

#### Test Updates
- Version detection test updated for v5.1
- Phase transition tests updated: REVIEWING→VALIDATING now blocked (must go through EXECUTING)
- All 125 PE overlay tests pass, all 46 subteam tests pass

---

## v5.0.0 (2026-02-24)

### New Features — PE Overlay Agent Architecture

QRALPH v5.0 infuses Principal Engineer practices via a PE Overlay that runs at every phase transition, enforcing architectural consistency, deep root-cause analysis, and completion rigor.

#### PE Overlay Gate (`pe-overlay.py`)
- **Phase transition gates**: Deterministic Python checks run at every phase transition (INIT→DISCOVERING, DISCOVERING→REVIEWING, etc.)
- **ADR loading and enforcement**: Loads Architecture Decision Records from `docs/adrs/`, checks agent findings against them, proposes new ADRs for architectural decisions
- **DoD template system**: Auto-detects project type (webapp/api/library) and selects appropriate Definition of Done checklist. Testing and Security items are blockers.
- **Requirements inference**: Detects implicit requirements from request text and technology stack (Stripe→test mode, Cloudflare→wrangler dev, etc.)
- **Codebase navigation strategy**: Auto-selects ts-aware, polyglot, or grep-enhanced search strategy based on project structure

#### COE / 5-Whys System
- **Root cause analysis**: Before marking remediation tasks fixed, create COE analysis with structured 5-Whys
- **Pattern scope identification**: COE analyses identify where else the same pattern exists in the codebase
- **Validation**: COE structure validated (required fields, non-empty root cause and search patterns)

#### Pattern Sweep
- **Automated sweep**: After fixing a task, searches codebase for remaining instances of the same pattern
- **Scope control**: File, directory, or repo-wide sweep
- **Integration**: Uses `codebase-nav.py` adaptive search strategies

#### Codebase Navigation (`codebase-nav.py`)
- **Strategy detection**: ts-aware (TypeScript imports/exports), polyglot (multi-language), grep-enhanced (smart ripgrep)
- **TypeScript features**: Import parsing, path alias resolution, dependency graph construction
- **Ripgrep integration**: Fast search with JSON output, fallback to Python when rg unavailable

#### Quality Gate Enhancement (7 criteria)
- **Check 6**: ADR consistency — agent findings don't contradict accepted ADRs
- **Check 7**: DoD template compliance — Testing and Security categories addressed
- **pe-reviewer promoted to CRITICAL_AGENTS** (joins security-reviewer, architecture-advisor, sde-iii)
- **Check 5 strengthened**: PE risk assessment now requires structured validation, not just keyword presence

#### CLI Usability
- **`init --request` alias**: `init` now accepts both positional and `--request` flag arguments, preventing the common Claude invocation error

#### New Commands
- `pe-gate --from-phase X --to-phase Y` — Run PE overlay gate check manually
- `coe-analyze --task REM-NNN [--validate]` — Create or validate COE analysis
- `pattern-sweep --task REM-NNN [--scope repo]` — Run pattern sweep for a task
- `adr-check --approve NNN` — Approve a proposed ADR
- `adr-list` — List all loaded ADRs

### New Files
- `.qralph/tools/pe-overlay.py` — Core PE gate logic (~600 lines)
- `.qralph/tools/codebase-nav.py` — Adaptive codebase navigation (~300 lines)
- `.qralph/tools/test_pe_overlay.py` — ~125 tests
- `.qralph/tools/test_codebase_nav.py` — ~46 tests
- `.qralph/templates/dod-webapp.md` — DoD for web applications
- `.qralph/templates/dod-api.md` — DoD for API/backend services
- `.qralph/templates/dod-library.md` — DoD for libraries/packages
- `.claude/agents/pe-overlay.md` — PE overlay reasoning agent prompt

### Modified Files
- `qralph-orchestrator.py` — PE overlay import, gate hooks, 5 new commands, init --request alias, v5.0.0
- `qralph-subteam.py` — Quality gate 5→7 criteria, pe-reviewer in CRITICAL_AGENTS, structured Check 5
- `qralph-watchdog.py` — PE overlay health checks, new preconditions (coe_analysis_exists, adrs_loaded)
- `qralph-state.py` — Extended state schema with pe_overlay, adrs, dod_template, coe_analyses defaults
- `SKILL.md` — v5.0.0, new execution rules 13-16, PE Overlay section, new commands reference
- `pe-reviewer.md` — ADR enforcement context

### Backward Compatibility
- All new state fields optional with empty/None defaults
- v4.1.x projects load without error — PE gates gracefully skip when no ADRs/DoD exist
- Quality gate checks 6-7 auto-pass when PE overlay data absent
- Existing 5 quality gate checks unchanged

### Test Results
- ~600+ tests passing (125 pe-overlay + 46 codebase-nav + existing 450+)

## v4.1.4 (2026-02-18)

### Fixed — Finalize Remediation Gate

- **Finalize blocks on open remediation tasks**: `cmd_finalize` now checks for open remediation tasks at the active `fix_level` before allowing transition to COMPLETE. Previously, `finalize` would happily mark a project complete even with dozens of unfixed P0/P1 tasks — the LLM could skip execution entirely after planning. Now the orchestrator enforces completion.
- **Resume includes remediation progress**: `cmd_resume` output now includes a `remediation_progress` object showing total/fixed/open task counts, blocking IDs, and a warning message. This ensures resumed sessions know exactly where to pick up.
- **SKILL.md Rules 10-11**: Added mandatory execution rules:
  - Rule 10: EXECUTING must complete before finalize — `remediate-verify` must return `"verified"` first
  - Rule 11: Session boundary discipline — checkpoint and inform user when interrupted mid-execution

### Modified Files
- `qralph-orchestrator.py` — Remediation gate in `_cmd_finalize_locked`, remediation progress in `_cmd_resume_locked`, VERSION bump
- `SKILL.md` — Execution Rules 10-11, version bumps
- `test_qralph_orchestrator.py` — 4 new tests: finalize blocks on open tasks, finalize allows lower-priority open, finalize succeeds with no tasks, resume includes progress

### Test Results
- 416 tests passing (211 orchestrator + 205 other, 0 regressions)

## v4.1.3 (2026-02-18)

### Fixed — Automatic Process Cleanup
- **Process sweep on init/resume/finalize**: `cmd_init`, `cmd_resume`, and `cmd_finalize` now automatically call `process_monitor.cmd_sweep()` to clean up orphaned processes from previous/crashed runs. Previously the process monitor existed but was never invoked automatically — users had to manually run `process-monitor.py sweep`.
- **Safe import**: Process monitor is imported at module level; `sweep_orphaned_processes()` wrapper catches exceptions so a missing/broken process-monitor.py never blocks orchestration.
- **SKILL.md Rule 9**: Added execution rule documenting automatic process cleanup.

### Modified Files
- `qralph-orchestrator.py` — Import process_monitor, `sweep_orphaned_processes()` helper, calls in `cmd_init`, `cmd_resume`, `cmd_finalize`, VERSION bump
- `SKILL.md` — Execution Rule 9 (process cleanup), version bump
- `test_qralph_orchestrator.py` — 3 new tests: sweep on init, sweep on resume, sweep on finalize

### Test Results
- 447 tests passing (444 existing + 3 new, 0 regressions)

## v4.1.2 (2026-02-18)

### New Features
- **`--fix-level` flag**: Control which findings get remediated: `none` (skip fixes), `p0` (critical only), `p0_p1` (default), `all` (P0+P1+P2). Stored in state, enforced by `cmd_remediate` and `cmd_remediate_verify`.
- **Status findings summary**: `cmd_status` now includes a `_status_summary` section with P0/P1/P2 counts, EQS score, remediation progress (open/fixed), validation results, and fix_level.
- **SKILL.md Execution Rules**: Added mandatory 8-point "Execution Rules (MANDATORY)" section to SKILL.md replacing the need for manual "CRITICAL CONSTRAINTS" prompts. Covers orchestrator-only state transitions, phase ordering, TeamCreate mandate, general-purpose agent type, artifact verification, decision logging, self-healing protocol, and fix_level respect.

### Modified Files
- `qralph-orchestrator.py` — `LEVEL_PRIORITIES` constant, `--fix-level` on init argparse, `fix_level` in state, `cmd_status` findings summary with `_status_summary`, `_cmd_remediate_locked` filters by fix_level (incl. `none` skip), `_cmd_remediate_verify_locked` blocks on active priorities, VERSION bump
- `qralph-state.py` — `fix_level: "p0_p1"` default in `repair_state()`
- `SKILL.md` — Execution Rules section, `--fix-level` in execution modes, version bumps (v4.1 -> v4.1.2, 420+ -> 440+ tests)
- `test_qralph_orchestrator.py` — 10 new tests: fix_level filtering, status findings summary, remediate-verify respecting level, fix_level=none skip, fix_level=all blocks on P2, invalid fix_level rejection

### Test Results
- 444 tests passing (434 existing + 10 new, 0 regressions)

## v4.1.1 (2026-02-18)

### Fixed — Deterministic Agent Output
- **Synthesis hard-gate**: `cmd_synthesize` now BLOCKS with error when any expected agent output file is missing or empty (<50 bytes). Previously, missing files were silently skipped, producing hollow reports that appeared successful.
- **`_error_result` includes status**: All error responses now include `"status": "error"` for consistent downstream handling.
- **Force `general-purpose` subagent_type**: Agent spawn instructions and team lead agent definition now mandate `subagent_type='general-purpose'` — specialized types (e.g., `usability-expert`, `pm`) lack the Write tool and cannot produce output files.
- **Prompt overhaul**: Agent prompts restructured — skills section moved AFTER workflow (labeled "Optional Skills"), explicit "Use the Write tool" instruction, verification step, output path repeated in CRITICAL REMINDER section at end of prompt.
- **QRALPH-RECEIPT**: Agent output template includes machine-verifiable `<!-- QRALPH-RECEIPT: {...} -->` HTML comment for automated completion detection.

### New Features
- **Evidence Quality Score (EQS)**: 0-100 metric computed at synthesis time: `(coverage*60) + (depth*30) + (findings*10)`. Thresholds: HIGH (80+), MEDIUM (50-79), LOW (20-49), HOLLOW RUN (0-19). Included in SYNTHESIS.md and SUMMARY.md.
- **Team lead verification protocol**: `qralph-team-lead.md` now includes mandatory Output Verification Protocol — Glob+Read each agent's output file before accepting task completion, check for QRALPH-RECEIPT, retry up to 2x.

### Modified Files
- `qralph-orchestrator.py` — `_error_result` adds status, `compute_evidence_quality_score()`, synthesis hard-gate, EQS in SYNTHESIS.md/SUMMARY.md, prompt overhaul with Write enforcement + QRALPH-RECEIPT + CRITICAL REMINDER, `general-purpose` subagent instruction
- `.claude/agents/qralph-team-lead.md` — Agent Spawning section (general-purpose mandate), Output Verification Protocol (MANDATORY)
- `test_qralph_orchestrator.py` — Updated tests for synthesis gate behavior, new tests for EQS, empty file gate, prompt content

### Test Results
- 434 tests passing (194 orchestrator + 240 others, 0 regressions)

## v4.1.0 (2026-02-18)

### New Features
- **Hierarchical Sub-Teams**: QRALPH now acts as "Sr. SDM" managing sub-team leads who each manage their own agent teams within a single context window. Sub-teams are ephemeral but their outputs survive on disk in `phase-outputs/`.
- **Quality Gate (95% Confidence)**: 5-point confidence check before proceeding past REVIEWING: critical agents complete, all domains covered, no contradictions, testable acceptance criteria, PE risk assessment present.
- **VALIDATING Phase**: Fresh-context validation by a sub-team that has NO knowledge of implementation decisions. Validates built artifacts against requirements with mini-UAT scenarios.
- **Execution Modes**: `--auto` (continue after quality gate passes) and `--human` (pause for approval, default) flags on init.
- **Sub-Team Lifecycle**: Full lifecycle management via `qralph-subteam.py`: create, check, collect, resume, teardown, quality-gate.
- **Version Detection**: `.qralph/VERSION` file with automatic update announcement on init/resume when version changes.
- **Sub-Team Recovery**: Automatic detection of interrupted sub-teams on session resume. `resume-subteam` identifies missing vs completed agents and outputs re-run instructions.

### New Files
- `.qralph/tools/qralph-subteam.py` — Sub-team lifecycle manager (6 commands)
- `.qralph/tools/test_qralph_subteam.py` — 45 tests for v4.1 features
- `.claude/agents/qralph-team-lead.md` — Sub-team lead agent definition
- `.claude/agents/qralph-validator.md` — Fresh-context validation agent
- `.qralph/VERSION` — Version file (4.1.0)

### Modified Files
- `qralph-orchestrator.py` — VERSION constant, `--auto`/`--human` flags, `--subteam` on select-agents, `subteam-status` and `quality-gate` commands, VALIDATING phase transitions, version check on init/resume
- `qralph-state.py` — `sub_teams` and `last_seen_version` in state schema, `VALIDATING` phase, `VALID_SUBTEAM_STATUSES`, sub_teams validation
- `session-state.py` — Sub-team recovery notice in session-start, recover sub-team state from phase-outputs
- `qralph-watchdog.py` — `check_subteam_health()`, updated `PHASE_PRECONDITIONS` for EXECUTING and VALIDATING, `VALIDATING` in valid phases
- `process-monitor.py` — `"team-agent": 1800` grace period
- `SKILL.md` — Hierarchical architecture diagram, sub-team commands, execution modes, quality gate docs

### Test Results
- 429 tests passing (384 existing + 45 new, 0 regressions)

## v4.0.5 (2026-02-15)

### Fixed
- **Log sanitization**: Upgraded from `\n\r` stripping to full control character removal via `re.sub(r'[\x00-\x1f\x7f]', ' ', msg)` in orchestrator `log_decision()`, healer `_safe_log_append()`, and process-monitor `_log_action()`. Prevents log injection via escape sequences, backspace, bell, etc.
- **Error response consistency**: Replaced final 8 `print(json.dumps(error))` calls with `_error_result()` in orchestrator commands: `cmd_init` validation, `cmd_synthesize` phase transition, `cmd_checkpoint` phase validation, `cmd_generate_uat` phase transition, `cmd_finalize` phase transition, `cmd_work_plan` phase transition, `cmd_remediate` phase check, `cmd_remediate_verify` phase transition.
- **Healer docstring**: Added missing `record-outcome` command to module docstring commands list.

### Test Results
- 384 tests passing (0 regressions)

### Publishing Status
- **PUBLISH-READY**: All P0 and P1 findings resolved across Runs 2-4 (35 total findings, 32 fixed, 3 P2 deferred as accepted risks)

## v4.0.4 (2026-02-15)

### Fixed
- **CONTROL.md false-positive parsing (P0)**: `check_control_commands()` used naive `if cmd in content` on entire file, causing template text like `- PAUSE - stop after current step` to trigger false PAUSE. Changed to line-exact matching — only a standalone line with just the command triggers it.
- **CONTROL.md template updated**: Help text now uses backtick-wrapped command names to prevent any future false matches.
- **Unused `subprocess` import**: Removed from `qralph-status.py` (leftover from clear_screen refactor).
- **Hardcoded phase list in status monitor**: `get_phase_progress()` now imports `QRALPH_PHASES` from session-state.py instead of maintaining a separate list.
- **Broad exception in healer rollback**: `except (JSONDecodeError, Exception)` narrowed to `(JSONDecodeError, ValueError, KeyError, OSError)`.
- **Broad exception in memory-store query/check**: `except Exception` narrowed to `(sqlite3.Error, ValueError, TypeError)` in `cmd_query` and `cmd_check`.
- **README path inconsistency**: Quickstart examples now consistently use `.qralph/tools/` prefix.

### Added
- 3 new tests for CONTROL.md parsing: template no-false-positive, old-template no-false-positive, whitespace-padded command detection.

### Test Results
- 384 tests passing (was 381 at v4.0.3 — 3 new CONTROL.md tests)

## v4.0.3 (2026-02-15)

### Fixed
- **Memory store `get_db_path()` ignores runtime env var**: `DB_PATH` was computed once at module import time, so `QRALPH_MEMORY_DB` set after import had no effect. All `cmd_*` functions connected to the default DB instead of the configured one. Fixed to read env var at call time.
- **Path validation rejected explicit `QRALPH_MEMORY_DB` paths**: The home-directory security check rejected all paths outside `~/` including legitimate temp/CI paths. Now trusts explicitly-set env var while still validating the default path.

### Test Results
- 381 tests passing (was 346 at v4.0.2 — 23 memory store tests were silently failing due to DB path bug, now fixed + 12 new tests from v4.0.2)

## v4.0.2 (2026-02-15)

### Fixed
- **F-008 (remaining)**: Log injection in `process-monitor.py:_log_action` - newline/CR sanitization added
- **F-011**: Circuit breaker `check_circuit_breakers()` now warns at runtime if called without `exclusive_state_lock()`
- **F-018**: Standardized error output - 25+ raw `json.dumps({"error":...})` calls replaced with `_error_result()` helper

### Added
- `is_exclusive_lock_held()` in qralph-state.py for runtime lock enforcement
- Thread-local `_lock_state` tracking in `exclusive_state_lock()` context manager
- Test: corrupt checkpoint recovery with fallback (`test_recover_from_corrupt_checkpoint_with_fallback`)
- Test: double-sweep kill prevention (`test_sweep_double_kill_prevention`)

### Test Results
- 346 tests passing (was 132 at v4.0.0, 300+ at v4.0.1)

## v4.0.1 (2026-02-15)

### Fixed
- **Orchestrator Loop Bug**: EXECUTING -> COMPLETE transition now valid in coding mode (Bug 1A)
- **Remediate Idempotency**: Second `remediate` call returns existing tasks instead of re-creating (Bug 1B)
- **Resume COMPLETE Guard**: `cmd_resume` returns `already_complete` for finished projects (Bug 1C)
- **Resume Locking**: `cmd_resume` wrapped in `exclusive_state_lock()` with checksum validation (Bug 1D)
- **Checkpoint Sync**: `save_state_and_checkpoint()` prevents state/checkpoint divergence (Bug 1E)
- **Recovery Phase Override**: `cmd_recover` preserves terminal phases; SUMMARY.md = COMPLETE (Bug 1F)
- **Work-Mode Steps**: `get_next_step()` covers PLANNING, USER_REVIEW, ESCALATE phases (Bug 1G)
- **Init Locking**: `cmd_init` wrapped in `exclusive_state_lock()` (F-001)
- **FTS5 Sanitization**: Full special character coverage in memory-store queries (F-004)
- **Exception Handling**: Narrowed broad `except Exception` in status monitor (F-005)
- **Log Injection**: Newline sanitization in `log_decision` and healer log (F-008)
- **PID Reuse Safety**: Process sweep re-verifies identity before kill (F-009)
- **State Loading**: session-state.py uses `load_state()` with checksum validation (F-010)
- **Clear Screen**: ANSI escape codes instead of subprocess (F-013)
- **DB Path**: `get_db_path()` uses validated module-level constant (F-015)
- **Phase Progress**: Status monitor uses correct phase names (F-019)
- **Watchdog Timeouts**: Configurable via environment variables (F-021)
- **Watch Interval**: Configurable via `--interval` / `QRALPH_STATUS_INTERVAL` (F-031)
- **Memory Rate Limiting**: Simple throttle on query frequency (F-022)
- **Database Permissions**: Restrictive umask on DB creation (F-023)

### Added
- `save_state_and_checkpoint()` helper for atomic phase advancement
- `_error_result()` helper for consistent error formatting
- `pyproject.toml` with pytest configuration (F-006)
- `README.md` with quickstart, architecture, configuration (F-007)
- `requirements.txt` (F-016)
- CHANGELOG v4.0.1 entry (F-020)
- TOCTOU warning in `load_state()` docstring (F-003)
- Windows process identity documentation (F-014)
- Loop bug tests and recovery tests (Phase 1H)

## v4.0.0 (2026-02-14)

### Migration
- **Migrated all orchestrator tools** from deeply nested project output to `.qralph/tools/`
- Updated SKILL.md with canonical tool paths and v4.0 features
- Added QWORK and QREMEMBER to QSHORTCUTS-REFERENCE.md

### New Features
- **Session State Persistence**: STATE.md lifecycle tracks phase progress, uncommitted work, and session history across Claude Code sessions. Commands: `create-state`, `session-start`, `session-end`, `recover`, `inject-claude-md`
- **Process Monitor**: PID registry with guaranteed launch at every entry/exit point. Orphan detection with grace periods, safe kill (registered only), and circuit breaker integration
- **Long-term Memory**: SQLite + FTS5 full-text search with porter stemming, recency-weighted scoring (30-day half-life), domain boost, and category weights. Auto-capture from healing success/failure, circuit breaker trips, and P0 findings
- **Work Mode**: Lightweight 1-3 agent mode for business tasks, writing, and research. Plan-first workflow with user review loop. Escalation to full coding mode when complexity grows
- **Watchdog**: Agent health checks with configurable timeouts per model tier. Phase precondition validation. Agent criticality levels (critical agents never auto-skipped)
- **QWORK shortcut**: Maps to `QRALPH --mode work` for quick access
- **QREMEMBER shortcut**: Manual memory capture via `memory-store.py`

### Improvements
- **Shared state module** (`qralph-state.py`): Atomic writes (write-to-temp + rename), SHA-256 checksums, fcntl locking (conditional for Windows), corruption recovery
- **Enhanced self-healing**: Pattern matching DB avoids retrying failed fixes, catastrophic rollback after 3+ consecutive failures, memory integration queries known resolutions before escalating
- **Error handling**: All bare `write_text()` and `json.loads(read_text())` calls wrapped with try/except using safe I/O utilities
- **Input sanitization**: Request field stripped of null bytes and path traversal sequences
- **Security**: Replaced unsafe shell invocations with `subprocess.run()` arrays
- **Cross-platform**: `fcntl` conditionally imported (Windows compatible)
- **Docstrings**: All ~50 public functions across all tool files documented

### Testing
- **300 tests** across 8 test files (was ~30 broken tests)
- Fixed 3 stale imports that crashed the entire test suite at import time
- Deleted 12 stale tests referencing removed v2.0 functions
- Added property-based tests for bounded outputs
- Full coverage of all new features: session state (29), process monitor (16), watchdog (21), work mode (23), healer (18), memory store (24)

### Files Added
- `.qralph/tools/qralph-state.py` - Shared state module
- `.qralph/tools/session-state.py` - Session persistence
- `.qralph/tools/process-monitor.py` - PID registry and orphan cleanup
- `.qralph/tools/qralph-watchdog.py` - Health checks and preconditions
- `.qralph/tools/test_session_state.py` - Session state tests
- `.qralph/tools/test_process_monitor.py` - Process monitor tests
- `.qralph/tools/test_qralph_healer.py` - Healer tests
- `.qralph/tools/test_qralph_watchdog.py` - Watchdog tests
- `.qralph/tools/test_work_mode.py` - Work mode tests
- `.claude/skills/learning/memory-store/scripts/memory-store.py` - SQLite + FTS5 store
- `.claude/skills/learning/memory-store/scripts/test_memory_store.py` - Memory store tests
- `.claude/skills/learning/memory-store/SKILL.md` - QREMEMBER skill definition

## v3.0.0 (2025-01-28)

### Features
- Native Claude Code teams (TeamCreate, TaskCreate, SendMessage)
- Dynamic plugin discovery and agent selection (3-7 agents)
- Domain classification across 12 domains
- Complexity scoring with model escalation (haiku -> sonnet -> opus)
- Circuit breakers: token limit, cost limit, error repetition, heal attempts
- CONTROL.md intervention commands (PAUSE, SKIP, ABORT, STATUS)
