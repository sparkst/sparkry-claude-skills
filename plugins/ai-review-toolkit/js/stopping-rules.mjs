// Deterministic stopping rules for the convergence loop.
//
// Orchestration-only, like workflow-helpers.mjs: these have no Python oracle, so
// they live outside adjudication.mjs and are inlined into the generated workflow
// separately.
//
// WHY THIS FILE EXISTS (claude-skills#82, this repo #45). Two production runs on
// 2026-09-02/03 showed the loop had no proportional-cost path and no real
// stopping rule:
//   * `pm-816-intake-0903` ran 19 rounds, ~3.5 hours and ~5M tokens on ONE issue
//     and was still surfacing 1-2 genuinely NEW P0s at round 18. Stuck detection
//     never fired because it only matches an IDENTICAL P0/P1 title set, and every
//     round's P0s were different. A human had to halt it; the artifact wanted a
//     SPLIT, not another round.
//   * A separate groom ran 9 rounds at ~11 min and ~273k tokens EACH to drain six
//     WORDING-level P1s, with every lens re-reading the whole artifact each round.
//
// Every rule here is a PURE function over facts the engine already holds. The
// judgment about whether to stop must not live in the LLM that wants to stop —
// the same principle that already governs runLoop's fix-ALL gate and min-rounds
// floor. Agents may supply mechanical measurements (a line count, a diff); they
// never supply the verdict.
//
// Everything fails CLOSED: any missing, malformed, or ambiguous input yields the
// expensive-but-correct answer (a full round), never the cheap one. A wrong
// "eligible" silently costs review quality; a wrong "ineligible" costs one round.

// ---------------------------------------------------------------------------
// Contract lines — what a "low risk" edit may NOT touch
// ---------------------------------------------------------------------------

/** Caps on a delta-eligible fix batch. Both must hold, not either. */
export const DELTA_DEFAULTS = { maxChangedLines: 20, maxChangedFraction: 0.05 };

/**
 * Sections whose every line is contract text regardless of content. A wording
 * fix inside a requirements table is not a wording fix — it is a contract edit,
 * and it earns a full round.
 */
export const PROTECTED_SECTIONS = [
  "requirement classes",
  "cross-repo design",
  "story points",
  "review receipt",
];

/** `REQ-<CLASS>-<n>` anywhere on the line. */
const REQ_ID = /REQ-[A-Z0-9]+-\d+/;

/**
 * Strip the markdown decoration that precedes a line's actual text, so
 * `* **Acceptance:** …`, `  - Acceptance: …` and `1. Acceptance …` all reduce to
 * text starting with "Acceptance". Ordering matters: quote/list markers can
 * precede emphasis markers and vice versa, so peel repeatedly until stable.
 */
function undecorate(line) {
  let s = String(line ?? "").trim();
  for (;;) {
    const before = s;
    s = s.replace(/^(?:[-*+>]\s*|\d+[.)]\s*|[*_`]+)/, "").trim();
    if (s === before) return s;
  }
}

/** Normalize a heading for comparison: drop leading `#`s, emphasis and case. */
function normalizeSection(section) {
  return undecorate(String(section ?? "").replace(/^#+/, "")).toLowerCase().replace(/\s+/g, " ").trim();
}

/**
 * Is this touched line contract text?
 *
 * @param touched { text, section } — one added-or-removed line as the diff probe
 *   reports it, with `section` = the nearest preceding heading in the artifact.
 * @returns { contract: boolean, kind: string } — `kind` names WHICH rule fired,
 *   so an ineligibility reason can be specific rather than "something matched".
 */
export function isContractLine(touched) {
  const text = String(touched?.text ?? "");
  const section = normalizeSection(touched?.section);

  if (PROTECTED_SECTIONS.includes(section)) return { contract: true, kind: `section:${section}` };
  if (REQ_ID.test(text)) return { contract: true, kind: "req-id" };

  const bare = undecorate(text).toLowerCase();
  if (bare.startsWith("acceptance")) return { contract: true, kind: "acceptance" };
  if (bare.startsWith("sto:")) return { contract: true, kind: "sto" };

  return { contract: false, kind: "" };
}

// ---------------------------------------------------------------------------
// Delta eligibility — when a fix batch buys a cheap verifier instead of a round
// ---------------------------------------------------------------------------

/**
 * Decide whether the fix batch just applied was small enough and safe enough
 * that the next round can be a single delta-verifier rather than a full N-lens
 * re-read of the whole artifact.
 *
 * The four predicates are #45's, each computed here rather than judged:
 *   1. the batch fixed ZERO P0 (P1 is allowed only because 2 and 3 bound what a
 *      P1 fix may touch);
 *   2. it changed at most `maxChangedLines` lines AND at most
 *      `maxChangedFraction` of the artifact — both, not either;
 *   3. it touched no contract line (see isContractLine);
 *   4. bookends — round 1 is always full and a delta round never follows another
 *      delta round. That predicate depends on loop position, not on the batch,
 *      so runLoop owns it; this function owns 1 to 3.
 *
 * @param probe { p0FixedCount, artifactLines, touched: [{text, section}], truncated }
 *   as measured by the diff probe. `touched` is EVERY added-or-removed line, so
 *   `changedLines` is its length — one source of truth, no cross-check to drift.
 * @param opts overrides for DELTA_DEFAULTS.
 * @returns { eligible, reason, changedLines } — `reason` is "eligible" or the
 *   name of the first predicate that failed.
 */
export function isDeltaEligible(probe, opts = {}) {
  const { maxChangedLines, maxChangedFraction } = { ...DELTA_DEFAULTS, ...opts };

  // A probe that could not enumerate the diff tells us nothing → full round.
  if (!probe || typeof probe !== "object") return { eligible: false, reason: "probe-unavailable", changedLines: null };
  if (probe.truncated === true) return { eligible: false, reason: "size-lines", changedLines: null };
  if (!Array.isArray(probe.touched)) return { eligible: false, reason: "probe-unavailable", changedLines: null };
  const artifactLines = Number(probe.artifactLines);
  if (!Number.isFinite(artifactLines) || artifactLines <= 0) {
    return { eligible: false, reason: "probe-unavailable", changedLines: probe.touched.length };
  }

  const changedLines = probe.touched.length;

  // 1. Severity.
  if (Number(probe.p0FixedCount ?? 0) > 0) return { eligible: false, reason: "p0-in-batch", changedLines };

  // A batch the fixer claims to have applied that changed nothing is a fixer that
  // did not land; that deserves real reviewers, not a confirmation pass.
  if (changedLines === 0) return { eligible: false, reason: "no-diff", changedLines };

  // 2. Size — both caps.
  if (changedLines > maxChangedLines) return { eligible: false, reason: "size-lines", changedLines };
  if (changedLines > artifactLines * maxChangedFraction) {
    return { eligible: false, reason: "size-fraction", changedLines };
  }

  // 3. Contract lines untouched.
  for (const t of probe.touched) {
    const { contract, kind } = isContractLine(t);
    if (contract) return { eligible: false, reason: `contract-line:${kind}`, changedLines };
  }

  return { eligible: true, reason: "eligible", changedLines };
}

// ---------------------------------------------------------------------------
// Divergence — the loop is not approaching a fixed point
// ---------------------------------------------------------------------------

/** Warm-up before the rule may fire, and the comparison window. */
export const DIVERGENCE_DEFAULTS = { window: 3, warmup: 6 };

/** Only rounds that actually ran with a reporting reviewer panel are evidence (#81). */
const validRoundsOf = (rounds) => (rounds ?? []).filter((r) => r && r.valid !== false);
const sumNew = (rounds) => rounds.reduce((n, r) => n + Number(r.newP0P1 ?? 0), 0);

/**
 * Is this run diverging rather than converging?
 *
 * Existing stuck detection only fires on an IDENTICAL P0/P1 title set across two
 * rounds, which is why the 19-round run never tripped it: every round's P0s were
 * genuinely new. The signal that DOES describe that run is the arrival rate of
 * new P0/P1 failing to decay.
 *
 * The rule, after `warmup` valid rounds and given `2 * window` of them:
 *   every one of the last `window` rounds surfaced at least one NEW P0/P1, AND
 *   the last `window` rounds surfaced at least as many as the `window` before them.
 * One clean round inside the window, or any decay at all, means the loop is still
 * working and the rule stays silent.
 *
 * INVALID rounds (below reviewer quorum, #81) are skipped entirely: they are
 * neither evidence of divergence nor of decay, so a flaky environment can never
 * fabricate this verdict.
 *
 * @param rounds round reports carrying { newP0P1, valid }.
 * @returns { diverging, reason, validRounds, recentSum, priorSum, window }
 */
export function detectDivergence(rounds, opts = {}) {
  const { window, warmup } = { ...DIVERGENCE_DEFAULTS, ...opts };
  const v = validRoundsOf(rounds);
  const base = { diverging: false, reason: "", validRounds: v.length, recentSum: null, priorSum: null, window };

  if (v.length < Math.max(warmup, window * 2)) return base;

  const recent = v.slice(-window);
  const prior = v.slice(-window * 2, -window);
  const recentSum = sumNew(recent);
  const priorSum = sumNew(prior);

  if (!recent.every((r) => Number(r.newP0P1 ?? 0) >= 1)) return { ...base, recentSum, priorSum };
  if (recentSum < priorSum) return { ...base, recentSum, priorSum };

  const span = `${recent[0].round}-${recent[recent.length - 1].round}`;
  const priorSpan = `${prior[0].round}-${prior[prior.length - 1].round}`;
  return {
    diverging: true,
    validRounds: v.length,
    recentSum,
    priorSum,
    window,
    reason:
      `Diverging: rounds ${span} each surfaced a NEW P0/P1 (${recentSum} new, versus ${priorSum} in rounds ` +
      `${priorSpan}) — the finding rate is not decaying, so this loop is not approaching a fixed point. ` +
      `More rounds will not converge it. SPLIT the artifact, re-scope it, or hand it back.`,
  };
}

// ---------------------------------------------------------------------------
// Budget — what the run has actually spent, in the verdict
// ---------------------------------------------------------------------------

/**
 * Roll the round reports into the counts an operator reads in the verdict, so a
 * 19-round run is obvious WHILE it is happening rather than afterwards.
 *
 * `validRounds` — not `roundsRun` — is what the round budget is spent against:
 * a round whose reviewers died is not progress toward an answer (#81).
 */
export function summarizeBudget(rounds, opts = {}) {
  const all = rounds ?? [];
  const v = validRoundsOf(all);
  const countKind = (k) => v.filter((r) => (r.kind ?? "full") === k).length;
  return {
    maxRounds: Number(opts.maxRounds ?? 0),
    roundsRun: all.length,
    validRounds: v.length,
    invalidRounds: all.length - v.length,
    fullRounds: countKind("full"),
    deltaRounds: countKind("delta"),
    gateRounds: countKind("gate"),
  };
}
