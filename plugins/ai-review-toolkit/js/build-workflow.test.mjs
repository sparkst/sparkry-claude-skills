// Freshness lock for the generated workflow scripts.
//
// Each *.workflow.js is generated from its *.template.js + the inlined libraries
// (see TARGETS in build-workflow.mjs). This asserts every committed file is in
// sync with its sources, so a change to an inlined library that wasn't re-inlined
// fails CI (mirrors the golden-fixture drift locks).

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

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
