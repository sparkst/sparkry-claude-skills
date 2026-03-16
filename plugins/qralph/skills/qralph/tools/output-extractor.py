"""Output extractor for QRALPH pipeline.

Deterministic extraction of structured data from messy LLM output.
Agents write naturally; this module extracts structure.

Pure functions, no I/O, no LLM calls.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Callable, Optional

# Import parse_findings from quality-dashboard (required peer dependency)
_qd_path = Path(__file__).parent / "quality-dashboard.py"
if _qd_path.exists():
    _qd_spec = importlib.util.spec_from_file_location("quality_dashboard", _qd_path)
    _qd_mod = importlib.util.module_from_spec(_qd_spec)
    _qd_spec.loader.exec_module(_qd_mod)
    _parse_findings: Callable[..., list[dict]] = _qd_mod.parse_findings
else:
    _parse_findings = None  # type: ignore[assignment]

# ─── Shared patterns ────────────────────────────────────────────────────────

_JSON_BLOCK_RE = re.compile(r'```json\s*\n(.*?)\n\s*```', re.DOTALL)
_EVIDENCE_FILE_LINE_RE = re.compile(r'\w+\.\w+:\d+')

# ─── Verdict patterns ───────────────────────────────────────────────────────

_VERDICT_REGEX_RE = re.compile(r'"verdict"\s*:\s*"(PASS|FAIL)"', re.IGNORECASE)

_NL_PASS_PATTERNS = [
    re.compile(r'all criteria (?:are )?met', re.IGNORECASE),
    re.compile(r'fully satisf', re.IGNORECASE),
    re.compile(r'verification pass', re.IGNORECASE),
]

_NL_FAIL_PATTERNS = [
    re.compile(r'\bfail', re.IGNORECASE),
    re.compile(r'\bnot met\b', re.IGNORECASE),
    re.compile(r'does not satisfy', re.IGNORECASE),
    re.compile(r'\bblocked?\b', re.IGNORECASE),
    re.compile(r'\breject', re.IGNORECASE),
]

# ─── Criteria patterns ──────────────────────────────────────────────────────

_TABLE_ROW_RE = re.compile(
    r'\|\s*(AC-\d+)\s*\|([^|]*)\|\s*(pass|fail|partial)\w*\s*\|',
    re.IGNORECASE,
)

_SECTION_HEADER_RE = re.compile(r'^#{1,4}\s+(AC-\d+)[:\s](.*)$', re.MULTILINE)

_NUMBERED_LIST_RE = re.compile(
    r'^\d+\.\s+(AC-\d+)[:\s](.+)',
    re.MULTILINE,
)

_STATUS_PASS_RE = re.compile(r'\b(?:pass|met|satisfied|implemented|works?|correct)\b', re.IGNORECASE)
_STATUS_FAIL_RE = re.compile(r'\b(?:fail|not met|missing|not implemented|broken|absent)\b', re.IGNORECASE)
_STATUS_PARTIAL_RE = re.compile(r'\b(?:partial|partially|incomplete)\b', re.IGNORECASE)

# ─── Reverify patterns ──────────────────────────────────────────────────────

_NL_RESOLVED_PATTERNS = [
    re.compile(r'\bfixed\b', re.IGNORECASE),
    re.compile(r'\baddressed\b', re.IGNORECASE),
    re.compile(r'\bno longer present\b', re.IGNORECASE),
    re.compile(r'\bresolved\b', re.IGNORECASE),
]

# ─── Smoke patterns ─────────────────────────────────────────────────────────

_BOLD_PASS_RE = re.compile(r'\*\*PASS\*\*', re.IGNORECASE)
_BOLD_FAIL_RE = re.compile(r'\*\*FAIL\*\*', re.IGNORECASE)
_BOLD_SKIP_RE = re.compile(r'\*\*SKIP\*\*', re.IGNORECASE)

_PLAIN_STATUS_RE = re.compile(r'(?<!\*)(?::\s*|—\s*|-\s*)(PASS|FAIL|SKIP)(?!\*)', re.IGNORECASE)

_CHECKBOX_PASS_RE = re.compile(r'\[x\]', re.IGNORECASE)
_CHECKBOX_FAIL_RE = re.compile(r'\[\s\]')

_SUMMARY_RE = re.compile(
    r'(\d+)\s*passed.*?(\d+)\s*failed(?:.*?(\d+)\s*skipped)?',
    re.IGNORECASE,
)

# ─── Gap patterns (anchored to line beginnings) ─────────────────────────────

_GAP_PATTERNS = [
    (re.compile(r'^[\s\-*]*missing\s+(?:test\s+)?coverage', re.IGNORECASE | re.MULTILINE),
     "missing test coverage for one or more requirements"),
    (re.compile(r'^[\s\-*]*missing\s+tests?', re.IGNORECASE | re.MULTILINE),
     "missing tests"),
    (re.compile(r'^[\s\-*]*not\s+covered', re.IGNORECASE | re.MULTILINE),
     "untested code or requirements not covered"),
    (re.compile(r'^[\s\-*]*(?:disconnected|dead\s+code|not\s+reachable)', re.IGNORECASE | re.MULTILINE),
     "wiring issues (disconnected or unreachable code)"),
    (re.compile(r'^[\s\-*]*import\s+.*(?:error|missing)', re.IGNORECASE | re.MULTILINE),
     "import or export wiring problems"),
]


# ─── JSON helpers ──────────────────────────────────────────────────────────

def _json_candidates(content: str) -> list[str]:
    """Return JSON strings to try: code-block first, then raw content."""
    candidates = []
    block_match = _JSON_BLOCK_RE.search(content)
    if block_match:
        candidates.append(block_match.group(1))
    candidates.append(content)
    return candidates


# ─── extract_verdict ────────────────────────────────────────────────────────

def extract_verdict(content: str) -> dict:
    """Extract verdict from verification output.

    4-tier fallback: JSON block → raw JSON → regex → natural language.
    Returns {"verdict": "PASS"|"FAIL"|None, "confidence": str, "source": str}.
    """
    if not content or not content.strip():
        return {"verdict": None, "confidence": "none", "source": "empty"}

    # Tier 1-2: JSON (code block first, then raw)
    block_match = _JSON_BLOCK_RE.search(content)
    json_sources = []
    if block_match:
        json_sources.append((block_match.group(1), "json_block"))
    json_sources.append((content, "raw_json"))

    for json_str, source in json_sources:
        try:
            data = json.loads(json_str)
            verdict = data.get("verdict", "").upper()
            if verdict in ("PASS", "FAIL"):
                return {"verdict": verdict, "confidence": "high", "source": source}
        except (json.JSONDecodeError, AttributeError):
            pass

    # Tier 3: Regex fallback
    match = _VERDICT_REGEX_RE.search(content)
    if match:
        return {"verdict": match.group(1).upper(), "confidence": "medium", "source": "regex"}

    # Tier 4: Natural language
    has_pass = any(p.search(content) for p in _NL_PASS_PATTERNS)
    has_fail = any(p.search(content) for p in _NL_FAIL_PATTERNS)

    if has_pass and has_fail:
        return {"verdict": None, "confidence": "none", "source": "ambiguous"}
    if has_pass:
        return {"verdict": "PASS", "confidence": "low", "source": "natural_language"}
    if has_fail:
        return {"verdict": "FAIL", "confidence": "low", "source": "natural_language"}

    return {"verdict": None, "confidence": "none", "source": "unknown"}


# ─── extract_criteria_results ───────────────────────────────────────────────

def _infer_status(text: str) -> str:
    """Infer pass/fail/partial from a block of text."""
    if _STATUS_PARTIAL_RE.search(text):
        return "partial"
    if _STATUS_FAIL_RE.search(text):
        return "fail"
    if _STATUS_PASS_RE.search(text):
        return "pass"
    return "unknown"


def extract_criteria_results(content: str) -> list[dict]:
    """Extract criteria_results from verification output.

    Tries: JSON block → raw JSON → markdown table → section headers → numbered list.
    Always returns a list (empty if nothing found), never None.
    """
    results: list[dict] = []
    seen_criteria: set[str] = set()

    def _add(criterion: str, status: str, evidence: str = "", source: str = ""):
        if criterion not in seen_criteria:
            seen_criteria.add(criterion)
            results.append({
                "criterion": criterion,
                "status": status.lower(),
                "evidence": evidence,
                "source": source,
            })

    # Tier 1: JSON (code block first, then raw) — pass through original dicts
    for json_str in _json_candidates(content):
        if results:
            break
        try:
            data = json.loads(json_str)
            if "criteria_results" in data and isinstance(data["criteria_results"], list):
                for entry in data["criteria_results"]:
                    if isinstance(entry, dict):
                        crit = entry.get("criterion", entry.get("criterion_index", ""))
                        seen_criteria.add(crit)
                        results.append(entry)
        except (json.JSONDecodeError, AttributeError):
            pass

    # Tier 2: Markdown table
    for m in _TABLE_ROW_RE.finditer(content):
        _add(m.group(1), m.group(3).strip(), "", "table")

    # Tier 3: Section headers — find AC-N headers and scan body for status
    for m in _SECTION_HEADER_RE.finditer(content):
        criterion = m.group(1)
        if criterion in seen_criteria:
            continue
        # Get the text until the next heading or end
        start = m.end()
        next_heading = re.search(r'^#{1,4}\s+', content[start:], re.MULTILINE)
        end = start + next_heading.start() if next_heading else len(content)
        body = content[start:end]
        status = _infer_status(body)
        _add(criterion, status, "", "section")

    # Tier 4: Numbered list
    for m in _NUMBERED_LIST_RE.finditer(content):
        criterion = m.group(1)
        line_text = m.group(2)
        status = _infer_status(line_text)
        _add(criterion, status, "", "numbered_list")

    return results


# ─── extract_request_satisfaction ───────────────────────────────────────────

def extract_request_satisfaction(content: str, fragment_ids: list[str]) -> list[dict]:
    """Extract request satisfaction status for each known fragment ID.

    Tries JSON first (backward compat), then searches prose for each fragment.
    """
    results: list[dict] = []
    found: dict[str, dict] = {}

    # Tier 1: JSON extraction
    json_results = _extract_json_key(content, "request_satisfaction")
    if isinstance(json_results, list):
        for entry in json_results:
            if isinstance(entry, dict):
                frag = entry.get("fragment", "")
                if frag in fragment_ids:
                    found[frag] = {"fragment": frag, "status": entry.get("status", "unknown"), "source": "json"}

    # Tier 2: Natural language search per fragment
    for fid in fragment_ids:
        if fid in found:
            continue
        if fid not in content:
            found[fid] = {"fragment": fid, "status": "missing", "source": "not_found"}
            continue

        # Find all text near the fragment ID
        pattern = re.compile(re.escape(fid) + r'[^.\n]*', re.IGNORECASE)
        matches = pattern.findall(content)
        context = " ".join(matches)

        if re.search(r'\bpartial', context, re.IGNORECASE):
            found[fid] = {"fragment": fid, "status": "partial", "source": "natural_language"}
        elif re.search(r'\b(?:satisfied|fully met|fully satisfied|complete)\b', context, re.IGNORECASE):
            found[fid] = {"fragment": fid, "status": "satisfied", "source": "natural_language"}
        elif re.search(r'\b(?:not met|missing|absent|fail)', context, re.IGNORECASE):
            found[fid] = {"fragment": fid, "status": "not_satisfied", "source": "natural_language"}
        else:
            found[fid] = {"fragment": fid, "status": "mentioned", "source": "natural_language"}

    for fid in fragment_ids:
        results.append(found.get(fid, {"fragment": fid, "status": "missing", "source": "not_found"}))

    return results


# ─── extract_reverify_verdicts ──────────────────────────────────────────────

def extract_reverify_verdicts(content: str, expected_ids: list[str]) -> dict[str, str]:
    """Extract RESOLVED/UNRESOLVED verdicts for each expected finding ID.

    Safety rail: RESOLVED without file:line evidence is downgraded to unresolved.
    Returns dict mapping finding_id → "resolved" | "unresolved".
    """
    verdicts: dict[str, str] = {}

    if not content:
        return {fid: "unresolved" for fid in expected_ids}

    lines = content.splitlines()

    # Pass 1: Explicit RESOLVED:/UNRESOLVED: lines
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.upper().startswith("RESOLVED:"):
            fid = stripped.split(":", 1)[1].strip()
            if fid in expected_ids:
                context_block = "\n".join(lines[i:i + 3])
                if _EVIDENCE_FILE_LINE_RE.search(context_block):
                    verdicts[fid] = "resolved"
                else:
                    verdicts[fid] = "unresolved"
        elif stripped.upper().startswith("UNRESOLVED:"):
            fid = stripped.split(":", 1)[1].strip()
            if fid in expected_ids:
                verdicts[fid] = "unresolved"

    # Pass 2: Natural language for remaining IDs
    for fid in expected_ids:
        if fid in verdicts:
            continue
        if fid not in content:
            verdicts[fid] = "unresolved"
            continue

        # Find context around the finding ID
        pattern = re.compile(re.escape(fid) + r'[^.\n]*')
        matches = pattern.findall(content)
        # Also look at full sentences containing the ID
        for i, line in enumerate(lines):
            if fid in line:
                matches.append(line)
                if i + 1 < len(lines):
                    matches.append(lines[i + 1])

        context = " ".join(matches)
        has_resolved_signal = any(p.search(context) for p in _NL_RESOLVED_PATTERNS)
        has_evidence = _EVIDENCE_FILE_LINE_RE.search(context)

        # Safety rail: resolved without file:line evidence is downgraded
        verdicts[fid] = "resolved" if (has_resolved_signal and has_evidence) else "unresolved"

    return verdicts


# ─── extract_smoke_results ──────────────────────────────────────────────────

def extract_smoke_results(content: str) -> dict:
    """Extract smoke test pass/fail/skip counts from agent output.

    Tries bold markers → plain markers → checkboxes → summary line.
    Returns {"passed", "failed", "skipped", "failures"}.
    """
    if not content or not content.strip():
        return {"passed": 0, "failed": 0, "skipped": 0, "failures": []}

    failures: list[str] = []

    # Tier 1: Bold markers (**PASS**, **FAIL**, **SKIP**)
    bold_pass = len(_BOLD_PASS_RE.findall(content))
    bold_fail = len(_BOLD_FAIL_RE.findall(content))
    bold_skip = len(_BOLD_SKIP_RE.findall(content))

    if bold_pass + bold_fail + bold_skip > 0:
        for line in content.splitlines():
            if re.search(r'\*\*FAIL\*\*', line, re.IGNORECASE):
                failures.append(line.strip())
        return {"passed": bold_pass, "failed": bold_fail, "skipped": bold_skip, "failures": failures}

    # Tier 2: Plain markers (PASS/FAIL/SKIP after : or — or -)
    plain_counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for m in _PLAIN_STATUS_RE.finditer(content):
        plain_counts[m.group(1).upper()] += 1

    if sum(plain_counts.values()) > 0:
        for line in content.splitlines():
            if re.search(r'(?<!\*)\bFAIL\b(?!\*)', line, re.IGNORECASE):
                failures.append(line.strip())
        return {
            "passed": plain_counts["PASS"],
            "failed": plain_counts["FAIL"],
            "skipped": plain_counts["SKIP"],
            "failures": failures,
        }

    # Tier 3: Checkbox format
    checkbox_pass = len(_CHECKBOX_PASS_RE.findall(content))
    checkbox_fail = len(_CHECKBOX_FAIL_RE.findall(content))

    if checkbox_pass + checkbox_fail > 0:
        for line in content.splitlines():
            if _CHECKBOX_FAIL_RE.search(line):
                failures.append(line.strip())
        return {"passed": checkbox_pass, "failed": checkbox_fail, "skipped": 0, "failures": failures}

    # Tier 4: Summary line fallback
    summary_match = _SUMMARY_RE.search(content)
    if summary_match:
        return {
            "passed": int(summary_match.group(1)),
            "failed": int(summary_match.group(2)),
            "skipped": int(summary_match.group(3)) if summary_match.group(3) else 0,
            "failures": [],
        }

    return {"passed": 0, "failed": 0, "skipped": 0, "failures": []}


# ─── extract_polish_issues ──────────────────────────────────────────────────

def extract_polish_issues(content: str) -> dict:
    """Extract polish issues: P0/P1 findings and coverage gaps.

    Uses parse_findings from quality-dashboard for finding extraction.
    Returns {"has_issues": bool, "findings": list, "gaps": list}.
    """
    if _parse_findings is None:
        raise RuntimeError(
            "quality-dashboard.py not found — extract_polish_issues requires parse_findings. "
            "Update your QRALPH plugin."
        )
    findings = _parse_findings(content)

    # has_issues driven by finding severity, not keyword presence
    p0_p1_findings = [f for f in findings if f["severity"] in ("P0", "P1")]

    # Gap detection — patterns anchored to line beginnings
    gaps: list[str] = []
    seen_gaps: set[str] = set()
    for pattern, description in _GAP_PATTERNS:
        if pattern.search(content) and description not in seen_gaps:
            gaps.append(description)
            seen_gaps.add(description)

    return {
        "has_issues": bool(p0_p1_findings or gaps),
        "findings": findings,
        "gaps": gaps,
    }


# ─── Helpers ────────────────────────────────────────────────────────────────

def _extract_json_key(content: str, key: str) -> Optional[list]:
    """Extract a JSON key from content, trying code block then raw JSON."""
    for json_str in _json_candidates(content):
        try:
            data = json.loads(json_str)
            if key in data and isinstance(data[key], list):
                return data[key]
        except (json.JSONDecodeError, AttributeError):
            pass
    return None
