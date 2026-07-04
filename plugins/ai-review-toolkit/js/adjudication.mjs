// Deterministic adjudication library — JS port of the Python hot-loop.
//
// Byte-for-byte equivalent (over the golden corpus) to the Python oracle in
// tools/finding-parser.py and tools/team-selector.py (the retired loop-driver.py's
// oracle functions were folded into finding-parser.py — see CHANGELOG).
// The review-loop.workflow.js scripts inline these so orchestration stays
// deterministic in-code. Drift against Python is caught by adjudication.test.mjs
// and tools/test_golden_parity.py, both asserting against the same fixtures.
//
// Pure functions, no I/O. See ~/.claude/plans/ai-review-ultracode-refactor.md.

export const SEVERITIES = ["P0", "P1", "P2", "P3"];
const SEVERITY_RANK = Object.fromEntries(SEVERITIES.map((s, i) => [s, i]));

const REQUIRED_FIELDS = [
  "id",
  "severity",
  "title",
  "requirement",
  "finding",
  "recommendation",
  "source",
];

// Python renders `{SEVERITIES}` as its list repr; reproduce it verbatim.
const SEVERITIES_REPR = "['P0', 'P1', 'P2', 'P3']";

const ID_PATTERN = /^P[0-3]-[a-zA-Z0-9]{3,}$/;
const ID_PREFIX_PATTERN = /^P[0-3]-/;

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

/**
 * Validate a single finding against the schema.
 * Returns {valid, errors}; errors is empty when valid. Error strings and their
 * order match finding-parser.py::validate_finding exactly.
 */
export function validateFinding(finding) {
  const errors = [];

  for (const field of REQUIRED_FIELDS) {
    const val = finding[field];
    if (
      val === undefined ||
      val === null ||
      (typeof val === "string" && val.trim() === "")
    ) {
      errors.push(`missing required field: ${field}`);
    }
  }

  const severity = finding.severity;
  if (
    severity !== undefined &&
    severity !== null &&
    !SEVERITIES.includes(severity)
  ) {
    errors.push(`invalid severity '${severity}'; must be one of ${SEVERITIES_REPR}`);
  }

  const fid = finding.id;
  if (typeof fid === "string" && !ID_PATTERN.test(fid)) {
    errors.push(
      `invalid id format '${fid}'; expected pattern P[0-3]-<alphanumeric 3+>`,
    );
  }

  // Cross-validate id prefix against severity.
  if (
    typeof fid === "string" &&
    severity !== undefined &&
    severity !== null &&
    SEVERITIES.includes(severity) &&
    ID_PREFIX_PATTERN.test(fid) &&
    !fid.startsWith(String(severity))
  ) {
    errors.push(
      `id/severity mismatch: id '${fid}' does not start with severity '${severity}'`,
    );
  }

  return { valid: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// Normalization helpers
// ---------------------------------------------------------------------------

/** Strip, lowercase, collapse internal whitespace — the dedup match key. */
function normalizeTitle(title) {
  return title.trim().toLowerCase().replace(/\s+/g, " ");
}

/** Return the higher severity (P0 > P1 > P2 > P3); ties keep `a`. */
function maxSeverity(a, b) {
  const ra = a in SEVERITY_RANK ? SEVERITY_RANK[a] : 99;
  const rb = b in SEVERITY_RANK ? SEVERITY_RANK[b] : 99;
  return ra <= rb ? a : b;
}

// ---------------------------------------------------------------------------
// Deduplication
// ---------------------------------------------------------------------------

/**
 * Merge findings with fuzzy-matching titles, keeping max severity.
 * Preserves first-seen bucket order; aggregates sources and evidence
 * (de-duped, insertion-ordered). Mirrors finding-parser.py::deduplicate_findings.
 */
export function deduplicateFindings(findings) {
  const buckets = new Map();
  const order = [];
  const keyIndex = new Map();

  for (const f of findings) {
    const titleRaw = String(f.title ?? "");
    const key = normalizeTitle(titleRaw);

    const source = String(f.source ?? "");
    const rawEvidence = f.evidence;
    let evidenceItems = [];
    if (Array.isArray(rawEvidence)) {
      evidenceItems = rawEvidence.filter((e) => e).map((e) => String(e));
    } else if (rawEvidence) {
      evidenceItems = [String(rawEvidence)];
    }

    if (!buckets.has(key)) {
      const idx = order.length;
      order.push(key);
      keyIndex.set(key, idx);
      buckets.set(key, {
        id: f.id,
        severity: f.severity,
        title: titleRaw,
        requirement: f.requirement ?? "",
        finding: f.finding ?? "",
        recommendation: f.recommendation ?? "",
        source: source || "",
        sources: source ? [source] : [],
        evidence: [...evidenceItems],
      });
    } else {
      const existing = buckets.get(key);
      const newSev = maxSeverity(String(existing.severity), String(f.severity));
      if (newSev !== existing.severity) {
        existing.severity = newSev;
        const oldId = String(existing.id);
        const candidateId = oldId.replace(/^P[0-3]/, newSev);
        if (ID_PATTERN.test(candidateId)) {
          existing.id = candidateId;
        } else {
          const idx = keyIndex.get(key);
          existing.id = `${newSev}-dedup-${String(idx).padStart(3, "0")}`;
        }
      }
      if (source && !existing.sources.includes(source)) {
        existing.sources.push(source);
      }
      for (const ev of evidenceItems) {
        if (!existing.evidence.includes(ev)) {
          existing.evidence.push(ev);
        }
      }
    }
  }

  return order.map((k) => buckets.get(k));
}

// ---------------------------------------------------------------------------
// Severity counting
// ---------------------------------------------------------------------------

/** Counts keyed by severity level (P0-P3), unknown severities ignored. */
export function countBySeverity(findings) {
  const counts = Object.fromEntries(SEVERITIES.map((s) => [s, 0]));
  for (const f of findings) {
    const sev = String(f.severity ?? "");
    if (sev in counts) {
      counts[sev] += 1;
    }
  }
  return counts;
}

// ---------------------------------------------------------------------------
// Convergence
// ---------------------------------------------------------------------------

/**
 * Check whether findings converge (safe to ship). Message strings match
 * finding-parser.py::check_convergence verbatim (including the em-dash).
 * Returns {converged, message}.
 */
export function checkConvergence(findings, threshold = 0, minFindings = 0) {
  if (minFindings > 0 && findings.length < minFindings) {
    return {
      converged: false,
      message: `no valid findings to evaluate — expected at least ${minFindings}, got ${findings.length}`,
    };
  }

  const counts = countBySeverity(findings);
  const p0 = counts.P0;
  const p1 = counts.P1;
  const low = counts.P2 + counts.P3;

  if (p0 > 0) {
    return { converged: false, message: `${p0} P0 finding(s) remain` };
  }
  if (p1 > 0) {
    return { converged: false, message: `${p1} P1 finding(s) remain` };
  }
  if (low > threshold) {
    return {
      converged: false,
      message: `${low} low-severity finding(s) exceed threshold (${threshold})`,
    };
  }
  return { converged: true, message: "converged" };
}

// ---------------------------------------------------------------------------
// Synthesis
// ---------------------------------------------------------------------------

/** Sort by severity rank (P0 first), then by id string. Stable. */
function sortFindings(findings) {
  return [...findings].sort((a, b) => {
    const ra = SEVERITY_RANK[String(a.severity ?? "P3")] ?? 99;
    const rb = SEVERITY_RANK[String(b.severity ?? "P3")] ?? 99;
    if (ra !== rb) return ra - rb;
    const ia = String(a.id ?? "");
    const ib = String(b.id ?? "");
    return ia < ib ? -1 : ia > ib ? 1 : 0;
  });
}

/**
 * Validate, merge, deduplicate, and sort findings from N reviewers.
 * Invalid findings are dropped; when *warnings* is provided (an array), each
 * dropped finding is appended as {finding, errors}. Mirrors
 * finding-parser.py::synthesize_findings.
 */
export function synthesizeFindings(reviewerResults, warnings = null) {
  const allValid = [];
  for (const reviewerList of reviewerResults) {
    for (const finding of reviewerList) {
      const { valid, errors } = validateFinding(finding);
      if (valid) {
        allValid.push(finding);
      } else if (warnings !== null) {
        warnings.push({ finding, errors });
      }
    }
  }

  const deduped = deduplicateFindings(allValid);
  return sortFindings(deduped);
}

// ---------------------------------------------------------------------------
// Model tiering
// ---------------------------------------------------------------------------

// Lenses eligible for the domain-score-gated high-stakes opus seat (OPT-006:
// architecture-reviewer dropped). Callers (team-selector.py) still gate the
// seat on the security/compliance domain scoring or an explicit override, then
// pass the resolved `highStakes` boolean here.
export const HIGH_STAKES_REVIEWERS = new Set(["security-reviewer"]);

/**
 * True if change complexity alone warrants Opus. OPT-005: raised from the
 * hair-trigger to a genuinely-large-change bar; the tool_types trigger dropped.
 */
function escalates(complexity) {
  return complexity.file_count > 3 || complexity.context_fraction > 0.4;
}

/**
 * Pick the model for a reviewer under the revised tiering policy. Pure function
 * of explicit per-reviewer signals — the team-level decisions of who is
 * eligible/high-stakes live in team-selector.py::select_team_with_scores.
 * high_stakes -> opus; else eligible + large change -> opus; else agent.model.
 * Mirrors team-selector.py::resolve_reviewer_model.
 */
export function resolveReviewerModel(
  agent,
  complexity = null,
  { escalationEligible = false, highStakes = false } = {},
) {
  if (highStakes) {
    return "opus";
  }
  if (escalationEligible && complexity !== null && escalates(complexity)) {
    return "opus";
  }
  return agent.model;
}

// ---------------------------------------------------------------------------
// Fix completeness
// ---------------------------------------------------------------------------

const ALLOWED_STATUSES = new Set(["FIXED", "ESCALATED"]);

/**
 * Returns {complete, missing}. Every finding must have a resolution whose
 * status is FIXED or ESCALATED with non-empty evidence; prohibited statuses
 * count as invalid. `missing` is sorted. Mirrors
 * finding-parser.py::check_fix_completeness.
 */
export function checkFixCompleteness(findings, resolutions) {
  const findingIds = new Set();
  for (const f of findings) {
    if (f.id) findingIds.add(String(f.id));
  }

  const validResolved = new Set();
  const invalidIds = [];
  for (const r of resolutions) {
    const fid = r.finding_id;
    if (!fid) continue;
    const status = String(r.status ?? "");
    if (!ALLOWED_STATUSES.has(status)) {
      invalidIds.push(String(fid));
    } else {
      const evidence = r.evidence;
      if (!evidence || (typeof evidence === "string" && evidence.trim() === "")) {
        invalidIds.push(String(fid));
      } else {
        validResolved.add(String(fid));
      }
    }
  }

  const missingSet = new Set();
  for (const id of findingIds) if (!validResolved.has(id)) missingSet.add(id);
  for (const id of invalidIds) if (!validResolved.has(id)) missingSet.add(id);
  const missing = [...missingSet].sort();

  return { complete: missing.length === 0, missing };
}
