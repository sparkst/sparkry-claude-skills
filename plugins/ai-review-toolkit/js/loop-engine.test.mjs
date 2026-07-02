// Unit tests for the extracted convergence engine.
//
// runLoop() takes its Workflow globals via ctx, so we can drive it with mocked
// agents that play a scripted sequence of rounds — exercising convergence,
// max-rounds escalation, stuck detection, the fix-ALL gate, and single-round
// (qreview) mode without spawning any real agents.

import { test } from "node:test";
import assert from "node:assert/strict";
import { runLoop } from "./loop-engine.mjs";

const F = (id, severity, title, extra = {}) => ({
  id, severity, title,
  requirement: "REQ-1", finding: "f", recommendation: "fix it", source: "r1",
  ...extra,
});
const R = (id) => ({ finding_id: id, status: "FIXED", evidence: "a.py:1", description: "fixed" });

// Mock ctx: parallel runs thunks; agent returns canned output keyed by round +
// label. ctx.calls records every agent label so tests can assert which fixer ran.
function makeCtx(rounds) {
  const calls = [];
  const ctx = {
    calls,
    agent: async (_prompt, opts) => {
      const label = opts.label || "";
      calls.push(label);
      const r = Number((label.match(/:r(\d+)$/) || [])[1] || 1);
      const plan = rounds[r - 1] || {};
      if (label.startsWith("tests:")) return { summary: `round ${r}`, all_passed: true, failures: [] };
      if (label.startsWith("review:")) return { findings: plan.findings ?? [] };
      if (label.startsWith("spotfix:")) return { resolutions: plan.spotResolutions ?? [R("spot")] };
      if (label.startsWith("spotcheck:")) return { all_applied: true, not_applied: [] };
      if (label.startsWith("fix:")) return { resolutions: plan.resolutions ?? [] };
      throw new Error("unexpected agent label: " + label);
    },
    parallel: (thunks) => Promise.all(thunks.map((t) => t())),
    phase: () => {},
    log: () => {},
  };
  return ctx;
}
const labelsWith = (ctx, prefix) => ctx.calls.filter((l) => l.startsWith(prefix));

const TEAM = [
  { name: "r1", model: "sonnet", review_lens: "x" },
  { name: "r2", model: "sonnet", review_lens: "y" },
];

test("converges once findings clear, respecting the min-2-rounds floor", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.outcome.round, 2);
  assert.equal(out.rounds, 2);
  assert.deepEqual(out.final_counts, { P0: 0, P1: 0, P2: 0, P3: 0 });
});

test("escalates on max rounds when it never converges (distinct findings avoid stuck)", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug A")], resolutions: [R("P0-001")] },
    { findings: [F("P0-001", "P0", "Bug B")], resolutions: [R("P0-001")] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 2 }, ctx);
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /Max rounds \(2\)/);
});

test("stuck detection escalates on identical P0/P1 across two rounds", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug A")], resolutions: [R("P0-001")] },
    { findings: [F("P0-001", "P0", "Bug A")], resolutions: [R("P0-001")] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /Stuck/);
});

test("fix-ALL gate escalates when the fixer misses a finding id", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug A")], resolutions: [] }, // fixer resolves nothing
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 3 }, ctx);
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /Fix-ALL gate failed/);
});

test("single-round (qreview) mode: one round, no fixer, escalates unresolved", async () => {
  const ctx = makeCtx([{ findings: [F("P0-001", "P0", "Bug A")] }]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: [TEAM[0]], rounds: 1 }, ctx);
  assert.equal(out.rounds, 1);
  assert.equal(out.outcome.status, "escalated");
});

test("validates inputs", async () => {
  const ctx = makeCtx([]);
  await assert.rejects(() => runLoop({ requirements: "r", team: TEAM }, ctx), /requires artifact/);
  await assert.rejects(() => runLoop({ artifact: "a", requirements: "r", team: [TEAM[0]] }, ctx), /at least 2 reviewers/);
});

test("trivial P2/P3 is spot-fixed (haiku), not main-fixed, and does not block convergence", async () => {
  const ctx = makeCtx([
    { findings: [F("P2-001", "P2", "Cosmetic nit")] }, // trivial, first-seen → no significant
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.rounds, 2);
  assert.equal(labelsWith(ctx, "spotfix:").length, 1, "trivial nit should be spot-fixed");
  assert.equal(labelsWith(ctx, "fix:").length, 0, "the main (significant) fixer must not run for a trivial nit");
  assert.equal(out.history[0].trivial, 1);
  assert.equal(out.history[0].significant, 0);
});

test("reviewer significance:true promotes a P2 to the full fix-loop", async () => {
  const ctx = makeCtx([
    { findings: [F("P2-001", "P2", "Serious P2", { significance: true })], resolutions: [R("P2-001")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.history[0].significant, 1, "flagged P2 is significant");
  assert.equal(labelsWith(ctx, "fix:").length, 1, "significant P2 goes through the main fixer");
});

test("a P2 that recurs across rounds is promoted to significant", async () => {
  const ctx = makeCtx([
    { findings: [F("P2-001", "P2", "Recurring nit")] },                    // r1: trivial, first-seen
    { findings: [F("P2-001", "P2", "Recurring nit")], resolutions: [R("P2-001")] }, // r2: recurs → significant
    { findings: [] },                                                       // r3: clean
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.history[0].significant, 0, "round 1: trivial");
  assert.equal(out.history[1].significant, 1, "round 2: recurrence promotes it");
  assert.equal(out.outcome.status, "converged");
});
