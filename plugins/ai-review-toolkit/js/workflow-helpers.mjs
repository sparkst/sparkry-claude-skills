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

// ---------------------------------------------------------------------------
// Adjudicated-findings ledger
//
// Reviewers are clean-context BY DESIGN — fresh eyes catch bugs a primed
// reviewer rationalizes away. But before this, only round N-1's findings reached
// round N, so by round 3 the earlier rounds were simply gone. A production run
// (2026-08-01) spent 5 rounds re-litigating geometry round 1 had already settled
// while each new fix introduced a new P1: "clean context" had degraded into
// amnesia.
//
// The ledger is the narrow fix: a CUMULATIVE record of findings whose resolution
// is SETTLED, carried into every later round. It deliberately excludes anything
// open — telling a fresh reviewer "the previous round thinks X is broken" primes
// them to confirm X, which is exactly the bias clean context exists to avoid.
// ---------------------------------------------------------------------------

/** Normalized title — the identity key for a finding across rounds. */
function ledgerKey(x) {
  return String(x.title ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

/**
 * Decide which of a round's findings are SETTLED and belong in the ledger.
 *
 * A finding is admitted only when BOTH hold:
 *   1. the fixer returned a `FIXED` resolution for its id (an `ESCALATED` one is
 *      an open question, not a settled decision), and
 *   2. the NEXT round's reviewers did not re-raise the same normalized title —
 *      i.e. the fix demonstrably held. A claimed-but-contradicted fix must never
 *      be labelled "do not re-litigate".
 *
 * `nextRoundFindings` is what makes (2) checkable, so a round is adjudicated one
 * round LATE — round r's entries are admitted when round r+1's findings are known.
 *
 * `resolution` is currently always "fixed" — the only adjudication the engine can
 * make automatically. The field is a string (not a boolean) so a future
 * dismissed-with-evidence path (a reviewer finding ruled invalid rather than
 * repaired) can emit "dismissed" without changing the ledger shape or renderer.
 *
 * @returns ledger entries: {id, round, severity, title, summary, file, resolution, resolved_by, evidence}
 */
export function adjudicateRound({
  round,
  findings = [],
  resolutions = [],
  nextRoundFindings = [],
}) {
  const fixedById = new Map();
  for (const res of resolutions) {
    if (String(res?.status ?? "").toUpperCase() === "FIXED") {
      fixedById.set(String(res.finding_id ?? ""), res);
    }
  }

  const stillLive = new Set(nextRoundFindings.map(ledgerKey));

  const entries = [];
  for (const f of findings) {
    const res = fixedById.get(String(f.id ?? ""));
    if (!res) continue; // open, or escalated → not settled
    if (stillLive.has(ledgerKey(f))) continue; // the fix did not hold
    entries.push({
      id: String(f.id ?? ""),
      round,
      severity: String(f.severity ?? ""),
      title: String(f.title ?? ""),
      summary: String(res.description ?? f.finding ?? ""),
      file: String(f.evidence ?? res.evidence ?? ""),
      resolution: "fixed",
      resolved_by: `round ${round} fixer`,
      evidence: String(res.evidence ?? ""),
    });
  }
  return entries;
}

/**
 * Accumulate new entries onto the running ledger, keyed by normalized title so
 * the same issue adjudicated twice collapses to its NEWEST adjudication rather
 * than appearing twice. Order follows first appearance; a replaced entry keeps
 * its original slot so the ledger reads chronologically.
 */
export function mergeLedger(ledger = [], entries = []) {
  const out = [...ledger];
  const indexByKey = new Map(out.map((e, i) => [ledgerKey(e), i]));
  for (const e of entries) {
    const key = ledgerKey(e);
    const at = indexByKey.get(key);
    if (at === undefined) {
      indexByKey.set(key, out.length);
      out.push(e);
    } else {
      out[at] = e;
    }
  }
  return out;
}

/**
 * Render the ledger as the prompt section injected into later rounds. Returns
 * "" for an empty ledger so callers never emit a dead heading.
 */
export function renderLedger(ledger = []) {
  if (!ledger.length) return "";

  const lines = [
    "## ADJUDICATED-FINDINGS LEDGER",
    "",
    "These findings were raised in PRIOR rounds and are already adjudicated —",
    "each was fixed, and a later round confirmed the fix held. Treat them as",
    "settled:",
    "",
    "- **Do NOT re-litigate them.** Re-raising a settled finding as though it were",
    "  new is the failure mode this ledger exists to prevent.",
    "- **DO verify the listed fixes actually held** at the cited evidence location.",
    "- **If a listed fix has regressed or was undone, report it as a NEW finding**",
    "  with normal severity — a regression is a real bug, not a re-litigation.",
    "- This ledger is not a checklist of everything wrong with the artifact. Issues",
    "  it does not mention are still fully in scope for your review.",
    "",
  ];

  for (const e of ledger) {
    lines.push(`### ${e.id} (round ${e.round}, ${e.severity}): ${e.title}`);
    lines.push(`**Resolution:** ${e.resolution} — ${e.resolved_by}`);
    if (e.summary) lines.push(`**What was done:** ${e.summary}`);
    if (e.evidence) lines.push(`**Evidence:** ${e.evidence}`);
    else if (e.file) lines.push(`**Location:** ${e.file}`);
    lines.push("");
  }

  return lines.join("\n").replace(/\s+$/, "");
}

// ---------------------------------------------------------------------------
// Reviewer attestation + quorum (#81 / this repo #43)
//
// A review round is EVIDENCE only if the panel that was asked for actually
// reported. Before this, `reviews.filter(Boolean)` dropped every reviewer that
// failed to return, so a dead reviewer and a reviewer that found nothing were
// indistinguishable — and an all-dead round yielded zero findings, which the
// termination rule read as CONVERGED. That false GREEN shipped twice on record:
// 29 of 32 review agents died on a usage limit and the loop returned
// `converged:true` over a broken artifact (2026-08), and both reviewers died on
// `Login expired` while the surviving spot-fixer wrote a test that PINNED a known
// defect, all under a green verdict (Quark, 2026-09-02).
//
// So the count is never dropped: every requested reviewer is attested as returned
// or missing-with-a-reason, and the quorum decides whether the round counts.
// ---------------------------------------------------------------------------

/** A reviewer that produced nothing at all — the shape `filter(Boolean)` ate. */
export const REVIEWER_NO_RESULT = "returned no result (agent produced no output)";
/** A reviewer that answered with something that is not a findings list. */
export const REVIEWER_MALFORMED = "returned a malformed result (no findings array)";
/** A death whose cause the runtime did not name. */
export const REVIEWER_UNKNOWN_REASON = "failed for an unnamed reason";

// Reasons come from agent runtimes and can be long or multi-line; the verdict has
// to stay one readable line, so normalize and cap them.
function cleanReason(reason) {
  const s = String(reason ?? "").replace(/\s+/g, " ").trim();
  if (!s) return REVIEWER_UNKNOWN_REASON;
  return s.length > 240 ? `${s.slice(0, 237)}...` : s;
}

/**
 * How many reviewers must actually report for a round to count as evidence.
 *
 * A majority of the panel, with a floor of 2 (or the whole panel when only one
 * was asked for, as in a proportional verifier round). Majority — not a fixed
 * floor — is what makes the 29-of-32 shape INVALID: three survivors clear any
 * constant floor while 90% of the lenses are silent.
 */
export function reviewerQuorum(requested) {
  const n = Math.max(0, Math.trunc(Number(requested) || 0));
  if (n === 0) return 0;
  return Math.max(Math.min(2, n), Math.ceil(n / 2));
}

/**
 * Attest one round's reviewer panel.
 *
 * @param settled per-reviewer results in request order, each
 *   `{ name, ok: true, value }` or `{ name, ok: false, reason }`. The caller
 *   settles them (catching rejections) so one dead reviewer cannot abort the fan-out.
 * @returns { requested, returned, quorum, quorumMet, missing: [{name, reason}], lists }
 *   `lists` holds ONLY the findings of reviewers that genuinely reported, so
 *   synthesis never mixes a silence in with the evidence.
 */
export function attestReviewers(settled = []) {
  const attested = (settled ?? []).map((s, i) => {
    const name = String(s?.name ?? `reviewer-${i + 1}`);
    if (s && s.ok === false) return { name, returned: false, reason: cleanReason(s.reason) };
    const value = s ? s.value : undefined;
    if (value === null || value === undefined) return { name, returned: false, reason: REVIEWER_NO_RESULT };
    const findings = Array.isArray(value)
      ? value
      : Array.isArray(value.findings)
        ? value.findings
        : null;
    if (findings === null) return { name, returned: false, reason: REVIEWER_MALFORMED };
    return { name, returned: true, findings };
  });

  const requested = attested.length;
  const returned = attested.filter((a) => a.returned);
  const quorum = reviewerQuorum(requested);
  return {
    requested,
    returned: returned.length,
    quorum,
    // A round that asked for no reviewers (the deterministic gate round) has
    // nothing to attest and is valid on its own terms — quorum gates panels.
    quorumMet: requested === 0 ? true : returned.length >= quorum,
    missing: attested.filter((a) => !a.returned).map((a) => ({ name: a.name, reason: a.reason })),
    lists: returned.map((a) => a.findings),
  };
}

/**
 * The loud line. A reviewer that died environmentally names WHY, because
 * "0 findings" and "nobody looked" must never read the same to a human.
 */
export function describeReviewerShortfall(round, attestation) {
  const a = attestation ?? {};
  const why = (a.missing ?? []).length
    ? (a.missing ?? []).map((m) => `${m.name}: ${m.reason}`).join("; ")
    : "no reviewer reported";
  return (
    `Round ${round} INVALID — reviewer quorum not met: ${a.returned ?? 0}/${a.requested ?? 0} reviewers ` +
    `returned (quorum ${a.quorum ?? 0}). Failed reviewers — ${why}. Zero findings from a panel that did not ` +
    `run is absence of evidence, not evidence of absence: this round proves nothing and counts for nothing.`
  );
}

/** The attestation as it rides in the verdict string: `reviewers 2/2 returned`. */
export function renderAttestation(attestation) {
  const a = attestation ?? {};
  return `reviewers ${a.returned ?? 0}/${a.requested ?? 0} returned`;
}
