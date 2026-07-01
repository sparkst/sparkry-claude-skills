// Reviewer / fixer prompt construction — JS port of the loop-driver builders.
//
// Part of the hot-loop but NOT in the adjudication corpus: these assemble the
// prompt strings the review-loop.workflow.js (step 4) will send to reviewer and
// fixer subagents. The workflow reads the artifact/requirements files itself and
// passes their content in, so these stay pure (no I/O). Output matches
// loop-driver.py / finding-parser.py byte-for-byte; locked by prompts.test.mjs
// and tools/test_prompt_parity.py against tools/fixtures/prompts.json.

// finding-parser.py::REVIEWER_OUTPUT_INSTRUCTIONS ({reviewer_name} is templated).
const REVIEWER_OUTPUT_INSTRUCTIONS = `Output your findings as a JSON array. Each finding must have these fields:
- id: string matching pattern P[0-3]-NNN (e.g., P0-001, P1-002)
- severity: one of P0, P1, P2, P3
- title: concise description of the issue
- requirement: which requirement this relates to
- finding: detailed description of the problem
- recommendation: how to fix it
- source: "{reviewer_name}"
- evidence: file path and line number if applicable

Severity guide:
- P0: Blocks shipping (correctness, security, data loss, requirement violation)
- P1: Must fix before v1 (quality, error handling, incomplete coverage)
- P2: Should fix (code smell, suboptimal pattern, minor UX, doc gap)
- P3: Nice to have (style, optional optimization, cosmetic)

Output ONLY the JSON array. No other text.`;

// ---------------------------------------------------------------------------
// Finding formatting (finding-parser.py::format_findings, markdown branch)
// ---------------------------------------------------------------------------

/** Render findings as the markdown block used inside reviewer/fixer prompts. */
export function formatFindings(findings) {
  if (!findings.length) {
    return "No findings.";
  }

  const lines = [];
  for (const f of findings) {
    const fid = f.id ?? "?";
    const title = f.title ?? "Untitled";
    const severity = f.severity ?? "?";
    const requirement = f.requirement ?? "";
    const findingText = f.finding ?? "";
    const recommendation = f.recommendation ?? "";

    const evidenceRaw = f.evidence ?? "";
    let evidence;
    if (Array.isArray(evidenceRaw)) {
      evidence = evidenceRaw;
    } else if (evidenceRaw) {
      evidence = [evidenceRaw];
    } else {
      evidence = [];
    }
    const sources = "sources" in f ? f.sources : [f.source ?? ""];

    lines.push(`### ${fid}: ${title}`);
    lines.push(`**Severity:** ${severity}`);
    lines.push(`**Requirement:** ${requirement}`);
    lines.push(`**Finding:** ${findingText}`);
    lines.push(`**Recommendation:** ${recommendation}`);

    if (evidence.length) {
      const evidenceStr = evidence.filter((e) => e).map((e) => String(e)).join(", ");
      if (evidenceStr) {
        lines.push(`**Evidence:** ${evidenceStr}`);
      }
    }

    if (Array.isArray(sources) && sources.length) {
      lines.push(`**Sources:** ${sources.map((s) => String(s)).join(", ")}`);
    } else if (sources) {
      lines.push(`**Sources:** ${sources}`);
    }

    lines.push("");
  }

  return lines.join("\n").replace(/\s+$/, "");
}

// ---------------------------------------------------------------------------
// Reviewer prompt (loop-driver.py::get_reviewer_prompt)
// ---------------------------------------------------------------------------

/**
 * Build a reviewer prompt. The workflow supplies file content directly.
 * Round 2+ (roundNum > 1) appends prior findings, applied resolutions, and
 * verification instructions.
 */
export function buildReviewerPrompt(agent, {
  artifactContent,
  requirementsContent,
  testSummary = "No test results available.",
  roundNum = 1,
  priorFindings = [],
  priorResolutions = [],
} = {}) {
  const reviewerName = agent.name;
  const reviewLens = agent.review_lens;

  const parts = [
    `You are a ${reviewerName} reviewing an artifact.`,
    "",
    `Your review lens: ${reviewLens}`,
    "",
    "## Artifact",
    "",
    artifactContent,
    "",
    "## Requirements",
    "",
    requirementsContent,
    "",
    "## Test Results",
    "",
    testSummary,
  ];

  if (roundNum > 1) {
    if (priorFindings.length) {
      parts.push(
        "",
        `## Prior Round Findings (Round ${roundNum - 1})`,
        "",
        formatFindings(priorFindings),
      );
    }

    if (priorResolutions.length) {
      const resLines = [];
      for (const res of priorResolutions) {
        const fid = res.finding_id ?? "?";
        const status = res.status ?? "?";
        const desc = res.description ?? "";
        const evidence = res.evidence ?? "";
        resLines.push(`- **${fid}**: ${status} -- ${desc}`);
        if (evidence) {
          resLines.push(`  Evidence: ${evidence}`);
        }
      }
      parts.push("", "## Fix Resolutions Applied", "", resLines.join("\n"));
    }

    parts.push(
      "",
      "## Verification Instructions",
      "",
      `The artifact content above is the POST-FIX version (after round ${roundNum - 1} fixes). ` +
        "For each fix resolution listed above, navigate to the cited evidence location " +
        "in the artifact and verify the fix is correct. Also check for NEW issues " +
        "introduced by the fixes — regressions, broken logic, incomplete changes.",
    );
  }

  const outputInstructions = REVIEWER_OUTPUT_INSTRUCTIONS.replace(
    "{reviewer_name}",
    reviewerName,
  );
  parts.push(
    "",
    "## Instructions",
    "",
    `Review the artifact against the requirements through your lens of ${reviewLens}.`,
    "",
    outputInstructions,
  );

  return parts.join("\n");
}

// ---------------------------------------------------------------------------
// Fixer prompt (loop-driver.py::get_fixer_prompt)
// ---------------------------------------------------------------------------

/** Build the fixer prompt listing every finding that must be resolved. */
export function buildFixerPrompt({
  artifactContent,
  requirementsContent,
  testSummary = "",
  findings = [],
} = {}) {
  const findingsText = formatFindings(findings);

  return `You are a fixer agent. Your job is to fix ALL findings from the review.

## Artifact

${artifactContent}

## Requirements

${requirementsContent}

## Test Results

${testSummary}

## Findings to Fix (ALL must be addressed)

${findingsText}

## Instructions

Fix EVERY finding listed above. Every single one, regardless of severity (P0 through P3).

For each finding, produce a resolution with these fields:
- finding_id: the ID of the finding being resolved (e.g., P0-001)
- status: MUST be "FIXED" with evidence of the fix. No WONTFIX, DEFERRED, or OUT_OF_SCOPE.
- evidence: what changed and where (file:line for code, section:quote for content)
- description: brief explanation of the fix

If a finding is genuinely unfixable (requires external dependency, architectural constraint, or user decision), set status to "ESCALATED" with justification.

Output a JSON array of resolution objects. No other text.`;
}
