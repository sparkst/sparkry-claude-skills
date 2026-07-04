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
  resolveReviewerModel,
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

// ---------------------------------------------------------------------------
// Prompt assembly for the sandboxed script.
//
// The script cannot read files, so reviewer/fixer prompts reference the
// artifact/requirements by PATH and instruct the agent to Read them. Prior-round
// findings ARE held in memory, so they are embedded via formatFindings().
// ---------------------------------------------------------------------------

function reviewerPrompt(agentDef, roundNum, artifact, requirements, testSummary, priorFindings, priorResolutions, historyPath) {
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

// Single-verifier prompt for the proportional verification round (OPT-009): a
// clean round + no fixer edits buys a cheap "still clean?" check instead of a
// full N-reviewer fan-out. ANY real finding it returns re-opens the full loop.
function verifierPrompt(artifact, requirements, priorFindings, priorResolutions, historyPath) {
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
function renderHistory(findings, resolutions) {
  const parts = ['## Prior Round Findings', '', formatFindings(findings)]
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
function historyWriterPrompt(historyPath, findings, resolutions) {
  return [
    `Write the following markdown VERBATIM to the file at ${historyPath} (create it, or overwrite if it`,
    'exists). Do NOT edit, summarize, reword, or reformat — write it exactly as given. Output nothing else.',
    '',
    '--- BEGIN CONTENT ---',
    renderHistory(findings, resolutions),
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
    complexity = null,
    skipTests = false,
  } = config

  const singleRound = rounds === 1
  const minRounds = singleRound ? 1 : 2
  const maxRounds = Math.max(maxRoundsArg ?? (singleRound ? 1 : 5), minRounds)

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
  let proportionalUsed = false    // the cheap verification round fires at most once
  let carriedTestCommand = null   // reuse round 1's test command in later rounds (OPT-007)
  let historyPath = null          // round r-1's externalized history file, if written (OPT-015)
  const historyPaths = []         // every history file written, for end-of-loop cleanup

  // OPT-015: persist a round's findings+resolutions to a file the NEXT round's
  // reviewers Read by path (constant-size prompts) instead of embedding it in
  // every reviewer prompt. Returns the path on success, or null → prompts embed
  // as before (zero information loss). Skipped when there is nothing to record.
  async function maybeWriteHistory(round, hFindings, hResolutions) {
    if (!hFindings.length && !hResolutions.length) return null
    const path = `${artifact}.review-r${round}.md`
    const res = await agent(historyWriterPrompt(path, hFindings, hResolutions), {
      label: `history:r${round}`, phase: `Round ${round}`, model: 'haiku', schema: WROTE_SCHEMA,
    })
    if (res && res.wrote === true) {
      historyPaths.push(path)
      return path
    }
    return null
  }

  for (let r = 1; r <= maxRounds; r++) {
    // OPT-009: a clean prior round with no fixer edits buys only a single cheap
    // verifier this round (still honoring the min-2-rounds floor), not a full
    // fan-out. Fires at most once; any finding it surfaces re-opens the full loop.
    const proportional = !proportionalUsed && r > 1 && lastRoundConverged && !fixerEverRan

    let reviewerLists
    let testSummary = 'No test results available.'

    if (proportional) {
      proportionalUsed = true
      phase(`Verify (round ${r})`)
      const verifier = await agent(
        verifierPrompt(artifact, requirements, priorFindings, priorResolutions, historyPath),
        { label: `verify:r${r}`, phase: `Round ${r}`, model: 'sonnet', schema: FINDINGS_SCHEMA },
      )
      reviewerLists = [verifier?.findings || []]
      testSummary = 'Proportional verification round — no test gate run.'
    } else {
      phase(r === 1 ? 'Review' : `Review (round ${r})`)

      // Deterministic test gate — an agent runs the project's tests, returns a
      // summary. Skipped for artifacts with no executable test surface (OPT-007).
      // Mechanical exit-code work → haiku, same as the TDD red/green gates (OPT-010).
      let test = null
      if (!skipTests) {
        test = await agent(testGatePrompt(artifact, r, carriedTestCommand), {
          label: `tests:r${r}`, phase: `Round ${r}`, model: 'haiku', schema: TEST_SCHEMA,
        })
        testSummary = test?.summary ?? 'No test results available.'
        if (test?.command) carriedTestCommand = test.command
      } else {
        testSummary = 'Tests skipped for this artifact (no executable test surface).'
      }

      // Fan out N clean-context reviewers, each on its resolved model (OPT-002).
      // team-selector.py already bakes the per-reviewer tier (with its domain-score
      // gates + opus-seat cap) into agentDef.model; we route through
      // resolveReviewerModel forwarding whatever escalation/high-stakes flags the
      // team object carries (default false → identity for the canonical path, so
      // the Python cap is never overridden), which also enforces tiering for a
      // caller that supplies flags but skipped team-selector.
      const reviews = await parallel(
        team.map((agentDef) => () =>
          agent(reviewerPrompt(agentDef, r, artifact, requirements, testSummary, priorFindings, priorResolutions, historyPath), {
            label: `review:${agentDef.name}:r${r}`,
            phase: `Round ${r}`,
            model: resolveReviewerModel(agentDef, resolverComplexity, {
              escalationEligible: agentDef.escalation_eligible ?? agentDef.escalationEligible ?? false,
              highStakes: agentDef.high_stakes ?? agentDef.highStakes ?? false,
            }) || agentDef.model || 'sonnet',
            schema: FINDINGS_SCHEMA,
          }),
        ),
      )

      reviewerLists = reviews.filter(Boolean).map((x) => x.findings || [])
      if (test?.failures?.length) reviewerLists.push(test.failures)
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
    roundReports.push({ round: r, findings, counts, significant: significant.length, trivial: trivial.length, newP0P1, dropped: dropped.length, converged, message, proportional })
    log(`Round ${r}: ${findings.length} findings (P0=${counts.P0} P1=${counts.P1} P2=${counts.P2} P3=${counts.P3}; ${significant.length} significant / ${trivial.length} trivial, ${newP0P1} new P0/P1) — ${message}`)

    // Spot-fix trivial nits cheaply (Haiku) + a light spot-check. Opportunistic,
    // non-blocking, doesn't reset the convergence counter.
    let trivialResolutions = []
    if (trivial.length) {
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
        }
      }
    }

    // Converged (no significant findings) AND past the minimum-rounds floor → done.
    // A re-opening proportional round never converges here (any finding re-opens).
    if (converged && r >= minRounds && !proportionalReopen) {
      outcome = { status: 'converged', message, round: r }
      break
    }

    // Out of rounds → escalate with the unresolved P0/P1s.
    if (r >= maxRounds) {
      const unresolved = findings.filter((f) => f.severity === 'P0' || f.severity === 'P1')
      outcome = { status: 'escalated', reason: `Max rounds (${maxRounds}) reached without convergence. ${message}.`, unresolved, round: r }
      break
    }

    // Significant cleared (below the floor, or a proportional round that surfaced
    // only trivial findings) → advance to re-review WITHOUT running the fixer.
    if (converged) {
      historyPath = await maybeWriteHistory(r, findings, trivialResolutions)
      priorFindings = findings
      priorResolutions = trivialResolutions
      prevP0P1 = p0p1Titles(findings)
      prevAllTitles = new Set(findings.map(normTitle))
      lastRoundConverged = true
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

    const combinedResolutions = [...resolutions, ...trivialResolutions]
    historyPath = await maybeWriteHistory(r, findings, combinedResolutions)
    priorFindings = findings
    priorResolutions = combinedResolutions
    prevP0P1 = curP0P1
    prevAllTitles = new Set(findings.map(normTitle))
    lastRoundConverged = false
  }

  // Best-effort cleanup of the temporary history files (OPT-015).
  if (historyPaths.length) {
    await agent(cleanupPrompt(historyPaths), {
      label: 'cleanup', phase: 'Cleanup', model: 'haiku', schema: WROTE_SCHEMA,
    })
  }

  const last = roundReports[roundReports.length - 1] || {}
  return {
    outcome,
    rounds: roundReports.length,
    edited_files: [...editedFiles].sort(),
    final_findings: last.findings || [],
    final_counts: last.counts || countBySeverity([]),
    history: roundReports.map((rr) => ({
      round: rr.round, counts: rr.counts, significant: rr.significant, trivial: rr.trivial,
      newP0P1: rr.newP0P1, converged: rr.converged, message: rr.message,
    })),
  }
}
