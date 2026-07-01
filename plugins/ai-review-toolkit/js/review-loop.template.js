export const meta = {
  name: 'review-loop',
  description: 'Multi-agent review→synthesize→gate→fix convergence loop (qreview=1 round, qloop=until-converged)',
  phases: [
    { title: 'Review', detail: 'N clean-context reviewers in parallel per round' },
    { title: 'Fix', detail: 'single in-place fixer per round; fixes persist to next round' },
  ],
}

// @@INLINE@@ build-workflow.mjs replaces this whole line with adjudication.mjs + prompts.mjs

// ---------------------------------------------------------------------------
// Structured-output schemas (agents are forced to return these shapes)
// ---------------------------------------------------------------------------

const FINDING_PROPS = {
  id: { type: 'string', description: 'P[0-3]-<alphanumeric 3+>, e.g. P0-a1b' },
  severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
  title: { type: 'string' },
  requirement: { type: 'string' },
  finding: { type: 'string' },
  recommendation: { type: 'string' },
  source: { type: 'string' },
  evidence: { type: 'string', description: 'file:line or section:quote, if applicable' },
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
// Unlike the Python driver, this script cannot read files, so reviewer/fixer
// prompts reference the artifact/requirements by PATH and instruct the agent to
// Read them. Prior-round findings ARE held in memory by the script, so they are
// embedded via the inlined formatFindings().
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
    'For each finding, return a resolution: finding_id, status ("FIXED" with evidence, or "ESCALATED" with',
    'justification if genuinely unfixable — no WONTFIX/DEFERRED/OUT_OF_SCOPE), evidence (what changed and where),',
    'and description.',
  ].join('\n')
}

// ---------------------------------------------------------------------------
// The convergence loop — mirrors loop-driver.py's state machine.
// ---------------------------------------------------------------------------

// `args` may arrive as a parsed object or a JSON string, depending on how the
// Workflow was invoked; tolerate both.
const A = typeof args === "string" ? JSON.parse(args) : (args || {})
const artifact = A.artifact
const requirements = A.requirements
const team = A.team || []
const threshold = A.threshold ?? 0
const singleRound = A.rounds === 1
const minRounds = singleRound ? 1 : 2
const maxRounds = Math.max(A.maxRounds ?? (singleRound ? 1 : 5), minRounds)

if (!artifact || !requirements) throw new Error('review-loop requires args.artifact and args.requirements')
if (team.length < 2 && !singleRound) throw new Error('review-loop requires at least 2 reviewers (args.team)')

// Normalized P0/P1 title set for stuck detection.
function p0p1Titles(findings) {
  const s = new Set()
  for (const f of findings) {
    if (f.severity === 'P0' || f.severity === 'P1') {
      s.add(String(f.title ?? '').trim().toLowerCase().replace(/\s+/g, ' '))
    }
  }
  return s
}
const sameSet = (a, b) => a.size === b.size && [...a].every((x) => b.has(x))

const roundReports = []
let priorFindings = []
let priorResolutions = []
let prevP0P1 = null
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

  const dropped = []
  const findings = synthesizeFindings(reviewerLists, dropped)
  const counts = countBySeverity(findings)
  const { converged, message } = checkConvergence(findings, threshold)
  roundReports.push({ round: r, findings, counts, dropped: dropped.length, converged, message })
  log(`Round ${r}: ${findings.length} findings (P0=${counts.P0} P1=${counts.P1} P2=${counts.P2} P3=${counts.P3}) — ${message}`)

  // Converged AND past the minimum-rounds floor → done.
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

  // Converged early but below the floor → advance to re-review, no fix needed.
  if (converged) {
    priorFindings = findings
    priorResolutions = []
    prevP0P1 = p0p1Titles(findings)
    continue
  }

  // Not converged → single in-place fixer for ALL findings.
  phase(`Fix (round ${r})`)
  const fix = await agent(fixerPrompt(artifact, requirements, testSummary, findings), {
    label: `fix:r${r}`,
    phase: `Round ${r}`,
    model: 'sonnet',
    schema: RESOLUTIONS_SCHEMA,
  })
  const resolutions = fix?.resolutions || []

  // Fix-ALL gate — every finding needs a FIXED/ESCALATED resolution with evidence.
  const { complete, missing } = checkFixCompleteness(findings, resolutions)
  if (!complete) {
    outcome = { status: 'escalated', reason: `Fix-ALL gate failed: ${missing.length} finding(s) unresolved (${missing.join(', ')}).`, unresolved: findings.filter((f) => missing.includes(String(f.id))), round: r }
    break
  }

  // Stuck detection — identical P0/P1 set across two consecutive rounds.
  const curP0P1 = p0p1Titles(findings)
  if (prevP0P1 && curP0P1.size > 0 && sameSet(prevP0P1, curP0P1)) {
    outcome = { status: 'escalated', reason: `Stuck: identical P0/P1 findings in rounds ${r - 1} and ${r}. Fix approach is not working.`, unresolved: findings.filter((f) => f.severity === 'P0' || f.severity === 'P1'), round: r }
    break
  }

  priorFindings = findings
  priorResolutions = resolutions
  prevP0P1 = curP0P1
}

const last = roundReports[roundReports.length - 1] || {}
return {
  outcome,
  rounds: roundReports.length,
  final_findings: last.findings || [],
  final_counts: last.counts || countBySeverity([]),
  history: roundReports.map((rr) => ({ round: rr.round, counts: rr.counts, converged: rr.converged, message: rr.message })),
}
