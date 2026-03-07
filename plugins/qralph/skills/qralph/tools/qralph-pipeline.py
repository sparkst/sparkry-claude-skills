#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
QRALPH v6.6.2 Pipeline — deterministic multi-agent orchestration, idea to production.

Full pipeline: IDEATE → PERSONA → CONCEPT → PLAN → EXECUTE → SIMPLIFY →
               QUALITY_LOOP → POLISH → VERIFY → DEPLOY → SMOKE → LEARN → COMPLETE
Python does the orchestration. Claude does the thinking.

Commands:
    plan "<request>"     — Init project, detect template, generate agent configs
    next [--confirm]     — Get next pipeline action (state machine driver)
    plan-collect         — Read agent-outputs/, compute execution manifest
    execute              — Read manifest, compute parallel groups, generate agent configs
    execute-collect      — Read execution-outputs/, check completeness
    verify               — Generate verification agent config
    finalize             — Write SUMMARY.md, mark COMPLETE
    resume               — Read checkpoint, return current phase + next action
    status               — Return project state
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
import atexit

# Import shared state module
import importlib.util

_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

_config_path = Path(__file__).parent / "qralph-config.py"
_config_spec = importlib.util.spec_from_file_location("qralph_config", _config_path)
qralph_config = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(qralph_config)

# Import plugin detector (optional — may not exist yet)
try:
    _detector_path = Path(__file__).parent / "plugin_detector.py"
    _detector_spec = importlib.util.spec_from_file_location("plugin_detector", _detector_path)
    _plugin_detector = importlib.util.module_from_spec(_detector_spec)
    _detector_spec.loader.exec_module(_plugin_detector)
    detect_all_plugins = _plugin_detector.detect_all_plugins
except (ImportError, FileNotFoundError, AttributeError, OSError):
    detect_all_plugins = None

# Import persona generator (optional — may not exist yet)
try:
    _persona_gen_path = Path(__file__).parent / "persona_generator.py"
    _persona_gen_spec = importlib.util.spec_from_file_location("persona_generator", _persona_gen_path)
    _persona_generator = importlib.util.module_from_spec(_persona_gen_spec)
    _persona_gen_spec.loader.exec_module(_persona_generator)
    suggest_archetypes = _persona_generator.suggest_archetypes
    generate_persona_template = _persona_generator.generate_persona_template
    generate_persona_review_prompt = _persona_generator.generate_persona_review_prompt
except (ImportError, FileNotFoundError, AttributeError, OSError):
    suggest_archetypes = None
    generate_persona_template = None
    generate_persona_review_prompt = None

# Import quality dashboard (optional — may not exist yet)
try:
    _qd_path = Path(__file__).parent / "quality-dashboard.py"
    _qd_spec = importlib.util.spec_from_file_location("quality_dashboard", _qd_path)
    _qd_mod = importlib.util.module_from_spec(_qd_spec)
    _qd_spec.loader.exec_module(_qd_mod)
    parse_findings = _qd_mod.parse_findings
    check_convergence = _qd_mod.check_convergence
    should_agent_continue = _qd_mod.should_agent_continue
    generate_dashboard = _qd_mod.generate_dashboard
except (ImportError, FileNotFoundError, AttributeError, OSError):
    parse_findings = None
    check_convergence = None
    should_agent_continue = None
    generate_dashboard = None

# Import confidence scorer (optional — may not exist yet)
try:
    _cs_path = Path(__file__).parent / "confidence-scorer.py"
    _cs_spec = importlib.util.spec_from_file_location("confidence_scorer", _cs_path)
    _cs_mod = importlib.util.module_from_spec(_cs_spec)
    _cs_spec.loader.exec_module(_cs_mod)
    detect_consensus = _cs_mod.detect_consensus
    should_backtrack = _cs_mod.should_backtrack
except (ImportError, FileNotFoundError, AttributeError, OSError):
    detect_consensus = None
    should_backtrack = None

# Import learning capture (optional — may not exist yet)
try:
    _lc_path = Path(__file__).parent / "learning-capture.py"
    _lc_spec = importlib.util.spec_from_file_location("learning_capture", _lc_path)
    _lc_mod = importlib.util.module_from_spec(_lc_spec)
    _lc_spec.loader.exec_module(_lc_mod)
    extract_learnings = _lc_mod.extract_learnings
    generate_learning_summary = _lc_mod.generate_learning_summary
except (ImportError, FileNotFoundError, AttributeError, OSError):
    extract_learnings = None
    generate_learning_summary = None

# Import self-healing rules (optional — may not exist yet)
try:
    _sh_path = Path(__file__).parent / "self-healing.py"
    _sh_spec = importlib.util.spec_from_file_location("self_healing", _sh_path)
    _self_healing = importlib.util.module_from_spec(_sh_spec)
    _sh_spec.loader.exec_module(_self_healing)
    match_heal_condition = _self_healing.match_condition
    is_heal_on_cooldown_fn = _self_healing.is_heal_on_cooldown
    learn_heal_counters = _self_healing.learn_update_counters
except (ImportError, FileNotFoundError, AttributeError, OSError):
    match_heal_condition = None
    is_heal_on_cooldown_fn = None
    learn_heal_counters = None

__version__ = "6.6.4"

QUALITY_STANDARD = """
## Quality Standard

You are expected to deliver production-quality work. The following rules are non-negotiable:

- No stubs, placeholders, TODOs, or "for now" implementations. Every piece of code must be complete and correct.
- No descoping of requirements without explicit escalation to the user. If something is hard, solve it — do not quietly drop it.
- No hardcoded workarounds. Implement real solutions only.
- Complete error handling. Every failure path must be handled with real behavior, not mocks or silent failures.
- Anti-shortcut patterns:
  - Never assume the user wants speed over quality.
  - Never silently drop requirements.
  - Never accept a partial implementation as done.
  - Never leave a known bug because it "doesn't matter right now."
- If you find yourself writing a workaround or deferring something, stop and solve it properly.

Good-enough is not good enough. Would a senior engineer at Amazon stake their name on this?
""".strip()


def _inject_quality_standard(prompt: str) -> str:
    """Append the QUALITY_STANDARD section to any agent prompt."""
    return prompt + "\n\n" + QUALITY_STANDARD


def _fragment_request(request_text: str) -> list[tuple[str, str]]:
    """Split a user request into numbered (REQ-F-N, text) tuples.

    Splits on sentence boundaries (. ! ?), numbered list items (1. 2. etc),
    semicolons, and line breaks preceded by dashes or bullets. Filters out
    conversational filler (fragments < 10 chars). Returns an empty list for
    very short requests (< 20 chars total).
    """
    if not request_text or len(request_text.strip()) < 20:
        return []

    # Normalize and insert NUL as a split sentinel at each delimiter
    text = request_text.strip().replace("\r\n", "\n").replace("\r", "\n")
    sep = "\x00"
    text = re.sub(r'(?m)^(\d+[.)]\s+)', sep + r'\1', text)       # numbered list items
    text = re.sub(r'(?m)^([-*•]\s+)', sep + r'\1', text)          # bullet/dash items
    text = re.sub(r'([.!?])\s+(?=[A-Z\-\*•\d])', r'\1' + sep, text)  # sentence endings
    text = re.sub(r';\s*', sep, text)                              # semicolons

    meaningful = [p for p in (p.strip() for p in text.split(sep)) if len(p) >= 10]
    return [(f"REQ-F-{i + 1}", frag) for i, frag in enumerate(meaningful)]


PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
PROJECTS_DIR = QRALPH_DIR / "projects"
STATE_FILE = QRALPH_DIR / "current-project.json"
# Session lock uses __file__-relative path to match hooks (immune to CWD changes)
SESSION_LOCK = Path(__file__).resolve().parent.parent / "active-session.lock"


def _acquire_session_lock() -> None:
    """Create session lock file atomically. Hooks use this to know QRALPH is active.

    Uses O_CREAT|O_EXCL for atomic creation to prevent TOCTOU races between
    concurrent sessions. If an existing lock is present, checks whether the
    locked PID is still alive. A dead PID (stale lock) is silently removed
    before retrying. A live PID raises RuntimeError.
    """
    lock_payload = json.dumps({
        "pid": os.getpid(),
        "started_at": datetime.now().isoformat(),
    }).encode()

    for _attempt in range(2):
        try:
            fd = os.open(str(SESSION_LOCK), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            try:
                os.write(fd, lock_payload)
            finally:
                os.close(fd)
            return
        except FileExistsError:
            _maybe_clear_stale_lock()  # removes stale or raises RuntimeError

    # Final fallback: overwrite (should rarely reach here)
    SESSION_LOCK.write_text(lock_payload.decode())


def _maybe_clear_stale_lock() -> None:
    """Remove session lock if the owning PID is dead. Raise if alive."""
    try:
        lock_data = json.loads(SESSION_LOCK.read_text())
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        SESSION_LOCK.unlink(missing_ok=True)
        return

    pid = lock_data.get("pid")
    if not isinstance(pid, int):
        SESSION_LOCK.unlink(missing_ok=True)
        return

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        SESSION_LOCK.unlink(missing_ok=True)
        return
    except PermissionError:
        pass  # PID exists but we can't signal it — treat as live

    started_at = lock_data.get("started_at", "unknown time")
    raise RuntimeError(
        f"Another QRALPH session (PID {pid}, started {started_at}) is already running. "
        "Wait for it to complete, or use /clear to start fresh."
    )


def _release_session_lock() -> None:
    """Remove session lock file. Hooks will silently allow everything."""
    SESSION_LOCK.unlink(missing_ok=True)

atexit.register(_release_session_lock)


def _pipeline_shutdown(state: dict, project_path: Path) -> str:
    """Release session lock, record shutdown timestamp, clear spawned agents.

    Returns the shutdown ISO timestamp.
    """
    _release_session_lock()
    shutdown_at = datetime.now().isoformat()
    pipeline = state.setdefault("pipeline", {})
    pipeline["shutdown_at"] = shutdown_at
    if "_spawned_agents" in pipeline:
        pipeline["_spawned_agents"] = {}
    return shutdown_at

# Minimum length for agent output to be considered valid (not a stub/error)
MIN_AGENT_OUTPUT_LENGTH = 100

# Pipeline phases
PHASES = ["IDEATE", "PERSONA", "CONCEPT_REVIEW", "PLAN", "EXECUTE",
          "SIMPLIFY", "QUALITY_LOOP", "POLISH", "VERIFY",
          "DEPLOY", "SMOKE",  # v7.0: idea-to-production
          "LEARN", "COMPLETE"]

# Max concurrent worktree agents
MAX_PARALLEL_AGENTS = 4

# Agent wait timeouts by model tier (seconds)
MAX_AGENT_WAIT_BY_MODEL = {
    "haiku": 180,
    "sonnet": 400,
    "opus": 900,
    "default": 400,
}


def _resolve_agent_output(output_dir: Path, agent_name: str, min_length: int = 100) -> tuple[Optional[Path], str]:
    """Resolve agent output file with priority: .respawn.md > .md > .hung.md.
    Returns (path, content) — content is empty string if nothing found or too short.
    """
    suffixes = [".respawn.md", ".md", ".hung.md"]
    for suffix in suffixes:
        candidate = output_dir / f"{agent_name}{suffix}"
        if candidate.exists():
            content = candidate.read_text(encoding="utf-8").strip()
            if content and len(content) >= min_length:
                return candidate, content
    return None, ""


def _record_agent_start(agent_name: str, agent_timing: dict) -> None:
    """Record agent start time using setdefault (write-once)."""
    agent_timing.setdefault("agent_start_times", {}).setdefault(
        agent_name, datetime.now().isoformat()
    )
    agent_timing.setdefault("respawn_counts", {}).setdefault(agent_name, 0)


def _check_agent_timeout(
    agent_timing: dict, agent_name: str, model: str,
    output_dir: Path, project_path: Path,
) -> Optional[dict]:
    """Check if an agent has timed out. Returns action dict or None.

    - None: agent still within timeout window
    - {"action": "respawn_agent", ...}: first timeout, re-spawn
    - {"action": "escalate_to_user", ...}: already re-spawned, escalate
    """
    start_str = agent_timing.get("agent_start_times", {}).get(agent_name)
    if not start_str:
        return None

    try:
        started = datetime.fromisoformat(start_str)
    except (ValueError, TypeError):
        return None

    timeout = MAX_AGENT_WAIT_BY_MODEL.get(model, MAX_AGENT_WAIT_BY_MODEL["default"])
    elapsed = (datetime.now() - started).total_seconds()

    if elapsed < timeout:
        return None

    respawn_count = agent_timing.get("respawn_counts", {}).get(agent_name, 0)

    if respawn_count < 1:
        # First timeout — rename existing output to .hung.md, trigger re-spawn
        original = output_dir / f"{agent_name}.md"
        hung = output_dir / f"{agent_name}.hung.md"
        if original.exists() and not hung.exists():
            original.rename(hung)
        agent_timing["respawn_counts"][agent_name] = respawn_count + 1
        agent_timing["agent_start_times"][agent_name] = datetime.now().isoformat()
        return {
            "action": "respawn_agent",
            "agent_name": agent_name,
            "model": model,
            "elapsed_seconds": int(elapsed),
            "output_file": f"{agent_name}.respawn.md",
        }

    return {
        "action": "escalate_to_user",
        "escalation_type": "agent_timeout",
        "agent_name": agent_name,
        "elapsed_seconds": int(elapsed),
        "message": (
            f"Agent '{agent_name}' timed out after {int(elapsed)}s "
            f"(limit: {timeout}s, model: {model}). "
            f"Re-spawn already attempted. Manual intervention required."
        ),
    }


# ─── Task Templates ─────────────────────────────────────────────────────────

TASK_TEMPLATES = {
    "code-audit": {
        "description": "Analyze code for bugs, security issues, and quality problems",
        "plan_agents": ["researcher", "sde-iii", "security-reviewer"],
    },
    "bug-fix": {
        "description": "Debug and fix a specific issue",
        "plan_agents": ["researcher", "sde-iii"],
    },
    "ui-change": {
        "description": "Modify user interface components",
        "plan_agents": ["researcher", "sde-iii", "ux-designer"],
    },
    "new-feature": {
        "description": "Build new functionality end-to-end",
        "plan_agents": ["researcher", "sde-iii", "security-reviewer", "ux-designer"],
    },
    "security": {
        "description": "Security audit and hardening",
        "plan_agents": ["researcher", "security-reviewer", "sde-iii"],
    },
    "architecture": {
        "description": "System design and architecture review",
        "plan_agents": ["researcher", "sde-iii", "architecture-advisor"],
    },
    "research": {
        "description": "Research a topic, produce options and recommendations",
        "plan_agents": ["researcher", "sde-iii"],
    },
}

# Critical agents that MUST be included in every template's plan_agents.
# These are non-negotiable — the pipeline enforces their presence.
CRITICAL_AGENTS = ["sde-iii", "architecture-advisor"]


def _enforce_critical_agents(agents: list[str]) -> list[str]:
    """Ensure all critical agents are present. Append any that are missing."""
    result = list(agents)
    for critical in CRITICAL_AGENTS:
        if critical not in result:
            result.append(critical)
    return result


# ─── Agent Relevance Filtering ───────────────────────────────────────────────

# Agents with an empty domain set are always relevant (no domain restriction).
# Agents with a non-empty domain set are only included when the request touches
# at least one of those domains.
_AGENT_DOMAINS: dict[str, set[str]] = {
    "researcher":           set(),          # general-purpose — always included
    "sde-iii":             set(),          # implementer — always included
    "ux-designer":         {"frontend"},
    "security-reviewer":   {"security"},
    "architecture-advisor": {"backend", "database", "infra"},
}


def _classify_request_domains(request: str) -> set[str]:
    """Return the set of domain names active in *request*.

    Reuses the _DOMAIN_SIGNALS dict from estimate_story_points so both
    functions stay consistent with each other.
    """
    lower = request.lower()
    return {
        domain
        for domain, signals in _DOMAIN_SIGNALS.items()
        if any(sig in lower for sig in signals)
    }


def _filter_agents_by_relevance(
    agents: list[str],
    request_domains: set[str],
    estimated_sp: float,
) -> list[str]:
    """Remove agents whose domains have zero overlap with *request_domains*.

    Agents with an empty domain set (_AGENT_DOMAINS entry is set()) are always
    kept.  When *request_domains* is itself empty (no strong domain signals
    detected) all agents are kept so we don't accidentally prune everything on
    ambiguous requests.

    architecture-advisor is additionally skipped for SP < 0.5 regardless of
    domain match — small tasks don't warrant architecture review.
    """
    # If we can't classify the request, don't filter — be conservative.
    if not request_domains:
        if estimated_sp < 0.5:
            return [a for a in agents if a != "architecture-advisor"]
        return list(agents)

    filtered = []
    for agent in agents:
        # SP gate for architecture-advisor overrides domain match
        if agent == "architecture-advisor" and estimated_sp < 0.5:
            continue
        agent_domains = _AGENT_DOMAINS.get(agent, set())
        if not agent_domains:
            # No domain restriction — always relevant
            filtered.append(agent)
        elif agent_domains & request_domains:
            # At least one domain overlaps
            filtered.append(agent)
        # else: skip — irrelevant to this request

    # sde-iii must always survive (belt-and-suspenders guard)
    if "sde-iii" not in filtered and "sde-iii" in agents:
        filtered.append("sde-iii")

    return filtered

# Keywords for template suggestion (simple, deterministic matching)
TEMPLATE_KEYWORDS = {
    "code-audit": ["audit", "review", "analyze", "quality", "lint", "check"],
    "bug-fix": ["bug", "fix", "error", "broken", "crash", "fail", "issue", "debug"],
    "ui-change": ["ui", "ux", "interface", "design", "layout", "component", "page", "button", "form", "css", "style"],
    "new-feature": ["add", "create", "build", "implement", "new", "feature"],
    "security": ["security", "vulnerability", "cve", "xss", "injection", "auth", "encrypt", "pentest"],
    "architecture": ["architecture", "design", "scale", "refactor", "migrate", "pattern", "system"],
    "research": ["research", "compare", "evaluate", "investigate", "options", "recommend"],
}


def _decontaminate_request(request: str) -> str:
    """Remove elaboration/negation context that skews keyword-based template scoring.

    Two transformations are applied:

    1. **Colon/em-dash truncation** — Requests like "Fix X: (1) skip UX for Y"
       describe primary intent before the first colon or em-dash, and implementation
       details (including mentions of things to *avoid*) afterward. Scoring only the
       pre-colon fragment prevents sub-items from polluting the template signal.

    2. **Negation phrase removal** — Phrases such as "skip UX designer", "without
       security-reviewer", "instead of OAuth" describe things to *exclude*, not things
       to *build*. They are stripped before scoring so that a mention of "UI" inside
       "skip UX designer for UI-only tasks" does not inflate the ui-change score.
    """
    # Truncate at the first colon+space, em-dash, or double-hyphen elaboration.
    text = re.split(r':\s+|—\s+|\s+--\s+', request, maxsplit=1)[0]

    # Remove negation phrases and the few words that follow them.
    # Covers: "skip X", "exclude X", "without X", "instead of X", "not X", "avoid X", "ignore X"
    text = re.sub(
        r'\b(?:skip|exclude|without|instead\s+of|not|avoid|ignore)\s+\S+(?:\s+\S+){0,3}',
        ' ',
        text,
        flags=re.IGNORECASE,
    )

    return text.strip()


def suggest_template(request: str) -> tuple[str, dict[str, int]]:
    """Suggest a template based on keyword matching. Returns (template_name, scores).

    The request is first decontaminated — elaboration text and negation phrases are
    stripped — so that words appearing in descriptive context (e.g. "skip UX designer")
    do not inflate the wrong template's score.
    """
    cleaned = _decontaminate_request(request)
    request_lower = cleaned.lower()
    scores: dict[str, int] = {}

    for template_name, keywords in TEMPLATE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in request_lower)
        if score > 0:
            scores[template_name] = score

    if not scores:
        return "research", {}

    best = max(scores, key=scores.get)
    return best, scores


# ─── Safety ──────────────────────────────────────────────────────────────────

_MAX_AGENT_OUTPUT_EMBED = 8000
_MAX_REQUEST_LENGTH = 2000

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous\s+|prior\s+)?(instructions?|prompts?|context)", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous\s+)?(instructions?|prompts?)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"new\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"act\s+as\b", re.IGNORECASE),
]


def _sanitize_agent_output(content: str) -> str:
    """Truncate and strip prompt injection patterns from agent output."""
    content = content[:_MAX_AGENT_OUTPUT_EMBED]
    for pattern in _INJECTION_PATTERNS:
        content = pattern.sub("[REDACTED]", content)
    return content


def _sanitize_request(request: str) -> str:
    """Validate and sanitize user request string."""
    if len(request) > _MAX_REQUEST_LENGTH:
        raise ValueError(f"Request too long ({len(request)} chars, max {_MAX_REQUEST_LENGTH})")
    if re.search(r'(?i)(key|token|secret|password)\s*[=:]\s*\S{8,}', request):
        print("Warning: Request may contain sensitive data. Review before proceeding.", file=sys.stderr)
    return request


def _parse_verdict(content: str) -> Optional[str]:
    """Extract verdict from verification output. Returns 'PASS', 'FAIL', or None."""
    # Try 1: Extract ```json ... ``` code block and parse
    block_match = re.search(r'```json\s*\n(.*?)\n\s*```', content, re.DOTALL)
    if block_match:
        try:
            data = json.loads(block_match.group(1))
            verdict = data.get("verdict", "").upper()
            if verdict in ("PASS", "FAIL"):
                return verdict
        except (json.JSONDecodeError, AttributeError):
            pass

    # Try 2: Parse entire content as JSON
    try:
        data = json.loads(content)
        verdict = data.get("verdict", "").upper()
        if verdict in ("PASS", "FAIL"):
            return verdict
    except (json.JSONDecodeError, AttributeError):
        pass

    # Try 3: Regex fallback (last resort)
    match = re.search(r'"verdict"\s*:\s*"(PASS|FAIL)"', content, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return None


def _parse_criteria_results(content: str) -> Optional[list]:
    """Extract criteria_results array from verification JSON output.

    Returns the list if found, or None when the key is absent.
    Tries the ```json block first, then raw JSON, matching _parse_verdict strategy.
    """
    def _extract(text: str) -> Optional[list]:
        try:
            data = json.loads(text)
            if "criteria_results" in data:
                val = data["criteria_results"]
                return val if isinstance(val, list) else None
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    # Try 1: JSON code block
    block_match = re.search(r'```json\s*\n(.*?)\n\s*```', content, re.DOTALL)
    if block_match:
        result = _extract(block_match.group(1))
        if result is not None:
            return result

    # Try 2: raw JSON (entire content)
    return _extract(content)


_EVIDENCE_FILE_LINE_RE = re.compile(r'\w+\.\w+:\d+')


def _validate_criteria_results(
    criteria_results: Optional[list],
    manifest_tasks: list,
) -> tuple[bool, list, list, list]:
    """Cross-reference criteria_results against every acceptance criterion in the manifest.

    Returns (is_valid, missing_criteria, failed_criteria, block_reasons).

    - missing_criteria: AC indices (e.g. "AC-3") present in manifest but absent from results.
    - failed_criteria: criterion labels from results where status is not 'pass',
      intent_match is false, or ship_ready is false.
    - block_reasons: human-readable strings describing each failure dimension.
    - is_valid is True only when criteria_results is present, every manifest AC appears
      in the results, no result has a non-pass status, all intent_match and ship_ready
      flags are true, and evidence depth meets the 80% file:line threshold.

    When the manifest has no acceptance criteria at all, criteria_results is not
    required and the function returns (True, [], [], []).
    """
    # Enumerate all acceptance criteria from the manifest
    all_criteria: list[str] = []
    for task in manifest_tasks:
        for ac in task.get("acceptance_criteria", []):
            all_criteria.append(ac)

    # No ACs defined — nothing to validate
    if not all_criteria:
        return True, [], [], []

    # criteria_results absent when ACs exist — all are missing
    if criteria_results is None:
        missing = [f"AC-{i + 1}" for i in range(len(all_criteria))]
        return False, missing, [], [f"criteria_results missing for: {', '.join(missing)}"]

    # Build a lookup of what the verifier covered (by index label or criterion text)
    covered_indices: set[str] = set()
    failed: list[str] = []
    block_reasons: list[str] = []
    total_evidence = 0
    strong_evidence = 0

    for entry in criteria_results:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("criterion_index", "")
        label = entry.get("criterion", "")
        status = str(entry.get("status", "")).lower()
        intent_match = entry.get("intent_match")
        ship_ready = entry.get("ship_ready")
        evidence = str(entry.get("evidence", ""))
        display = idx or label or str(entry)

        if idx:
            covered_indices.add(str(idx))
        # Also accept plain "AC-N" in the criterion text
        for part in str(label).split():
            if re.match(r'AC-\d+', part, re.IGNORECASE):
                covered_indices.add(part.upper())

        # Status check
        if status not in ("pass", "passed"):
            failed.append(display)
            block_reasons.append(f"{display}: status={status!r}")
        else:
            # Only apply intent_match / ship_ready / evidence checks to passing criteria
            # so that failed criteria don't double-count.
            if intent_match is False:
                if display not in failed:
                    failed.append(display)
                block_reasons.append(
                    f"{display}: intent_match=false — implementation may satisfy the literal AC "
                    "wording but missed what the user actually meant"
                )
            if ship_ready is False:
                if display not in failed:
                    failed.append(display)
                block_reasons.append(
                    f"{display}: ship_ready=false — contains stub, TODO, placeholder, partial "
                    "implementation, or hardcoded workaround; not production-quality"
                )

        # Evidence depth tracking (applies to all entries)
        if evidence:
            total_evidence += 1
            if _EVIDENCE_FILE_LINE_RE.search(evidence):
                strong_evidence += 1

    missing = [f"AC-{i + 1}" for i in range(len(all_criteria)) if f"AC-{i + 1}" not in covered_indices]

    if missing:
        block_reasons.append(f"missing results for: {', '.join(missing)}")

    # Evidence depth check: at least 80% of entries must have file:line references
    if total_evidence > 0:
        strength_ratio = strong_evidence / total_evidence
        if strength_ratio < 0.8:
            weak_count = total_evidence - strong_evidence
            block_reasons.append(
                f"evidence depth too weak: {weak_count}/{total_evidence} entries lack file:line "
                f"references (need ≥80% with 'filename.ext:N' pattern, got "
                f"{strength_ratio:.0%})"
            )

    is_valid = not block_reasons
    return is_valid, missing, failed, block_reasons


def _parse_request_satisfaction(content: str) -> Optional[list]:
    """Extract request_satisfaction array from verification JSON output.

    Returns the list if found, or None when the key is absent.
    Mirrors the _parse_criteria_results strategy (json block, then raw JSON).
    """
    def _extract(text: str) -> Optional[list]:
        try:
            data = json.loads(text)
            if "request_satisfaction" in data:
                val = data["request_satisfaction"]
                return val if isinstance(val, list) else None
        except (json.JSONDecodeError, AttributeError):
            pass
        return None

    # Try 1: JSON code block
    block_match = re.search(r'```json\s*\n(.*?)\n\s*```', content, re.DOTALL)
    if block_match:
        result = _extract(block_match.group(1))
        if result is not None:
            return result

    # Try 2: raw JSON (entire content)
    return _extract(content)


def _validate_request_satisfaction(
    state: dict,
    verify_result: Optional[list],
) -> tuple[bool, list]:
    """Check that every REQ-F-N fragment is fully satisfied.

    Returns (is_satisfied, block_reasons).

    - is_satisfied: True only when every fragment in state['request_fragments']
      has status 'satisfied' in verify_result.
    - block_reasons: human-readable strings for each partial or missing fragment.

    When state has no request_fragments this check is skipped (returns True, []).
    When verify_result is None but fragments exist, all are treated as missing.
    """
    stored_fragments: list[dict] = state.get("request_fragments", [])
    if not stored_fragments:
        return True, []

    # Build lookup by fragment_id
    satisfaction_by_id: dict[str, str] = {}
    if verify_result:
        for entry in verify_result:
            if isinstance(entry, dict):
                fid = entry.get("fragment_id", "")
                status = str(entry.get("status", "")).lower()
                if fid:
                    satisfaction_by_id[fid] = status

    block_reasons: list[str] = []
    for frag in stored_fragments:
        fid = frag.get("id", "")
        ftext = frag.get("text", "")
        status = satisfaction_by_id.get(fid, "missing")
        if status in ("partial", "missing"):
            block_reasons.append(
                f"{fid} ({ftext[:60]!r}): status={status!r} — requirement not fully delivered"
            )

    return not block_reasons, block_reasons


def _validate_tasks(tasks: list) -> list[str]:
    """Validate task schema. Returns list of error messages (empty = valid)."""
    errors = []
    for i, task in enumerate(tasks):
        prefix = f"Task {task.get('id', f'#{i}')}"
        if "id" not in task:
            errors.append(f"{prefix}: missing 'id'")
        if "summary" not in task:
            errors.append(f"{prefix}: missing 'summary'")
        if "files" not in task or not isinstance(task.get("files"), list):
            errors.append(f"{prefix}: missing or invalid 'files' (must be a list)")
        ac = task.get("acceptance_criteria")
        if not ac or not isinstance(ac, list) or not any(ac):
            errors.append(f"{prefix}: missing or empty 'acceptance_criteria' (must be a non-empty list)")
    return errors


# Keywords that signal monetized / downloadable flows
_MONETIZED_SIGNALS = {"checkout", "purchase", "buy", "payment", "stripe", "paywall", "subscribe", "subscription"}
_ASSET_SIGNALS = {"download", "pdf", "ebook", "book", "guide", "asset", "deliverable", "r2", "s3", "bucket"}
_JOURNEY_PHRASES = {"user can", "customer can", "visitor can", "click", "complete purchase", "receive"}


def _warn_manifest_gaps(tasks: list) -> list[str]:
    """Scan manifest tasks for common product-completeness gaps. Returns warnings (non-blocking)."""
    warnings = []
    all_summaries = " ".join(t.get("summary", "").lower() for t in tasks)
    all_acs = " ".join(
        ac.lower() for t in tasks for ac in t.get("acceptance_criteria", [])
    )

    # Check 1: monetized flow without a content/asset task
    has_monetized = any(kw in all_summaries for kw in _MONETIZED_SIGNALS)
    has_asset_task = any(kw in all_summaries for kw in _ASSET_SIGNALS)
    if has_monetized and not has_asset_task:
        warnings.append(
            "Monetized flow detected (checkout/payment) but no task creates the deliverable "
            "content (book, PDF, download asset). Add a task for the thing being sold."
        )

    # Check 2: all ACs are technical (none mention user journeys)
    has_journey_ac = any(phrase in all_acs for phrase in _JOURNEY_PHRASES)
    if tasks and not has_journey_ac:
        warnings.append(
            "All acceptance criteria appear technical (no user-journey language). "
            "Consider adding ACs like 'user can complete purchase and receive the asset'."
        )

    # Check 3: asset references in ACs without a creation task
    for task in tasks:
        for ac in task.get("acceptance_criteria", []):
            ac_lower = ac.lower()
            if any(kw in ac_lower for kw in ("r2", "s3", "bucket", "object key")):
                asset_created = any(
                    any(kw in t.get("summary", "").lower() for kw in _ASSET_SIGNALS)
                    for t in tasks
                )
                if not asset_created:
                    warnings.append(
                        f"Task {task.get('id', '?')}: AC references a storage object but no task creates that asset."
                    )
                break  # one warning per task is enough

    return warnings


def _safe_project_path(state: dict) -> Path:
    """Resolve project path and assert containment within PROJECTS_DIR."""
    raw = state.get("project_path", "")
    path = Path(raw).resolve()
    projects_root = PROJECTS_DIR.resolve()
    if not str(path).startswith(str(projects_root) + os.sep):
        raise ValueError(f"project_path escapes PROJECTS_DIR: {path}")
    return path


# ─── Agent Prompt Generation ────────────────────────────────────────────────

def _build_research_instructions(config: dict) -> str:
    """Build research tool instructions from config."""
    research_tools = config.get("research_tools", {})
    detected = config.get("detected", [])

    lines = []
    if "context7" in detected:
        lines.append("- For library/API documentation: use Context7 MCP (resolve-library-id -> query-docs)")
    if "tavily" in detected:
        lines.append("- For web research on bugs/design/patterns: use Tavily MCP")
    if "brave_search" in detected:
        lines.append("- For web search: use Brave Search MCP")
    lines.append("- Fallback: use WebSearch for anything the above tools don't cover")
    lines.append("- Use WebFetch to read specific URLs when needed")

    return "\n".join(lines)


def generate_plan_agent_prompt(
    agent_type: str,
    request: str,
    project_path: str,
    config: dict,
    *,
    mode: str = "",
    ideation_md: str = "",
    concept_md: str = "",
) -> dict:
    """Generate a deterministic prompt for a plan-phase agent.

    In thorough mode, ideation_md and concept_md are appended as additional
    context so plan agents benefit from earlier IDEATE/CONCEPT_REVIEW outputs.
    In quick mode (or when mode is empty), these are omitted.
    """
    research_instructions = _build_research_instructions(config)

    base_context = (
        f"You are analyzing a codebase to help plan work on this request:\n\n"
        f"REQUEST: {request}\n\n"
        f"PROJECT PATH: {project_path}\n\n"
        f"Write your analysis as markdown. Be specific about file paths, line numbers, "
        f"and concrete findings. Keep your response under 3000 words.\n\n"
        f"IMPORTANT: Do NOT write any files to disk. Return your entire analysis as your "
        f"response text. The orchestrator will save your output."
    )

    # In thorough mode, append ideation and concept synthesis as additional context
    if mode == "thorough":
        if ideation_md:
            base_context += (
                f"\n\n## IDEATION Context\n"
                f"The following IDEATION document was produced during the ideation phase. "
                f"Use it to understand the product concept and strategic direction:\n\n"
                f"{ideation_md}"
            )
        if concept_md:
            base_context += (
                f"\n\n## CONCEPT-SYNTHESIS Context\n"
                f"The following CONCEPT-SYNTHESIS was produced during concept review. "
                f"It contains prioritized feedback from multiple reviewers:\n\n"
                f"{concept_md}"
            )

    prompts = {
        "researcher": {
            "name": "researcher",
            "model": "opus",
            "prompt": (
                f"You are a technical researcher. Your job is to gather facts about the codebase "
                f"and external documentation relevant to the request.\n\n"
                f"{base_context}\n\n"
                f"## Research Tools\n{research_instructions}\n\n"
                f"## Your Deliverable\n"
                f"1. **Codebase Analysis**: Key files, patterns, dependencies relevant to the request\n"
                f"2. **External Research**: Relevant documentation, known issues, best practices\n"
                f"3. **Constraints**: Technical limitations, compatibility concerns, breaking changes\n"
                f"4. **Recommendations**: Specific suggestions based on your research"
            ),
        },
        "sde-iii": {
            "name": "sde-iii",
            "model": "opus",
            "prompt": (
                f"You are a senior software engineer (SDE-III). Your job is to analyze the codebase "
                f"and create a concrete implementation plan.\n\n"
                f"{base_context}\n\n"
                f"## Your Deliverable\n"
                f"1. **Files to Change**: List every file that needs modification with specific changes\n"
                f"2. **Implementation Steps**: Ordered list of changes with dependencies between them\n"
                f"3. **Testing Strategy**: What tests to write, what to verify\n"
                f"4. **Risk Assessment**: What could go wrong, edge cases, breaking changes\n"
                f"5. **Acceptance Criteria**: Testable conditions that prove the work is done"
            ),
        },
        "security-reviewer": {
            "name": "security-reviewer",
            "model": "opus",
            "prompt": (
                f"You are a security reviewer. Your job is to identify security concerns "
                f"in the current code and in the proposed changes.\n\n"
                f"{base_context}\n\n"
                f"## Your Deliverable\n"
                f"1. **Current Vulnerabilities**: Security issues in existing code (with file:line)\n"
                f"2. **Change Risks**: Security implications of the proposed changes\n"
                f"3. **Recommendations**: Specific security improvements, ordered by severity\n"
                f"4. **Compliance**: OWASP Top 10, input validation, auth/authz concerns"
            ),
        },
        "ux-designer": {
            "name": "ux-designer",
            "model": "opus",
            "prompt": (
                f"You are a UX designer. Your job is to evaluate the user experience "
                f"implications of the proposed changes.\n\n"
                f"{base_context}\n\n"
                f"## Your Deliverable\n"
                f"1. **Current UX Assessment**: How the current UI/UX works\n"
                f"2. **Proposed Changes**: UX improvements aligned with the request\n"
                f"3. **Accessibility**: WCAG compliance considerations\n"
                f"4. **User Flows**: Key interaction paths affected by the changes"
            ),
        },
        "architecture-advisor": {
            "name": "architecture-advisor",
            "model": "opus",
            "prompt": (
                f"You are a system architect. Your job is to evaluate the architectural "
                f"implications of the proposed changes.\n\n"
                f"{base_context}\n\n"
                f"## Your Deliverable\n"
                f"1. **Current Architecture**: How the system is structured\n"
                f"2. **Impact Analysis**: How the proposed changes affect the architecture\n"
                f"3. **Alternatives**: Different approaches with trade-offs\n"
                f"4. **Recommendations**: Preferred approach with justification"
            ),
        },
    }

    return prompts.get(agent_type, {
        "name": agent_type,
        "model": "opus",
        "prompt": (
            f"You are a {agent_type}. Analyze the codebase for this request.\n\n"
            f"{base_context}"
        ),
    })


# ─── IDEATE Phase Prompt Generators ──────────────────────────────────────────

def generate_ideate_prompt(request: str, detected_plugins: list[str]) -> str:
    """Generate the brainstorming agent prompt for the IDEATE phase."""
    lines = [
        "You are a product strategist and ideation agent. Your job is to brainstorm",
        "and validate a product concept before any code is written.",
        "",
        f"## User Request",
        f"{request}",
        "",
        "## Business Frameworks",
        "Apply the following frameworks to structure your thinking:",
        "- **Lean Canvas**: Problem, Solution, Key Metrics, Unique Value Proposition,",
        "  Unfair Advantage, Channels, Customer Segments, Cost Structure, Revenue Streams",
        "- **Jobs-to-be-Done (JTBD)**: What job is the user hiring this product to do?",
        "  What are the functional, emotional, and social dimensions?",
        "- **Competitive Moat Analysis**: What makes this defensible? Network effects,",
        "  switching costs, data advantages, brand, or technical moat?",
        "- **Minimum Viable Feature Set**: What is the smallest set of features that",
        "  delivers the core value proposition? Ruthlessly cut scope.",
        "",
        "## Research Requirements",
        "Use web search (WebSearch, Brave Search MCP, or similar) to validate:",
        "- Existing competitors and their positioning",
        "- Market size and trends",
        "- Common pain points users report with existing solutions",
        "- Relevant technology choices and trade-offs",
        "",
    ]

    if detected_plugins:
        lines.append("## Detected Plugins")
        lines.append("The following Claude Code plugins are available and should inform your recommendations:")
        for plugin in detected_plugins:
            lines.append(f"- {plugin}")
        lines.append("")

    lines.extend([
        "## Output Format",
        "Write your output as **IDEATION.md** with these sections:",
        "",
        "# IDEATION",
        "## Concept",
        "## Target Users",
        "## Core Features (MVP)",
        "## Non-Goals (v1)",
        "## Tech Stack Recommendation",
        "## Competitive Landscape",
        "## Business Model",
        "## Detected Plugins",
        "## Open Questions",
        "",
        "Be specific, opinionated, and concise. Prioritize actionable insights over",
        "vague generalizations. Keep the document under 2000 words.",
    ])

    return "\n".join(lines)


def _generate_business_advisor_prompt(request: str, ideation_md: str) -> str:
    """Generate a prompt for the business advisor agent used in concept review."""
    return "\n".join([
        "You are a business advisor reviewing a product concept for viability,",
        "monetization potential, and competitive positioning.",
        "",
        f"## Original Request",
        f"{request}",
        "",
        f"## IDEATION Document",
        f"{ideation_md}",
        "",
        "## Your Review Focus",
        "1. **Viability Assessment**: Is this concept technically and commercially viable?",
        "   What are the biggest risks?",
        "2. **Monetization Strategy**: Evaluate the proposed business model. Suggest",
        "   alternatives if the current approach is weak.",
        "3. **Competitive Positioning**: How does this differentiate from existing solutions?",
        "   Is the moat real or imagined?",
        "4. **Go-to-Market**: What is the simplest path to first paying customers?",
        "",
        "## Output Format",
        "Prioritize your feedback using:",
        "- **P0** (Critical): Must address before building anything",
        "- **P1** (Important): Should address in v1",
        "- **P2** (Nice-to-have): Can defer to v2+",
        "",
        "Be direct. If the idea has fatal flaws, say so clearly.",
    ])


def _generate_ui_concept_prompt(request: str, ideation_md: str) -> str:
    """Generate a prompt for UI concept generation when frontend-design is detected."""
    return "\n".join([
        "You are a UI/UX design consultant generating interface concepts",
        "for a new product.",
        "",
        f"## Original Request",
        f"{request}",
        "",
        f"## IDEATION Document",
        f"{ideation_md}",
        "",
        "## Your Design Focus",
        "1. **Information Architecture**: How should the UI be organized? What are the",
        "   primary navigation patterns and page hierarchy?",
        "2. **Core Screens**: Describe the 3-5 most important screens/views with their",
        "   key elements and user interactions.",
        "3. **Design System Foundations**: Recommend typography, color palette direction,",
        "   spacing system, and component library approach.",
        "4. **Responsive Strategy**: How should the interface adapt across devices?",
        "5. **Accessibility**: WCAG 2.1 AA compliance considerations from day one.",
        "",
        "## Output Format",
        "For each core screen, provide:",
        "- Screen name and purpose",
        "- Key UI components and their layout",
        "- Primary user actions available",
        "- Design rationale",
        "",
        "Focus on clarity and usability over visual flourish. The goal is a solid",
        "structural foundation that developers can implement efficiently.",
    ])


# ─── Concept Review Agents ───────────────────────────────────────────────────

def generate_concept_review_agents(
    request: str,
    ideation_md: str,
    personas: list[dict],
    detected_plugins: list[str],
) -> list[dict]:
    """Generate concept review agents: one per persona, a business advisor, and optionally a UI designer.

    Each agent gets CLEAN context — no other agent's output appears in its prompt.
    """
    agents: list[dict] = []

    # One agent per persona
    for persona in personas:
        name = persona.get("name", "Unknown")
        slug = _slugify(name)
        agent_name = f"persona-{slug}"

        # Build persona markdown for the review prompt
        if generate_persona_template:
            persona_md = generate_persona_template(persona)
        else:
            persona_md = f"# Persona: {name}\nRole: {persona.get('role', 'User')}\n"

        if generate_persona_review_prompt:
            prompt = generate_persona_review_prompt(persona_md, request)
        else:
            prompt = (
                f"Review this project as {name} ({persona.get('role', 'User')}).\n\n"
                f"Request: {request}\n\nIDEATION:\n{ideation_md}\n"
            )

        agents.append({"name": agent_name, "model": "sonnet", "prompt": prompt})

    # Always include business advisor
    biz_prompt = _generate_business_advisor_prompt(request, ideation_md)
    agents.append({"name": "business-advisor", "model": "sonnet", "prompt": biz_prompt})

    # UI concept designer only when frontend-design plugin is detected
    if "frontend-design" in detected_plugins:
        ui_prompt = _generate_ui_concept_prompt(request, ideation_md)
        agents.append({"name": "ui-concept-designer", "model": "sonnet", "prompt": ui_prompt})

    return agents


def synthesize_concept_reviews(reviews: dict[str, str]) -> str:
    """Consolidate concept review outputs into CONCEPT-SYNTHESIS.md content."""
    severity_pattern = re.compile(r'\[P([012])\]\s*(.*)')

    findings: dict[str, list[tuple[str, str]]] = {"P0": [], "P1": [], "P2": []}

    for agent_name, content in reviews.items():
        for line in content.splitlines():
            m = severity_pattern.search(line)
            if m:
                level = f"P{m.group(1)}"
                detail = m.group(2).strip()
                findings[level].append((agent_name, detail))

    sections = [
        ("P0", "Critical"),
        ("P1", "Important"),
        ("P2", "Suggestions"),
    ]

    lines = ["# CONCEPT-SYNTHESIS", ""]
    for level, label in sections:
        lines.append(f"## {level} — {label}")
        lines.append("")
        items = findings[level]
        if items:
            for agent_name, detail in items:
                lines.append(f"- **[{agent_name}]** {detail}")
        else:
            lines.append("No findings.")
        lines.append("")

    return "\n".join(lines)


# ─── Manifest & Parallel Groups ─────────────────────────────────────────────

def compute_parallel_groups(tasks: list[dict]) -> list[list[str]]:
    """
    Compute parallel execution groups based on file overlap.
    Tasks sharing files are sequential. Tasks with no overlap are grouped.
    """
    if not tasks:
        return []

    task_files: dict[str, set[str]] = {}
    for task in tasks:
        tid = task["id"]
        files = set(task.get("files", []))
        task_files[tid] = files

    task_ids = [t["id"] for t in tasks]

    # Build dependency graph from task depends_on + file overlap
    depends_on: dict[str, set[str]] = {}
    for task in tasks:
        tid = task["id"]
        depends_on[tid] = set(task.get("depends_on", []))

    # Add file-overlap dependencies (earlier task blocks later)
    for i, tid_a in enumerate(task_ids):
        for tid_b in task_ids[i + 1:]:
            if task_files[tid_a] & task_files[tid_b]:
                depends_on[tid_b].add(tid_a)

    # Topological grouping: group tasks whose deps are all in prior groups
    groups: list[list[str]] = []
    placed: set[str] = set()
    remaining = set(task_ids)

    while remaining:
        ready = [tid for tid in remaining if depends_on[tid].issubset(placed)]
        if not ready:
            # Circular dependency — break by placing first remaining
            ready = [sorted(remaining)[0]]
        groups.append(sorted(ready))
        placed.update(ready)
        remaining -= set(ready)

    return groups


_NPM_SCRIPT_PRIORITY = [
    "typecheck", "type-check", "tsc",
    "lint",
    "test", "test:unit", "test:integration",
    "check", "validate",
]


_LINTER_CONFIGS = {
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", ".eslintrc.yaml",
    "eslint.config.js", "eslint.config.mjs", "eslint.config.ts",
    "biome.json", "biome.jsonc", ".prettierrc", ".prettierrc.json",
}

_UNSUPPORTED_SHELL_OPS = re.compile(r'[|;]|>>?|<<|`|\$\(')


def _is_safe_gate_cwd(cwd: str) -> bool:
    """Check that a CWD path is contained within PROJECT_ROOT."""
    try:
        resolved = Path(cwd).resolve()
        proj_root = PROJECT_ROOT.resolve()
        return str(resolved).startswith(str(proj_root) + os.sep) or resolved == proj_root
    except (OSError, ValueError):
        return False


def _check_linter_effective(directory: Path) -> bool:
    """Check if a linter config exists in the directory."""
    for config_name in _LINTER_CONFIGS:
        if (directory / config_name).exists():
            return True
    return False


def _run_shell_chain(cmd: str, cwd: str, timeout: int = 120) -> tuple[int, str]:
    """Run a '&&'-chained command string without invoking a shell.

    Splits cmd on ' && ' and executes each sub-command sequentially via
    shlex.split() + shell=False. Aborts on the first non-zero exit code,
    mirroring && semantics. Returns (returncode, combined_output).

    Only supports '&&' chains of simple commands. Pipes, redirects, semicolons,
    and other shell operators are rejected with ValueError.

    Raises ValueError if cmd contains unsupported shell operators.
    Raises subprocess.TimeoutExpired if any single sub-command exceeds timeout.
    Raises OSError if a sub-command binary is not found.
    """
    if _UNSUPPORTED_SHELL_OPS.search(cmd):
        raise ValueError(
            f"_run_shell_chain does not support shell operators (|, ;, >, etc.) in: {cmd!r}"
        )
    MAX_OUTPUT = 2000
    sub_commands = [part.strip() for part in cmd.split(" && ")]
    combined_output = []
    for sub_cmd in sub_commands:
        args = shlex.split(sub_cmd)
        result = subprocess.run(
            args, shell=False, cwd=cwd,
            capture_output=True, text=True, timeout=timeout,
        )
        combined_output.append(result.stdout + result.stderr)
        if result.returncode != 0:
            return result.returncode, "".join(combined_output)[-MAX_OUTPUT:]
    return 0, "".join(combined_output)[-MAX_OUTPUT:]


def _detect_quality_gate_in(directory: Path) -> dict:
    """Try to detect a quality gate rooted at *directory*. Returns {} on miss."""
    pkg_json = directory / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            parts = [f"npm run {name}" for name in _NPM_SCRIPT_PRIORITY if name in scripts]
            if parts:
                return {"cmd": " && ".join(parts), "cwd": str(directory)}
        except (json.JSONDecodeError, OSError):
            pass

    if (directory / "pytest.ini").exists() or (directory / "pyproject.toml").exists():
        return {"cmd": "python3 -m pytest", "cwd": str(directory)}

    if (directory / "Cargo.toml").exists():
        return {"cmd": "cargo test", "cwd": str(directory)}

    if (directory / "go.mod").exists():
        return {"cmd": "go test ./...", "cwd": str(directory)}

    if (directory / "Makefile").exists():
        return {"cmd": "make test", "cwd": str(directory)}

    return {}


def detect_quality_gate(site_dir: str | None = None) -> dict:
    """Detect project test infrastructure and return quality gate info.

    Args:
        site_dir: Optional explicit site directory to scan first.
                  Must be contained within PROJECT_ROOT.

    Returns dict with cmd, cwd, and effective fields.
    """
    if site_dir:
        resolved = Path(site_dir).resolve()
        proj_root = PROJECT_ROOT.resolve()
        if not (str(resolved).startswith(str(proj_root) + os.sep) or resolved == proj_root):
            return {}
        result = _detect_quality_gate_in(resolved)
        if result:
            result["effective"] = _check_linter_effective(resolved)
            return result

    result = _detect_quality_gate_in(PROJECT_ROOT)
    if result:
        result["effective"] = _check_linter_effective(PROJECT_ROOT)
        return result

    try:
        for subdir in sorted(PROJECT_ROOT.iterdir()):
            if subdir.is_dir() and not subdir.name.startswith("."):
                resolved_sub = subdir.resolve()
                proj_root = PROJECT_ROOT.resolve()
                if not str(resolved_sub).startswith(str(proj_root) + os.sep):
                    continue
                result = _detect_quality_gate_in(resolved_sub)
                if result:
                    result["effective"] = _check_linter_effective(resolved_sub)
                    return result
    except OSError:
        pass

    return {}


# ─── Project Management ─────────────────────────────────────────────────────

def _next_project_id() -> str:
    """Generate next sequential project ID."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(PROJECTS_DIR.iterdir()) if PROJECTS_DIR.exists() else []
    max_num = 0
    for d in existing:
        if d.is_dir():
            match = re.match(r"(\d+)-", d.name)
            if match:
                max_num = max(max_num, int(match.group(1)))
    return str(max_num + 1).zfill(3)


def _slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    slug = re.sub(r'[^a-z0-9\s-]', '', text.lower())
    slug = re.sub(r'[\s]+', '-', slug.strip())
    return slug[:50]


def _init_project(request: str, target_dir: Optional[str] = None) -> dict:
    """Initialize a new project directory and state."""
    num = _next_project_id()
    slug = _slugify(request)
    project_id = f"{num}-{slug}"
    project_path = PROJECTS_DIR / project_id

    # Resolve target directory for implementation files
    if target_dir:
        td = Path(target_dir)
        if not td.is_absolute():
            td = PROJECT_ROOT / td
        td.mkdir(parents=True, exist_ok=True)
        target_directory = str(td)
    else:
        target_directory = str(PROJECT_ROOT)

    # Create project directories (mode defaults to thorough; cmd_plan may
    # call init_project_directory again with the actual mode after init)
    init_project_directory(str(project_path), mode="thorough")

    # Initialize state
    state = {
        "project_id": project_id,
        "project_path": str(project_path),
        "request": request,
        "target_directory": target_directory,
        "mode": "pipeline",
        "phase": "PLAN",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "heal_attempts": 0,
        "circuit_breakers": {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}},
        "pipeline_version": __version__,
    }

    with qralph_state.exclusive_state_lock():
        qralph_state.save_state(state)

    # Write initial decisions.log
    log_path = project_path / "decisions.log"
    qralph_state.safe_write(log_path, f"[{datetime.now().isoformat()}] INIT: Project created — {request}\n")

    return state


def _log_decision(project_path: Path, message: str):
    """Append to decisions.log (append-mode, lock-protected)."""
    log_path = project_path / "decisions.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, 'a') as f:
            qralph_state._lock_file(f, exclusive=True)
            try:
                f.write(f"[{datetime.now().isoformat()}] {message}\n")
                f.flush()
            finally:
                qralph_state._unlock_file(f)
    except OSError:
        pass


def _save_checkpoint(project_path: Path, state: dict):
    """Save state checkpoint for crash recovery."""
    checkpoint_dir = project_path / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_file = checkpoint_dir / "state.json"
    qralph_state.safe_write_json(checkpoint_file, state)


# ─── Story Point Estimation ──────────────────────────────────────────────────

# Ordered from smallest to largest — estimate_story_points() snaps to this scale.
_SP_SCALE = [0.05, 0.1, 0.2, 0.3, 0.5, 0.8, 1, 2, 3, 5]

_ACTION_VERBS = {
    "add", "create", "build", "implement", "fix", "update", "refactor",
    "migrate", "redesign", "integrate", "deploy", "configure",
}

_DOMAIN_SIGNALS = {
    # Require more specific terms to avoid false positives on generic words
    # (e.g. "server" alone triggers for "hello world server" — use "backend"/"api"/"endpoint" instead)
    "frontend":  ("frontend", "ui component", "css", "html", "react", "vue", "svelte", "angular", "tailwind"),
    "backend":   ("backend", "rest api", "graphql", "endpoint", "route handler", "controller", "microservice"),
    "database":  ("database", "db migration", "schema migration", "orm", "sql query", "postgres", "mysql", "mongo"),
    "security":  ("oauth", "jwt", "authentication", "authorization", "encryption", "rbac", "permission system"),
    "infra":     ("docker", "kubernetes", "ci/cd", "terraform", "aws", "gcp", "azure", "pipeline"),
    "testing":   ("test suite", "coverage", "tdd", "e2e test", "integration test", "unit test"),
}

# File-extension pattern — each distinct extension in the request adds to complexity
_EXT_PATTERN = re.compile(r'\.\w{1,6}\b')


def estimate_story_points(request: str) -> float:
    """Estimate task complexity on the coding SP scale.

    Uses heuristics rather than an LLM to keep the fast-path cheap and
    deterministic.  The returned value is always a member of _SP_SCALE.

    Signals and their weights
    -------------------------
    word_count         — baseline complexity proxy
    action_verb_count  — each distinct action verb adds breadth
    file_ext_count     — each distinct file extension mentioned adds scope
    domain_breadth     — number of distinct domains touched (frontend/backend/…)
    """
    lower = request.lower()
    words = lower.split()

    # --- individual signals (raw counts / booleans) --------------------------
    word_count = len(words)

    verbs_found = {v for v in _ACTION_VERBS if v in words}
    action_verb_count = len(verbs_found)

    exts_found = set(_EXT_PATTERN.findall(lower))
    file_ext_count = len(exts_found)

    # Multi-word domain signals checked against the full request string
    domains_touched = sum(
        1 for signals in _DOMAIN_SIGNALS.values()
        if any(sig in lower for sig in signals)
    )

    # --- combine into a raw complexity score ---------------------------------
    # Calibrated against these anchors:
    #   "fix typo in README"                               → raw ~1.2 → SP 0.05
    #   "create a hello world nodejs http server"          → raw ~1.5 → SP 0.1
    #   "add unit tests for existing auth module"          → raw ~2.5 → SP 0.2
    #   "build auth system with OAuth, DB migration, FE"  → raw ~5.5 → SP 1
    #   large multi-domain, multi-verb redesign            → raw 9+   → SP 3+
    score = (
        (word_count / 10)          # 1 point per 10 words
        + action_verb_count * 0.8  # each extra action verb signals scope
        + file_ext_count * 0.5     # each file type adds a touch of breadth
        + domains_touched * 2.0    # cross-domain tasks are substantially harder
    )

    # Map continuous score to SP.  Each entry means "if score < threshold → return sp".
    breakpoints = [
        (1.5,  0.05),
        (2.0,  0.1),
        (3.0,  0.2),
        (4.0,  0.3),
        (5.0,  0.5),
        (6.5,  0.8),
        (8.0,  1),
        (11.0, 2),
        (15.0, 3),
    ]
    for threshold, sp in breakpoints:
        if score < threshold:
            return sp
    return 5.0


# ─── Adaptive Cost Budgeting ─────────────────────────────────────────────────

_BUDGET_TIERS = {
    "simple":   {"thorough": 5.0,  "quick": 2.0},
    "moderate": {"thorough": 25.0, "quick": 5.0},
    "complex":  {"thorough": 75.0, "quick": 15.0},
}


def calculate_adaptive_budget(estimated_sp: float, mode: str) -> float:
    """Calculate cost budget based on story point estimate and mode.

    Budget tiers:
        Simple   (SP <= 2):  thorough=$5,  quick=$2
        Moderate (3 <= SP <= 8): thorough=$25, quick=$5
        Complex  (SP > 8):  thorough=$75, quick=$15

    Returns a budget that scales linearly within the tier range.
    """
    if estimated_sp <= 2:
        tier = "simple"
        # Linearly interpolate within tier: SP 0..2 maps to 40%..100% of tier max
        fraction = 0.4 + 0.6 * (estimated_sp / 2.0)
    elif estimated_sp <= 8:
        tier = "moderate"
        # SP 3..8 maps to 40%..100% of tier max
        fraction = 0.4 + 0.6 * ((estimated_sp - 3.0) / 5.0)
    else:
        tier = "complex"
        # SP 9..21 maps to 40%..100% of tier max
        fraction = 0.4 + 0.6 * min((estimated_sp - 9.0) / 12.0, 1.0)

    return round(_BUDGET_TIERS[tier][mode] * fraction, 2)


# ─── Quality Agent Selection ─────────────────────────────────────────────────

def select_quality_agents(estimated_sp: float, personas: list[dict], mode: str) -> list[dict]:
    """Select review agents based on task complexity and mode.

    Quick mode: always code-reviewer + security-reviewer (2 agents).
    Thorough mode scales with SP:
      - Simple (<=2): code-reviewer, test-verifier
      - Moderate (3-8): code-reviewer, security-reviewer, pe-architect, 1 persona
      - Complex (>8): All 7 core agents + persona reviewers
    """
    if mode == "quick":
        return [
            {"name": "code-reviewer", "model": "sonnet", "role": "Code quality and style review"},
            {"name": "security-reviewer", "model": "sonnet", "role": "Security vulnerability analysis"},
        ]

    if estimated_sp <= 2:
        return [
            {"name": "code-reviewer", "model": "sonnet", "role": "Code quality and style review"},
            {"name": "test-verifier", "model": "sonnet", "role": "Test coverage and correctness verification"},
        ]

    if estimated_sp <= 8:
        agents = [
            {"name": "code-reviewer", "model": "sonnet", "role": "Code quality and style review"},
            {"name": "security-reviewer", "model": "sonnet", "role": "Security vulnerability analysis"},
            {"name": "pe-architect", "model": "sonnet", "role": "Architecture and performance review"},
        ]
        if personas:
            p = personas[0]
            slug = _slugify(p.get("name", "user"))
            agents.append({"name": f"persona-{slug}", "model": "sonnet", "role": f"Review as {p.get('name', 'User')}"})
        return agents

    # Complex (>8)
    agents = [
        {"name": "pe-architect", "model": "sonnet", "role": "Architecture and performance review"},
        {"name": "failure-analyst", "model": "sonnet", "role": "Failure mode and edge case analysis"},
        {"name": "security-reviewer", "model": "sonnet", "role": "Security vulnerability analysis"},
        {"name": "usability-reviewer", "model": "sonnet", "role": "Usability and accessibility review"},
        {"name": "business-advisor", "model": "sonnet", "role": "Business impact and requirements alignment"},
        {"name": "code-reviewer", "model": "sonnet", "role": "Code quality and style review"},
    ]
    for p in personas:
        slug = _slugify(p.get("name", "user"))
        agents.append({"name": f"persona-{slug}", "model": "sonnet", "role": f"Review as {p.get('name', 'User')}"})
    return agents


def max_discovery_rounds(estimated_sp: float, override: int = 0) -> int:
    """Return maximum quality discovery rounds based on SP complexity.

    Simple (<=2): 2 rounds
    Moderate (3-8): 3 rounds
    Complex (>8): 3 rounds (overridable up to hard cap of 5)
    """
    if estimated_sp <= 2:
        return 2
    if estimated_sp <= 8:
        return 3
    # Complex
    if override > 0:
        return min(override, 5)
    return 3


# ─── Project Directory Structure ────────────────────────────────────────────

_BASE_DIRS = [
    "agent-outputs",
    "execution-outputs",
    "verification",
    "checkpoints",
    "quality-reports",
]

_THOROUGH_ONLY_DIRS = [
    "personas",
    "concept-reviews",
]


def init_project_directory(project_path: str, mode: str = "thorough") -> None:
    """Create the v2 project directory structure.

    Both modes create: agent-outputs, execution-outputs, verification,
    checkpoints, quality-reports.

    Thorough mode additionally creates: personas, concept-reviews.
    """
    root = Path(project_path)
    root.mkdir(parents=True, exist_ok=True)

    for d in _BASE_DIRS:
        (root / d).mkdir(exist_ok=True)

    if mode == "thorough":
        for d in _THOROUGH_ONLY_DIRS:
            (root / d).mkdir(exist_ok=True)


# ─── Pipeline Commands ───────────────────────────────────────────────────────

def cmd_plan(request: str, target_dir: Optional[str] = None, mode: str = "thorough") -> dict:
    """Initialize project, suggest template, generate plan agent configs.

    For requests estimated below 0.2 SP the function fast-tracks to a single
    sde-iii agent instead of spawning the full multi-agent planning team.

    Args:
        mode: "thorough" starts at IDEATE phase, "quick" starts at PLAN phase.
    """
    # Validate mode
    if mode not in ("thorough", "quick"):
        return {"action": "error", "error": f"Invalid mode '{mode}'. Must be 'thorough' or 'quick'."}

    # Load or create config
    config = qralph_config.load_config()
    if not config:
        try:
            qralph_config.cmd_setup()
        except Exception as e:
            return {"error": f"Configuration setup failed: {e}. Check disk space and permissions on .qralph/"}
        config = qralph_config.load_config()
        if not config:
            return {"error": "Configuration setup failed. Check disk space and permissions on .qralph/"}

    # Init project
    request = _sanitize_request(request)
    state = _init_project(request, target_dir=target_dir)
    project_path = Path(state["project_path"])

    # Acquire session lock — hooks use this to enforce deterministic flow
    _acquire_session_lock()
    try:

        # Set starting phase based on mode
        if mode == "thorough":
            state["phase"] = "IDEATE"
            starting_sub_phase = "IDEATE_BRAINSTORM"
        else:
            state["phase"] = "PLAN"
            starting_sub_phase = "INIT"

        # Story-point estimate — must happen before agent generation
        estimated_sp = estimate_story_points(request)
        _log_decision(project_path, f"SP-ESTIMATE: {estimated_sp} for '{request[:80]}'")

        # Adaptive cost budget
        budget = calculate_adaptive_budget(estimated_sp, mode)
        state["circuit_breakers"]["budget_usd"] = budget
        _log_decision(project_path, f"BUDGET: ${budget} (SP={estimated_sp}, mode={mode})")

        # Re-initialize project dirs with correct mode (quick skips personas/concept-reviews)
        init_project_directory(str(project_path), mode=mode)

        # Suggest template (used by both paths for metadata)
        suggested, scores = suggest_template(request)
        template = TASK_TEMPLATES[suggested]

        # Fragment the request for deterministic requirements tracking — stored in state
        # so they persist across all phases and retries without re-parsing.
        request_fragments = _fragment_request(request)
        state["request_fragments"] = [
            {"id": frag_id, "text": frag_text}
            for frag_id, frag_text in request_fragments
        ]
        _log_decision(
            project_path,
            f"FRAGMENTS: {len(request_fragments)} requirement fragments extracted"
        )

        # ── Fast-track: trivial tasks skip multi-agent planning ──────────────────
        if estimated_sp < 0.2:
            agent_config = generate_plan_agent_prompt(
                "sde-iii", request, str(project_path), config
            )
            agents = [agent_config]

            state["agents"] = [agent_config["name"]]
            state["template"] = suggested
            state["estimated_sp"] = estimated_sp
            state["pipeline"] = {
                "mode": mode,
                "sub_phase": starting_sub_phase,
                "plan_agents": agents,
                "execution_groups": [],
                "current_group_index": 0,
                "single_agent_mode": True,
            }
            with qralph_state.exclusive_state_lock():
                qralph_state.save_state(state)

            _save_checkpoint(project_path, state)
            _log_decision(
                project_path,
                f"PLAN: Fast-track (SP={estimated_sp} < 0.2, mode={mode}) — single sde-iii agent, "
                f"template='{suggested}'"
            )

            return {
                "status": "plan_ready",
                "project_id": state["project_id"],
                "project_path": str(project_path),
                "phase": state["phase"],
                "suggested_template": suggested,
                "template_description": template["description"],
                "all_templates": {k: v["description"] for k, v in TASK_TEMPLATES.items()},
                "scores": scores,
                "agents": agents,
                "estimated_sp": estimated_sp,
                "fast_track": True,
                "pipeline": state["pipeline"],
                "research_config": config.get("research_tools", {}),
            }

        # ── Full multi-agent planning path ───────────────────────────────────────
        # 1. Start from template agents, enforce mandatory critical agents.
        # 2. Classify request domains and prune agents with zero domain overlap.
        #    This removes ux-designer from backend requests, security-reviewer
        #    from UI-only requests, and architecture-advisor for SP < 0.5.
        request_domains = _classify_request_domains(request)
        base_agent_types = _enforce_critical_agents(template["plan_agents"])
        plan_agent_types = _filter_agents_by_relevance(base_agent_types, request_domains, estimated_sp)

        # In thorough mode, load IDEATION.md and CONCEPT-SYNTHESIS.md for plan agent context
        ideation_md = ""
        concept_md = ""
        if mode == "thorough":
            ideation_path = project_path / "IDEATION.md"
            concept_path = project_path / "CONCEPT-SYNTHESIS.md"
            if ideation_path.exists():
                ideation_md = ideation_path.read_text().strip()
            if concept_path.exists():
                concept_md = concept_path.read_text().strip()

        agents = []
        for agent_type in plan_agent_types:
            agent_config = generate_plan_agent_prompt(
                agent_type, request, str(project_path), config,
                mode=mode, ideation_md=ideation_md, concept_md=concept_md,
            )
            agents.append(agent_config)

        state["agents"] = [a["name"] for a in agents]
        state["template"] = suggested
        state["estimated_sp"] = estimated_sp
        state["pipeline"] = {
            "mode": mode,
            "sub_phase": starting_sub_phase,
            "plan_agents": agents,
            "execution_groups": [],
            "current_group_index": 0,
            "single_agent_mode": False,
        }
        with qralph_state.exclusive_state_lock():
            qralph_state.save_state(state)

        _save_checkpoint(project_path, state)
        _log_decision(
            project_path,
            f"PLAN: Template '{suggested}' suggested (SP={estimated_sp}, mode={mode}, "
            f"domains={request_domains}, agents={plan_agent_types}, scores: {scores})"
        )

        return {
            "status": "plan_ready",
            "project_id": state["project_id"],
            "project_path": str(project_path),
            "phase": state["phase"],
            "suggested_template": suggested,
            "template_description": template["description"],
            "all_templates": {k: v["description"] for k, v in TASK_TEMPLATES.items()},
            "scores": scores,
            "agents": agents,
            "estimated_sp": estimated_sp,
            "fast_track": False,
            "pipeline": state["pipeline"],
            "research_config": config.get("research_tools", {}),
        }
    except BaseException:
        _release_session_lock()
        raise


def cmd_plan_collect() -> dict:
    """Read agent-outputs/, compute execution manifest, write manifest.json + PLAN.md."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project. Run 'plan' first."}

    if state.get("phase") != "PLAN":
        return {"error": f"Cannot plan-collect in phase {state.get('phase')}. Must be in PLAN."}

    project_path = _safe_project_path(state)
    outputs_dir = project_path / "agent-outputs"

    # Read all agent outputs (sanitized against prompt injection)
    agent_analyses = {}
    missing_agents = []
    for agent_name in state.get("agents", []):
        output_file = outputs_dir / f"{agent_name}.md"
        if output_file.exists():
            content = _sanitize_agent_output(output_file.read_text().strip())
            if content:
                agent_analyses[agent_name] = content
            else:
                missing_agents.append(agent_name)
        else:
            missing_agents.append(agent_name)

    if not agent_analyses:
        return {"error": "No agent outputs found. Write agent results to agent-outputs/ first."}

    # Detect quality gate
    quality_gate = detect_quality_gate()

    # Build manifest skeleton — Claude fills in the actual tasks after reviewing the analyses
    manifest = {
        "project_id": state["project_id"],
        "request": state["request"],
        "template": state.get("template", "research"),
        "target_directory": state.get("target_directory", str(PROJECT_ROOT)),
        "agent_analyses": list(agent_analyses.keys()),
        "missing_agents": missing_agents,
        "tasks": [],  # Claude fills these in based on agent analyses
        "parallel_groups": [],
        "quality_gate_cmd": quality_gate.get("cmd", ""),
        "quality_gate_cwd": quality_gate.get("cwd", ""),
        "created_at": datetime.now().isoformat(),
    }

    # Write agent analyses summary for Claude to parse
    analyses_summary = "## Agent Analyses\n\n"
    for name, content in agent_analyses.items():
        analyses_summary += f"### {name}\n\n{content}\n\n---\n\n"

    analyses_summary += (
        "## Task Definition Rules\n\n"
        "- Name tasks as user outcomes, not technical components. "
        "\"Customer receives book after purchase\" not \"Add Stripe checkout route.\"\n"
        "- For every monetized flow (checkout, purchase, subscription), include BOTH:\n"
        "  (a) a task to create the deliverable content/asset being sold\n"
        "  (b) an AC stating \"user can complete purchase and receive the asset\"\n"
        "- For every download or storage asset referenced in code, include an AC: "
        "\"asset exists at expected storage path\"\n"
        "- Include at least one user-journey AC per user-facing flow: "
        "\"user can click X, complete Y, and see Z\"\n\n"
    )

    # Write manifest (skeleton — tasks to be filled by Claude)
    manifest_path = project_path / "manifest.json"
    qralph_state.safe_write_json(manifest_path, manifest)

    # Write PLAN.md with agent analyses for user review
    plan_md = f"# Execution Plan: {state['request']}\n\n"
    plan_md += f"**Template**: {state.get('template', 'research')}\n"
    plan_md += f"**Agents**: {', '.join(agent_analyses.keys())}\n"
    if missing_agents:
        plan_md += f"**Missing agents**: {', '.join(missing_agents)} (skipped)\n"
    plan_md += f"\n{analyses_summary}"
    if quality_gate:
        plan_md += f"\n## Quality Gate\n\n```\n{quality_gate}\n```\n"
    plan_md += (
        "\n## Next Steps\n\n"
        "Review the agent analyses above. Then define execution tasks by updating "
        "manifest.json with concrete tasks, files, and acceptance criteria.\n"
    )

    plan_path = project_path / "PLAN.md"
    qralph_state.safe_write(plan_path, plan_md)

    _log_decision(project_path, f"PLAN-COLLECT: {len(agent_analyses)} agents reported, {len(missing_agents)} missing")
    _save_checkpoint(project_path, state)

    return {
        "status": "manifest_ready",
        "project_id": state["project_id"],
        "manifest_path": str(manifest_path),
        "plan_path": str(plan_path),
        "agents_reported": list(agent_analyses.keys()),
        "agents_missing": missing_agents,
        "quality_gate_cmd": quality_gate,
        "analyses_summary": analyses_summary,
    }


def cmd_plan_finalize() -> dict:
    """Finalize the plan after user approves and tasks are defined in manifest."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project."}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"error": str(e)}
    manifest_path = project_path / "manifest.json"

    if not manifest_path.exists():
        return {"error": "No manifest.json found. Run plan-collect first."}

    manifest = qralph_state.safe_read_json(manifest_path, {})
    tasks = manifest.get("tasks", [])

    if not tasks:
        return {"error": "No tasks defined in manifest.json. Define tasks before finalizing."}

    # Validate task schema
    task_errors = _validate_tasks(tasks)
    if task_errors:
        return {"error": f"Invalid tasks in manifest.json: {'; '.join(task_errors)}"}

    # Compute parallel groups from tasks
    groups = compute_parallel_groups(tasks)
    manifest["parallel_groups"] = groups
    qralph_state.safe_write_json(manifest_path, manifest)

    # Generate readable PLAN.md
    plan_md = f"# Execution Plan: {state['request']}\n\n"
    for task in tasks:
        plan_md += f"### Task {task['id']}: {task.get('summary', 'Untitled')}\n"
        if task.get("files"):
            plan_md += f"- **Files**: {', '.join(task['files'])}\n"
        if task.get("depends_on"):
            plan_md += f"- **Depends on**: {', '.join(task['depends_on'])}\n"
        if task.get("acceptance_criteria"):
            for ac in task["acceptance_criteria"]:
                plan_md += f"- **Acceptance**: {ac}\n"
        plan_md += f"- **Tests needed**: {'Yes' if task.get('tests_needed', True) else 'No'}\n\n"

    plan_md += "### Execution Order\n\n"
    for i, group in enumerate(groups, 1):
        if len(group) == 1:
            plan_md += f"{i}. [{group[0]}] solo\n"
        else:
            plan_md += f"{i}. [{', '.join(group)}] parallel (worktree isolation)\n"

    if manifest.get("quality_gate_cmd"):
        plan_md += f"\n### Quality Gate\n\n```\n{manifest['quality_gate_cmd']}\n```\n"

    plan_path = project_path / "PLAN.md"
    qralph_state.safe_write(plan_path, plan_md)

    # Transition to EXECUTE phase
    with qralph_state.exclusive_state_lock():
        state = qralph_state.load_state()
        state["phase"] = "EXECUTE"
        qralph_state.save_state(state)

    _log_decision(project_path, f"PLAN-FINALIZE: {len(tasks)} tasks, {len(groups)} groups, transitioning to EXECUTE")
    _save_checkpoint(project_path, state)

    return {
        "status": "plan_finalized",
        "project_id": state["project_id"],
        "tasks": len(tasks),
        "groups": groups,
        "plan_path": str(plan_path),
        "phase": "EXECUTE",
    }


def cmd_execute() -> dict:
    """Read manifest, compute parallel groups, generate implementation agent prompts."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project."}

    if state.get("phase") != "EXECUTE":
        return {"error": f"Cannot execute in phase {state.get('phase')}. Must be in EXECUTE."}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"error": str(e)}
    manifest_path = project_path / "manifest.json"

    if not manifest_path.exists():
        return {"error": "No manifest.json. Run plan-collect and plan-finalize first."}

    manifest = qralph_state.safe_read_json(manifest_path, {})
    tasks = manifest.get("tasks", [])
    groups = manifest.get("parallel_groups", [])
    quality_gate = manifest.get("quality_gate_cmd", "")

    if not tasks:
        return {"error": "No tasks in manifest. Define tasks first."}

    # Build task lookup
    task_map = {t["id"]: t for t in tasks}

    # Cap group sizes to MAX_PARALLEL_AGENTS
    capped_groups = []
    for group_ids in groups:
        for i in range(0, len(group_ids), MAX_PARALLEL_AGENTS):
            capped_groups.append(group_ids[i:i + MAX_PARALLEL_AGENTS])
    groups = capped_groups

    # Generate agent configs for each group
    execution_groups = []
    for group_ids in groups:
        group_agents = []
        for tid in group_ids:
            task = task_map.get(tid)
            if not task:
                continue

            prompt = _generate_execute_agent_prompt(task, manifest)
            group_agents.append({
                "task_id": tid,
                "name": f"{tid}",
                "model": "sonnet",
                "prompt": prompt,
                "use_worktree": len(group_ids) > 1,
            })

        execution_groups.append({
            "task_ids": group_ids,
            "agents": group_agents,
            "parallel": len(group_ids) > 1,
        })

    _log_decision(project_path, f"EXECUTE: {len(execution_groups)} groups prepared")

    return {
        "status": "execute_ready",
        "project_id": state["project_id"],
        "groups": execution_groups,
        "quality_gate_cmd": quality_gate,
        "total_tasks": len(tasks),
    }


def _generate_execute_agent_prompt(task: dict, manifest: dict) -> str:
    """Generate a deterministic prompt for an execution agent."""
    acceptance = "\n".join(f"- {ac}" for ac in task.get("acceptance_criteria", []))
    files = ", ".join(task.get("files", []))
    quality_gate = manifest.get("quality_gate_cmd", "")
    working_dir = manifest.get("target_directory", str(PROJECT_ROOT))

    prompt = (
        f"You are implementing a specific task for this project.\n\n"
        f"## Working Directory\n"
        f"IMPORTANT: All files MUST be created/modified in: {working_dir}\n"
        f"Do NOT write files anywhere else. Use absolute paths based on this directory.\n\n"
        f"## Original Request\n{manifest.get('request', '')}\n\n"
        f"## Your Task: {task.get('summary', 'Untitled')}\n\n"
        f"{task.get('description', '')}\n\n"
        f"## Files to Modify\n{files}\n\n"
        f"## Acceptance Criteria\n{acceptance}\n\n"
    )

    if task.get("tests_needed", True):
        prompt += (
            "## Testing\n"
            "Write tests BEFORE implementation (TDD). Tests must:\n"
            "- Cover each acceptance criterion\n"
            "- Be co-located with the code (*.spec.ts or *.test.ts)\n"
            "- Pass after implementation\n\n"
        )

    if quality_gate:
        prompt += (
            f"## Quality Gate\n"
            f"After implementation, run: `{quality_gate}`\n"
            f"All checks must pass.\n\n"
        )

    prompt += (
        "## Output Format\n"
        "When done, report:\n"
        "1. Files changed (with brief description of each change)\n"
        "2. Tests written (file paths)\n"
        "3. Quality gate results (pass/fail with output)\n"
        "4. Any issues or concerns\n"
    )

    return _inject_quality_standard(prompt)


def cmd_execute_collect() -> dict:
    """Read execution-outputs/, check completeness."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project."}

    if state.get("phase") != "EXECUTE":
        return {"error": f"Cannot execute-collect in phase {state.get('phase')}. Must be in EXECUTE."}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"error": str(e)}
    manifest_path = project_path / "manifest.json"
    manifest = qralph_state.safe_read_json(manifest_path, {})
    tasks = manifest.get("tasks", [])
    outputs_dir = project_path / "execution-outputs"

    if not tasks:
        return {"error": "No tasks in manifest. Cannot collect execution results."}

    completed = []
    missing = []
    for task in tasks:
        tid = task.get("id")
        if not tid:
            continue
        output_file = outputs_dir / f"{tid}.md"
        if output_file.exists() and output_file.read_text().strip():
            completed.append(tid)
        else:
            missing.append(tid)

    all_done = len(missing) == 0

    if all_done:
        # Transition to VERIFY
        with qralph_state.exclusive_state_lock():
            state = qralph_state.load_state()
            state["phase"] = "VERIFY"
            qralph_state.save_state(state)
        _log_decision(project_path, f"EXECUTE-COLLECT: All {len(completed)} tasks complete, transitioning to VERIFY")
    else:
        _log_decision(project_path, f"EXECUTE-COLLECT: {len(completed)}/{len(tasks)} tasks complete, {len(missing)} missing")

    _save_checkpoint(project_path, state)

    return {
        "status": "execute_complete" if all_done else "execute_incomplete",
        "completed_tasks": completed,
        "missing_tasks": missing,
        "total_tasks": len(tasks),
        "phase": "VERIFY" if all_done else "EXECUTE",
    }


def cmd_verify() -> dict:
    """Generate verification agent config for fresh-context review."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project."}

    if state.get("phase") != "VERIFY":
        return {"error": f"Cannot verify in phase {state.get('phase')}. Must be in VERIFY."}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"error": str(e)}
    manifest_path = project_path / "manifest.json"
    manifest = qralph_state.safe_read_json(manifest_path, {})

    # Gather changed files from execution outputs
    outputs_dir = project_path / "execution-outputs"
    execution_results = ""
    if outputs_dir.exists():
        for f in sorted(outputs_dir.glob("*.md")):
            execution_results += f"### {f.stem}\n\n{_sanitize_agent_output(f.read_text().strip())}\n\n---\n\n"

    # Build indexed acceptance criteria — one line per criterion with AC-N label
    indexed_criteria: list[tuple[str, str, str]] = []  # (ac_index, task_id, criterion_text)
    ac_counter = 0
    for task in manifest.get("tasks", []):
        for ac in task.get("acceptance_criteria", []):
            ac_counter += 1
            indexed_criteria.append((f"AC-{ac_counter}", task["id"], ac))

    if indexed_criteria:
        criteria_lines = [
            f"- **{idx}** [{task_id}] {text}"
            for idx, task_id, text in indexed_criteria
        ]
        criteria_text = "\n".join(criteria_lines)
    else:
        criteria_text = "No acceptance criteria defined."

    quality_gate = manifest.get("quality_gate_cmd", "")

    # Load request fragments stored at plan time for deterministic coverage tracking
    stored_fragments: list[dict] = state.get("request_fragments", [])

    working_dir = manifest.get("target_directory", state.get("target_directory", str(PROJECT_ROOT)))
    prompt = (
        f"You are a fresh-context verification agent. You have NO knowledge of how "
        f"the implementation was done. Your job is to independently verify the work.\n\n"
        f"## Working Directory\n"
        f"The project codebase is at: {working_dir}\n"
        f"Read files from this directory to verify the implementation.\n\n"
        f"## Original Request\n{manifest.get('request', state.get('request', ''))}\n\n"
        f"## Acceptance Criteria (verify each independently)\n{criteria_text}\n\n"
        f"## What Was Reported Done\n{execution_results}\n\n"
    )

    if quality_gate:
        prompt += f"## Quality Gate\nRun: `{quality_gate}`\n\n"

    # Requirements Coverage: list every REQ-F-N fragment the verifier must account for.
    # Fragments were extracted deterministically at plan time so nothing can be silently dropped.
    if stored_fragments:
        frag_lines = [
            f"- **{frag['id']}**: {frag['text']}"
            for frag in stored_fragments
        ]
        frag_text = "\n".join(frag_lines)
        prompt += (
            "## Requirements Coverage\n"
            "The user's request was decomposed into the following atomic requirement fragments "
            "at plan time. You MUST account for every fragment — a PASS verdict requires that "
            "each fragment is satisfied or explicitly documented as out-of-scope with justification.\n\n"
            f"{frag_text}\n\n"
        )

    # Build the criteria_results schema example from actual AC indices
    if indexed_criteria:
        example_entries = ", ".join(
            f'{{"criterion_index": "{idx}", "criterion": "{text[:40]}...", "status": "pass", "intent_match": true, "ship_ready": true, "evidence": "file.ts:42 — <quote>"}}'
            for idx, _, text in indexed_criteria[:2]
        )
        criteria_schema = f"[{example_entries}]"
    else:
        criteria_schema = "[]"

    # Build the request_satisfaction schema example from actual fragments
    if stored_fragments:
        sat_examples = stored_fragments[:2]
        sat_entries = ", ".join(
            f'{{"fragment_id": "{f["id"]}", "fragment_text": "{f["text"][:50]}...", "status": "satisfied", "evidence": "implemented in <file>"}}'
            for f in sat_examples
        )
        satisfaction_schema = f"[{sat_entries}]"
    else:
        satisfaction_schema = "[]"

    prompt += (
        "## Your Job\n"
        "1. Read the changed files directly from the codebase — do NOT rely on what was reported done.\n"
        "2. For EACH acceptance criterion above (AC-1, AC-2, …), open the relevant file and\n"
        "   confirm the criterion is met. Record the exact file path and line number as evidence.\n"
        "3. If any criterion cannot be confirmed with file:line evidence, mark it FAIL.\n"
        "4. For EACH requirement fragment (REQ-F-1, REQ-F-2, …), confirm the implementation\n"
        "   satisfies it. Status must be 'satisfied', 'partial', or 'missing'.\n"
        "5. Run the quality gate command if provided.\n"
        "6. After checking all ACs, re-read the Original Request and ask yourself: "
        "'Did we deliver what this person wanted, or what was convenient?' "
        "If the implementation satisfied the letter of an AC but missed the user's actual intent, "
        "set `intent_match` to false for that criterion.\n"
        "7. Write your findings to verification/result.md using the EXACT JSON block below.\n\n"
        "## Quality Bar (Non-Negotiable)\n"
        "A stub, placeholder, no-op, TODO, partial implementation, or hardcoded workaround is a FAIL. "
        "Good-enough is not good enough. Would a senior Amazon or Apple engineer stake their name on this?\n\n"
        "IMPORTANT: `verdict` must be 'PASS' only when EVERY criterion has status 'pass' AND\n"
        "every requirement fragment has status 'satisfied'. A single 'missing' or 'partial'\n"
        "fragment without explicit out-of-scope justification MUST result in verdict 'FAIL'.\n\n"
        "```json\n"
        "{\n"
        '  "verdict": "PASS",\n'
        f'  "criteria_results": {criteria_schema},\n'
        f'  "request_satisfaction": {satisfaction_schema},\n'
        '  "quality_gate": "pass",\n'
        '  "issues": []\n'
        "}\n"
        "```\n"
        "\n"
        "Each `criteria_results` entry MUST include:\n"
        '- `"criterion_index"`: the AC-N label (e.g. "AC-1")\n'
        '- `"criterion"`: the criterion text\n'
        '- `"status"`: exactly "pass" or "fail"\n'
        '- `"intent_match"`: true if the implementation does what the user actually meant '
        '(not just the literal AC wording); false if the spirit of the requirement was missed\n'
        '- `"ship_ready"`: true only if a senior Amazon/Apple engineer would stake their name on this; '
        'false if there are stubs, TODOs, workarounds, partial implementations, or hardcoded values\n'
        '- `"evidence"`: "file/path.ext:LINE — <quoted snippet>" (required for pass; explain why for fail)\n'
        "\n"
        "Each `request_satisfaction` entry MUST include:\n"
        '- `"fragment_id"`: the REQ-F-N label (e.g. "REQ-F-1")\n'
        '- `"fragment_text"`: the original requirement fragment text\n'
        '- `"status"`: exactly "satisfied", "partial", or "missing"\n'
        '- `"evidence"`: where in the codebase this is fulfilled, or reason for partial/missing\n'
        "\n"
        "## User Journey Checks\n"
        "For any task that involves a user-facing flow (forms, buttons, checkout, downloads):\n"
        "- Confirm the UI element exists in the rendered page (href, form action, button onclick)\n"
        "- Confirm the action target points to a valid, implemented route\n"
        "- Confirm any referenced assets (PDFs, images, downloads) exist at their expected paths\n"
        "  (check for R2/S3 object references in download routes and verify matching upload tasks)\n"
        "- Flag any flow where the user would hit a 404, broken link, or missing file\n"
        "- If a checkout/payment flow exists, verify the complete path: button → payment → delivery\n"
    )

    prompt = _inject_quality_standard(prompt)

    _log_decision(project_path, "VERIFY: Verification agent prepared")

    return {
        "status": "verify_ready",
        "project_id": state["project_id"],
        "agent": {
            "name": "result",
            "model": "sonnet",
            "prompt": prompt,
        },
    }


def _compute_evidence_metrics(project_path: Path, state: dict, pipeline: dict) -> dict:
    """Scan agent-outputs/ and compute evidence quality metrics for SUMMARY.md."""
    outputs_dir = project_path / "agent-outputs"
    total_agents = 0
    agents_with_output = 0
    total_words = 0
    agent_status: dict = {}

    if outputs_dir.exists():
        md_files = list(outputs_dir.glob("*.md"))
        total_agents = len(md_files)
        for md_file in md_files:
            agent_name = md_file.stem
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                content = ""
            words = len(content.split())
            if words > 0:
                agents_with_output += 1
                total_words += words
                agent_status[agent_name] = {"words": words, "status": "present"}
            else:
                agent_status[agent_name] = {"words": 0, "status": "empty"}

    eqs = round(agents_with_output / max(total_agents, 1) * 100)

    if eqs >= 80:
        confidence = "HIGH"
    elif eqs >= 50:
        confidence = "MEDIUM"
    elif eqs >= 20:
        confidence = "LOW"
    else:
        confidence = "HOLLOW RUN"

    quality_loop_rounds = pipeline.get("quality_loop", {}).get("rounds_history", [])

    return {
        "agents_with_output": agents_with_output,
        "total_agents": total_agents,
        "total_words": total_words,
        "agent_status": agent_status,
        "eqs": eqs,
        "confidence": confidence,
        "quality_loop_rounds": quality_loop_rounds,
    }


def cmd_finalize() -> dict:
    """Write SUMMARY.md, mark COMPLETE."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project."}

    allowed_finalize_phases = {"VERIFY", "DEPLOY", "SMOKE", "LEARN"}
    if state.get("phase") not in allowed_finalize_phases:
        return {"error": f"Cannot finalize in phase {state.get('phase')}. Must be in one of: {', '.join(sorted(allowed_finalize_phases))}."}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"error": str(e)}

    # Check verification result exists
    verify_result = project_path / "verification" / "result.md"
    if not verify_result.exists():
        return {"error": "No verification result. Write verification output to verification/result.md first."}

    verification_content = verify_result.read_text().strip()

    # Block unless verdict is explicitly PASS
    verdict = _parse_verdict(verification_content)
    if verdict != "PASS":
        reason = "FAILED" if verdict == "FAIL" else "no PASS/FAIL verdict found"
        return {
            "error": f"Verification {reason}. Review verification/result.md before finalizing.",
            "verification_path": str(verify_result),
        }

    # Read manifest for summary (needed for criteria validation below)
    manifest = qralph_state.safe_read_json(project_path / "manifest.json", {})

    # Block if per-criterion results are missing or any criterion failed
    criteria_results = _parse_criteria_results(verification_content)
    is_valid, missing, failed, criteria_block_reasons = _validate_criteria_results(
        criteria_results, manifest.get("tasks", [])
    )

    # Also block if any request fragments are unsatisfied
    satisfaction_results = _parse_request_satisfaction(verification_content)
    is_satisfied, satisfaction_block_reasons = _validate_request_satisfaction(
        state, satisfaction_results
    )

    if not is_valid or not is_satisfied:
        all_reasons = criteria_block_reasons + satisfaction_block_reasons
        reason_str = "; ".join(all_reasons) if all_reasons else "unknown failure"
        return {
            "error": f"Verification criteria incomplete or failed: {reason_str}. "
                     "Review verification/result.md before finalizing.",
            "verification_path": str(verify_result),
            "missing_criteria": missing,
            "failed_criteria": failed,
        }

    # Compute evidence metrics from agent-outputs/ on disk
    pipeline = state.get("pipeline", {})
    em = _compute_evidence_metrics(project_path, state, pipeline)

    # Build SUMMARY.md
    summary = f"# Project Summary: {state.get('request', '')}\n\n"
    summary += f"**Project ID**: {state['project_id']}\n"
    summary += f"**Template**: {state.get('template', 'N/A')}\n"
    summary += f"**Created**: {state.get('created_at', 'N/A')}\n"
    summary += f"**Completed**: {datetime.now().isoformat()}\n\n"

    # Tasks summary
    tasks = manifest.get("tasks", [])
    if tasks:
        summary += "## Tasks\n\n"
        for task in tasks:
            summary += f"- **{task['id']}**: {task.get('summary', 'Untitled')}\n"
        summary += "\n"

    # Agent analyses used
    agents = manifest.get("agent_analyses", state.get("agents", []))
    if agents:
        summary += f"## Agents Used\n\n{', '.join(agents)}\n\n"

    # Evidence Quality
    summary += "## Evidence Quality\n\n"
    summary += f"- **Agents with output**: {em['agents_with_output']} / {em['total_agents']}\n"
    summary += f"- **Total output words**: {em['total_words']:,}\n"
    summary += f"- **Evidence Quality Score**: {em['eqs']}/100 ({em['confidence']})\n\n"

    # Verification
    summary += f"## Verification\n\n{verification_content}\n\n"

    # Quality gate
    if manifest.get("quality_gate_cmd"):
        summary += f"## Quality Gate\n\n```\n{manifest['quality_gate_cmd']}\n```\n"

    # Mark COMPLETE before shutdown so state is saved correctly
    with qralph_state.exclusive_state_lock():
        state = qralph_state.load_state()
        state["phase"] = "COMPLETE"
        state["completed_at"] = datetime.now().isoformat()
        qralph_state.save_state(state)

    # Perform deterministic shutdown: release lock, record timestamp, clear agents
    shutdown_at = _pipeline_shutdown(state, project_path)

    # Lifecycle section — reflects actual shutdown state
    summary += "## Lifecycle\n\n"
    summary += "- Pipeline cleanup: completed\n"
    summary += "- Session lock: released\n"
    summary += f"- Completed at: {shutdown_at}\n"

    summary_path = project_path / "SUMMARY.md"
    qralph_state.safe_write(summary_path, summary)

    _log_decision(project_path, "FINALIZE: Project marked COMPLETE")
    _save_checkpoint(project_path, state)

    return {
        "status": "complete",
        "project_id": state["project_id"],
        "summary_path": str(summary_path),
        "phase": "COMPLETE",
    }


def cmd_resume() -> dict:
    """Read checkpoint, return current phase + next action."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project to resume."}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"error": str(e)}

    # Re-acquire session lock for resumed sessions (hooks need it)
    if state.get("phase") != "COMPLETE":
        _acquire_session_lock()
    try:

        phase = state.get("phase", "PLAN")

        # Determine next action based on phase
        next_actions = {
            "PLAN": "Run plan-collect if agents have reported. Otherwise spawn plan agents.",
            "EXECUTE": "Run execute if tasks are ready. Check execution-outputs/ for progress.",
            "VERIFY": "Run verify to generate verification agent. Check verification/result.md.",
            "COMPLETE": "Project is complete. Review SUMMARY.md.",
        }

        # Check what exists
        has_manifest = (project_path / "manifest.json").exists()
        has_plan = (project_path / "PLAN.md").exists()
        agent_outputs = list((project_path / "agent-outputs").glob("*.md")) if (project_path / "agent-outputs").exists() else []
        exec_outputs = list((project_path / "execution-outputs").glob("*.md")) if (project_path / "execution-outputs").exists() else []

        return {
            "status": "resumable",
            "project_id": state["project_id"],
            "request": state.get("request", ""),
            "phase": phase,
            "next_action": next_actions.get(phase, "Unknown phase"),
            "has_manifest": has_manifest,
            "has_plan": has_plan,
            "agent_outputs_count": len(agent_outputs),
            "execution_outputs_count": len(exec_outputs),
            "template": state.get("template", ""),
        }
    except BaseException:
        _release_session_lock()
        raise


def cmd_status() -> dict:
    """Return current project state."""
    state = qralph_state.load_state()
    if not state:
        return {"status": "no_active_project"}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"error": str(e)}

    return {
        "project_id": state.get("project_id"),
        "request": state.get("request", "")[:200],
        "phase": state.get("phase", "UNKNOWN"),
        "template": state.get("template", ""),
        "agents": state.get("agents", []),
        "created_at": state.get("created_at", ""),
        "pipeline_version": state.get("pipeline_version", ""),
        "project_path": str(project_path),
    }


# ─── Pipeline State Machine (cmd_next) ───────────────────────────────────────

# Valid sub-phases for the pipeline state machine
VALID_SUB_PHASES = {
    "INIT",
    "IDEATE_BRAINSTORM", "IDEATE_WAITING", "IDEATE_REVIEW",
    "PERSONA_GEN", "PERSONA_REVIEW",
    "CONCEPT_SPAWN", "CONCEPT_WAITING", "CONCEPT_REVIEW",
    "PLAN_WAITING", "PLAN_REVIEW",
    "EXEC_WAITING",
    "SIMPLIFY_RUN", "SIMPLIFY_WAITING",
    "QUALITY_DISCOVERY", "QUALITY_FIX", "QUALITY_DASHBOARD",
    "POLISH_RUN", "POLISH_WAITING", "POLISH_REVIEW",
    "VERIFY_WAIT",
    "DEPLOY_PREFLIGHT", "DEPLOY_GATE", "DEPLOY_RUN",
    "SMOKE_GENERATE", "SMOKE_WAIT", "SMOKE_VERDICT", "SMOKE_FAILURE_GATE",
    "LEARN_CAPTURE", "LEARN_COMPLETE",
    "BACKTRACK_REPLAN",
    "COMPLETE",
}

# Retry limits for infinite-loop prevention
MAX_QUALITY_GATE_RETRIES = 3
MAX_VERIFY_RETRIES = 3


def _handle_retry_or_escalate(
    state: dict,
    pipeline: dict,
    project_path: Path,
    *,
    counter_key: str,
    max_retries: int,
    log_prefix: str,
    escalation_type: str,
    escalation_options: list[dict],
    escalation_message: str,
    error_message: str,
    technical_detail: str = "",
    extra_error_fields: dict | None = None,
) -> dict:
    """Increment a retry counter and return error or escalation response.

    Shared logic for quality-gate and verify retry limits. Returns an error
    dict on retries below the limit, or an escalate_to_user dict at the limit.
    """
    retries = pipeline.get(counter_key, 0) + 1
    pipeline[counter_key] = retries
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"{log_prefix}: Failure #{retries} of {max_retries}")

    if retries >= max_retries:
        _log_decision(project_path, f"{log_prefix}: Retry limit reached — escalating to user")
        mode = pipeline.get("mode", "thorough")
        result = {
            "action": "escalate_to_user",
            "escalation_type": escalation_type,
            "retry_count": retries,
            "options": escalation_options,
            "message": escalation_message,
        }
        if mode != "thorough":
            result["technical_detail"] = technical_detail
        return result

    error_response = {
        "action": "error",
        "message": error_message,
        "retry_count": retries,
        "retries_remaining": max_retries - retries,
    }
    if extra_error_fields:
        error_response.update(extra_error_fields)
    return error_response


# ─── Deploy Intent Detection ─────────────────────────────────────────────────

# Explicit = user said "deploy to X" -> skip gate, auto-deploy
DEPLOY_EXPLICIT = [
    "deploy to", "deploy on", "deploy it to", "ship to",
    "push to prod", "put it live", "go live on",
]

# Implicit = deployment mentioned but not a direct command -> show gate
# Note: explicit phrases also match implicit (checked first), so no overlap needed
DEPLOY_IMPLICIT = [
    "deploy", "ship it", "go live",
    "put it on", "launch it", "release to",
]


def _has_explicit_deploy(request: str) -> bool:
    """Returns True if user explicitly commanded deployment (skip gate)."""
    lower = request.lower()
    return any(phrase in lower for phrase in DEPLOY_EXPLICIT)


def _has_deploy_intent(request: str) -> bool:
    """Returns True if deployment is part of the request at all (explicit or implicit)."""
    lower = request.lower()
    return (any(phrase in lower for phrase in DEPLOY_EXPLICIT)
            or any(phrase in lower for phrase in DEPLOY_IMPLICIT))


_PHASES_QUICK = ["PLAN", "EXECUTE", "SIMPLIFY", "VERIFY", "DEPLOY", "SMOKE", "LEARN", "COMPLETE"]
_PHASES_THOROUGH = PHASES  # all 13


def _build_phase_progress(state: dict, pipeline: dict) -> dict:
    """Compute phase_progress metadata for cmd_next() responses."""
    mode = pipeline.get("mode", "thorough")
    active_phases = _PHASES_QUICK if mode == "quick" else _PHASES_THOROUGH
    current_phase = state.get("phase", "PLAN")
    sub_phase = pipeline.get("sub_phase", "")
    try:
        phase_index = active_phases.index(current_phase) + 1
    except ValueError:
        phase_index = 1
    return {
        "current_phase": current_phase,
        "phase_index": phase_index,
        "total_phases": len(active_phases),
        "sub_phase": sub_phase,
    }


def cmd_next(confirm: bool = False) -> dict:
    """Return the next pipeline action. Validates previous step before advancing."""
    state = qralph_state.load_state()
    if not state:
        return {"action": "error", "message": "No active project. Run 'plan' first."}

    try:
        project_path = _safe_project_path(state)
    except ValueError as e:
        return {"action": "error", "message": str(e)}
    pipeline = state.get("pipeline", {})
    sub_phase = pipeline.get("sub_phase", "INIT")

    # --- Gap 3: Staleness detection ---
    # If we're in a WAITING sub-phase and last_activity_at is >30min old,
    # the orchestrator likely died mid-session. Fast-forward agent timeouts
    # so the watchdog fires immediately, or escalate directly.
    STALE_THRESHOLD_SECONDS = 1800  # 30 minutes
    last_activity = pipeline.get("last_activity_at")
    if last_activity and sub_phase.endswith("_WAITING"):
        try:
            last_dt = datetime.fromisoformat(last_activity)
            elapsed = (datetime.now() - last_dt).total_seconds()
            if elapsed > STALE_THRESHOLD_SECONDS:
                heal_suggestion = None
                if match_heal_condition is not None:
                    heal_suggestion = match_heal_condition("session_stale", {
                        "elapsed_seconds": elapsed,
                        "sub_phase": sub_phase,
                    })
                # Backdate all agent start times so watchdog fires immediately
                agent_timing = pipeline.get("agent_timing", {})
                if agent_timing:
                    backdated = (datetime.now() - timedelta(hours=2)).isoformat()
                    for agent_name in agent_timing:
                        agent_timing[agent_name]["started_at"] = backdated
                    pipeline["agent_timing"] = agent_timing
                    pipeline["last_activity_at"] = datetime.now().isoformat()
                    qralph_state.save_state(state)
                    # Fall through to normal dispatch — watchdog will fire
                else:
                    # No agents tracked — escalate directly
                    return {
                        "action": "escalate_to_user",
                        "message": (
                            f"The pipeline has been inactive for {int(elapsed // 60)} minutes "
                            f"in {sub_phase}. This suggests the previous session ended unexpectedly."
                        ),
                        "options": [
                            "Resume from current state",
                            "Start this phase over",
                        ],
                        "heal_suggestion": heal_suggestion,
                    }
        except (ValueError, TypeError):
            pass  # Malformed timestamp — proceed normally

    result = _dispatch_next(sub_phase, state, pipeline, project_path, confirm)

    # Inject phase_progress into non-error responses
    if result.get("action") != "error":
        result["phase_progress"] = _build_phase_progress(state, pipeline)

    return result


def _dispatch_next(sub_phase: str, state: dict, pipeline: dict, project_path: Path, confirm: bool) -> dict:
    """Inner dispatch — routes to sub-phase handlers."""

    # --- IDEATE phase handlers ---
    if sub_phase == "IDEATE_BRAINSTORM":
        return _next_ideate_brainstorm(state, pipeline, project_path)
    elif sub_phase == "IDEATE_WAITING":
        return _next_ideate_waiting(state, pipeline, project_path)
    elif sub_phase == "IDEATE_REVIEW":
        return _next_ideate_review(state, pipeline, project_path, confirm)

    # --- PERSONA phase handlers ---
    elif sub_phase == "PERSONA_GEN":
        return _next_persona_gen(state, pipeline, project_path)
    elif sub_phase == "PERSONA_REVIEW":
        return _next_persona_review(state, pipeline, project_path, confirm)

    # --- CONCEPT_REVIEW phase handlers ---
    elif sub_phase == "CONCEPT_SPAWN":
        return _next_concept_spawn(state, pipeline, project_path)
    elif sub_phase == "CONCEPT_WAITING":
        return _next_concept_waiting(state, pipeline, project_path)
    elif sub_phase == "CONCEPT_REVIEW":
        return _next_concept_review(state, pipeline, project_path, confirm)

    # --- PLAN phase handlers ---
    elif sub_phase == "INIT":
        return _next_init(state, pipeline, project_path, confirm)
    elif sub_phase == "PLAN_WAITING":
        return _next_plan_waiting(state, pipeline, project_path)
    elif sub_phase == "PLAN_REVIEW":
        return _next_plan_review(state, pipeline, project_path, confirm)
    elif sub_phase == "EXEC_WAITING":
        return _next_exec_waiting(state, pipeline, project_path)
    elif sub_phase == "SIMPLIFY_RUN":
        return _next_simplify_run(state, pipeline, project_path)
    elif sub_phase == "SIMPLIFY_WAITING":
        return _next_simplify_waiting(state, pipeline, project_path)

    # --- QUALITY_LOOP phase handlers ---
    elif sub_phase == "QUALITY_DISCOVERY":
        return _next_quality_discovery(state, pipeline, project_path)
    elif sub_phase == "QUALITY_FIX":
        return _next_quality_fix(state, pipeline, project_path)
    elif sub_phase == "QUALITY_REVERIFY":
        return _next_quality_reverify(state, pipeline, project_path)
    elif sub_phase == "QUALITY_REVERIFY_WAITING":
        return _next_quality_reverify_waiting(state, pipeline, project_path)
    elif sub_phase == "QUALITY_DASHBOARD":
        return _next_quality_dashboard(state, pipeline, project_path)

    # --- POLISH phase handlers ---
    elif sub_phase == "POLISH_RUN":
        return _next_polish_run(state, pipeline, project_path)
    elif sub_phase == "POLISH_WAITING":
        return _next_polish_waiting(state, pipeline, project_path)
    elif sub_phase == "POLISH_REVIEW":
        return _next_polish_review(state, pipeline, project_path)

    elif sub_phase == "VERIFY_WAIT":
        return _next_verify_wait(state, pipeline, project_path)

    # --- DEPLOY phase handlers ---
    elif sub_phase == "DEPLOY_PREFLIGHT":
        return _next_deploy_preflight(state, pipeline, project_path)
    elif sub_phase == "DEPLOY_GATE":
        return _next_deploy_gate(state, pipeline, project_path, confirm)
    elif sub_phase == "DEPLOY_RUN":
        return _next_deploy_run(state, pipeline, project_path)

    # --- SMOKE phase handlers ---
    elif sub_phase == "SMOKE_GENERATE":
        return _next_smoke_generate(state, pipeline, project_path)
    elif sub_phase == "SMOKE_WAIT":
        return _next_smoke_wait(state, pipeline, project_path)
    elif sub_phase == "SMOKE_VERDICT":
        return _next_smoke_verdict(state, pipeline, project_path)
    elif sub_phase == "SMOKE_FAILURE_GATE":
        # Two-call gate: first call shows failures, second (--confirm) advances
        if not confirm:
            pipeline["awaiting_confirmation"] = "confirm_smoke_failures"
            _save_pipeline_state(state, pipeline, project_path)
            return {
                "action": "smoke_failure",
                "message": "Smoke test failures detected. Review SMOKE-REPORT.md and confirm to accept and continue.",
                "smoke_report": str(project_path / "SMOKE-REPORT.md"),
            }
        if pipeline.get("awaiting_confirmation") != "confirm_smoke_failures":
            return {"action": "error", "message": "Gate violation: must call next (without --confirm) first to review smoke failures."}
        del pipeline["awaiting_confirmation"]
        _log_decision(project_path, "SMOKE: User accepted smoke failures — advancing to LEARN")
        return _advance_to_learn(state, pipeline, project_path)

    # --- BACKTRACK handler ---
    elif sub_phase == "BACKTRACK_REPLAN":
        return _next_backtrack_replan(state, pipeline, project_path)

    # --- LEARN phase handlers ---
    elif sub_phase == "LEARN_CAPTURE":
        return _next_learn_capture(state, pipeline, project_path)
    elif sub_phase == "LEARN_COMPLETE":
        return _next_learn_complete(state, pipeline, project_path)

    elif sub_phase == "COMPLETE":
        return {"action": "complete", "summary_path": str(project_path / "SUMMARY.md")}
    else:
        return {"action": "error", "message": f"Unknown sub_phase: {sub_phase}"}


def _next_ideate_brainstorm(state: dict, pipeline: dict, project_path: Path) -> dict:
    """IDEATE_BRAINSTORM: Detect plugins, generate brainstormer agent, advance to IDEATE_WAITING."""
    # Detect relevant plugins
    if detect_all_plugins:
        detected = detect_all_plugins(state["request"], state.get("target_directory"))
    else:
        detected = []
    pipeline["detected_plugins"] = detected

    # Generate brainstormer agent
    prompt = generate_ideate_prompt(state["request"], detected)
    agent = {"name": "brainstormer", "model": "opus", "prompt": prompt}
    pipeline.setdefault("_spawned_agents", {})[agent["name"]] = agent

    pipeline["sub_phase"] = "IDEATE_WAITING"
    _record_agent_start("brainstormer", pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}}))
    pipeline["last_activity_at"] = datetime.now().isoformat()
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"IDEATE: Brainstorm started, detected {len(detected)} plugins")

    return {"action": "spawn_agents", "agents": [agent], "phase": "IDEATE"}


def _next_ideate_waiting(state: dict, pipeline: dict, project_path: Path) -> dict:
    """IDEATE_WAITING: Check brainstormer output, copy to IDEATION.md, advance to IDEATE_REVIEW."""
    output_dir = project_path / "agent-outputs"
    output_path, brainstorm_content = _resolve_agent_output(output_dir, "brainstormer", MIN_AGENT_OUTPUT_LENGTH)
    if not output_path:
        timeout_result = _check_agent_timeout(
            pipeline.get("agent_timing", {}), "brainstormer", "opus",
            output_dir, project_path,
        )
        if timeout_result:
            if timeout_result["action"] == "respawn_agent":
                spawned = pipeline.get("_spawned_agents", {}).get("brainstormer")
                if spawned:
                    timeout_result["agent"] = spawned
                    timeout_result["output_dir"] = str(output_dir)
            elif timeout_result["action"] == "escalate_to_user" and match_heal_condition:
                heal = match_heal_condition("agent_timeout", timeout_result)
                if heal:
                    timeout_result["heal_suggestion"] = heal
            return timeout_result
        return {
            "action": "error",
            "message": "Brainstormer output not found or too short. Write agent output to agent-outputs/brainstormer.md and call next again.",
        }

    # Copy to IDEATION.md
    ideation_path = project_path / "IDEATION.md"
    ideation_path.write_text(brainstorm_content)

    pipeline["sub_phase"] = "IDEATE_REVIEW"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "IDEATE: Brainstormer output collected, awaiting review")

    return {"action": "confirm_ideation", "artifacts": ["IDEATION.md"], "phase": "IDEATE"}


def _next_ideate_review(state: dict, pipeline: dict, project_path: Path, confirm: bool) -> dict:
    """IDEATE_REVIEW: Confirmation gate — if confirmed, advance to PERSONA phase."""
    if not confirm:
        pipeline["awaiting_confirmation"] = "confirm_ideation"
        _save_pipeline_state(state, pipeline, project_path)
        return {
            "action": "confirm_ideation",
            "message": "Please review IDEATION.md and confirm to proceed.",
            "phase": "IDEATE",
        }
    if pipeline.get("awaiting_confirmation") != "confirm_ideation":
        return {"action": "error", "message": "Gate violation: must call next (without --confirm) first to see IDEATION.md."}
    del pipeline["awaiting_confirmation"]
    state["phase"] = "PERSONA"
    pipeline["sub_phase"] = "PERSONA_GEN"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "IDEATE: Ideation confirmed, advancing to PERSONA phase")

    return {"action": "advance", "phase": "PERSONA", "sub_phase": "PERSONA_GEN"}


def _next_persona_gen(state: dict, pipeline: dict, project_path: Path) -> dict:
    """PERSONA_GEN: Suggest archetypes, write persona files, advance to PERSONA_REVIEW."""
    # Read IDEATION.md for context (optional — not required for persona generation)
    ideation_path = project_path / "IDEATION.md"
    if ideation_path.exists():
        _ideation_context = ideation_path.read_text()

    # Generate archetype personas
    if suggest_archetypes:
        archetypes = suggest_archetypes(state["request"])
    else:
        # Fallback: minimal default personas
        archetypes = [
            {"name": "Primary User", "role": "User", "goals": ["Use the product"], "pain_points": ["Unclear UX"], "tech_comfort": "medium", "success_criteria": "Can complete core task"},
            {"name": "New User", "role": "Newcomer", "goals": ["Get started"], "pain_points": ["Steep learning curve"], "tech_comfort": "low", "success_criteria": "Can onboard quickly"},
        ]

    # Write persona files to personas/ directory
    personas_dir = project_path / "personas"
    personas_dir.mkdir(parents=True, exist_ok=True)

    for i, persona in enumerate(archetypes, start=1):
        slug = _slugify(persona.get("name", f"persona-{i}"))
        filename = f"persona-{i}-{slug}.md"
        if generate_persona_template:
            content = generate_persona_template(persona)
        else:
            content = f"# Persona: {persona.get('name', 'Unknown')}\n"
        (personas_dir / filename).write_text(content)

    # Store personas in pipeline state
    pipeline["personas"] = archetypes
    pipeline["sub_phase"] = "PERSONA_REVIEW"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"PERSONA: Generated {len(archetypes)} persona archetypes")

    return {"action": "confirm_personas", "personas": archetypes, "phase": "PERSONA"}


def _next_persona_review(state: dict, pipeline: dict, project_path: Path, confirm: bool) -> dict:
    """PERSONA_REVIEW: Confirmation gate — if confirmed, advance to CONCEPT_REVIEW phase."""
    if not confirm:
        pipeline["awaiting_confirmation"] = "confirm_personas"
        _save_pipeline_state(state, pipeline, project_path)
        return {
            "action": "confirm_personas",
            "message": "Please review the generated personas and confirm to proceed.",
            "phase": "PERSONA",
        }
    if pipeline.get("awaiting_confirmation") != "confirm_personas":
        return {"action": "error", "message": "Gate violation: must call next (without --confirm) first to see personas."}
    del pipeline["awaiting_confirmation"]
    state["phase"] = "CONCEPT_REVIEW"
    pipeline["sub_phase"] = "CONCEPT_SPAWN"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "PERSONA: Personas confirmed, advancing to CONCEPT_REVIEW phase")

    return {"action": "advance", "phase": "CONCEPT_REVIEW", "sub_phase": "CONCEPT_SPAWN"}


def _next_concept_spawn(state: dict, pipeline: dict, project_path: Path) -> dict:
    """CONCEPT_SPAWN: Generate concept review agents, return spawn_agents."""
    ideation_path = project_path / "IDEATION.md"
    ideation_md = ideation_path.read_text() if ideation_path.exists() else ""

    personas = pipeline.get("personas", [])
    detected_plugins = pipeline.get("detected_plugins", [])

    agents = generate_concept_review_agents(
        state["request"], ideation_md, personas, detected_plugins,
    )

    pipeline["concept_agents"] = [a["name"] for a in agents]
    for a in agents:
        pipeline.setdefault("_spawned_agents", {})[a["name"]] = a
    pipeline["sub_phase"] = "CONCEPT_WAITING"
    agent_timing = pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}})
    for a in agents:
        _record_agent_start(a["name"], agent_timing)
    pipeline["last_activity_at"] = datetime.now().isoformat()
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"CONCEPT: Spawning {len(agents)} concept review agents")

    return {"action": "spawn_agents", "agents": agents, "phase": "CONCEPT_REVIEW"}


def _next_concept_waiting(state: dict, pipeline: dict, project_path: Path) -> dict:
    """CONCEPT_WAITING: Collect concept review outputs, synthesize, advance to CONCEPT_REVIEW."""
    output_dir = project_path / "agent-outputs"
    expected = pipeline.get("concept_agents", [])

    reviews: dict[str, str] = {}
    missing = []
    for name in expected:
        resolved_path, content = _resolve_agent_output(output_dir, name, MIN_AGENT_OUTPUT_LENGTH)
        if resolved_path and content:
            reviews[name] = content
        else:
            missing.append(name)

    if missing:
        # Check for agent timeouts before returning error
        for agent_name in missing:
            timeout_result = _check_agent_timeout(
                pipeline.get("agent_timing", {}), agent_name, "sonnet",
                output_dir, project_path,
            )
            if timeout_result:
                if timeout_result["action"] == "respawn_agent":
                    spawned = pipeline.get("_spawned_agents", {}).get(agent_name)
                    if spawned:
                        timeout_result["agent"] = spawned
                        timeout_result["output_dir"] = str(output_dir)
                elif timeout_result["action"] == "escalate_to_user" and match_heal_condition:
                    heal = match_heal_condition("agent_timeout", timeout_result)
                    if heal:
                        timeout_result["heal_suggestion"] = heal
                return timeout_result
        return {
            "action": "error",
            "message": f"Missing concept review outputs: {', '.join(missing)}",
            "output_dir": str(output_dir),
            "expected": expected,
        }

    # Synthesize reviews
    synthesis = synthesize_concept_reviews(reviews)
    synthesis_path = project_path / "CONCEPT-SYNTHESIS.md"
    synthesis_path.write_text(synthesis)

    pipeline["sub_phase"] = "CONCEPT_REVIEW"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"CONCEPT: {len(reviews)} reviews collected, synthesis written")

    return {"action": "confirm_concept", "artifacts": ["CONCEPT-SYNTHESIS.md"], "phase": "CONCEPT_REVIEW"}


def _next_concept_review(state: dict, pipeline: dict, project_path: Path, confirm: bool) -> dict:
    """CONCEPT_REVIEW: Confirmation gate — if confirmed, advance to PLAN phase (INIT sub-phase)."""
    if not confirm:
        pipeline["awaiting_confirmation"] = "confirm_concept"
        _save_pipeline_state(state, pipeline, project_path)
        return {
            "action": "confirm_concept",
            "message": "Please review CONCEPT-SYNTHESIS.md and confirm to proceed.",
            "phase": "CONCEPT_REVIEW",
        }
    if pipeline.get("awaiting_confirmation") != "confirm_concept":
        return {"action": "error", "message": "Gate violation: must call next (without --confirm) first to see CONCEPT-SYNTHESIS.md."}
    del pipeline["awaiting_confirmation"]
    state["phase"] = "PLAN"
    pipeline["sub_phase"] = "INIT"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "CONCEPT: Concept review confirmed, advancing to PLAN phase")

    return {"action": "advance", "phase": "PLAN", "sub_phase": "INIT"}


def _save_pipeline_state(state: dict, pipeline: dict, project_path: Path):
    """Save pipeline sub-phase state atomically."""
    state["pipeline"] = pipeline
    with qralph_state.exclusive_state_lock():
        qralph_state.save_state(state)
    _save_checkpoint(project_path, state)


def _next_init(state: dict, pipeline: dict, project_path: Path, confirm: bool) -> dict:
    """INIT: Show template + agents. --confirm advances to PLAN_WAITING."""
    agents = pipeline.get("plan_agents", [])
    output_dir = str(project_path / "agent-outputs")

    if not confirm:
        pipeline["awaiting_confirmation"] = "confirm_template"
        _save_pipeline_state(state, pipeline, project_path)
        return {
            "action": "confirm_template",
            "template": state.get("template", ""),
            "template_description": TASK_TEMPLATES.get(state.get("template", ""), {}).get("description", ""),
            "agents": [{"name": a["name"], "model": a["model"]} for a in agents],
            "project_path": str(project_path),
        }

    if pipeline.get("awaiting_confirmation") != "confirm_template":
        return {"action": "error", "message": "Gate violation: must call next (without --confirm) first to see template."}
    del pipeline["awaiting_confirmation"]

    # --confirm: advance to PLAN_WAITING, return spawn_agents
    pipeline["sub_phase"] = "PLAN_WAITING"
    agent_timing = pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}})
    for a in agents:
        _record_agent_start(a["name"], agent_timing)
        pipeline.setdefault("_spawned_agents", {})[a["name"]] = a
    pipeline["last_activity_at"] = datetime.now().isoformat()
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "NEXT: Template confirmed, spawning plan agents")

    return {
        "action": "spawn_agents",
        "agents": agents,
        "output_dir": output_dir,
    }


def _next_plan_waiting(state: dict, pipeline: dict, project_path: Path) -> dict:
    """PLAN_WAITING: Validate agent outputs exist. If valid, auto-run plan-collect."""
    expected = [a["name"] for a in pipeline.get("plan_agents", [])]
    outputs_dir = project_path / "agent-outputs"

    missing = []
    # Build model lookup from plan_agents config (opus agents need longer timeout)
    agent_models = {a["name"]: a.get("model", "sonnet") for a in pipeline.get("plan_agents", [])}
    for name in expected:
        resolved_path, content = _resolve_agent_output(outputs_dir, name, MIN_AGENT_OUTPUT_LENGTH)
        if not resolved_path:
            missing.append(name)

    if missing:
        # Check for agent timeouts before returning error
        for agent_name in missing:
            timeout_result = _check_agent_timeout(
                pipeline.get("agent_timing", {}), agent_name,
                agent_models.get(agent_name, "sonnet"),
                outputs_dir, project_path,
            )
            if timeout_result:
                if timeout_result["action"] == "respawn_agent":
                    spawned = pipeline.get("_spawned_agents", {}).get(agent_name)
                    if spawned:
                        timeout_result["agent"] = spawned
                        timeout_result["output_dir"] = str(outputs_dir)
                elif timeout_result["action"] == "escalate_to_user" and match_heal_condition:
                    heal = match_heal_condition("agent_timeout", timeout_result)
                    if heal:
                        timeout_result["heal_suggestion"] = heal
                return timeout_result
        return {
            "action": "error",
            "message": f"Missing outputs: {', '.join(missing)}",
            "output_dir": str(outputs_dir),
            "expected": expected,
        }

    # All outputs present — auto-run plan-collect
    result = cmd_plan_collect()
    if "error" in result:
        return {"action": "error", "message": result["error"]}

    pipeline["sub_phase"] = "PLAN_REVIEW"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "NEXT: Agent outputs validated, plan collected")

    return {
        "action": "define_tasks",
        "analyses_summary": result.get("analyses_summary", ""),
        "manifest_path": result.get("manifest_path", ""),
        "plan_path": result.get("plan_path", ""),
    }


def _next_plan_review(state: dict, pipeline: dict, project_path: Path, confirm: bool) -> dict:
    """PLAN_REVIEW: Show plan + tasks. --confirm finalizes and starts execution."""
    manifest_path = project_path / "manifest.json"
    plan_path = project_path / "PLAN.md"
    manifest = qralph_state.safe_read_json(manifest_path, {})
    tasks = manifest.get("tasks", [])

    if not confirm:
        pipeline["awaiting_confirmation"] = "confirm_plan"
        _save_pipeline_state(state, pipeline, project_path)
        result = {
            "action": "confirm_plan",
            "plan_path": str(plan_path),
            "manifest_path": str(manifest_path),
            "tasks": [{"id": t["id"], "summary": t.get("summary", "")} for t in tasks],
        }
        # Surface product-completeness warnings before user confirms
        warnings = _warn_manifest_gaps(tasks)
        if warnings:
            result["warnings"] = warnings
        return result

    if pipeline.get("awaiting_confirmation") != "confirm_plan":
        return {"action": "error", "message": "Gate violation: must call next (without --confirm) first to see PLAN.md."}
    del pipeline["awaiting_confirmation"]

    if not tasks:
        return {"action": "error", "message": "No tasks defined in manifest.json. Define tasks before confirming."}

    # --confirm: auto-run plan-finalize
    finalize_result = cmd_plan_finalize()
    if "error" in finalize_result:
        return {"action": "error", "message": finalize_result["error"]}

    # Auto-run execute to get agent configs
    execute_result = cmd_execute()
    if "error" in execute_result:
        return {"action": "error", "message": execute_result["error"]}

    groups = execute_result.get("groups", [])
    if not groups:
        return {"action": "error", "message": "No execution groups computed."}

    # Reload state — cmd_plan_finalize/cmd_execute modified it on disk
    state = qralph_state.load_state()
    pipeline = state.get("pipeline", {})
    pipeline["execution_groups"] = groups
    pipeline["current_group_index"] = 0
    pipeline["sub_phase"] = "EXEC_WAITING"
    first_group = groups[0]
    agent_timing = pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}})
    for a in first_group.get("agents", []):
        _record_agent_start(a.get("name", a.get("id", "")), agent_timing)
        pipeline.setdefault("_spawned_agents", {})[a.get("name", a.get("id", ""))] = a
    pipeline["last_activity_at"] = datetime.now().isoformat()
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"NEXT: Plan finalized, {len(groups)} execution groups ready")

    return {
        "action": "spawn_agents",
        "agents": first_group.get("agents", []),
        "output_dir": str(project_path / "execution-outputs"),
    }


def _next_exec_waiting(state: dict, pipeline: dict, project_path: Path) -> dict:
    """EXEC_WAITING: Validate execution outputs for current group."""
    groups = pipeline.get("execution_groups", [])
    idx = pipeline.get("current_group_index", 0)
    outputs_dir = project_path / "execution-outputs"

    if idx >= len(groups):
        return {"action": "error", "message": "No execution groups remaining."}

    current_group = groups[idx]
    expected_ids = current_group.get("task_ids", [])

    missing = []
    for tid in expected_ids:
        resolved_path, content = _resolve_agent_output(outputs_dir, tid, MIN_AGENT_OUTPUT_LENGTH)
        if not resolved_path:
            missing.append(tid)

    if missing:
        # Check for agent timeouts before returning error
        for agent_name in missing:
            timeout_result = _check_agent_timeout(
                pipeline.get("agent_timing", {}), agent_name, "sonnet",
                outputs_dir, project_path,
            )
            if timeout_result:
                if timeout_result["action"] == "respawn_agent":
                    spawned = pipeline.get("_spawned_agents", {}).get(agent_name)
                    if spawned:
                        timeout_result["agent"] = spawned
                        timeout_result["output_dir"] = str(outputs_dir)
                elif timeout_result["action"] == "escalate_to_user" and match_heal_condition:
                    heal = match_heal_condition("agent_timeout", timeout_result)
                    if heal:
                        timeout_result["heal_suggestion"] = heal
                return timeout_result
        return {
            "action": "error",
            "message": f"Missing outputs: {', '.join(missing)}",
            "output_dir": str(outputs_dir),
            "expected": expected_ids,
        }

    # Current group complete — check if more groups
    next_idx = idx + 1
    if next_idx < len(groups):
        pipeline["current_group_index"] = next_idx
        pipeline["sub_phase"] = "EXEC_WAITING"
        next_group = groups[next_idx]
        agent_timing = pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}})
        for a in next_group.get("agents", []):
            _record_agent_start(a.get("name", a.get("id", "")), agent_timing)
            pipeline.setdefault("_spawned_agents", {})[a.get("name", a.get("id", ""))] = a
        pipeline["last_activity_at"] = datetime.now().isoformat()
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(project_path, f"NEXT: Group {idx + 1}/{len(groups)} complete, spawning group {next_idx + 1}")

        return {
            "action": "spawn_agents",
            "agents": next_group.get("agents", []),
            "output_dir": str(outputs_dir),
        }

    # All groups done — auto-run execute-collect
    collect_result = cmd_execute_collect()
    if "error" in collect_result:
        return {"action": "error", "message": collect_result["error"]}

    if collect_result.get("status") != "execute_complete":
        return {
            "action": "error",
            "message": f"Execution incomplete. Missing tasks: {collect_result.get('missing_tasks', [])}",
        }

    # Run quality gate BEFORE simplify/verification — pipeline enforces this
    # Prefer manifest's explicit quality_gate_cmd (set during plan-collect),
    # fall back to auto-detection only when manifest has no explicit command.
    manifest_path = project_path / "manifest.json"
    manifest = qralph_state.safe_read_json(manifest_path, {}) if manifest_path.exists() else {}
    manifest_qg_cmd = manifest.get("quality_gate_cmd", "")
    manifest_qg_cwd = manifest.get("quality_gate_cwd", "")
    if manifest_qg_cmd:
        quality_gate_cmd = manifest_qg_cmd
        quality_gate_cwd = manifest_qg_cwd or str(PROJECT_ROOT)
    else:
        quality_gate = detect_quality_gate()
        quality_gate_cmd = quality_gate.get("cmd", "") if isinstance(quality_gate, dict) else quality_gate
        quality_gate_cwd = quality_gate.get("cwd", str(PROJECT_ROOT)) if isinstance(quality_gate, dict) else str(PROJECT_ROOT)
        # I1: Log GATE_INEFFECTIVE warning when linter config is missing
        if isinstance(quality_gate, dict) and not quality_gate.get("effective", True):
            _log_decision(project_path, "GATE_INEFFECTIVE: Lint gate is a no-op — no linter config found")
            pipeline.setdefault("gate_warnings", []).append({
                "type": "GATE_INEFFECTIVE",
                "message": "Lint gate has no linter configured",
            })
    if quality_gate_cmd:
        if not _is_safe_gate_cwd(quality_gate_cwd):
            _log_decision(project_path, f"QUALITY-GATE: CWD '{quality_gate_cwd}' failed containment, using PROJECT_ROOT")
            quality_gate_cwd = str(PROJECT_ROOT)
        _log_decision(project_path, f"QUALITY-GATE: Running '{quality_gate_cmd}' in {quality_gate_cwd}")
        gate_failed = False
        gate_output = ""
        gate_error_message = ""
        try:
            gate_returncode, gate_output = _run_shell_chain(
                quality_gate_cmd, quality_gate_cwd, timeout=120,
            )
            gate_passed = gate_returncode == 0
            _log_decision(project_path, f"QUALITY-GATE: {'PASSED' if gate_passed else 'FAILED'} (exit {gate_returncode})")
            if not gate_passed:
                gate_failed = True
                gate_error_message = f"Quality gate FAILED (exit {gate_returncode}). Fix issues before verification."
        except subprocess.TimeoutExpired:
            _log_decision(project_path, "QUALITY-GATE: TIMEOUT (120s)")
            gate_failed = True
            gate_error_message = "Quality gate timed out after 120s."
        except OSError as e:
            _log_decision(project_path, f"QUALITY-GATE: OS ERROR — {e}")
            gate_failed = True
            gate_error_message = f"Quality gate command failed: {e}"
        except Exception as e:
            _log_decision(project_path, f"QUALITY-GATE: UNEXPECTED ERROR — {e}")
            gate_failed = True
            gate_error_message = f"Quality gate raised unexpected error: {e}"

        if gate_failed:
            return _handle_retry_or_escalate(
                state, pipeline, project_path,
                counter_key="quality_gate_retries",
                max_retries=MAX_QUALITY_GATE_RETRIES,
                log_prefix="QUALITY-GATE",
                escalation_type="quality_gate_retry_limit",
                escalation_options=[
                    {"id": "skip", "label": "Skip the quality check and continue to the next step"},
                    {"id": "abort", "label": "Stop the pipeline here"},
                ],
                escalation_message=(
                    "The automated checks have failed 3 times in a row. "
                    "The code may have a deeper issue that automatic fixes cannot resolve. "
                    "You can skip the checks and continue anyway, or stop here."
                ),
                error_message=gate_error_message,
                technical_detail=gate_output,
                extra_error_fields={
                    "quality_gate_cmd": quality_gate_cmd,
                    "quality_gate_output": gate_output,
                },
            )

        # Gate passed — reset retry counter
        pipeline["quality_gate_retries"] = 0

    # Transition to SIMPLIFY phase instead of directly to VERIFY
    state["phase"] = "SIMPLIFY"
    pipeline["sub_phase"] = "SIMPLIFY_RUN"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "NEXT: All execution groups complete, transitioning to SIMPLIFY")

    return _next_simplify_run(state, pipeline, project_path)


def _next_simplify_run(state: dict, pipeline: dict, project_path: Path) -> dict:
    """SIMPLIFY_RUN: Spawn a simplifier agent that runs /simplify on changed files."""
    manifest_path = project_path / "manifest.json"
    manifest = qralph_state.safe_read_json(manifest_path, {}) if manifest_path.exists() else {}
    tasks = manifest.get("tasks", [])

    # Collect all files touched during execution
    changed_files: list[str] = []
    for task in tasks:
        for f in task.get("files", []):
            if f not in changed_files:
                changed_files.append(f)

    files_list = "\n".join(f"- {f}" for f in changed_files) if changed_files else "- (no files listed in manifest)"

    prompt = (
        "You are a code simplifier. Your job is to review recently changed files "
        "and apply the /simplify pattern: reduce complexity, remove dead code, "
        "improve naming, and ensure readability.\n\n"
        "## Files Changed During Execution\n"
        f"{files_list}\n\n"
        "## Instructions\n"
        "1. Read each file listed above\n"
        "2. Apply /simplify: remove unnecessary complexity, dead code, redundant comments\n"
        "3. Improve variable/function naming where unclear\n"
        "4. Ensure consistent formatting and style\n"
        "5. Do NOT change behavior — only simplify structure and readability\n"
        "6. Report what you changed in your output\n\n"
        f"Working Directory: {str(PROJECT_ROOT)}\n"
    )

    agent = {"name": "simplifier", "model": "sonnet", "prompt": prompt}
    pipeline.setdefault("_spawned_agents", {})[agent["name"]] = agent

    pipeline["sub_phase"] = "SIMPLIFY_WAITING"
    _record_agent_start("simplifier", pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}}))
    pipeline["last_activity_at"] = datetime.now().isoformat()
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"SIMPLIFY: Spawning simplifier agent for {len(changed_files)} files")

    return {
        "action": "spawn_agents",
        "agents": [agent],
        "output_dir": str(project_path / "execution-outputs"),
    }


def _next_simplify_waiting(state: dict, pipeline: dict, project_path: Path) -> dict:
    """SIMPLIFY_WAITING: Check simplifier output, then advance based on mode."""
    output_path, simplifier_content = _resolve_agent_output(
        project_path / "execution-outputs", "simplifier", MIN_AGENT_OUTPUT_LENGTH
    )
    if not output_path:
        timeout_result = _check_agent_timeout(
            pipeline.get("agent_timing", {}), "simplifier", "sonnet",
            project_path / "execution-outputs", project_path,
        )
        if timeout_result:
            if timeout_result["action"] == "respawn_agent":
                spawned = pipeline.get("_spawned_agents", {}).get("simplifier")
                if spawned:
                    timeout_result["agent"] = spawned
                    timeout_result["output_dir"] = str(project_path / "execution-outputs")
            elif timeout_result["action"] == "escalate_to_user" and match_heal_condition:
                heal = match_heal_condition("agent_timeout", timeout_result)
                if heal:
                    timeout_result["heal_suggestion"] = heal
            return timeout_result
        return {
            "action": "error",
            "message": "Missing or too short simplifier output. Write to execution-outputs/simplifier.md and call next again.",
        }

    mode = pipeline.get("mode", "thorough")

    if mode == "quick":
        # Quick mode: skip quality loop, go directly to VERIFY
        _log_decision(project_path, "SIMPLIFY: Quick mode — skipping quality loop, advancing to VERIFY")

        # Save to disk before cmd_verify() reloads state
        state["phase"] = "VERIFY"
        _save_pipeline_state(state, pipeline, project_path)

        verify_result = cmd_verify()
        if "error" in verify_result:
            return {"action": "error", "message": verify_result["error"]}

        # Reload state — cmd_verify modified it on disk
        state = qralph_state.load_state()
        pipeline = state.get("pipeline", {})
        pipeline["sub_phase"] = "VERIFY_WAIT"
        _save_pipeline_state(state, pipeline, project_path)

        verifier = verify_result.get("agent", {})
        return {
            "action": "spawn_agents",
            "agents": [verifier],
            "output_dir": str(project_path / "verification"),
        }

    # Thorough mode: advance to QUALITY_LOOP (QUALITY_DISCOVERY sub-phase)
    _log_decision(project_path, "SIMPLIFY: Thorough mode — advancing to QUALITY_DISCOVERY")
    state["phase"] = "QUALITY_LOOP"
    pipeline["sub_phase"] = "QUALITY_DISCOVERY"
    _save_pipeline_state(state, pipeline, project_path)

    return {"action": "advance", "phase": "QUALITY_LOOP", "sub_phase": "QUALITY_DISCOVERY"}


def _generate_quality_review_prompt(agent_name: str, agent_role: str, request: str, project_path: Path, manifest: dict) -> str:
    """Generate a review prompt for a quality loop agent."""
    tasks = manifest.get("tasks", [])
    files_list = []
    for task in tasks:
        for f in task.get("files", []):
            if f not in files_list:
                files_list.append(f)
    files_md = "\n".join(f"- {f}" for f in files_list) if files_list else "- (no files listed)"

    task_summaries = "\n".join(f"- {t.get('id', '?')}: {t.get('summary', 'N/A')}" for t in tasks)

    role_instructions = {
        "code-reviewer": "Focus on code quality, readability, naming, DRY violations, and style consistency.",
        "security-reviewer": "Focus on security vulnerabilities: injection, auth bypass, secrets in code, input validation.",
        "pe-architect": "Focus on architecture, performance bottlenecks, scalability concerns, and design patterns.",
        "test-verifier": "Focus on test coverage, missing edge cases, test quality, and assertion completeness.",
        "failure-analyst": "Focus on failure modes, error handling gaps, edge cases, and resilience.",
        "usability-reviewer": "Focus on user experience, accessibility, error messages, and workflow clarity.",
        "business-advisor": "Focus on requirements alignment, business logic correctness, and feature completeness.",
    }
    specific = role_instructions.get(agent_name, f"Review from the perspective of a {agent_role}.")

    prompt = f"""You are a {agent_role} reviewing a completed implementation.

## Original Request
{request}

## What Was Built
The following tasks were implemented:
{task_summaries}

### Files Modified
{files_md}

Review the files listed above and check for issues from your perspective.

## Your Role: {agent_role}
{specific}

## Output Format
For each finding, report:
[P0/P1/P2] {agent_name.upper()}-NNN: <title>
<description>
**Suggested fix:** <concrete suggestion>
**Confidence:** high/medium/low

Severity guide:
- P0: Critical — blocks ship (security holes, data loss, crashes)
- P1: Important — should fix before ship (bugs, missing validation, poor error handling)
- P2: Suggestion — nice to have (style, naming, minor refactors)

If no issues found, state "No issues found." and explain why you are confident.
"""
    return _inject_quality_standard(prompt)


def _next_quality_discovery(state: dict, pipeline: dict, project_path: Path) -> dict:
    """QUALITY_DISCOVERY: Initialize quality loop and spawn review agents."""
    ql = pipeline.get("quality_loop")
    estimated_sp = state.get("estimated_sp", 5.0)
    personas = pipeline.get("personas", [])
    mode = pipeline.get("mode", "thorough")

    if ql is None:
        # Round 1: initialize quality_loop state
        agents = select_quality_agents(estimated_sp, personas, mode)
        ql = {
            "round": 1,
            "max_rounds": max_discovery_rounds(estimated_sp),
            "rounds_history": [],
            "active_agents": [a["name"] for a in agents],
            "dropped_agents": [],
            "replan_count": 0,
        }
        pipeline["quality_loop"] = ql
    else:
        # Round 2+: use active_agents from previous round
        active_names = ql.get("active_agents", [])
        if not active_names:
            # All agents dropped — converge by default
            pipeline["sub_phase"] = "QUALITY_DASHBOARD"
            ql["_dashboard_action"] = "converged"
            _save_pipeline_state(state, pipeline, project_path)
            return _next_quality_dashboard(state, pipeline, project_path)
        # Rebuild agent dicts from names
        all_agents = select_quality_agents(estimated_sp, personas, mode)
        agents = [a for a in all_agents if a["name"] in active_names]
        # If an agent got dropped from the full list, keep what we have
        if not agents:
            agents = [{"name": n, "model": "sonnet", "role": "Review agent"} for n in active_names]

    # Read manifest for context
    manifest_path = project_path / "manifest.json"
    manifest = qralph_state.safe_read_json(manifest_path, {}) if manifest_path.exists() else {}

    # Generate prompts for each agent
    agents_with_prompts = []
    for agent in agents:
        prompt = _generate_quality_review_prompt(
            agent["name"], agent.get("role", agent["name"]),
            state["request"], project_path, manifest,
        )
        agents_with_prompts.append({
            "name": agent["name"],
            "model": agent.get("model", "sonnet"),
            "prompt": prompt,
            "output_file": f"quality-round-{ql['round']}-{agent['name']}.md",
        })

    pipeline["sub_phase"] = "QUALITY_FIX"
    _save_pipeline_state(state, pipeline, project_path)
    round_num = ql["round"]
    _log_decision(project_path, f"QUALITY_DISCOVERY: Round {round_num} — spawning {len(agents_with_prompts)} review agents")

    return {
        "action": "spawn_agents",
        "agents": agents_with_prompts,
        "phase": "QUALITY_LOOP",
        "output_dir": str(project_path / "agent-outputs"),
    }


def _next_quality_fix(state: dict, pipeline: dict, project_path: Path) -> dict:
    """QUALITY_FIX: Collect agent outputs, parse findings, determine next action."""
    ql = pipeline.get("quality_loop", {})
    round_num = ql.get("round", 1)
    active_agents = ql.get("active_agents", [])

    # Collect and parse findings from agent outputs
    all_findings = []
    agent_results = []
    still_active = []
    output_dir = project_path / "agent-outputs"

    for agent_name in active_agents:
        file_stem = f"quality-round-{round_num}-{agent_name}"
        resolved_path, content = _resolve_agent_output(output_dir, file_stem, min_length=1)
        if not content:
            content = ""

        if parse_findings:
            findings = parse_findings(content, agent_name)
        else:
            findings = []

        all_findings.extend(findings)
        agent_results.append({"agent": agent_name, "findings": findings})

        # Determine if agent should continue
        if should_agent_continue and should_agent_continue(findings):
            still_active.append(agent_name)
        elif findings:
            # Agent found only P2s — drop it
            pass
        elif content.strip():
            # Agent found nothing and wrote output — drop it
            pass
        else:
            # No output at all — keep for retry
            still_active.append(agent_name)

    # Build round result and add to history
    round_result = {
        "round": round_num,
        "findings": all_findings,
        "agents": active_agents,
    }
    ql["rounds_history"].append(round_result)

    # Determine convergence (pass previous round findings for regression detection)
    prev_findings = []
    history = pipeline.get("quality_loop", {}).get("rounds_history", [])
    if len(history) >= 2:
        prev_round = history[-2]  # -1 is current (just appended), -2 is previous
        prev_findings = prev_round.get("findings", [])
    if check_convergence:
        conv = check_convergence(all_findings, prev_findings=prev_findings)
    else:
        conv = {"converged": len(all_findings) == 0, "p0_count": 0, "p1_count": 0, "p2_count": 0, "total": len(all_findings)}

    if detect_consensus:
        consensus = detect_consensus(agent_results)
    else:
        consensus = {"consensus": False, "recommendation": "continue"}

    p0_count = conv.get("p0_count", 0)
    replan_count = ql.get("replan_count", 0)

    est_sp = pipeline.get("manifest", {}).get("estimated_sp", 5.0)
    if should_backtrack and should_backtrack(round_num, p0_count, replan_count, estimated_sp=est_sp):
        dashboard_action = "backtrack"
    elif conv.get("regressed") and round_num >= 3:
        # P0 count increased with truly NEW findings at round 3+ — replan
        dashboard_action = "backtrack"
    elif conv.get("stagnant"):
        # Same P0+P1 count (>=3) as previous round — stop spinning
        dashboard_action = "max_rounds"
    elif conv["converged"]:
        # Zero P0 and zero P1 — fully converged
        if consensus.get("consensus"):
            dashboard_action = "early_terminate"
        else:
            dashboard_action = "converged"
    elif round_num >= ql.get("max_rounds", 3):
        dashboard_action = "max_rounds"
    else:
        dashboard_action = "continue"

    # Update active agents — drop agents that found nothing meaningful
    dropped_this_round = [a for a in active_agents if a not in still_active]
    ql["active_agents"] = still_active
    ql["dropped_agents"] = list(set(ql.get("dropped_agents", []) + dropped_this_round))
    ql["_dashboard_action"] = dashboard_action
    ql["_current_findings"] = all_findings

    # Route to QUALITY_REVERIFY when continuing with P0/P1 findings so each
    # finding is independently confirmed as fixed before the next discovery round.
    p0_p1_findings = [f for f in all_findings if f.get("severity") in ("P0", "P1")]
    if dashboard_action == "continue" and p0_p1_findings:
        pipeline["sub_phase"] = "QUALITY_REVERIFY"
    else:
        pipeline["sub_phase"] = "QUALITY_DASHBOARD"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"QUALITY_FIX: Round {round_num} — {len(all_findings)} findings, action={dashboard_action}")

    return {
        "action": "quality_assessed",
        "round": round_num,
        "findings_count": len(all_findings),
        "p0_count": p0_count,
        "p1_count": conv.get("p1_count", 0),
        "dashboard_action": dashboard_action,
    }


def _next_quality_reverify(state: dict, pipeline: dict, project_path: Path) -> dict:
    """QUALITY_REVERIFY: Spawn a targeted verifier agent to confirm each P0/P1 fix."""
    ql = pipeline.get("quality_loop", {})
    rounds_history = ql.get("rounds_history", [])

    # The current round's findings were just appended by QUALITY_FIX
    prev_findings = rounds_history[-1]["findings"] if rounds_history else []
    p0_p1_findings = [f for f in prev_findings if f.get("severity") in ("P0", "P1")]

    if not p0_p1_findings:
        # No P0/P1 to verify — skip straight to dashboard
        pipeline["sub_phase"] = "QUALITY_DASHBOARD"
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(project_path, "QUALITY_REVERIFY: No P0/P1 findings — skipping to QUALITY_DASHBOARD")
        return _next_quality_dashboard(state, pipeline, project_path)

    # Build a targeted verification prompt listing every P0/P1 finding
    finding_lines = []
    for f in p0_p1_findings:
        fid = f.get("id", "UNKNOWN")
        severity = f.get("severity", "P?")
        title = f.get("title", f.get("raw", "no title"))
        location = f.get("location", "")
        loc_hint = f" (at {location})" if location else ""
        finding_lines.append(f"- [{severity}] {fid}: {title}{loc_hint}")
    findings_block = "\n".join(finding_lines)

    round_num = ql.get("round", 1)

    project_files_hint = ""
    manifest_path = project_path / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        file_list = list(dict.fromkeys(
            fpath
            for task in manifest.get("tasks", [])
            for fpath in task.get("files", [])
        ))
        if file_list:
            project_files_hint = "\n## Project Files to Check\n" + "\n".join(f"- {p}" for p in file_list) + "\n"
    verifier_prompt = (
        "You are a verification agent. Your ONLY job is to check whether specific findings "
        "from a previous quality review have been fixed in the code.\n\n"
        "## Findings to Verify\n"
        f"{findings_block}\n"
        f"{project_files_hint}\n"
        "## Instructions\n"
        "For EACH finding listed above:\n"
        "1. Read the referenced files in the codebase.\n"
        "2. Look for concrete evidence that the fix was applied "
        "(changed code, added checks, removed problematic patterns).\n"
        "3. Report one of exactly two verdicts per finding:\n"
        "   - `RESOLVED: <finding-id>` — the fix is present in the code\n"
        "   - `UNRESOLVED: <finding-id>` — no fix evidence found\n\n"
        "## Output Format\n"
        "List one verdict per line in the form:\n"
        "```\n"
        "RESOLVED: <finding-id>\n"
        "UNRESOLVED: <finding-id>\n"
        "```\n"
        "Do NOT skip any finding. Every finding must have a verdict.\n"
    )

    output_file = f"quality-reverify-round-{round_num}.md"
    pipeline["sub_phase"] = "QUALITY_REVERIFY_WAITING"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(
        project_path,
        f"QUALITY_REVERIFY: Round {round_num} — spawning verifier for {len(p0_p1_findings)} P0/P1 findings",
    )

    return {
        "action": "spawn_agents",
        "agents": [
            {
                "name": "quality-verifier",
                "model": "haiku",
                "prompt": verifier_prompt,
                "output_file": output_file,
            }
        ],
        "phase": "QUALITY_LOOP",
        "output_dir": str(project_path / "agent-outputs"),
    }


def _next_quality_reverify_waiting(state: dict, pipeline: dict, project_path: Path) -> dict:
    """QUALITY_REVERIFY_WAITING: Collect verifier output and update finding statuses."""
    ql = pipeline.get("quality_loop", {})
    round_num = ql.get("round", 1)
    output_dir = project_path / "agent-outputs"
    output_file_stem = f"quality-reverify-round-{round_num}"

    _, content = _resolve_agent_output(output_dir, output_file_stem, min_length=1)

    rounds_history = ql.get("rounds_history", [])
    prev_findings = rounds_history[-1]["findings"] if rounds_history else []
    p0_p1_findings = [f for f in prev_findings if f.get("severity") in ("P0", "P1")]

    # Parse RESOLVED / UNRESOLVED verdicts from verifier output
    resolved_ids: set[str] = set()
    unresolved_ids: set[str] = set()
    if content:
        for line in content.splitlines():
            line = line.strip()
            if line.upper().startswith("RESOLVED:"):
                fid = line.split(":", 1)[1].strip()
                resolved_ids.add(fid)
            elif line.upper().startswith("UNRESOLVED:"):
                fid = line.split(":", 1)[1].strip()
                unresolved_ids.add(fid)

    # Mark findings with their verification status
    for f in prev_findings:
        fid = f.get("id", "")
        if fid in resolved_ids:
            f["reverify_status"] = "resolved"
        elif fid in unresolved_ids:
            f["reverify_status"] = "unresolved"

    # Collect unresolved P0/P1 findings
    still_unresolved = [
        f for f in p0_p1_findings
        if f.get("reverify_status") != "resolved"
    ]

    ql["reverify_unresolved"] = still_unresolved

    pipeline["sub_phase"] = "QUALITY_DASHBOARD"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(
        project_path,
        f"QUALITY_REVERIFY_WAITING: Round {round_num} — "
        f"{len(p0_p1_findings) - len(still_unresolved)}/{len(p0_p1_findings)} P0/P1 resolved",
    )

    return {
        "action": "quality_reverify_complete",
        "round": round_num,
        "resolved_count": len(p0_p1_findings) - len(still_unresolved),
        "unresolved_count": len(still_unresolved),
        "unresolved_findings": still_unresolved,
    }


def _next_quality_dashboard(state: dict, pipeline: dict, project_path: Path) -> dict:
    """QUALITY_DASHBOARD: Generate dashboard, decide next action."""
    ql = pipeline.get("quality_loop", {})
    round_num = ql.get("round", 1)
    max_rounds = ql.get("max_rounds", 3)
    dashboard_action = ql.pop("_dashboard_action", "continue")
    current_findings = ql.pop("_current_findings", [])

    # Generate dashboard markdown
    if generate_dashboard:
        dashboard_md = generate_dashboard(
            round_num=round_num,
            max_rounds=max_rounds,
            rounds=ql.get("rounds_history", []),
            agents_active=ql.get("active_agents", []),
            agents_dropped=ql.get("dropped_agents", []),
            current_findings=current_findings,
        )
    else:
        dashboard_md = f"# Quality Dashboard - Round {round_num}\nNo dashboard module available.\n"

    # Write dashboard to quality-reports/
    reports_dir = project_path / "quality-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"round-{round_num}.md").write_text(dashboard_md)

    if dashboard_action in ("converged", "early_terminate"):
        # Advance to POLISH (POLISH_RUN sub-phase)
        state["phase"] = "POLISH"
        pipeline["sub_phase"] = "POLISH_RUN"
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(project_path, f"QUALITY_DASHBOARD: {dashboard_action} — advancing to POLISH")

        return {
            "action": "advance",
            "phase": "POLISH",
            "sub_phase": "POLISH_RUN",
            "dashboard": dashboard_md,
            "reason": dashboard_action,
        }

    if dashboard_action == "max_rounds":
        # Check for remaining P0 findings — if any, escalate to user instead of bypassing to POLISH
        rounds_history = ql.get("rounds_history", [])
        last_round_findings = rounds_history[-1]["findings"] if rounds_history else []
        p0_findings = [
            f for f in last_round_findings
            if "P0" in str(f.get("severity", "")).upper()
            or "critical" in str(f.get("severity", "")).lower()
            or "P0" in str(f.get("priority", "")).upper()
        ]

        if p0_findings:
            finding_lines = []
            for f in p0_findings:
                fid = f.get("id", "UNKNOWN")
                title = f.get("title", f.get("raw", "No description"))
                agent = f.get("agent", "unknown agent")
                finding_lines.append(f"- [{fid}] {title} (found by {agent})")
            findings_text = "\n".join(finding_lines)
            message = (
                f"Maximum quality rounds ({max_rounds}) reached, but {len(p0_findings)} critical (P0) "
                f"finding(s) remain unresolved:\n\n{findings_text}\n\n"
                "These issues may affect the correctness or security of the project."
            )
            _log_decision(project_path, f"QUALITY_DASHBOARD: max_rounds with {len(p0_findings)} P0 findings — escalating to user")
            return {
                "action": "escalate_to_user",
                "escalation_type": "max_quality_rounds_p0_remaining",
                "message": message,
                "p0_findings": p0_findings,
                "p0_count": len(p0_findings),
                "dashboard": dashboard_md,
                "options": [
                    {"id": "accept", "label": "Accept and continue to polish"},
                    {"id": "retry", "label": "Retry quality loop"},
                    {"id": "abort", "label": "Abort project"},
                ],
            }

        # No P0 findings — only P1/P2 remain, safe to advance to POLISH
        state["phase"] = "POLISH"
        pipeline["sub_phase"] = "POLISH_RUN"
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(project_path, "QUALITY_DASHBOARD: max_rounds — no P0 findings, advancing to POLISH")

        return {
            "action": "advance",
            "phase": "POLISH",
            "sub_phase": "POLISH_RUN",
            "dashboard": dashboard_md,
            "reason": "max_rounds",
        }

    if dashboard_action == "backtrack":
        replan_count = ql.get("replan_count", 0)
        if replan_count >= 2:
            # Max replans reached — advance to POLISH anyway
            state["phase"] = "POLISH"
            pipeline["sub_phase"] = "POLISH_RUN"
            _save_pipeline_state(state, pipeline, project_path)
            _log_decision(project_path, "QUALITY_DASHBOARD: Max replans reached — advancing to POLISH")
            return {
                "action": "advance",
                "phase": "POLISH",
                "sub_phase": "POLISH_RUN",
                "dashboard": dashboard_md,
                "reason": "max_replans",
            }
        ql["replan_count"] = replan_count + 1
        pipeline["sub_phase"] = "BACKTRACK_REPLAN"
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(project_path, f"QUALITY_DASHBOARD: Backtracking to replan (replan #{replan_count + 1})")
        return {
            "action": "backtrack",
            "phase": "QUALITY_LOOP",
            "sub_phase": "BACKTRACK_REPLAN",
            "dashboard": dashboard_md,
            "reason": "backtrack",
        }

    # "continue" — increment round, return findings as fix tasks, loop back to QUALITY_DISCOVERY
    p0_and_p1 = [f for f in current_findings if f.get("severity") in ("P0", "P1")]
    ql["round"] = round_num + 1
    pipeline["sub_phase"] = "QUALITY_DISCOVERY"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"QUALITY_DASHBOARD: Continuing to round {round_num + 1} with {len(p0_and_p1)} fix tasks")

    return {
        "action": "quality_fix_tasks",
        "findings": p0_and_p1,
        "dashboard": dashboard_md,
        "next_round": round_num + 1,
    }


def _next_polish_run(state: dict, pipeline: dict, project_path: Path) -> dict:
    """POLISH_RUN: Spawn bug_fixer, wiring_agent, requirements_tracer agents."""
    manifest_path = project_path / "manifest.json"
    manifest = qralph_state.safe_read_json(manifest_path, {}) if manifest_path.exists() else {}
    tasks = manifest.get("tasks", [])

    # Collect all files touched during execution
    changed_files: list[str] = []
    for task in tasks:
        for f in task.get("files", []):
            if f not in changed_files:
                changed_files.append(f)
    files_list = "\n".join(f"- {f}" for f in changed_files) if changed_files else "- (no files listed in manifest)"

    request = state.get("request", "")

    bug_fixer_prompt = _inject_quality_standard(
        "You are a bug fixer. Review the implementation for bugs, edge cases, "
        "and correctness issues.\n\n"
        f"## Original Request\n{request}\n\n"
        f"## Files Changed\n{files_list}\n\n"
        "## Instructions\n"
        "1. Read each file and look for bugs, off-by-one errors, null checks, edge cases\n"
        "2. Check error handling completeness\n"
        "3. Verify logic correctness against the original request\n"
        "4. Report findings with severity (P0=critical, P1=high, P2=medium)\n"
        "5. Fix any P0/P1 issues directly\n"
        f"Working Directory: {str(PROJECT_ROOT)}\n"
    )

    wiring_prompt = _inject_quality_standard(
        "You are a wiring agent. Verify that all components are properly connected "
        "and integrated.\n\n"
        f"## Original Request\n{request}\n\n"
        f"## Files Changed\n{files_list}\n\n"
        "## Instructions\n"
        "1. Check imports and exports are correct\n"
        "2. Verify API contracts between modules\n"
        "3. Ensure configuration files reference the right paths\n"
        "4. Check that new code is reachable from entry points\n"
        "5. Report any disconnected or dead code\n"
        f"Working Directory: {str(PROJECT_ROOT)}\n"
    )

    tracer_prompt = _inject_quality_standard(
        "You are a requirements tracer. Verify test coverage for all requirements.\n\n"
        f"## Original Request\n{request}\n\n"
        f"## Files Changed\n{files_list}\n\n"
        "## Instructions\n"
        "1. Find all REQ-IDs in requirements files\n"
        "2. Scan test files for REQ-ID references\n"
        "3. Report which requirements have test coverage\n"
        "4. Flag any requirements missing test coverage\n"
        "5. Generate a coverage summary\n"
        f"Working Directory: {str(PROJECT_ROOT)}\n"
    )

    agents = [
        {"name": "bug_fixer", "model": "sonnet", "prompt": bug_fixer_prompt},
        {"name": "wiring_agent", "model": "sonnet", "prompt": wiring_prompt},
        {"name": "requirements_tracer", "model": "sonnet", "prompt": tracer_prompt},
    ]

    pipeline["sub_phase"] = "POLISH_WAITING"
    agent_timing = pipeline.setdefault("agent_timing", {"agent_start_times": {}, "respawn_counts": {}})
    for a in agents:
        _record_agent_start(a["name"], agent_timing)
        pipeline.setdefault("_spawned_agents", {})[a["name"]] = a
    pipeline["last_activity_at"] = datetime.now().isoformat()
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"POLISH: Spawning 3 agents (bug_fixer, wiring_agent, requirements_tracer) for {len(changed_files)} files")

    return {
        "action": "spawn_agents",
        "agents": agents,
        "output_dir": str(project_path / "agent-outputs"),
        "phase": "POLISH",
    }


def _next_polish_waiting(state: dict, pipeline: dict, project_path: Path) -> dict:
    """POLISH_WAITING: Check that all 3 polish agent outputs are present."""
    output_dir = project_path / "agent-outputs"
    expected_agents = ["bug_fixer", "wiring_agent", "requirements_tracer"]
    missing = []

    for agent_name in expected_agents:
        resolved_path, content = _resolve_agent_output(output_dir, agent_name, MIN_AGENT_OUTPUT_LENGTH)
        if not resolved_path:
            missing.append(agent_name)

    if missing:
        # Check for agent timeouts before returning error
        for agent_name in missing:
            timeout_result = _check_agent_timeout(
                pipeline.get("agent_timing", {}), agent_name, "sonnet",
                output_dir, project_path,
            )
            if timeout_result:
                if timeout_result["action"] == "respawn_agent":
                    spawned = pipeline.get("_spawned_agents", {}).get(agent_name)
                    if spawned:
                        timeout_result["agent"] = spawned
                        timeout_result["output_dir"] = str(output_dir)
                elif timeout_result["action"] == "escalate_to_user" and match_heal_condition:
                    heal = match_heal_condition("agent_timeout", timeout_result)
                    if heal:
                        timeout_result["heal_suggestion"] = heal
                return timeout_result
        return {
            "action": "error",
            "message": f"Missing or too short polish agent outputs: {', '.join(missing)}. Write to agent-outputs/<agent>.md and call next again.",
            "output_dir": str(output_dir),
            "expected": expected_agents,
        }

    # Collect outputs and generate POLISH-REPORT.md
    report_lines = ["# Polish Report\n"]
    has_issues = False

    for agent_name in expected_agents:
        _, content = _resolve_agent_output(output_dir, agent_name, MIN_AGENT_OUTPUT_LENGTH)
        report_lines.append(f"## {agent_name}\n")
        report_lines.append(content)
        report_lines.append("")

        # Detect issues (P0/P1 findings or missing coverage)
        content_lower = content.lower()
        if any(marker in content_lower for marker in ["p0", "p1", "critical", "missing coverage", "not covered"]):
            has_issues = True

    verdict = "NEEDS_ATTENTION" if has_issues else "CLEAN"
    report_lines.append(f"\n## Verdict: {verdict}\n")

    report_md = "\n".join(report_lines)
    (project_path / "POLISH-REPORT.md").write_text(report_md)

    pipeline["sub_phase"] = "POLISH_REVIEW"
    pipeline["polish_verdict"] = verdict
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"POLISH: All agent outputs collected, verdict={verdict}")

    return {
        "action": "confirm_polish",
        "verdict": verdict,
        "report_path": str(project_path / "POLISH-REPORT.md"),
        "phase": "POLISH",
    }


_POLISH_RETRY_CAP = 2


def _extract_polish_gaps(report_content: str) -> list[str]:
    """Extract specific gap descriptions from a POLISH-REPORT.md.

    Scans for known gap markers (missing tests, missing coverage, wiring issues,
    critical/P0/P1 findings) and returns a deduplicated list of plain-language
    descriptions suitable for decisions.log and user escalation messages.
    """
    gaps: list[str] = []
    content_lower = report_content.lower()

    if "missing coverage" in content_lower or "not covered" in content_lower:
        gaps.append("missing test coverage for one or more requirements")
    if "missing test" in content_lower or "no test" in content_lower:
        gaps.append("missing tests")
    if "p0" in content_lower or "critical" in content_lower:
        gaps.append("critical (P0) bugs or correctness issues")
    if "p1" in content_lower:
        gaps.append("high-severity (P1) findings")
    if "disconnected" in content_lower or "dead code" in content_lower or "not reachable" in content_lower:
        gaps.append("wiring issues (disconnected or unreachable code)")
    if "import" in content_lower and ("error" in content_lower or "missing" in content_lower):
        gaps.append("import or export wiring problems")

    return gaps if gaps else ["unspecified quality issues (see POLISH-REPORT.md)"]


def _next_polish_review(state: dict, pipeline: dict, project_path: Path) -> dict:
    """POLISH_REVIEW: Review POLISH-REPORT.md and route to VERIFY, retry, or escalate.

    SHIP_IT / CLEAN verdict: advance to VERIFY immediately.
    NEEDS_ATTENTION verdict:
      - retry_count < _POLISH_RETRY_CAP: log gaps, increment counter, re-run POLISH agents.
      - retry_count >= _POLISH_RETRY_CAP: escalate to user with plain-language explanation.
    """
    report_path = project_path / "POLISH-REPORT.md"
    if not report_path.exists():
        return {
            "action": "error",
            "message": "Missing POLISH-REPORT.md. Run POLISH_WAITING first.",
        }

    report_content = report_path.read_text()
    verdict = pipeline.get("polish_verdict", "CLEAN")

    # Advance when verdict is clean in pipeline state or when the report says CLEAN with no NEEDS_ATTENTION
    clean_in_report = "CLEAN" in report_content and "NEEDS_ATTENTION" not in report_content
    if verdict in ("CLEAN", "SHIP_IT") or clean_in_report:
        # Reset retry counter on clean pass so it doesn't bleed into next project
        pipeline["polish_retry_count"] = 0
        # Advance to VERIFY — save to disk before cmd_verify() reloads state
        state["phase"] = "VERIFY"
        _save_pipeline_state(state, pipeline, project_path)

        # Auto-run verify to get verifier config
        verify_result = cmd_verify()
        if "error" in verify_result:
            return {"action": "error", "message": verify_result["error"]}

        # Reload state — cmd_verify modified it on disk
        state = qralph_state.load_state()
        pipeline = state.get("pipeline", {})
        pipeline["sub_phase"] = "VERIFY_WAIT"
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(project_path, "POLISH: Clean verdict — advancing to VERIFY")

        verifier = verify_result.get("agent", {})
        return {
            "action": "spawn_agents",
            "agents": [verifier],
            "output_dir": str(project_path / "verification"),
            "phase": "VERIFY",
        }

    # NEEDS_ATTENTION — enforce completeness with retry-then-escalate logic
    retry_count = pipeline.get("polish_retry_count", 0)
    gaps = _extract_polish_gaps(report_content)
    gaps_text = "; ".join(gaps)

    if retry_count < _POLISH_RETRY_CAP:
        retry_count += 1
        pipeline["polish_retry_count"] = retry_count
        pipeline["sub_phase"] = "POLISH_RUN"
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(
            project_path,
            f"POLISH: NEEDS_ATTENTION (retry {retry_count}/{_POLISH_RETRY_CAP}) — gaps: {gaps_text}",
        )
        # Re-spawn polish agents for another round
        return _next_polish_run(state, pipeline, project_path)

    # Retry cap reached — escalate to user
    _log_decision(
        project_path,
        f"POLISH: NEEDS_ATTENTION after {retry_count} retries — escalating to user. Gaps: {gaps_text}",
    )
    gap_bullets = "\n".join(f"  - {g}" for g in gaps)
    escalation_message = (
        f"The POLISH phase ran {retry_count} time(s) but the project still has incomplete areas:\n\n"
        f"{gap_bullets}\n\n"
        "Please review POLISH-REPORT.md for details. You can choose to fix these issues and retry, "
        "accept the current state and continue to VERIFY, or abort."
    )
    return {
        "action": "escalate_to_user",
        "escalation_type": "polish_retry_limit",
        "retry_count": retry_count,
        "gaps": gaps,
        "report_path": str(report_path),
        "message": escalation_message,
        "options": [
            {"id": "retry", "label": "Fix the issues and retry POLISH"},
            {"id": "accept", "label": "Accept the current state and continue to VERIFY"},
            {"id": "abort", "label": "Stop the pipeline here"},
        ],
    }


def _next_verify_wait(state: dict, pipeline: dict, project_path: Path) -> dict:
    """VERIFY_WAIT: Validate verification output exists and passes. Auto-finalize."""
    verify_file = project_path / "verification" / "result.md"
    if not verify_file.exists() or not verify_file.read_text().strip():
        return {
            "action": "error",
            "message": "Missing output: verification/result.md",
            "output_dir": str(project_path / "verification"),
            "expected": ["result"],
        }

    # Parse verdict — block finalize on FAIL or ambiguous
    verification_content = verify_file.read_text().strip()
    verdict = _parse_verdict(verification_content)

    verify_blocked = False
    block_reason = ""
    block_detail: dict = {}

    if verdict == "FAIL":
        _log_decision(project_path, "VERIFY: Verdict is FAIL — blocking finalize")
        verify_blocked = True
        block_reason = "Verification verdict is FAIL. Fix issues and re-run verification."
        block_detail = {"verification_path": str(verify_file)}

    elif verdict != "PASS":
        _log_decision(project_path, "VERIFY: No PASS/FAIL verdict found — blocking finalize")
        verify_blocked = True
        block_reason = "Verification output has no clear verdict. Must contain '\"verdict\": \"PASS\"' to proceed."
        block_detail = {"verification_path": str(verify_file)}

    else:
        # Validate per-criterion results against manifest
        manifest = qralph_state.safe_read_json(project_path / "manifest.json", {})
        criteria_results = _parse_criteria_results(verification_content)
        is_valid, missing, failed, criteria_block_reasons = _validate_criteria_results(
            criteria_results, manifest.get("tasks", [])
        )

        # Validate request satisfaction (REQ-F-N fragment coverage)
        satisfaction_results = _parse_request_satisfaction(verification_content)
        is_satisfied, satisfaction_block_reasons = _validate_request_satisfaction(
            state, satisfaction_results
        )

        # Unify all failure dimensions into one block_reason
        if not is_valid or not is_satisfied:
            all_block_reasons = criteria_block_reasons + satisfaction_block_reasons
            reason = "; ".join(all_block_reasons) if all_block_reasons else "unknown validation failure"
            _log_decision(project_path, f"VERIFY: Validation failed — {reason}")
            verify_blocked = True
            block_reason = f"Verification failed: {reason}. Fix and re-run verification."
            block_detail = {
                "verification_path": str(verify_file),
                "missing_criteria": missing,
                "failed_criteria": failed,
                "unsatisfied_fragments": [
                    r.split(":")[0] for r in satisfaction_block_reasons
                ],
            }

    if verify_blocked:
        return _handle_retry_or_escalate(
            state, pipeline, project_path,
            counter_key="verify_retries",
            max_retries=MAX_VERIFY_RETRIES,
            log_prefix="VERIFY",
            escalation_type="verify_retry_limit",
            escalation_options=[
                {"id": "accept", "label": "Accept the current state and continue to deployment"},
                {"id": "back_to_polish", "label": "Go back for more fixes (return to POLISH phase)"},
                {"id": "abort", "label": "Stop the pipeline here"},
            ],
            escalation_message=(
                "The verification check has failed 3 times. "
                "The project may need more work, or the checks may need to be adjusted. "
                "You can go back for more fixes, accept the current state and continue, or stop here."
            ),
            error_message=block_reason,
            technical_detail=block_reason,
            extra_error_fields=block_detail,
        )

    # Verification passed — reset retry counter
    pipeline["verify_retries"] = 0
    _log_decision(project_path, "VERIFY: Verdict is PASS and all criteria validated — advancing to DEPLOY")

    # Advance to DEPLOY phase (v7.0: idea-to-production)
    state["phase"] = "DEPLOY"
    pipeline["sub_phase"] = "DEPLOY_PREFLIGHT"
    _save_pipeline_state(state, pipeline, project_path)

    # Auto-advance into DEPLOY_PREFLIGHT immediately
    return _next_deploy_preflight(state, pipeline, project_path)


def generate_verify_prompt_v2(manifest: dict, mode: str, has_playwright: bool) -> str:
    """Generate an enhanced verification prompt.

    Always includes: test suite, typecheck, lint, acceptance criteria validation,
    requirements trace.
    If mode=="thorough": includes dependency audit (npm audit), performance check.
    If has_playwright: includes Playwright E2E test run.
    """
    sections = []

    # --- Always included ---
    sections.append(
        "## Verification Checks\n\n"
        "### Test Suite\n"
        "Run the full test suite and report results.\n\n"
        "### Typecheck\n"
        "Run typecheck (e.g. `npx tsc --noEmit`) and confirm zero errors.\n\n"
        "### Lint\n"
        "Run the linter and confirm zero warnings/errors.\n\n"
        "### Acceptance Criteria Validation\n"
        "For each acceptance criterion in the manifest, verify it is satisfied "
        "with file:line evidence.\n\n"
        "### Requirements Trace\n"
        "Confirm every REQ-ID referenced in tests maps to an implemented feature.\n"
    )

    # --- Thorough-only checks ---
    if mode == "thorough":
        sections.append(
            "\n### Dependency Audit\n"
            "Run `npm audit` and report any high/critical vulnerabilities.\n\n"
            "### Performance Check\n"
            "If applicable, measure Core Web Vitals or run performance benchmarks "
            "and flag any regressions.\n"
        )

    # --- Playwright E2E ---
    if has_playwright:
        sections.append(
            "\n### Playwright E2E Tests\n"
            "Run Playwright end-to-end tests (`npx playwright test`) and report results.\n"
        )

    # --- Acceptance criteria from manifest ---
    tasks = manifest.get("tasks", [])
    if tasks:
        criteria_lines = []
        ac_counter = 0
        for task in tasks:
            for ac in task.get("acceptance_criteria", []):
                ac_counter += 1
                criteria_lines.append(f"- **AC-{ac_counter}** [{task.get('id', '?')}] {ac}")
        if criteria_lines:
            sections.append(
                "\n## Acceptance Criteria\n" + "\n".join(criteria_lines) + "\n"
            )

    return "\n".join(sections)


def handle_verify_failure(failures: list[str]) -> dict:
    """Route verification failures back to POLISH phase."""
    return {
        "action": "route_to_polish",
        "failures": failures,
        "message": f"Verification found {len(failures)} issue(s). Routing back to POLISH for remediation.",
    }


def prepare_backtrack(original_request: str, failure_context: dict) -> str:
    """Build a replanning prompt that includes all failure context.

    Args:
        original_request: The original user request.
        failure_context: Dict with reason, persistent_findings, and attempts.

    Returns:
        A string prompt for replanning agents that includes the full failure history.
    """
    parts = [
        f"## Backtrack-to-Replan\n",
        f"The previous plan failed and needs replanning.\n",
        f"### Original Request\n{original_request}\n",
        f"### Failure Reason\n{failure_context.get('reason', 'Unknown')}\n",
    ]

    persistent = failure_context.get("persistent_findings", [])
    if persistent:
        parts.append("### Persistent Findings\n")
        for finding in persistent:
            parts.append(f"- {finding}\n")

    attempts = failure_context.get("attempts", [])
    if attempts:
        parts.append("\n### Previous Attempts\n")
        for attempt in attempts:
            if isinstance(attempt, dict):
                round_num = attempt.get("round", "?")
                fix = attempt.get("fix", "unknown")
                result = attempt.get("result", "unknown")
                parts.append(f"- Round {round_num}: Applied '{fix}' — Result: {result}\n")
            else:
                parts.append(f"- {attempt}\n")

    parts.append(
        "\n### Instructions\n"
        "Create a NEW plan that avoids the failures above. "
        "Consider alternative approaches to resolve persistent findings.\n"
    )

    return "".join(parts)


def can_backtrack(replan_count: int) -> bool:
    """Return True if replanning is still allowed (max 2 replans per project)."""
    return replan_count < 2


def _next_backtrack_replan(state: dict, pipeline: dict, project_path: Path) -> dict:
    """BACKTRACK_REPLAN: Prepare failure context and route back to PLAN phase."""
    ql = pipeline.get("quality_loop", {})
    backtrack_ctx = pipeline.get("backtrack_context", {})
    replan_count = ql.get("replan_count", 0)

    # Increment replan_count
    ql["replan_count"] = replan_count + 1
    pipeline["quality_loop"] = ql

    # Clear agent_timing on backtrack — fresh start for replanned agents
    pipeline["agent_timing"] = {"agent_start_times": {}, "respawn_counts": {}}

    # Build replan prompt from failure context
    replan_prompt = prepare_backtrack(
        original_request=state.get("request", ""),
        failure_context=backtrack_ctx,
    )

    # Route back to PLAN phase
    state["phase"] = "PLAN"
    pipeline["sub_phase"] = "INIT"
    pipeline["replan_prompt"] = replan_prompt
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"BACKTRACK_REPLAN: Replanning (attempt #{replan_count + 1})")

    return {
        "action": "backtrack_replan",
        "phase": "PLAN",
        "sub_phase": "INIT",
        "replan_prompt": replan_prompt,
        "replan_count": replan_count + 1,
    }


def _next_learn_capture(state: dict, pipeline: dict, project_path: Path) -> dict:
    """LEARN_CAPTURE: Extract learnings from quality loop findings and store in pipeline state."""
    project_id = state.get("project_id", "unknown")
    ql = pipeline.get("quality_loop", {})
    rounds_history = ql.get("rounds_history", [])

    # Collect all findings from quality loop history
    all_findings = []
    for round_data in rounds_history:
        findings = round_data.get("findings", [])
        all_findings.extend(findings)

    # Extract learnings using learning-capture module
    learnings = []
    if extract_learnings and all_findings:
        learnings = extract_learnings(all_findings, project_id=project_id)

    pipeline["learnings"] = learnings
    pipeline["sub_phase"] = "LEARN_COMPLETE"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"LEARN_CAPTURE: Extracted {len(learnings)} learnings from {len(all_findings)} findings")

    return {
        "action": "learn_complete",
        "learnings_captured": len(learnings),
        "total_findings_processed": len(all_findings),
    }


def _next_learn_complete(state: dict, pipeline: dict, project_path: Path) -> dict:
    """LEARN_COMPLETE: Generate learning summary, write to project, advance to COMPLETE."""
    project_id = state.get("project_id", "unknown")
    learnings = pipeline.get("learnings", [])

    # Generate and write learning summary
    if generate_learning_summary:
        summary = generate_learning_summary(learnings, project_id=project_id)
    else:
        summary = f"# Learning Summary — {project_id}\n\nNo learning capture module available.\n"

    summary_path = project_path / "learning-summary.md"
    summary_path.write_text(summary)
    _log_decision(project_path, f"LEARN_COMPLETE: Wrote learning summary with {len(learnings)} entries")

    # Auto-run finalize
    finalize_result = cmd_finalize()
    if "error" in finalize_result:
        return {"action": "error", "message": finalize_result["error"]}

    # Reload state — cmd_finalize modified it on disk
    state = qralph_state.load_state()
    pipeline = state.get("pipeline", {})
    pipeline["sub_phase"] = "COMPLETE"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "LEARN: Learning phase complete, project finalized")

    return {
        "action": "complete",
        "summary_path": finalize_result.get("summary_path", str(project_path / "SUMMARY.md")),
        "learning_summary_path": str(summary_path),
    }


def _set_phase_learn(state: dict, pipeline: dict, project_path: Path) -> None:
    """Set pipeline state to LEARN_CAPTURE and save checkpoint."""
    state["phase"] = "LEARN"
    pipeline["sub_phase"] = "LEARN_CAPTURE"
    _save_pipeline_state(state, pipeline, project_path)


def _advance_to_learn(state: dict, pipeline: dict, project_path: Path) -> dict:
    """Advance pipeline to LEARN_CAPTURE phase and return its first action."""
    _set_phase_learn(state, pipeline, project_path)
    return _next_learn_capture(state, pipeline, project_path)


# ─── DEPLOY Phase ────────────────────────────────────────────────────────────


def _detect_deploy_command(project_path: Path, state: dict) -> dict:
    """Detect deploy command and target from project configuration."""
    target_dir = state.get("target_directory", str(PROJECT_ROOT))
    search_roots = [target_dir, str(PROJECT_ROOT)]

    def _find_config(*patterns: str) -> Optional[Path]:
        """Search roots for the first matching config file."""
        for root in search_roots:
            for pattern in patterns:
                matches = list(Path(root).glob(pattern))
                if matches:
                    return matches[0]
        return None

    # Cloudflare Workers
    match = _find_config("**/wrangler.toml", "**/wrangler.jsonc")
    if match:
        return {
            "platform": "cloudflare-workers",
            "deploy_cmd": "npx wrangler deploy",
            "deploy_dir": str(match.parent),
            "config_file": str(match),
        }

    # Vercel
    match = _find_config("**/vercel.json")
    if match:
        return {
            "platform": "vercel",
            "deploy_cmd": "npx vercel --prod",
            "deploy_dir": str(match.parent),
            "config_file": str(match),
        }

    # package.json with deploy script
    for root in search_roots:
        for pkg_path in Path(root).glob("**/package.json"):
            try:
                pkg = json.loads(pkg_path.read_text())
                if "deploy" in pkg.get("scripts", {}):
                    return {
                        "platform": "npm-script",
                        "deploy_cmd": "npm run deploy",
                        "deploy_dir": str(pkg_path.parent),
                        "config_file": str(pkg_path),
                    }
            except (json.JSONDecodeError, OSError):
                continue

    return {"platform": "unknown", "deploy_cmd": "", "deploy_dir": "", "config_file": ""}


def _generate_preflight_checklist(state: dict, deploy_info: dict) -> list[str]:
    """Generate pre-deploy checklist items from project config."""
    checklist = []
    config_file = deploy_info.get("config_file", "")
    platform = deploy_info.get("platform", "unknown")

    if platform == "cloudflare-workers" and config_file:
        try:
            content = Path(config_file).read_text()
            # Check for placeholder KV namespace IDs
            if "placeholder" in content.lower():
                checklist.append("Replace placeholder KV namespace ID in wrangler.toml")
            # Check for secrets referenced
            secrets = re.findall(r'#.*secret.*?:\s*(\w+)', content, re.IGNORECASE)
            if not secrets:
                # Check for common secret patterns in bindings
                for secret_name in ["RESEND_API_KEY", "TURNSTILE_SECRET_KEY", "API_KEY", "SECRET_KEY"]:
                    if secret_name in content:
                        checklist.append(f"Ensure secret '{secret_name}' is set via: npx wrangler secret put {secret_name}")
        except OSError:
            pass

    if platform == "vercel":
        checklist.append("Ensure environment variables are configured in Vercel dashboard")

    # Check for placeholder URLs in deploy directory
    deploy_dir = deploy_info.get("deploy_dir", "")
    if deploy_dir:
        wrangler_path = Path(deploy_dir) / "wrangler.toml"
        if wrangler_path.exists():
            wrangler_content = wrangler_path.read_text()
            if "example.com" in wrangler_content:
                checklist.append("Update SITE_URL from example.com to actual domain")
            if "0x00" in wrangler_content:
                checklist.append("Update TURNSTILE_SITE_KEY from placeholder to actual key")

    if not checklist:
        checklist.append("Review deployment configuration before proceeding")

    return checklist


def _extract_live_url(deploy_output: str, platform: str) -> str:
    """Extract live URL from deploy command output."""
    platform_patterns = {
        "cloudflare-workers": [
            r'(https://[^\s]+\.workers\.dev[^\s]*)',
            r'(https://[^\s]+\.[a-z]{2,}[^\s]*)',  # custom domains
        ],
        "vercel": [
            r'(https://[^\s]+\.vercel\.app[^\s]*)',
        ],
    }

    for pattern in platform_patterns.get(platform, []):
        match = re.search(pattern, deploy_output)
        if match:
            return match.group(1)

    # Generic URL extraction
    match = re.search(r'(https://[^\s]+)', deploy_output)
    return match.group(1) if match else ""


def _next_deploy_preflight(state: dict, pipeline: dict, project_path: Path) -> dict:
    """DEPLOY_PREFLIGHT: Check deploy intent, detect deploy command, generate checklist."""
    request = state.get("request", "")

    # No deploy intent at all → skip DEPLOY and SMOKE, go to LEARN
    if not _has_deploy_intent(request):
        _log_decision(project_path, "DEPLOY: No deploy intent in request — skipping to LEARN")
        return _advance_to_learn(state, pipeline, project_path)

    # Detect deploy command
    deploy_info = _detect_deploy_command(project_path, state)
    pipeline["deploy_info"] = deploy_info

    if not deploy_info.get("deploy_cmd"):
        _log_decision(project_path, "DEPLOY: No deploy command detected — asking user")
        # Keep sub_phase as DEPLOY_PREFLIGHT so retry works after user fixes config
        _save_pipeline_state(state, pipeline, project_path)
        return {
            "action": "error",
            "message": "Could not detect deployment configuration. No wrangler.toml, vercel.json, or 'deploy' npm script found. Add deployment config or skip deployment.",
        }

    # Generate checklist
    checklist = _generate_preflight_checklist(state, deploy_info)
    pipeline["deploy_checklist"] = checklist

    # Explicit deploy → skip gate, go straight to DEPLOY_RUN
    if _has_explicit_deploy(request):
        _log_decision(project_path, f"DEPLOY: Explicit deploy intent — auto-deploying via '{deploy_info['deploy_cmd']}'")
        pipeline["sub_phase"] = "DEPLOY_RUN"
        _save_pipeline_state(state, pipeline, project_path)
        return _next_deploy_run(state, pipeline, project_path)

    # Implicit deploy → show gate
    pipeline["sub_phase"] = "DEPLOY_GATE"
    _save_pipeline_state(state, pipeline, project_path)
    return _next_deploy_gate(state, pipeline, project_path, confirm=False)


def _next_deploy_gate(state: dict, pipeline: dict, project_path: Path, confirm: bool = False) -> dict:
    """DEPLOY_GATE: Confirm deployment with user."""
    deploy_info = pipeline.get("deploy_info", {})
    checklist = pipeline.get("deploy_checklist", [])

    if not confirm:
        pipeline["awaiting_confirmation"] = "confirm_deploy"
        _save_pipeline_state(state, pipeline, project_path)
        return {
            "action": "confirm_deploy",
            "platform": deploy_info.get("platform", "unknown"),
            "deploy_cmd": deploy_info.get("deploy_cmd", ""),
            "checklist": checklist,
            "message": "Ready to deploy. Review the checklist and confirm when ready.",
        }

    if pipeline.get("awaiting_confirmation") != "confirm_deploy":
        return {"action": "error", "message": "Gate violation: must call next (without --confirm) first to see deploy checklist."}
    del pipeline["awaiting_confirmation"]

    _log_decision(project_path, "DEPLOY: User confirmed deployment")
    pipeline["sub_phase"] = "DEPLOY_RUN"
    _save_pipeline_state(state, pipeline, project_path)
    return _next_deploy_run(state, pipeline, project_path)


def _next_deploy_run(state: dict, pipeline: dict, project_path: Path) -> dict:
    """DEPLOY_RUN: Execute deployment command, capture output, extract live URL."""
    deploy_info = pipeline.get("deploy_info", {})
    deploy_cmd = deploy_info.get("deploy_cmd", "")

    if not deploy_cmd:
        return {"action": "error", "message": "No deploy command configured."}

    _log_decision(project_path, f"DEPLOY: Running '{deploy_cmd}'")

    # Run deploy command (shell=False for safety, cwd handles directory)
    try:
        result = subprocess.run(
            shlex.split(deploy_cmd),
            shell=False,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=deploy_info.get("deploy_dir", str(PROJECT_ROOT)),
        )
        deploy_output = result.stdout + "\n" + result.stderr
        deploy_exit_code = result.returncode
    except subprocess.TimeoutExpired:
        deploy_output = "Deployment timed out after 300 seconds."
        deploy_exit_code = 1
    except Exception as e:
        deploy_output = f"Deployment failed: {e}"
        deploy_exit_code = 1

    # Build deploy report
    report_path = project_path / "DEPLOY-REPORT.md"
    report = (
        f"# Deploy Report\n\n"
        f"**Command:** `{deploy_cmd}`\n"
        f"**Exit Code:** {deploy_exit_code}\n"
        f"**Timestamp:** {datetime.now().isoformat()}\n\n"
        f"## Output\n\n```\n{deploy_output.strip()}\n```\n"
    )

    if deploy_exit_code != 0:
        report += "\n## Status: FAILED\n"
        qralph_state.safe_write(report_path, report)
        _log_decision(project_path, f"DEPLOY: Deployment FAILED (exit {deploy_exit_code})")

        # Reset to DEPLOY_PREFLIGHT so next call re-detects config after user fixes issues
        pipeline["sub_phase"] = "DEPLOY_PREFLIGHT"
        pipeline.pop("deploy_info", None)
        _save_pipeline_state(state, pipeline, project_path)

        return {
            "action": "error",
            "message": (
                f"Deployment failed (exit code {deploy_exit_code}). "
                "Fix the issue, then call next to retry. "
                "Review DEPLOY-REPORT.md for details."
            ),
            "deploy_report": str(report_path),
            "deploy_output": deploy_output.strip()[-500:],
        }

    # Extract live URL
    platform = deploy_info.get("platform", "unknown")
    live_url = _extract_live_url(deploy_output, platform)
    pipeline["live_url"] = live_url

    report += "\n## Status: SUCCESS\n"
    if live_url:
        report += f"**Live URL:** {live_url}\n"
    qralph_state.safe_write(report_path, report)
    _log_decision(project_path, f"DEPLOY: Deployment SUCCESS — live at {live_url or 'URL not detected'}")

    # Advance to SMOKE
    state["phase"] = "SMOKE"
    pipeline["sub_phase"] = "SMOKE_GENERATE"
    _save_pipeline_state(state, pipeline, project_path)

    return _next_smoke_generate(state, pipeline, project_path)


# ─── SMOKE Phase ─────────────────────────────────────────────────────────────


def _generate_smoke_agents(manifest: dict, live_url: str, state: dict) -> list[dict]:
    """Generate parallel smoke test agents from acceptance criteria."""
    tasks = manifest.get("tasks", [])
    request = state.get("request", "")

    # Categorize acceptance criteria for parallel agents
    category_keywords = {
        "pages": ["get /", "html", "page", "landing", "theme", "headline", "form", "input", "button"],
        "api": ["post ", "api", "subscribe", "email", "returns {"],
        "security": ["security", "csp", "hsts", "cors", "header"],
        "seo": ["robots", "sitemap", "seo", "meta"],
        "errors": ["404", "error", "unknown", "invalid"],
    }
    categories: dict[str, list[str]] = {cat: [] for cat in category_keywords}

    for task in tasks:
        for ac in task.get("acceptance_criteria", []):
            ac_lower = ac.lower()
            label = f"[{task['id']}] {ac}"
            matched = False
            for cat, keywords in category_keywords.items():
                if any(kw in ac_lower for kw in keywords):
                    categories[cat].append(label)
                    matched = True
                    break
            if not matched:
                categories["pages"].append(label)

    agents = []
    for cat, criteria in categories.items():
        if not criteria:
            continue
        criteria_text = "\n".join(f"- {c}" for c in criteria)
        agents.append({
            "name": f"smoke-{cat}",
            "model": "haiku",
            "prompt": (
                f"You are a production smoke test agent. Your job is to verify the LIVE deployment works.\n\n"
                f"## Live URL\n{live_url}\n\n"
                f"## Original Request\n{request}\n\n"
                f"## Criteria to Verify\n{criteria_text}\n\n"
                f"## Rules\n"
                f"- Use WebFetch for GET requests to verify page content and headers.\n"
                f"- Use Bash with curl for POST requests, HEAD requests, or when you need specific headers.\n"
                f"- For each criterion, report PASS or FAIL with evidence (HTTP status, response snippet).\n"
                f"- Do NOT read source code. You are testing the LIVE deployed site.\n"
                f"- Be fast — check what's checkable via HTTP. Skip criteria that require browser JS execution.\n"
                f"- For criteria that need JavaScript (form submission, loading states), mark as SKIP with reason.\n\n"
                f"## Output Format\n"
                f"Report each criterion as:\n"
                f"- **PASS** [T-NNN] criterion text — evidence\n"
                f"- **FAIL** [T-NNN] criterion text — what went wrong\n"
                f"- **SKIP** [T-NNN] criterion text — why (e.g., requires browser JS)\n\n"
                f"End with a summary line: `SMOKE VERDICT: X passed, Y failed, Z skipped`\n"
            ),
        })

    return agents


def _next_smoke_generate(state: dict, pipeline: dict, project_path: Path) -> dict:
    """SMOKE_GENERATE: Generate parallel smoke test agents."""
    live_url = pipeline.get("live_url", "")

    if not live_url:
        _log_decision(project_path, "SMOKE: No live URL detected — skipping smoke tests, advancing to LEARN")
        return _advance_to_learn(state, pipeline, project_path)

    manifest = qralph_state.safe_read_json(project_path / "manifest.json", {})
    agents = _generate_smoke_agents(manifest, live_url, state)

    if not agents:
        _log_decision(project_path, "SMOKE: No smoke agents generated — advancing to LEARN")
        return _advance_to_learn(state, pipeline, project_path)

    pipeline["smoke_agents"] = [a["name"] for a in agents]
    pipeline["sub_phase"] = "SMOKE_WAIT"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"SMOKE: Spawning {len(agents)} parallel smoke test agents against {live_url}")

    smoke_dir = project_path / "smoke-tests"
    smoke_dir.mkdir(parents=True, exist_ok=True)

    return {
        "action": "spawn_agents",
        "agents": agents,
        "output_dir": str(smoke_dir),
        "phase": "SMOKE",
        "parallel": True,
        "live_url": live_url,
    }


def _next_smoke_wait(state: dict, pipeline: dict, project_path: Path) -> dict:
    """SMOKE_WAIT: Validate smoke test outputs exist."""
    smoke_dir = project_path / "smoke-tests"
    expected = pipeline.get("smoke_agents", [])
    missing = []

    for name in expected:
        output_file = smoke_dir / f"{name}.md"
        if not output_file.exists() or not output_file.read_text().strip():
            missing.append(name)

    if missing:
        return {
            "action": "error",
            "message": f"Missing smoke test outputs: {', '.join(missing)}",
            "output_dir": str(smoke_dir),
            "expected": expected,
        }

    pipeline["sub_phase"] = "SMOKE_VERDICT"
    _save_pipeline_state(state, pipeline, project_path)
    return _next_smoke_verdict(state, pipeline, project_path)


def _next_smoke_verdict(state: dict, pipeline: dict, project_path: Path) -> dict:
    """SMOKE_VERDICT: Aggregate smoke test results. PASS → LEARN, FAIL → show to user."""
    smoke_dir = project_path / "smoke-tests"
    expected = pipeline.get("smoke_agents", [])
    live_url = pipeline.get("live_url", "")

    total_pass = 0
    total_fail = 0
    total_skip = 0
    all_results = []
    failures = []

    for name in expected:
        output_file = smoke_dir / f"{name}.md"
        content = output_file.read_text().strip()
        all_results.append(f"## {name}\n\n{content}\n")

        passes = len(re.findall(r'\*\*PASS\*\*', content))
        fails = len(re.findall(r'\*\*FAIL\*\*', content))
        skips = len(re.findall(r'\*\*SKIP\*\*', content))
        total_pass += passes
        total_fail += fails
        total_skip += skips

        if fails > 0:
            # Extract failure lines
            for line in content.split("\n"):
                if "**FAIL**" in line:
                    failures.append(f"[{name}] {line.strip()}")

    # Write smoke report
    report = (
        f"# Smoke Test Report\n\n"
        f"**Live URL:** {live_url}\n"
        f"**Timestamp:** {datetime.now().isoformat()}\n"
        f"**Result:** {total_pass} passed, {total_fail} failed, {total_skip} skipped\n\n"
    ) + "\n".join(all_results)

    report_path = project_path / "SMOKE-REPORT.md"
    qralph_state.safe_write(report_path, report)

    if total_fail > 0:
        _log_decision(project_path, f"SMOKE: {total_fail} failures detected — showing to user")
        # Stay on SMOKE phase but mark sub_phase so pipeline can advance after user decides
        pipeline["sub_phase"] = "SMOKE_FAILURE_GATE"
        _save_pipeline_state(state, pipeline, project_path)
        return {
            "action": "smoke_failure",
            "live_url": live_url,
            "passed": total_pass,
            "failed": total_fail,
            "skipped": total_skip,
            "failures": failures,
            "smoke_report": str(report_path),
            "message": f"Smoke tests found {total_fail} failure(s). Review and decide: fix + redeploy, or accept and continue.",
        }

    _log_decision(project_path, f"SMOKE: All checks passed ({total_pass} pass, {total_skip} skip) — advancing to LEARN")

    # All passed -- checkpoint to LEARN (next call enters LEARN_CAPTURE)
    _set_phase_learn(state, pipeline, project_path)

    return {
        "action": "smoke_results",
        "live_url": live_url,
        "passed": total_pass,
        "failed": 0,
        "skipped": total_skip,
        "smoke_report": str(report_path),
        "message": f"Production smoke tests passed! {total_pass} checks verified against {live_url}.",
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=f"QRALPH v{__version__} Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    plan_parser = subparsers.add_parser("plan", help="Init project and generate plan agent configs")
    plan_parser.add_argument("request", help="The user's request")
    plan_parser.add_argument("--target-dir", dest="target_dir", default=None, help="Directory for implementation files (relative to PROJECT_ROOT or absolute)")
    plan_parser.add_argument("--mode", choices=["thorough", "quick"], default="thorough", help="Pipeline mode: thorough (starts at IDEATE) or quick (starts at PLAN)")
    plan_parser.add_argument("--dry-run", action="store_true", help="Show template suggestion without creating project")

    subparsers.add_parser("plan-collect", help="Read agent outputs and compute manifest")
    subparsers.add_parser("plan-finalize", help="Finalize plan after user approval")
    subparsers.add_parser("execute", help="Generate execution agent configs")
    subparsers.add_parser("execute-collect", help="Check execution completeness")
    subparsers.add_parser("verify", help="Generate verification agent config")
    subparsers.add_parser("finalize", help="Write SUMMARY.md and mark complete")
    subparsers.add_parser("resume", help="Resume from checkpoint")
    subparsers.add_parser("status", help="Show project status")

    next_parser = subparsers.add_parser("next", help="Get next pipeline action")
    next_parser.add_argument("--confirm", action="store_true", help="Confirm gate (template/plan approval)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "plan": lambda: cmd_plan(args.request, target_dir=args.target_dir, mode=args.mode) if not args.dry_run else _dry_run_plan(args.request),
        "plan-collect": cmd_plan_collect,
        "plan-finalize": cmd_plan_finalize,
        "execute": cmd_execute,
        "execute-collect": cmd_execute_collect,
        "verify": cmd_verify,
        "finalize": cmd_finalize,
        "resume": cmd_resume,
        "status": cmd_status,
        "next": lambda: cmd_next(confirm=args.confirm),
    }

    handler = commands.get(args.command)
    if handler:
        result = handler()
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
        sys.exit(1)


def _dry_run_plan(request: str) -> dict:
    """Show template suggestion without creating a project."""
    suggested, scores = suggest_template(request)
    template = TASK_TEMPLATES[suggested]
    config = qralph_config.load_config()

    agents = []
    for agent_type in template["plan_agents"]:
        agent_config = generate_plan_agent_prompt(agent_type, request, "<project-path>", config or {})
        agents.append({"name": agent_config["name"], "model": agent_config["model"]})

    return {
        "status": "dry_run",
        "suggested_template": suggested,
        "template_description": template["description"],
        "scores": scores,
        "agents": agents,
        "quality_gate": detect_quality_gate(),
    }


if __name__ == "__main__":
    main()
