// Freshness lock for the generated workflow script.
//
// review-loop.workflow.js is generated from review-loop.template.js +
// adjudication.mjs + prompts.mjs. This asserts the committed file is in sync
// with its sources, so a change to the adjudication library that wasn't
// re-inlined fails CI (mirrors the golden-fixture drift locks).

import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
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
