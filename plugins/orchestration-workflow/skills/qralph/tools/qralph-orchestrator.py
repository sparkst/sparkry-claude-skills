#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
QRALPH Orchestrator v4.1 - Hierarchical team orchestration with sub-team architecture.

This orchestrator MANAGES STATE and DISCOVERS PLUGINS. Claude creates native
teams via TeamCreate, spawns teammates, and coordinates via TaskList/SendMessage.
v4.1 adds hierarchical sub-teams, quality gates, and validation phases.

Commands:
    python3 qralph-orchestrator.py init "<request>" [--mode planning] [--auto|--human] [--fix-level none|p0|p0_p1|all]
    python3 qralph-orchestrator.py discover
    python3 qralph-orchestrator.py select-agents [--agents a,b,c] [--subteam]
    python3 qralph-orchestrator.py synthesize
    python3 qralph-orchestrator.py checkpoint <phase>
    python3 qralph-orchestrator.py generate-uat
    python3 qralph-orchestrator.py finalize
    python3 qralph-orchestrator.py resume <project-id>
    python3 qralph-orchestrator.py status [<project-id>]
    python3 qralph-orchestrator.py heal "<error-details>"
    python3 qralph-orchestrator.py work-plan
    python3 qralph-orchestrator.py work-approve
    python3 qralph-orchestrator.py work-iterate "<feedback>"
    python3 qralph-orchestrator.py escalate
    python3 qralph-orchestrator.py remediate
    python3 qralph-orchestrator.py remediate-done "REM-001,REM-002" [--notes "..."]
    python3 qralph-orchestrator.py remediate-verify
    python3 qralph-orchestrator.py subteam-status --phase <phase>
    python3 qralph-orchestrator.py quality-gate --phase <phase>
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Import shared state module
import importlib.util
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

safe_write = qralph_state.safe_write
safe_write_json = qralph_state.safe_write_json
safe_read_json = qralph_state.safe_read_json

# Import process monitor module
_pm_path = Path(__file__).parent / "process-monitor.py"
_pm_spec = importlib.util.spec_from_file_location("process_monitor", _pm_path)
process_monitor = importlib.util.module_from_spec(_pm_spec)
_pm_spec.loader.exec_module(process_monitor)

# Version
VERSION = "4.1.6"

# Constants
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
PROJECTS_DIR = QRALPH_DIR / "projects"
AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
PLUGINS_DIR = PROJECT_ROOT / ".claude" / "plugins"
NOTIFY_TOOL = Path.home() / ".claude" / "tools" / "notify.py"
VERSION_FILE = QRALPH_DIR / "VERSION"

# Safe project ID pattern (matches session-state.py)
SAFE_PROJECT_ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_\-]{0,99}$')

# Circuit Breaker Limits
MAX_TOKENS = 500_000
MAX_COST_USD = 40.0
MAX_SAME_ERROR = 3
MAX_HEAL_ATTEMPTS = 5

# Fix level priorities: which finding severities to remediate
LEVEL_PRIORITIES = {
    "none": [],
    "p0": ["P0"],
    "p0_p1": ["P0", "P1"],
    "all": ["P0", "P1", "P2"],
}

# Model Pricing (per 1M tokens - input, simplified for estimation)
MODEL_COSTS = {
    "haiku": 0.25,
    "sonnet": 3.0,
    "opus": 15.0,
}

# Domain keywords for request classification
DOMAIN_KEYWORDS = {
    "security": ["security", "auth", "authentication", "authorization", "encrypt",
                  "token", "password", "vulnerability", "owasp", "xss", "injection",
                  "csrf", "cors", "ssl", "tls", "secret", "credential"],
    "frontend": ["ui", "ux", "page", "component", "form", "button", "modal",
                  "dashboard", "layout", "responsive", "mobile", "css", "html",
                  "react", "vue", "angular", "svelte", "tailwind", "design",
                  "dark mode", "theme", "animation", "accessibility", "a11y"],
    "backend": ["api", "endpoint", "server", "database", "query", "migration",
                "rest", "graphql", "webhook", "middleware", "cron", "worker",
                "microservice", "queue", "cache", "redis", "postgres", "sql"],
    "architecture": ["architecture", "system design", "scalability", "pattern",
                     "refactor", "restructure", "monolith", "modular", "dependency",
                     "interface", "contract", "coupling", "cohesion"],
    "testing": ["test", "qa", "validation", "coverage", "e2e", "unit test",
                "integration test", "mock", "fixture", "assertion", "regression"],
    "devops": ["deploy", "ci", "cd", "pipeline", "docker", "kubernetes",
               "terraform", "infrastructure", "monitoring", "logging", "release"],
    "content": ["write", "article", "blog", "content", "copy", "documentation",
                "readme", "guide", "tutorial", "newsletter", "post"],
    "research": ["research", "analyze", "compare", "investigate", "evaluate",
                 "benchmark", "survey", "study", "report", "assessment"],
    "strategy": ["strategy", "plan", "roadmap", "business", "market", "pricing",
                 "growth", "acquisition", "retention", "monetization", "roi"],
    "data": ["data", "analytics", "metrics", "dashboard", "chart", "visualization",
             "etl", "pipeline", "warehouse", "reporting", "tracking"],
    "performance": ["performance", "optimize", "speed", "latency", "throughput",
                    "memory", "cpu", "profiling", "bottleneck", "benchmark"],
    "compliance": ["compliance", "gdpr", "ccpa", "hipaa", "sox", "regulation",
                   "privacy", "consent", "audit", "legal", "license"],
}

# Agent capabilities registry - maps agent types to their domains and model tiers
AGENT_REGISTRY = {
    # Core development agents
    "security-reviewer": {"domains": ["security", "compliance"], "model": "sonnet", "category": "security"},
    "architecture-advisor": {"domains": ["architecture", "backend", "performance"], "model": "sonnet", "category": "architecture"},
    "sde-iii": {"domains": ["backend", "architecture", "testing"], "model": "sonnet", "category": "implementation"},
    "requirements-analyst": {"domains": ["strategy", "architecture"], "model": "sonnet", "category": "planning"},
    "ux-designer": {"domains": ["frontend", "data"], "model": "sonnet", "category": "design"},
    "code-quality-auditor": {"domains": ["testing", "architecture"], "model": "haiku", "category": "quality"},
    "pe-reviewer": {"domains": ["architecture", "security", "performance"], "model": "sonnet", "category": "quality"},
    "pe-designer": {"domains": ["architecture", "backend"], "model": "sonnet", "category": "architecture"},
    "test-writer": {"domains": ["testing"], "model": "sonnet", "category": "testing"},
    "debugger": {"domains": ["backend", "testing", "performance"], "model": "sonnet", "category": "implementation"},
    "perf-optimizer": {"domains": ["performance", "backend"], "model": "sonnet", "category": "performance"},
    "integration-specialist": {"domains": ["backend", "devops", "architecture"], "model": "sonnet", "category": "integration"},
    "api-schema": {"domains": ["backend", "architecture"], "model": "haiku", "category": "api"},
    "migration-refactorer": {"domains": ["architecture", "backend"], "model": "sonnet", "category": "implementation"},
    "validation-specialist": {"domains": ["testing", "quality"], "model": "sonnet", "category": "testing"},
    "ux-tester": {"domains": ["frontend", "testing"], "model": "sonnet", "category": "testing"},
    # Planning & strategy agents
    "pm": {"domains": ["strategy", "research"], "model": "sonnet", "category": "planning"},
    "strategic-advisor": {"domains": ["strategy", "research"], "model": "sonnet", "category": "strategy"},
    "finance-consultant": {"domains": ["strategy", "data"], "model": "haiku", "category": "strategy"},
    "legal-expert": {"domains": ["compliance", "strategy"], "model": "sonnet", "category": "compliance"},
    "cos": {"domains": ["strategy"], "model": "opus", "category": "strategy"},
    # Research agents
    "research-director": {"domains": ["research"], "model": "sonnet", "category": "research"},
    "fact-checker": {"domains": ["research", "content"], "model": "haiku", "category": "research"},
    "source-evaluator": {"domains": ["research"], "model": "haiku", "category": "research"},
    "industry-signal-scout": {"domains": ["research", "strategy"], "model": "sonnet", "category": "research"},
    "dissent-moderator": {"domains": ["research", "strategy"], "model": "opus", "category": "research"},
    # Content agents
    "synthesis-writer": {"domains": ["content", "research"], "model": "opus", "category": "content"},
    "docs-writer": {"domains": ["content"], "model": "haiku", "category": "content"},
    # Operations agents
    "release-manager": {"domains": ["devops"], "model": "haiku", "category": "devops"},
}

# Skill capabilities - maps skill names to their domains
SKILL_REGISTRY = {
    "frontend-design": {"domains": ["frontend"], "description": "Create distinctive frontend interfaces"},
    "writing": {"domains": ["content"], "description": "Multi-agent writing system"},
    "feature-dev": {"domains": ["backend", "architecture", "testing"], "description": "Guided feature development"},
    "code-review": {"domains": ["security", "quality", "architecture"], "description": "Code review"},
    "pr-review-toolkit": {"domains": ["security", "quality", "testing"], "description": "PR review agents"},
    "research-workflow": {"domains": ["research"], "description": "Research specialist agents"},
    "orchestration-workflow": {"domains": ["architecture"], "description": "Multi-agent orchestration"},
}


def sweep_orphaned_processes() -> Optional[dict]:
    """Run process monitor sweep to clean up orphaned processes from previous runs.

    Returns sweep results dict, or None if sweep fails/unavailable.
    """
    try:
        result = process_monitor.cmd_sweep(dry_run=False)
        killed = result.get("killed", 0)
        if killed > 0:
            print(f"Process sweep: cleaned up {killed} orphaned process(es)", file=sys.stderr)
        return result
    except Exception as e:
        print(f"Warning: Process sweep failed: {e}", file=sys.stderr)
        return None


def get_state_file() -> Path:
    """Return the path to the global QRALPH state file."""
    return QRALPH_DIR / "current-project.json"


def load_state() -> dict:
    """Load the current QRALPH project state with locking and checksum validation."""
    return qralph_state.load_state(get_state_file())


def save_state(state: dict):
    """Persist project state atomically with locking and checksum injection."""
    qralph_state.save_state(state, get_state_file())


def save_state_and_checkpoint(state: dict):
    """Save state to both current-project.json AND checkpoints/state.json.

    Use this instead of bare save_state() when advancing phases, to prevent
    checkpoint divergence where current-project.json and checkpoints/state.json
    get out of sync.
    """
    save_state(state)
    project_path = Path(state.get("project_path", ""))
    if project_path.exists():
        checkpoint_file = project_path / "checkpoints" / "state.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        safe_write_json(checkpoint_file, state)


def sanitize_request(request: str) -> str:
    """Sanitize request string: strip null bytes, path traversal, and markdown injection."""
    if not request or not isinstance(request, str):
        return ""
    sanitized = request.replace('\x00', '')
    # Loop until stable to prevent bypass via nested sequences like "....//"
    prev = None
    while prev != sanitized:
        prev = sanitized
        sanitized = re.sub(r'\.\.[/\\]', '', sanitized)
    # Escape markdown heading/link injection characters at line starts
    sanitized = re.sub(r'^(#{1,6}\s)', r'\\\1', sanitized, flags=re.MULTILINE)
    sanitized = sanitized.replace('[', '\\[').replace(']', '\\]')
    return sanitized[:2000].strip()


def validate_request(request: str) -> bool:
    """Check that request is a non-empty string with at least 3 characters."""
    if not request or not isinstance(request, str):
        return False
    return len(request.strip()) >= 3


def _error_result(message: str) -> dict:
    """Create and print a consistent error result dict."""
    result = {"status": "error", "error": message}
    print(json.dumps(result))
    return result


def validate_phase_transition(current_phase: str, next_phase: str, mode: str = "coding") -> bool:
    """Validate that a phase transition is allowed for the given mode."""
    coding_transitions = {
        "INIT": ["DISCOVERING", "REVIEWING"],
        "DISCOVERING": ["REVIEWING"],
        "REVIEWING": ["EXECUTING", "VALIDATING", "COMPLETE"],
        "EXECUTING": ["UAT", "VALIDATING", "COMPLETE"],
        "VALIDATING": ["COMPLETE", "EXECUTING"],
        "UAT": ["COMPLETE"],
        "COMPLETE": [],
    }
    work_transitions = {
        "INIT": ["DISCOVERING"],
        "DISCOVERING": ["PLANNING"],
        "PLANNING": ["USER_REVIEW"],
        "USER_REVIEW": ["EXECUTING", "PLANNING"],
        "EXECUTING": ["COMPLETE", "ESCALATE"],
        "ESCALATE": ["REVIEWING"],
        "REVIEWING": ["EXECUTING", "COMPLETE"],
        "COMPLETE": [],
    }
    transitions = work_transitions if mode == "work" else coding_transitions
    return next_phase in transitions.get(current_phase, [])


def generate_slug(request: str) -> str:
    """Generate a URL-safe project slug from the first 3 content words of a request."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', request.lower())
    stop_words = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into'}
    slug_words = [w for w in words if w not in stop_words][:3]
    return "-".join(slug_words)[:30] or "project"


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token."""
    return len(text) // 4


def estimate_cost(tokens: int, model: str) -> float:
    """Estimate USD cost for a given token count and model tier."""
    cost_per_million = MODEL_COSTS.get(model, MODEL_COSTS["sonnet"])
    return (tokens / 1_000_000) * cost_per_million


def check_circuit_breakers(state: dict) -> Optional[str]:
    """Return an error message if any circuit breaker is tripped, else None.

    Note: Callers must hold exclusive_state_lock() to avoid TOCTOU races
    between checking breakers and updating state.
    """
    if not qralph_state.is_exclusive_lock_held():
        print("Warning: check_circuit_breakers called without exclusive_state_lock()",
              file=sys.stderr)
    breakers = state.get("circuit_breakers", {})
    total_tokens = breakers.get("total_tokens", 0)
    if total_tokens > MAX_TOKENS:
        return f"Circuit breaker: Token limit exceeded ({total_tokens:,} > {MAX_TOKENS:,})"
    total_cost = breakers.get("total_cost_usd", 0.0)
    if total_cost > MAX_COST_USD:
        return f"Circuit breaker: Cost limit exceeded (${total_cost:.2f} > ${MAX_COST_USD:.2f})"
    error_counts = breakers.get("error_counts", {})
    for error, count in error_counts.items():
        if count >= MAX_SAME_ERROR:
            return f"Circuit breaker: Same error occurred {count} times: {error[:100]}"
    heal_attempts = state.get("heal_attempts", 0)
    if heal_attempts >= MAX_HEAL_ATTEMPTS:
        return f"Circuit breaker: Max heal attempts exceeded ({heal_attempts} >= {MAX_HEAL_ATTEMPTS})"
    return None


def update_circuit_breakers(state: dict, tokens: int = 0, model: str = "sonnet", error: str = None):
    """Accumulate token/cost usage and error counts in the circuit breaker state."""
    if "circuit_breakers" not in state:
        state["circuit_breakers"] = {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}}
    breakers = state["circuit_breakers"]
    breakers["total_tokens"] += tokens
    breakers["total_cost_usd"] += estimate_cost(tokens, model)
    if error:
        error_key = error[:100]
        breakers["error_counts"][error_key] = breakers["error_counts"].get(error_key, 0) + 1
        # Cap error_counts to prevent unbounded memory growth
        if len(breakers["error_counts"]) > 100:
            least_frequent = min(breakers["error_counts"], key=breakers["error_counts"].get)
            del breakers["error_counts"][least_frequent]


def check_control_commands(project_path: Path) -> Optional[str]:
    """Read CONTROL.md and return the first recognized command, or None.

    Only lines that contain ONLY a recognized command (ignoring whitespace)
    are treated as active commands.  Template/help text is ignored.
    """
    control_file = project_path / "CONTROL.md"
    if not control_file.exists():
        return None
    try:
        for line in control_file.read_text().splitlines():
            stripped = line.strip().upper()
            if stripped in ("PAUSE", "SKIP", "ABORT", "STATUS", "ESCALATE"):
                return stripped
    except (OSError, UnicodeDecodeError):
        pass
    return None


# ─── PLUGIN & SKILL DISCOVERY ───────────────────────────────────────────────

def classify_domains(request: str) -> List[str]:
    """Classify which domains a request touches."""
    request_lower = request.lower()
    domain_scores: Dict[str, int] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in request_lower)
        if score > 0:
            domain_scores[domain] = score

    # Sort by score descending, return domain names
    ranked = sorted(domain_scores.items(), key=lambda x: -x[1])
    return [d for d, _ in ranked]


def estimate_complexity(request: str, domains: List[str]) -> int:
    """Estimate request complexity to determine agent count (3-7)."""
    score = 0

    # More domains = more complex
    score += len(domains)

    # Longer request = likely more complex
    word_count = len(request.split())
    if word_count > 30:
        score += 2
    elif word_count > 15:
        score += 1

    # Certain keywords signal complexity
    complex_signals = ["and", "with", "also", "integrate", "migrate", "refactor",
                       "redesign", "overhaul", "comprehensive", "full-stack", "end-to-end"]
    score += sum(1 for s in complex_signals if s in request.lower())

    # Map score to agent count: 3-7
    if score <= 2:
        return 3
    elif score <= 4:
        return 4
    elif score <= 6:
        return 5
    elif score <= 8:
        return 6
    else:
        return 7


def estimate_work_complexity(request: str, domains: List[str]) -> int:
    """Estimate agent count for work mode (1-3, lighter than coding's 3-7)."""
    score = len(domains)
    word_count = len(request.split())
    if word_count > 100:
        score += 2
    elif word_count > 50:
        score += 1
    return min(max(score // 2, 1), 3)


# Skill discovery keyword mapping
WORK_SKILL_KEYWORDS = {
    "write": ["writing"],
    "research": ["research-workflow"],
    "automate": [],
    "scan": [],
    "feedback": ["qshortcuts-learning"],
    "presentation": [],
    "document": ["writing-workflow"],
    "proposal": ["writing-workflow"],
    "analyze": ["research-workflow"],
    "review": ["pr-review-toolkit"],
    "plan": [],
}

# Code signals that trigger TDD mandate in work mode
CODE_SIGNAL_KEYWORDS = {"script", "function", "api", "automate", "deploy", "build",
                        "implement", "refactor", "code", "test", "endpoint", "database",
                        "migration", "pipeline", "server", "cli"}


def contains_code_signals(request: str) -> bool:
    """Detect if a work-mode request contains code-related signals."""
    words = set(re.findall(r'\b\w+\b', request.lower()))
    return bool(words & CODE_SIGNAL_KEYWORDS)


def detect_test_infrastructure() -> Dict[str, Any]:
    """Detect the project's test infrastructure by scanning config files.

    Returns a dict with detected test/lint/typecheck commands and framework info.
    This makes QRALPH self-contained — it doesn't rely on CLAUDE.md for TDD knowledge.
    """
    infra: Dict[str, Any] = {
        "test_cmd": None,
        "lint_cmd": None,
        "typecheck_cmd": None,
        "framework": None,
        "quality_gate_cmd": None,
        "detected_from": None,
    }

    # 1. Check package.json (Node/JS/TS projects)
    pkg_json = PROJECT_ROOT / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            infra["detected_from"] = "package.json"

            if "test" in scripts:
                infra["test_cmd"] = "npm run test"
                # Detect framework from test script content
                test_script = scripts["test"]
                for fw in ("vitest", "jest", "mocha", "ava", "tap"):
                    if fw in test_script:
                        infra["framework"] = fw
                        break
            if "lint" in scripts:
                infra["lint_cmd"] = "npm run lint"
            if "typecheck" in scripts:
                infra["typecheck_cmd"] = "npm run typecheck"
            elif "type-check" in scripts:
                infra["typecheck_cmd"] = "npm run type-check"
            elif "tsc" in scripts:
                infra["typecheck_cmd"] = "npm run tsc"

            # Build composite quality gate command
            gates = [cmd for cmd in [infra["typecheck_cmd"], infra["lint_cmd"], infra["test_cmd"]] if cmd]
            if gates:
                infra["quality_gate_cmd"] = " && ".join(gates)
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Check for Python projects (pyproject.toml, setup.py, pytest.ini)
    if not infra["test_cmd"]:
        for marker in ("pyproject.toml", "setup.py", "setup.cfg", "pytest.ini"):
            if (PROJECT_ROOT / marker).exists():
                infra["detected_from"] = marker
                infra["test_cmd"] = "python -m pytest"
                infra["framework"] = "pytest"
                # Check for ruff/flake8/mypy
                if (PROJECT_ROOT / "pyproject.toml").exists():
                    try:
                        toml_text = (PROJECT_ROOT / "pyproject.toml").read_text()
                        if "ruff" in toml_text:
                            infra["lint_cmd"] = "ruff check ."
                        if "mypy" in toml_text:
                            infra["typecheck_cmd"] = "mypy ."
                    except OSError:
                        pass
                gates = [cmd for cmd in [infra["typecheck_cmd"], infra["lint_cmd"], infra["test_cmd"]] if cmd]
                if gates:
                    infra["quality_gate_cmd"] = " && ".join(gates)
                break

    # 3. Check for Rust projects
    if not infra["test_cmd"] and (PROJECT_ROOT / "Cargo.toml").exists():
        infra["detected_from"] = "Cargo.toml"
        infra["test_cmd"] = "cargo test"
        infra["framework"] = "cargo"
        infra["lint_cmd"] = "cargo clippy"
        infra["quality_gate_cmd"] = "cargo clippy && cargo test"

    # 4. Check for Go projects
    if not infra["test_cmd"] and (PROJECT_ROOT / "go.mod").exists():
        infra["detected_from"] = "go.mod"
        infra["test_cmd"] = "go test ./..."
        infra["framework"] = "go"
        infra["lint_cmd"] = "golangci-lint run"
        infra["quality_gate_cmd"] = "go test ./..."

    # 5. Check for Makefile with test target
    if not infra["test_cmd"]:
        makefile = PROJECT_ROOT / "Makefile"
        if makefile.exists():
            try:
                content = makefile.read_text()
                if re.search(r'^test:', content, re.MULTILINE):
                    infra["detected_from"] = "Makefile"
                    infra["test_cmd"] = "make test"
                    infra["quality_gate_cmd"] = "make test"
            except OSError:
                pass

    return infra


def discover_work_skills(request: str) -> List[str]:
    """Discover relevant skills for a work-mode request."""
    lower = request.lower()
    skills = []
    for keyword, mapped_skills in WORK_SKILL_KEYWORDS.items():
        if keyword in lower:
            skills.extend(mapped_skills)
    return list(set(skills))


def should_escalate_to_coding(state: dict) -> bool:
    """Check if a work-mode project should escalate to full coding mode."""
    domains = state.get("domains", [])
    if len(domains) > 3:
        return True
    heal_attempts = state.get("heal_attempts", 0)
    if heal_attempts >= 3:
        return True
    findings = state.get("findings", [])
    p0_count = sum(1 for f in findings if f.get("priority") == "P0")
    if p0_count > 0:
        return True
    return False


def discover_local_agents() -> List[Dict[str, Any]]:
    """Discover custom agents from .claude/agents/ directory."""
    agents = []
    if not AGENTS_DIR.exists():
        return agents

    for agent_file in sorted(AGENTS_DIR.glob("*.md")):
        agent_name = agent_file.stem
        # Skip planner sub-types for discovery (they're specialized)
        if agent_name.startswith("planner."):
            continue

        agents.append({
            "name": agent_name,
            "source": "local_agent",
            "file": str(agent_file),
        })

    return agents


def discover_plugins() -> List[Dict[str, Any]]:
    """Discover installed plugins from .claude/plugins/ directory."""
    plugins = []
    if not PLUGINS_DIR.exists():
        return plugins

    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue

        # Look for plugin.json in standard locations
        for json_path in [
            plugin_dir / "plugin.json",
            plugin_dir / ".claude-plugin" / "plugin.json",
        ]:
            if json_path.exists():
                try:
                    config = json.loads(json_path.read_text())
                    plugins.append({
                        "name": config.get("name", plugin_dir.name),
                        "version": config.get("version", "unknown"),
                        "description": config.get("description", ""),
                        "source": "plugin",
                        "path": str(plugin_dir),
                    })
                except (json.JSONDecodeError, KeyError):
                    plugins.append({
                        "name": plugin_dir.name,
                        "source": "plugin",
                        "path": str(plugin_dir),
                    })
                break

    return plugins


def score_capability(capability: Dict[str, Any], domains: List[str], request: str) -> float:
    """Score a capability's relevance to the request (0.0 - 1.0)."""
    score = 0.0
    cap_name = capability.get("name", "")
    cap_domains = capability.get("domains", [])
    cap_description = capability.get("description", "")

    # Domain overlap (primary signal)
    if cap_domains and domains:
        overlap = len(set(cap_domains) & set(domains))
        score += (overlap / max(len(domains), 1)) * 0.6

    # Name keyword match
    request_lower = request.lower()
    name_words = cap_name.replace("-", " ").replace("_", " ").lower().split()
    name_matches = sum(1 for w in name_words if w in request_lower)
    if name_words:
        score += (name_matches / len(name_words)) * 0.25

    # Description keyword match
    if cap_description:
        desc_words = cap_description.lower().split()
        desc_matches = sum(1 for w in desc_words if w in request_lower)
        if desc_words:
            score += (desc_matches / len(desc_words)) * 0.15

    return min(score, 1.0)


def cmd_discover():
    """Discover available plugins, skills, and agents."""
    with qralph_state.exclusive_state_lock():
        return _cmd_discover_locked()


def _cmd_discover_locked():
    """Inner discover logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project. Run init first.")

    project_path = Path(state["project_path"])
    request = state["request"]
    domains = classify_domains(request)

    # Discover all capabilities
    local_agents = discover_local_agents()
    plugins = discover_plugins()

    # Build unified capability list from agent registry
    all_capabilities = []

    for agent_name, agent_info in AGENT_REGISTRY.items():
        all_capabilities.append({
            "name": agent_name,
            "type": "agent",
            "source": "builtin",
            "domains": agent_info["domains"],
            "model": agent_info["model"],
            "category": agent_info["category"],
        })

    # Add skills
    for skill_name, skill_info in SKILL_REGISTRY.items():
        all_capabilities.append({
            "name": skill_name,
            "type": "skill",
            "source": "builtin",
            "domains": skill_info["domains"],
            "description": skill_info["description"],
        })

    # Add local agents (with domain inference from name)
    for agent in local_agents:
        name = agent["name"]
        # Check if already in registry
        if name in AGENT_REGISTRY:
            continue
        # Infer domains from agent name
        inferred_domains = []
        for domain, keywords in DOMAIN_KEYWORDS.items():
            name_lower = name.replace("-", " ").lower()
            if any(kw in name_lower for kw in keywords):
                inferred_domains.append(domain)
        all_capabilities.append({
            "name": name,
            "type": "agent",
            "source": "local",
            "domains": inferred_domains,
            "file": agent["file"],
        })

    # Add discovered plugins
    for plugin in plugins:
        all_capabilities.append({
            "name": plugin["name"],
            "type": "plugin",
            "source": "installed",
            "domains": [],
            "description": plugin.get("description", ""),
            "path": plugin.get("path", ""),
        })

    # Score all capabilities against request
    scored = []
    for cap in all_capabilities:
        relevance = score_capability(cap, domains, request)
        cap["relevance_score"] = round(relevance, 3)
        scored.append(cap)

    # Sort by relevance
    scored.sort(key=lambda x: -x["relevance_score"])

    # Save discovery results
    discovery_result = {
        "request": request,
        "domains_detected": domains,
        "total_capabilities": len(scored),
        "relevant_capabilities": [c for c in scored if c["relevance_score"] >= 0.1],
        "discovered_at": datetime.now().isoformat(),
    }

    safe_write_json(project_path / "discovered-plugins.json", discovery_result)

    # Detect test infrastructure (makes QRALPH self-contained for TDD)
    test_infra = detect_test_infrastructure()

    # Update state
    state["phase"] = "DISCOVERING"
    state["domains"] = domains
    state["discovery"] = {
        "total": len(scored),
        "relevant": len(discovery_result["relevant_capabilities"]),
    }
    state["test_infrastructure"] = test_infra
    save_state(state)

    infra_summary = f"test_infra={test_infra['framework'] or 'none'}"
    if test_infra["quality_gate_cmd"]:
        infra_summary += f", gate={test_infra['quality_gate_cmd']}"

    log_decision(project_path, f"Discovery: {len(domains)} domains, {len(discovery_result['relevant_capabilities'])} relevant capabilities, {infra_summary}")

    # Output for Claude
    output = {
        "status": "discovered",
        "project_id": state["project_id"],
        "domains_detected": domains,
        "relevant_count": len(discovery_result["relevant_capabilities"]),
        "top_capabilities": [
            {"name": c["name"], "type": c["type"], "relevance": c["relevance_score"]}
            for c in scored[:15]
        ],
        "recommended_skills": [
            c["name"] for c in scored
            if c["type"] == "skill" and c["relevance_score"] >= 0.2
        ],
        "test_infrastructure": test_infra,
        "next_step": "Run select-agents to pick the best team composition",
    }
    print(json.dumps(output, indent=2))
    return output


# ─── PROJECT INITIALIZATION ─────────────────────────────────────────────────

def check_version_update(state: dict) -> Optional[str]:
    """Compare VERSION against state's last_seen_version. Return announcement if changed."""
    last_seen = state.get("last_seen_version", "")
    if last_seen != VERSION:
        state["last_seen_version"] = VERSION
        return f"QRALPH updated to v{VERSION} — see CHANGELOG.md for changes."
    return None


def cmd_init(request: str, mode: str = "coding", execution_mode: str = "human", fix_level: str = "p0_p1"):
    """Initialize a new QRALPH project: create directory, state, and STATE.md."""
    # Sweep orphaned processes from any previous run before starting fresh
    sweep_orphaned_processes()

    request = sanitize_request(request)
    if not validate_request(request):
        return _error_result("Invalid request: must be non-empty string with at least 3 characters")

    if fix_level not in LEVEL_PRIORITIES:
        return _error_result(f"Invalid fix_level: {fix_level}. Must be one of: {', '.join(LEVEL_PRIORITIES.keys())}")

    with qralph_state.exclusive_state_lock():
        return _cmd_init_locked(request, mode, execution_mode, fix_level)


def _cmd_init_locked(request: str, mode: str = "coding", execution_mode: str = "human", fix_level: str = "p0_p1"):
    """Inner init logic, called under exclusive lock."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Get next project number
    existing = list(PROJECTS_DIR.glob("[0-9][0-9][0-9]-*"))
    next_num = max([int(p.name[:3]) for p in existing], default=0) + 1

    slug = generate_slug(request)
    project_id = f"{next_num:03d}-{slug}"
    project_path = PROJECTS_DIR / project_id

    # Create directory structure
    (project_path / "agent-outputs").mkdir(parents=True)
    (project_path / "checkpoints").mkdir(parents=True)
    (project_path / "healing-attempts").mkdir(parents=True)
    (project_path / "phase-outputs").mkdir(parents=True)

    # Create initial files
    try:
        safe_write(project_path / "CONTROL.md",
            "# QRALPH Control\n\n"
            "To issue a command, write it alone on a line (e.g. just `PAUSE`).\n\n"
            "Available commands:\n"
            "- `PAUSE` — stop after current step\n"
            "- `SKIP` — skip current operation\n"
            "- `ABORT` — graceful shutdown\n"
            "- `STATUS` — force status dump\n"
        )

        safe_write(project_path / "decisions.log",
            f"[{datetime.now().strftime('%H:%M:%S')}] Project initialized: {project_id}\n"
            f"[{datetime.now().strftime('%H:%M:%S')}] Request: {request}\n"
            f"[{datetime.now().strftime('%H:%M:%S')}] Mode: {mode}\n"
        )
    except Exception as e:
        print(f"Warning: Error creating project files: {e}", file=sys.stderr)

    state = {
        "project_id": project_id,
        "project_path": str(project_path),
        "request": request,
        "mode": mode,
        "phase": "INIT",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "team_name": f"qralph-{project_id}",
        "teammates": [],
        "skills_for_agents": {},
        "domains": [],
        "findings": [],
        "heal_attempts": 0,
        "circuit_breakers": {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "error_counts": {},
        },
        "execution_mode": execution_mode,
        "fix_level": fix_level,
        "sub_teams": {},
        "last_seen_version": VERSION,
    }
    save_state(state)
    safe_write_json(project_path / "checkpoints" / "state.json", state)

    # Check for version update announcement
    version_update = None
    # On init, we just set last_seen_version, so no announcement needed

    output = {
        "status": "initialized",
        "project_id": project_id,
        "project_path": str(project_path),
        "team_name": state["team_name"],
        "mode": mode,
        "execution_mode": execution_mode,
        "next_step": "Run discover to scan available plugins and skills, then select-agents",
    }
    print(json.dumps(output, indent=2))
    return output


# ─── AGENT SELECTION ─────────────────────────────────────────────────────────

def cmd_select_agents(custom_agents: Optional[list] = None, use_subteam: bool = False):
    """Select best agents based on discovery results and request analysis."""
    with qralph_state.exclusive_state_lock():
        return _cmd_select_agents_locked(custom_agents, use_subteam)


def _cmd_select_agents_locked(custom_agents: Optional[list] = None, use_subteam: bool = False):
    """Inner select-agents logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project. Run init first.")

    project_path = Path(state["project_path"])

    # Check control/circuit
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        return _error_result(breaker_error)

    request = state["request"]
    domains = state.get("domains") or classify_domains(request)

    # Load discovery results if available
    discovery_file = project_path / "discovered-plugins.json"
    discovery = safe_read_json(discovery_file, {})

    if custom_agents:
        # User specified agents
        agents = []
        for a in custom_agents[:7]:
            info = AGENT_REGISTRY.get(a, {"model": "sonnet", "category": "custom", "domains": []})
            agents.append({
                "agent_type": a,
                "model": info.get("model", "sonnet"),
                "category": info.get("category", "custom"),
                "domains": info.get("domains", []),
            })
    else:
        # Dynamic selection based on discovery
        target_count = estimate_complexity(request, domains)

        # Score and rank agents
        candidates = []
        for agent_name, agent_info in AGENT_REGISTRY.items():
            cap = {"name": agent_name, "domains": agent_info["domains"]}
            relevance = score_capability(cap, domains, request)
            candidates.append({
                "agent_type": agent_name,
                "model": agent_info["model"],
                "category": agent_info["category"],
                "domains": agent_info["domains"],
                "relevance": relevance,
            })

        # Sort by relevance
        candidates.sort(key=lambda x: -x["relevance"])

        # Select with diversity constraint (max 2 per category)
        agents = []
        category_counts: Dict[str, int] = {}
        for c in candidates:
            if c["relevance"] < 0.1:
                break
            cat = c["category"]
            if category_counts.get(cat, 0) < 2:
                agents.append(c)
                category_counts[cat] = category_counts.get(cat, 0) + 1
            if len(agents) >= target_count:
                break

        # Ensure minimum of 3 - fill from top candidates if needed
        if len(agents) < 3:
            for c in candidates:
                if c not in agents:
                    agents.append(c)
                if len(agents) >= 3:
                    break

    # Determine which skills are relevant for each agent
    skills_for_agents: Dict[str, List[str]] = {}
    relevant_skills = discovery.get("recommended_skills", []) if discovery else []
    if not relevant_skills:
        # Fallback: check SKILL_REGISTRY
        for skill_name, skill_info in SKILL_REGISTRY.items():
            skill_cap = {"name": skill_name, "domains": skill_info["domains"],
                         "description": skill_info["description"]}
            if score_capability(skill_cap, domains, request) >= 0.2:
                relevant_skills.append(skill_name)

    for agent in agents:
        agent_domains = set(agent.get("domains", []))
        matching_skills = []
        for skill_name in relevant_skills:
            skill_info = SKILL_REGISTRY.get(skill_name, {})
            skill_domains = set(skill_info.get("domains", []))
            if agent_domains & skill_domains:
                matching_skills.append(skill_name)
        if matching_skills:
            skills_for_agents[agent["agent_type"]] = matching_skills

    # Generate agent configs with prompts
    agent_configs = []
    for agent in agents:
        agent_type = agent["agent_type"]
        agent_skills = skills_for_agents.get(agent_type, [])

        prompt = generate_team_agent_prompt(
            agent_type=agent_type,
            request=request,
            project_id=state["project_id"],
            project_path=project_path,
            team_name=state["team_name"],
            available_skills=agent_skills,
        )

        tokens = estimate_tokens(prompt)

        agent_configs.append({
            "agent_type": agent_type,
            "model": agent["model"],
            "category": agent.get("category", "general"),
            "name": f"{agent_type}-agent",
            "team_name": state["team_name"],
            "description": f"{agent_type.replace('-', ' ').title()} review",
            "prompt": prompt,
            "output_file": str(project_path / "agent-outputs" / f"{agent_type}.md"),
            "skills": agent_skills,
            "relevance": round(agent.get("relevance", 0), 3),
        })

    # Update state
    state["agents"] = [a["agent_type"] for a in agent_configs]
    state["teammates"] = [a["name"] for a in agent_configs]
    state["skills_for_agents"] = skills_for_agents
    state["phase"] = "REVIEWING"
    save_state_and_checkpoint(state)

    # Save team config
    team_config = {
        "team_name": state["team_name"],
        "project_id": state["project_id"],
        "agents": agent_configs,
        "skills_for_agents": skills_for_agents,
        "domains": domains,
        "created_at": datetime.now().isoformat(),
    }
    safe_write_json(project_path / "team-config.json", team_config)

    log_decision(project_path,
        f"Team composed: {len(agent_configs)} agents [{', '.join(state['agents'])}], "
        f"skills: {skills_for_agents or 'none'}"
    )

    if use_subteam:
        instruction = (
            "1. Run: python3 .qralph/tools/qralph-subteam.py create-subteam --phase REVIEWING\n"
            "2. Follow sub-team creation instructions from output\n"
            "3. Monitor: python3 .qralph/tools/qralph-subteam.py check-subteam --phase REVIEWING\n"
            "4. Quality gate: python3 .qralph/tools/qralph-subteam.py quality-gate --phase REVIEWING\n"
            "5. Collect: python3 .qralph/tools/qralph-subteam.py collect-results --phase REVIEWING\n"
            "6. Then run synthesize"
        )
    else:
        instruction = (
            "1. TeamCreate(team_name='" + state["team_name"] + "')\n"
            "2. TaskCreate for each agent's review task\n"
            "3. Spawn teammates via Task(subagent_type='general-purpose', team_name=..., name=...)\n"
            "   IMPORTANT: Always use subagent_type='general-purpose' — specialized types may lack the Write tool.\n"
            "4. Monitor via TaskList + receive SendMessage from teammates\n"
            "5. When all complete, run synthesize"
        )

    output = {
        "status": "agents_selected",
        "project_id": state["project_id"],
        "team_name": state["team_name"],
        "agent_count": len(agent_configs),
        "agents": agent_configs,
        "skills_for_agents": skills_for_agents,
        "use_subteam": use_subteam,
        "instruction": instruction,
    }
    print(json.dumps(output, indent=2))
    return output


def compute_evidence_quality_score(agents: List[str], outputs_dir: Path) -> Dict[str, Any]:
    """Compute Evidence Quality Score (EQS) for a synthesis run.

    Returns dict with eqs (0-100), agents_with_output, total_words,
    confidence level, and per-agent status.
    """
    total_agents = len(agents) if agents else 1
    agents_with_output = 0
    total_words = 0
    has_findings = False
    agent_status = {}

    for agent in agents:
        output_file = outputs_dir / f"{agent}.md"
        if output_file.exists():
            content = output_file.read_text()
            size = len(content)
            words = len(content.split())
            has_receipt = "QRALPH-RECEIPT" in content
            if size >= 50:
                agents_with_output += 1
                total_words += words
                if any(p in content for p in ["P0", "P1", "P2"]):
                    has_findings = True
                agent_status[agent] = {"status": "present", "words": words, "receipt": has_receipt}
            else:
                agent_status[agent] = {"status": "empty", "words": words, "receipt": False}
        else:
            agent_status[agent] = {"status": "missing", "words": 0, "receipt": False}

    # EQS = (agents_with_output / total) * 60 + (avg_words / 300) * 30 + findings_bonus * 10
    coverage_score = (agents_with_output / total_agents) * 60
    avg_words = total_words / max(agents_with_output, 1)
    depth_score = min((avg_words / 300) * 30, 30)
    findings_bonus = 10 if has_findings else 0
    eqs = round(min(coverage_score + depth_score + findings_bonus, 100))

    if eqs >= 80:
        confidence = "HIGH"
    elif eqs >= 50:
        confidence = "MEDIUM"
    elif eqs >= 20:
        confidence = "LOW"
    else:
        confidence = "HOLLOW RUN"

    return {
        "eqs": eqs,
        "agents_with_output": agents_with_output,
        "total_agents": total_agents,
        "total_words": total_words,
        "confidence": confidence,
        "agent_status": agent_status,
    }


def generate_team_agent_prompt(
    agent_type: str,
    request: str,
    project_id: str,
    project_path: Path,
    team_name: str,
    available_skills: List[str],
) -> str:
    """Generate a prompt for a team-based agent."""
    agent_context = {
        "security-reviewer": "Authentication/authorization, input validation, sensitive data, injection, OWASP Top 10",
        "architecture-advisor": "System design patterns, scalability, technical debt, dependencies, interface contracts",
        "code-quality-auditor": "Code style, error handling, test coverage, documentation, CLAUDE.md compliance",
        "requirements-analyst": "Requirement clarity, acceptance criteria, edge cases, dependencies, story points",
        "ux-designer": "User flows, accessibility, error states, loading states, mobile responsiveness",
        "sde-iii": "Implementation complexity, performance, integration points, testing strategy, deployment",
        "pm": "Market fit, user value, prioritization, success metrics, stakeholder impact",
        "synthesis-writer": "Content clarity, voice consistency, structure, audience alignment",
        "pe-reviewer": "Architecture patterns, security, performance, code quality enforcement",
        "pe-designer": "System architecture, scalability patterns, technical feasibility",
        "test-writer": "Test strategy, coverage, edge cases, TDD approach",
        "strategic-advisor": "Market positioning, competitive landscape, growth strategy",
        "research-director": "Research methodology, source evaluation, evidence synthesis",
        "fact-checker": "Claim verification, source independence, evidence quality",
        "validation-specialist": "Functional verification, UI validation, integration testing",
        "debugger": "Root cause analysis, minimal reproduction, targeted fixes",
        "perf-optimizer": "Hot paths, bottlenecks, measurable optimizations",
        "integration-specialist": "API contracts, system integration, external services",
        "ux-tester": "Usability testing, heuristic evaluation, user research, interaction patterns",
        "release-manager": "Release gates, deployment readiness, version management, CI/CD",
        "usability-expert": "Usability heuristics, user flows, interaction patterns, accessibility",
    }

    focus = agent_context.get(
        agent_type,
        f"Analyze the {agent_type.replace('-', ' ')} aspects of the request: identify risks, gaps, and specific recommendations."
    )

    output_path = f"{project_path}/agent-outputs/{agent_type}.md"
    timestamp = datetime.now().isoformat()

    skills_section = ""
    if available_skills:
        skill_lines = "\n".join(f"- /{s} - Use when relevant to your review" for s in available_skills)
        skills_section = f"""
## Optional Skills (use AFTER writing your output file)

Complete steps 1-7 of the Workflow FIRST. Only then invoke skills if they would
add value to your already-written analysis.

{skill_lines}
"""

    return f"""You are the {agent_type.replace('-', ' ')} on team "{team_name}". Your PRIMARY deliverable is the output file at {output_path}. Everything else is secondary to producing that file.

REQUEST: {request}

PROJECT PATH: {project_path}

## Your Role in the Team

You are a teammate in a QRALPH team. You coordinate with other agents through:
- **TaskList** - Check for your assigned tasks
- **TaskUpdate** - Mark tasks as in_progress/completed
- **SendMessage** - Report findings to team lead when done

## Focus Areas
{focus}

## Workflow

1. Check TaskList for your assigned task
2. Mark it in_progress via TaskUpdate
3. Analyze the request from your specialized perspective
4. **Use the Write tool** to save your analysis to: `{output_path}`
   IMPORTANT: You MUST call the Write tool. Writing text in your response is NOT sufficient.
5. Verify the Write tool succeeded (check for errors in the tool response)
6. Mark task completed via TaskUpdate
7. Send summary to team lead via SendMessage — include "File written: YES" or "File written: NO, error: [reason]"
{skills_section}
## Output Format

Use the Write tool to write this structure to `{output_path}`:

# {agent_type.replace('-', ' ').title()} Review

## Summary
[2-3 sentence summary of your analysis]

## Findings

### P0 - Critical (blocks progress)
- [Finding with specific location/file if applicable]

### P1 - Important (should address)
- [Finding with specific recommendation]

### P2 - Suggestions (nice to have)
- [Finding with rationale]

## Recommendations
[Numbered list of specific actions]

---
*Review completed at: {timestamp}*
<!-- QRALPH-RECEIPT: {{"agent":"{agent_type}","status":"complete","written_at":"{timestamp}"}} -->

---
## CRITICAL REMINDER

Before marking your task complete, you MUST have:
1. Called the Write tool to write your findings to: `{output_path}`
2. Verified the Write tool returned success
3. The file MUST end with the QRALPH-RECEIPT comment shown in the Output Format above

If you cannot write the file, report the error in your SendMessage to the team lead.
DO NOT mark your task as completed without a confirmed written output file.
"""


# ─── SYNTHESIS ───────────────────────────────────────────────────────────────

def cmd_synthesize():
    """Consolidate agent outputs into SYNTHESIS.md with P0/P1/P2 findings."""
    with qralph_state.exclusive_state_lock():
        return _cmd_synthesize_locked()


def _cmd_synthesize_locked():
    """Inner synthesize logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project. Run init first.")

    project_path = Path(state["project_path"])

    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        return _error_result(breaker_error)

    outputs_dir = project_path / "agent-outputs"

    # Check for sub-team result file (v4.1 hierarchical teams)
    reviewing_result_file = project_path / "phase-outputs" / "REVIEWING-result.json"
    subteam_metadata = None
    if reviewing_result_file.exists():
        subteam_metadata = safe_read_json(reviewing_result_file, {})

    agents = state.get("agents", [])

    # ── PHASE 1: Synthesis hard-gate on missing outputs ──
    if agents:
        missing_outputs = [a for a in agents if not (outputs_dir / f"{a}.md").exists()]
        if missing_outputs:
            log_decision(project_path,
                f"Synthesis BLOCKED: {len(missing_outputs)}/{len(agents)} agent outputs missing: {missing_outputs}")
            return _error_result(
                f"Synthesis blocked: {len(missing_outputs)}/{len(agents)} agents have not written "
                f"output files: {missing_outputs}. Check team tasks or re-run failed agents."
            )
        empty_outputs = [
            a for a in agents
            if (outputs_dir / f"{a}.md").exists() and (outputs_dir / f"{a}.md").stat().st_size < 50
        ]
        if empty_outputs:
            log_decision(project_path,
                f"Synthesis BLOCKED: {len(empty_outputs)} agent outputs empty: {empty_outputs}")
            return _error_result(
                f"Synthesis blocked: {len(empty_outputs)} agents wrote empty output (<50 bytes): {empty_outputs}"
            )

    # ── PHASE 2D: Compute Evidence Quality Score ──
    eqs_data = compute_evidence_quality_score(agents, outputs_dir)
    log_decision(project_path,
        f"Synthesis preflight: {eqs_data['agents_with_output']}/{eqs_data['total_agents']} agent outputs present, "
        f"EQS={eqs_data['eqs']}/100 ({eqs_data['confidence']})")

    all_findings = {"P0": [], "P1": [], "P2": []}
    agent_summaries = []

    for i, agent in enumerate(agents, 1):
        print(f"Synthesizing agent {i}/{len(agents)}: {agent}...", file=sys.stderr)
        output_file = outputs_dir / f"{agent}.md"
        if output_file.exists():
            content = output_file.read_text()
            agent_summaries.append(f"### {agent}\n{extract_summary(content)}")
            tokens = estimate_tokens(content)
            update_circuit_breakers(state, tokens, "haiku")
            for priority in ["P0", "P1", "P2"]:
                findings = extract_findings(content, priority)
                for f in findings:
                    all_findings[priority].append({"agent": agent, "finding": f})

    # Include team composition and plugin info
    skills_info = state.get("skills_for_agents", {})
    skills_section = ""
    if skills_info:
        skills_section = "\n## Skills Used\n"
        for agent, skills in skills_info.items():
            skills_section += f"- **{agent}**: {', '.join(skills)}\n"

    # Build evidence quality section
    eqs_warning = ""
    if eqs_data["eqs"] < 20:
        eqs_warning = (
            "\n> **WARNING: HOLLOW RUN** — No agent output files contained substantive content. "
            "The findings below reflect absence of evidence, not evidence of absence. "
            "Do not act on this synthesis without re-running or manually inspecting agents.\n"
        )
    elif eqs_data["eqs"] < 50:
        eqs_warning = (
            "\n> **WARNING: LOW CONFIDENCE** — Partial agent output. "
            "Synthesis may be incomplete.\n"
        )

    agent_evidence_lines = []
    for agent in agents:
        status_info = eqs_data["agent_status"].get(agent, {})
        s = status_info.get("status", "missing")
        w = status_info.get("words", 0)
        r = " [receipt]" if status_info.get("receipt") else ""
        mark = "present" if s == "present" else s.upper()
        agent_evidence_lines.append(f"| {agent} | {mark} | {w} |{r}")

    evidence_table = "\n".join(agent_evidence_lines)

    synthesis = f"""# QRALPH Synthesis Report: {state['project_id']}

## Request
{state['request']}

## Evidence Quality

| Metric | Value |
|--------|-------|
| Agents with output | {eqs_data['agents_with_output']} / {eqs_data['total_agents']} |
| Total output words | {eqs_data['total_words']:,} |
| Evidence Quality Score | {eqs_data['eqs']}/100 |
| Confidence | {eqs_data['confidence']} |
{eqs_warning}
| Agent | Output | Words |
|-------|--------|-------|
{evidence_table}

## Team Composition
- **Team**: {state.get('team_name', 'N/A')}
- **Agents**: {len(state.get('agents', []))} ({', '.join(state.get('agents', []))})
- **Domains**: {', '.join(state.get('domains', []))}
{skills_section}
## Agent Summaries
{"".join(agent_summaries)}

## Consolidated Findings

### P0 - Critical ({len(all_findings['P0'])} issues)
{format_findings(all_findings['P0'])}

### P1 - Important ({len(all_findings['P1'])} issues)
{format_findings(all_findings['P1'])}

### P2 - Suggestions ({len(all_findings['P2'])} issues)
{format_findings(all_findings['P2'])}

## Recommended Actions

{generate_action_plan(all_findings)}

---
*Synthesized at: {datetime.now().isoformat()}*
*QRALPH v{VERSION} - Hierarchical Team Orchestration*
*Evidence Quality Score: {eqs_data['eqs']}/100 ({eqs_data['confidence']})*
"""

    safe_write(project_path / "SYNTHESIS.md", synthesis)

    next_phase = "EXECUTING"
    if not validate_phase_transition(state["phase"], next_phase, state.get("mode", "coding")):
        return _error_result(f"Invalid phase transition: {state['phase']} -> {next_phase}")

    state["findings"] = all_findings
    state["phase"] = next_phase
    save_state_and_checkpoint(state)

    log_decision(project_path,
        f"Synthesis complete: {len(all_findings['P0'])} P0, "
        f"{len(all_findings['P1'])} P1, {len(all_findings['P2'])} P2 "
        f"[EQS:{eqs_data['eqs']}/100 — {eqs_data['confidence']}]"
    )

    # Store EQS in state for SUMMARY.md
    state["evidence_quality"] = eqs_data

    output = {
        "status": "synthesized",
        "project_id": state["project_id"],
        "synthesis_file": str(project_path / "SYNTHESIS.md"),
        "p0_count": len(all_findings["P0"]),
        "p1_count": len(all_findings["P1"]),
        "p2_count": len(all_findings["P2"]),
        "evidence_quality_score": eqs_data["eqs"],
        "evidence_confidence": eqs_data["confidence"],
        "next_phase": state["phase"],
        "team_shutdown_needed": False,
    }
    print(json.dumps(output, indent=2))
    return output


def extract_summary(content: str) -> str:
    """Extract the ## Summary section from an agent output markdown file."""
    match = re.search(r'## Summary\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    return match.group(1).strip() if match else "(No summary found)"


def extract_findings(content: str, priority: str) -> list:
    """Extract bullet-point findings under a ### priority heading (P0/P1/P2)."""
    pattern = rf'### {priority}[^\n]*\n(.*?)(?=\n###|\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        findings_text = match.group(1)
        findings = re.findall(r'^[-*]\s*(.+)$', findings_text, re.MULTILINE)
        skip = {"none identified", "none", "n/a", "no issues", "no findings"}
        return [f.strip() for f in findings if f.strip() and not f.startswith('(') and f.strip().lower() not in skip]
    return []


def format_findings(findings: list) -> str:
    """Format a list of {agent, finding} dicts into markdown bullet points."""
    if not findings:
        return "- None identified"
    return "\n".join(f"- **[{f['agent']}]** {f['finding']}" for f in findings)


def generate_action_plan(findings: dict) -> str:
    """Generate a numbered action plan from prioritized findings."""
    actions = []
    if findings["P0"]:
        actions.append("1. **BLOCK** - Address P0 issues before proceeding:")
        for i, f in enumerate(findings["P0"], 1):
            actions.append(f"   {i}. {f['finding'][:100]}...")
    if findings["P1"]:
        actions.append(f"\n2. **FIX** - Address {len(findings['P1'])} P1 issues")
    if findings["P2"]:
        actions.append(f"\n3. **CONSIDER** - Review {len(findings['P2'])} P2 suggestions")
    if not any(findings.values()):
        actions.append("1. No issues identified - proceed to UAT")
    return "\n".join(actions)


# ─── HEALING ─────────────────────────────────────────────────────────────────

def cmd_heal(error_details: str):
    """Attempt self-healing: classify error, escalate model tier, apply fix."""
    with qralph_state.exclusive_state_lock():
        return _cmd_heal_locked(error_details)


def _cmd_heal_locked(error_details: str):
    """Inner heal logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project. Run init first.")

    project_path = Path(state["project_path"])

    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)

    state["heal_attempts"] = state.get("heal_attempts", 0) + 1
    heal_attempt = state["heal_attempts"]

    update_circuit_breakers(state, 0, "haiku", error_details)

    if heal_attempt > MAX_HEAL_ATTEMPTS:
        deferred_content = f"""# Deferred Issue

## Error
{error_details}

## Attempts
Failed after {MAX_HEAL_ATTEMPTS} healing attempts.

## Resolution
Issue deferred for manual review.

---
*Deferred at: {datetime.now().isoformat()}*
"""
        safe_write(project_path / "DEFERRED.md", deferred_content)
        log_decision(project_path, f"Issue deferred after {MAX_HEAL_ATTEMPTS} attempts")

        output = {
            "status": "deferred",
            "heal_attempts": heal_attempt,
            "deferred_file": str(project_path / "DEFERRED.md"),
            "message": "Max heal attempts exceeded. Issue deferred.",
        }
        print(json.dumps(output, indent=2))
        save_state(state)
        return output

    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    heal_file = project_path / "healing-attempts" / f"attempt-{heal_attempt:02d}.md"
    safe_write(heal_file, f"""# Healing Attempt {heal_attempt}

## Model
{model}

## Error
{error_details}

## Timestamp
{datetime.now().isoformat()}
""")

    log_decision(project_path, f"Heal attempt {heal_attempt} using {model}")
    save_state(state)

    output = {
        "status": "healing",
        "heal_attempt": heal_attempt,
        "model": model,
        "error_summary": error_details[:200],
        "instruction": f"Retry using {model} model. Attempt {heal_attempt}/{MAX_HEAL_ATTEMPTS}.",
    }
    print(json.dumps(output, indent=2))
    return output


# ─── CHECKPOINT / UAT / FINALIZE ─────────────────────────────────────────────

def cmd_checkpoint(phase: str):
    """Save a timestamped checkpoint snapshot for the given phase."""
    with qralph_state.exclusive_state_lock():
        return _cmd_checkpoint_locked(phase)


def _cmd_checkpoint_locked(phase: str):
    """Inner checkpoint logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    if phase not in qralph_state.VALID_PHASES:
        return _error_result(f"Invalid phase: {phase}. Must be one of {sorted(qralph_state.VALID_PHASES)}")

    project_path = Path(state["project_path"])
    state["phase"] = phase
    state["checkpoint_at"] = datetime.now().isoformat()
    save_state(state)

    checkpoint_file = project_path / "checkpoints" / f"{phase.lower()}-{datetime.now().strftime('%H%M%S')}.json"
    safe_write_json(checkpoint_file, state)
    # Also update state.json so cmd_resume picks up the latest phase
    safe_write_json(project_path / "checkpoints" / "state.json", state)

    log_decision(project_path, f"Checkpoint saved: {phase}")

    print(json.dumps({
        "status": "checkpointed",
        "phase": phase,
        "checkpoint_file": str(checkpoint_file),
    }))


def cmd_generate_uat():
    """Generate UAT.md with acceptance test scenarios from synthesis findings."""
    with qralph_state.exclusive_state_lock():
        return _cmd_generate_uat_locked()


def _cmd_generate_uat_locked():
    """Inner UAT generation logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    project_path = Path(state["project_path"])

    uat_content = f"""# User Acceptance Test: {state['project_id']}

## Request
{state['request']}

## Pre-Requisites
- [ ] All P0 issues resolved
- [ ] All P1 issues addressed
- [ ] Code compiles/runs without errors

## Test Scenarios

### UAT-001: Primary Functionality
**Given** the system is in its initial state
**When** the user performs the main action from the request
**Then** the expected outcome occurs

### UAT-002: Edge Cases
**Given** the system has boundary conditions
**When** edge cases are tested
**Then** the system handles them gracefully

### UAT-003: Error Handling
**Given** an error condition
**When** the error occurs
**Then** appropriate feedback is provided

## Verification Checklist
- [ ] All scenarios pass
- [ ] No regressions
- [ ] Performance acceptable
- [ ] Documentation updated

---
*Generated at: {datetime.now().isoformat()}*
"""

    safe_write(project_path / "UAT.md", uat_content)

    if not validate_phase_transition(state["phase"], "UAT", state.get("mode", "coding")):
        return _error_result(f"Invalid phase transition: {state['phase']} -> UAT")

    state["phase"] = "UAT"
    save_state_and_checkpoint(state)
    log_decision(project_path, "UAT generated")

    print(json.dumps({
        "status": "uat_generated",
        "uat_file": str(project_path / "UAT.md"),
    }))


def cmd_finalize():
    """Complete the project: generate SUMMARY.md, mark COMPLETE, notify."""
    # Final sweep to clean up any lingering processes before shutdown
    sweep_orphaned_processes()

    with qralph_state.exclusive_state_lock():
        return _cmd_finalize_locked()


def _cmd_finalize_locked():
    """Inner finalize logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    project_path = Path(state["project_path"])

    # Gate: block finalize if remediation tasks exist and are incomplete
    tasks = state.get("remediation_tasks", [])
    if tasks:
        fix_level = state.get("fix_level", "p0_p1")
        active_priorities = LEVEL_PRIORITIES.get(fix_level, ["P0", "P1"])
        open_blocking = [t for t in tasks if t.get("priority") in active_priorities and t.get("status") == "open"]
        if open_blocking:
            ids = [t["id"] for t in open_blocking[:10]]
            suffix = f" (and {len(open_blocking) - 10} more)" if len(open_blocking) > 10 else ""
            log_decision(project_path, f"Finalize blocked: {len(open_blocking)} remediation tasks open at fix_level={fix_level}")
            return _error_result(
                f"Cannot finalize: {len(open_blocking)} remediation tasks still open at fix_level={fix_level}. "
                f"Open tasks: {', '.join(ids)}{suffix}. "
                f"Fix them and run remediate-verify, or change fix_level."
            )

    # Evidence quality data
    eqs = state.get("evidence_quality", {})
    eqs_score = eqs.get("eqs", "N/A")
    eqs_confidence = eqs.get("confidence", "N/A")
    eqs_agents_with = eqs.get("agents_with_output", "?")
    eqs_agents_total = eqs.get("total_agents", "?")
    eqs_words = eqs.get("total_words", 0)

    # Per-agent evidence
    agent_evidence_lines = []
    for agent in state.get("agents", []):
        status_info = eqs.get("agent_status", {}).get(agent, {})
        s = status_info.get("status", "unknown")
        mark = "present" if s == "present" else s.upper()
        agent_evidence_lines.append(f"  - {agent}: {mark} ({status_info.get('words', 0)} words)")
    agent_evidence = "\n".join(agent_evidence_lines) if agent_evidence_lines else "  - No agent data"

    findings = state.get('findings', {}) if isinstance(state.get('findings'), dict) else {}

    summary = f"""# QRALPH Summary: {state['project_id']}

## Request
{state['request']}

## Execution Details
- **Mode**: {state['mode']}
- **Team**: {state.get('team_name', 'N/A')}
- **Started**: {state['created_at']}
- **Completed**: {datetime.now().isoformat()}
- **Agents**: {', '.join(state.get('agents', []))}
- **Domains**: {', '.join(state.get('domains', []))}
- **Self-Heal Attempts**: {state.get('heal_attempts', 0)}

## Evidence Quality
- **Agents with output**: {eqs_agents_with} / {eqs_agents_total}
- **Total output words**: {eqs_words:,}
- **Evidence Quality Score**: {eqs_score}/100
- **Confidence**: {eqs_confidence}

## Results

| Priority | Count | Evidence |
|----------|-------|---------|
| P0       | {len(findings.get('P0', []))}     | {eqs_agents_with}/{eqs_agents_total} agents reported |
| P1       | {len(findings.get('P1', []))}     | {eqs_agents_with}/{eqs_agents_total} agents reported |
| P2       | {len(findings.get('P2', []))}     | {eqs_agents_with}/{eqs_agents_total} agents reported |

## Agent Output Status
{agent_evidence}

## Team Lifecycle
1. Team created: {state.get('team_name', 'N/A')}
2. Teammates: {', '.join(state.get('teammates', []))}
3. Skills used: {json.dumps(state.get('skills_for_agents', {}))}
4. Team shutdown: pending

## Next Steps
1. Review SYNTHESIS.md for action items
2. Shutdown team via SendMessage(type="shutdown_request")
3. TeamDelete() to clean up

---
*QRALPH v{VERSION} - Hierarchical Team Orchestration*
*Evidence Quality Score: {eqs_score}/100 ({eqs_confidence})*
"""

    safe_write(project_path / "SUMMARY.md", summary)

    if not validate_phase_transition(state["phase"], "COMPLETE", state.get("mode", "coding")):
        return _error_result(f"Invalid phase transition: {state['phase']} -> COMPLETE")

    state["phase"] = "COMPLETE"
    state["completed_at"] = datetime.now().isoformat()
    save_state_and_checkpoint(state)
    log_decision(project_path, "Project finalized")
    notify(f"QRALPH complete: {state['project_id']}")

    print(json.dumps({
        "status": "complete",
        "project_id": state["project_id"],
        "summary_file": str(project_path / "SUMMARY.md"),
        "team_shutdown": {
            "team_name": state.get("team_name"),
            "teammates": state.get("teammates", []),
            "instruction": "Send shutdown_request to each teammate, then TeamDelete()",
        },
    }))


# ─── WORK MODE ──────────────────────────────────────────────────────────────

def cmd_work_plan():
    """Generate a plan for work-mode project. Creates PLAN.md with steps, skills, estimates."""
    with qralph_state.exclusive_state_lock():
        return _cmd_work_plan_locked()


def _cmd_work_plan_locked():
    """Inner work-plan logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    if state.get("mode") != "work":
        return _error_result("work-plan only available in work mode")

    project_path = Path(state["project_path"])
    request = state["request"]
    domains = state.get("domains") or classify_domains(request)

    skills = discover_work_skills(request)
    agent_count = estimate_work_complexity(request, domains)
    has_code = contains_code_signals(request)

    plan_content = f"""# Work Plan: {state['project_id']}

## Request
{request}

## Domains
{', '.join(domains)}

## Recommended Skills
{', '.join(skills) if skills else 'None identified'}

## Agent Count
{agent_count} agent(s)

## Steps
- [ ] Step 1: Research and gather context
- [ ] Step 2: Draft initial deliverable
- [ ] Step 3: Review and iterate
{'- [ ] Step 4: Write tests (TDD mandate - code signals detected)' if has_code else ''}

## Code Signals
{'Detected - TDD mandate applies' if has_code else 'Not detected - no TDD requirement'}

## Escalation Criteria
- Domains > 3 -> escalate to coding mode
- P0 findings -> escalate to coding mode
- 3+ healing failures -> escalate to coding mode

---
*Generated by QRALPH work mode*
"""

    safe_write(project_path / "PLAN.md", plan_content)

    if not validate_phase_transition(state["phase"], "PLANNING", state.get("mode", "coding")):
        return _error_result(f"Invalid phase transition: {state['phase']} -> PLANNING")

    state["phase"] = "PLANNING"
    state["domains"] = domains
    save_state_and_checkpoint(state)
    log_decision(project_path, "Work plan generated")

    output = {
        "status": "plan_generated",
        "project_id": state["project_id"],
        "plan_file": str(project_path / "PLAN.md"),
        "agent_count": agent_count,
        "skills": skills,
        "code_signals": has_code,
        "next_step": "Review PLAN.md, then run work-approve to proceed",
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_work_approve():
    """Approve work plan and move to execution. Transitions PLANNING -> USER_REVIEW -> EXECUTING."""
    with qralph_state.exclusive_state_lock():
        return _cmd_work_approve_locked()


def _cmd_work_approve_locked():
    """Inner work-approve logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    if state.get("mode") != "work":
        return _error_result("work-approve only available in work mode")

    project_path = Path(state["project_path"])

    if state["phase"] == "PLANNING":
        state["phase"] = "USER_REVIEW"
        save_state_and_checkpoint(state)
        log_decision(project_path, "Plan submitted for user review")

    if state["phase"] == "USER_REVIEW":
        state["phase"] = "EXECUTING"
        save_state_and_checkpoint(state)
        log_decision(project_path, "Plan approved, moving to execution")

    output = {
        "status": "approved",
        "project_id": state["project_id"],
        "phase": state["phase"],
        "next_step": "Execute the plan. Run select-agents then synthesize.",
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_work_iterate(feedback: str):
    """Iterate on work plan based on user feedback."""
    with qralph_state.exclusive_state_lock():
        return _cmd_work_iterate_locked(feedback)


def _cmd_work_iterate_locked(feedback: str):
    """Inner work-iterate logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    if state.get("mode") != "work":
        return _error_result("work-iterate only available in work mode")

    project_path = Path(state["project_path"])

    # Sanitize feedback before writing to file (prevents markdown/command injection)
    feedback = sanitize_request(feedback)

    # Save feedback
    feedback_file = project_path / "PLAN-FEEDBACK.md"
    timestamp = datetime.now().isoformat()
    feedback_content = f"\n\n## Feedback ({timestamp})\n\n{feedback}\n"

    if feedback_file.exists():
        existing = feedback_file.read_text()
        safe_write(feedback_file, existing + feedback_content)
    else:
        safe_write(feedback_file, f"# Plan Feedback\n{feedback_content}")

    # Return to PLANNING phase
    if validate_phase_transition(state["phase"], "PLANNING", "work"):
        state["phase"] = "PLANNING"
        save_state_and_checkpoint(state)
        log_decision(project_path, f"Plan iteration requested: {feedback[:80]}")

    output = {
        "status": "iterating",
        "project_id": state["project_id"],
        "feedback_file": str(feedback_file),
        "next_step": "Revise PLAN.md based on feedback, then work-approve again",
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_escalate():
    """Escalate work-mode project to full coding mode with 3-7 agent team."""
    with qralph_state.exclusive_state_lock():
        return _cmd_escalate_locked()


def _cmd_escalate_locked():
    """Inner escalate logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    project_path = Path(state["project_path"])

    old_mode = state.get("mode", "coding")
    state["mode"] = "coding"

    # Transition to ESCALATE then REVIEWING
    if state["phase"] in ("EXECUTING", "PLANNING", "USER_REVIEW"):
        state["phase"] = "REVIEWING"
    save_state_and_checkpoint(state)
    log_decision(project_path, f"Escalated from {old_mode} mode to coding mode")

    output = {
        "status": "escalated",
        "project_id": state["project_id"],
        "old_mode": old_mode,
        "new_mode": "coding",
        "phase": state["phase"],
        "next_step": "Run select-agents for full 3-7 agent team, then synthesize",
    }
    print(json.dumps(output, indent=2))
    return output


# ─── REMEDIATION COMMANDS ───────────────────────────────────────────────────

def cmd_remediate():
    """Create remediation tasks from synthesis findings. Requires EXECUTING phase."""
    with qralph_state.exclusive_state_lock():
        return _cmd_remediate_locked()


def _cmd_remediate_locked():
    """Inner remediate logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    if state["phase"] != "EXECUTING":
        return _error_result(f"Remediate requires EXECUTING phase, currently: {state['phase']}")

    # Idempotency guard: if remediation tasks already exist, return them
    existing_tasks = state.get("remediation_tasks", [])
    if existing_tasks:
        open_tasks = [t for t in existing_tasks if t["status"] == "open"]
        fixed_tasks = [t for t in existing_tasks if t["status"] == "fixed"]
        output = {
            "status": "remediation_exists",
            "project_id": state["project_id"],
            "total_tasks": len(existing_tasks),
            "open_tasks": len(open_tasks),
            "fixed_tasks": len(fixed_tasks),
            "message": "Remediation tasks already exist. Use remediate-done to mark tasks fixed.",
        }
        print(json.dumps(output, indent=2))
        return output

    project_path = Path(state["project_path"])
    findings = state.get("findings", {})

    # Check fix_level — skip remediation entirely if "none"
    fix_level = state.get("fix_level", "p0_p1")
    active_priorities = LEVEL_PRIORITIES.get(fix_level, ["P0", "P1"])

    if fix_level == "none":
        log_decision(project_path, "Remediation skipped (fix_level=none)")
        output = {
            "status": "remediation_skipped",
            "fix_level": "none",
            "project_id": state["project_id"],
            "message": "Remediation skipped: fix_level is set to 'none'.",
        }
        print(json.dumps(output, indent=2))
        return output

    # Detect TDD applicability from test infrastructure
    test_infra = state.get("test_infrastructure", {})
    has_test_infra = bool(test_infra.get("test_cmd"))
    tdd_applicable = has_test_infra and state.get("mode") == "coding"

    # Normalize findings: support both dict {"P0": [...]} and flat list [{"priority": "P0", ...}]
    tasks = []
    task_id = 1
    if isinstance(findings, list):
        for item in findings:
            priority = item.get("priority", "P2")
            if priority not in active_priorities:
                continue
            title = item.get("title", item.get("finding", str(item)))
            task = {
                "id": f"REM-{task_id:03d}",
                "priority": priority,
                "finding": title,
                "status": "open",
            }
            if tdd_applicable:
                task["tdd_steps"] = [
                    "Write a failing test that reproduces the finding",
                    "Implement the minimal fix to make the test pass",
                    f"Run quality gate: {test_infra['quality_gate_cmd'] or test_infra['test_cmd']}",
                ]
            tasks.append(task)
            task_id += 1
    else:
        for priority in active_priorities:
            for finding in findings.get(priority, []):
                task = {
                    "id": f"REM-{task_id:03d}",
                    "priority": priority,
                    "finding": finding,
                    "status": "open",
                }
                if tdd_applicable:
                    task["tdd_steps"] = [
                        "Write a failing test that reproduces the finding",
                        "Implement the minimal fix to make the test pass",
                        f"Run quality gate: {test_infra['quality_gate_cmd'] or test_infra['test_cmd']}",
                    ]
                tasks.append(task)
                task_id += 1

    state["remediation_tasks"] = tasks
    save_state(state)
    safe_write_json(project_path / "checkpoints" / "state.json", state)

    # Write REMEDIATION.md
    lines = ["# Remediation Plan\n"]
    if tdd_applicable:
        lines.append(f"\n> **TDD Enforcement Active** — test infrastructure detected: `{test_infra['framework']}`")
        lines.append(f"> Quality gate: `{test_infra['quality_gate_cmd'] or test_infra['test_cmd']}`")
        lines.append("> Each task MUST follow: write failing test → implement fix → run quality gate\n")
    elif has_test_infra:
        lines.append(f"\n> Test infrastructure detected: `{test_infra['framework']}` — run `{test_infra['test_cmd']}` to verify fixes\n")
    for priority in ("P0", "P1", "P2"):
        priority_tasks = [t for t in tasks if t["priority"] == priority]
        if priority_tasks:
            lines.append(f"\n## {priority} ({len(priority_tasks)} tasks)\n")
            for t in priority_tasks:
                lines.append(f"- [ ] **{t['id']}**: {t['finding']}")
                if t.get("tdd_steps"):
                    for step in t["tdd_steps"]:
                        lines.append(f"  - [ ] {step}")
    lines.append(f"\n---\n*Generated at: {datetime.now().isoformat()}*")
    safe_write(project_path / "REMEDIATION.md", "\n".join(lines))

    log_decision(project_path, f"Remediation plan created: {len(tasks)} tasks")

    output = {
        "status": "remediation_created",
        "project_id": state["project_id"],
        "total_tasks": len(tasks),
        "p0_tasks": len([t for t in tasks if t["priority"] == "P0"]),
        "p1_tasks": len([t for t in tasks if t["priority"] == "P1"]),
        "p2_tasks": len([t for t in tasks if t["priority"] == "P2"]),
        "remediation_file": str(project_path / "REMEDIATION.md"),
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_remediate_done(task_ids: str, notes: str = ""):
    """Mark specific remediation tasks as fixed."""
    with qralph_state.exclusive_state_lock():
        return _cmd_remediate_done_locked(task_ids, notes)


def _cmd_remediate_done_locked(task_ids: str, notes: str = ""):
    """Inner remediate-done logic, called under exclusive lock."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    ids = [tid.strip() for tid in task_ids.split(",")]
    tasks = state.get("remediation_tasks", [])
    marked = []

    for task in tasks:
        if task["id"] in ids:
            task["status"] = "fixed"
            if notes:
                task["notes"] = notes
            marked.append(task["id"])

    state["remediation_tasks"] = tasks
    save_state(state)

    project_path = Path(state["project_path"])
    safe_write_json(project_path / "checkpoints" / "state.json", state)
    log_decision(project_path, f"Remediation tasks marked fixed: {', '.join(marked)}")

    open_tasks = [t for t in tasks if t["status"] == "open"]
    output = {
        "status": "tasks_updated",
        "marked_fixed": marked,
        "remaining_open": len(open_tasks),
        "remaining_p0": len([t for t in open_tasks if t["priority"] == "P0"]),
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_remediate_verify():
    """Verify remediation is complete. Blocks on open P0 tasks."""
    with qralph_state.exclusive_state_lock():
        return _cmd_remediate_verify_locked()


def _cmd_remediate_verify_locked():
    """Inner remediate-verify logic, called under exclusive lock.

    Performs TWO verification passes:
    1. Bookkeeping check: all active-priority tasks marked "fixed"
    2. Quality gate check: runs detected test/lint/typecheck commands
    Both must pass before transitioning to COMPLETE.
    """
    state = load_state()
    if not state:
        return _error_result("No active project.")

    tasks = state.get("remediation_tasks", [])
    fix_level = state.get("fix_level", "p0_p1")
    active_priorities = LEVEL_PRIORITIES.get(fix_level, ["P0", "P1"])

    open_blocking = [t for t in tasks if t["priority"] in active_priorities and t["status"] == "open"]
    open_all = [t for t in tasks if t["status"] == "open"]

    project_path = Path(state["project_path"])

    if open_blocking:
        log_decision(project_path, f"Remediation verify blocked: {len(open_blocking)} tasks open at fix_level={fix_level}")
        output = {
            "status": "blocked",
            "reason": f"{len(open_blocking)} tasks still open at fix_level={fix_level}",
            "open_blocking_tasks": [t["id"] for t in open_blocking],
            "fix_level": fix_level,
            "total_open": len(open_all),
        }
        print(json.dumps(output, indent=2))
        return output

    # ── Quality gate verification ──
    # Re-detect test infrastructure (agents may have created it during EXECUTING)
    test_infra = detect_test_infrastructure()
    if test_infra.get("test_cmd") and not state.get("test_infrastructure", {}).get("test_cmd"):
        log_decision(project_path, f"Post-execution test infra detected: {test_infra['framework']} via {test_infra['detected_from']}")
        state["test_infrastructure"] = test_infra
        save_state(state)
    elif test_infra.get("test_cmd"):
        # Use latest detection (infra may have changed during execution)
        state["test_infrastructure"] = test_infra
        save_state(state)
    quality_gate_cmd = test_infra.get("quality_gate_cmd")
    quality_gate_result = None

    if quality_gate_cmd and state.get("mode") == "coding":
        log_decision(project_path, f"Running quality gate: {quality_gate_cmd}")
        try:
            result = subprocess.run(
                quality_gate_cmd,
                shell=True,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            quality_gate_result = {
                "command": quality_gate_cmd,
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
                "stdout_tail": result.stdout[-2000:] if result.stdout else "",
                "stderr_tail": result.stderr[-2000:] if result.stderr else "",
            }
            state["quality_gate_result"] = quality_gate_result
            save_state(state)

            if result.returncode != 0:
                log_decision(project_path, f"Quality gate FAILED (exit code {result.returncode})")
                output = {
                    "status": "quality_gate_failed",
                    "reason": f"Quality gate command failed: {quality_gate_cmd}",
                    "exit_code": result.returncode,
                    "stdout_tail": quality_gate_result["stdout_tail"],
                    "stderr_tail": quality_gate_result["stderr_tail"],
                    "instruction": "Fix the failing tests/lint/typecheck, then run remediate-verify again.",
                }
                print(json.dumps(output, indent=2))
                return output
        except subprocess.TimeoutExpired:
            log_decision(project_path, f"Quality gate TIMEOUT: {quality_gate_cmd}")
            output = {
                "status": "quality_gate_timeout",
                "reason": f"Quality gate timed out after 300s: {quality_gate_cmd}",
                "instruction": "Investigate hanging tests, then run remediate-verify again.",
            }
            print(json.dumps(output, indent=2))
            return output
        except OSError as e:
            log_decision(project_path, f"Quality gate error: {e}")
            # Non-blocking — proceed if command can't be run (e.g., missing tool)
            quality_gate_result = {"command": quality_gate_cmd, "error": str(e), "passed": None}
            state["quality_gate_result"] = quality_gate_result
            save_state(state)

    # All active-priority tasks resolved + quality gate passed — transition to COMPLETE
    if not validate_phase_transition(state["phase"], "COMPLETE", state.get("mode", "coding")):
        return _error_result(f"Invalid phase transition: {state['phase']} -> COMPLETE")

    state["phase"] = "COMPLETE"
    save_state(state)
    safe_write_json(project_path / "checkpoints" / "state.json", state)

    gate_msg = ""
    if quality_gate_result and quality_gate_result.get("passed"):
        gate_msg = f", quality gate passed ({quality_gate_cmd})"
    elif quality_gate_result and quality_gate_result.get("passed") is None:
        gate_msg = f", quality gate skipped (command error: {quality_gate_result.get('error', 'unknown')})"
    elif not quality_gate_cmd:
        gate_msg = ", no quality gate detected"

    log_decision(project_path, f"Remediation verified (fix_level={fix_level}): all required priorities fixed{gate_msg}, {len(open_all)} lower-priority open")

    output = {
        "status": "verified",
        "project_id": state["project_id"],
        "phase": "COMPLETE",
        "open_lower_priority": len(open_all),
        "quality_gate": quality_gate_result,
        "team_shutdown_needed": True,
    }
    print(json.dumps(output, indent=2))
    return output


# ─── RESUME / STATUS ────────────────────────────────────────────────────────

def cmd_resume(project_id: str):
    """Resume a project from its last checkpoint and restore team config."""
    # Sweep orphaned processes from the interrupted run before resuming
    sweep_orphaned_processes()

    if not SAFE_PROJECT_ID.match(project_id):
        return _error_result(f"Invalid project_id: {project_id}")
    with qralph_state.exclusive_state_lock():
        return _cmd_resume_locked(project_id)


def _cmd_resume_locked(project_id: str):
    """Inner resume logic, called under exclusive lock."""
    matches = list(PROJECTS_DIR.glob(f"{project_id}*"))
    if not matches:
        return _error_result(f"No project found matching: {project_id}")

    project_path = matches[0]
    checkpoint_dir = project_path / "checkpoints"
    state_file = checkpoint_dir / "state.json"

    if state_file.exists():
        state = qralph_state.load_state(state_file)
    else:
        checkpoints = sorted(checkpoint_dir.glob("*.json"))
        if checkpoints:
            state = qralph_state.load_state(checkpoints[-1])
        else:
            return _error_result("No checkpoint found")

    if not state:
        return _error_result("Failed to load state (corrupt or empty)")

    # Guard: don't overwrite current-project.json if project is already COMPLETE
    if state.get("phase") == "COMPLETE":
        output = {
            "status": "already_complete",
            "project_id": state.get("project_id", project_id),
            "phase": "COMPLETE",
            "completed_at": state.get("completed_at", "unknown"),
            "message": "Project is already complete. Review SUMMARY.md for results.",
        }
        print(json.dumps(output, indent=2))
        return output

    # Version check
    version_update = check_version_update(state)

    save_state(state)
    log_decision(project_path, f"Resumed from phase: {state['phase']}")

    # Load team config for re-creation
    team_config_file = project_path / "team-config.json"
    team_config = safe_read_json(team_config_file, {})

    # Check for running sub-teams that need recovery
    sub_teams = state.get("sub_teams", {})
    running_subteams = {k: v for k, v in sub_teams.items()
                        if isinstance(v, dict) and v.get("status") == "running"}

    output = {
        "status": "resumed",
        "project_id": state["project_id"],
        "phase": state["phase"],
        "team_name": state.get("team_name"),
        "team_config": team_config,
        "next_step": get_next_step(state["phase"]),
        "execution_mode": state.get("execution_mode", "human"),
    }

    # Include remediation progress so the LLM knows what's left
    rem_tasks = state.get("remediation_tasks", [])
    if rem_tasks:
        fix_level = state.get("fix_level", "p0_p1")
        active_priorities = LEVEL_PRIORITIES.get(fix_level, ["P0", "P1"])
        open_blocking = [t for t in rem_tasks if t.get("priority") in active_priorities and t.get("status") == "open"]
        output["remediation_progress"] = {
            "total": len(rem_tasks),
            "fixed": len([t for t in rem_tasks if t.get("status") == "fixed"]),
            "open_at_fix_level": len(open_blocking),
            "fix_level": fix_level,
        }
        if open_blocking:
            output["remediation_progress"]["blocking_ids"] = [t["id"] for t in open_blocking[:20]]
            output["remediation_progress"]["warning"] = (
                f"{len(open_blocking)} tasks must be fixed before finalize. "
                "Continue remediation, then run remediate-verify."
            )

    if version_update:
        output["version_update"] = version_update

    if running_subteams:
        output["recovery_needed"] = True
        output["running_subteams"] = list(running_subteams.keys())
        output["recovery_instruction"] = (
            f"Sub-teams were interrupted: {', '.join(running_subteams.keys())}. "
            "Run resume-subteam --phase <phase> to recover."
        )

    print(json.dumps(output, indent=2))
    return output


def cmd_status(project_id: Optional[str] = None):
    """Show status of a specific project or list all projects."""
    if project_id:
        if not SAFE_PROJECT_ID.match(project_id):
            return _error_result(f"Invalid project_id: {project_id}")
        matches = list(PROJECTS_DIR.glob(f"{project_id}*"))
        if matches:
            project_path = matches[0]
            state_file = project_path / "checkpoints" / "state.json"
            state = safe_read_json(state_file)
            if state:
                # Build findings summary
                findings = state.get("findings", {})
                if isinstance(findings, dict):
                    p0_count = len(findings.get("P0", []))
                    p1_count = len(findings.get("P1", []))
                    p2_count = len(findings.get("P2", []))
                elif isinstance(findings, list):
                    p0_count = len([f for f in findings if f.get("priority") == "P0"])
                    p1_count = len([f for f in findings if f.get("priority") == "P1"])
                    p2_count = len([f for f in findings if f.get("priority") == "P2"])
                else:
                    p0_count = p1_count = p2_count = 0

                eqs_data = state.get("evidence_quality", {})
                remediation = state.get("remediation_tasks", [])

                # Read validation result if exists
                validation_result = None
                validating_file = project_path / "phase-outputs" / "VALIDATING-result.json"
                if validating_file.exists():
                    validation_result = safe_read_json(validating_file)

                state["_status_summary"] = {
                    "findings": {
                        "p0": p0_count,
                        "p1": p1_count,
                        "p2": p2_count,
                    },
                    "eqs": eqs_data.get("eqs", None),
                    "eqs_confidence": eqs_data.get("confidence", None),
                    "remediation": {
                        "total": len(remediation),
                        "open": len([t for t in remediation if t.get("status") == "open"]),
                        "fixed": len([t for t in remediation if t.get("status") == "fixed"]),
                    },
                    "validation": validation_result,
                    "fix_level": state.get("fix_level", "p0_p1"),
                }

                print(json.dumps(state, indent=2))
            else:
                print(json.dumps({"project": project_path.name, "status": "no state file"}))
        else:
            _error_result(f"Project not found: {project_id}")
    else:
        projects = []
        if PROJECTS_DIR.exists():
            for p in sorted(PROJECTS_DIR.glob("[0-9][0-9][0-9]-*")):
                state_file = p / "checkpoints" / "state.json"
                state = safe_read_json(state_file)
                if state:
                    projects.append({
                        "id": p.name,
                        "phase": state.get("phase", "unknown"),
                        "mode": state.get("mode", "unknown"),
                        "team": state.get("team_name", "N/A"),
                        "agents": len(state.get("agents", [])),
                        "created": state.get("created_at", "unknown"),
                    })
                else:
                    projects.append({"id": p.name, "phase": "no state"})
        print(json.dumps({"projects": projects}, indent=2))


def get_next_step(phase: str) -> str:
    """Return human-readable instructions for the next action after a phase."""
    steps = {
        "INIT": "Run discover to scan plugins/skills, then select-agents",
        "DISCOVERING": "Run select-agents to pick team composition",
        "REVIEWING": "TeamCreate, spawn teammates, then run synthesize when complete",
        "EXECUTING": "Run remediate to create tasks, fix findings, then remediate-verify",
        "VALIDATING": "Fresh validation sub-team running UAT against requirements",
        "UAT": "Execute UAT scenarios, then run finalize",
        "COMPLETE": "Shutdown team and review SUMMARY.md",
        "PLANNING": "Review PLAN.md, then run work-approve to proceed",
        "USER_REVIEW": "User reviews the plan, then run work-approve to execute",
        "ESCALATE": "Escalating to full coding mode with 3-7 agent team",
    }
    return steps.get(phase, "Unknown phase")


# ─── CONTROL COMMANDS ────────────────────────────────────────────────────────

def handle_control_command(command: str, state: dict, project_path: Path) -> dict:
    """Execute a CONTROL.md command (PAUSE, SKIP, ABORT, STATUS, ESCALATE)."""
    output = {"status": "control_command", "command": command}

    if command == "PAUSE":
        log_decision(project_path, "PAUSE command detected")
        output["action"] = "paused"
        output["message"] = "Execution paused. Remove PAUSE from CONTROL.md to continue."
        print(json.dumps(output, indent=2))
        sys.exit(0)
    elif command == "SKIP":
        log_decision(project_path, "SKIP command detected")
        output["action"] = "skipped"
        output["message"] = "Operation skipped."
    elif command == "ABORT":
        log_decision(project_path, "ABORT command detected")
        cmd_checkpoint(state["phase"])
        output["action"] = "aborted"
        output["message"] = "Execution aborted. Checkpoint saved. Use 'resume' to continue."
        output["team_shutdown"] = {
            "team_name": state.get("team_name"),
            "teammates": state.get("teammates", []),
            "instruction": "Send shutdown_request to all teammates before exiting",
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)
    elif command == "STATUS":
        log_decision(project_path, "STATUS command detected")
        write_status_file(state, project_path)
        output["action"] = "status_written"
        output["message"] = "Status written to STATUS.md"
    elif command == "ESCALATE":
        log_decision(project_path, "ESCALATE command detected")
        output["action"] = "escalating"
        output["message"] = "Escalating to full coding mode"
        cmd_escalate()
        return output

    print(json.dumps(output, indent=2))
    return output


def write_status_file(state: dict, project_path: Path):
    """Write a human-readable STATUS.md with phase, team, and breaker info."""
    breakers = state.get("circuit_breakers", {})
    status_content = f"""# QRALPH Status: {state.get('project_id', 'unknown')}

## Current State
- **Phase**: {state.get('phase', 'unknown')}
- **Mode**: {state.get('mode', 'unknown')}
- **Team**: {state.get('team_name', 'N/A')}
- **Heal Attempts**: {state.get('heal_attempts', 0)} / {MAX_HEAL_ATTEMPTS}

## Team
- **Agents**: {', '.join(state.get('agents', []))}
- **Teammates**: {', '.join(state.get('teammates', []))}
- **Domains**: {', '.join(state.get('domains', []))}

## Circuit Breakers
- **Total Tokens**: {breakers.get('total_tokens', 0):,} / {MAX_TOKENS:,}
- **Total Cost**: ${breakers.get('total_cost_usd', 0.0):.2f} / ${MAX_COST_USD:.2f}
- **Unique Errors**: {len(breakers.get('error_counts', {}))}

## Findings Summary
- P0: {len(state.get('findings', {}).get('P0', []))}
- P1: {len(state.get('findings', {}).get('P1', []))}
- P2: {len(state.get('findings', {}).get('P2', []))}

---
*Status generated at: {datetime.now().isoformat()}*
"""
    safe_write(project_path / "STATUS.md", status_content)


def log_decision(project_path: Path, message: str):
    """Append a timestamped entry to the project's decisions.log audit trail."""
    log_file = project_path / "decisions.log"
    try:
        if os.path.islink(str(log_file)):
            print(f"Warning: Refusing to write to symlink: {log_file}", file=sys.stderr)
            return
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a") as f:
            qralph_state._lock_file(f, exclusive=True)
            try:
                sanitized_msg = re.sub(r'[\x00-\x1f\x7f]', ' ', message)
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {sanitized_msg}\n")
                f.flush()
            finally:
                qralph_state._unlock_file(f)
    except Exception as e:
        print(f"Warning: Failed to log decision: {e}", file=sys.stderr)


def notify(message: str):
    """Send a desktop notification via the notify.py tool if available."""
    if NOTIFY_TOOL.exists():
        try:
            subprocess.run(
                ["python3", str(NOTIFY_TOOL), "--event", "complete", "--message", message],
                capture_output=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, Exception):
            pass


# ─── SUBTEAM COMMANDS (v4.1) ─────────────────────────────────────────────────

def cmd_subteam_status(phase: str):
    """Check sub-team status with circuit breaker and control command checks."""
    state, project_path = load_state(), None
    if state:
        project_path = Path(state.get("project_path", ""))

    if not state or not project_path or not project_path.exists():
        return _error_result("No active project.")

    # Control + circuit breaker checks
    with qralph_state.exclusive_state_lock():
        control_cmd = check_control_commands(project_path)
        if control_cmd:
            return handle_control_command(control_cmd, state, project_path)
        breaker_error = check_circuit_breakers(state)
        if breaker_error:
            return _error_result(breaker_error)

    # Delegate to subteam tool
    _subteam_path = SCRIPT_DIR / "qralph-subteam.py"
    _subteam_spec = importlib.util.spec_from_file_location("qralph_subteam", _subteam_path)
    subteam_mod = importlib.util.module_from_spec(_subteam_spec)
    _subteam_spec.loader.exec_module(subteam_mod)
    return subteam_mod.cmd_check_subteam(phase)


def cmd_quality_gate_wrapper(phase: str):
    """Run quality gate with logging."""
    state = load_state()
    if not state:
        return _error_result("No active project.")

    project_path = Path(state.get("project_path", ""))

    _subteam_path = SCRIPT_DIR / "qralph-subteam.py"
    _subteam_spec = importlib.util.spec_from_file_location("qralph_subteam", _subteam_path)
    subteam_mod = importlib.util.module_from_spec(_subteam_spec)
    _subteam_spec.loader.exec_module(subteam_mod)
    result = subteam_mod.cmd_quality_gate(phase)

    if project_path.exists():
        passed = result.get("passed", False) if isinstance(result, dict) else False
        log_decision(project_path, f"Quality gate {phase}: {'PASSED' if passed else 'FAILED'} "
                     f"(confidence: {result.get('confidence', 0) if isinstance(result, dict) else 0})")
    return result


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    """CLI entry point: parse args and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(description="QRALPH Orchestrator v4.1 - Hierarchical Teams")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize new project")
    init_parser.add_argument("request", help="The request to execute")
    init_parser.add_argument("--mode", choices=["coding", "planning", "work"], default="coding")
    exec_group = init_parser.add_mutually_exclusive_group()
    exec_group.add_argument("--auto", action="store_const", const="auto", dest="execution_mode",
                            help="Auto-continue after review (no pause)")
    exec_group.add_argument("--human", action="store_const", const="human", dest="execution_mode",
                            help="Pause for human approval after review (default)")
    init_parser.set_defaults(execution_mode="human")
    init_parser.add_argument("--fix-level",
        choices=["none", "p0", "p0_p1", "all"],
        default="p0_p1",
        dest="fix_level",
        help="Which findings to remediate: none (skip fixes), p0 (critical only), p0_p1 (default), all (P0+P1+P2)")

    # discover
    subparsers.add_parser("discover", help="Discover available plugins and skills")

    # select-agents
    select_parser = subparsers.add_parser("select-agents", help="Select best agents for team")
    select_parser.add_argument("--agents", help="Comma-separated agent list (override)")
    select_parser.add_argument("--subteam", action="store_true",
                               help="Use hierarchical sub-team architecture (v4.1)")

    # synthesize
    subparsers.add_parser("synthesize", help="Synthesize agent findings")

    # checkpoint
    cp_parser = subparsers.add_parser("checkpoint", help="Save checkpoint")
    cp_parser.add_argument("phase", help="Current phase name")

    # generate-uat
    subparsers.add_parser("generate-uat", help="Generate UAT scenarios")

    # finalize
    subparsers.add_parser("finalize", help="Finalize project")

    # heal
    heal_parser = subparsers.add_parser("heal", help="Self-healing with model escalation")
    heal_parser.add_argument("error_details", help="Error description to heal from")

    # resume
    resume_parser = subparsers.add_parser("resume", help="Resume project")
    resume_parser.add_argument("project_id", help="Project ID to resume")

    # status
    status_parser = subparsers.add_parser("status", help="Show project status")
    status_parser.add_argument("project_id", nargs="?", help="Optional project ID")

    # work mode commands
    subparsers.add_parser("work-plan", help="Generate work plan (work mode)")
    subparsers.add_parser("work-approve", help="Approve work plan (work mode)")
    iterate_parser = subparsers.add_parser("work-iterate", help="Iterate on work plan with feedback")
    iterate_parser.add_argument("feedback", help="User feedback on plan")
    subparsers.add_parser("escalate", help="Escalate to full coding mode")

    # remediation commands
    subparsers.add_parser("remediate", help="Create remediation tasks from findings")
    rem_done_parser = subparsers.add_parser("remediate-done", help="Mark remediation tasks as fixed")
    rem_done_parser.add_argument("task_ids", help="Comma-separated task IDs (e.g. REM-001,REM-002)")
    rem_done_parser.add_argument("--notes", default="", help="Optional notes about the fix")
    subparsers.add_parser("remediate-verify", help="Verify remediation and transition to COMPLETE")

    # v4.1 sub-team commands
    st_status_parser = subparsers.add_parser("subteam-status", help="Check sub-team status")
    st_status_parser.add_argument("--phase", required=True, help="Phase to check")
    qg_parser = subparsers.add_parser("quality-gate", help="Run quality gate on phase")
    qg_parser.add_argument("--phase", required=True, help="Phase to validate")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args.request, args.mode, args.execution_mode, args.fix_level)
    elif args.command == "discover":
        cmd_discover()
    elif args.command == "select-agents":
        agents = args.agents.split(",") if args.agents else None
        cmd_select_agents(agents, use_subteam=args.subteam)
    elif args.command == "synthesize":
        cmd_synthesize()
    elif args.command == "checkpoint":
        cmd_checkpoint(args.phase)
    elif args.command == "generate-uat":
        cmd_generate_uat()
    elif args.command == "finalize":
        cmd_finalize()
    elif args.command == "heal":
        cmd_heal(args.error_details)
    elif args.command == "resume":
        cmd_resume(args.project_id)
    elif args.command == "status":
        cmd_status(args.project_id)
    elif args.command == "work-plan":
        cmd_work_plan()
    elif args.command == "work-approve":
        cmd_work_approve()
    elif args.command == "work-iterate":
        cmd_work_iterate(args.feedback)
    elif args.command == "escalate":
        cmd_escalate()
    elif args.command == "remediate":
        cmd_remediate()
    elif args.command == "remediate-done":
        cmd_remediate_done(args.task_ids, args.notes)
    elif args.command == "remediate-verify":
        cmd_remediate_verify()
    elif args.command == "subteam-status":
        cmd_subteam_status(args.phase)
    elif args.command == "quality-gate":
        cmd_quality_gate_wrapper(args.phase)
    else:
        parser.print_help()


if __name__ == "__main__":
    if sys.version_info < (3, 6):
        sys.exit("QRALPH requires Python 3.6+")
    main()
