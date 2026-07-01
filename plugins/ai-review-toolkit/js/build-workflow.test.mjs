// Freshness lock for the generated workflow script.
//
// review-loop.workflow.js is generated from review-loop.template.js +
// adjudication.mjs + prompts.mjs. This asserts the committed file is in sync
// with its sources, so a change to the adjudication library that wasn't
// re-inlined fails CI (mirrors the golden-fixture drift locks).

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));

test("review-loop.workflow.js is in sync with its sources", () => {
  // Exits 0 when fresh, non-zero (throwing) when stale.
  const out = execFileSync("node", [join(HERE, "build-workflow.mjs"), "--check"], {
    encoding: "utf8",
  });
  assert.match(out, /in sync/);
});

test("generated workflow parses as valid JS", () => {
  // `node --check` throws on a syntax error.
  execFileSync("node", ["--check", join(HERE, "review-loop.workflow.js")]);
});

test("no injection-marker residue leaked into the generated script", () => {
  // Guards the class of bug where trailing text on the @@INLINE@@ line leaks
  // out as bare code (node --check is too lenient to always catch it; the
  // Workflow engine's parser is stricter).
  const generated = readFileSync(join(HERE, "review-loop.workflow.js"), "utf8");
  assert.ok(!generated.includes("@@INLINE@@"), "injection marker survived");
  assert.ok(
    !generated.includes("build-workflow.mjs replaces this whole line"),
    "marker-line trailing text leaked into output",
  );
});
