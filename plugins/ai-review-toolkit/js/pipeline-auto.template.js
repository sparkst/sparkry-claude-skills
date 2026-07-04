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
const toolsDir = A.toolsDir || '/Users/travis/.claude/ai-review-tools/tools'
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
    config: { threshold, maxRounds, maxParallel },
    engines: {
      runLoop: typeof runLoop,
      buildProposal: typeof buildProposal,
      resolveEscalation: typeof resolveEscalation,
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

const report = { goal, artifacts: {}, slices: null, integration: null }

// ── Phase 0: resolve the reviewer team ───────────────────────────────────
if (team.length < 2) {
  phase('Resolve')
  const t = await agent(
    [
      'Resolve the reviewer team best suited to this goal.',
      `Run: python3 ${toolsDir}/team-selector.py --json (consult its --help for the exact flags to pass the goal).`,
      `Goal: ${JSON.stringify(goal)}`,
      'Return {team:[{name, review_lens, model}, ...]} with at least 2 reviewers.',
    ].join('\n'),
    { label: 'team-resolve', model: 'haiku', schema: TEAM_SCHEMA },
  )
  team = (t && Array.isArray(t.team) ? t.team : []).filter(Boolean)
}
if (team.length < 2) {
  // Deterministic fallback so the loop's ≥2-reviewer invariant always holds.
  team = [
    { name: 'correctness-reviewer', review_lens: 'correctness, requirements coverage, contracts', model: 'sonnet' },
    { name: 'robustness-reviewer', review_lens: 'edge cases, security, failure modes, tests', model: 'sonnet' },
  ]
}
log(`Team resolved: ${team.map((m) => m.name).join(', ')}`)

// ── Phase 1: REQUIREMENTS → converge ─────────────────────────────────────
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
if (stopAfter === 'requirements') return { status: 'stopped', at: 'requirements', report }

// ── Phase 2: DESIGN (contracts + slice decomposition) → converge ─────────
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
const sliceById = {}
for (const s of slices) sliceById[s.id] = s
if (stopAfter === 'design') return { status: 'stopped', at: 'design', report }

// ── Phase 3: separate-context TDD, per slice, one shared worktree each, by wave ──
phase('TDD')
const greenIds = []
for (const wave of waves) {
  // Slices in a wave are independent (disjoint files + disjoint worktree dirs +
  // branches) → build them in parallel, capped by maxParallel. No harness isolation
  // is needed: each slice has ONE named worktree its four agents share.
  const batch = wave.map((id) => sliceById[id]).filter(Boolean)
  const results = await parallel(
    batch.slice(0, maxParallel).map((slice) => () => buildSlice(slice)),
  )
  for (const r of results.filter(Boolean)) if (r.green) greenIds.push(r.id)
  // Any overflow beyond maxParallel builds in a follow-on pass (rare; waves are usually small).
  for (const slice of batch.slice(maxParallel)) {
    const r = await buildSlice(slice)
    if (r && r.green) greenIds.push(r.id)
  }
}
if (stopAfter === 'tdd') return { status: 'stopped', at: 'tdd', greenIds, report }

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
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason: 'Test-writer did not create/return the slice worktree' })
    return { id: slice.id, green: false, decision }
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
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason: `RED gate failed: ${(red && red.reason) || 'no result'}` })
    return { id: slice.id, green: false, decision }
  }
  // Context B — make them green in the SAME worktree; tests frozen + tamper-checked via commits.
  await agent(buildImplementerPrompt(slice, { designPath, redSummary: red.reason, worktreePath }), {
    label: `implementer:${slice.id}`, model: 'sonnet', phase: `Slice ${slice.id}`,
  })
  const green = await agent(
    [
      `Verify slice ${slice.id} in its worktree "${worktreePath}" (cd there first). Diff COMMITS, not dirty state:`,
      `  cd "${worktreePath}" && git diff --name-only pipeline-tests/${slice.id}..HEAD   # everything the implementer changed`,
      `(1) TAMPER-CHECK — every changed path must be one of ${(slice.files || []).join(', ') || '(none)'}, NONE may be a`,
      `test file (${(slice.test_files || []).join(', ') || '(none)'}), and \`git diff --name-only pipeline-tests/${slice.id}..HEAD -- ${(slice.test_files || []).join(' ')}\` MUST be empty`,
      `(interpret with python3 ${toolsDir}/tdd-harness.py check_tamper). (2) GREEN gate — the suite now PASSES with tests`,
      'still collected. Return {ok, reason, tests_collected, exit_code}.',
    ].join('\n'),
    { label: `green-gate:${slice.id}`, model: 'haiku', phase: `Slice ${slice.id}`, schema: GATE_SCHEMA },
  )
  if (!green || !green.ok) {
    await cleanupSlice(slice)
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason: `GREEN/tamper gate failed: ${(green && green.reason) || 'no result'}` })
    return { id: slice.id, green: false, decision }
  }
  return { id: slice.id, green: true }
}

// ── Phase 4/5: serialized integration of the green slice BRANCHES ────────
phase('Integrate')
const mergeRun = await agent(
  [
    'Serially integrate the green slice BRANCHES, ONE AT A TIME, into the current feature branch.',
    'Each green slice committed its tests + impl on a branch `pipeline/<sliceId>` in its own worktree.',
    `Compute the order: python3 ${toolsDir}/integrator.py merge-order --slices ${slicesPath} --green ${greenIds.join(',') || '(none)'}`,
    'For each id in `order` (run from the repo root, NOT a slice worktree): `git merge --no-ff pipeline/<id>`,',
    'then run the FULL suite and interpret with integrator.py merge_gate. On a failing suite, run an IMPL-ONLY',
    'conflict-resolver (the prompt below) — tests stay frozen. After a slice merges green, tear down its worktree:',
    '`git worktree remove --force "${ROOT}.pipeline-wt/<id>" ; git branch -d pipeline/<id> ; git tag -d pipeline-tests/<id>`',
    '(ROOT=$(git rev-parse --show-toplevel)), then `git worktree prune`. Leave failed slices\' branches for triage.',
    'Report {merged:[ids], resolved:[ids], failed:[{id,reason}]}.',
    '',
    'CONFLICT-RESOLVER PROMPT (per failing slice):',
    buildConflictResolverPrompt({ id: '<SLICE>', summary: '<summary>', files: ['<impl files>'], test_files: ['<test files>'], public_contract: '<contract>' }, { suiteFailure: '<the failure>' }),
  ].join('\n'),
  { label: 'integrate', model: 'sonnet', schema: {
      type: 'object', additionalProperties: false, required: ['merged', 'failed'],
      properties: {
        merged: { type: 'array', items: { type: 'string' } },
        resolved: { type: 'array', items: { type: 'string' } },
        failed: { type: 'array', items: { type: 'object', additionalProperties: true, required: ['id'], properties: { id: { type: 'string' }, reason: { type: 'string' } } } },
      },
    } },
)
report.integration = mergeRun || { merged: [], failed: [] }
if (mergeRun && Array.isArray(mergeRun.failed) && mergeRun.failed.length) {
  const decision = await qdecide({ type: 'integration-fail', reason: `Integration failed for: ${mergeRun.failed.map((f) => f.id).join(', ')}` })
  if (halts(decision)) return { status: 'halted', at: 'integration', decision, report }
}

// Cross-slice seam tests from a fresh context, then converge the integration plan.
await agent(buildIntegrationTestWriterPrompt(slices, { designPath, requirementsPath }), {
  label: 'integration-test-writer', model: 'sonnet',
})
await agent(
  [
    `Author ${integrationPlanPath}: how the slices compose, the seams under test, and the deploy/verify checklist. Read ${designPath}.`,
    '',
    DOC_ONLY,
  ].join('\n'),
  { label: 'integration-plan-author', model: 'sonnet' },
)
const intPlanRun = await converge(integrationPlanPath, { rounds: undefined, maxRounds: 3 })
report.artifacts.integration_plan = intPlanRun.outcome
if (halts(intPlanRun.decision)) return { status: 'halted', at: 'integration-plan', decision: intPlanRun.decision, report }
if (stopAfter === 'integration') return { status: 'stopped', at: 'integration', report }

// ── Phase 6: unit + integration verify (hard gate), scorecard ────────────
phase('Verify')
const verify = await agent(
  [
    'Run the FULL test suite (unit + integration) as a hard gate. Do NOT fix anything.',
    `  python3 ${toolsDir}/test-runner.py --json (or the project's test command).`,
    'Return {ok, reason, tests_collected, exit_code} — ok=true only if everything passes.',
  ].join('\n'),
  { label: 'verify', model: 'sonnet', schema: GATE_SCHEMA },
)
report.verify = verify || { ok: false, reason: 'no result' }
if (!verify || !verify.ok) {
  const decision = await qdecide({ type: 'converge', artifact: 'full-suite', reason: `Final verify failed: ${(verify && verify.reason) || 'no result'}` })
  return { status: 'halted', at: 'verify', decision, report }
}

// deployTarget null → stop at the verified point (plain `/qpipeline auto`, no deploy).
if (!deployTarget) {
  log('Pipeline complete to verified stop. deployTarget=null (stop-at-verify).')
  return { status: 'verified', report }
}

// ── Phase 7: the production tail (DEPLOY-PLAN → staging deploy → staging smoke) ──
// A deployTarget is DECLARED, so run the reversible staging tail. The prod tail
// (phase 8) only runs under prodAutonomous (`/qpipeline auto prod`).
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
  integrationGreen: !!verify.ok,
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
