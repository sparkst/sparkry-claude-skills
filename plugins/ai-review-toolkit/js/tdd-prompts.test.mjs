import { test } from "node:test";
import assert from "node:assert/strict";
import { buildTestWriterPrompt, buildImplementerPrompt } from "./tdd-prompts.mjs";

const SLICE = {
  id: "S-001",
  summary: "POST /widgets -> 201",
  files: ["src/widgets/create.ts"],
  test_files: ["src/widgets/create.spec.ts"],
  req_ids: ["REQ-101"],
  public_contract: "createWidget(input): Widget",
};

test("test-writer prompt: writes only test files, never impl, must fail first", () => {
  const p = buildTestWriterPrompt(SLICE, { requirementsPath: "REQUIREMENTS.md", designPath: "DESIGN.md" });
  assert.match(p, /TEST-WRITER for slice S-001/);
  assert.match(p, /src\/widgets\/create\.spec\.ts/);
  assert.match(p, /REQ-101/);
  assert.match(p, /createWidget\(input\): Widget/);
  assert.match(p, /Every test MUST fail now/);
  assert.ok(!p.includes("src/widgets/create.ts"), "test-writer must not be told to touch impl files");
});

test("implementer prompt: writes only impl, tests are frozen + tamper-checked", () => {
  const p = buildImplementerPrompt(SLICE, { designPath: "DESIGN.md", redSummary: "3 failing" });
  assert.match(p, /IMPLEMENTER for slice S-001/);
  assert.match(p, /src\/widgets\/create\.ts/);
  assert.match(p, /READ-ONLY/);
  assert.match(p, /may NOT edit, delete, skip, rename, or weaken any test/);
  assert.match(p, /tamper-check/);
  assert.match(p, /3 failing/);
});

test("builders tolerate missing optional fields", () => {
  const bare = { id: "S-000" };
  assert.doesNotThrow(() => buildTestWriterPrompt(bare, {}));
  assert.doesNotThrow(() => buildImplementerPrompt(bare, {}));
});
