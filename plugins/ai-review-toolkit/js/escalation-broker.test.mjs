import { test } from "node:test";
import assert from "node:assert/strict";
import {
  classifyEvent,
  mustHardStop,
  buildProposal,
  mapRecommendation,
  resolveEscalation,
} from "./escalation-broker.mjs";

// A convergence escalation as loop-engine.mjs actually emits it.
const CONVERGE_EVENT = {
  type: "converge",
  artifact: "DESIGN.md",
  reason: "Max rounds (4) reached without convergence.",
  unresolved: [{ id: "F1", severity: "P1", title: "n+1 query" }],
  round: 4,
};

// ── classifyEvent ────────────────────────────────────────────────────────

test("classifyEvent: a convergence escalation is reversible internal engineering work", () => {
  const c = classifyEvent(CONVERGE_EVENT);
  assert.equal(c.category, "reversible-internal");
  assert.equal(c.domain, "engineering");
  assert.equal(c.audience, "internal");
  assert.equal(c.irreversibility, "reversible");
});

test("classifyEvent: integration failure and staging deploy are reversible internal", () => {
  assert.equal(classifyEvent({ type: "integration-fail" }).category, "reversible-internal");
  assert.equal(classifyEvent({ type: "staging-deploy" }).category, "reversible-internal");
});

test("classifyEvent: prod deploy is irreversible", () => {
  const c = classifyEvent({ type: "prod-deploy" });
  assert.equal(c.category, "irreversible");
  assert.equal(c.irreversibility, "irreversible");
});

test("classifyEvent: merge to main is irreversible", () => {
  assert.equal(classifyEvent({ type: "merge-main" }).category, "irreversible");
});

test("classifyEvent: external publish is external + public content", () => {
  const c = classifyEvent({ type: "external-publish" });
  assert.equal(c.category, "external");
  assert.equal(c.domain, "content");
  assert.equal(c.audience, "public");
});

test("classifyEvent: external comms is external + client-facing communication", () => {
  const c = classifyEvent({ type: "external-comms" });
  assert.equal(c.category, "external");
  assert.equal(c.domain, "communication");
  assert.equal(c.audience, "client-facing");
});

test("classifyEvent: real-money spend is the spend category, finance domain", () => {
  const c = classifyEvent({ type: "spend", amount: 200 });
  assert.equal(c.category, "spend");
  assert.equal(c.domain, "finance");
});

test("classifyEvent: an unknown event type is treated as ambiguous, never silently auto-proceedable", () => {
  const c = classifyEvent({ type: "who-knows" });
  assert.equal(c.category, "ambiguous");
});

// ── mustHardStop ─────────────────────────────────────────────────────────

test("mustHardStop: true for the irreversible / external / spend triad", () => {
  for (const type of ["prod-deploy", "merge-main", "external-publish", "external-comms", "spend"]) {
    assert.equal(mustHardStop({ type }), true, `${type} must hard-stop`);
  }
});

test("mustHardStop: false for reversible internal work", () => {
  for (const type of ["converge", "integration-fail", "staging-deploy"]) {
    assert.equal(mustHardStop({ type }), false, `${type} must not hard-stop`);
  }
});

test("mustHardStop: accepts an already-classified object", () => {
  assert.equal(mustHardStop({ category: "irreversible" }), true);
  assert.equal(mustHardStop({ category: "reversible-internal" }), false);
});

// ── buildProposal ────────────────────────────────────────────────────────

test("buildProposal: emits every field validate-proposal.py requires", () => {
  const p = buildProposal(CONVERGE_EVENT);
  for (const key of ["action", "domain", "stake_estimate", "context"]) {
    assert.ok(p[key] !== undefined && p[key] !== "", `missing required field ${key}`);
  }
  for (const axis of ["financial", "time", "relational", "reputational", "irreversibility"]) {
    assert.ok(p.stake_estimate[axis] !== undefined, `missing stake axis ${axis}`);
  }
});

test("buildProposal: the irreversibility axis mirrors the classification", () => {
  assert.equal(buildProposal(CONVERGE_EVENT).stake_estimate.irreversibility, "reversible");
  assert.equal(buildProposal({ type: "prod-deploy" }).stake_estimate.irreversibility, "irreversible");
});

test("buildProposal: carries the event reason into context so qdecide sees the real situation", () => {
  const p = buildProposal(CONVERGE_EVENT);
  assert.match(p.context, /Max rounds/);
});

test("buildProposal: a spend event with a numeric amount sets a numeric financial axis", () => {
  const p = buildProposal({ type: "spend", amount: 200, reason: "buy a domain" });
  assert.equal(p.domain, "finance");
  assert.equal(p.stake_estimate.financial, 200);
});

test("buildProposal: external comms carries the draft text into draft_payload", () => {
  const p = buildProposal({ type: "external-comms", draft: "Hi client, ...", reason: "scope reply" });
  assert.equal(p.audience, "client-facing");
  assert.equal(p.draft_payload, "Hi client, ...");
});

// ── mapRecommendation ────────────────────────────────────────────────────

test("mapRecommendation: 0/1/2 map to act/draft/decline", () => {
  assert.deepEqual(mapRecommendation(0), { recommendation: "act", action: "proceed" });
  assert.deepEqual(mapRecommendation(1), { recommendation: "draft", action: "proceed-and-stage" });
  assert.deepEqual(mapRecommendation(2), { recommendation: "decline", action: "hard-stop" });
});

test("mapRecommendation: any non-0/1/2 code fails safe to a declining hard-stop", () => {
  for (const bad of [undefined, null, NaN, 3, -1, 137, "1"]) {
    const r = mapRecommendation(bad);
    assert.equal(r.recommendation, "decline", `${String(bad)} should fail safe`);
    assert.equal(r.action, "hard-stop");
    assert.equal(r.failsafe, true);
  }
});

// ── resolveEscalation (the combiner the workflow calls) ──────────────────

test("resolveEscalation: reversible-internal + act → proceed autonomously", () => {
  assert.equal(resolveEscalation(CONVERGE_EVENT, 0).action, "proceed");
});

test("resolveEscalation: reversible-internal + draft → proceed-and-stage (decision #2, makes no-stopping real)", () => {
  const d = resolveEscalation(CONVERGE_EVENT, 1);
  assert.equal(d.action, "proceed-and-stage");
  assert.equal(d.recommendation, "draft");
});

test("resolveEscalation: any decline is a hard-stop", () => {
  assert.equal(resolveEscalation(CONVERGE_EVENT, 2).action, "hard-stop");
});

test("resolveEscalation: irreversible + act/draft routes to a human gate — qdecide can never authorize it", () => {
  assert.equal(resolveEscalation({ type: "prod-deploy" }, 0).action, "human-gate");
  assert.equal(resolveEscalation({ type: "prod-deploy" }, 1).action, "human-gate");
});

test("resolveEscalation: irreversible + decline still hard-stops (decline always blocks)", () => {
  assert.equal(resolveEscalation({ type: "prod-deploy" }, 2).action, "hard-stop");
});

test("resolveEscalation: a fail-safe exit code hard-stops even for a spend", () => {
  const d = resolveEscalation({ type: "spend", amount: 500 }, undefined);
  assert.equal(d.action, "hard-stop");
  assert.equal(d.failsafe, true);
});

test("resolveEscalation: ambiguous work never auto-proceeds — it goes to a human gate", () => {
  assert.equal(resolveEscalation({ type: "who-knows" }, 0).action, "human-gate");
});
