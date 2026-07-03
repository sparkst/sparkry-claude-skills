// Production-tail prompt builders + fan-out helpers (Phase F2 of /qpipeline auto).
//
// The prod tail is the ONLY phase that can touch production. Its safety verdicts
// (the §6 guardrail gate, the stateful rollback downgrade) are deterministic and
// live single-source in prod-tail.py; this module holds the AGENT-facing prompt
// builders and the two trivial in-process control helpers the workflow needs to
// drive the parallel smoke fan-out.
//
//   - buildDeployPlanPrompt   -- author DEPLOY-PLAN.md: declared commands, smoke
//                                assertions, rollback criteria; forces the feature
//                                to append its checks to the cumulative suite.
//   - buildStagingDeployPrompt / buildProdPublishPrompt -- run EXACTLY the declared
//                                staging / prod command (never inferred).
//   - buildSmokeBatchPrompt   -- a Haiku agent runs a batch of curated checks
//                                against a URL and reports per-check pass/fail.
//   - buildRollbackPrompt     -- run EXACTLY the declared rollback command.
//   - planSmokeBatches / aggregateSmoke -- pure JS mirrors of prod-tail.py's
//                                plan_smoke_batches / aggregate_smoke, run in-process
//                                so the workflow can fan out parallel() smoke agents
//                                and combine their results (the multi-input safety
//                                verdicts stay in python).
//   - buildGateState          -- assemble the deploy_gate --state dict from the run.
//
// Pure builders (no I/O) — the agents Read the real files and run the real commands.
// Inlined into pipeline-auto.workflow.js in Phase F2 alongside the other helpers.

/**
 * Author DEPLOY-PLAN.md: the declared deploy commands (echoed, never invented), the
 * staging + prod smoke assertions, the rollback command, and the promote/rollback
 * criteria — plus the requirement that this feature APPEND its smoke checks to the
 * cumulative suite (a feature that ships no smoke check for its new behavior fails
 * the guardrail gate).
 */
export function buildDeployPlanPrompt(deployTarget, { requirementsPath, designPath, planPath = 'DEPLOY-PLAN.md', suitePath = 'smoke/prod.suite.json' } = {}) {
  const dt = deployTarget ?? {}
  return [
    `Author the deployment plan at ${planPath} for a ${dt.kind ?? 'declared'} target.`,
    'Cover, using the DECLARED commands exactly (echo them — do NOT invent or auto-detect):',
    `  - staging deploy: ${dt.stagingCmd ?? '(none declared)'}`,
    `  - prod deploy:    ${dt.prodCmd ?? '(none declared)'}`,
    `  - rollback:       ${dt.rollbackCmd ?? '(none declared)'}`,
    'Define the staging + prod smoke assertions to run and the promote-vs-rollback criteria.',
    '',
    `Every NEW behavior in this feature MUST add at least one NEW check to the cumulative smoke suite`,
    `${suitePath} (a growing regression net) — append them there now. A feature that adds no smoke check`,
    'for its new behavior fails the deterministic guardrail gate.',
    '',
    `Declared deploy target: ${JSON.stringify(dt)}`,
    `Design: read ${designPath ?? 'DESIGN.md'}. Requirements: read ${requirementsPath ?? 'REQUIREMENTS.md'}.`,
    '',
    `Write ONLY the deployment plan (${planPath}) and, if needed, append checks to ${suitePath}.`,
    'Do NOT deploy anything, run no deploy/publish/rollback commands, and touch no source or test files.',
  ].join('\n')
}

/**
 * Deploy the feature branch to STAGING only, running exactly the declared staging
 * command. Never touches production.
 */
export function buildStagingDeployPrompt(deployTarget, { planPath = 'DEPLOY-PLAN.md' } = {}) {
  const dt = deployTarget ?? {}
  return [
    'You are a STAGING-DEPLOY agent. Deploy the current feature branch to STAGING only.',
    `Run EXACTLY the declared staging command: ${dt.stagingCmd ?? '(none declared)'}`,
    dt.stagingUrl ? `Staging URL (for the smoke step): ${dt.stagingUrl}` : '',
    `Follow ${planPath}. Do NOT deploy to production and do NOT run the prod command.`,
    'Return {ok, reason, url} — ok=true only if the staging deploy succeeded.',
  ].filter(Boolean).join('\n')
}

/**
 * Publish to PRODUCTION, running exactly the declared prod command. This is
 * IRREVERSIBLE and only runs because the guardrail gate already passed.
 */
export function buildProdPublishPrompt(deployTarget, { planPath = 'DEPLOY-PLAN.md' } = {}) {
  const dt = deployTarget ?? {}
  return [
    'You are a PROD-PUBLISH agent. The guardrail gate passed; publish to PRODUCTION now.',
    'This is an IRREVERSIBLE production deploy — run ONLY the single declared command, nothing else.',
    `Run EXACTLY the declared prod command: ${dt.prodCmd ?? '(none declared)'}`,
    dt.prodUrl ? `Prod URL (for the smoke step): ${dt.prodUrl}` : '',
    `Follow ${planPath}. Do NOT modify source, tests, or the deploy plan.`,
    'Return {ok, reason, url} — ok=true only if the prod publish succeeded.',
  ].filter(Boolean).join('\n')
}

/**
 * Run a batch of curated smoke checks against a deployed URL and report per-check
 * pass/fail with evidence. Observe only — never fix or deploy.
 */
export function buildSmokeBatchPrompt(batch, { url, environment = 'staging' } = {}) {
  const checks = (batch ?? [])
    .map((c) => `  - ${c.id}: ${c.description ?? ''}${c.assert ? ` (assert: ${c.assert})` : ''}`)
    .join('\n') || '  (no checks)'
  return [
    `You are a SMOKE-TEST agent running a batch of checks against the ${environment} deployment.`,
    url ? `Target URL: ${url}` : 'Target: the deployed service (URL from the deploy plan)',
    '',
    'Run EACH check below and record a pass/fail with concrete evidence (status code, response snippet).',
    'Do NOT fix anything, do NOT deploy, do NOT modify any file — only observe and report.',
    '',
    'Checks:',
    checks,
    '',
    'Return {results:[{id, passed, evidence}]} — exactly one entry per check id above.',
  ].join('\n')
}

/**
 * Roll production back to the last good state, running exactly the declared
 * rollback command. Only invoked after a prod-smoke failure on a stateless target.
 */
export function buildRollbackPrompt(deployTarget) {
  const dt = deployTarget ?? {}
  return [
    'You are a ROLLBACK agent. The prod smoke FAILED — roll production back to the last good state NOW.',
    `Run EXACTLY the declared rollback command: ${dt.rollbackCmd ?? '(none declared)'}`,
    'Do NOT redeploy, do NOT modify source or tests. After it completes, prod will be re-smoked.',
    'Return {ok, reason} — ok=true only if the rollback command completed.',
  ].join('\n')
}

/**
 * In-process mirror of prod-tail.py `plan_smoke_batches`: chunk checks
 * (order-preserving) into batches for parallel Haiku fan-out. Coerces a bad batch
 * size to >=1 so the fan-out never divides by zero.
 */
export function planSmokeBatches(checks, batchSize) {
  const list = Array.isArray(checks) ? checks : []
  const size = Math.max(1, Math.floor(Number(batchSize) || 0) || 1)
  const batches = []
  for (let i = 0; i < list.length; i += size) batches.push(list.slice(i, i + size))
  return batches
}

/**
 * In-process mirror of prod-tail.py `aggregate_smoke`: the curated suite is
 * all-or-nothing and a zero-check run is never a pass.
 */
export function aggregateSmoke(results) {
  const list = Array.isArray(results) ? results : []
  const failed = list.filter((r) => !(r && r.passed)).map((r) => String(r && r.id))
  const total = list.length
  return { ok: total > 0 && failed.length === 0, total, passed: total - failed.length, failed }
}

/**
 * Assemble the deploy_gate --state dict (prod-tail.py deploy_gate is the single
 * source of truth for the verdict). Every field defaults to a BLOCKING value so a
 * missing fact never fails the gate open.
 */
export function buildGateState({
  artifacts = [],
  unitGreen = false,
  integrationGreen = false,
  stagingSmoke = {},
  deployTarget = null,
  rollbackDryOk = false,
  prodSmokeReviewed = false,
  newSmokeChecksAdded = false,
  qdecideDecision = null,
  prodAutonomous = false,
  humanConfirmed = false,
} = {}) {
  const ss = stagingSmoke || {}
  return {
    artifacts: Array.isArray(artifacts) ? artifacts : [],
    unit_green: unitGreen === true,
    integration_green: integrationGreen === true,
    staging_smoke: { total: Number(ss.total) || 0, passed: Number(ss.passed) || 0 },
    rollback_cmd_present: !!(deployTarget && deployTarget.rollbackCmd),
    rollback_dry_ok: rollbackDryOk === true,
    prod_smoke_reviewed: prodSmokeReviewed === true,
    new_smoke_checks_added: newSmokeChecksAdded === true,
    qdecide_decision: qdecideDecision,
    prod_autonomous: prodAutonomous === true,
    human_confirmed: humanConfirmed === true,
  }
}
