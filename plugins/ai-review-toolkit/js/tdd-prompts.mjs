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

/**
 * Context A. The test-writer sees requirements + design + the public contract,
 * and writes ONLY the slice's test files. It never sees or writes implementation.
 */
export function buildTestWriterPrompt(slice, { requirementsPath, designPath } = {}) {
  return [
    `You are a TEST-WRITER for slice ${slice.id}: ${slice.summary ?? ''}`.trim(),
    '',
    'Author FAILING tests that pin this slice\'s contract BEFORE any implementation exists.',
    'The tests you write are the frozen contract the implementer must satisfy — they cannot change them.',
    '',
    `Requirements to discharge: ${(slice.req_ids ?? []).join(', ') || '(none listed)'} — read ${requirementsPath}`,
    `Design: read ${designPath}`,
    `Public contract (the stub both contexts share): ${slice.public_contract ?? '(none)'}`,
    '',
    `Write ONLY these test files: ${(slice.test_files ?? []).join(', ') || '(none)'}`,
    'Do NOT write, read, or scaffold any implementation. Do NOT touch files outside the test files above.',
    '',
    '## Rules',
    '- Every test MUST fail now (no implementation exists yet) — a test that passes pre-implementation is wrong.',
    '- Assert REAL behavior tied to the requirements/contract. No vacuous, always-true, or empty tests.',
    '- Cite the REQ-ID each test discharges.',
    '',
    'Return a short summary of the tests written and the exact test-file paths.',
  ].join('\n')
}

/**
 * Context B. The implementer sees the public contract + the tests READ-ONLY and
 * the red report, and writes ONLY the slice's implementation files. A tamper-check
 * enforces it never mutates a test.
 */
export function buildImplementerPrompt(slice, { designPath, redSummary } = {}) {
  return [
    `You are an IMPLEMENTER for slice ${slice.id}: ${slice.summary ?? ''}`.trim(),
    '',
    'Make the FAILING tests pass (green) by writing ONLY the implementation. Do not change the approach the',
    'tests encode — satisfy them.',
    '',
    `Design: read ${designPath}`,
    `Public contract: ${slice.public_contract ?? '(none)'}`,
    '',
    `The tests are FROZEN. Read them READ-ONLY at: ${(slice.test_files ?? []).join(', ') || '(none)'}`,
    'You may NOT edit, delete, skip, rename, or weaken any test, and you may NOT add new test files.',
    'A tamper-check (git-diff scope + test-file hashes) enforces this — a violation reverts your work.',
    '',
    `Write ONLY these implementation files: ${(slice.files ?? []).join(', ') || '(none)'}`,
    '',
    `## Current red state`,
    '',
    redSummary || '(tests are failing pre-implementation)',
    '',
    'Make every test pass without modifying the tests. Return what you implemented and where (file:line).',
  ].join('\n')
}
