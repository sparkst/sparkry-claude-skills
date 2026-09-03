import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ensureUniqueIds,
  adjudicateRound,
  mergeLedger,
  renderLedger,
  reviewerQuorum,
  attestReviewers,
  describeReviewerShortfall,
  renderAttestation,
  REVIEWER_NO_RESULT,
  REVIEWER_MALFORMED,
  REVIEWER_UNKNOWN_REASON,
} from "./workflow-helpers.mjs";

test("leaves already-unique ids untouched", () => {
  const out = ensureUniqueIds([{ id: "P0-001" }, { id: "P1-002" }]);
  assert.deepStrictEqual(out.map((f) => f.id), ["P0-001", "P1-002"]);
});

test("suffixes colliding ids deterministically, preserving order", () => {
  // Two reviewers both emitted P0-001 and P0-002 for different findings.
  const out = ensureUniqueIds([
    { id: "P0-001", title: "divide" },
    { id: "P0-001", title: "sqli" },
    { id: "P0-002", title: "sqli-2" },
    { id: "P0-002", title: "divide-2" },
  ]);
  assert.deepStrictEqual(out.map((f) => f.id), [
    "P0-001",
    "P0-001-2",
    "P0-002",
    "P0-002-2",
  ]);
});

test("third collision gets -3; does not mutate the input objects", () => {
  const input = [{ id: "X" }, { id: "X" }, { id: "X" }];
  const out = ensureUniqueIds(input);
  assert.deepStrictEqual(out.map((f) => f.id), ["X", "X-2", "X-3"]);
  assert.strictEqual(input[1].id, "X", "input must not be mutated");
});

test("all four unique ids are now distinct — the fix-ALL gate can cover them", () => {
  const out = ensureUniqueIds([
    { id: "P0-001" }, { id: "P0-001" }, { id: "P0-002" }, { id: "P0-002" },
  ]);
  assert.strictEqual(new Set(out.map((f) => f.id)).size, 4);
});

// ── LEDGER-001..005: the adjudicated-findings ledger ─────────────────────────
//
// Production incident (2026-08-01): a bugfix went through 5 review rounds; each
// round's clean-context reviewer started blind, re-litigated geometry the prior
// round had already settled, and each round's fix introduced a NEW P1. Reviewers
// are clean-context BY DESIGN (fresh eyes for new bugs) — the defect was that
// only round N-1 reached round N, so "clean context" degraded into amnesia.

const LF = (id, severity, title, extra = {}) => ({
  id,
  severity,
  title,
  requirement: "REQ-1",
  finding: "f",
  recommendation: "fix it",
  source: "r1",
  ...extra,
});

test("LEDGER-001: a FIXED resolution whose finding did not recur is adjudicated as fixed", () => {
  const entries = adjudicateRound({
    round: 1,
    findings: [LF("P0-001", "P0", "Bug A")],
    resolutions: [
      { finding_id: "P0-001", status: "FIXED", evidence: "a.py:1", description: "guarded" },
    ],
    nextRoundFindings: [],
  });
  assert.strictEqual(entries.length, 1);
  assert.strictEqual(entries[0].id, "P0-001");
  assert.strictEqual(entries[0].resolution, "fixed");
  assert.strictEqual(entries[0].resolved_by, "round 1 fixer");
  assert.strictEqual(entries[0].evidence, "a.py:1");
});

test("LEDGER-002: an OPEN finding (no resolution) is NEVER admitted to the ledger", () => {
  // Injecting open findings biases a clean-context reviewer toward confirming
  // them — an explicit design decision, not an oversight.
  const entries = adjudicateRound({
    round: 1,
    findings: [LF("P0-001", "P0", "Bug A"), LF("P1-002", "P1", "Bug B")],
    resolutions: [{ finding_id: "P0-001", status: "FIXED", evidence: "a.py:1", description: "d" }],
    nextRoundFindings: [],
  });
  assert.deepStrictEqual(entries.map((e) => e.id), ["P0-001"]);
});

test("LEDGER-003: an ESCALATED resolution is NOT settled — it stays out of the ledger", () => {
  const entries = adjudicateRound({
    round: 2,
    findings: [LF("P0-001", "P0", "Bug A")],
    resolutions: [
      { finding_id: "P0-001", status: "ESCALATED", evidence: "", description: "needs a decision" },
    ],
    nextRoundFindings: [],
  });
  assert.deepStrictEqual(entries, []);
});

test("LEDGER-004: a fix that did NOT hold (finding recurs next round) is withheld from the ledger", () => {
  // Verification gate: a claimed fix is only adjudicated once the NEXT round's
  // reviewers failed to re-raise it. Otherwise the ledger would tell reviewers
  // "do not re-litigate" about a bug that is still live.
  const entries = adjudicateRound({
    round: 1,
    findings: [LF("P0-001", "P0", "Bug A")],
    resolutions: [{ finding_id: "P0-001", status: "FIXED", evidence: "a.py:1", description: "d" }],
    nextRoundFindings: [LF("P0-009", "P0", "Bug A")], // same normalized title → still live
  });
  assert.deepStrictEqual(entries, []);
});

test("LEDGER-005: mergeLedger accumulates across rounds and keeps the newest entry per title", () => {
  const r1 = adjudicateRound({
    round: 1,
    findings: [LF("P0-001", "P0", "Bug A")],
    resolutions: [{ finding_id: "P0-001", status: "FIXED", evidence: "a.py:1", description: "d" }],
    nextRoundFindings: [],
  });
  const r2 = adjudicateRound({
    round: 2,
    findings: [LF("P1-002", "P1", "Bug B")],
    resolutions: [{ finding_id: "P1-002", status: "FIXED", evidence: "b.py:2", description: "d" }],
    nextRoundFindings: [],
  });
  const ledger = mergeLedger(mergeLedger([], r1), r2);
  assert.deepStrictEqual(ledger.map((e) => e.id), ["P0-001", "P1-002"]);
  // Round 1's entry survives into round 3's prompt — the whole point of the fix.
  assert.strictEqual(ledger[0].round, 1);
});

test("LEDGER-005b: re-adjudicating the same title replaces rather than duplicates", () => {
  const a = [{ id: "P0-001", round: 1, severity: "P0", title: "Bug A", summary: "s", file: "a.py", resolution: "fixed", resolved_by: "round 1 fixer", evidence: "a.py:1" }];
  const b = [{ id: "P0-007", round: 3, severity: "P0", title: "bug a", summary: "s2", file: "a.py", resolution: "fixed", resolved_by: "round 3 fixer", evidence: "a.py:9" }];
  const merged = mergeLedger(a, b);
  assert.strictEqual(merged.length, 1, "same normalized title collapses");
  assert.strictEqual(merged[0].round, 3, "newest adjudication wins");
});

// The second fixture row uses resolution:"dismissed" deliberately. The engine
// only ever emits "fixed" today; this pins that the renderer stays generic over
// the reserved value, so a future dismissal path needs no renderer change.
test("LEDGER-006: renderLedger emits the do-not-re-litigate framing and every entry", () => {
  const ledger = [
    { id: "P0-001", round: 1, severity: "P0", title: "Bug A", summary: "off-by-one in the offset", file: "a.py", resolution: "fixed", resolved_by: "round 1 fixer", evidence: "a.py:1" },
    { id: "P2-004", round: 2, severity: "P2", title: "Bug B", summary: "naming", file: "b.py", resolution: "dismissed", resolved_by: "round 2 reviewer consensus", evidence: "not applicable on this platform" },
  ];
  const out = renderLedger(ledger);
  assert.match(out, /ADJUDICATED-FINDINGS LEDGER/);
  assert.match(out, /do not re-litigate/i);
  assert.match(out, /verify/i);
  assert.match(out, /NEW finding/);
  assert.match(out, /P0-001/);
  assert.match(out, /P2-004/);
  assert.match(out, /off-by-one in the offset/);
});

test("LEDGER-006b: renderLedger returns empty string for an empty ledger (no dead section)", () => {
  assert.strictEqual(renderLedger([]), "");
});

// ---------------------------------------------------------------------------
// #81 — reviewer attestation + quorum
// ---------------------------------------------------------------------------

test("QUORUM-H01: quorum is a majority of the panel with a floor of 2", () => {
  // 32 reviewers with 3 survivors (the 2026-08 incident) must be below quorum,
  // which a constant floor of 2 would have waved through.
  const table = [[0, 0], [1, 1], [2, 2], [3, 2], [4, 2], [5, 3], [8, 4], [32, 16]];
  for (const [requested, expected] of table) {
    assert.equal(reviewerQuorum(requested), expected, `requested=${requested}`);
  }
});

test("QUORUM-H02: garbage panel sizes never produce a negative or fractional quorum", () => {
  for (const bad of [-4, null, undefined, "x", NaN]) {
    assert.equal(reviewerQuorum(bad), 0, `requested=${String(bad)}`);
  }
});

test("QUORUM-H03: a full panel attests as returned and its findings pass through", () => {
  const att = attestReviewers([
    { name: "opus", ok: true, value: { findings: [{ id: "P0-001" }] } },
    { name: "sonnet", ok: true, value: { findings: [] } },
  ]);
  assert.equal(att.requested, 2);
  assert.equal(att.returned, 2);
  assert.equal(att.quorumMet, true);
  assert.deepStrictEqual(att.missing, []);
  assert.deepStrictEqual(att.lists, [[{ id: "P0-001" }], []]);
});

test("QUORUM-H04: a thrown reason is preserved verbatim, not swallowed", () => {
  const att = attestReviewers([
    { name: "opus", ok: false, reason: "Login expired" },
    { name: "sonnet", ok: false, reason: "Login expired" },
  ]);
  assert.equal(att.returned, 0);
  assert.equal(att.quorumMet, false);
  assert.deepStrictEqual(att.missing, [
    { name: "opus", reason: "Login expired" },
    { name: "sonnet", reason: "Login expired" },
  ]);
  assert.deepStrictEqual(att.lists, []);
});

test("QUORUM-H05: a null result and a malformed result are missing, not silent zeros", () => {
  const att = attestReviewers([
    { name: "a", ok: true, value: null },
    { name: "b", ok: true, value: {} },
    { name: "c", ok: true, value: { findings: [] } },
  ]);
  assert.equal(att.returned, 1, "only the reviewer with a findings array reported");
  assert.deepStrictEqual(att.missing, [
    { name: "a", reason: REVIEWER_NO_RESULT },
    { name: "b", reason: REVIEWER_MALFORMED },
  ]);
});

test("QUORUM-H06: an unnamed failure still names that it failed", () => {
  const att = attestReviewers([{ name: "a", ok: false, reason: "   " }]);
  assert.equal(att.missing[0].reason, REVIEWER_UNKNOWN_REASON);
});

test("QUORUM-H07: a multi-line runtime error collapses to one capped line", () => {
  const att = attestReviewers([{ name: "a", ok: false, reason: `boom\n  at x\n${"y".repeat(400)}` }]);
  assert.ok(!att.missing[0].reason.includes("\n"), "reason must stay one line");
  assert.ok(att.missing[0].reason.length <= 240, "reason must stay capped");
});

test("QUORUM-H08: an empty panel (the deterministic gate round) is valid on its own terms", () => {
  const att = attestReviewers([]);
  assert.equal(att.requested, 0);
  assert.equal(att.quorumMet, true, "quorum gates reviewer panels, not gate rounds");
});

test("QUORUM-H09: the shortfall line names the count AND every failure reason", () => {
  const line = describeReviewerShortfall(3, attestReviewers([
    { name: "opus", ok: false, reason: "Login expired" },
    { name: "sonnet", ok: false, reason: "Login expired" },
  ]));
  assert.match(line, /Round 3 INVALID/);
  assert.match(line, /0\/2 reviewers returned \(quorum 2\)/);
  assert.match(line, /opus: Login expired; sonnet: Login expired/);
});

test("QUORUM-H10: the verdict fragment carries returned/requested", () => {
  assert.equal(renderAttestation({ returned: 2, requested: 4 }), "reviewers 2/4 returned");
});
