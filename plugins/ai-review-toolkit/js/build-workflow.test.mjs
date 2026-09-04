// Freshness lock for the generated workflow scripts.
//
// Each *.workflow.js is generated from its *.template.js + the inlined libraries
// (see TARGETS in build-workflow.mjs). This asserts every committed file is in
// sync with its sources, so a change to an inlined library that wasn't re-inlined
// fails CI (mirrors the golden-fixture drift locks).

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const HERE = dirname(fileURLToPath(import.meta.url));
const WORKFLOWS = ["review-loop.workflow.js", "pipeline-auto.workflow.js"];

test("all generated workflows are in sync with their sources", () => {
  // Exits 0 when every target is fresh, non-zero (throwing) when any is stale.
  const out = execFileSync("node", [join(HERE, "build-workflow.mjs"), "--check"], {
    encoding: "utf8",
  });
  assert.match(out, /in sync/);
});

for (const wf of WORKFLOWS) {
  test(`${wf} parses as valid JS`, () => {
    // `node --check` throws on a syntax error (the Workflow sandbox parser is
    // stricter still — a live planOnly smoke is the ultimate gate).
    execFileSync("node", ["--check", join(HERE, wf)]);
  });

  test(`${wf}: no injection-marker residue leaked into the generated script`, () => {
    const generated = readFileSync(join(HERE, wf), "utf8");
    assert.ok(!generated.includes("@@INLINE@@"), "injection marker survived");
    assert.ok(
      !generated.includes("build-workflow.mjs replaces this whole line"),
      "marker-line trailing text leaked into output",
    );
  });
}

test("REQ-NOW-03: generated review workflow resolves when the runtime clock throws", async () => {
  const dir = mkdtempSync(join(tmpdir(), "review-workflow-now-"));
  try {
    const artifact = join(dir, "artifact.txt");
    const requirements = join(dir, "requirements.txt");
    writeFileSync(artifact, "tiny artifact\n");
    writeFileSync(requirements, "REQ-1: remain reviewable\n");

    // Workflow accepts exported helpers in its script body. A classic vm.Script
    // does not, so remove only the export modifier before wrapping the same body.
    const source = readFileSync(join(HERE, "review-loop.workflow.js"), "utf8")
      .replace(/^export\s+/gm, "");
    const context = vm.createContext({
      args: {
        artifact,
        requirements,
        team: [{ name: "reviewer", model: "sonnet", review_lens: "correctness" }],
        rounds: 1,
        skipTests: true,
      },
      Date: class WorkflowDate extends Date {
        static now() {
          throw new Error("Date.now() / new Date() are unavailable in workflow scripts (breaks resume)");
        }
      },
      agent: async () => ({ findings: [] }),
      parallel: (thunks) => Promise.all(thunks.map((thunk) => thunk())),
      pipeline: async (fn) => fn(),
      phase: () => {},
      log: () => {},
      budget: {},
    });
    const result = await new vm.Script(`(async () => {\n${source}\n})()`).runInContext(context);
    assert.equal(typeof result.outcome, "object");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
