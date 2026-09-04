// Shared review→synthesize→gate→fix convergence loop engine.
//
// Extracted from review-loop so BOTH review-loop.workflow.js and the future
// pipeline-auto.workflow.js can run the SAME drift-locked loop per artifact
// WITHOUT nesting workflow() (which is one level only). The Workflow globals
// (agent/parallel/phase/log) are injected via `ctx`, so this stays a pure,
// unit-testable function with no hidden dependency on the sandbox runtime.
//
// These imports are STRIPPED at build time — build-workflow.mjs inlines
// adjudication.mjs / prompts.mjs / workflow-helpers.mjs / stopping-rules.mjs /
// this file into one scope, so the bare references resolve there. The imports
// exist only for standalone node use + loop-engine.test.mjs.

import {
  synthesizeFindings,
  countBySeverity,
  checkConvergence,
  checkFixCompleteness,
  resolveReviewerModel,
} from "./adjudication.mjs";
import { formatFindings, REVIEWER_OUTPUT_INSTRUCTIONS } from "./prompts.mjs";
import {
  ensureUniqueIds,
  adjudicateRound,
  mergeLedger,
  renderLedger,
  attestReviewers,
  describeReviewerShortfall,
  renderAttestation,
} from "./workflow-helpers.mjs";
import {
  DELTA_DEFAULTS,
  isDeltaEligible,
  detectDivergence,
  summarizeBudget,
} from "./stopping-rules.mjs";

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

// Confirmation that a mechanical write/delete landed (OPT-015 history files).
const WROTE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['wrote'],
  properties: { wrote: { type: 'boolean' } },
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
    // SMOKE-008: every repo-relative file path the fixer edited (beyond the artifact
    // itself), so the pipeline commit step can pathspec-commit them and keep the
    // committed tree in sync with what verify runs on.
    edited_files: { type: 'array', items: { type: 'string' } },
  },
}

const TEST_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['summary', 'all_passed', 'failures'],
  properties: {
    summary: { type: 'string' },
    all_passed: { type: 'boolean' },
    // OPTIONAL. The exact test command the gate ran, so rounds 2+ can re-run it
    // verbatim instead of re-discovering it every round (OPT-007).
    command: { type: 'string', description: 'the exact test command that was run' },
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

// The diff probe returns MEASUREMENTS ONLY. Every risk judgment on this payload
// is made by isDeltaEligible() in JS, so the model that would like to skip a
// round never gets to decide whether it may.
const DIFF_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['artifact_lines', 'touched'],
  properties: {
    artifact_lines: { type: 'number', description: 'total line count of the artifact after the fix' },
    truncated: { type: 'boolean', description: 'true if the diff exceeded the cap or could not be read' },
    touched: {
      type: 'array',
      description: 'one entry per added-or-removed line',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['text'],
        properties: {
          text: { type: 'string', description: 'the line content, without the leading + or -' },
          section: { type: 'string', description: 'nearest preceding heading line, or empty' },
        },
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

function reviewerPrompt(agentDef, roundNum, artifact, requirements, testSummary, priorFindings, priorResolutions, historyPath, ledger) {
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
    if (historyPath) {
      // OPT-015: the prior-round findings + resolutions live in a file the
      // reviewer Reads (constant-size prompt) instead of being embedded verbatim
      // in every reviewer's prompt each round. REQUIRED read — no information loss.
      parts.push(
        '',
        `## Prior Round Review Summary (Round ${roundNum - 1})`,
        '',
        `The findings from round ${roundNum - 1} and the fix resolutions applied to them are recorded ` +
          `in a summary file. You are REQUIRED to Read this file before reviewing:`,
        `  ${historyPath}`,
      )
    } else {
      // Fallback (history file not written): embed verbatim as before.
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
    }
    parts.push(
      '',
      '## Verification Instructions',
      '',
      `The artifact on disk is the POST-FIX version (after round ${roundNum - 1} fixes). For each ` +
        'prior resolution, navigate to the cited evidence and verify the fix is correct. Also check ' +
        'for NEW issues introduced by the fixes — regressions, broken logic, incomplete changes.',
    )
    // LEDGER: everything settled in rounds 1..r-1, not just the previous round.
    // The body goes inline, or lives in the history file the reviewer is required
    // to Read (OPT-015). The STANDING RULE is in the prompt itself so it never
    // depends on the reviewer having opened the file — but it is emitted ONLY
    // when the ledger is non-empty. Adjudication lags a round, so round 2's
    // ledger is always empty; announcing a section that isn't there is a false
    // pointer that costs the reviewer a fruitless search.
    if ((ledger ?? []).length) {
    parts.push(
      '',
      '## Adjudicated Findings — Standing Rule',
      '',
      'Some findings from earlier rounds are already ADJUDICATED (fixed, and a later round ' +
        'confirmed the fix held); they are listed under "ADJUDICATED-FINDINGS LEDGER" ' +
        (historyPath ? 'in the summary file above.' : 'below.') +
        ' Do NOT re-litigate them. DO verify each listed fix actually held at its cited evidence, ' +
        'and if one has regressed or been undone, report that as a NEW finding at its proper severity. ' +
        'The ledger is not a list of everything wrong with the artifact — anything it does not ' +
        'mention is fully in scope.',
    )
    const ledgerBlock = historyPath ? '' : renderLedger(ledger ?? [])
    if (ledgerBlock) parts.push('', ledgerBlock)
    }
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
    '',
    'Also return `edited_files`: the list of EVERY repo-relative file path you edited (including files',
    'beyond the artifact itself, e.g. test files) so the pipeline commits them. Omit unchanged files.',
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

// Deterministic test-gate prompt. Round 1 discovers the command; rounds 2+ are
// told to re-run the exact command that worked, avoiding re-discovery (OPT-007).
function testGatePrompt(artifact, roundNum, carriedCommand) {
  const parts = [`Run this project's test suite for the artifact at ${artifact}. Do NOT fix anything.`]
  if (carriedCommand) {
    parts.push(`Run exactly this command (it worked in a prior round): ${carriedCommand}`)
  } else {
    parts.push(`Prefer \`python3 tools/test-runner.py\` if present, else the project's standard test command.`)
  }
  parts.push(
    'Report a one-line summary, whether all passed, any failures as P0/P1 findings, and put the exact ' +
      'test command you ran in the "command" field.',
  )
  return parts.join(' ')
}

// Diff probe for the proportional-round predicate (#82 / #45). Deliberately
// asks for MEASUREMENT and nothing else: the four eligibility predicates are
// applied by isDeltaEligible() in JS. Anything malformed or missing fails closed
// to a full round, so a lazy or confused probe costs a round, never a review.
function diffProbePrompt(artifact, cap) {
  return [
    `Mechanical measurement only. Do NOT review, judge, fix or comment on anything at ${artifact}.`,
    '',
    `1. Run: git diff -U0 -- ${artifact}`,
    `   If ${artifact} is untracked, git is unavailable, or the command fails, return`,
    '   {"artifact_lines": 0, "touched": [], "truncated": true} and stop.',
    `2. Count the total number of lines in the CURRENT ${artifact} → artifact_lines.`,
    '3. For EVERY added (+) or removed (-) line in that diff, emit one entry in "touched":',
    '   - "text": the line content with the leading + or - removed, otherwise verbatim.',
    `   - "section": the exact text of the nearest preceding line in the CURRENT ${artifact}`,
    '     that starts with "#" (a markdown heading), or "" if there is none.',
    `4. If there are more than ${cap} such lines, stop counting and return`,
    `   {"artifact_lines": <count>, "touched": [], "truncated": true}.`,
    '',
    'Report facts. Make no assessment of size, risk, or importance — that is decided elsewhere.',
  ].join('\n')
}

// Single-verifier prompt for the proportional verification round (OPT-009): a
// clean round + no fixer edits buys a cheap "still clean?" check instead of a
// full N-reviewer fan-out. ANY real finding it returns re-opens the full loop.
function verifierPrompt(artifact, requirements, priorFindings, priorResolutions, historyPath, ledger) {
  const parts = [
    'You are a single verification reviewer. The prior round found no blocking issues and nothing has been',
    'changed since. Confirm the artifact is still clean.',
    '',
    `Read the artifact at: ${artifact}`,
    `Read the requirements at: ${requirements}`,
  ]
  if (historyPath) {
    parts.push('', `The prior round summary is in a file you MUST Read: ${historyPath}`)
  } else {
    if (priorFindings.length) parts.push('', '## Prior Round Findings', '', formatFindings(priorFindings))
    if (priorResolutions.length) {
      const lines = priorResolutions.map((r) => `- ${r.finding_id ?? '?'}: ${r.status ?? '?'} -- ${r.description ?? ''}`)
      parts.push('', '## Trivial Resolutions Applied', '', lines.join('\n'))
    }
  }
  const ledgerBlockV = renderLedger(ledger ?? [])
  if (ledgerBlockV) parts.push('', ledgerBlockV)
  parts.push(
    '',
    '## Instructions',
    '',
    'Spot-check that the artifact is unchanged from the clean prior round and that any trivial resolutions',
    'above actually landed. Report a finding ONLY if you find a REAL issue (any severity); if everything is',
    'fine, return an empty findings array.',
    '',
    REVIEWER_OUTPUT_INSTRUCTIONS.replace('{reviewer_name}', 'verifier'),
  )
  return parts.join('\n')
}

// Render the prior-round findings + resolutions as the history-file body (OPT-015).
function renderHistory(findings, resolutions, ledger) {
  const parts = []
  // LEDGER first: the settled cross-round record the reviewer must not re-open.
  const ledgerBlock = renderLedger(ledger ?? [])
  if (ledgerBlock) parts.push(ledgerBlock, '')
  parts.push('## Prior Round Findings', '', formatFindings(findings))
  if (resolutions.length) {
    const resLines = []
    for (const res of resolutions) {
      resLines.push(`- **${res.finding_id ?? '?'}**: ${res.status ?? '?'} -- ${res.description ?? ''}`)
      if (res.evidence) resLines.push(`  Evidence: ${res.evidence}`)
    }
    parts.push('', '## Fix Resolutions Applied', '', resLines.join('\n'))
  }
  return parts.join('\n')
}

// Prompt a cheap agent to persist the round's history verbatim to a file so the
// next round's reviewers Read it by path instead of receiving it embedded.
function historyWriterPrompt(historyPath, findings, resolutions, ledger) {
  return [
    `Write the following markdown VERBATIM to the file at ${historyPath} (create it, or overwrite if it`,
    'exists). Do NOT edit, summarize, reword, or reformat — write it exactly as given. Output nothing else.',
    '',
    '--- BEGIN CONTENT ---',
    renderHistory(findings, resolutions, ledger),
    '--- END CONTENT ---',
  ].join('\n')
}

// Best-effort cleanup of the temporary history files at loop end (OPT-015).
function cleanupPrompt(paths) {
  return [
    'Delete these temporary review-history files if they exist (they are scratch state from the review loop):',
    ...paths.map((p) => `  ${p}`),
    '',
    'Return wrote:true once done. If a file is already gone, that is fine.',
  ].join('\n')
}

// Map the additive camelCase `complexity` config ({files, toolTypes, contextFraction})
// onto the snake_case shape resolveReviewerModel/escalates consume. Tolerant of
// either casing; this is plumbing only — the escalation policy lives in adjudication.mjs.
function toResolverComplexity(complexity) {
  if (!complexity) return null
  return {
    file_count: complexity.file_count ?? complexity.files ?? 1,
    tool_types: complexity.tool_types ?? complexity.toolTypes ?? 0,
    context_fraction: complexity.context_fraction ?? complexity.contextFraction ?? 0,
  }
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
// The convergence loop — the canonical state machine (formerly loop-driver.py).
// ---------------------------------------------------------------------------

/**
 * Run the review→synthesize→gate→fix loop for a single artifact.
 *
 * @param config { artifact, requirements, team, threshold, rounds, maxRounds, complexity, skipTests }
 *   rounds===1 → single-pass diagnose (qreview: min 1 round, no fixer beyond it);
 *   otherwise until-converged (qloop: min 2 rounds, in-place fixer per round).
 *   complexity — optional {files, toolTypes, contextFraction}; routed through
 *     resolveReviewerModel so complexity can escalate reviewers that the team
 *     object marks escalation_eligible (OPT-002). team-selector.py resolves the
 *     canonical tier + opus cap into agentDef.model; this is a forwarding pass.
 *   skipTests — optional; skip the per-round test gate for artifacts with no
 *     executable test surface, e.g. documents (OPT-007).
 *   maxGateRounds — optional (default 2); how many CONSECUTIVE rounds the
 *     deterministic test/lint gate may claim on its own before a full reviewer
 *     round runs anyway, so gate thrash can never starve review (#82).
 *   deltaCaps — optional {maxChangedLines, maxChangedFraction}; overrides for the
 *     proportional-round size predicate.
 *   divergence — optional {window, warmup}; overrides for the divergence halt.
 *   maxInvalidRounds — optional (default maxRounds); how many rounds that did
 *     not count toward the budget (below reviewer quorum, #81) the loop tolerates
 *     before escalating on the ENVIRONMENT rather than on the artifact.
 *   validateRound — optional (report) => boolean; returning false marks a round
 *     INVALID, so it spends no round budget and fills no divergence window. This
 *     is the seam the reviewer-quorum gate (#81 / this repo #43) plugs into; the
 *     report it receives already carries reviewers_requested/reviewers_returned.
 *     Default: every round is valid.
 * @param ctx { agent, parallel, phase, log } — the injected Workflow globals.
 * @returns { outcome, rounds, budget, final_findings, final_counts, history }
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
    complexity = null,
    skipTests = false,
    maxGateRounds = 2,
    deltaCaps = null,
    divergence = null,
    maxInvalidRounds: maxInvalidRoundsArg,
    validateRound = null,
  } = config

  const singleRound = rounds === 1
  const minRounds = singleRound ? 1 : 2
  const maxRounds = Math.max(maxRoundsArg ?? (singleRound ? 1 : 5), minRounds)
  // The round BUDGET is spent in valid rounds only (#81), so the `for` bound must
  // be an absolute ceiling or a reviewer panel that keeps dying would spin forever.
  const maxInvalidRounds = Math.max(0, maxInvalidRoundsArg ?? maxRounds)
  const hardCap = maxRounds + maxInvalidRounds
  const deltaOpts = { ...DELTA_DEFAULTS, ...(deltaCaps || {}) }
  const now = () => (typeof Date !== 'undefined' && Date.now ? Date.now() : 0)
  const startedAt = now()

  if (!artifact || !requirements) throw new Error('runLoop requires artifact and requirements')
  if (team.length < 2 && !singleRound) throw new Error('runLoop requires at least 2 reviewers (team)')

  const resolverComplexity = toResolverComplexity(complexity)

  const roundReports = []
  let priorFindings = []
  let priorResolutions = []
  let prevP0P1 = null
  let prevAllTitles = new Set() // for recurrence-based significance promotion
  let outcome = null

  // SMOKE-008: union of every file the fixer/spot-fixer declares it edited across all
  // rounds, surfaced in the return so the pipeline commit step can capture them.
  const editedFiles = new Set()
  // State for the waste-cutting optimizations.
  let fixerEverRan = false        // full re-review stays mandatory after any fix (OPT-009)
  let lastRoundConverged = false  // was the previous round clean (0 significant)?
  let proportionalUsed = false    // the no-fixer-yet shortcut (OPT-009) fires at most once
  let lastRoundKind = null        // 'full' | 'delta' | 'gate' — the bookend rule reads this
  let deltaEligibility = null     // isDeltaEligible() verdict on the LAST fix batch (#82/#45)
  let consecutiveGateRounds = 0   // bound on deterministic-gate-only rounds (#82)
  let carriedTestCommand = null   // reuse round 1's test command in later rounds (OPT-007)
  let historyPath = null          // round r-1's externalized history file, if written (OPT-015)
  const historyPaths = []         // every history file written, for end-of-loop cleanup
  // LEDGER: cumulative record of findings whose resolution is SETTLED (fixed and
  // then verified by a later round). Carried into EVERY subsequent round's
  // prompts so round 5's reviewer still knows what round 1 decided. `pending`
  // holds the round just fixed — it can only be adjudicated once the NEXT round's
  // findings prove the fix held, so admission always lags one round.
  let ledger = []
  let pendingAdjudication = null

  // OPT-015: persist a round's findings+resolutions to a file the NEXT round's
  // reviewers Read by path (constant-size prompts) instead of embedding it in
  // every reviewer prompt. Returns the path on success, or null → prompts embed
  // as before (zero information loss). Skipped when there is nothing to record.
  async function maybeWriteHistory(round, hFindings, hResolutions) {
    if (!hFindings.length && !hResolutions.length && !ledger.length) return null
    const path = `${artifact}.review-r${round}.md`
    const res = await agent(historyWriterPrompt(path, hFindings, hResolutions, ledger), {
      label: `history:r${round}`, phase: `Round ${round}`, model: 'haiku', schema: WROTE_SCHEMA,
    })
    if (res && res.wrote === true) {
      historyPaths.push(path)
      return path
    }
    return null
  }

  // Fan out N clean-context reviewers, each on its resolved model (OPT-002).
  // team-selector.py already bakes the per-reviewer tier (with its domain-score
  // gates + opus-seat cap) into agentDef.model; we route through
  // resolveReviewerModel forwarding whatever escalation/high-stakes flags the
  // team object carries (default false → identity for the canonical path, so the
  // Python cap is never overridden), which also enforces tiering for a caller
  // that supplies flags but skipped team-selector.
  //
  // Returns the ATTESTATION (#81): the per-reviewer findings lists PLUS how many
  // reviewers were asked for versus how many came back, and why each missing one
  // is missing. The counts are recorded on every round report
  // and in the verdict; deciding that a shortfall makes the round INVALID is the
  // quorum gate (#81 / this repo #43), which flips `valid` on the round report.
  // Everything downstream of that flag — the round budget and the divergence
  // window — already ignores invalid rounds.
  //
  // Each reviewer is SETTLED rather than awaited raw: one that dies
  // environmentally (expired auth, killed session, timeout) must be recorded WITH
  // its reason — never allowed to abort the whole fan-out, and never dropped by a
  // filter that leaves it indistinguishable from a reviewer who found nothing.
  async function settleReviewer(name, thunk) {
    try {
      return { name, ok: true, value: await thunk() }
    } catch (e) {
      return { name, ok: false, reason: e && e.message ? e.message : String(e) }
    }
  }

  async function fanOutReviewers(r, testSummary) {
    const reviews = await parallel(
      team.map((agentDef) => () =>
        settleReviewer(agentDef.name, () =>
          agent(reviewerPrompt(agentDef, r, artifact, requirements, testSummary, priorFindings, priorResolutions, historyPath, ledger), {
            label: `review:${agentDef.name}:r${r}`,
            phase: `Round ${r}`,
            model: resolveReviewerModel(agentDef, resolverComplexity, {
              escalationEligible: agentDef.escalation_eligible ?? agentDef.escalationEligible ?? false,
              highStakes: agentDef.high_stakes ?? agentDef.highStakes ?? false,
            }) || agentDef.model || 'sonnet',
            schema: FINDINGS_SCHEMA,
          }),
        ),
      ),
    )
    return attestReviewers(reviews)
  }

  for (let r = 1; r <= hardCap; r++) {
    const roundStartedAt = now()
    let reviewersRequested = 0
    let reviewersReturned = 0

    // ── Is this round PROPORTIONAL (one cheap verifier) or FULL (every lens)? ──
    //
    // Two routes in, both bounded by the same bookend rule: round 1 is always
    // full, and a delta round may only follow a FULL one — never another delta.
    // That keeps drift to at most one small, contract-safe batch behind the last
    // whole-artifact read.
    //
    //   (a) OPT-009 — the prior round was clean and the fixer has never run, so
    //       nothing has changed since a full read. Fires at most once.
    //   (b) #82/#45 — the prior FULL round's fix batch was measured by the diff
    //       probe and judged small, P0-free and contract-safe by isDeltaEligible.
    const bookendOk = r > 1 && lastRoundKind === 'full'
    const opt009 = !proportionalUsed && lastRoundConverged && !fixerEverRan
    const deltaOk = deltaEligibility?.eligible === true
    const proportional = bookendOk && (opt009 || deltaOk)

    // Why this round is (or is not) proportional — recorded on the round report so
    // an operator can see the predicate's verdict, not just its consequence.
    const deltaReasonForRound = proportional
      ? (opt009 ? 'no-fixer-yet' : 'eligible')
      : !bookendOk && r > 1
        ? `bookend:${lastRoundKind ?? 'none'}`
        : deltaEligibility?.reason ?? (r === 1 ? 'round-1-always-full' : 'no-probe')

    let reviewerLists
    let testSummary = 'No test results available.'
    let roundKind = proportional ? 'delta' : 'full'
    // #81: this round's reviewer attestation. A deterministic gate round asks for
    // no reviewers at all, so it starts as an empty — and therefore satisfied — panel.
    let attestation = attestReviewers([])

    if (proportional) {
      if (opt009) proportionalUsed = true
      deltaEligibility = null
      phase(`Verify (round ${r})`)
      // The single verifier IS this round's whole panel, so it is attested like any
      // other: a dead verifier makes a dead round, not a clean one (#81).
      const verifier = await settleReviewer('verifier', () =>
        agent(
          verifierPrompt(artifact, requirements, priorFindings, priorResolutions, historyPath, ledger),
          { label: `verify:r${r}`, phase: `Round ${r}`, model: 'sonnet', schema: FINDINGS_SCHEMA },
        ),
      )
      attestation = attestReviewers([verifier])
      reviewersRequested = attestation.requested
      reviewersReturned = attestation.returned
      reviewerLists = attestation.lists
      testSummary = 'Proportional verification round — no test gate run.'
    } else {
      deltaEligibility = null

      // ── DETERMINISTIC BEFORE AGENTIC (#82) ──────────────────────────────────
      // The test/lint gate runs FIRST, and when it fails it claims the round on
      // its own: a defect a test or a linter can name must never cost a reviewer
      // round. A failing gate means the artifact is provably broken, so paying
      // four lenses to read the whole thing is waste — the fixer already has a
      // complete, mechanically-derived work list. Bounded by maxGateRounds so a
      // permanently-red suite cannot starve review of the rest of the artifact.
      let test = null
      if (!skipTests) {
        phase(r === 1 ? 'Gate' : `Gate (round ${r})`)
        test = await agent(testGatePrompt(artifact, r, carriedTestCommand), {
          label: `tests:r${r}`, phase: `Round ${r}`, model: 'haiku', schema: TEST_SCHEMA,
        })
        testSummary = test?.summary ?? 'No test results available.'
        if (test?.command) carriedTestCommand = test.command
      } else {
        testSummary = 'Tests skipped for this artifact (no executable test surface).'
      }

      const gateFailures = test?.failures?.length ? test.failures : []
      // NEVER in single-round mode: qreview promises one clean-context diagnose
      // pass, and a caller who asked for lenses must get lenses even when the
      // suite is red. The short-circuit only pays off across rounds anyway — it
      // trades this round's fan-out for a cheaper one after the fix lands, and a
      // single-round run has no next round to spend it on.
      const gateMayClaimRound = !singleRound && consecutiveGateRounds < maxGateRounds
      if (gateFailures.length && gateMayClaimRound) {
        consecutiveGateRounds += 1
        roundKind = 'gate'
        reviewerLists = [gateFailures]
        log(
          `Round ${r}: deterministic gate failed with ${gateFailures.length} finding(s) — fixing those first, ` +
            `no reviewer fan-out this round (gate round ${consecutiveGateRounds}/${maxGateRounds}).`,
        )
      } else {
        if (gateFailures.length) {
          log(`Round ${r}: gate still failing after ${consecutiveGateRounds} gate round(s) — running the full review anyway.`)
        }
        consecutiveGateRounds = 0
        attestation = await fanOutReviewers(r, testSummary)
        reviewerLists = attestation.lists
        reviewersRequested = attestation.requested
        reviewersReturned = attestation.returned
        if (gateFailures.length) reviewerLists.push(gateFailures)
      }
    }

    // ── THE QUORUM GATE (#81 / this repo #43) ───────────────────────────────
    // The panel that was asked for did not report, so this round is not evidence
    // ABOUT THE ARTIFACT and nothing downstream may act on it: no synthesis, no
    // ledger adjudication (a fix "not re-raised" by reviewers who never ran is not
    // settled), no spot-fixer on the survivors' partial list, and above all no
    // convergence. The round is recorded INVALID with every failure reason, spends
    // no round budget, and the loop re-runs. A panel that keeps dying escalates on
    // the ENVIRONMENT rather than certifying the artifact.
    if (!attestation.quorumMet) {
      const shortfall = describeReviewerShortfall(r, attestation)
      log(shortfall)
      roundReports.push({
        round: r, findings: [], counts: countBySeverity([]), significant: 0, trivial: 0,
        newP0P1: 0, dropped: 0, converged: false, message: shortfall, proportional,
        kind: roundKind, valid: false, ms: Math.max(0, now() - roundStartedAt),
        reviewers_requested: attestation.requested, reviewers_returned: attestation.returned,
        reviewers_quorum: attestation.quorum, reviewers_missing: attestation.missing,
        delta_reason: deltaReasonForRound,
      })
      const spentInvalid = summarizeBudget(roundReports, { maxRounds })
      if (maxInvalidRounds > 0 && spentInvalid.invalidRounds >= maxInvalidRounds) {
        outcome = {
          status: 'escalated',
          reason:
            `Environment: ${spentInvalid.invalidRounds} of ${spentInvalid.roundsRun} rounds did not produce a ` +
            `valid reviewer panel (limit ${maxInvalidRounds}). This run proves nothing about the artifact — ` +
            `fix the environment and re-run. ${shortfall}`,
          reviewers: {
            requested: attestation.requested, returned: attestation.returned,
            quorum: attestation.quorum, missing: attestation.missing,
          },
          unresolved: [],
          round: r,
        }
        break
      }
      // A dead panel leaves the artifact unread, so nothing carries forward: the
      // next round is a FULL re-read, never a delta off state nobody verified.
      lastRoundKind = 'invalid'
      lastRoundConverged = false
      deltaEligibility = null
      continue
    }

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

    // LEDGER: this round's findings are the verdict on last round's fixes. A fix
    // this round did NOT re-raise is settled and joins the ledger; one that
    // recurred stays out, so the ledger never claims a live bug is closed.
    if (pendingAdjudication) {
      ledger = mergeLedger(
        ledger,
        adjudicateRound({ ...pendingAdjudication, nextRoundFindings: findings }),
      )
      pendingAdjudication = null
    }

    // Split into significant (full fix-loop) and trivial (spot-fix). P0/P1 are
    // always significant; a recurring or reviewer-flagged P2/P3 is too.
    const significant = findings.filter((f) => isSignificant(f, prevAllTitles, flaggedTitles))
    const trivial = findings.filter((f) => !isSignificant(f, prevAllTitles, flaggedTitles))

    // The LOOP gate is significant-only: trivial P2/P3 don't block convergence
    // (they're spot-fixed opportunistically). P0/P1 stay 0-total-hard because
    // they're always significant.
    const { converged, message } = checkConvergence(significant, threshold)
    // A proportional verification round that surfaced ANY finding re-opens the
    // full loop — it must not converge on the spot even if the finding is trivial.
    const proportionalReopen = proportional && findings.length > 0
    const newP0P1 = findings.filter(
      (f) => (f.severity === 'P0' || f.severity === 'P1') && !prevP0P1?.has(normTitle(f)),
    ).length
    // `valid` is the quorum gate's flag (#81): a round whose reviewer panel did
    // not reach quorum is not evidence, so it must not spend budget or fill the
    // divergence window. Every round is valid unless `validateRound` says
    // otherwise — that hook is the seam the quorum gate plugs into.
    const report = {
      round: r, findings, counts, significant: significant.length, trivial: trivial.length,
      newP0P1, dropped: dropped.length, converged, message, proportional,
      kind: roundKind, valid: true, ms: Math.max(0, now() - roundStartedAt),
      reviewers_requested: reviewersRequested, reviewers_returned: reviewersReturned,
      reviewers_quorum: attestation.quorum, reviewers_missing: attestation.missing,
      delta_reason: deltaReasonForRound,
    }
    // The hook may only ADD invalidation: a round that failed the quorum gate never
    // reaches here, so no caller can vote a dead panel back into evidence.
    if (validateRound) report.valid = validateRound(report) !== false
    roundReports.push(report)
    // The round's position in the budget rides on every line, so a run that is
    // heading for 19 rounds is visible in `/workflows` WHILE it happens (#82).
    const spentSoFar = summarizeBudget(roundReports, { maxRounds })
    log(
      `Round ${r}/${maxRounds} [${roundKind}${report.valid ? '' : ', INVALID'}]: ${findings.length} findings ` +
        `(P0=${counts.P0} P1=${counts.P1} P2=${counts.P2} P3=${counts.P3}; ${significant.length} significant / ` +
        `${trivial.length} trivial, ${newP0P1} new P0/P1) — budget ${spentSoFar.validRounds}/${maxRounds} valid ` +
        `(${spentSoFar.fullRounds} full, ${spentSoFar.deltaRounds} delta, ${spentSoFar.gateRounds} gate) — ${message}`,
    )

    // Spot-fix trivial nits cheaply (Haiku) + a light spot-check. Opportunistic,
    // non-blocking, doesn't reset the convergence counter.
    // REQ-42-1: single-round (/qreview) mode is DIAGNOSE-ONLY. The skill promises
    // "/qreview never edits the artifact", so no spot-fixer and no spot-check may
    // touch the tree there — trivial findings are still counted and reported.
    let trivialResolutions = []
    if (trivial.length && !singleRound) {
      const spot = await agent(spotFixerPrompt(artifact, requirements, trivial), {
        label: `spotfix:r${r}`, phase: `Round ${r}`, model: 'haiku', schema: RESOLUTIONS_SCHEMA,
      })
      trivialResolutions = spot?.resolutions || []
      for (const p of spot?.edited_files || []) editedFiles.add(p)
      if (trivialResolutions.length) {
        const check = await agent(spotCheckPrompt(artifact, trivialResolutions), {
          label: `spotcheck:r${r}`, phase: `Round ${r}`, model: 'haiku', schema: SPOTCHECK_SCHEMA,
        })
        if (check && check.all_applied === false && check.not_applied?.length) {
          log(`Round ${r}: spot-check flagged ${check.not_applied.length} trivial fix(es) not applied: ${check.not_applied.join(', ')}`)
          // LEDGER: the spot-check is affirmative evidence the fix did NOT land,
          // so drop those resolutions — never ledger a fix as settled while
          // holding proof it is still open. They stay in the round's log above.
          const rejected = new Set(check.not_applied.map(String))
          trivialResolutions = trivialResolutions.filter((res) => !rejected.has(String(res.finding_id ?? '')))
        }
      }
    }

    // Converged (no significant findings) AND past the minimum-rounds floor → done.
    // A re-opening proportional round never converges here (any finding re-opens).
    // The min-rounds floor counts VALID rounds, not attempts (#81): converging off
    // one valid round because the other attempt had a dead panel is the same false
    // green by another route.
    if (converged && spentSoFar.validRounds >= minRounds && !proportionalReopen) {
      outcome = {
        status: 'converged',
        // The count rides IN the verdict, so a human reading only this line sees
        // what the execution table shows: who was asked, and who answered.
        message: `${message} (${renderAttestation(attestation)})`,
        round: r,
        reviewers: {
          requested: attestation.requested, returned: attestation.returned,
          quorum: attestation.quorum, missing: attestation.missing,
        },
      }
      break
    }

    const unresolvedNow = () => findings.filter((f) => f.severity === 'P0' || f.severity === 'P1')

    // DIVERGENCE (#82) — the loop is not approaching a fixed point, so more rounds
    // will not converge it. Stuck detection cannot see this shape: it matches an
    // IDENTICAL P0/P1 title set, and a diverging run surfaces genuinely NEW P0s
    // every round (pm-816-intake-0903 ran 19 rounds and ~5M tokens that way before
    // a human halted it). Checked BEFORE the fixer, so a diverging round does not
    // also pay for a fix batch nobody will re-review.
    const div = detectDivergence(roundReports, divergence || {})
    if (div.diverging) {
      log(`Round ${r}: ${div.reason}`)
      outcome = { status: 'escalated', reason: div.reason, divergence: div, unresolved: unresolvedNow(), round: r }
      break
    }

    // Out of BUDGET → escalate with the unresolved P0/P1s. The budget is spent in
    // VALID rounds, so rounds lost to a dead reviewer panel (#81) do not consume
    // it — but they are capped separately, and running out of THOSE escalates on
    // the environment rather than blaming the artifact.
    const spent = summarizeBudget(roundReports, { maxRounds })
    if (spent.validRounds >= maxRounds) {
      outcome = { status: 'escalated', reason: `Max rounds (${maxRounds}) reached without convergence. ${message}.`, unresolved: unresolvedNow(), round: r }
      break
    }
    if (spent.invalidRounds >= maxInvalidRounds && maxInvalidRounds > 0) {
      outcome = {
        status: 'escalated',
        reason:
          `Environment: ${spent.invalidRounds} of ${spent.roundsRun} rounds did not produce a valid reviewer panel ` +
          `(limit ${maxInvalidRounds}). This run proves nothing about the artifact — fix the environment and re-run.`,
        unresolved: unresolvedNow(),
        round: r,
      }
      break
    }

    // Significant cleared (below the floor, or a proportional round that surfaced
    // only trivial findings) → advance to re-review WITHOUT running the fixer.
    if (converged) {
      pendingAdjudication = { round: r, findings, resolutions: trivialResolutions }
      historyPath = await maybeWriteHistory(r, findings, trivialResolutions)
      priorFindings = findings
      priorResolutions = trivialResolutions
      prevP0P1 = p0p1Titles(findings)
      prevAllTitles = new Set(findings.map(normTitle))
      lastRoundConverged = true
      lastRoundKind = roundKind
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
    fixerEverRan = true
    const resolutions = fix?.resolutions || []
    for (const p of fix?.edited_files || []) editedFiles.add(p)

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

    // PROPORTIONAL ROUNDS (#82 / this repo #45) — does this fix batch buy a cheap
    // delta round, or must the next round re-read the whole artifact with every
    // lens? Only a FULL round's batch can, so a gate or delta round never even
    // pays for the probe; neither does a batch that fixed a P0, which is
    // disqualified by predicate 1 before any agent is spawned. That ordering is
    // the deterministic-before-agentic rule applied to the engine's own spending.
    const p0FixedCount = significant.filter((f) => f.severity === 'P0').length
    if (roundKind !== 'full' || p0FixedCount > 0) {
      deltaEligibility = { eligible: false, reason: roundKind !== 'full' ? `bookend:${roundKind}` : 'p0-in-batch' }
    } else {
      const probe = await agent(diffProbePrompt(artifact, deltaOpts.maxChangedLines), {
        label: `diff:r${r}`, phase: `Round ${r}`, model: 'haiku', schema: DIFF_SCHEMA,
      })
      deltaEligibility = isDeltaEligible(
        probe
          ? { p0FixedCount, artifactLines: probe.artifact_lines, touched: probe.touched, truncated: probe.truncated }
          : null,
        deltaOpts,
      )
      log(
        `Round ${r}: fix batch is ${deltaEligibility.eligible ? 'DELTA-ELIGIBLE' : 'not delta-eligible'} ` +
          `(${deltaEligibility.reason}; ${deltaEligibility.changedLines ?? '?'} changed line(s)) — round ${r + 1} is a ` +
          `${deltaEligibility.eligible ? 'single delta verifier' : 'full review'}.`,
      )
    }

    const combinedResolutions = [...resolutions, ...trivialResolutions]
    pendingAdjudication = { round: r, findings, resolutions: combinedResolutions }
    historyPath = await maybeWriteHistory(r, findings, combinedResolutions)
    priorFindings = findings
    priorResolutions = combinedResolutions
    prevP0P1 = curP0P1
    prevAllTitles = new Set(findings.map(normTitle))
    lastRoundConverged = false
    lastRoundKind = roundKind
  }

  // A run that falls out of the loop with no verdict would read downstream as
  // neither converged nor escalated — silence that the pipeline's halt check waves
  // through. Every exit gets a verdict (#81).
  if (!outcome) {
    const spentFinal = summarizeBudget(roundReports, { maxRounds })
    const lastReport = roundReports[roundReports.length - 1] || {}
    outcome = {
      status: 'escalated',
      reason:
        `Hard cap (${hardCap} rounds) reached without a verdict: ${spentFinal.validRounds} valid round(s), ` +
        `${spentFinal.invalidRounds} invalid (below reviewer quorum). This run proves nothing about the artifact.` +
        (lastReport.message ? ` Last round: ${lastReport.message}` : ''),
      unresolved: (lastReport.findings || []).filter((f) => f.severity === 'P0' || f.severity === 'P1'),
      round: roundReports.length,
    }
  }

  // Best-effort cleanup of the temporary history files (OPT-015).
  if (historyPaths.length) {
    await agent(cleanupPrompt(historyPaths), {
      label: 'cleanup', phase: 'Cleanup', model: 'haiku', schema: WROTE_SCHEMA,
    })
  }

  // A run that ends while a round is still pending has no LATER round to confirm
  // its fixes. When the loop CONVERGED, the final clean round is itself that
  // confirmation, so those fixes are settled; on an escalation they are not.
  if (pendingAdjudication && outcome?.status === 'converged') {
    ledger = mergeLedger(ledger, adjudicateRound({ ...pendingAdjudication, nextRoundFindings: [] }))
    pendingAdjudication = null
  }

  const last = roundReports[roundReports.length - 1] || {}
  // COST IN THE VERDICT (#82) — rounds by kind and wall-clock travel WITH the
  // outcome, so a 19-round run is obvious to whoever reads the result rather than
  // only to whoever re-reads the workflow JSON afterwards. Token cost is priced
  // by tools/scorecard.py, which has the per-agent usage this sandbox cannot see.
  const budget = {
    ...summarizeBudget(roundReports, { maxRounds }),
    maxInvalidRounds,
    hardCap,
    wallClockMs: Math.max(0, now() - startedAt),
  }
  return {
    outcome,
    rounds: roundReports.length,
    budget,
    edited_files: [...editedFiles].sort(),
    ledger,
    final_findings: last.findings || [],
    final_counts: last.counts || countBySeverity([]),
    history: roundReports.map((rr) => ({
      round: rr.round, counts: rr.counts, significant: rr.significant, trivial: rr.trivial,
      newP0P1: rr.newP0P1, converged: rr.converged, message: rr.message,
      kind: rr.kind, valid: rr.valid, ms: rr.ms, delta_reason: rr.delta_reason,
      reviewers_requested: rr.reviewers_requested, reviewers_returned: rr.reviewers_returned,
      reviewers_quorum: rr.reviewers_quorum, reviewers_missing: rr.reviewers_missing,
    })),
  }
}
