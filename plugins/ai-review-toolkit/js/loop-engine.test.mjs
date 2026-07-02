// Unit tests for the extracted convergence engine.
//
// runLoop() takes its Workflow globals via ctx, so we can drive it with mocked
// agents that play a scripted sequence of rounds — exercising convergence,
// max-rounds escalation, stuck detection, the fix-ALL gate, and single-round
// (qreview) mode without spawning any real agents.

import { test } from "node:test";
import assert from "node:assert/strict";
import { runLoop } from "./loop-engine.mjs";

const F = (id, severity, title) => ({
  id, severity, title,
  requirement: "REQ-1", finding: "f", recommendation: "fix it", source: "r1",
});
const R = (id) => ({ finding_id: id, status: "FIXED", evidence: "a.py:1", description: "fixed" });

// Mock ctx: parallel runs thunks; agent returns canned output keyed by round + label.
function makeCtx(rounds) {
  const agent = async (_prompt, opts) => {
    const label = opts.label || "";
    const r = Number((label.match(/:r(\d+)$/) || [])[1] || 1);
    const plan = rounds[r - 1] || {};
    if (label.startsWith("tests:")) return { summary: `round ${r}`, all_passed: true, failures: [] };
    if (label.startsWith("review:")) return { findings: plan.findings ?? [] };
    if (label.startsWith("fix:")) return { resolutions: plan.resolutions ?? [] };
    throw new Error("unexpected agent label: " + label);
  };
  return {
    agent,
    parallel: (thunks) => Promise.all(thunks.map((t) => t())),
    phase: () => {},
    log: () => {},
  };
}

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
