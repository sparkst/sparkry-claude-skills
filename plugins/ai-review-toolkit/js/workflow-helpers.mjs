// Orchestration-only helpers for review-loop.workflow.js.
//
// These are NOT part of the Python-oracle adjudication contract (they have no
// Python equivalent), so they live outside adjudication.mjs and are inlined
// into the generated workflow separately. Pure functions; unit-tested by
// workflow-helpers.test.mjs.

/**
 * Make finding IDs unique within a synthesized set.
 *
 * Reviewers number their own findings independently (P0-001, P0-002, ...), so
 * two distinct findings from two reviewers routinely collide on the same id.
 * Dedup merges by *title*, not id, so collisions survive synthesis — which
 * breaks the id-keyed fix-ALL gate (checkFixCompleteness) and tempts the fixer
 * to invent disambiguated ids that then match nothing. This suffixes each
 * collision deterministically (`P0-001`, `P0-001-2`, `P0-001-3`, …), preserving
 * order and leaving already-unique ids untouched.
 */
export function ensureUniqueIds(findings) {
  const counts = new Map();
  return findings.map((f) => {
    const id = String(f.id ?? "");
    const n = (counts.get(id) ?? 0) + 1;
    counts.set(id, n);
    return n === 1 ? f : { ...f, id: `${id}-${n}` };
  });
}
