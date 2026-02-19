# QRALPH Changelog

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
