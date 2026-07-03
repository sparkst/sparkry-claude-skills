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
const deployTarget = A.deployTarget ?? null
const prodAutonomous = A.prodAutonomous === true
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
      buildConflictResolverPrompt: typeof buildConflictResolverPrompt,
      buildIntegrationTestWriterPrompt: typeof buildIntegrationTestWriterPrompt,
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

// ── Phase 3: separate-context TDD, per slice, one worktree each, by wave ──
phase('TDD')
const greenIds = []
for (const wave of waves) {
  // Slices in a wave are independent (disjoint files) → build them in parallel,
  // capped by maxParallel, each in its own git worktree.
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

// One slice: TEST-WRITER (red-gated) then IMPLEMENTER (tests read-only, tamper-checked, green-gated),
// each converged. Runs in an isolated worktree so parallel slices never clobber each other.
async function buildSlice(slice) {
  // Context A — author failing tests.
  await agent(buildTestWriterPrompt(slice, { requirementsPath, designPath }), {
    label: `test-writer:${slice.id}`, model: 'sonnet', isolation: 'worktree',
    phase: `Slice ${slice.id}`,
  })
  const red = await agent(
    [
      `Run the tests for slice ${slice.id} and report the RED gate.`,
      `  python3 ${toolsDir}/test-runner.py --json (or the project's test command) for: ${(slice.test_files || []).join(', ')}`,
      `Then interpret with: python3 ${toolsDir}/tdd-harness.py (red_gate semantics: must FAIL with ≥1 test collected).`,
      'Return {ok, reason, tests_collected, exit_code}. ok=true only if the tests fail pre-implementation.',
    ].join('\n'),
    { label: `red-gate:${slice.id}`, model: 'haiku', isolation: 'worktree', phase: `Slice ${slice.id}`, schema: GATE_SCHEMA },
  )
  if (!red || !red.ok) {
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason: `RED gate failed: ${(red && red.reason) || 'no result'}` })
    return { id: slice.id, green: false, decision }
  }
  // Context B — make them green, tests frozen + tamper-checked.
  await agent(buildImplementerPrompt(slice, { designPath, redSummary: red.reason }), {
    label: `implementer:${slice.id}`, model: 'sonnet', isolation: 'worktree', phase: `Slice ${slice.id}`,
  })
  const green = await agent(
    [
      `Verify slice ${slice.id}: (1) TAMPER-CHECK — the frozen test files ${(slice.test_files || []).join(', ')} are`,
      `unchanged and the diff touched only ${(slice.files || []).join(', ')} (tdd-harness.py check_tamper); (2) GREEN`,
      'gate — the suite now PASSES with tests still collected. Return {ok, reason, tests_collected, exit_code}.',
    ].join('\n'),
    { label: `green-gate:${slice.id}`, model: 'haiku', isolation: 'worktree', phase: `Slice ${slice.id}`, schema: GATE_SCHEMA },
  )
  if (!green || !green.ok) {
    const decision = await qdecide({ type: 'converge', artifact: slice.id, reason: `GREEN/tamper gate failed: ${(green && green.reason) || 'no result'}` })
    return { id: slice.id, green: false, decision }
  }
  return { id: slice.id, green: true }
}

// ── Phase 4/5: serialized integration of the green worktrees ─────────────
phase('Integrate')
const mergeRun = await agent(
  [
    'Serially integrate the green slice worktrees, ONE AT A TIME, into the feature branch.',
    `Compute the order: python3 ${toolsDir}/integrator.py merge-order --slices ${slicesPath} --green ${greenIds.join(',') || '(none)'}`,
    'For each id in `order`: merge its worktree, run the FULL suite, and interpret with integrator.py',
    'merge_gate. On a failing suite, run an IMPL-ONLY conflict-resolver (the prompt below) — tests stay frozen.',
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

// deployTarget null → stop at a verified point (the prod tail is Phase F, opt-in).
log(`Pipeline complete to verified stop. deployTarget=${deployTarget ? (deployTarget.kind || 'declared') : 'null (stop-at-verify)'}.`)
return { status: 'verified', report }
