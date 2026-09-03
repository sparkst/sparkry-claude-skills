// Unit tests for the deterministic stopping rules (claude-skills#82, this repo #45).
//
// Every function here is PURE: the engine, not the model that wants to stop,
// decides whether a fix batch was small and contract-safe, whether the loop is
// still approaching a fixed point, and how much budget has actually been spent.

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DELTA_DEFAULTS,
  DIVERGENCE_DEFAULTS,
  isContractLine,
  isDeltaEligible,
  detectDivergence,
  summarizeBudget,
} from "./stopping-rules.mjs";

// A touched line as the diff probe reports it.
const L = (text, section = "") => ({ text, section });
// A round report as runLoop pushes it.
const RR = (round, newP0P1, extra = {}) => ({ round, newP0P1, valid: true, kind: "full", ...extra });

// ── contract lines ───────────────────────────────────────────────────────────

test("STOP-001: a line naming a REQ id is a contract line", () => {
  assert.equal(isContractLine(L("- **REQ-GRM-004** — the threshold is a value")).contract, true);
  assert.equal(isContractLine(L("REQ-PM-182 owns the night charter")).contract, true);
  assert.equal(isContractLine(L("the requirement is clear")).contract, false);
});

test("STOP-002: an acceptance line is a contract line under real markdown decoration", () => {
  for (const raw of [
    "Acceptance: the gate fails",
    "  - Acceptance: the gate fails",
    "* **Acceptance:** the gate fails",
    "1. Acceptance criteria are met",
    "> Acceptance: quoted",
  ]) {
    assert.equal(isContractLine(L(raw)).contract, true, `expected contract line: ${raw}`);
  }
  assert.equal(isContractLine(L("we accept this tradeoff")).contract, false);
});

test("STOP-003: an sto: line is a contract line", () => {
  assert.equal(isContractLine(L("sto: 2026-09-10")).contract, true);
  assert.equal(isContractLine(L("  sto: 2026-09-10")).contract, true);
  assert.equal(isContractLine(L("the customer is a stoic")).contract, false);
});

test("STOP-004: any line inside a protected section is a contract line, whatever it says", () => {
  assert.equal(isContractLine(L("| tests | none |", "### Requirement classes")).contract, true);
  assert.equal(isContractLine(L("prose", "### Cross-repo design")).contract, true);
  assert.equal(isContractLine(L("SP: 3", "### Story points")).contract, true);
  assert.equal(isContractLine(L("rounds: 3", "### Review receipt")).contract, true);
  // Heading match is exact-after-normalization, so a lookalike section is not protected.
  assert.equal(isContractLine(L("prose", "### Requirements")).contract, false);
  assert.equal(isContractLine(L("prose", "## Problem")).contract, false);
});

// ── delta eligibility ────────────────────────────────────────────────────────

const SMALL = { p0FixedCount: 0, artifactLines: 400, touched: [L("a typo fix"), L("another word"), L("third")] };

test("STOP-010: a small, P0-free, contract-safe batch is delta-eligible", () => {
  const got = isDeltaEligible(SMALL);
  assert.equal(got.eligible, true);
  assert.equal(got.reason, "eligible");
  assert.equal(got.changedLines, 3);
});

test("STOP-011: a batch that fixed any P0 is never delta-eligible", () => {
  const got = isDeltaEligible({ ...SMALL, p0FixedCount: 1 });
  assert.equal(got.eligible, false);
  assert.equal(got.reason, "p0-in-batch");
});

test("STOP-012: over the absolute line cap is not eligible", () => {
  const touched = Array.from({ length: DELTA_DEFAULTS.maxChangedLines + 1 }, (_, i) => L(`line ${i}`));
  const got = isDeltaEligible({ p0FixedCount: 0, artifactLines: 10000, touched });
  assert.equal(got.eligible, false);
  assert.equal(got.reason, "size-lines");
});

test("STOP-013: over the artifact fraction is not eligible even when under the line cap", () => {
  // 6 lines of a 100-line artifact = 6% > the 5% cap, and 6 <= the 20-line cap.
  const touched = Array.from({ length: 6 }, (_, i) => L(`line ${i}`));
  const got = isDeltaEligible({ p0FixedCount: 0, artifactLines: 100, touched });
  assert.equal(got.eligible, false);
  assert.equal(got.reason, "size-fraction");
});

test("STOP-014: BOTH size predicates must hold, not either", () => {
  // 6 lines of a 400-line artifact clears both.
  const touched = Array.from({ length: 6 }, (_, i) => L(`line ${i}`));
  assert.equal(isDeltaEligible({ p0FixedCount: 0, artifactLines: 400, touched }).eligible, true);
});

test("STOP-015: one touched contract line disqualifies the whole batch", () => {
  const got = isDeltaEligible({
    ...SMALL,
    touched: [L("a typo fix"), L("  - Acceptance: the gate fails"), L("third")],
  });
  assert.equal(got.eligible, false);
  assert.ok(got.reason.startsWith("contract-line"), got.reason);
});

test("STOP-016: an unusable probe fails CLOSED — a full round, never a delta round", () => {
  for (const bad of [
    undefined,
    {},
    { p0FixedCount: 0, artifactLines: 400, touched: "nope" },
    { p0FixedCount: 0, artifactLines: 0, touched: [L("x")] },
    { p0FixedCount: 0, artifactLines: 400, touched: [L("x")], truncated: true },
  ]) {
    const got = isDeltaEligible(bad);
    assert.equal(got.eligible, false, `expected ineligible for ${JSON.stringify(bad)}`);
  }
  assert.equal(isDeltaEligible({ p0FixedCount: 0, artifactLines: 400, touched: [L("x")], truncated: true }).reason, "size-lines");
  assert.equal(isDeltaEligible({}).reason, "probe-unavailable");
});

test("STOP-017: a fix batch that changed nothing fails closed — the fixer did not land", () => {
  const got = isDeltaEligible({ p0FixedCount: 0, artifactLines: 400, touched: [] });
  assert.equal(got.eligible, false);
  assert.equal(got.reason, "no-diff");
});

test("STOP-018: the caps are overridable but default to #45's numbers", () => {
  assert.deepEqual(DELTA_DEFAULTS, { maxChangedLines: 20, maxChangedFraction: 0.05 });
  const touched = Array.from({ length: 25 }, (_, i) => L(`line ${i}`));
  assert.equal(isDeltaEligible({ p0FixedCount: 0, artifactLines: 10000, touched }).eligible, false);
  assert.equal(
    isDeltaEligible({ p0FixedCount: 0, artifactLines: 10000, touched }, { maxChangedLines: 30 }).eligible,
    true,
  );
});

// ── divergence ───────────────────────────────────────────────────────────────

test("STOP-020: the 19-round shape — new P0/P1 every round with no decay — is DIVERGING", () => {
  // pm-816-intake-0903: rounds 9-18 each surfaced 1-2 genuinely new P0s.
  const rounds = [1, 2, 3, 4, 5, 6].map((r) => RR(r, 2));
  const got = detectDivergence(rounds);
  assert.equal(got.diverging, true);
  assert.match(got.reason, /SPLIT/);
  assert.equal(got.recentSum, 6);
  assert.equal(got.priorSum, 6);
});

test("STOP-021: divergence never fires before the warmup — a short run is just a run", () => {
  for (let n = 1; n <= 5; n++) {
    const rounds = Array.from({ length: n }, (_, i) => RR(i + 1, 2));
    assert.equal(detectDivergence(rounds).diverging, false, `fired at ${n} rounds`);
  }
});

test("STOP-022: a decaying finding rate is convergence, not divergence", () => {
  const rounds = [RR(1, 5), RR(2, 4), RR(3, 3), RR(4, 2), RR(5, 1), RR(6, 1)];
  assert.equal(detectDivergence(rounds).diverging, false);
});

test("STOP-023: one clean round inside the window breaks divergence", () => {
  const rounds = [RR(1, 3), RR(2, 3), RR(3, 3), RR(4, 3), RR(5, 0), RR(6, 3)];
  assert.equal(detectDivergence(rounds).diverging, false);
});

test("STOP-024: INVALID rounds are not progress — they neither fill nor break the window (#81)", () => {
  // Six rounds, but two died below quorum. Only four valid rounds exist, so the
  // rule has no business firing: a flaky environment must not read as divergence.
  const rounds = [
    RR(1, 2), RR(2, 2), RR(3, 0, { valid: false }),
    RR(4, 2), RR(5, 0, { valid: false }), RR(6, 2),
  ];
  const got = detectDivergence(rounds);
  assert.equal(got.diverging, false, "an all-zero dead round must not look like decay either");
  assert.equal(got.validRounds, 4);
});

test("STOP-025: the window and warmup are tunable", () => {
  const rounds = [RR(1, 1), RR(2, 1), RR(3, 1), RR(4, 1)];
  assert.equal(detectDivergence(rounds).diverging, false);
  assert.equal(detectDivergence(rounds, { window: 2, warmup: 4 }).diverging, true);
  assert.deepEqual(DIVERGENCE_DEFAULTS, { window: 3, warmup: 6 });
});

// ── budget ───────────────────────────────────────────────────────────────────

test("STOP-030: the budget counts rounds by kind and excludes invalid ones (#81)", () => {
  const rounds = [
    RR(1, 2, { kind: "gate" }),
    RR(2, 1, { kind: "full" }),
    RR(3, 0, { kind: "delta" }),
    RR(4, 0, { kind: "full", valid: false }),
    RR(5, 0, { kind: "full" }),
  ];
  assert.deepEqual(summarizeBudget(rounds, { maxRounds: 5 }), {
    maxRounds: 5,
    roundsRun: 5,
    validRounds: 4,
    invalidRounds: 1,
    fullRounds: 2,
    deltaRounds: 1,
    gateRounds: 1,
  });
});

test("STOP-031: an empty run summarizes to zeros rather than throwing", () => {
  assert.deepEqual(summarizeBudget([], { maxRounds: 5 }), {
    maxRounds: 5,
    roundsRun: 0,
    validRounds: 0,
    invalidRounds: 0,
    fullRounds: 0,
    deltaRounds: 0,
    gateRounds: 0,
  });
});
