// Escalation broker (Phase D of /qpipeline auto).
//
// Every "need a human" moment in the autonomous pipeline funnels through here.
// This module is the drift-locked, PURE decision logic (no I/O, no agent calls):
// it classifies an escalation event, builds a valid proposed-action for qdecide's
// validate-proposal.py, interprets qdecide's exit code, and — honoring the settled
// decisions — resolves what the pipeline should do next.
//
// The load-bearing invariant (also in the SKILL): qdecide is advisory / draft-only.
// It can only authorize CONTINUATION OF REVERSIBLE INTERNAL WORK. Anything in the
// irreversible / external / spend triad routes to a human gate no matter what
// qdecide says; a `decline` (and any fail-safe) always hard-stops.
//
// The workflow layer (Phase E) shells validate-proposal.py from a thin Haiku
// agent() and feeds the exit code to mapRecommendation/resolveEscalation. Kept as
// a pure library so it is fully unit-testable and inlinable into the sandbox.

// Canonical event taxonomy → the qdecide-facing shape. `category` drives routing;
// `mustHardStop` fires for the triad {irreversible, external, spend}.
const EVENT_TYPES = {
  // Reversible internal engineering work — the only class qdecide may authorize.
  "converge": { category: "reversible-internal", domain: "engineering", audience: "internal", irreversibility: "reversible" },
  "integration-fail": { category: "reversible-internal", domain: "engineering", audience: "internal", irreversibility: "reversible" },
  "staging-deploy": { category: "reversible-internal", domain: "engineering", audience: "internal", irreversibility: "reversible" },
  // Irreversible — qdecide structurally never returns `act` (H-010); human-gated.
  "prod-deploy": { category: "irreversible", domain: "engineering", audience: "internal", irreversibility: "irreversible" },
  "merge-main": { category: "irreversible", domain: "engineering", audience: "internal", irreversibility: "irreversible" },
  // External — leaves the building; human-gated.
  "external-publish": { category: "external", domain: "content", audience: "public", irreversibility: "sticky" },
  "external-comms": { category: "external", domain: "communication", audience: "client-facing", irreversibility: "sticky" },
  // Real-money spend — human-gated.
  "spend": { category: "spend", domain: "finance", audience: "internal", irreversibility: "sticky" },
  // Genuinely ambiguous — routes to the qescalate council / human, never auto-acts.
  "ambiguous-requirements": { category: "ambiguous", domain: "engineering", audience: "internal", irreversibility: "reversible" },
};

// Unknown event types are conservatively ambiguous — never silently auto-proceedable.
const UNKNOWN = { category: "ambiguous", domain: "engineering", audience: "internal", irreversibility: "reversible" };

const HARD_STOP_CATEGORIES = new Set(["irreversible", "external", "spend"]);

/**
 * Map a raw escalation event to its qdecide-facing classification.
 * @returns {{category, domain, audience, irreversibility}}
 */
export function classifyEvent(event) {
  const type = (event && event.type) || "";
  return { ...(EVENT_TYPES[type] || UNKNOWN) };
}

/**
 * True when qdecide can never authorize the action on its own — the
 * irreversible / external / spend triad. Accepts a raw event or a classification.
 */
export function mustHardStop(eventOrClassification) {
  const category = eventOrClassification && eventOrClassification.category
    ? eventOrClassification.category
    : classifyEvent(eventOrClassification).category;
  return HARD_STOP_CATEGORIES.has(category);
}

/**
 * Build a valid proposed-action (schema/proposed-action.schema.json) to pipe into
 * validate-proposal.py. Pure — the caller shells the validator.
 */
export function buildProposal(event) {
  const c = classifyEvent(event);
  const reason = (event && (event.reason || event.context)) || "";
  const financial = typeof (event && event.amount) === "number" ? event.amount : "n/a";

  const proposal = {
    action: (event && event.action) || `Autonomous pipeline: ${(event && event.type) || "event"}`,
    domain: c.domain,
    audience: c.audience,
    context: reason || `Escalation raised for a ${c.category} ${(event && event.type) || "event"}.`,
    stake_estimate: {
      financial,
      time: "low",
      relational: "n/a",
      reputational: c.audience === "public" ? "high" : "n/a",
      irreversibility: c.irreversibility,
    },
  };
  if (event && event.draft) proposal.draft_payload = event.draft;
  return proposal;
}

/**
 * Interpret validate-proposal.py's exit code. 0=act, 1=draft, 2=decline; any other
 * value (error / timeout / missing binary) FAILS SAFE to a declining hard-stop.
 */
export function mapRecommendation(exitCode) {
  if (exitCode === 0) return { recommendation: "act", action: "proceed" };
  if (exitCode === 1) return { recommendation: "draft", action: "proceed-and-stage" };
  if (exitCode === 2) return { recommendation: "decline", action: "hard-stop" };
  return { recommendation: "decline", action: "hard-stop", failsafe: true };
}

/**
 * The combiner the workflow calls: given an event and qdecide's exit code, resolve
 * the pipeline's next action, honoring the advisory-only invariant.
 *   - decline / fail-safe        → hard-stop (always blocks)
 *   - reversible-internal + act  → proceed
 *   - reversible-internal + draft→ proceed-and-stage
 *   - anything else (triad or ambiguous) + act/draft → human-gate
 */
export function resolveEscalation(event, exitCode) {
  const c = classifyEvent(event);
  const rec = mapRecommendation(exitCode);
  const base = { recommendation: rec.recommendation, category: c.category, hardStop: mustHardStop(c) };
  if (rec.failsafe) base.failsafe = true;

  if (rec.recommendation === "decline") return { ...base, action: "hard-stop" };
  if (c.category === "reversible-internal") return { ...base, action: rec.action };
  return { ...base, action: "human-gate" };
}
