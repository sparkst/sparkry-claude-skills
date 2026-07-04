import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildTestWriterPrompt,
  buildImplementerPrompt,
  sliceBranch,
  sliceTestsRef,
  worktreeSetup,
  worktreeCleanup,
  isSafeSliceId,
} from "./tdd-prompts.mjs";

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

// ── SMOKE-001: shared named worktree per slice (not per-agent isolation) ────

test("sliceBranch / sliceTestsRef derive deterministic per-slice refs", () => {
  assert.equal(sliceBranch("S-001"), "pipeline/S-001");
  assert.equal(sliceTestsRef("S-001"), "pipeline-tests/S-001");
});

test("worktreeSetup(create) creates a named sibling worktree + branch off HEAD", () => {
  const p = worktreeSetup(SLICE, { create: true });
  // sibling of the repo (outside the tracked tree, not a nested dir)
  assert.match(p, /ROOT="\$\(git rev-parse --show-toplevel\)"/);
  assert.match(p, /SLICE_WT="\$\{ROOT\}\.pipeline-wt\/S-001"/);
  assert.match(p, /SLICE_BRANCH="pipeline\/S-001"/);
  assert.match(p, /git worktree add "\$SLICE_WT" -b "\$SLICE_BRANCH" HEAD/);
  assert.match(p, /cd "\$SLICE_WT"/);
});

test("worktreeSetup(non-create) enters the existing worktree, never re-creates it", () => {
  const p = worktreeSetup(SLICE, { create: false });
  assert.match(p, /cd "\$SLICE_WT"/);
  assert.ok(!p.includes("git worktree add"), "gate/implementer must not create the worktree");
});

test("worktreeSetup forbids off-script git history manipulation (SMOKE-007c containment)", () => {
  // The S-005 breach: a slice agent merged sibling branches + resurrected a dangling
  // commit to green its tests. The prompt must forbid that in both modes.
  for (const create of [true, false]) {
    const p = worktreeSetup(SLICE, { create });
    assert.match(p, /do NOT|never/i);
    assert.match(p, /merge/i);
    assert.match(p, /cherry-pick/i);
    assert.match(p, /rebase|reset/i);
  }
});

test("worktreeCleanup removes the worktree, branch, and frozen-tests tag", () => {
  const p = worktreeCleanup(SLICE);
  assert.match(p, /git worktree remove --force "\$\{ROOT\}\.pipeline-wt\/S-001"/);
  assert.match(p, /git branch -D "pipeline\/S-001"/);
  assert.match(p, /git tag -d "pipeline-tests\/S-001"/);
});

test("test-writer prompt: creates the worktree, commits+tags tests, returns the absolute path", () => {
  const p = buildTestWriterPrompt(SLICE, { requirementsPath: "REQUIREMENTS.md", designPath: "DESIGN.md" });
  // no per-agent harness isolation — an explicit shared worktree instead
  assert.match(p, /git worktree add "\$SLICE_WT" -b "\$SLICE_BRANCH" HEAD/);
  assert.match(p, /git commit/);
  assert.match(p, /git tag -f "pipeline-tests\/S-001"/);
  assert.match(p, /worktree/i); // asked to report the absolute worktree path
  // still the two-context contract: writes tests, not impl
  assert.match(p, /Every test MUST fail now/);
  assert.ok(!p.includes("src/widgets/create.ts"), "test-writer must not be told to touch impl files");
});

test("implementer prompt: works in the passed absolute worktree and commits impl", () => {
  const p = buildImplementerPrompt(SLICE, {
    designPath: "DESIGN.md",
    redSummary: "3 failing",
    worktreePath: "/repo.pipeline-wt/S-001",
  });
  assert.match(p, /\/repo\.pipeline-wt\/S-001/); // the literal absolute path is embedded
  assert.match(p, /git commit/);
  assert.match(p, /READ-ONLY/);
  assert.match(p, /may NOT edit, delete, skip, rename, or weaken any test/);
  assert.match(p, /3 failing/);
});

test("worktree helpers tolerate a bare slice", () => {
  assert.doesNotThrow(() => worktreeSetup({ id: "S-000" }, {}));
  assert.doesNotThrow(() => worktreeCleanup({ id: "S-000" }));
  assert.doesNotThrow(() => buildImplementerPrompt({ id: "S-000" }, {}));
});

test("isSafeSliceId: only ids safe to embed in shell worktree/branch/tag names pass", () => {
  for (const ok of ["S-000", "S-001", "kernel.core", "slice_42", "A-b_c.d"]) {
    assert.equal(isSafeSliceId(ok), true, `${ok} should be safe`);
  }
  for (const bad of ["", "S 001", "S;rm -rf /", "$(whoami)", "a/b", "a`b`", "a&b", "slice*", undefined, null, 42]) {
    assert.equal(isSafeSliceId(bad), false, `${JSON.stringify(bad)} must be rejected`);
  }
});
