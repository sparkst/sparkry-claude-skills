// Golden prompt-construction parity (JS side).
//
// Asserts js/prompts.mjs reproduces the Python oracle's reviewer/fixer prompt
// strings exactly, against the same tools/fixtures/prompts.json that
// tools/test_prompt_parity.py locks on the Python side.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { formatFindings, buildReviewerPrompt, buildFixerPrompt } from "./prompts.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "..", "tools", "fixtures", "prompts.json");
const corpus = JSON.parse(readFileSync(FIXTURES, "utf8"));

function runCase(builder, inp) {
  switch (builder) {
    case "format_findings":
      return formatFindings(inp.findings);
    case "reviewer_prompt":
      return buildReviewerPrompt(inp.agent, {
        artifactContent: inp.artifact_content,
        requirementsContent: inp.requirements_content,
        testSummary: inp.test_summary,
        roundNum: inp.round_num,
        priorFindings: inp.prior_findings,
        priorResolutions: inp.prior_resolutions,
      });
    case "fixer_prompt":
      return buildFixerPrompt({
        artifactContent: inp.artifact_content,
        requirementsContent: inp.requirements_content,
        testSummary: inp.test_summary,
        findings: inp.findings,
      });
    default:
      throw new Error(`unknown builder: ${builder}`);
  }
}

for (const [builder, cases] of Object.entries(corpus.cases)) {
  for (const c of cases) {
    test(`${builder}/${c.name} reproduces the Python oracle`, () => {
      assert.strictEqual(runCase(builder, c.input), c.expected);
    });
  }
}
