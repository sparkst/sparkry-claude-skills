// Two-context TDD prompt builders (Phase B of /qpipeline auto).
//
// The whole point is a STRUCTURAL separation between two agent contexts so the
// implementer cannot weaken the tests to pass:
//   - Context A (test-writer) authors the failing tests — the frozen contract.
//   - Context B (implementer) makes them pass, seeing the tests READ-ONLY.
// Enforcement is deterministic (red/green gates + tamper-check in tdd-harness.py);
// these prompts state the contract in words. Pure string builders (no I/O) — the
// agents Read the real files by path. Inlined into pipeline-auto.workflow.js in
// Phase E.
//
// SMOKE-001 fix: the four per-slice agents (test-writer / red-gate / implementer /
// green-gate) MUST share ONE tree — otherwise the red-gate never sees the tests the
// test-writer wrote and every slice fails RED. Instead of per-agent harness
// `isolation:'worktree'` (which hands each agent a fresh anonymous worktree), each
// slice gets ONE dedicated NAMED git worktree, created by the test-writer and reused
// by the rest. It lives OUTSIDE the repo tree (sibling `${ROOT}.pipeline-wt/<id>`),
// so it never pollutes the user's tracked tree nor gets picked up by in-repo test
// discovery. The test-writer commits + tags the frozen tests; the implementer commits
// impl; the green-gate tamper-checks by diffing COMMITS (`pipeline-tests/<id>..HEAD`),
// not dirty state; the integrator merges the `pipeline/<id>` BRANCHES in merge-order.

// Slice ids flow verbatim into shell commands (worktree dirs, branch + tag names),
// so they must be constrained to a shell-safe charset. Anything else is rejected
// loudly rather than interpolated into bash.
const SAFE_SLICE_ID = /^[A-Za-z0-9._-]+$/;

/** True iff `id` is safe to embed in a worktree path / branch / tag name. */
export function isSafeSliceId(id) {
  return typeof id === "string" && SAFE_SLICE_ID.test(id);
}

/** Per-slice branch that carries the slice's tests + impl commits. */
export function sliceBranch(sliceId) {
  return `pipeline/${sliceId}`;
}

/** Tag marking the FROZEN tests commit (the tamper-check's baseline). */
export function sliceTestsRef(sliceId) {
  return `pipeline-tests/${sliceId}`;
}

/**
 * Bash preamble resolving + entering the slice's dedicated worktree. `create`
 * (test-writer only) adds the worktree + branch off the current feature-branch HEAD;
 * the gate/implementer agents reuse it (create:false). The worktree is a SIBLING of
 * the repo dir (`${ROOT}.pipeline-wt/<id>`) — outside the working tree on purpose.
 */
export function worktreeSetup(slice, { create = false } = {}) {
  const id = slice?.id ?? "";
  const lines = [
    "This slice builds in its OWN dedicated git worktree, shared by every agent on the slice.",
    'Run these EXACT commands first, then do ALL work inside "$SLICE_WT" (agent cwd may reset',
    'between bash calls, so prefix every later command with `cd "$SLICE_WT" &&` and write files',
    "using their absolute path under $SLICE_WT):",
    "```bash",
    'ROOT="$(git rev-parse --show-toplevel)"',
    `SLICE_WT="\${ROOT}.pipeline-wt/${id}"`,
    `SLICE_BRANCH="pipeline/${id}"`,
  ];
  if (create) {
    lines.push(
      "# create the dedicated worktree + slice branch off the current HEAD (idempotent)",
      'git worktree add "$SLICE_WT" -b "$SLICE_BRANCH" HEAD 2>/dev/null || true',
    );
  }
  lines.push('cd "$SLICE_WT"', "```");
  return lines.join("\n");
}

/** Commit + tag the frozen tests on the slice branch (test-writer). */
export function commitTestsInstruction(slice) {
  const id = slice?.id ?? "";
  return [
    "COMMIT the tests on the slice branch and TAG the frozen baseline:",
    "```bash",
    'cd "$SLICE_WT" && git add -A',
    `cd "$SLICE_WT" && git commit -m "test(${id}): failing tests pinning the slice contract"`,
    `cd "$SLICE_WT" && git tag -f "pipeline-tests/${id}" HEAD`,
    "```",
    "The tag marks the FROZEN tests — nothing under it may change afterwards.",
  ].join("\n");
}

/** Commit the implementation on the slice branch (implementer). */
export function commitImplInstruction(slice) {
  const id = slice?.id ?? "";
  return [
    "COMMIT your implementation on the slice branch (do NOT amend, move, or delete the tests commit/tag):",
    "```bash",
    'cd "$SLICE_WT" && git add -A',
    `cd "$SLICE_WT" && git commit -m "feat(${id}): implement the slice"`,
    "```",
  ].join("\n");
}

/** Remove the slice worktree, branch, and tests tag (on merge or on failure). */
export function worktreeCleanup(slice) {
  const id = slice?.id ?? "";
  return [
    "```bash",
    'ROOT="$(git rev-parse --show-toplevel)"; cd "$ROOT"',
    `git worktree remove --force "\${ROOT}.pipeline-wt/${id}" 2>/dev/null || true`,
    `git branch -D "pipeline/${id}" 2>/dev/null || true`,
    `git tag -d "pipeline-tests/${id}" 2>/dev/null || true`,
    "git worktree prune 2>/dev/null || true",
    "```",
  ].join("\n");
}

/**
 * Context A. The test-writer sees requirements + design + the public contract,
 * and writes ONLY the slice's test files. It never sees or writes implementation.
 */
export function buildTestWriterPrompt(slice, { requirementsPath, designPath } = {}) {
  return [
    `You are a TEST-WRITER for slice ${slice.id}: ${slice.summary ?? ''}`.trim(),
    '',
    worktreeSetup(slice, { create: true }),
    '',
    'Author FAILING tests that pin this slice\'s contract BEFORE any implementation exists.',
    'The tests you write are the frozen contract the implementer must satisfy — they cannot change them.',
    '',
    `Requirements to discharge: ${(slice.req_ids ?? []).join(', ') || '(none listed)'} — read ${requirementsPath}`,
    `Design: read ${designPath}`,
    `Public contract (the stub both contexts share): ${slice.public_contract ?? '(none)'}`,
    '',
    `Write ONLY these test files, as ABSOLUTE paths under $SLICE_WT (e.g. $SLICE_WT/<path>): ${(slice.test_files ?? []).join(', ') || '(none)'}`,
    'Do NOT write, read, or scaffold any implementation. Do NOT touch files outside the test files above.',
    '',
    '## Rules',
    '- Every test MUST fail now (no implementation exists yet) — a test that passes pre-implementation is wrong.',
    '- Assert REAL behavior tied to the requirements/contract. No vacuous, always-true, or empty tests.',
    '- Cite the REQ-ID each test discharges.',
    '',
    commitTestsInstruction(slice),
    '',
    'Return {worktree, branch, tests_committed}: the ABSOLUTE value of $SLICE_WT, the branch',
    `("pipeline/${slice.id}"), and whether the tests were committed — plus a short summary + the test-file paths.`,
  ].join('\n')
}

/**
 * Context B. The implementer sees the public contract + the tests READ-ONLY and
 * the red report, and writes ONLY the slice's implementation files. A tamper-check
 * enforces it never mutates a test.
 */
export function buildImplementerPrompt(slice, { designPath, redSummary, worktreePath } = {}) {
  const wt = worktreePath || '$SLICE_WT';
  return [
    `You are an IMPLEMENTER for slice ${slice.id}: ${slice.summary ?? ''}`.trim(),
    '',
    `All work happens in the slice's dedicated worktree at: ${wt}`,
    `\`cd "${wt}"\` first and prefix every command with it (agent cwd may reset between bash calls);`,
    'write your implementation files using their ABSOLUTE path under that directory.',
    '',
    'Make the FAILING tests pass (green) by writing ONLY the implementation. Do not change the approach the',
    'tests encode — satisfy them.',
    '',
    `Design: read ${designPath}`,
    `Public contract: ${slice.public_contract ?? '(none)'}`,
    '',
    `The tests are FROZEN. Read them READ-ONLY at: ${(slice.test_files ?? []).join(', ') || '(none)'}`,
    'You may NOT edit, delete, skip, rename, or weaken any test, and you may NOT add new test files.',
    'A tamper-check (git-diff scope of your commit + the frozen-tests tag) enforces this — a violation reverts your work.',
    '',
    `Write ONLY these implementation files: ${(slice.files ?? []).join(', ') || '(none)'}`,
    '',
    `## Current red state`,
    '',
    redSummary || '(tests are failing pre-implementation)',
    '',
    commitImplInstruction(slice),
    '',
    'Make every test pass without modifying the tests. Return what you implemented and where (file:line).',
  ].join('\n')
}
