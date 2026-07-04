// Unit tests for the extracted convergence engine.
//
// runLoop() takes its Workflow globals via ctx, so we can drive it with mocked
// agents that play a scripted sequence of rounds — exercising convergence,
// max-rounds escalation, stuck detection, the fix-ALL gate, and single-round
// (qreview) mode without spawning any real agents.

import { test } from "node:test";
import assert from "node:assert/strict";
import { runLoop } from "./loop-engine.mjs";
import { resolveReviewerModel } from "./adjudication.mjs";

const F = (id, severity, title, extra = {}) => ({
  id, severity, title,
  requirement: "REQ-1", finding: "f", recommendation: "fix it", source: "r1",
  ...extra,
});
const R = (id) => ({ finding_id: id, status: "FIXED", evidence: "a.py:1", description: "fixed" });

// Mock ctx: parallel runs thunks; agent returns canned output keyed by round +
// label. ctx.calls records every agent label so tests can assert which fixer ran;
// ctx.modelByLabel and ctx.promptByLabel let tests assert model tiering (OPT-002/010)
// and prompt content (OPT-007/015). `opts.historyWriteFails` simulates a failed
// history write so the embed fallback (OPT-015) can be exercised.
function makeCtx(rounds, opts = {}) {
  const calls = [];
  const modelByLabel = {};
  const promptByLabel = {};
  const ctx = {
    calls,
    modelByLabel,
    promptByLabel,
    agent: async (prompt, o) => {
      const label = o.label || "";
      calls.push(label);
      modelByLabel[label] = o.model;
      promptByLabel[label] = prompt;
      const r = Number((label.match(/:r(\d+)$/) || [])[1] || 1);
      const plan = rounds[r - 1] || {};
      if (label.startsWith("tests:")) return { summary: `round ${r}`, all_passed: true, failures: plan.testFailures ?? [], command: plan.testCommand };
      if (label.startsWith("review:")) return { findings: plan.findings ?? [] };
      if (label.startsWith("verify:")) return { findings: plan.verifyFindings ?? plan.findings ?? [] };
      if (label.startsWith("history:")) return { wrote: opts.historyWriteFails ? false : true };
      if (label === "cleanup") return { wrote: true };
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
// Reviewer labels are `review:<name>:r<N>`, so filter fan-outs by round suffix.
const reviewersInRound = (ctx, r) => ctx.calls.filter((l) => l.startsWith("review:") && l.endsWith(`:r${r}`));

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

// ── OPT-010: per-round test gate runs on haiku, not sonnet ───────────────────
test("OPT-010: the per-round test gate is spawned on haiku", async () => {
  const ctx = makeCtx([{ findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] }, { findings: [] }]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(ctx.modelByLabel["tests:r1"], "haiku", "test gate must run on haiku");
});

// ── OPT-002: reviewers routed through resolveReviewerModel, forwarding flags ──
// Policy-agnostic: assert the engine's spawned model equals resolveReviewerModel's
// own decision (the policy lives in adjudication.mjs, owned by the policy batch),
// while forwarding the per-agent escalation/high-stakes flags the team carries.
test("OPT-002: the high_stakes flag on a team member is forwarded and changes the resolved model", async () => {
  const team = [
    { name: "hs", model: "sonnet", review_lens: "x", high_stakes: true },
    { name: "plain", model: "sonnet", review_lens: "y" },
  ];
  const exp = (a) =>
    resolveReviewerModel(a, null, { escalationEligible: a.escalation_eligible ?? false, highStakes: a.high_stakes ?? false }) ||
    a.model || "sonnet";
  const ctx = makeCtx([{ findings: [] }, { findings: [] }]);
  await runLoop({ artifact: "a", requirements: "r", team, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(ctx.modelByLabel["review:hs:r1"], exp(team[0]));
  assert.equal(ctx.modelByLabel["review:plain:r1"], exp(team[1]));
  assert.notEqual(ctx.modelByLabel["review:hs:r1"], ctx.modelByLabel["review:plain:r1"], "high_stakes must change the tier");
});

test("OPT-002: complexity escalates only the escalation_eligible reviewers", async () => {
  const team = [
    { name: "elig", model: "sonnet", review_lens: "x", escalation_eligible: true },
    { name: "inelig", model: "sonnet", review_lens: "y" },
  ];
  const complexity = { files: 9, toolTypes: 9, contextFraction: 0.99 }; // large under any policy bar
  const mapped = { file_count: 9, tool_types: 9, context_fraction: 0.99 };
  const ctx = makeCtx([{ findings: [] }, { findings: [] }]);
  await runLoop({ artifact: "a", requirements: "r", team, threshold: 0, maxRounds: 5, complexity }, ctx);
  assert.equal(ctx.modelByLabel["review:elig:r1"], resolveReviewerModel(team[0], mapped, { escalationEligible: true, highStakes: false }));
  assert.equal(ctx.modelByLabel["review:inelig:r1"], resolveReviewerModel(team[1], mapped, { escalationEligible: false, highStakes: false }));
  assert.notEqual(ctx.modelByLabel["review:elig:r1"], ctx.modelByLabel["review:inelig:r1"], "complexity escalates the eligible reviewer only");
});

test("OPT-002: with no flags and no complexity, reviewers keep their team model", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  for (const a of TEAM) assert.equal(ctx.modelByLabel[`review:${a.name}:r1`], a.model);
});

// ── OPT-007: doc-artifact test-gate skip + test-command carry-forward ────────
test("OPT-007: skipTests suppresses the per-round test gate entirely", async () => {
  const ctx = makeCtx([{ findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] }, { findings: [] }]);
  await runLoop({ artifact: "doc.md", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, skipTests: true }, ctx);
  assert.equal(labelsWith(ctx, "tests:").length, 0, "no test agent should run for a document artifact");
});

test("OPT-007: the discovered test command is carried into round 2's test gate", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")], testCommand: "pytest -q tools/" },
    { findings: [] },
  ]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.match(ctx.promptByLabel["tests:r1"], /standard test command/, "round 1 discovers the command");
  assert.match(ctx.promptByLabel["tests:r2"], /Run exactly this command.*pytest -q tools\//, "round 2 re-runs it verbatim");
});

// ── OPT-009: proportional verification round ─────────────────────────────────
test("OPT-009: a clean round 1 with no fixer buys a single verifier, not a full round-2 fan-out", async () => {
  const ctx = makeCtx([
    { findings: [] },                 // r1 clean, no fixer
    { verifyFindings: [] },           // r2 verifier: still clean
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.rounds, 2, "min-2-rounds floor still honored");
  assert.equal(labelsWith(ctx, "verify:r2").length, 1, "round 2 runs a single verifier");
  assert.equal(reviewersInRound(ctx, 2).length, 0, "no full reviewer fan-out in round 2");
  assert.equal(labelsWith(ctx, "tests:r2").length, 0, "no test gate in the proportional round");
  assert.equal(ctx.modelByLabel["verify:r2"], "sonnet", "the verifier runs on sonnet");
});

test("OPT-009: a P0 surfaced by the verifier re-opens the full loop (fix + full re-review)", async () => {
  const ctx = makeCtx([
    { findings: [] },                                       // r1 clean, no fixer
    { verifyFindings: [F("P0-001", "P0", "Regression")], resolutions: [R("P0-001")] }, // r2 verifier finds a P0
    { findings: [] },                                       // r3 full re-review: clean
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(labelsWith(ctx, "verify:r2").length, 1, "round 2 is proportional");
  assert.equal(labelsWith(ctx, "fix:r2").length, 1, "the verifier's P0 triggers a fixer");
  assert.equal(reviewersInRound(ctx, 3).length, 2, "round 3 goes back to full fan-out (2 reviewers)");
  assert.equal(labelsWith(ctx, "verify:").length, 1, "the cheap verifier fires at most once");
  assert.equal(out.outcome.status, "converged");
});

test("OPT-009: after any fixer edit, the mandatory re-review round stays a full fan-out", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug")], resolutions: [R("P0-001")] }, // r1 has a fix
    { findings: [] },                                                     // r2 must be full re-review
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(labelsWith(ctx, "verify:").length, 0, "no proportional shortcut after a fix");
  assert.equal(reviewersInRound(ctx, 2).length, 2, "round 2 re-reviews with the full team");
  assert.equal(out.outcome.status, "converged");
});

// ── OPT-015: findings-history externalized to a file, referenced by path ─────
test("OPT-015: round 2 reviewers reference the history file by path, not an embedded block", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug")], resolutions: [R("P0-001")] }, // r1 → history written
    { findings: [] },
  ]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(labelsWith(ctx, "history:r1").length, 1, "round 1 writes its history file");
  const r2prompt = ctx.promptByLabel["review:r1:r2"];
  assert.match(r2prompt, /a\.review-r1\.md/, "round 2 reviewer prompt cites the history file path");
  assert.match(r2prompt, /REQUIRED to Read/, "reviewer is required to read it");
  assert.doesNotMatch(r2prompt, /## Prior Round Findings/, "the findings block is NOT embedded when externalized");
  assert.equal(ctx.calls.filter((l) => l === "cleanup").length, 1, "history files are cleaned up at loop end");
});

test("OPT-015: if the history write fails, round 2 falls back to embedding (zero information loss)", async () => {
  const ctx = makeCtx(
    [
      { findings: [F("P0-001", "P0", "Bug")], resolutions: [R("P0-001")] },
      { findings: [] },
    ],
    { historyWriteFails: true },
  );
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  const r2prompt = ctx.promptByLabel["review:r1:r2"];
  assert.match(r2prompt, /## Prior Round Findings/, "falls back to the embedded block");
  assert.doesNotMatch(r2prompt, /review-r1\.md/, "no path reference when the write failed");
});
