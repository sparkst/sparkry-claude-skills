// Shared review→synthesize→gate→fix convergence loop engine.
//
// Extracted from review-loop so BOTH review-loop.workflow.js and the future
// pipeline-auto.workflow.js can run the SAME drift-locked loop per artifact
// WITHOUT nesting workflow() (which is one level only). The Workflow globals
// (agent/parallel/phase/log) are injected via `ctx`, so this stays a pure,
// unit-testable function with no hidden dependency on the sandbox runtime.
//
// These imports are STRIPPED at build time — build-workflow.mjs inlines
// adjudication.mjs / prompts.mjs / workflow-helpers.mjs / this file into one
// scope, so the bare references resolve there. The imports exist only for
// standalone node use + loop-engine.test.mjs.

import {
  synthesizeFindings,
  countBySeverity,
  checkConvergence,
  checkFixCompleteness,
} from "./adjudication.mjs";
import { formatFindings, REVIEWER_OUTPUT_INSTRUCTIONS } from "./prompts.mjs";
import { ensureUniqueIds } from "./workflow-helpers.mjs";

// ---------------------------------------------------------------------------
// Structured-output schemas (agents are forced to return these shapes)
// ---------------------------------------------------------------------------

export const FINDING_PROPS = {
  id: { type: 'string', description: 'P[0-3]-<alphanumeric 3+>, e.g. P0-a1b' },
  severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
  title: { type: 'string' },
  requirement: { type: 'string' },
  finding: { type: 'string' },
  recommendation: { type: 'string' },
  source: { type: 'string' },
  evidence: { type: 'string', description: 'file:line or section:quote, if applicable' },
  // OPTIONAL. Reviewer flag: a P2/P3 that is actually significant (real risk /
  // requirement gap), so it gets the full fix-loop rather than a cheap spot-fix.
  // Additive-only: the drift-locked adjudication ignores it, so the golden
  // corpus stays frozen.
  significance: { type: 'boolean', description: 'true = this P2/P3 is significant, full-loop it (not a trivial cosmetic nit)' },
}

// Cheap verification of trivial spot-fixes.
const SPOTCHECK_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['all_applied', 'not_applied'],
  properties: {
    all_applied: { type: 'boolean' },
    not_applied: { type: 'array', items: { type: 'string' }, description: 'finding ids whose spot-fix did not land' },
  },
}

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'severity', 'title', 'requirement', 'finding', 'recommendation', 'source'],
        properties: FINDING_PROPS,
      },
    },
  },
}

const RESOLUTIONS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['resolutions'],
  properties: {
    resolutions: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['finding_id', 'status', 'evidence', 'description'],
        properties: {
          finding_id: { type: 'string' },
          status: { type: 'string', enum: ['FIXED', 'ESCALATED'] },
          evidence: { type: 'string', description: 'what changed and where (file:line)' },
          description: { type: 'string' },
        },
      },
    },
  },
}

const TEST_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'all_passed', 'failures'],
  properties: {
    summary: { type: 'string' },
    all_passed: { type: 'boolean' },
    failures: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'severity', 'title', 'requirement', 'finding', 'recommendation', 'source'],
        properties: FINDING_PROPS,
      },
    },
  },
}

// ---------------------------------------------------------------------------
// Prompt assembly for the sandboxed script.
//
// The script cannot read files, so reviewer/fixer prompts reference the
// artifact/requirements by PATH and instruct the agent to Read them. Prior-round
// findings ARE held in memory, so they are embedded via formatFindings().
// ---------------------------------------------------------------------------

function reviewerPrompt(agentDef, roundNum, artifact, requirements, testSummary, priorFindings, priorResolutions) {
  const parts = [
    `You are a ${agentDef.name} reviewing an artifact.`,
    '',
    `Your review lens: ${agentDef.review_lens}`,
    '',
    `Read the artifact at: ${artifact}`,
    `Read the requirements at: ${requirements}`,
    '',
    '## Test Results',
    '',
    testSummary || 'No test results available.',
  ]

  if (roundNum > 1) {
    if (priorFindings.length) {
      parts.push('', `## Prior Round Findings (Round ${roundNum - 1})`, '', formatFindings(priorFindings))
    }
    if (priorResolutions.length) {
      const resLines = []
      for (const res of priorResolutions) {
        resLines.push(`- **${res.finding_id ?? '?'}**: ${res.status ?? '?'} -- ${res.description ?? ''}`)
        if (res.evidence) resLines.push(`  Evidence: ${res.evidence}`)
      }
      parts.push('', '## Fix Resolutions Applied', '', resLines.join('\n'))
    }
    parts.push(
      '',
      '## Verification Instructions',
      '',
      `The artifact on disk is the POST-FIX version (after round ${roundNum - 1} fixes). For each ` +
        'resolution above, navigate to the cited evidence and verify the fix is correct. Also check ' +
        'for NEW issues introduced by the fixes — regressions, broken logic, incomplete changes.',
    )
  }

  parts.push(
    '',
    '## Instructions',
    '',
    `Review the artifact against the requirements through your lens of ${agentDef.review_lens}.`,
    '',
    REVIEWER_OUTPUT_INSTRUCTIONS.replace('{reviewer_name}', agentDef.name),
  )
  return parts.join('\n')
}

function fixerPrompt(artifact, requirements, testSummary, findings) {
  return [
    'You are a fixer agent. Fix ALL findings from the review, editing files IN PLACE so the changes persist.',
    '',
    `Artifact to fix: ${artifact}`,
    `Requirements: ${requirements}`,
    '',
    '## Test Results',
    '',
    testSummary || '',
    '',
    '## Findings to Fix (ALL must be addressed)',
    '',
    formatFindings(findings),
    '',
    '## Instructions',
    '',
    'Fix EVERY finding above, regardless of severity (P0 through P3). Apply the edits to the artifact on disk.',
    'For each finding, return a resolution with these fields:',
    '- finding_id: copy the finding\'s id EXACTLY as shown in its heading above (e.g. "P0-001" or',
    '  "P0-001-2") — verbatim, do NOT shorten, rename, or append anything to it. The gate matches ids literally.',
    '- status: "FIXED" (with evidence) or "ESCALATED" (with justification if genuinely unfixable). No',
    '  WONTFIX/DEFERRED/OUT_OF_SCOPE.',
    '- evidence: what changed and where (file:line).',
    '- description: brief explanation of the fix.',
  ].join('\n')
}

function spotFixerPrompt(artifact, requirements, trivialFindings) {
  return [
    'You are a spot-fixer for TRIVIAL, low-risk findings (cosmetic nits, style, minor wording).',
    'Apply each fix IN PLACE, minimally and safely — do NOT refactor or change behavior.',
    '',
    `Artifact to fix: ${artifact}`,
    `Requirements: ${requirements}`,
    '',
    '## Trivial findings to spot-fix',
    '',
    formatFindings(trivialFindings),
    '',
    '## Instructions',
    '',
    'Make the smallest edit that resolves each nit. For each, return a resolution: finding_id (copy the id',
    'EXACTLY as shown in its heading — verbatim), status "FIXED" (with evidence) or "ESCALATED" (if it is not',
    'actually trivial), evidence (file:line), and a one-line description.',
  ].join('\n')
}

function spotCheckPrompt(artifact, trivialResolutions) {
  const lines = trivialResolutions.map((r) => `- ${r.finding_id}: ${r.evidence ?? ''}`)
  return [
    'Spot-check that these trivial fixes actually landed in the artifact. Read ONLY the cited evidence',
    'locations — do not re-review the whole file.',
    '',
    `Artifact: ${artifact}`,
    '',
    '## Claimed trivial fixes',
    '',
    lines.join('\n'),
    '',
    'Return all_applied (true if every cited fix is present) and not_applied (the finding ids whose fix is missing).',
  ].join('\n')
}

// Normalized title for recurrence + stuck detection.
function normTitle(f) {
  return String(f.title ?? '').trim().toLowerCase().replace(/\s+/g, ' ')
}

// Normalized P0/P1 title set for stuck detection.
function p0p1Titles(findings) {
  const s = new Set()
  for (const f of findings) {
    if (f.severity === 'P0' || f.severity === 'P1') s.add(normTitle(f))
  }
  return s
}
const sameSet = (a, b) => a.size === b.size && [...a].every((x) => b.has(x))

// A finding is SIGNIFICANT (gets the full fix-loop) if it is P0/P1, a reviewer
// flagged it significant, or its title recurred from the previous round
// (persistence = significance). Otherwise it is TRIVIAL (spot-fix + spot-check).
//
// `flaggedTitles` and `prevTitles` are matched by normalized title because
// deduplicateFindings rebuilds merged findings without the `significance` field
// (it is not part of the drift-locked adjudication schema), so the flag is
// captured from the RAW reviewer findings before synthesis.
function isSignificant(f, prevTitles, flaggedTitles) {
  const t = normTitle(f)
  return (
    f.severity === 'P0' ||
    f.severity === 'P1' ||
    flaggedTitles.has(t) ||
    prevTitles.has(t)
  )
}

// ---------------------------------------------------------------------------
// The convergence loop — mirrors loop-driver.py's state machine.
// ---------------------------------------------------------------------------

/**
 * Run the review→synthesize→gate→fix loop for a single artifact.
 *
 * @param config { artifact, requirements, team, threshold, rounds, maxRounds }
 *   rounds===1 → single-pass diagnose (qreview: min 1 round, no fixer beyond it);
 *   otherwise until-converged (qloop: min 2 rounds, in-place fixer per round).
 * @param ctx { agent, parallel, phase, log } — the injected Workflow globals.
 * @returns { outcome, rounds, final_findings, final_counts, history }
 */
export async function runLoop(config, ctx) {
  const { agent, parallel, phase, log } = ctx
  const {
    artifact,
    requirements,
    team = [],
    threshold = 0,
    rounds,
    maxRounds: maxRoundsArg,
  } = config

  const singleRound = rounds === 1
  const minRounds = singleRound ? 1 : 2
  const maxRounds = Math.max(maxRoundsArg ?? (singleRound ? 1 : 5), minRounds)

  if (!artifact || !requirements) throw new Error('runLoop requires artifact and requirements')
  if (team.length < 2 && !singleRound) throw new Error('runLoop requires at least 2 reviewers (team)')

  const roundReports = []
  let priorFindings = []
  let priorResolutions = []
  let prevP0P1 = null
  let prevAllTitles = new Set() // for recurrence-based significance promotion
  let outcome = null

  for (let r = 1; r <= maxRounds; r++) {
    phase(r === 1 ? 'Review' : `Review (round ${r})`)

    // Deterministic test gate — an agent runs the project's tests, returns a summary.
    const test = await agent(
      `Run this project's test suite (prefer \`python3 tools/test-runner.py\` if present, else the project's ` +
        `standard test command) for the artifact at ${artifact}. Do NOT fix anything. Report a one-line summary, ` +
        `whether all passed, and any failures as P0/P1 findings.`,
      { label: `tests:r${r}`, phase: `Round ${r}`, model: 'sonnet', schema: TEST_SCHEMA },
    )
    const testSummary = test?.summary ?? 'No test results available.'

    // Fan out N clean-context reviewers with their resolved models.
    const reviews = await parallel(
      team.map((agentDef) => () =>
        agent(reviewerPrompt(agentDef, r, artifact, requirements, testSummary, priorFindings, priorResolutions), {
          label: `review:${agentDef.name}:r${r}`,
          phase: `Round ${r}`,
          model: agentDef.model || 'sonnet',
          schema: FINDINGS_SCHEMA,
        }),
      ),
    )

    const reviewerLists = reviews.filter(Boolean).map((x) => x.findings || [])
    if (test?.failures?.length) reviewerLists.push(test.failures)

    // Capture reviewer `significance` flags from the RAW findings by normalized
    // title, BEFORE synthesis strips the field during dedup.
    const flaggedTitles = new Set()
    for (const list of reviewerLists) {
      for (const f of list) if (f && f.significance === true) flaggedTitles.add(normTitle(f))
    }

    const dropped = []
    // Reviewers number findings independently, so distinct findings collide on
    // ids (e.g. two P0-001s). Make them unique so the id-keyed fix-ALL gate is
    // meaningful and the fixer can echo exact ids.
    const findings = ensureUniqueIds(synthesizeFindings(reviewerLists, dropped))
    const counts = countBySeverity(findings)

    // Split into significant (full fix-loop) and trivial (spot-fix). P0/P1 are
    // always significant; a recurring or reviewer-flagged P2/P3 is too.
    const significant = findings.filter((f) => isSignificant(f, prevAllTitles, flaggedTitles))
    const trivial = findings.filter((f) => !isSignificant(f, prevAllTitles, flaggedTitles))

    // The LOOP gate is significant-only: trivial P2/P3 don't block convergence
    // (they're spot-fixed opportunistically). P0/P1 stay 0-total-hard because
    // they're always significant.
    const { converged, message } = checkConvergence(significant, threshold)
    const newP0P1 = findings.filter(
      (f) => (f.severity === 'P0' || f.severity === 'P1') && !prevP0P1?.has(normTitle(f)),
    ).length
    roundReports.push({ round: r, findings, counts, significant: significant.length, trivial: trivial.length, newP0P1, dropped: dropped.length, converged, message })
    log(`Round ${r}: ${findings.length} findings (P0=${counts.P0} P1=${counts.P1} P2=${counts.P2} P3=${counts.P3}; ${significant.length} significant / ${trivial.length} trivial, ${newP0P1} new P0/P1) — ${message}`)

    // Spot-fix trivial nits cheaply (Haiku) + a light spot-check. Opportunistic,
    // non-blocking, doesn't reset the convergence counter.
    let trivialResolutions = []
    if (trivial.length) {
      const spot = await agent(spotFixerPrompt(artifact, requirements, trivial), {
        label: `spotfix:r${r}`, phase: `Round ${r}`, model: 'haiku', schema: RESOLUTIONS_SCHEMA,
      })
      trivialResolutions = spot?.resolutions || []
      if (trivialResolutions.length) {
        const check = await agent(spotCheckPrompt(artifact, trivialResolutions), {
          label: `spotcheck:r${r}`, phase: `Round ${r}`, model: 'haiku', schema: SPOTCHECK_SCHEMA,
        })
        if (check && check.all_applied === false && check.not_applied?.length) {
          log(`Round ${r}: spot-check flagged ${check.not_applied.length} trivial fix(es) not applied: ${check.not_applied.join(', ')}`)
        }
      }
    }

    // Converged (no significant findings) AND past the minimum-rounds floor → done.
    if (converged && r >= minRounds) {
      outcome = { status: 'converged', message, round: r }
      break
    }

    // Out of rounds → escalate with the unresolved P0/P1s.
    if (r >= maxRounds) {
      const unresolved = findings.filter((f) => f.severity === 'P0' || f.severity === 'P1')
      outcome = { status: 'escalated', reason: `Max rounds (${maxRounds}) reached without convergence. ${message}.`, unresolved, round: r }
      break
    }

    // Significant cleared early but below the floor → advance to re-review.
    if (converged) {
      priorFindings = findings
      priorResolutions = trivialResolutions
      prevP0P1 = p0p1Titles(findings)
      prevAllTitles = new Set(findings.map(normTitle))
      continue
    }

    // Not converged → full in-place fixer for the SIGNIFICANT findings.
    phase(`Fix (round ${r})`)
    const fix = await agent(fixerPrompt(artifact, requirements, testSummary, significant), {
      label: `fix:r${r}`,
      phase: `Round ${r}`,
      model: 'sonnet',
      schema: RESOLUTIONS_SCHEMA,
    })
    const resolutions = fix?.resolutions || []

    // Fix-ALL gate — every SIGNIFICANT finding needs a FIXED/ESCALATED resolution with evidence.
    const { complete, missing } = checkFixCompleteness(significant, resolutions)
    if (!complete) {
      outcome = { status: 'escalated', reason: `Fix-ALL gate failed: ${missing.length} finding(s) unresolved (${missing.join(', ')}).`, unresolved: significant.filter((f) => missing.includes(String(f.id))), round: r }
      break
    }

    // Stuck detection — identical P0/P1 set across two consecutive rounds.
    const curP0P1 = p0p1Titles(findings)
    if (prevP0P1 && curP0P1.size > 0 && sameSet(prevP0P1, curP0P1)) {
      outcome = { status: 'escalated', reason: `Stuck: identical P0/P1 findings in rounds ${r - 1} and ${r}. Fix approach is not working.`, unresolved: findings.filter((f) => f.severity === 'P0' || f.severity === 'P1'), round: r }
      break
    }

    priorFindings = findings
    priorResolutions = [...resolutions, ...trivialResolutions]
    prevP0P1 = curP0P1
    prevAllTitles = new Set(findings.map(normTitle))
  }

  const last = roundReports[roundReports.length - 1] || {}
  return {
    outcome,
    rounds: roundReports.length,
    final_findings: last.findings || [],
    final_counts: last.counts || countBySeverity([]),
    history: roundReports.map((rr) => ({
      round: rr.round, counts: rr.counts, significant: rr.significant, trivial: rr.trivial,
      newP0P1: rr.newP0P1, converged: rr.converged, message: rr.message,
    })),
  }
}
