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
      // #81: simulate a reviewer/verifier that never reports back.
      // `opts.reviewerOutcome(label, round)` returns "throw:<reason>" (an
      // environmental death, e.g. Login expired), "null" (no output at all — the
      // shape `filter(Boolean)` used to eat), "empty" (a malformed result with no
      // findings array), or undefined for the normal path.
      if (label.startsWith("review:") || label.startsWith("verify:")) {
        const fate = opts.reviewerOutcome ? opts.reviewerOutcome(label, r) : undefined;
        if (fate === "null") return null;
        if (fate === "empty") return {};
        if (typeof fate === "string" && fate.startsWith("throw:")) throw new Error(fate.slice(6));
      }
      if (label.startsWith("tests:")) return { summary: `round ${r}`, all_passed: true, failures: plan.testFailures ?? [], command: plan.testCommand };
      if (label.startsWith("review:")) return { findings: plan.findings ?? [] };
      if (label.startsWith("verify:")) return { findings: plan.verifyFindings ?? plan.findings ?? [] };
      if (label.startsWith("history:")) return { wrote: opts.historyWriteFails ? false : true };
      if (label === "cleanup") return { wrote: true };
      if (label.startsWith("spotfix:")) return { resolutions: plan.spotResolutions ?? [R("spot")], edited_files: plan.spotEditedFiles ?? [] };
      if (label.startsWith("spotcheck:")) return { all_applied: !opts.notApplied, not_applied: opts.notApplied ?? [] };
      if (label.startsWith("fix:")) return { resolutions: plan.resolutions ?? [], edited_files: plan.editedFiles ?? [] };
      // The diff probe (#82). No `plan.diff` → the probe came back unusable, which
      // fails CLOSED to a full round, so every pre-existing test keeps its shape.
      if (label.startsWith("diff:")) return plan.diff ?? null;
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

test("REQ-42-1: single-round (qreview) mode never runs the spot-fixer or spot-check on trivial findings", async () => {
  const ctx = makeCtx([{ findings: [F("P2-001", "P2", "Cosmetic nit")] }]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: [TEAM[0]], rounds: 1 }, ctx);
  assert.equal(out.rounds, 1);
  assert.deepEqual(labelsWith(ctx, "spotfix:"), [], "no spot-fixer may run on a plain /qreview");
  assert.deepEqual(labelsWith(ctx, "spotcheck:"), [], "no spot-check may run on a plain /qreview");
  assert.equal(out.history[0].trivial, 1, "the trivial finding is still reported, just never spot-fixed");
});

test("REQ-42-1 latent-shape guard: rounds:1 with maxRounds>1 still withholds the spot-fixer", async () => {
  const ctx = makeCtx([
    { findings: [F("P2-001", "P2", "Cosmetic nit")] },
    { findings: [] },
  ]);
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, rounds: 1, maxRounds: 5 },
    ctx
  );
  assert.equal(out.rounds, 1, "rounds:1 must keep its 1-round floor (no forced second round)");
  assert.equal(
    labelsWith(ctx, "spotfix:").length,
    0,
    "REQ-42-1 is literal: rounds:1 withholds the spot-fixer regardless of maxRounds"
  );
});

test("REQ-42-1: pipeline-auto's {rounds:1, maxRounds:4} integration-plan diagnose stays edit-free", async () => {
  const ctx = makeCtx([
    { findings: [F("P2-001", "P2", "Cosmetic nit")] },
    { findings: [] },
  ]);
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, rounds: 1, maxRounds: 4 },
    ctx
  );
  assert.equal(out.rounds, 1, "rounds:1 must keep its 1-round floor (no forced second round)");
  assert.equal(labelsWith(ctx, "fix:").length, 0, "no full fixer round may run on a single-pass diagnose");
  assert.equal(
    labelsWith(ctx, "spotfix:").length,
    0,
    "no spot-fixer may run on pipeline-auto's documented single-pass diagnose"
  );
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

// ── SMOKE-008: surface fixer-declared edited files so the pipeline commit step can
// capture them (a converge's fixer may edit test files beyond the artifact; if the
// commit only pathspec-scopes the artifact, verify runs on an uncommitted tree). ──
test("SMOKE-008: runLoop aggregates the fixer's declared edited_files (deduped + sorted)", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug"), F("P2-001", "P2", "Nit")], resolutions: [R("P0-001")], editedFiles: ["src/b.md", "tests/a.test.py"], spotEditedFiles: ["src/b.md"] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "src/b.md", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.deepEqual(out.edited_files, ["src/b.md", "tests/a.test.py"], "fixer + spot-fixer edits, deduped and sorted");
});

test("SMOKE-008: edited_files is an empty array when no fixer runs (clean first round)", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.deepEqual(out.edited_files, [], "no edits declared → empty array, never undefined");
});

test("SMOKE-008: the fixer prompt instructs declaring edited_files", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug")], resolutions: [R("P0-001")], editedFiles: ["x.py"] },
    { findings: [] },
  ]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.match(ctx.promptByLabel["fix:r1"], /edited_files/, "fixer is told to declare every file it edited");
});

// ── LEDGER-007..011: cross-round adjudicated-findings ledger ─────────────────
//
// Production incident (2026-08-01): 5 review rounds, each reviewer blind to
// everything before round N-1, re-litigating settled decisions while every fix
// introduced a new P1. The engine now carries a CUMULATIVE ledger of adjudicated
// findings (fixed-and-verified, or dismissed) into every later round's prompts.
// Open findings are deliberately excluded — injecting them biases reviewers.

test("LEDGER-007: round 3's history carries a round-1 finding, not just round 2's", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Round one bug")], resolutions: [R("P0-001")] },
    { findings: [F("P1-002", "P1", "Round two bug")], resolutions: [R("P1-002")] },
    { findings: [] },
  ]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  const r2history = ctx.promptByLabel["history:r2"];
  assert.match(r2history, /Round one bug/, "the round-1 finding must survive into the round-2 history file");
  assert.match(r2history, /Round two bug/, "the round-2 finding is there too");
  assert.match(r2history, /ADJUDICATED-FINDINGS LEDGER/);
});

test("LEDGER-008: a fix that did not hold is NOT presented as adjudicated", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Persistent bug")], resolutions: [R("P0-001")] },
    { findings: [F("P0-001", "P0", "Persistent bug")], resolutions: [R("P0-001")] }, // recurs → stuck
  ]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  const r1history = ctx.promptByLabel["history:r1"] || "";
  assert.doesNotMatch(
    r1history,
    /LEDGER[\s\S]*Persistent bug/,
    "a fix contradicted by the next round must not be labelled adjudicated",
  );
});

test("LEDGER-009: the reviewer prompt carries the do-not-re-litigate instruction", async () => {
  // Round 3 is the first round with a non-empty ledger (adjudication lags one
  // round), so it is the first round that carries the standing rule.
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] },
    { findings: [F("P1-002", "P1", "Bug Y")], resolutions: [R("P1-002")] },
    { findings: [] },
  ]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  const r3prompt = ctx.promptByLabel["review:r1:r3"];
  assert.match(r3prompt, /do not re-litigate/i);
  assert.match(r3prompt, /regression/i, "a regression of a ledger entry is a NEW finding");
});

test("LEDGER-010: convergence, round counting and the min-2 floor are unchanged", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.outcome.round, 2);
  assert.equal(out.rounds, 2);
});

test("LEDGER-011: runLoop returns the accumulated ledger for the caller", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.ok(Array.isArray(out.ledger), "ledger is always an array");
  assert.deepEqual(out.ledger.map((e) => e.title), ["Bug X"]);
  assert.equal(out.ledger[0].resolution, "fixed");
});

// ── LEDGER-012..014: review hardening (PR #40) ──────────────────────────────

test("LEDGER-012: when the history write fails, the ledger is embedded INLINE in the prompt", async () => {
  // The inline embed is the ONLY ledger carrier on the fallback path. Without
  // this test it survives deletion in mutation testing: the standing rule would
  // still point reviewers at a ledger that silently vanished.
  const ctx = makeCtx(
    [
      { findings: [F("P0-001", "P0", "Round one bug")], resolutions: [R("P0-001")] },
      { findings: [F("P1-002", "P1", "Round two bug")], resolutions: [R("P1-002")] },
      { findings: [] },
    ],
    { historyWriteFails: true },
  );
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  const r3prompt = ctx.promptByLabel["review:r1:r3"];
  assert.match(r3prompt, /ADJUDICATED-FINDINGS LEDGER/, "ledger body must be embedded inline");
  assert.match(r3prompt, /Round one bug/, "the round-1 adjudicated finding is carried inline");
});

test("LEDGER-013: a spot-fix the spot-check says did NOT land is kept out of the ledger", async () => {
  // The engine must never ledger a fix as 'fixed' while holding affirmative
  // evidence it did not land.
  const ctx = makeCtx(
    [
      { findings: [F("P2-001", "P2", "Cosmetic nit")], spotResolutions: [R("P2-001")] },
      { findings: [] },
    ],
    { notApplied: ["P2-001"] },
  );
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.deepEqual(out.ledger, [], "a fix contradicted by the spot-check is not adjudicated");
});

test("LEDGER-013b: a spot-fix the spot-check confirms DOES reach the ledger", async () => {
  const ctx = makeCtx([
    { findings: [F("P2-001", "P2", "Cosmetic nit")], spotResolutions: [R("P2-001")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.deepEqual(out.ledger.map((e) => e.title), ["Cosmetic nit"]);
});

test("LEDGER-014: round 2 gets NO standing rule — its ledger is always empty", async () => {
  // Adjudication lags one round, so at round 2 there is nothing settled yet.
  // Announcing a LEDGER section that does not exist is a false pointer.
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] },
    { findings: [F("P1-002", "P1", "Bug Y")], resolutions: [R("P1-002")] },
    { findings: [] },
  ]);
  await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.doesNotMatch(
    ctx.promptByLabel["review:r1:r2"],
    /ADJUDICATED-FINDINGS LEDGER/,
    "round 2 must not advertise a ledger it does not have",
  );
  assert.match(
    ctx.promptByLabel["review:r1:r3"],
    /ADJUDICATED-FINDINGS LEDGER/,
    "round 3 does have one, so the rule appears",
  );
});

// ═════════════════════════════════════════════════════════════════════════════
// claude-skills#82 / this repo #45 — proportional cost and a real stopping rule.
//
// Every assertion below is an acceptance criterion from #82, driven end to end
// through runLoop with mocked agents.
// ═════════════════════════════════════════════════════════════════════════════

// A diff probe payload: `n` touched lines in an artifact of `lines` lines.
const DIFF = (n, lines = 400, section = "") => ({
  artifact_lines: lines,
  touched: Array.from({ length: n }, (_, i) => ({ text: `reworded phrase ${i}`, section })),
});
const diffLabels = (ctx) => ctx.calls.filter((l) => l.startsWith("diff:"));

// ── Deterministic checks run BEFORE agentic ones ─────────────────────────────

test("STOP-100: a failing test gate claims the round — zero reviewer fan-out, straight to the fixer", async () => {
  const ctx = makeCtx([
    { testFailures: [F("P0-t01", "P0", "test_pricing fails")], resolutions: [R("P0-t01")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(reviewersInRound(ctx, 1).length, 0, "a defect a test can name must not cost a reviewer round");
  assert.equal(labelsWith(ctx, "fix:r1").length, 1, "the fixer still gets the gate's work list");
  assert.equal(reviewersInRound(ctx, 2).length, 2, "the gate passes in round 2, so the lenses run");
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.budget.gateRounds, 1);
  assert.equal(out.budget.fullRounds, 1);
  assert.equal(out.history[0].kind, "gate");
});

test("STOP-101: gate-only rounds are bounded — a third failing gate reviews anyway", async () => {
  const ctx = makeCtx([
    { testFailures: [F("P0-t01", "P0", "fail A")], resolutions: [R("P0-t01")] },
    { testFailures: [F("P0-t02", "P0", "fail B")], resolutions: [R("P0-t02")] },
    { testFailures: [F("P0-t03", "P0", "fail C")], findings: [], resolutions: [R("P0-t03")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 6 }, ctx);
  assert.equal(reviewersInRound(ctx, 1).length, 0);
  assert.equal(reviewersInRound(ctx, 2).length, 0);
  assert.equal(reviewersInRound(ctx, 3).length, 2, "a permanently-red suite must not starve review");
  assert.equal(out.budget.gateRounds, 2, "maxGateRounds caps consecutive gate rounds at 2");
  assert.equal(out.outcome.status, "converged");
});

test("STOP-102: maxGateRounds:0 disables the short-circuit entirely", async () => {
  const ctx = makeCtx([
    { testFailures: [F("P0-t01", "P0", "fail A")], findings: [], resolutions: [R("P0-t01")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxGateRounds: 0 }, ctx);
  assert.equal(reviewersInRound(ctx, 1).length, 2, "the lenses run alongside the failing gate, as before");
  assert.equal(out.budget.gateRounds, 0);
});

// ── Proportional rounds: a small contract-safe batch buys a delta verifier ────

test("STOP-110: a small, contract-safe P1 batch is verified WITHOUT a full all-lens re-read", async () => {
  const ctx = makeCtx([
    { findings: [F("P1-001", "P1", "Awkward wording")], resolutions: [R("P1-001")], diff: DIFF(3) },
    { verifyFindings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(labelsWith(ctx, "verify:r2").length, 1, "round 2 is a single delta verifier");
  assert.equal(reviewersInRound(ctx, 2).length, 0, "no full fan-out for a wording fix");
  assert.equal(labelsWith(ctx, "tests:r2").length, 0, "no test gate in a delta round");
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.budget.deltaRounds, 1);
  assert.equal(out.history[1].delta_reason, "eligible");
});

test("STOP-111: the SAME batch touching an acceptance line earns a full round", async () => {
  const ctx = makeCtx([
    {
      findings: [F("P1-001", "P1", "Awkward wording")],
      resolutions: [R("P1-001")],
      diff: { artifact_lines: 400, touched: [{ text: "  - Acceptance: the gate fails", section: "" }] },
    },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(reviewersInRound(ctx, 2).length, 2, "acceptance text is the contract a builder implements from");
  assert.equal(labelsWith(ctx, "verify:").length, 0);
  assert.equal(out.history[1].delta_reason, "contract-line:acceptance");
  assert.equal(out.budget.deltaRounds, 0);
});

test("STOP-112: a 25-line batch is over the cap and earns a full round", async () => {
  const ctx = makeCtx([
    { findings: [F("P1-001", "P1", "Restructure the section")], resolutions: [R("P1-001")], diff: DIFF(25, 10000) },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(reviewersInRound(ctx, 2).length, 2);
  assert.equal(out.history[1].delta_reason, "size-lines");
});

test("STOP-113: the bookend rule — delta, full, never delta, delta", async () => {
  const ctx = makeCtx([
    { findings: [F("P1-001", "P1", "Wording A")], resolutions: [R("P1-001")], diff: DIFF(3) },
    { verifyFindings: [F("P1-002", "P1", "Wording B")], resolutions: [R("P1-002")], diff: DIFF(3) },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(labelsWith(ctx, "verify:r2").length, 1, "round 2 is delta");
  assert.equal(diffLabels(ctx).includes("diff:r2"), false, "a delta round's batch is never even measured");
  assert.equal(reviewersInRound(ctx, 3).length, 2, "round 3 is FULL — drift stays one small batch deep");
  assert.equal(out.history.map((h) => h.kind).join(","), "full,delta,full");
});

test("STOP-114: a delta round that surfaces ANY finding re-opens the full loop", async () => {
  const ctx = makeCtx([
    { findings: [F("P1-001", "P1", "Wording")], resolutions: [R("P1-001")], diff: DIFF(3) },
    { verifyFindings: [F("P3-001", "P3", "A nit the verifier caught")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.rounds, 3, "the delta round must not converge on a finding of any severity");
  assert.equal(reviewersInRound(ctx, 3).length, 2);
  assert.equal(out.outcome.status, "converged");
});

test("STOP-115: a batch containing a P0 is disqualified in JS — the probe never spawns", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Real bug")], resolutions: [R("P0-001")], diff: DIFF(3) },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.deepEqual(diffLabels(ctx), [], "predicate 1 is checked before any agent is paid for");
  assert.equal(reviewersInRound(ctx, 2).length, 2);
  assert.equal(out.history[1].delta_reason, "p0-in-batch");
});

test("STOP-116: an unusable diff probe fails closed to a full round", async () => {
  const ctx = makeCtx([
    { findings: [F("P1-001", "P1", "Wording")], resolutions: [R("P1-001")] }, // no `diff` → probe returns null
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.deepEqual(diffLabels(ctx), ["diff:r1"], "the probe ran");
  assert.equal(reviewersInRound(ctx, 2).length, 2, "and its silence bought nothing");
  assert.equal(out.history[1].delta_reason, "probe-unavailable");
});

// ── The stopping rule: divergence halts instead of running the budget out ─────

test("STOP-120: the 19-round shape halts at the warmup and escalates with SPLIT", async () => {
  // pm-816-intake-0903: a genuinely NEW P0 every round, so stuck detection (which
  // matches an IDENTICAL P0/P1 set) never fired and the run reached 19 rounds.
  const rounds = Array.from({ length: 12 }, (_, i) => ({
    findings: [F("P0-001", "P0", `Bug ${i + 1}`)],
    resolutions: [R("P0-001")],
  }));
  const ctx = makeCtx(rounds);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 12 }, ctx);
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /SPLIT/);
  assert.equal(out.rounds, 6, "halts at the warmup, not at the 12-round budget");
  assert.equal(out.outcome.divergence.diverging, true);
  assert.equal(labelsWith(ctx, "fix:r6").length, 0, "a diverging round does not also pay for a fix batch");
});

test("STOP-121: a decaying finding rate is left alone to converge", async () => {
  const many = (n, tag) => ({
    findings: Array.from({ length: n }, (_, i) => F(`P0-00${i + 1}`, "P0", `${tag}-${i}`)),
    resolutions: Array.from({ length: n }, (_, i) => R(`P0-00${i + 1}`)),
  });
  const ctx = makeCtx([many(3, "a"), many(3, "b"), many(3, "c"), many(1, "d"), many(1, "e"), many(1, "f"), { findings: [] }]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 12 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.rounds, 7, "3,3,3 then 1,1,1 is decay — the halt must not fire on it");
});

// ── #81 coordination: an INVALID round is not progress ───────────────────────

test("STOP-125: invalid rounds spend no round budget (#81)", async () => {
  const rounds = Array.from({ length: 8 }, (_, i) => ({
    findings: [F("P0-001", "P0", `Bug ${i + 1}`)],
    resolutions: [R("P0-001")],
  }));
  const ctx = makeCtx(rounds);
  const out = await runLoop(
    {
      artifact: "a", requirements: "r", team: TEAM, threshold: 0,
      maxRounds: 3, maxInvalidRounds: 5,
      // Stand in for the quorum gate: rounds 1 and 2 lost their reviewer panel.
      validateRound: (rr) => rr.round > 2,
    },
    ctx,
  );
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /Max rounds \(3\)/);
  assert.equal(out.rounds, 5, "3 valid rounds were still owed after 2 dead ones");
  assert.equal(out.budget.validRounds, 3);
  assert.equal(out.budget.invalidRounds, 2);
});

test("STOP-126: too many invalid rounds escalate on the ENVIRONMENT, not the artifact (#81)", async () => {
  const rounds = Array.from({ length: 8 }, (_, i) => ({
    findings: [F("P0-001", "P0", `Bug ${i + 1}`)],
    resolutions: [R("P0-001")],
  }));
  const ctx = makeCtx(rounds);
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 2, validateRound: () => false },
    ctx,
  );
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /Environment/);
  assert.match(out.outcome.reason, /proves nothing about the artifact/);
  assert.equal(out.budget.validRounds, 0, "a flaky panel must never read as convergence OR as a spent budget");
});

test("STOP-127: an invalid round cannot fabricate divergence (#81)", async () => {
  const rounds = Array.from({ length: 10 }, (_, i) => ({
    findings: [F("P0-001", "P0", `Bug ${i + 1}`)],
    resolutions: [R("P0-001")],
  }));
  const ctx = makeCtx(rounds);
  // Only rounds 1,3,5,7 are valid, so after 7 rounds just 4 valid ones exist —
  // one short of the 6-round warmup, so the halt must stay silent.
  const out = await runLoop(
    {
      artifact: "a", requirements: "r", team: TEAM, threshold: 0,
      maxRounds: 4, maxInvalidRounds: 9, validateRound: (rr) => rr.round % 2 === 1,
    },
    ctx,
  );
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /Max rounds \(4\)/, "the budget ran out; divergence never fired");
});

// ── Cost visible in the verdict ──────────────────────────────────────────────

test("STOP-130: the verdict carries rounds by kind, reviewer counts and wall clock", async () => {
  const ctx = makeCtx([
    { testFailures: [F("P1-t01", "P1", "ruff: unused import")], resolutions: [R("P1-t01")] },
    { findings: [F("P1-001", "P1", "Wording")], resolutions: [R("P1-001")], diff: DIFF(3) },
    { verifyFindings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.deepEqual(
    { ...out.budget, wallClockMs: undefined },
    {
      maxRounds: 5, roundsRun: 3, validRounds: 3, invalidRounds: 0,
      fullRounds: 1, deltaRounds: 1, gateRounds: 1,
      maxInvalidRounds: 5, hardCap: 10, wallClockMs: undefined,
    },
  );
  assert.equal(typeof out.budget.wallClockMs, "number");
  assert.ok(out.history.every((h) => typeof h.ms === "number"));
  // The reviewer counts the quorum gate needs are recorded on every round (#81).
  // The gate round asks for no reviewers (0/0); the full round fans out to both
  // lenses (2/2); the delta round's single verifier IS its panel, so it attests
  // 1/1 — recording it as 0/0 would leave a dead verifier invisible to the gate.
  assert.deepEqual(out.history.map((h) => `${h.reviewers_returned}/${h.reviewers_requested}`), ["0/0", "2/2", "1/1"]);
});

test("STOP-103: single-round (qreview) mode never lets the gate claim the round", async () => {
  // qreview promises one clean-context diagnose pass. A red suite must not turn
  // that into "here are your test failures, no reviewer read the artifact".
  const ctx = makeCtx([{ testFailures: [F("P0-t01", "P0", "suite is red")], findings: [F("P1-001", "P1", "Real finding")] }]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, rounds: 1 }, ctx);
  assert.equal(reviewersInRound(ctx, 1).length, 2, "the lenses run even with a failing gate");
  assert.equal(out.budget.gateRounds, 0);
  assert.equal(out.final_counts.P1, 1, "the reviewer's finding is in the result");
});

// ---------------------------------------------------------------------------
// #81 — reviewer attestation + the quorum gate.
//
// Both false-GREEN incidents on record are replayed here: 29 of 32 review agents
// dead on a usage limit with the loop returning converged over a broken artifact
// (2026-08), and both reviewers dead on `Login expired` with only the spot-fixer
// alive (Quark, 2026-09-02, $3.85, five findings untouched). A dead reviewer and
// a reviewer that found nothing must never be the same thing.
// ---------------------------------------------------------------------------

const reviewerName = (label) => (label.match(/^review:(.+):r\d+$/) || [])[1] ?? "";
const TEAM32 = Array.from({ length: 32 }, (_, i) => ({
  name: `r${i + 1}`, model: "sonnet", review_lens: `lens-${i + 1}`,
}));

test("QUORUM-001 (#81): an all-dead reviewer round is INVALID, never converged", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }], {
    reviewerOutcome: () => "throw:Login expired",
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 1 },
    ctx,
  );
  assert.notEqual(out.outcome.status, "converged", "zero findings from a dead panel is not convergence");
  assert.equal(out.outcome.status, "escalated");
  assert.equal(out.history[0].valid, false);
  assert.equal(out.history[0].reviewers_requested, 2);
  assert.equal(out.history[0].reviewers_returned, 0);
  assert.match(out.outcome.reason, /Login expired/, "the environmental reason must reach the verdict");
  assert.deepEqual(labelsWith(ctx, "fix:"), [], "no fixer may run under a dead panel");
  assert.deepEqual(labelsWith(ctx, "spotfix:"), [], "no spot-fixer may run under a dead panel");
});

test("QUORUM-002 (#81): 29 of 32 reviewers dead is below quorum — the 2026-08 incident shape", async () => {
  const dead = new Set(TEAM32.slice(0, 29).map((t) => t.name));
  const ctx = makeCtx([{ findings: [] }], {
    reviewerOutcome: (label) => (dead.has(reviewerName(label)) ? "throw:usage limit reached" : undefined),
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM32, threshold: 0, maxRounds: 5, maxInvalidRounds: 1 },
    ctx,
  );
  assert.notEqual(out.outcome.status, "converged");
  assert.equal(out.history[0].valid, false, "3 of 32 survivors is not a panel");
  assert.equal(out.history[0].reviewers_returned, 3);
  assert.equal(out.history[0].reviewers_requested, 32);
  assert.equal(out.history[0].reviewers_quorum, 16);
  assert.match(out.outcome.reason, /usage limit reached/);
});

test("QUORUM-003 (#81): the Quark shape — both reviewers dead, fixer alive — is INVALID and names why", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }], {
    reviewerOutcome: (label) => (label.startsWith("review:") ? "throw:Login expired" : undefined),
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 2 },
    ctx,
  );
  assert.notEqual(out.outcome.status, "converged");
  assert.match(out.outcome.reason, /Login expired/);
  assert.deepEqual(
    out.history[0].reviewers_missing.map((m) => `${m.name}: ${m.reason}`),
    ["r1: Login expired", "r2: Login expired"],
  );
});

test("QUORUM-004 (#81): a below-quorum round never reaches the spot-fixer with its partial findings", async () => {
  // One survivor of four reports a trivial nit. Under the old code that nit was
  // spot-fixed and the round read clean; the panel that would have caught the
  // real defects never ran, so nothing here may be acted on.
  const team4 = Array.from({ length: 4 }, (_, i) => ({ name: `r${i + 1}`, model: "sonnet", review_lens: "x" }));
  const ctx = makeCtx([{ findings: [F("P3-001", "P3", "Cosmetic nit")] }], {
    reviewerOutcome: (label) => (reviewerName(label) === "r1" ? undefined : "throw:Login expired"),
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: team4, threshold: 0, maxRounds: 5, maxInvalidRounds: 1 },
    ctx,
  );
  assert.equal(out.history[0].valid, false);
  assert.equal(out.history[0].reviewers_returned, 1);
  assert.deepEqual(labelsWith(ctx, "spotfix:"), [], "partial findings from a dead panel are not a work list");
  assert.notEqual(out.outcome.status, "converged");
});

test("QUORUM-005 (#81): a healthy round converges exactly as before, verdict carrying returned/requested", async () => {
  const ctx = makeCtx([
    { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.outcome.round, 2);
  assert.match(out.outcome.message, /reviewers 2\/2 returned/);
  assert.equal(out.outcome.reviewers.returned, 2);
  assert.equal(out.outcome.reviewers.requested, 2);
  assert.equal(out.history[1].valid, true);
});

test("QUORUM-006 (#81): one dead of two is below quorum (majority, floor 2)", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }], {
    reviewerOutcome: (label) => (reviewerName(label) === "r2" ? "throw:session killed" : undefined),
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 1 },
    ctx,
  );
  assert.notEqual(out.outcome.status, "converged");
  assert.equal(out.history[0].valid, false);
  assert.match(out.outcome.reason, /session killed/);
});

test("QUORUM-007 (#81): a reviewer that returns nothing at all counts as missing, not as clean", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }], { reviewerOutcome: () => "null" });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 1 },
    ctx,
  );
  assert.notEqual(out.outcome.status, "converged");
  assert.equal(out.history[0].reviewers_returned, 0);
  assert.match(out.outcome.reason, /no result/i);
});

test("QUORUM-008 (#81): an invalid round spends no round budget and the recovered panel converges", async () => {
  const ctx = makeCtx(
    [
      { findings: [] },
      { findings: [F("P0-001", "P0", "Bug X")], resolutions: [R("P0-001")] },
      { findings: [] },
    ],
    { reviewerOutcome: (label, r) => (r === 1 ? "throw:Login expired" : undefined) },
  );
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 3, maxInvalidRounds: 2 },
    ctx,
  );
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.budget.invalidRounds, 1);
  assert.equal(out.budget.validRounds, 2);
});

test("QUORUM-009 (#81): the min-2-rounds floor counts VALID rounds, not attempts", async () => {
  // Round 1's panel dies, round 2 is clean. Converging at round 2 would rest the
  // whole verdict on a single valid round — the floor exists to prevent exactly that.
  const ctx = makeCtx([{ findings: [] }, { findings: [] }, { findings: [] }], {
    reviewerOutcome: (label, r) => (r === 1 ? "throw:Login expired" : undefined),
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 2 },
    ctx,
  );
  assert.equal(out.outcome.status, "converged");
  assert.equal(out.outcome.round, 3, "rounds 2 and 3 are the two valid rounds");
});

test("QUORUM-010 (#81): a dead verifier on a proportional round is INVALID too", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }, { findings: [] }], {
    reviewerOutcome: (label) => (label.startsWith("verify:") ? "throw:Login expired" : undefined),
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 1 },
    ctx,
  );
  assert.equal(out.history[1].kind, "delta", "round 2 is the proportional verifier round");
  assert.equal(out.history[1].valid, false);
  assert.equal(out.history[1].reviewers_requested, 1);
  assert.equal(out.history[1].reviewers_returned, 0);
  assert.notEqual(out.outcome.status, "converged");
});

test("QUORUM-011 (#81): a deterministic gate round asks for no reviewers and stays valid", async () => {
  const ctx = makeCtx([
    { testFailures: [F("P0-t1", "P0", "Suite red")], resolutions: [R("P0-t1")] },
    { findings: [] },
    { findings: [] },
  ]);
  const out = await runLoop({ artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5 }, ctx);
  assert.equal(out.history[0].kind, "gate");
  assert.equal(out.history[0].reviewers_requested, 0);
  assert.equal(out.history[0].valid, true, "quorum gates reviewer panels, not gate rounds");
  assert.equal(out.outcome.status, "converged");
});

test("QUORUM-012 (#81): the validateRound hook can still invalidate, but cannot validate a dead panel", async () => {
  const ctx = makeCtx([{ findings: [] }, { findings: [] }], {
    reviewerOutcome: () => "throw:Login expired",
  });
  const out = await runLoop(
    {
      artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 5, maxInvalidRounds: 1,
      validateRound: () => true,
    },
    ctx,
  );
  assert.equal(out.history[0].valid, false, "the quorum gate is not overridable from config");
  assert.notEqual(out.outcome.status, "converged");
});

test("QUORUM-013 (#81): the run never ends with a null outcome, even when every round is invalid", async () => {
  // maxInvalidRounds:0 disables the environment escalation; the hard cap must
  // still produce a verdict, because a null outcome reads downstream as neither
  // converged nor escalated — the same silence this issue exists to kill.
  const ctx = makeCtx([{ findings: [] }, { findings: [] }, { findings: [] }], {
    reviewerOutcome: () => "throw:Login expired",
  });
  const out = await runLoop(
    { artifact: "a", requirements: "r", team: TEAM, threshold: 0, maxRounds: 2, maxInvalidRounds: 0 },
    ctx,
  );
  assert.ok(out.outcome, "a run must always carry a verdict");
  assert.equal(out.outcome.status, "escalated");
  assert.match(out.outcome.reason, /valid reviewer panel|Login expired/);
});
