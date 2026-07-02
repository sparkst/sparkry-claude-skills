import { test } from "node:test";
import assert from "node:assert/strict";
import { buildConflictResolverPrompt, buildIntegrationTestWriterPrompt } from "./integrator-prompts.mjs";

const SLICE = {
  id: "S-101",
  summary: "widget listing",
  files: ["src/widgets/list.ts"],
  test_files: ["src/widgets/list.spec.ts"],
  public_contract: "listWidgets(): Widget[]",
};

// ── conflict-resolver ────────────────────────────────────────────────────

test("conflict-resolver prompt: fixes the merge regression touching only impl files", () => {
  const p = buildConflictResolverPrompt(SLICE, {
    suiteFailure: "3 failing in src/widgets/list.spec.ts",
    conflicts: ["src/widgets/list.ts"],
  });
  assert.match(p, /CONFLICT-RESOLVER for slice S-101/);
  assert.match(p, /src\/widgets\/list\.ts/);
  assert.match(p, /3 failing/);
  // tests remain frozen + tamper-checked at integration time
  assert.match(p, /READ-ONLY|frozen/i);
  assert.match(p, /tamper-check/);
  assert.match(p, /may NOT edit, delete, skip, rename, or weaken any test/);
});

test("conflict-resolver prompt: never instructs touching a test file", () => {
  const p = buildConflictResolverPrompt(SLICE, { suiteFailure: "x" });
  assert.ok(!p.includes("Write ONLY these test"), "resolver must not be told to write tests");
});

test("conflict-resolver prompt: tolerates missing optional fields", () => {
  assert.doesNotThrow(() => buildConflictResolverPrompt({ id: "S-000" }, {}));
});

// ── integration test-writer (cross-slice seams) ──────────────────────────

test("integration test-writer prompt: authors cross-slice seam tests from a fresh context", () => {
  const p = buildIntegrationTestWriterPrompt([SLICE, { id: "S-102", public_contract: "createWidget(): Widget" }], {
    designPath: "DESIGN.md",
    requirementsPath: "REQUIREMENTS.md",
  });
  assert.match(p, /INTEGRATION TEST-WRITER/);
  assert.match(p, /seam|integration|interaction/i);
  assert.match(p, /S-101/);
  assert.match(p, /S-102/);
  assert.match(p, /listWidgets\(\): Widget\[\]/);
  assert.match(p, /DESIGN\.md/);
  assert.match(p, /REQUIREMENTS\.md/);
});

test("integration test-writer prompt: tolerates an empty slice list and missing paths", () => {
  assert.doesNotThrow(() => buildIntegrationTestWriterPrompt([], {}));
});
