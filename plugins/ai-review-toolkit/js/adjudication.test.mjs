// Golden-fixture parity tests — the JS<->Python drift lock (JS side).
//
// Step 2 of the ultracode refactor: the JS port must reproduce the committed
// adjudication corpus that step 1 froze from the Python oracle. This test loads
// the SAME fixtures/adjudication.json the Python test asserts against, so any
// divergence on either side fails CI.
//
// Plain node — no framework. Run: node --test plugins/ai-review-toolkit/js/
//
// See ~/.claude/plans/ai-review-ultracode-refactor.md (step 2).

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  validateFinding,
  deduplicateFindings,
  countBySeverity,
  checkConvergence,
  synthesizeFindings,
  resolveReviewerModel,
  checkFixCompleteness,
} from "./adjudication.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "..", "tools", "fixtures", "adjudication.json");

const corpus = JSON.parse(readFileSync(FIXTURES, "utf8"));

// Mirror of gen-golden-fixtures.py::run_case — one function, JSON-shaped result.
function runCase(fn, inp) {
  switch (fn) {
    case "validate_finding": {
      const { valid, errors } = validateFinding(inp.finding);
      return { valid, errors };
    }
    case "deduplicate_findings":
      return deduplicateFindings(inp.findings);
    case "count_by_severity":
      return countBySeverity(inp.findings);
    case "check_convergence": {
      const { converged, message } = checkConvergence(
        inp.findings,
        inp.threshold ?? 0,
        inp.min_findings ?? 0,
      );
      return { converged, message };
    }
    case "synthesize_findings": {
      const dropped = [];
      const findings = synthesizeFindings(inp.reviewer_results, dropped);
      return { findings, dropped };
    }
    case "resolve_reviewer_model":
      return resolveReviewerModel(inp.agent, inp.complexity);
    case "check_fix_completeness": {
      const { complete, missing } = checkFixCompleteness(
        inp.findings,
        inp.resolutions,
      );
      return { complete, missing };
    }
    default:
      throw new Error(`unknown function: ${fn}`);
  }
}

const TARGET_FUNCTIONS = [
  "validate_finding",
  "deduplicate_findings",
  "count_by_severity",
  "check_convergence",
  "synthesize_findings",
  "resolve_reviewer_model",
  "check_fix_completeness",
];

test("corpus contains every target function group", () => {
  for (const fn of TARGET_FUNCTIONS) {
    assert.ok(corpus.cases[fn], `corpus missing function group: ${fn}`);
    assert.ok(
      corpus.cases[fn].length >= 3,
      `${fn}: expected >=3 cases for coverage`,
    );
  }
});

for (const [fn, cases] of Object.entries(corpus.cases)) {
  for (const c of cases) {
    test(`${fn}/${c.name} reproduces the Python oracle`, () => {
      assert.deepStrictEqual(runCase(fn, c.input), c.expected);
    });
  }
}
