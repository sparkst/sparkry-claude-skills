export const meta = {
  name: 'pipeline-auto',
  description: 'Autonomous end-to-end SDLC: requirements → design → separate-context TDD (per-slice worktrees) → unit-verify → integration, every artifact gated by the shared convergence engine and every human-moment routed through qdecide first. Stops at a staged/verified point (the prod tail is opt-in).',
  phases: [
    { title: 'Resolve', detail: 'resolve the reviewer team for the goal' },
    { title: 'Requirements', detail: 'author + converge REQUIREMENTS' },
    { title: 'Design', detail: 'author + converge DESIGN (contracts + slice decomposition)' },
    { title: 'TDD', detail: 'per-slice: test-writer (red) → implementer (green), one worktree each, waves' },
    { title: 'Integrate', detail: 'serialized merge of green worktrees → full suite → conflict-resolver → seam tests' },
    { title: 'Verify', detail: 'unit + integration hard gates; scorecard' },
  ],
}

// @@INLINE@@ build-workflow.mjs replaces this whole line with the inlined libraries

// `args` may arrive parsed or as a JSON string, depending on how the Workflow was
// invoked; tolerate both.
const A = typeof args === "string" ? JSON.parse(args) : (args || {})

const goal = A.goal
if (!goal) throw new Error('pipeline-auto requires a `goal`')

const requirementsPath = A.requirements || 'requirements/current.md'
const designPath = A.design || 'DESIGN.md'
const slicesPath = A.slices || 'slices.json'
const integrationPlanPath = A.integrationPlan || 'INTEGRATION-PLAN.md'
// Fork-synced runtime tools (team-selector.py, tdd-harness.py, integrator.py, scorecard.py).
// Default targets the FLAT live fork (py at the root, no /tools subdir); plugin callers
// pass their own `<plugin>/tools`. (OPT-008: a /tools default silently misses on the fork.)
const toolsDir = A.toolsDir || '/Users/travis/.claude/ai-review-tools'
const QDECIDE_VALIDATOR = '/Users/travis/.claude/skills/qdecide/tools/validate-proposal.py'

const threshold = A.threshold ?? 0
const maxRounds = A.maxRounds ?? 4
const maxParallel = A.maxParallel ?? 5
// deployTarget is DECLARED, never inferred: {kind, stagingCmd, prodCmd, stagingUrl,
// prodUrl, rollbackCmd, stateful}. null → stop at the verified point (plain `auto`
// with no deploy). Present → run the staging tail; prodAutonomous adds the prod tail.
const deployTarget = A.deployTarget ?? null
const prodAutonomous = A.prodAutonomous === true
const deployPlanPath = A.deployPlan || 'DEPLOY-PLAN.md'
// The ONE curated, cumulative smoke suite every feature appends its checks to.
const smokeSuitePath = A.smokeContract || 'smoke/prod.suite.json'
const smokeBatchSize = A.smokeBatchSize ?? 25
const humanConfirmed = A.humanConfirmed === true
// OPT-002: optional CLI-time complexity signal {files, toolTypes, contextFraction}.
// Threaded into runLoop config (loop-engine tiers reviewers off it) and into the
// team-resolve flags (OPT-020) so model escalation is deterministic, not defaulted.
const complexity = A.complexity ?? null
// A full-SDLC build is definitionally multi-file / multi-tool → floor the complexity
// (OPT-020) so escalation engages. `resolvedComplexity` is what actually reaches
// in-engine tiering (OPT-002): the args-provided signal, else the floor — never null.
const cxFiles = Math.max(2, (complexity && Number(complexity.files)) || 5)
const cxToolTypes = Math.max(2, (complexity && Number(complexity.toolTypes)) || 3)
const resolvedComplexity = complexity || { files: cxFiles, toolTypes: cxToolTypes }
// OPT-012 / design decision #6: a graceful per-run spend stop. The Workflow runtime
// injects a shared `budget` global (budget.total, budget.spent(), budget.remaining())
// pooled across the main loop and every agent. `budgetReserve` is the fraction of the
// run's total to keep in reserve so the graceful stop fires BEFORE the runtime's hard
// throw, leaving room for the tail (integration cleanup + scorecard).
const budgetReserve = A.budgetReserve ?? 0.05
const planOnly = A.planOnly === true
// Optional bound: halt after a named phase ('requirements'|'design'|'tdd'|'integration').
// Used for staged runs and for a cost-capped behavioral smoke that stops before the
// TDD worktrees build inside a repo. null = run the whole SDLC to the verified stop.
const stopAfter = A.stopAfter || null

let team = Array.isArray(A.team) ? A.team : []

// ── Structured-output schemas for the orchestration agents ────────────────
const EXITCODE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['exitCode'],
  properties: { exitCode: { type: 'integer', description: 'validate-proposal.py process exit (0=act,1=draft,2=decline; -1=error)' } },
}
const TEAM_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['team'],
  properties: {
    team: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['name', 'review_lens'],
        properties: { name: { type: 'string' }, review_lens: { type: 'string' }, model: { type: 'string' } },
      },
    },
  },
}
const SLICES_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['slices', 'waves', 'valid'],
  properties: {
    valid: { type: 'boolean' },
    errors: { type: 'array', items: { type: 'string' } },
    waves: { type: 'array', items: { type: 'array', items: { type: 'string' } } },
    slices: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: true, required: ['id', 'files', 'test_files', 'req_ids', 'depends_on'],
        properties: {
          id: { type: 'string' }, summary: { type: 'string' }, public_contract: { type: 'string' },
          files: { type: 'array', items: { type: 'string' } },
          test_files: { type: 'array', items: { type: 'string' } },
          req_ids: { type: 'array', items: { type: 'string' } },
          depends_on: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}
const GATE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['ok', 'reason'],
  properties: { ok: { type: 'boolean' }, reason: { type: 'string' }, tests_collected: { type: 'integer' }, exit_code: { type: 'integer' } },
}
// The test-writer creates the slice's dedicated worktree and reports its ABSOLUTE
// path, which the workflow threads into the red-gate / implementer / green-gate.
const WORKTREE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['worktree', 'branch'],
  properties: { worktree: { type: 'string' }, branch: { type: 'string' }, tests_committed: { type: 'boolean' } },
}
// ── Prod-tail schemas (Phase F2) ──────────────────────────────────────────
const SUITE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['valid', 'checks', 'newChecksAdded'],
  properties: {
    valid: { type: 'boolean' },
    newChecksAdded: { type: 'boolean' },
    errors: { type: 'array', items: { type: 'string' } },
    checks: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: true, required: ['id'],
        properties: { id: { type: 'string' }, description: { type: 'string' }, feature: { type: 'string' }, assert: { type: 'string' } },
      },
    },
  },
}
const DEPLOY_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['ok', 'reason'],
  properties: { ok: { type: 'boolean' }, reason: { type: 'string' }, url: { type: 'string' } },
}
const SMOKE_BATCH_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['results'],
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['id', 'passed'],
        properties: { id: { type: 'string' }, passed: { type: 'boolean' }, evidence: { type: 'string' } },
      },
    },
  },
}
const DEPLOY_GATE_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['allowed', 'blockers'],
  properties: { allowed: { type: 'boolean' }, blockers: { type: 'array', items: { type: 'string' } } },
}
const ROLLBACK_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['action', 'reason'],
  properties: { action: { type: 'string' }, reason: { type: 'string' } },
}

// ── qdecide adapter: a thin Haiku agent shells validate-proposal.py; the exit
// code drives the drift-locked escalation broker (buildProposal/resolveEscalation
// are inlined from escalation-broker.mjs). Never authorizes irreversible work.
async function qdecide(event) {
  const proposal = buildProposal(event)
  const res = await agent(
    [
      "Run Travis's decision validator on the proposal below and report ONLY its process exit code.",
      'Steps: write the JSON proposal to a temp file, then run exactly:',
      `  python3 ${QDECIDE_VALIDATOR} --input <tempfile> ; echo "EXIT:$?"`,
      'Read the EXIT: line. Return {"exitCode": <that integer>} (0=act, 1=draft, 2=decline).',
      'If the validator is missing, times out, or errors, return {"exitCode": -1}. Do NOT guess a code.',
      '',
      'PROPOSAL:',
      JSON.stringify(proposal),
    ].join('\n'),
    { label: `qdecide:${event.type}`, model: 'haiku', schema: EXITCODE_SCHEMA },
  )
  const code = res && typeof res.exitCode === 'number' ? res.exitCode : undefined
  return resolveEscalation(event, code)
}

// ── CONVERGE wrapper: run the shared loop engine IN-PROCESS per artifact (no
// nested workflow()). On a convergence escalation, route through qdecide before
// deciding whether the pipeline may proceed.
async function converge(artifact, opts = {}) {
  const res = await runLoop(
    {
      artifact,
      requirements: requirementsPath,
      team,
      threshold: opts.threshold ?? threshold,
      rounds: opts.rounds,
      maxRounds: opts.maxRounds ?? maxRounds,
      // OPT-002: forward the resolved complexity so runLoop tiers reviewer models via
      // resolveReviewerModel instead of trusting the team's declared model.
      complexity: resolvedComplexity,
      // OPT-007: every converge() in pipeline-auto gates a DOCUMENT (requirements,
      // design, integration-plan, deploy-plan) with no test surface — the code
      // artifacts go through the TDD red/green gates, not converge — so skip the
      // per-round test gate by default. Overridable via opts.skipTests.
      skipTests: opts.skipTests ?? true,
    },
    { agent, parallel, phase, log },
  )
  if (res.outcome && res.outcome.status === 'escalated') {
    res.decision = await qdecide({ type: 'converge', artifact, reason: res.outcome.reason, unresolved: res.outcome.unresolved })
    log(`CONVERGE(${artifact}) escalated → ${res.decision.action}: ${res.outcome.reason}`)
  }
  return res
}

// A hard-stop / human-gate decision from qdecide halts the pipeline; a fresh error
// is surfaced to the caller. `proceed-and-stage` and `proceed` both continue.
function halts(decision) {
  return decision && (decision.action === 'hard-stop' || decision.action === 'human-gate')
}

// ── Budget ceiling (OPT-012 / design decision #6) ─────────────────────────
// The Workflow runtime injects a shared `budget` global — `budget.total` (null when no
// target is set), `budget.spent()`, `budget.remaining()` — pooled across the main loop
// and every agent, and agent() itself throws once `total` is reached. checkBudget stops
// GRACEFULLY before that hard throw (leaving a `budgetReserve` fraction of total so the
// tail still runs). `budget.remaining()` is authoritative; typeof-guarded so an absent
// global never throws. Units are the runtime's own (total/remaining share them), so the
// reserve is a fraction, not a hardcoded dollar figure.
const report = { goal, artifacts: {}, slices: null, integration: null, warnings: [] }
let budgetAdvisoryLogged = false
// Call before each converge() and each TDD wave. On breach, returns a broker-classified
// spend hard-stop (budget-exceeded ∈ mustHardStop); the caller returns {status:'halted'}.
function checkBudget(where) {
  const hasTarget = typeof budget !== 'undefined' && budget && typeof budget.total === 'number' && budget.total > 0
  if (!hasTarget) {
    // No target set → remaining() is unbounded; nothing to gracefully stop before.
    if (!budgetAdvisoryLogged) {
      budgetAdvisoryLogged = true
      const warn = 'BUDGET CEILING ADVISORY — no budget target set for this run; the graceful pre-throw stop is inactive.'
      report.warnings.push(warn)
      log(warn)
    }
    return null
  }
  const remaining = typeof budget.remaining === 'function' ? budget.remaining() : null
  if (typeof remaining === 'number' && remaining <= budget.total * budgetReserve && mustHardStop({ type: 'budget-exceeded' })) {
    const spent = typeof budget.spent === 'function' ? budget.spent() : (budget.total - remaining)
    log(`BUDGET CEILING REACHED at ${where}: remaining ${remaining} of ${budget.total} (spent ${spent}) ≤ ${budgetReserve} reserve — graceful hard stop.`)
    return { action: 'hard-stop', recommendation: 'decline', category: 'spend', reason: `budget reserve reached at ${where}: remaining ${remaining} of ${budget.total}` }
  }
  return null
}

// Extra orchestration schemas (OPT-011 per-merge sequencer, OPT-013 seam gate).
const MERGE_ORDER_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['order', 'blocked'],
  properties: {
    order: { type: 'array', items: { type: 'string' }, description: 'slice ids only, e.g. "S-001" — the tool JSON\'s order field verbatim' },
    blocked: { type: 'array', items: { type: 'string' }, description: 'the tool JSON\'s blocked field verbatim' },
    skipped: { type: 'array', items: { type: 'string' } },
  },
}
const SEAM_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['test_files'],
  properties: { test_files: { type: 'array', items: { type: 'string' } }, summary: { type: 'string' } },
}

// Authoring agents each produce exactly ONE document; the product itself is built
// later under the separate-context TDD gate. Without this guard an eager author
// scaffolds the whole project (impl + tests + npm install), which pre-satisfies the
// tests and makes the red gate spuriously fail — the two-context TDD is corrupted.
const DOC_ONLY =
  'Write ONLY the single document named above. Do NOT create, edit, or scaffold ANY other file — no ' +
  'source code, no test files, no package.json/tsconfig/lockfiles, no directories — and do NOT run ' +
  'installers, generators, or build tools. The implementation is authored later under a separate TDD ' +
  'gate that requires the tests to fail before any code exists; producing code now breaks that gate.'

// planOnly: prove the whole inlined bundle links in the sandbox and echo the
// resolved plan — the cheap early parser/link smoke (no agent spend).
if (planOnly) {
  return {
    status: 'plan',
    goal,
    deployTarget: deployTarget ? (deployTarget.kind || 'declared') : null,
    prodAutonomous,
    config: { threshold, maxRounds, maxParallel, budgetReserve, complexity: complexity || null },
    engines: {
      runLoop: typeof runLoop,
      buildProposal: typeof buildProposal,
      resolveEscalation: typeof resolveEscalation,
      collectBlockers: typeof collectBlockers,
      buildTestWriterPrompt: typeof buildTestWriterPrompt,
      buildImplementerPrompt: typeof buildImplementerPrompt,
      worktreeSetup: typeof worktreeSetup,
      worktreeCleanup: typeof worktreeCleanup,
      buildConflictResolverPrompt: typeof buildConflictResolverPrompt,
      buildIntegrationTestWriterPrompt: typeof buildIntegrationTestWriterPrompt,
      buildDeployPlanPrompt: typeof buildDeployPlanPrompt,
      buildStagingDeployPrompt: typeof buildStagingDeployPrompt,
      buildProdPublishPrompt: typeof buildProdPublishPrompt,
      buildSmokeBatchPrompt: typeof buildSmokeBatchPrompt,
      buildRollbackPrompt: typeof buildRollbackPrompt,
      planSmokeBatches: typeof planSmokeBatches,
      aggregateSmoke: typeof aggregateSmoke,
      buildGateState: typeof buildGateState,
    },
  }
}

// ── Phase 0: resolve the reviewer team ───────────────────────────────────
// OPT-020: a full-SDLC build is definitionally multi-file / multi-tool, so the
// complexity posture is EXPLICIT — the CLI gets real --files/--tool-types (cxFiles /
// cxToolTypes, resolved up top) so model escalation engages deterministically rather
// than defaulting to files=1 at a haiku agent's discretion.
if (team.length < 2) {
  phase('Resolve')
  const t = await agent(
    [
      'Resolve the reviewer team best suited to this goal.',
      `Run: python3 ${toolsDir}/team-selector.py --json --files ${cxFiles} --tool-types ${cxToolTypes} (pass the goal per --help).`,
      'The --files/--tool-types flags are REQUIRED (do not omit them) — they drive model tiering for this multi-file build.',
      `Goal: ${JSON.stringify(goal)}`,
      'Return {team:[{name, review_lens, model}, ...]} with at least 2 reviewers.',
    ].join('\n'),
    { label: 'team-resolve', model: 'haiku', schema: TEAM_SCHEMA },
  )
  team = (t && Array.isArray(t.team) ? t.team : []).filter(Boolean)
}
if (team.length < 2) {
  // OPT-016: team-selector unavailable → do NOT silently proceed with two generic
  // sonnet lenses. Mirror the catalog floor (add a security lens at the HIGH_STAKES
  // tier) and log the degradation loudly into the workflow log + final report.
  const warn = 'TEAM RESOLUTION DEGRADED — team-selector unavailable; using the hardcoded catalog-floor fallback (incl. a security lens at opus). Check toolsDir + model tiering.'
  report.warnings.push(warn)
  log(warn)
  team = [
    { name: 'correctness-reviewer', review_lens: 'correctness, requirements coverage, contracts', model: 'sonnet' },
    { name: 'robustness-reviewer', review_lens: 'edge cases, failure modes, tests', model: 'sonnet' },
    { name: 'security-reviewer', review_lens: 'authz, secrets, injection, SSRF, path traversal, unsafe deserialization', model: 'opus' },
  ]
}
log(`Team resolved: ${team.map((m) => m.name).join(', ')}`)

// ── Phase 1: REQUIREMENTS → converge ─────────────────────────────────────
{ const b = checkBudget('requirements'); if (b) return { status: 'halted', at: 'budget', decision: b, report } }
phase('Requirements')
await agent(
  [
    `Author the requirements for this goal at ${requirementsPath} in the project's REQ-ID format`,
    '(each `## REQ-NNN` with an Acceptance line). Be complete and testable; no implementation.',
    `Goal: ${JSON.stringify(goal)}`,
    '',
    DOC_ONLY,
  ].join('\n'),
  { label: 'requirements-author', model: 'sonnet' },
)
const reqRun = await converge(requirementsPath, { rounds: undefined, maxRounds: 4 })
report.artifacts.requirements = reqRun.outcome
if (halts(reqRun.decision)) return { status: 'halted', at: 'requirements', decision: reqRun.decision, report }
await commitConverged(requirementsPath, reqRun, `docs(pipeline): requirements converged r${(reqRun.outcome && reqRun.outcome.round) || ''}`)
if (stopAfter === 'requirements') return { status: 'stopped', at: 'requirements', report }

// ── Phase 2: DESIGN (contracts + slice decomposition) → converge ─────────
{ const b = checkBudget('design'); if (b) return { status: 'halted', at: 'budget', decision: b, report } }
phase('Design')
await agent(
  [
    `Author the design at ${designPath}: public contracts, and a VERTICAL-SLICE decomposition where each`,
    'slice is {id, summary, public_contract, files[], test_files[], req_ids[], depends_on[]}. File ownership',
    'MUST be a partition (no two slices share a file); shared code goes in an explicit S-000 kernel with no',
    `deps. Cover every REQ-ID in ${requirementsPath}. Read the requirements first.`,
    '',
    DOC_ONLY,
  ].join('\n'),
  { label: 'design-author', model: 'sonnet' },
)
const designRun = await converge(designPath, { rounds: undefined, maxRounds: 4 })
report.artifacts.design = designRun.outcome
if (halts(designRun.decision)) return { status: 'halted', at: 'design', decision: designRun.decision, report }
await commitConverged(designPath, designRun, `docs(pipeline): design converged r${(designRun.outcome && designRun.outcome.round) || ''}`)

// Extract + validate the slice decomposition (partition/coverage/waves via tdd-harness.py).
const sliceRun = await agent(
  [
    `Read ${designPath}. Extract its vertical slices to ${slicesPath} as a JSON array of`,
    '{id, summary, public_contract, files, test_files, req_ids, depends_on}.',
    `Then validate + wave them:`,
    `  python3 ${toolsDir}/tdd-harness.py validate-slices --slices ${slicesPath} --req-ids <comma-separated REQ-IDs>`,
    `  python3 ${toolsDir}/tdd-harness.py waves --slices ${slicesPath}`,
    'Return {valid, errors, slices, waves} (waves = array of arrays of slice ids).',
    '',
    `${DOC_ONLY} (Here the single document is ${slicesPath}; you may also read ${designPath}.)`,
  ].join('\n'),
  { label: 'slice-plan', model: 'sonnet', schema: SLICES_SCHEMA },
)
const slices = (sliceRun && Array.isArray(sliceRun.slices)) ? sliceRun.slices : []
const waves = (sliceRun && Array.isArray(sliceRun.waves)) ? sliceRun.waves : []
report.slices = { count: slices.length, waves, valid: !!(sliceRun && sliceRun.valid) }
if (!sliceRun || !sliceRun.valid || !slices.length) {
  const decision = await qdecide({ type: 'ambiguous-requirements', reason: `Slice decomposition invalid: ${(sliceRun && sliceRun.errors || []).join('; ') || 'no slices'}` })
  return { status: 'halted', at: 'slice-plan', decision, report }
}
// Shell-safety: slice ids flow verbatim into worktree dirs + branch + tag names.
// Reject anything outside [A-Za-z0-9._-] loudly rather than interpolate it into bash.
const unsafeIds = slices.map((s) => s.id).filter((id) => !isSafeSliceId(id))
if (unsafeIds.length) {
  const msg = `Unsafe slice id(s) ${JSON.stringify(unsafeIds)} — ids feed shell worktree/branch/tag names and must match [A-Za-z0-9._-]+.`
  log(msg)
  const decision = await qdecide({ type: 'ambiguous-requirements', reason: msg })
  return { status: 'halted', at: 'slice-plan', decision, report }
}
const sliceById = {}
for (const s of slices) sliceById[s.id] = s
await commitArtifact(slicesPath, 'docs(pipeline): slice decomposition validated')
if (stopAfter === 'design') return { status: 'stopped', at: 'design', report }

// ── Phase 3+4: per-wave TDD then IMMEDIATE integration (SMOKE-004) ─────────
// The defining smoke defect: ALL slice worktrees branched from PRE-merge main and
// integration happened after every wave, so a wiring slice (depends_on earlier slices)
// could NEVER green in isolation — it was deleted and the pipeline shipped main without
// it while claiming "verified". Fix: integrate each wave's green slices IMMEDIATELY, so
// the next wave's worktrees branch from a main that already contains the prior merges.
// Waves are dependency-ordered by the slice planner; merge-order within a wave still
// comes from integrator.py. Seam tests + final verify stay after all waves.
phase('TDD')
const integration = { merged: [], resolved: [], failed: [] }
const droppedSlices = []
for (const wave of waves) {
  // OPT-012: a full-SDLC × CONVERGE × slices fan-out is where spend concentrates —
  // check the ceiling before each wave.
  { const b = checkBudget('tdd-wave'); if (b) return { status: 'halted', at: 'budget', decision: b, report } }
  // Slices in a wave are independent (disjoint files + disjoint worktree dirs +
  // branches) → build them in parallel, capped by maxParallel. Each worktree branches
  // from the CURRENT main (includes prior waves' merges), so wiring slices can green.
  const batch = wave.map((id) => sliceById[id]).filter(Boolean)
  const built = []
  const results = await parallel(
    batch.slice(0, maxParallel).map((slice) => () => buildSlice(slice)),
  )
  for (const r of results.filter(Boolean)) built.push(r)
  // Any overflow beyond maxParallel builds in a follow-on pass (rare; waves are usually small).
  for (const slice of batch.slice(maxParallel)) {
    const r = await buildSlice(slice)
    if (r) built.push(r)
  }
  const waveGreen = []
  for (const r of built) {
    if (r.green) waveGreen.push(r.id)
    else droppedSlices.push({ id: r.id, reason: r.reason || 'slice failed its gate' })
  }
  // Integrate THIS wave now so later waves see its merges on main.
  await integrateWave(waveGreen)
}
report.integration = integration
// SMOKE-007b: force-sweep every pipeline worktree/branch/tag, even ones never merged
// (the smoke left an orphaned pipeline/S-005 worktree that survived per-merge teardown).
await sweepPipelineArtifacts()
if (stopAfter === 'tdd') return { status: 'stopped', at: 'tdd', report }

// Tear down a slice's worktree + branch + tests tag (on failure, so orphans never
// accumulate; the integrator does the same after a successful merge).
async function cleanupSlice(slice) {
  await agent(
    ['Clean up the slice\'s dedicated worktree, branch, and frozen-tests tag — run exactly:', worktreeCleanup(slice)].join('\n'),
    { label: `cleanup:${slice.id}`, model: 'haiku', phase: `Slice ${slice.id}` },
  )
}

// One slice: TEST-WRITER (red-gated) then IMPLEMENTER (tests read-only, tamper-checked, green-gated).
// All four agents share ONE named worktree (the test-writer creates it and returns its ABSOLUTE
// path); parallel slices never clobber each other because their worktree dirs + branches are disjoint.
async function buildSlice(slice) {
  // Context A — create the shared worktree + author failing tests, committed + tagged.
  const setup = await agent(buildTestWriterPrompt(slice, { requirementsPath, designPath }), {
    label: `test-writer:${slice.id}`, model: 'sonnet', phase: `Slice ${slice.id}`, schema: WORKTREE_SCHEMA,
  })
  const worktreePath = setup && setup.worktree
  if (!worktreePath) {
    await cleanupSlice(slice)
    const reason = 'test-writer did not create/return the slice worktree'
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason })
    return { id: slice.id, green: false, reason, decision }
  }
  const red = await agent(
    [
      `Run the tests for slice ${slice.id} and report the RED gate. Work in the slice worktree:`,
      `  cd "${worktreePath}" && python3 ${toolsDir}/test-runner.py --json (or the project's test command) for: ${(slice.test_files || []).join(', ')}`,
      `Then interpret with: python3 ${toolsDir}/tdd-harness.py (red_gate semantics: must FAIL with ≥1 test collected).`,
      'Return {ok, reason, tests_collected, exit_code}. ok=true only if the tests fail pre-implementation.',
    ].join('\n'),
    { label: `red-gate:${slice.id}`, model: 'haiku', phase: `Slice ${slice.id}`, schema: GATE_SCHEMA },
  )
  if (!red || !red.ok) {
    await cleanupSlice(slice)
    const reason = `RED gate failed: ${(red && red.reason) || 'no result'}`
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason })
    return { id: slice.id, green: false, reason, decision }
  }
  // Context B — make them green in the SAME worktree; tests frozen + tamper-checked via commits.
  await agent(buildImplementerPrompt(slice, { designPath, redSummary: red.reason, worktreePath }), {
    label: `implementer:${slice.id}`, model: 'sonnet', phase: `Slice ${slice.id}`,
  })
  const green = await agent(
    [
      `Verify slice ${slice.id} in its worktree "${worktreePath}" (cd there first). Diff COMMITS, not dirty state:`,
      `  cd "${worktreePath}" && git diff --name-only pipeline-tests/${slice.id}..HEAD   # everything the implementer changed`,
      `(1) TAMPER-CHECK — every changed path must be one of ${(slice.files || []).join(', ') || '(none)'}, OR`,
      `incidental drift the test/build runner rewrites as a side effect (lockfiles, package/project`,
      `manifests, caches: package-lock.json, *.lock, pnpm-lock.yaml, .project/manifest.yaml, __pycache__/,`,
      `*.pyc, node_modules/) — such drift is NOT a violation, do NOT fail the slice for it. NO changed path`,
      `may be a test file (${(slice.test_files || []).join(', ') || '(none)'}), and \`git diff --name-only pipeline-tests/${slice.id}..HEAD -- ${(slice.test_files || []).join(' ')}\` MUST be empty`,
      `(these are tdd-harness.py::check_tamper's INCIDENTAL_DRIFT_GLOBS semantics; a test file is never excused).`,
      // SMOKE-007a: catch a slice that goes off-script by merging sibling branches or
      // resurrecting commits to manufacture a passing state.
      `(2) BRANCH-HISTORY SANITY — the slice branch may contain ONLY this slice's own commits since the`,
      `frozen-tests tag: \`cd "${worktreePath}" && git rev-list --merges pipeline-tests/${slice.id}..HEAD\` MUST be EMPTY`,
      `(no merge commits — the slice must NOT merge other branches), and \`git merge-base --is-ancestor pipeline-tests/${slice.id} HEAD\``,
      'MUST succeed (linear history). If either fails, the slice went off-script → return ok:false.',
      '(3) GREEN gate — the suite now PASSES with tests still collected. Return {ok, reason, tests_collected, exit_code}.',
    ].join('\n'),
    { label: `green-gate:${slice.id}`, model: 'haiku', phase: `Slice ${slice.id}`, schema: GATE_SCHEMA },
  )
  if (!green || !green.ok) {
    await cleanupSlice(slice)
    const reason = `GREEN/tamper/history gate failed: ${(green && green.reason) || 'no result'}`
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason })
    return { id: slice.id, green: false, reason, decision }
  }
  return { id: slice.id, green: true }
}

// Serialized, per-merge integration of ONE wave's green slice branches (OPT-011):
// deterministic merge order, then per slice a haiku merge+suite gate, a sonnet
// conflict-resolver ONLY on failure, and an INDEPENDENT haiku tamper+green re-gate —
// the two-context/tamper separation is structural here too. Mutates `integration`.
async function integrateWave(waveGreen) {
  if (!waveGreen.length) return
  { const b = checkBudget('integrate'); if (b) { integration.failed.push({ id: '(wave)', reason: b.reason }); return } }
  const orderRun = await agent(
    [
      'Compute the deterministic merge order for these green slice branches.',
      `Run: python3 ${toolsDir}/integrator.py merge-order --slices ${slicesPath} --green ${waveGreen.join(',')} --merged ${integration.merged.join(',') || '""'}`,
      '(--merged = slices already integrated in earlier waves; their deps count as satisfied.)',
      'The tool prints a JSON object {"order": [...], "blocked": [...], "skipped": [...]}. Parse it and return',
      'those three fields VERBATIM — each entry is a bare slice id like "S-001", never a "key: value" string.',
    ].join('\n'),
    { label: 'merge-order', model: 'haiku', phase: 'Integrate', schema: MERGE_ORDER_SCHEMA },
  )
  // Trust-but-verify the haiku adapter: only known green slice ids may enter the merge
  // loop (re-smoke regression: the adapter once returned the tool's printed LINES as
  // order entries, and the unknown-id skip silently dropped a whole green wave).
  const knownGreen = new Set(waveGreen)
  const rawOrder = (orderRun && Array.isArray(orderRun.order)) ? orderRun.order : []
  const order = rawOrder.filter((id) => knownGreen.has(id))
  const blocked = ((orderRun && Array.isArray(orderRun.blocked)) ? orderRun.blocked : []).filter((id) => knownGreen.has(id))
  if (order.length !== rawOrder.length) log(`merge-order adapter returned ${rawOrder.length - order.length} malformed entrie(s) — filtered to known ids`)
  // A green slice the tool neither ordered nor blocked (or a fully malformed adapter
  // reply) must NOT vanish: everything unaccounted-for is treated as blocked.
  for (const id of waveGreen) if (!order.includes(id) && !blocked.includes(id)) blocked.push(id)
  for (const id of blocked) {
    integration.failed.push({ id, reason: 'blocked: dependency not merged (merge-order) — slice was green but never integrated' })
    await agent(['Tear down the blocked slice — run exactly:', worktreeCleanup(sliceById[id])].join('\n'),
      { label: `blocked-cleanup:${id}`, model: 'haiku', phase: 'Integrate' })
  }
  for (const id of order) {
    const slice = sliceById[id]
    if (!slice) continue
    // 1) haiku: merge this branch into main + run the FULL suite.
    const merge = await agent(
      [
        `Integrate slice ${id}. From the repo root (git rev-parse --show-toplevel; NOT a slice worktree):`,
        `  git merge --no-ff pipeline/${id}`,
        `Then run the FULL test suite (python3 ${toolsDir}/test-runner.py --json, or the project command) and`,
        `interpret with python3 ${toolsDir}/integrator.py merge_gate.`,
        'Return {ok, reason, tests_collected, exit_code}. ok=true iff the merge is clean AND the suite is green.',
      ].join('\n'),
      { label: `merge:${id}`, model: 'haiku', phase: 'Integrate', schema: GATE_SCHEMA },
    )
    let ok = !!(merge && merge.ok)
    // 2) on failure → sonnet conflict-resolver (impl-only) using the REAL slice fields.
    if (!ok) {
      await agent(
        buildConflictResolverPrompt(slice, { suiteFailure: (merge && merge.reason) || 'full suite failing after merge' }),
        { label: `conflict-resolver:${id}`, model: 'sonnet', phase: 'Integrate' },
      )
      // 3) INDEPENDENT haiku tamper + green re-gate — the resolver may not touch tests.
      const regate = await agent(
        [
          `Re-verify slice ${id} after the conflict-resolver, from the repo root. Diff the resolver's changes:`,
          `  git diff --name-only pipeline-tests/${id}..HEAD`,
          `(1) TAMPER-CHECK — NO test file (${(slice.test_files || []).join(', ') || '(none)'}) changed vs the frozen tag`,
          `(python3 ${toolsDir}/tdd-harness.py check_tamper); the resolver may edit ONLY ${(slice.files || []).join(', ') || '(none)'}.`,
          '(2) GREEN — the FULL suite now passes with tests still collected. Return {ok, reason, tests_collected, exit_code}.',
        ].join('\n'),
        { label: `merge-regate:${id}`, model: 'haiku', phase: 'Integrate', schema: GATE_SCHEMA },
      )
      ok = !!(regate && regate.ok)
      if (ok) integration.resolved.push(id)
    }
    if (ok) {
      integration.merged.push(id)
      await agent(['Tear down the merged slice — run exactly:', worktreeCleanup(slice)].join('\n'),
        { label: `merge-cleanup:${id}`, model: 'haiku', phase: 'Integrate' })
    } else {
      integration.failed.push({ id, reason: (merge && merge.reason) || 'merge/tamper/green gate failed' })
    }
  }
}

// SMOKE-007b end-of-run sweep: force-remove EVERY pipeline worktree/branch/tag, even
// ones the merge-order never touched (an off-script slice can leave an orphan that the
// per-merge teardown misses).
async function sweepPipelineArtifacts() {
  await agent(
    [
      'End-of-run sweep — force-remove ALL pipeline worktrees, branches, and tags regardless of merge',
      'status. From the repo root run exactly:',
      '```bash',
      'ROOT="$(git rev-parse --show-toplevel)"; cd "$ROOT"',
      'for wt in "${ROOT}".pipeline-wt/*; do [ -d "$wt" ] && git worktree remove --force "$wt" 2>/dev/null || true; done',
      'rm -rf "${ROOT}".pipeline-wt 2>/dev/null || true',
      'git worktree prune 2>/dev/null || true',
      'git branch --list "pipeline/*" | sed "s/^[* ]*//" | while read -r b; do [ -n "$b" ] && git branch -D "$b" 2>/dev/null || true; done',
      'git tag -l "pipeline-tests/*" | while read -r t; do [ -n "$t" ] && git tag -d "$t" 2>/dev/null || true; done',
      '```',
    ].join('\n'),
    { label: 'sweep-pipeline-artifacts', model: 'haiku', phase: 'Verify' },
  )
}

// SMOKE-006: commit each authored artifact on the current branch when it converges, so
// the working tree isn't left full of untracked docs/tests that final verify silently
// counts. Skips cleanly when nothing changed; pathspec-scoped so it commits only itself.
async function commitArtifact(paths, message) {
  await agent(
    [
      `Commit pipeline artifact(s) ${paths} on the current branch (from the repo root; no-op if unchanged):`,
      '```bash',
      'ROOT="$(git rev-parse --show-toplevel)"; cd "$ROOT"',
      `git add -- ${paths} 2>/dev/null || true`,
      `git commit -m ${JSON.stringify(message)} -- ${paths} 2>/dev/null || echo "nothing to commit: ${paths}"`,
      '```',
    ].join('\n'),
    { label: 'commit-artifact', model: 'haiku', phase: 'Commit' },
  )
}

// SMOKE-008: a converge's fixer may edit files BEYOND the artifact (e.g. a test file
// while fixing an integration-plan finding). Commit those alongside the artifact —
// through the SAME pathspec-scoped commit (never `git add -A`, which would sweep
// leftover .pipeline-wt/ worktree state) — so the committed tree matches what `verify`
// runs on. Without this, verify goes green on a working tree the committed branch lacks.
async function commitConverged(artifactPath, run, message) {
  const declared = run && Array.isArray(run.edited_files) ? run.edited_files : []
  // Only shell-safe repo-relative paths, so a malformed declaration can neither break
  // the commit command nor escape the pathspec.
  const safe = declared.filter((p) => typeof p === 'string' && /^[\w./-]+$/.test(p))
  await commitArtifact([...new Set([artifactPath, ...safe])].join(' '), message)
}

// Cross-slice seam tests from a fresh context, then GATE them (OPT-013): they must run
// (≥1 collected, pass) and must not have mutated any pre-existing test file before they
// silently ride into final verify.
const seam = await agent(buildIntegrationTestWriterPrompt(slices, { designPath, requirementsPath }), {
  label: 'integration-test-writer', model: 'sonnet', schema: SEAM_SCHEMA,
})
const seamFiles = (seam && Array.isArray(seam.test_files)) ? seam.test_files : []
if (seamFiles.length) {
  // SMOKE-006: commit the seam tests before the gate/verify so they aren't counted as
  // untracked working-tree files.
  await commitArtifact(seamFiles.join(' '), 'test(pipeline): cross-slice seam tests')
  const seamGate = await agent(
    [
      `Gate the NEW seam tests just written: ${seamFiles.join(', ')}. From the repo root:`,
      `run ONLY those files (python3 ${toolsDir}/test-runner.py --json, or the project command).`,
      '(1) they MUST pass with tests_collected ≥ 1 (no vacuous seam test);',
      '(2) DIFF-SCOPE — they must not have modified any pre-existing test file (git diff --name-only;',
      `interpret with python3 ${toolsDir}/tdd-harness.py check_tamper — only the new seam files may be added).`,
      'Return {ok, reason, tests_collected, exit_code}.',
    ].join('\n'),
    { label: 'seam-gate', model: 'haiku', phase: 'Integrate', schema: GATE_SCHEMA },
  )
  report.seam_gate = seamGate || { ok: false, reason: 'no result' }
  if (!seamGate || !seamGate.ok) {
    const decision = await qdecide({ type: 'integration-fail', reason: `Seam-test gate failed: ${(seamGate && seamGate.reason) || 'no result'}` })
    if (halts(decision)) return { status: 'halted', at: 'seam-gate', decision, report }
  }
}
await agent(
  [
    `Author ${integrationPlanPath}: how the slices compose, the seams under test, and the deploy/verify checklist. Read ${designPath}.`,
    '',
    DOC_ONLY,
  ].join('\n'),
  { label: 'integration-plan-author', model: 'sonnet' },
)
// OPT-018: INTEGRATION-PLAN.md is a compose/verify checklist — the lowest-stakes
// artifact in the run. A single-pass diagnose (rounds:1) replaces the full
// requirements/design-grade fan-out (min 2 rounds × maxRounds 3 ≈ 9-12 calls).
const intPlanRun = await converge(integrationPlanPath, { rounds: 1 })
report.artifacts.integration_plan = intPlanRun.outcome
if (halts(intPlanRun.decision)) return { status: 'halted', at: 'integration-plan', decision: intPlanRun.decision, report }
await commitConverged(integrationPlanPath, intPlanRun, `docs(pipeline): integration plan r${(intPlanRun.outcome && intPlanRun.outcome.round) || ''}`)
if (stopAfter === 'integration') return { status: 'stopped', at: 'integration', report }

// ── Phase 6: unit + integration verify (hard gate), scorecard ────────────
phase('Verify')
const verify = await agent(
  [
    'Run the FULL test suite (unit + integration) as a hard gate. Do NOT fix anything.',
    `  python3 ${toolsDir}/test-runner.py --json (or the project's test command).`,
    'Return {ok, reason, tests_collected, exit_code} — ok=true only if everything passes.',
  ].join('\n'),
  // OPT-010: mechanical suite-runner — shell the runner, interpret an exit code, fill a
  // schema — exactly what the red/green gates already do reliably on haiku.
  { label: 'verify', model: 'haiku', schema: GATE_SCHEMA },
)
report.verify = verify || { ok: false, reason: 'no result' }
if (!verify || !verify.ok) {
  const decision = await qdecide({ type: 'converge', artifact: 'full-suite', reason: `Final verify failed: ${(verify && verify.reason) || 'no result'}` })
  return { status: 'halted', at: 'verify', decision, report }
}

// SMOKE-005 status honesty: even with a green suite, "verified" is IMPOSSIBLE if any
// slice was dropped, any integration failed, or any artifact escalated unresolved (a
// draft-proceed is still unresolved). Surface every such blocker and halt instead — the
// smoke shipped a CLI-less main as "verified" precisely because this gate was missing.
const blockers = collectBlockers({ droppedSlices, integrationFailed: integration.failed, artifacts: report.artifacts })
if (blockers.length) {
  report.blockers = blockers
  log(`Pipeline INCOMPLETE — ${blockers.length} blocker(s): ${blockers.join(' | ')}`)
  return { status: 'halted', at: 'verify', blockers, report }
}

// deployTarget null → stop at the verified point (only reachable when the run is clean).
if (!deployTarget) {
  log('Pipeline complete to verified stop. deployTarget=null (stop-at-verify).')
  return { status: 'verified', report }
}

// ── Phase 7: the production tail (DEPLOY-PLAN → staging deploy → staging smoke) ──
// A deployTarget is DECLARED, so run the reversible staging tail. The prod tail
// (phase 8) only runs under prodAutonomous (`/qpipeline auto prod`).
{ const b = checkBudget('deploy'); if (b) return { status: 'halted', at: 'budget', decision: b, report } }
phase('Deploy')

// DEPLOY-PLAN: declared commands + smoke assertions + rollback criteria, reviewed up
// front (qloop'd), and the feature appends its checks to the cumulative suite.
await agent(
  buildDeployPlanPrompt(deployTarget, { requirementsPath, designPath, planPath: deployPlanPath, suitePath: smokeSuitePath }),
  { label: 'deploy-plan-author', model: 'sonnet' },
)
const deployPlanRun = await converge(deployPlanPath, { rounds: undefined, maxRounds: 3 })
report.artifacts.deploy_plan = deployPlanRun.outcome
if (halts(deployPlanRun.decision)) return { status: 'halted', at: 'deploy-plan', decision: deployPlanRun.decision, report }

// Read + validate the cumulative smoke suite; confirm THIS feature added its checks
// (the guardrail refuses a feature that ships no smoke check for its new behavior).
const suiteRun = await agent(
  [
    `Read the cumulative prod smoke suite ${smokeSuitePath} and validate it:`,
    `  python3 ${toolsDir}/prod-tail.py validate-suite --suite ${smokeSuitePath}`,
    `Then confirm this feature's NEW behavior added at least one NEW check (cross-check ${deployPlanPath}).`,
    'Return {valid, checks:[{id,description,feature,assert?}], newChecksAdded, errors}.',
  ].join('\n'),
  { label: 'smoke-suite', model: 'haiku', schema: SUITE_SCHEMA },
)
const suiteChecks = (suiteRun && Array.isArray(suiteRun.checks)) ? suiteRun.checks : []
if (!suiteRun || !suiteRun.valid || !suiteChecks.length) {
  const decision = await qdecide({ type: 'converge', artifact: smokeSuitePath, reason: `Invalid/empty smoke suite: ${(suiteRun && suiteRun.errors || []).join('; ') || 'no checks'}` })
  return { status: 'halted', at: 'smoke-suite', decision, report }
}

// Staging deploy (reversible-internal — routed through qdecide for the record).
const stagingDeploy = await agent(
  buildStagingDeployPrompt(deployTarget, { planPath: deployPlanPath }),
  { label: 'staging-deploy', model: 'sonnet', phase: 'Deploy', schema: DEPLOY_SCHEMA },
)
if (!stagingDeploy || !stagingDeploy.ok) {
  const decision = await qdecide({ type: 'staging-deploy', reason: `Staging deploy failed: ${(stagingDeploy && stagingDeploy.reason) || 'no result'}` })
  return { status: 'halted', at: 'staging-deploy', decision, report }
}

// Staging smoke: the FULL curated suite via parallel Haiku fan-out.
const stagingSmoke = await runSmoke(suiteChecks, { url: deployTarget.stagingUrl, environment: 'staging' })
report.stagingSmoke = stagingSmoke
if (!stagingSmoke.ok) {
  // Staging smoke failed → NEVER touch prod. Escalate.
  const decision = await qdecide({ type: 'staging-deploy', reason: `Staging smoke failed (${stagingSmoke.passed}/${stagingSmoke.total}): ${stagingSmoke.failed.join(', ')}` })
  return { status: 'halted', at: 'staging-smoke', decision, report }
}

// Fan the curated suite out in batches (order-preserving) and combine all-or-nothing.
// Pure helpers mirror prod-tail.py; the batches drive parallel() Haiku smoke agents.
async function runSmoke(checks, { url, environment }) {
  const batches = planSmokeBatches(checks, smokeBatchSize)
  const batchResults = await parallel(
    batches.map((b) => () => agent(
      buildSmokeBatchPrompt(b, { url, environment }),
      { label: `smoke:${environment}:${b.length}`, model: 'haiku', phase: 'Deploy', schema: SMOKE_BATCH_SCHEMA },
    )),
  )
  const flat = []
  for (const r of batchResults.filter(Boolean)) for (const x of (r.results || [])) flat.push(x)
  return aggregateSmoke(flat)
}

// The convergence artifacts, mapped to the {name,p0,p1} shape the gate checks. By
// this point every one has converged (0 P0/P1) or the pipeline already halted.
function convergedArtifacts() {
  const arts = report.artifacts || {}
  return Object.keys(arts).map((name) => {
    const counts = (arts[name] && arts[name].counts) || {}
    return { name, p0: counts.P0 ?? 0, p1: counts.P1 ?? 0 }
  })
}

// prodAutonomous OFF (`/qpipeline auto`) → staged/verified STOP, before prod.
if (!prodAutonomous) {
  log(`Staging deployed + smoked green (${stagingSmoke.passed}/${stagingSmoke.total}). Stopping before prod (pass prodAutonomous / use \`auto prod\` to deploy).`)
  return { status: 'staged', report }
}

// ── Phase 8: GUARDRAIL GATE → qdecide(irreversible) → prod publish → prod smoke ──
phase('Prod')

// qdecide the IRREVERSIBLE prod deploy. Per H-010 it can never AUTHORIZE; a `decline`
// hard-blocks, and its recommendation feeds the deterministic guardrail gate. The
// prodAutonomous opt-in (a declared `auto prod` + rollbackCmd) is the human's
// pre-authorization; qdecide here acts as a veto/router, not the authorizer.
const qd = await qdecide({
  type: 'prod-deploy',
  reason: `Deploy "${goal}" to production (${deployTarget.kind || 'declared'})`,
  action: `Publish to production: ${deployTarget.prodCmd || '(declared prodCmd)'}`,
})
if (qd.action === 'hard-stop') return { status: 'halted', at: 'prod-guardrail', decision: qd, report }

// Dry-validate the declared rollback command (prod is REFUSED without one). Never
// executes a real rollback.
let rollbackDryOk = false
if (deployTarget.rollbackCmd) {
  const rbDry = await agent(
    [
      `Dry-validate the declared rollback command WITHOUT executing a real rollback: ${deployTarget.rollbackCmd}`,
      'Confirm it exists and would run (e.g. --dry-run / --help / a plan), but do NOT roll anything back.',
      'Return {ok, reason}.',
    ].join('\n'),
    { label: 'rollback-dry-validate', model: 'haiku', phase: 'Prod', schema: GATE_SCHEMA },
  )
  rollbackDryOk = !!(rbDry && rbDry.ok)
}

// Deterministic §6 guardrail gate — prod-tail.py deploy_gate is the single source of
// truth. The agent writes the state JSON to a temp file and runs the gate.
const gateState = buildGateState({
  artifacts: convergedArtifacts(),
  unitGreen: !!verify.ok,
  // SMOKE-005: a dropped slice or unresolved escalation means integration is NOT clean,
  // so the guardrail gate can never pass (defense in depth — the verify-stage blocker
  // check already halts before here when blockers exist).
  integrationGreen: !!verify.ok && !(report.blockers && report.blockers.length),
  stagingSmoke,
  deployTarget,
  rollbackDryOk,
  prodSmokeReviewed: true, // DEPLOY-PLAN converged → prod smoke assertions reviewed up front
  newSmokeChecksAdded: !!(suiteRun && suiteRun.newChecksAdded),
  qdecideDecision: qd.recommendation,
  prodAutonomous,
  humanConfirmed,
})
const gate = await agent(
  [
    'Evaluate the deterministic production guardrail gate. Write this EXACT JSON to a temp file, then run:',
    `  python3 ${toolsDir}/prod-tail.py deploy-gate --state <tempfile> ; echo "EXIT:$?"`,
    'Return {allowed, blockers} exactly as the tool prints (allowed=true only on EXIT:0).',
    '',
    'GATE STATE:',
    JSON.stringify(gateState),
  ].join('\n'),
  { label: 'guardrail-gate', model: 'haiku', phase: 'Prod', schema: DEPLOY_GATE_SCHEMA },
)
report.deployGate = gate || { allowed: false, blockers: ['gate did not run'] }
if (!gate || !gate.allowed) {
  // Surface every blocker in one shot — this is the effective human gate.
  const decision = await qdecide({ type: 'prod-deploy', reason: `Guardrail gate refused prod: ${(gate && gate.blockers || ['unknown']).join('; ')}` })
  return { status: 'halted', at: 'guardrail-gate', gate: report.deployGate, decision, report }
}

// Gate green → PROD PUBLISH (irreversible).
const prodPublish = await agent(
  buildProdPublishPrompt(deployTarget, { planPath: deployPlanPath }),
  { label: 'prod-publish', model: 'sonnet', phase: 'Prod', schema: DEPLOY_SCHEMA },
)
if (!prodPublish || !prodPublish.ok) {
  const decision = await qdecide({ type: 'prod-deploy', reason: `Prod publish failed: ${(prodPublish && prodPublish.reason) || 'no result'}` })
  return { status: 'halted', at: 'prod-publish', decision, report }
}

// Prod smoke: the FULL curated suite against production.
const prodSmoke = await runSmoke(suiteChecks, { url: deployTarget.prodUrl, environment: 'production' })
report.prodSmoke = prodSmoke
if (prodSmoke.ok) {
  log(`PROMOTED: prod deploy of "${goal}" smoked green (${prodSmoke.passed}/${prodSmoke.total}).`)
  return { status: 'promoted', report }
}

// Prod smoke FAILED → rollback_decision (stateful downgrades to hard-page, #7).
const rb = await agent(
  [
    'Prod smoke FAILED. Decide the recovery action deterministically — run exactly:',
    `  python3 ${toolsDir}/prod-tail.py rollback --smoke-failed ${deployTarget.stateful ? '--stateful ' : ''}${deployTarget.rollbackCmd ? '--rollback-present' : ''} ; echo "EXIT:$?"`,
    'Return {action, reason} exactly as printed (action is "rollback" or "hard-page").',
  ].join('\n'),
  { label: 'rollback-decision', model: 'haiku', phase: 'Prod', schema: ROLLBACK_SCHEMA },
)
report.rollback = rb || { action: 'hard-page', reason: 'no result' }
if (!rb || rb.action !== 'rollback') {
  // Stateful or no-rollback target → page a human immediately (no auto-rollback).
  const decision = await qdecide({ type: 'prod-deploy', reason: `Prod smoke failed on a stateful/no-rollback target — HARD PAGE. Failures: ${prodSmoke.failed.join(', ')}` })
  return { status: 'hard-page', at: 'prod-smoke', decision, report }
}

// Auto-rollback → re-smoke to PROVE prod is restored.
const rollback = await agent(
  buildRollbackPrompt(deployTarget),
  { label: 'auto-rollback', model: 'sonnet', phase: 'Prod', schema: DEPLOY_SCHEMA },
)
const reSmoke = await runSmoke(suiteChecks, { url: deployTarget.prodUrl, environment: 'production' })
report.reSmoke = reSmoke
if (rollback && rollback.ok && reSmoke.ok) {
  const decision = await qdecide({ type: 'prod-deploy', reason: `Prod deploy of "${goal}" failed smoke; auto-rollback restored prod (re-smoke ${reSmoke.passed}/${reSmoke.total} green). Review needed.` })
  return { status: 'rolled-back', at: 'prod-smoke', decision, report }
}
// Rollback did NOT restore prod → hard-page immediately.
const decision = await qdecide({ type: 'prod-deploy', reason: `Prod smoke failed AND auto-rollback did NOT restore prod (re-smoke ${reSmoke.passed}/${reSmoke.total}). HARD PAGE.` })
return { status: 'hard-page', at: 'prod-smoke', decision, report }
