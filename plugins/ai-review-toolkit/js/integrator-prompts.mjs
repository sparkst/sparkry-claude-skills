// Integrator prompt builders (Phase C of /qpipeline auto).
//
// Two agent prompts used by the SERIALIZED integrator after the per-slice TDD
// waves merge back:
//   - the CONFLICT-RESOLVER makes the full suite green again after a merge, editing
//     ONLY impl files (tests stay frozen + tamper-checked, exactly as during
//     implementation).
//   - the INTEGRATION TEST-WRITER, from a fresh context, authors cross-slice SEAM
//     tests once all slices are merged green.
// Pure string builders (no I/O) — the agents Read the real files by path. Inlined
// into pipeline-auto.workflow.js in Phase E, alongside tdd-prompts.mjs.

/**
 * The full suite regressed after merging this slice's worktree. Fix it by editing
 * ONLY the slice's implementation — the tests are the frozen contract and a
 * tamper-check reverts any test edit.
 */
export function buildConflictResolverPrompt(slice, { suiteFailure, conflicts } = {}) {
  const conflictLine = (conflicts ?? []).length
    ? `Merge conflicts were reported in: ${conflicts.join(', ')}.`
    : 'The merge applied cleanly but the full suite regressed.';
  return [
    `You are a CONFLICT-RESOLVER for slice ${slice.id}: ${slice.summary ?? ''}`.trim(),
    '',
    'This slice was merged into the integration branch and the FULL test suite is now failing.',
    'Make the whole suite green again by editing ONLY this slice\'s implementation. Do not change the',
    'behavior any test encodes — reconcile your implementation with the rest of the integrated code.',
    '',
    conflictLine,
    'Design: read DESIGN.md',
    `Public contract: ${slice.public_contract ?? '(none)'}`,
    '',
    `The tests are FROZEN. Read them READ-ONLY at: ${(slice.test_files ?? []).join(', ') || '(none)'}`,
    'You may NOT edit, delete, skip, rename, or weaken any test, and you may NOT add new test files.',
    'A tamper-check (git-diff scope + test-file hashes) enforces this — a violation reverts your work.',
    '',
    `Edit ONLY these implementation files: ${(slice.files ?? []).join(', ') || '(none)'}`,
    '',
    '## Current failure',
    '',
    suiteFailure || '(full suite failing after merge)',
    '',
    'Make every test pass without modifying any test. Return what you changed and where (file:line).',
  ].join('\n')
}

/**
 * Fresh-context author of the cross-slice seam tests. Sees the merged slices and
 * their public contracts and writes NEW integration test files exercising the
 * interactions between slices — the seams no single-slice test covers.
 */
export function buildIntegrationTestWriterPrompt(slices, { designPath, requirementsPath } = {}) {
  const roster = (slices ?? [])
    .map((s) => `  - ${s.id}: ${s.public_contract ?? s.summary ?? '(contract unstated)'}`)
    .join('\n') || '  (no slices)';
  return [
    'You are an INTEGRATION TEST-WRITER working from a FRESH context.',
    '',
    'Every slice below has been implemented and merged with its own unit tests green. Your job is to',
    'author NEW integration tests that exercise the SEAMS between slices — the cross-slice interactions',
    'and contract hand-offs that no single-slice test covers.',
    '',
    `Requirements: read ${requirementsPath ?? 'REQUIREMENTS.md'}`,
    `Design (contracts + slice decomposition): read ${designPath ?? 'DESIGN.md'}`,
    '',
    'Merged slices and their public contracts:',
    roster,
    '',
    '## Rules',
    '- Write only NEW integration/seam test files — do NOT modify any existing per-slice test.',
    '- Assert real cross-slice behavior (data flowing across contracts), not re-tested single-slice logic.',
    '- Cite the REQ-ID(s) each seam test discharges.',
    '',
    'Return a short summary of the seam tests written and their exact file paths.',
  ].join('\n')
}
