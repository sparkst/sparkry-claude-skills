#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
PE Overlay Gate Module v5.0 - Deterministic gate checks at every QRALPH phase transition.

This module provides the Principal Engineer overlay for QRALPH orchestration.
Every phase transition (e.g., INIT -> DISCOVERING) passes through a set of
gate checks that enforce ADR compliance, DoD completeness, requirements
inference, codebase navigation strategy, and COE/5-Whys analysis.

Imported by qralph-orchestrator.py. Not a CLI tool.
"""

import glob as glob_mod
import importlib.util
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Import shared state module (same pattern as orchestrator)
# ---------------------------------------------------------------------------
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
_qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(_qralph_state)

safe_write = _qralph_state.safe_write
safe_write_json = _qralph_state.safe_write_json
safe_read_json = _qralph_state.safe_read_json

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VERSION = "5.0.0"

SCRIPT_DIR = Path(__file__).parent

DOD_TEMPLATES = {
    "webapp": "dod-webapp.md",
    "api": "dod-api.md",
    "library": "dod-library.md",
}

REQUIREMENT_PATTERNS: Dict[str, List[str]] = {
    "stripe": [
        "test mode configuration",
        "webhook signature validation",
        "idempotency keys",
    ],
    "cloudflare": [
        "wrangler dev testing",
        "environment bindings",
        "secrets management",
    ],
    "database": [
        "migration testing",
        "rollback strategy",
        "connection pooling",
    ],
    "auth": [
        "token expiry handling",
        "session management",
        "CSRF protection",
    ],
    "api": [
        "rate limiting",
        "input validation",
        "error response format",
    ],
    "email": [
        "template testing",
        "bounce handling",
        "unsubscribe mechanism",
    ],
}

COE_REQUIRED_FIELDS = [
    "task_id",
    "finding",
    "why_1",
    "why_2",
    "why_3",
    "root_cause",
    "fix_strategy",
    "pattern_scope",
    "search_patterns",
]

# Keywords that suggest architectural decisions worthy of ADRs
_ADR_SIGNAL_KEYWORDS = [
    "should use",
    "recommend",
    "architecture",
    "pattern",
    "approach",
    "migrate to",
    "replace with",
    "adopt",
    "deprecate",
]

# Dependency -> requirement-pattern key mapping for package scanning
_DEPENDENCY_SIGNALS: Dict[str, str] = {
    "stripe": "stripe",
    "@stripe/stripe-js": "stripe",
    "hono": "api",
    "express": "api",
    "fastify": "api",
    "flask": "api",
    "django": "api",
    "resend": "email",
    "nodemailer": "email",
    "sendgrid": "email",
    "@cloudflare/workers-types": "cloudflare",
    "wrangler": "cloudflare",
    "prisma": "database",
    "@prisma/client": "database",
    "drizzle-orm": "database",
    "sequelize": "database",
    "sqlalchemy": "database",
    "next-auth": "auth",
    "lucia": "auth",
    "passport": "auth",
    "jsonwebtoken": "auth",
    "jose": "auth",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_repo_root(state: dict, project_path: Path) -> Path:
    """Resolve the target repository root.

    Uses state["repo_root"] if present, otherwise walks up from cwd to find
    a .git directory. Falls back to cwd.
    """
    repo_root_str = state.get("repo_root")
    if repo_root_str:
        candidate = Path(repo_root_str)
        if candidate.is_dir():
            return candidate

    current = Path.cwd()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def _gate_result(
    passed: bool,
    *,
    blockers: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    **extra: Any,
) -> dict:
    """Build a standard gate-check return dict."""
    result: Dict[str, Any] = {
        "passed": passed,
        "blockers": blockers or [],
        "warnings": warnings or [],
    }
    result.update(extra)
    return result


def _read_text_safe(path: Path) -> str:
    """Read a text file, returning empty string on any failure."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _collect_agent_outputs(project_path: Path) -> List[Tuple[str, str]]:
    """Collect agent output markdown files as (filename, content) tuples."""
    outputs_dir = project_path / "agent-outputs"
    if not outputs_dir.is_dir():
        return []
    results = []
    for md_file in sorted(outputs_dir.glob("*.md")):
        content = _read_text_safe(md_file)
        if content:
            results.append((md_file.name, content))
    return results


# ---------------------------------------------------------------------------
# ADR Functions
# ---------------------------------------------------------------------------

def _parse_adr_file(path: Path) -> dict:
    """Parse a single ADR markdown file into structured data.

    Extracts:
      - id: derived from filename (ADR-NNN)
      - title: first heading
      - status: Accepted / Proposed / Superseded
      - enforcement_rules: list of {pattern, scope, check} dicts
    """
    content = _read_text_safe(path)
    if not content:
        return {}

    adr: Dict[str, Any] = {
        "id": path.stem,
        "file": str(path),
        "title": "",
        "status": "Proposed",
        "enforcement_rules": [],
    }

    # Extract title from first heading
    title_match = re.search(r"^#\s+(.+)", content, re.MULTILINE)
    if title_match:
        adr["title"] = title_match.group(1).strip()

    # Extract status
    status_match = re.search(
        r"(?:^|\n)\*?\*?Status\*?\*?\s*:\s*(Accepted|Proposed|Superseded|Deprecated|Draft)",
        content,
        re.IGNORECASE,
    )
    if status_match:
        adr["status"] = status_match.group(1).strip().capitalize()

    # Extract enforcement rules section
    enforcement_section = re.search(
        r"##\s*Enforcement\s*Rules?\s*\n(.*?)(?=\n##|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if enforcement_section:
        section_text = enforcement_section.group(1)
        # Parse bullet items with Pattern/Scope/Check fields
        current_rule: Dict[str, str] = {}
        for line in section_text.splitlines():
            line = line.strip()
            field_match = re.match(
                r"[-*]\s*(Pattern|Scope|Check)\s*:\s*(.+)", line, re.IGNORECASE
            )
            if field_match:
                key = field_match.group(1).lower()
                current_rule[key] = field_match.group(2).strip()
                if len(current_rule) >= 2:
                    adr["enforcement_rules"].append(dict(current_rule))
            elif line.startswith(("-", "*")) and current_rule:
                current_rule = {}

        # Flush last rule if it has content
        if current_rule and current_rule not in adr["enforcement_rules"]:
            adr["enforcement_rules"].append(dict(current_rule))

    return adr


def load_adrs(state: dict, project_path: Path) -> dict:
    """Load ADRs from docs/adrs/ in the target repo.

    Looks for docs/adrs/ADR-NNN-*.md files. Parses markdown to extract
    status, enforcement rules (optional section with Pattern, Scope, Check).

    Returns: {"passed": True, "adrs_loaded": N, "adrs": [...]}
    Falls back gracefully if no ADRs exist.
    """
    repo_root = _resolve_repo_root(state, project_path)
    adrs_dir = repo_root / "docs" / "adrs"

    if not adrs_dir.is_dir():
        return _gate_result(True, adrs_loaded=0, adrs=[])

    adr_files = sorted(adrs_dir.glob("ADR-*-*.md")) + sorted(adrs_dir.glob("adr-*-*.md"))
    adrs = []
    for adr_file in adr_files:
        parsed = _parse_adr_file(adr_file)
        if parsed:
            adrs.append(parsed)

    # Store in state for downstream checks
    state["_pe_adrs"] = adrs
    return _gate_result(True, adrs_loaded=len(adrs), adrs=adrs)


def check_adr_consistency(state: dict, project_path: Path) -> dict:
    """Check agent findings against loaded ADRs for contradictions.

    Reads agent-outputs/*.md files, checks enforcement rules from ADRs.
    Returns: {"passed": bool, "contradictions": [...], "warnings": [...]}
    """
    adrs = state.get("_pe_adrs", [])
    if not adrs:
        return _gate_result(True, contradictions=[])

    agent_outputs = _collect_agent_outputs(project_path)
    if not agent_outputs:
        return _gate_result(True, contradictions=[],
                            warnings=["No agent outputs found to check against ADRs"])

    contradictions: List[str] = []
    warnings: List[str] = []

    for adr in adrs:
        if adr.get("status", "").lower() in ("superseded", "deprecated"):
            continue

        for rule in adr.get("enforcement_rules", []):
            pattern_str = rule.get("pattern", "")
            if not pattern_str:
                continue

            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
            except re.error:
                warnings.append(
                    f"ADR {adr['id']}: invalid regex pattern '{pattern_str}'"
                )
                continue

            check_type = rule.get("check", "warn").lower()
            for filename, content in agent_outputs:
                matches = pattern.findall(content)
                if matches:
                    msg = (
                        f"ADR {adr['id']} enforcement '{pattern_str}' "
                        f"triggered in {filename} ({len(matches)} match(es))"
                    )
                    if check_type == "block":
                        contradictions.append(msg)
                    else:
                        warnings.append(msg)

    passed = len(contradictions) == 0
    return _gate_result(passed, contradictions=contradictions, warnings=warnings)


def propose_new_adrs(state: dict, project_path: Path) -> dict:
    """Identify architectural decisions in agent outputs that should become ADRs.

    Scans for keywords indicating architectural recommendations.
    Returns: {"passed": True, "proposed_adrs": [...]}
    """
    agent_outputs = _collect_agent_outputs(project_path)
    if not agent_outputs:
        return _gate_result(True, proposed_adrs=[])

    proposed: List[Dict[str, str]] = []
    counter = 1

    for filename, content in agent_outputs:
        agent_name = filename.replace(".md", "")
        lines = content.splitlines()

        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in _ADR_SIGNAL_KEYWORDS:
                if keyword in line_lower:
                    # Extract surrounding context (up to 3 lines)
                    start = max(0, i - 1)
                    end = min(len(lines), i + 3)
                    context = "\n".join(lines[start:end]).strip()

                    # Derive a title from the line
                    title = line.strip().lstrip("#-*> ").rstrip(".:;")
                    if len(title) > 120:
                        title = title[:117] + "..."

                    proposed.append({
                        "id": f"PROPOSED-{counter:03d}",
                        "title": title,
                        "context": context,
                        "source_agent": agent_name,
                    })
                    counter += 1
                    break  # One proposal per line

    # Deduplicate by title similarity (exact match only for simplicity)
    seen_titles: set = set()
    deduped: List[Dict[str, str]] = []
    for p in proposed:
        normalized = p["title"].lower().strip()
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            deduped.append(p)

    # Re-number after dedup
    for i, p in enumerate(deduped, 1):
        p["id"] = f"PROPOSED-{i:03d}"

    state["_pe_proposed_adrs"] = deduped
    return _gate_result(True, proposed_adrs=deduped)


def adr_final_check(state: dict, project_path: Path) -> dict:
    """Final ADR compliance check against changed files."""
    adrs = state.get("_pe_adrs", [])
    if not adrs:
        return _gate_result(True, warnings=["No ADRs loaded; skipping final check"])

    enforceable = [a for a in adrs if a.get("enforcement_rules")
                   and a.get("status", "").lower() not in ("superseded", "deprecated")]

    if not enforceable:
        return _gate_result(True, checked=0)

    # Check agent outputs one more time for any remaining violations
    result = check_adr_consistency(state, project_path)
    result["checked"] = len(enforceable)
    return result


def final_adr_compliance(state: dict, project_path: Path) -> dict:
    """Sign-off check - all enforceable ADRs verified."""
    adrs = state.get("_pe_adrs", [])
    enforceable = [a for a in adrs if a.get("enforcement_rules")
                   and a.get("status", "").lower() not in ("superseded", "deprecated")]

    if not enforceable:
        return _gate_result(True, signed_off=True,
                            warnings=["No enforceable ADRs to verify"])

    result = check_adr_consistency(state, project_path)
    result["signed_off"] = result["passed"]
    return result


def save_proposed_adrs(proposed_adrs: list, project_path: Path):
    """Write proposed ADRs to project_path/proposed-adrs/ directory."""
    if not proposed_adrs:
        return

    output_dir = project_path / "proposed-adrs"
    output_dir.mkdir(parents=True, exist_ok=True)

    for adr in proposed_adrs:
        adr_id = adr.get("id", "PROPOSED-000")
        title = adr.get("title", "Untitled")
        safe_title = re.sub(r"[^a-zA-Z0-9\-]", "-", title.lower())[:60]
        filename = f"{adr_id}-{safe_title}.md"

        content = (
            f"# {adr_id}: {title}\n\n"
            f"**Status:** Proposed\n\n"
            f"## Context\n\n{adr.get('context', 'N/A')}\n\n"
            f"## Source\n\nAgent: {adr.get('source_agent', 'unknown')}\n\n"
            f"## Decision\n\n_To be determined._\n\n"
            f"## Consequences\n\n_To be determined._\n"
        )
        safe_write(output_dir / filename, content)

    # Write index
    index_lines = ["# Proposed ADRs\n"]
    for adr in proposed_adrs:
        index_lines.append(f"- **{adr['id']}**: {adr.get('title', 'Untitled')} "
                           f"(from {adr.get('source_agent', 'unknown')})")
    safe_write(output_dir / "INDEX.md", "\n".join(index_lines) + "\n")


# ---------------------------------------------------------------------------
# DoD Functions
# ---------------------------------------------------------------------------

def detect_project_type(project_path: Path) -> str:
    """Detect project type by examining package.json, pyproject.toml, etc.

    Rules:
      - package.json with react/vue/svelte/next -> "webapp"
      - package.json with hono/express or Python web framework -> "api"
      - package.json with exports/main or pyproject.toml with build-system -> "library"
      - Default: "api"
    """
    state_stub: dict = {}
    repo_root = _resolve_repo_root(state_stub, project_path)

    # Check package.json
    pkg_path = repo_root / "package.json"
    pkg = safe_read_json(pkg_path) if pkg_path.is_file() else None

    if pkg and isinstance(pkg, dict):
        all_deps = {}
        for dep_key in ("dependencies", "devDependencies", "peerDependencies"):
            deps = pkg.get(dep_key, {})
            if isinstance(deps, dict):
                all_deps.update(deps)

        dep_names_lower = {k.lower() for k in all_deps}

        # Webapp indicators
        webapp_signals = {"react", "vue", "svelte", "next", "@sveltejs/kit",
                          "nuxt", "vite", "gatsby", "remix", "astro"}
        if dep_names_lower & webapp_signals:
            return "webapp"

        # API indicators
        api_signals = {"hono", "express", "fastify", "koa", "@hono/node-server"}
        if dep_names_lower & api_signals:
            return "api"

        # Library indicators (has exports or main, no framework)
        if pkg.get("exports") or pkg.get("main"):
            return "library"

    # Check pyproject.toml
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        content = _read_text_safe(pyproject)
        if "build-system" in content.lower():
            # Check for web frameworks
            if any(fw in content.lower() for fw in ("flask", "django", "fastapi", "starlette")):
                return "api"
            return "library"

    # Check for requirements.txt with web frameworks
    req_txt = repo_root / "requirements.txt"
    if req_txt.is_file():
        content = _read_text_safe(req_txt).lower()
        if any(fw in content for fw in ("flask", "django", "fastapi", "starlette", "aiohttp")):
            return "api"

    # Check for wrangler.toml (Cloudflare Worker = api)
    if (repo_root / "wrangler.toml").is_file() or (repo_root / "wrangler.jsonc").is_file():
        return "api"

    return "api"


def load_dod_template(template_name: str) -> dict:
    """Load and parse a DoD template from .qralph/templates/.

    Returns: {"categories": {"Code Quality": [items], ...}, "blockers": ["Testing", "Security"]}
    If the template file does not exist, returns a sensible default.
    """
    templates_dir = SCRIPT_DIR.parent / "templates"
    template_path = templates_dir / template_name

    if template_path.is_file():
        content = _read_text_safe(template_path)
        return _parse_dod_markdown(content)

    # Provide built-in defaults when template files are absent
    return _default_dod_template()


def _parse_dod_markdown(content: str) -> dict:
    """Parse a DoD markdown template into categories and blocker designations."""
    categories: Dict[str, List[str]] = {}
    blockers: List[str] = []
    current_category = ""

    for line in content.splitlines():
        heading_match = re.match(r"^##\s+(.+)", line)
        if heading_match:
            current_category = heading_match.group(1).strip()
            # Strip blocker marker
            if "[BLOCKER]" in current_category.upper():
                current_category = current_category.replace("[BLOCKER]", "").replace("[blocker]", "").strip()
                blockers.append(current_category)
            categories.setdefault(current_category, [])
            continue

        item_match = re.match(r"^\s*[-*]\s+\[[ x]?\]\s*(.*)", line)
        if item_match and current_category:
            item_text = item_match.group(1).strip()
            if item_text:
                categories[current_category].append(item_text)

    # Default blockers if not explicitly marked
    if not blockers:
        for cat in categories:
            if cat.lower() in ("testing", "security"):
                blockers.append(cat)

    return {"categories": categories, "blockers": blockers}


def _default_dod_template() -> dict:
    """Provide a built-in default DoD when no template file exists."""
    return {
        "categories": {
            "Code Quality": [
                "No lint errors or warnings",
                "Type-safe with no `any` types",
                "Functions under 40 lines",
            ],
            "Testing": [
                "Unit tests for business logic",
                "Integration tests for API endpoints",
                "All tests passing",
            ],
            "Security": [
                "Input validation on all endpoints",
                "No secrets in source code",
                "Authentication/authorization verified",
            ],
            "Documentation": [
                "API endpoints documented",
                "README updated if applicable",
            ],
        },
        "blockers": ["Testing", "Security"],
    }


def select_dod_template(state: dict, project_path: Path) -> dict:
    """Select DoD template based on detected project type.

    Returns: {"passed": True, "project_type": str, "dod_template": str}
    """
    project_type = detect_project_type(project_path)
    template_name = DOD_TEMPLATES.get(project_type, DOD_TEMPLATES["api"])

    state["_pe_project_type"] = project_type
    state["_pe_dod_template"] = template_name
    state["_pe_dod"] = load_dod_template(template_name)

    return _gate_result(True, project_type=project_type, dod_template=template_name)


def validate_dod_selected(state: dict, project_path: Path) -> dict:
    """Verify a DoD template was selected during INIT->DISCOVERING."""
    if state.get("_pe_dod_template"):
        return _gate_result(True)

    sub_result = select_dod_template(state, project_path)
    sub_result.setdefault("warnings", [])
    sub_result["warnings"].insert(
        0, "DoD template was not selected in INIT phase; selecting now"
    )
    return sub_result


def validate_dod_completeness(state: dict, project_path: Path) -> dict:
    """Check that DoD template categories are addressable by findings."""
    dod = state.get("_pe_dod")
    if not dod:
        return _gate_result(True, warnings=["No DoD loaded; skipping completeness check"])

    agent_outputs = _collect_agent_outputs(project_path)
    all_output_text = " ".join(content for _, content in agent_outputs).lower()

    categories = dod.get("categories", {})
    unaddressed: List[str] = []
    warnings: List[str] = []

    for category, items in categories.items():
        category_lower = category.lower()
        # Simple heuristic: check if the category name appears in agent outputs
        if category_lower not in all_output_text and not any(
            item.lower()[:20] in all_output_text for item in items
        ):
            if category in dod.get("blockers", []):
                unaddressed.append(
                    f"Blocker category '{category}' not addressed in agent outputs"
                )
            else:
                warnings.append(
                    f"Category '{category}' not explicitly addressed in agent outputs"
                )

    passed = len(unaddressed) == 0
    return _gate_result(passed, blockers=unaddressed, warnings=warnings)


def full_dod_check(state: dict, project_path: Path) -> dict:
    """Full DoD compliance check. Items in Testing and Security are blockers."""
    dod = state.get("_pe_dod")
    if not dod:
        return _gate_result(True, warnings=["No DoD loaded; skipping full check"])

    agent_outputs = _collect_agent_outputs(project_path)
    all_output_text = " ".join(content for _, content in agent_outputs).lower()

    blocker_categories = set(dod.get("blockers", []))
    categories = dod.get("categories", {})

    blockers: List[str] = []
    warnings: List[str] = []
    items_checked = 0
    items_satisfied = 0

    for category, items in categories.items():
        is_blocker = category in blocker_categories
        for item in items:
            items_checked += 1
            # Check if item or its key phrases appear in outputs
            item_words = item.lower().split()
            key_phrases = [" ".join(item_words[i:i+3])
                           for i in range(max(1, len(item_words) - 2))]
            found = any(phrase in all_output_text for phrase in key_phrases)

            if found:
                items_satisfied += 1
            elif is_blocker:
                blockers.append(f"[{category}] {item}")
            else:
                warnings.append(f"[{category}] {item} - not confirmed in outputs")

    passed = len(blockers) == 0
    return _gate_result(
        passed,
        blockers=blockers,
        warnings=warnings,
        items_checked=items_checked,
        items_satisfied=items_satisfied,
    )


def dod_signoff(state: dict, project_path: Path) -> dict:
    """Final DoD sign-off."""
    result = full_dod_check(state, project_path)
    result["signed_off"] = result["passed"]
    return result


# ---------------------------------------------------------------------------
# Requirements Inference
# ---------------------------------------------------------------------------

def infer_requirements(state: dict, project_path: Path) -> dict:
    """Infer implicit requirements from the request text and codebase.

    Scans request text for REQUIREMENT_PATTERNS keys. Also scans
    package.json/requirements.txt for dependency-based inferences.
    Returns: {"passed": True, "inferred": [...], "confidence": float}
    """
    request_text = state.get("request", "").lower()
    repo_root = _resolve_repo_root(state, project_path)

    inferred: List[Dict[str, Any]] = []
    matched_keys: set = set()

    # Phase 1: Scan request text for pattern keys
    for key, requirements in REQUIREMENT_PATTERNS.items():
        if key in request_text:
            matched_keys.add(key)
            for req in requirements:
                inferred.append({
                    "source": "request_text",
                    "trigger": key,
                    "requirement": req,
                    "confidence": 0.8,
                })

    # Phase 2: Scan dependencies for additional signals
    pkg_path = repo_root / "package.json"
    pkg = safe_read_json(pkg_path) if pkg_path.is_file() else None

    if pkg and isinstance(pkg, dict):
        all_deps = set()
        for dep_key in ("dependencies", "devDependencies"):
            deps = pkg.get(dep_key, {})
            if isinstance(deps, dict):
                all_deps.update(deps.keys())

        for dep_name, pattern_key in _DEPENDENCY_SIGNALS.items():
            if dep_name in all_deps and pattern_key not in matched_keys:
                matched_keys.add(pattern_key)
                for req in REQUIREMENT_PATTERNS.get(pattern_key, []):
                    inferred.append({
                        "source": "dependency",
                        "trigger": dep_name,
                        "requirement": req,
                        "confidence": 0.6,
                    })

    # Phase 3: Scan requirements.txt
    req_txt = repo_root / "requirements.txt"
    if req_txt.is_file():
        content = _read_text_safe(req_txt).lower()
        for dep_name, pattern_key in _DEPENDENCY_SIGNALS.items():
            if dep_name in content and pattern_key not in matched_keys:
                matched_keys.add(pattern_key)
                for req in REQUIREMENT_PATTERNS.get(pattern_key, []):
                    inferred.append({
                        "source": "requirements.txt",
                        "trigger": dep_name,
                        "requirement": req,
                        "confidence": 0.6,
                    })

    # Compute overall confidence
    if not inferred:
        confidence = 1.0  # No inferences needed = high confidence
    else:
        confidence = sum(r["confidence"] for r in inferred) / len(inferred)

    state["_pe_inferred_requirements"] = inferred
    return _gate_result(True, inferred=inferred, confidence=round(confidence, 2))


def confirm_inferred_requirements(state: dict, project_path: Path) -> dict:
    """Confirm that inferred requirements were acknowledged.

    Checks that the inferred requirements list is present in state. If no
    requirements were inferred, passes automatically.
    """
    inferred = state.get("_pe_inferred_requirements", [])
    if not inferred:
        return _gate_result(True, warnings=["No requirements were inferred"])

    # Check if acknowledgment flag is set (set by orchestrator after user review)
    acknowledged = state.get("_pe_requirements_acknowledged", False)
    if acknowledged:
        return _gate_result(True, confirmed=len(inferred))

    # Not a blocker - just a warning for awareness
    return _gate_result(
        True,
        warnings=[
            f"{len(inferred)} inferred requirement(s) have not been explicitly acknowledged",
        ],
        inferred_count=len(inferred),
    )


# ---------------------------------------------------------------------------
# Codebase Navigation Strategy
# ---------------------------------------------------------------------------

def select_nav_strategy(state: dict, project_path: Path) -> dict:
    """Select codebase navigation strategy based on project structure.

    - tsconfig.json present -> "ts-aware"
    - Multiple language extensions -> "polyglot"
    - Default -> "grep-enhanced"

    Returns: {"passed": True, "strategy": str, "detected_languages": [...]}
    """
    repo_root = _resolve_repo_root(state, project_path)

    # Detect languages by extension sampling
    extension_counts: Dict[str, int] = {}
    language_map = {
        ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript",
        ".py": "Python",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".rb": "Ruby",
        ".swift": "Swift",
        ".kt": "Kotlin",
    }

    # Sample up to 500 files to avoid slow scans on large repos
    file_count = 0
    for root, dirs, files in os.walk(str(repo_root)):
        # Skip hidden dirs, node_modules, vendor, etc.
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in ("node_modules", "vendor", "__pycache__",
                                 "dist", "build", ".git", "target")]
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in language_map:
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
                file_count += 1
            if file_count >= 500:
                break
        if file_count >= 500:
            break

    detected_languages = sorted(set(
        language_map[ext] for ext in extension_counts if ext in language_map
    ))

    # Strategy selection
    strategy = "grep-enhanced"  # default

    if (repo_root / "tsconfig.json").is_file():
        strategy = "ts-aware"
    elif len(detected_languages) >= 3:
        strategy = "polyglot"

    state["_pe_nav_strategy"] = strategy
    state["_pe_detected_languages"] = detected_languages

    return _gate_result(
        True,
        strategy=strategy,
        detected_languages=detected_languages,
    )


def validate_nav_strategy_selected(state: dict, project_path: Path) -> dict:
    """Verify nav strategy was selected."""
    if state.get("_pe_nav_strategy"):
        return _gate_result(True, strategy=state["_pe_nav_strategy"])

    # Auto-select if missing
    sub_result = select_nav_strategy(state, project_path)
    sub_result.setdefault("warnings", [])
    sub_result["warnings"].insert(
        0, "Nav strategy was not selected in INIT phase; selecting now"
    )
    return sub_result


# ---------------------------------------------------------------------------
# COE / 5-Whys System
# ---------------------------------------------------------------------------

def create_coe_template(task_id: str, finding: str) -> dict:
    """Create a blank COE analysis template for a task."""
    return {
        "task_id": task_id,
        "finding": finding,
        "created_at": datetime.now().isoformat(),
        "why_1": "",
        "why_2": "",
        "why_3": "",
        "root_cause": "",
        "fix_strategy": "",
        "pattern_scope": "",
        "search_patterns": [],
    }


def validate_coe_analysis(coe_path: Path) -> dict:
    """Validate COE analysis file has all required fields filled.

    Returns: {"valid": bool, "missing_fields": [...], "warnings": [...]}
    """
    data = safe_read_json(coe_path)
    if not data:
        return {"valid": False, "missing_fields": list(COE_REQUIRED_FIELDS), "warnings": []}

    missing: List[str] = []
    warnings: List[str] = []

    for field in COE_REQUIRED_FIELDS:
        value = data.get(field)
        if value is None or value == "" or value == []:
            missing.append(field)

    # Warn on shallow analysis
    if data.get("why_1") and not data.get("why_2"):
        warnings.append("Only 1 'why' level filled; deeper analysis recommended")
    if data.get("why_2") and not data.get("why_3"):
        warnings.append("Only 2 'why' levels filled; consider going deeper")

    search_patterns = data.get("search_patterns", [])
    if isinstance(search_patterns, list) and len(search_patterns) == 0:
        missing.append("search_patterns")
    elif isinstance(search_patterns, list):
        for i, pat in enumerate(search_patterns):
            if not isinstance(pat, str) or not pat.strip():
                warnings.append(f"search_patterns[{i}] is empty or not a string")

    return {"valid": len(missing) == 0, "missing_fields": missing, "warnings": warnings}


def load_coe_analysis(project_path: Path, task_id: str) -> Optional[dict]:
    """Load COE analysis from project_path/coe-analyses/task_id.json."""
    coe_dir = project_path / "coe-analyses"
    coe_file = coe_dir / f"{task_id}.json"

    if not coe_file.is_file():
        return None

    return safe_read_json(coe_file)


# ---------------------------------------------------------------------------
# Pattern Sweep
# ---------------------------------------------------------------------------

def pattern_sweep(project_path: Path, task_id: str, coe_analysis: dict) -> dict:
    """Run pattern sweep using COE analysis search_patterns.

    Searches the repo root for remaining instances of the patterns identified
    in the COE analysis.
    Returns: {"clean": bool, "remaining_instances": [...], "patterns_checked": [...]}
    """
    search_patterns = coe_analysis.get("search_patterns", [])
    if not search_patterns:
        return {"clean": True, "remaining_instances": [], "patterns_checked": []}

    # Resolve repo root from a stub state
    repo_root = _resolve_repo_root({}, project_path)
    remaining: List[Dict[str, Any]] = []
    patterns_checked: List[str] = []

    # Directories to skip during sweep
    skip_dirs = {".git", "node_modules", "__pycache__", "dist", "build",
                 ".qralph", "vendor", "target", ".next", ".svelte-kit"}

    for pattern_str in search_patterns:
        if not isinstance(pattern_str, str) or not pattern_str.strip():
            continue

        patterns_checked.append(pattern_str)

        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
        except re.error:
            remaining.append({
                "pattern": pattern_str,
                "error": "invalid regex",
                "file": None,
                "line": None,
            })
            continue

        # Walk the repo
        for root, dirs, files in os.walk(str(repo_root)):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for fname in files:
                fpath = Path(root) / fname
                # Skip binary / large files
                if fpath.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".ico",
                                             ".woff", ".woff2", ".ttf", ".eot",
                                             ".zip", ".tar", ".gz", ".lock"):
                    continue

                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                for line_num, line in enumerate(content.splitlines(), 1):
                    if pattern.search(line):
                        remaining.append({
                            "pattern": pattern_str,
                            "file": str(fpath.relative_to(repo_root)),
                            "line": line_num,
                            "text": line.strip()[:200],
                        })

    return {
        "clean": len(remaining) == 0,
        "remaining_instances": remaining,
        "patterns_checked": patterns_checked,
    }


def pattern_sweep_summary(state: dict, project_path: Path) -> dict:
    """Summarize pattern sweep results across all fixed tasks."""
    coe_dir = project_path / "coe-analyses"
    if not coe_dir.is_dir():
        return _gate_result(True, sweeps_run=0,
                            warnings=["No COE analyses directory found"])

    total_sweeps = 0
    total_remaining = 0
    all_remaining: List[Dict[str, Any]] = []
    blockers: List[str] = []

    for coe_file in sorted(coe_dir.glob("*.json")):
        coe_data = safe_read_json(coe_file)
        if not coe_data:
            continue

        task_id = coe_data.get("task_id", coe_file.stem)
        result = pattern_sweep(project_path, task_id, coe_data)
        total_sweeps += 1

        if not result["clean"]:
            count = len(result["remaining_instances"])
            total_remaining += count
            all_remaining.extend(result["remaining_instances"])
            blockers.append(
                f"Task {task_id}: {count} remaining instance(s) of pattern(s)"
            )

    passed = total_remaining == 0
    return _gate_result(
        passed,
        blockers=blockers,
        sweeps_run=total_sweeps,
        total_remaining=total_remaining,
        remaining_instances=all_remaining[:50],  # Cap output size
    )


# ---------------------------------------------------------------------------
# Memory / Learnings
# ---------------------------------------------------------------------------

def store_learnings_to_memory(state: dict, project_path: Path) -> dict:
    """Store project learnings at completion.

    Captures ADR decisions, common patterns found, COE root causes.
    Writes to project_path/learnings.json.
    """
    learnings: Dict[str, Any] = {
        "project_id": state.get("project_id", "unknown"),
        "completed_at": datetime.now().isoformat(),
        "project_type": state.get("_pe_project_type", "unknown"),
        "nav_strategy": state.get("_pe_nav_strategy", "unknown"),
        "adrs_loaded": len(state.get("_pe_adrs", [])),
        "proposed_adrs": len(state.get("_pe_proposed_adrs", [])),
        "inferred_requirements": len(state.get("_pe_inferred_requirements", [])),
        "coe_analyses": [],
        "patterns_found": [],
    }

    # Collect COE summaries
    coe_dir = project_path / "coe-analyses"
    if coe_dir.is_dir():
        for coe_file in sorted(coe_dir.glob("*.json")):
            coe_data = safe_read_json(coe_file)
            if coe_data:
                learnings["coe_analyses"].append({
                    "task_id": coe_data.get("task_id"),
                    "root_cause": coe_data.get("root_cause", ""),
                    "fix_strategy": coe_data.get("fix_strategy", ""),
                })

    # Save proposed ADRs if any
    proposed = state.get("_pe_proposed_adrs", [])
    if proposed:
        save_proposed_adrs(proposed, project_path)

    # Write learnings file
    safe_write_json(project_path / "learnings.json", learnings)

    return _gate_result(
        True,
        learnings_stored=True,
        coe_count=len(learnings["coe_analyses"]),
        proposed_adr_count=len(proposed),
    )


# ---------------------------------------------------------------------------
# Gate Check Registry
# ---------------------------------------------------------------------------

GATE_CHECKS: Dict[Tuple[str, str], list] = {
    ("INIT", "DISCOVERING"): [
        load_adrs,
        infer_requirements,
        select_dod_template,
        select_nav_strategy,
    ],
    ("DISCOVERING", "REVIEWING"): [
        validate_nav_strategy_selected,
        validate_dod_selected,
        confirm_inferred_requirements,
    ],
    ("REVIEWING", "EXECUTING"): [
        check_adr_consistency,
        propose_new_adrs,
        validate_dod_completeness,
    ],
    ("EXECUTING", "VALIDATING"): [
        full_dod_check,
        adr_final_check,
        pattern_sweep_summary,
    ],
    ("VALIDATING", "COMPLETE"): [
        final_adr_compliance,
        dod_signoff,
        store_learnings_to_memory,
    ],
}


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def run_gate(current_phase: str, next_phase: str, state: dict, project_path: Path) -> dict:
    """Run all gate checks for a phase transition.

    Returns: {"passed": bool, "blockers": [...], "warnings": [...], "proposed_adrs": [...]}

    If no gate checks defined for the transition, returns passed=True with
    empty lists. Gate checks that fail non-critically add to warnings.
    Critical failures add to blockers.
    """
    transition = (current_phase, next_phase)
    checks = GATE_CHECKS.get(transition)

    if not checks:
        return {
            "passed": True,
            "blockers": [],
            "warnings": [],
            "proposed_adrs": [],
            "transition": f"{current_phase} -> {next_phase}",
            "checks_run": 0,
        }

    all_blockers: List[str] = []
    all_warnings: List[str] = []
    all_proposed_adrs: List[dict] = []
    check_results: List[Dict[str, Any]] = []

    for check_fn in checks:
        fn_name = check_fn.__name__
        try:
            result = check_fn(state, project_path)
        except Exception as exc:
            # Gate check errors are warnings, not blockers (backward compatibility)
            all_warnings.append(f"Gate check '{fn_name}' raised: {exc}")
            check_results.append({"check": fn_name, "error": str(exc)})
            continue

        if not isinstance(result, dict):
            all_warnings.append(f"Gate check '{fn_name}' returned non-dict: {type(result)}")
            continue

        check_results.append({"check": fn_name, **result})

        if not result.get("passed", True):
            all_blockers.extend(result.get("blockers", []))

        all_warnings.extend(result.get("warnings", []))
        all_proposed_adrs.extend(result.get("proposed_adrs", []))

    passed = len(all_blockers) == 0

    return {
        "passed": passed,
        "blockers": all_blockers,
        "warnings": all_warnings,
        "proposed_adrs": all_proposed_adrs,
        "transition": f"{current_phase} -> {next_phase}",
        "checks_run": len(checks),
        "check_results": check_results,
    }
