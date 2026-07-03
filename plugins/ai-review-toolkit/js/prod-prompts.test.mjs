import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildDeployPlanPrompt,
  buildStagingDeployPrompt,
  buildProdPublishPrompt,
  buildSmokeBatchPrompt,
  buildRollbackPrompt,
  planSmokeBatches,
  aggregateSmoke,
  buildGateState,
} from "./prod-prompts.mjs";

const TARGET = {
  kind: "cloudflare-worker",
  stagingCmd: "wrangler deploy --env staging",
  prodCmd: "wrangler deploy --env production",
  stagingUrl: "https://staging.example.dev",
  prodUrl: "https://example.dev",
  rollbackCmd: "wrangler rollback --env production",
  stateful: false,
};

// ── DEPLOY-PLAN author ────────────────────────────────────────────────────

test("deploy-plan prompt echoes declared commands, demands smoke-suite additions, forbids deploying", () => {
  const p = buildDeployPlanPrompt(TARGET, {
    requirementsPath: "REQUIREMENTS.md",
    designPath: "DESIGN.md",
    planPath: "DEPLOY-PLAN.md",
    suitePath: "smoke/prod.suite.json",
  });
  assert.match(p, /DEPLOY-PLAN\.md/);
  assert.match(p, /wrangler deploy --env staging/);
  assert.match(p, /wrangler deploy --env production/);
  assert.match(p, /smoke\/prod\.suite\.json/);
  assert.match(p, /NEW/); // must add its new smoke checks
  assert.match(p, /Do NOT deploy/i);
});

// ── staging deploy / prod publish ─────────────────────────────────────────

test("staging-deploy prompt runs only the staging command and never prod", () => {
  const p = buildStagingDeployPrompt(TARGET, { planPath: "DEPLOY-PLAN.md" });
  assert.match(p, /STAGING/);
  assert.match(p, /wrangler deploy --env staging/);
  assert.match(p, /Do NOT deploy to production/i);
  assert.ok(!p.includes("wrangler deploy --env production"), "staging deploy must not mention the prod command");
});

test("prod-publish prompt runs the prod command and flags irreversibility", () => {
  const p = buildProdPublishPrompt(TARGET, { planPath: "DEPLOY-PLAN.md" });
  assert.match(p, /PROD/i);
  assert.match(p, /wrangler deploy --env production/);
  assert.match(p, /irreversible/i);
});

// ── smoke batch ───────────────────────────────────────────────────────────

test("smoke-batch prompt lists every check id and pins the target url + environment", () => {
  const batch = [
    { id: "SMK-001", description: "home returns 200" },
    { id: "SMK-002", description: "login returns 200", assert: "status==200" },
  ];
  const p = buildSmokeBatchPrompt(batch, { url: "https://staging.example.dev", environment: "staging" });
  assert.match(p, /SMK-001/);
  assert.match(p, /SMK-002/);
  assert.match(p, /status==200/);
  assert.match(p, /https:\/\/staging\.example\.dev/);
  assert.match(p, /staging/);
  assert.match(p, /results/); // return shape
  assert.match(p, /Do NOT/i); // no fixing / no deploying
});

// ── rollback ───────────────────────────────────────────────────────────────

test("rollback prompt runs exactly the declared rollback command", () => {
  const p = buildRollbackPrompt(TARGET);
  assert.match(p, /ROLLBACK/i);
  assert.match(p, /wrangler rollback --env production/);
});

// ── builders tolerate missing fields ───────────────────────────────────────

test("builders don't throw on a bare/empty target", () => {
  assert.doesNotThrow(() => buildDeployPlanPrompt({}, {}));
  assert.doesNotThrow(() => buildStagingDeployPrompt(undefined, {}));
  assert.doesNotThrow(() => buildProdPublishPrompt(null, {}));
  assert.doesNotThrow(() => buildSmokeBatchPrompt([], {}));
  assert.doesNotThrow(() => buildRollbackPrompt({}));
});

// ── planSmokeBatches (JS mirror of prod-tail.py plan_smoke_batches) ─────────

test("planSmokeBatches chunks in order, exactly like the python core", () => {
  const checks = Array.from({ length: 10 }, (_, i) => `c${i}`);
  assert.deepEqual(planSmokeBatches(checks, 4), [
    ["c0", "c1", "c2", "c3"],
    ["c4", "c5", "c6", "c7"],
    ["c8", "c9"],
  ]);
});

test("planSmokeBatches handles 200+ checks and coerces a bad batch size to >=1", () => {
  const checks = Array.from({ length: 205 }, (_, i) => `c${i}`);
  const batches = planSmokeBatches(checks, 25);
  assert.equal(batches.reduce((n, b) => n + b.length, 0), 205);
  assert.ok(batches.every((b) => b.length <= 25));
  // batch size <= 0 must not divide-by-zero / infinite-loop.
  assert.equal(planSmokeBatches(["a", "b"], 0).length, 2);
});

// ── aggregateSmoke (JS mirror of prod-tail.py aggregate_smoke) ──────────────

test("aggregateSmoke is all-or-nothing and names failures", () => {
  assert.deepEqual(aggregateSmoke([{ id: "c1", passed: true }, { id: "c2", passed: true }]), {
    ok: true, total: 2, passed: 2, failed: [],
  });
  const bad = aggregateSmoke([{ id: "c1", passed: true }, { id: "c2", passed: false }]);
  assert.equal(bad.ok, false);
  assert.deepEqual(bad.failed, ["c2"]);
});

test("aggregateSmoke on zero checks is never a pass", () => {
  assert.equal(aggregateSmoke([]).ok, false);
  assert.equal(aggregateSmoke(undefined).ok, false);
});

// ── buildGateState (assembles the deploy_gate --state dict) ─────────────────

test("buildGateState maps facts into the deploy_gate schema", () => {
  const state = buildGateState({
    artifacts: [{ name: "REQUIREMENTS.md", p0: 0, p1: 0 }],
    unitGreen: true,
    integrationGreen: true,
    stagingSmoke: { total: 210, passed: 210, ok: true, failed: [] },
    deployTarget: TARGET,
    rollbackDryOk: true,
    prodSmokeReviewed: true,
    newSmokeChecksAdded: true,
    qdecideDecision: "draft",
    prodAutonomous: true,
  });
  assert.equal(state.unit_green, true);
  assert.equal(state.integration_green, true);
  assert.deepEqual(state.staging_smoke, { total: 210, passed: 210 });
  assert.equal(state.rollback_cmd_present, true); // TARGET has a rollbackCmd
  assert.equal(state.rollback_dry_ok, true);
  assert.equal(state.prod_smoke_reviewed, true);
  assert.equal(state.new_smoke_checks_added, true);
  assert.equal(state.qdecide_decision, "draft");
  assert.equal(state.prod_autonomous, true);
  assert.equal(state.human_confirmed, false);
});

test("buildGateState marks rollback absent when the target declares no rollbackCmd", () => {
  const state = buildGateState({ deployTarget: { kind: "npm", prodCmd: "npm publish" } });
  assert.equal(state.rollback_cmd_present, false);
  // everything defaults to a blocking value (never fail-open).
  assert.equal(state.unit_green, false);
  assert.equal(state.prod_autonomous, false);
  assert.deepEqual(state.staging_smoke, { total: 0, passed: 0 });
});
