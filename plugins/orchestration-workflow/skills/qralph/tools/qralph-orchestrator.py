#!/usr/bin/env python3
"""
QRALPH Orchestrator v3.0 - Team-based state management with plugin discovery.

This orchestrator MANAGES STATE and DISCOVERS PLUGINS. Claude creates native
teams via TeamCreate, spawns teammates, and coordinates via TaskList/SendMessage.

Commands:
    python3 qralph-orchestrator.py init "<request>" [--mode planning]
    python3 qralph-orchestrator.py discover
    python3 qralph-orchestrator.py select-agents [--agents a,b,c]
    python3 qralph-orchestrator.py synthesize
    python3 qralph-orchestrator.py checkpoint <phase>
    python3 qralph-orchestrator.py generate-uat
    python3 qralph-orchestrator.py finalize
    python3 qralph-orchestrator.py resume <project-id>
    python3 qralph-orchestrator.py status [<project-id>]
    python3 qralph-orchestrator.py heal <error-details>
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

# Constants
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
PROJECTS_DIR = QRALPH_DIR / "projects"
AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
PLUGINS_DIR = PROJECT_ROOT / ".claude" / "plugins"
NOTIFY_TOOL = Path.home() / ".claude" / "tools" / "notify.py"

# Circuit Breaker Limits
MAX_TOKENS = 500_000
MAX_COST_USD = 40.0
MAX_SAME_ERROR = 3
MAX_HEAL_ATTEMPTS = 5

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


def get_state_file() -> Path:
    return QRALPH_DIR / "current-project.json"


def load_state() -> dict:
    return qralph_state.load_state(get_state_file())


def save_state(state: dict):
    qralph_state.save_state(state, get_state_file())


def sanitize_request(request: str) -> str:
    """Sanitize request string: strip null bytes and path traversal sequences."""
    if not request or not isinstance(request, str):
        return ""
    sanitized = request.replace('\x00', '')
    sanitized = re.sub(r'\.\.[/\\]', '', sanitized)
    return sanitized[:2000].strip()


def validate_request(request: str) -> bool:
    if not request or not isinstance(request, str):
        return False
    return len(request.strip()) >= 3


def validate_phase_transition(current_phase: str, next_phase: str, mode: str = "coding") -> bool:
    coding_transitions = {
        "INIT": ["DISCOVERING", "REVIEWING"],
        "DISCOVERING": ["REVIEWING"],
        "REVIEWING": ["EXECUTING", "COMPLETE"],
        "EXECUTING": ["UAT"],
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
    words = re.findall(r'\b[a-zA-Z]{3,}\b', request.lower())
    stop_words = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into'}
    slug_words = [w for w in words if w not in stop_words][:3]
    return "-".join(slug_words)[:30] or "project"


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def estimate_cost(tokens: int, model: str) -> float:
    cost_per_million = MODEL_COSTS.get(model, MODEL_COSTS["sonnet"])
    return (tokens / 1_000_000) * cost_per_million


def check_circuit_breakers(state: dict) -> Optional[str]:
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
    if "circuit_breakers" not in state:
        state["circuit_breakers"] = {"total_tokens": 0, "total_cost_usd": 0.0, "error_counts": {}}
    breakers = state["circuit_breakers"]
    breakers["total_tokens"] += tokens
    breakers["total_cost_usd"] += estimate_cost(tokens, model)
    if error:
        error_key = error[:100]
        breakers["error_counts"][error_key] = breakers["error_counts"].get(error_key, 0) + 1


def check_control_commands(project_path: Path) -> Optional[str]:
    control_file = project_path / "CONTROL.md"
    if not control_file.exists():
        return None
    try:
        content = control_file.read_text().upper()
        for cmd in ["PAUSE", "SKIP", "ABORT", "STATUS", "ESCALATE"]:
            if cmd in content:
                return cmd
    except Exception:
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
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project. Run init first."}))
        return

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

    # Update state
    state["phase"] = "DISCOVERING"
    state["domains"] = domains
    state["discovery"] = {
        "total": len(scored),
        "relevant": len(discovery_result["relevant_capabilities"]),
    }
    save_state(state)

    log_decision(project_path, f"Discovery: {len(domains)} domains, {len(discovery_result['relevant_capabilities'])} relevant capabilities")

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
        "next_step": "Run select-agents to pick the best team composition",
    }
    print(json.dumps(output, indent=2))
    return output


# ─── PROJECT INITIALIZATION ─────────────────────────────────────────────────

def cmd_init(request: str, mode: str = "coding"):
    request = sanitize_request(request)
    if not validate_request(request):
        error = {"error": "Invalid request: must be non-empty string with at least 3 characters"}
        print(json.dumps(error))
        return error

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

    # Create initial files
    try:
        safe_write(project_path / "CONTROL.md",
            "# QRALPH Control\n\n"
            "Write commands here:\n"
            "- PAUSE - stop after current step\n"
            "- SKIP - skip current operation\n"
            "- ABORT - graceful shutdown\n"
            "- STATUS - force status dump\n"
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
    }
    save_state(state)
    safe_write_json(project_path / "checkpoints" / "state.json", state)

    output = {
        "status": "initialized",
        "project_id": project_id,
        "project_path": str(project_path),
        "team_name": state["team_name"],
        "mode": mode,
        "next_step": "Run discover to scan available plugins and skills, then select-agents",
    }
    print(json.dumps(output, indent=2))
    return output


# ─── AGENT SELECTION ─────────────────────────────────────────────────────────

def cmd_select_agents(custom_agents: Optional[list] = None):
    """Select best agents based on discovery results and request analysis."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project. Run init first."}))
        return

    project_path = Path(state["project_path"])

    # Check control/circuit
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        print(json.dumps({"error": breaker_error}))
        return

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
    save_state(state)

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

    output = {
        "status": "agents_selected",
        "project_id": state["project_id"],
        "team_name": state["team_name"],
        "agent_count": len(agent_configs),
        "agents": agent_configs,
        "skills_for_agents": skills_for_agents,
        "instruction": (
            "1. TeamCreate(team_name='" + state["team_name"] + "')\n"
            "2. TaskCreate for each agent's review task\n"
            "3. Spawn teammates via Task(subagent_type=..., team_name=..., name=...)\n"
            "4. Monitor via TaskList + receive SendMessage from teammates\n"
            "5. When all complete, run synthesize"
        ),
    }
    print(json.dumps(output, indent=2))
    return output


def generate_team_agent_prompt(
    agent_type: str,
    request: str,
    project_id: str,
    project_path: Path,
    team_name: str,
    available_skills: List[str],
) -> str:
    """Generate a prompt for a team-based agent."""
    skills_section = ""
    if available_skills:
        skill_lines = "\n".join(f"- /{s} - Use when relevant to your review" for s in available_skills)
        skills_section = f"""
## Available Skills

You have access to these skills that are relevant to your work:
{skill_lines}

Use the Skill tool to invoke them when they would improve your analysis.
"""

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
    }

    focus = agent_context.get(agent_type, "Analyze from your specialized perspective")

    return f"""You are {agent_type.replace('-', ' ')} on team "{team_name}", reviewing project {project_id}.

REQUEST: {request}

PROJECT PATH: {project_path}

## Your Role in the Team

You are a teammate in a QRALPH team. You coordinate with other agents through:
- **TaskList** - Check for your assigned tasks
- **TaskUpdate** - Mark tasks as in_progress/completed
- **SendMessage** - Report findings to team lead when done

## Focus Areas
{focus}
{skills_section}
## Workflow

1. Check TaskList for your assigned task
2. Mark it in_progress via TaskUpdate
3. Analyze the request from your specialized perspective
4. Write findings to: {project_path}/agent-outputs/{agent_type}.md
5. Mark task completed via TaskUpdate
6. Send summary to team lead via SendMessage

## Output Format

Write your findings using this structure:

# {agent_type.replace('-', ' ').title()} Review

## Summary
[2-3 sentence summary]

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
*Review completed at: {datetime.now().isoformat()}*
"""


# ─── SYNTHESIS ───────────────────────────────────────────────────────────────

def cmd_synthesize():
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project. Run init first."}))
        return

    project_path = Path(state["project_path"])

    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        print(json.dumps({"error": breaker_error}))
        return

    outputs_dir = project_path / "agent-outputs"

    all_findings = {"P0": [], "P1": [], "P2": []}
    agent_summaries = []

    for agent in state.get("agents", []):
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

    synthesis = f"""# QRALPH Synthesis Report: {state['project_id']}

## Request
{state['request']}

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
*QRALPH v3.0 - Team Orchestration*
"""

    safe_write(project_path / "SYNTHESIS.md", synthesis)

    next_phase = "EXECUTING" if state["mode"] == "coding" else "COMPLETE"
    if not validate_phase_transition(state["phase"], next_phase, state.get("mode", "coding")):
        error = {"error": f"Invalid phase transition: {state['phase']} -> {next_phase}"}
        print(json.dumps(error))
        return error

    state["findings"] = all_findings
    state["phase"] = next_phase
    save_state(state)

    log_decision(project_path,
        f"Synthesis complete: {len(all_findings['P0'])} P0, "
        f"{len(all_findings['P1'])} P1, {len(all_findings['P2'])} P2"
    )

    output = {
        "status": "synthesized",
        "project_id": state["project_id"],
        "synthesis_file": str(project_path / "SYNTHESIS.md"),
        "p0_count": len(all_findings["P0"]),
        "p1_count": len(all_findings["P1"]),
        "p2_count": len(all_findings["P2"]),
        "next_phase": state["phase"],
        "team_shutdown_needed": state["phase"] == "COMPLETE",
    }
    print(json.dumps(output, indent=2))
    return output


def extract_summary(content: str) -> str:
    match = re.search(r'## Summary\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    return match.group(1).strip() if match else "(No summary found)"


def extract_findings(content: str, priority: str) -> list:
    pattern = rf'### {priority}[^\n]*\n(.*?)(?=\n###|\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        findings_text = match.group(1)
        findings = re.findall(r'^[-*]\s*(.+)$', findings_text, re.MULTILINE)
        return [f.strip() for f in findings if f.strip() and not f.startswith('(')]
    return []


def format_findings(findings: list) -> str:
    if not findings:
        return "- None identified"
    return "\n".join(f"- **[{f['agent']}]** {f['finding']}" for f in findings)


def generate_action_plan(findings: dict) -> str:
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
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project. Run init first."}))
        return

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
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    project_path = Path(state["project_path"])
    state["phase"] = phase
    state["checkpoint_at"] = datetime.now().isoformat()
    save_state(state)

    checkpoint_file = project_path / "checkpoints" / f"{phase.lower()}-{datetime.now().strftime('%H%M%S')}.json"
    safe_write_json(checkpoint_file, state)

    log_decision(project_path, f"Checkpoint saved: {phase}")

    print(json.dumps({
        "status": "checkpointed",
        "phase": phase,
        "checkpoint_file": str(checkpoint_file),
    }))


def cmd_generate_uat():
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

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
        error = {"error": f"Invalid phase transition: {state['phase']} -> UAT"}
        print(json.dumps(error))
        return error

    state["phase"] = "UAT"
    save_state(state)
    log_decision(project_path, "UAT generated")

    print(json.dumps({
        "status": "uat_generated",
        "uat_file": str(project_path / "UAT.md"),
    }))


def cmd_finalize():
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    project_path = Path(state["project_path"])

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

## Results
- P0 Issues: {len(state.get('findings', {}).get('P0', []))}
- P1 Issues: {len(state.get('findings', {}).get('P1', []))}
- P2 Issues: {len(state.get('findings', {}).get('P2', []))}

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
*QRALPH v3.0 - Team Orchestration*
"""

    safe_write(project_path / "SUMMARY.md", summary)

    if not validate_phase_transition(state["phase"], "COMPLETE", state.get("mode", "coding")):
        error = {"error": f"Invalid phase transition: {state['phase']} -> COMPLETE"}
        print(json.dumps(error))
        return error

    state["phase"] = "COMPLETE"
    state["completed_at"] = datetime.now().isoformat()
    save_state(state)
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
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    if state.get("mode") != "work":
        print(json.dumps({"error": "work-plan only available in work mode"}))
        return

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
        error = {"error": f"Invalid phase transition: {state['phase']} -> PLANNING"}
        print(json.dumps(error))
        return error

    state["phase"] = "PLANNING"
    state["domains"] = domains
    save_state(state)
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
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    if state.get("mode") != "work":
        print(json.dumps({"error": "work-approve only available in work mode"}))
        return

    project_path = Path(state["project_path"])

    if state["phase"] == "PLANNING":
        state["phase"] = "USER_REVIEW"
        save_state(state)
        log_decision(project_path, "Plan submitted for user review")

    if state["phase"] == "USER_REVIEW":
        state["phase"] = "EXECUTING"
        save_state(state)
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
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    if state.get("mode") != "work":
        print(json.dumps({"error": "work-iterate only available in work mode"}))
        return

    project_path = Path(state["project_path"])

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
        save_state(state)
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
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    project_path = Path(state["project_path"])

    old_mode = state.get("mode", "coding")
    state["mode"] = "coding"

    # Transition to ESCALATE then REVIEWING
    if state["phase"] in ("EXECUTING", "PLANNING", "USER_REVIEW"):
        state["phase"] = "REVIEWING"
    save_state(state)
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


# ─── RESUME / STATUS ────────────────────────────────────────────────────────

def cmd_resume(project_id: str):
    matches = list(PROJECTS_DIR.glob(f"{project_id}*"))
    if not matches:
        print(json.dumps({"error": f"No project found matching: {project_id}"}))
        return

    project_path = matches[0]
    checkpoint_dir = project_path / "checkpoints"
    state_file = checkpoint_dir / "state.json"

    if state_file.exists():
        state = safe_read_json(state_file, {})
    else:
        checkpoints = sorted(checkpoint_dir.glob("*.json"))
        if checkpoints:
            state = safe_read_json(checkpoints[-1], {})
        else:
            print(json.dumps({"error": "No checkpoint found"}))
            return

    if not state:
        print(json.dumps({"error": "Failed to load state (corrupt or empty)"}))
        return

    save_state(state)
    log_decision(project_path, f"Resumed from phase: {state['phase']}")

    # Load team config for re-creation
    team_config_file = project_path / "team-config.json"
    team_config = safe_read_json(team_config_file, {})

    print(json.dumps({
        "status": "resumed",
        "project_id": state["project_id"],
        "phase": state["phase"],
        "team_name": state.get("team_name"),
        "team_config": team_config,
        "next_step": get_next_step(state["phase"]),
    }))


def cmd_status(project_id: Optional[str] = None):
    if project_id:
        matches = list(PROJECTS_DIR.glob(f"{project_id}*"))
        if matches:
            project_path = matches[0]
            state_file = project_path / "checkpoints" / "state.json"
            state = safe_read_json(state_file)
            if state:
                print(json.dumps(state, indent=2))
            else:
                print(json.dumps({"project": project_path.name, "status": "no state file"}))
        else:
            print(json.dumps({"error": f"Project not found: {project_id}"}))
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
    steps = {
        "INIT": "Run discover to scan plugins/skills, then select-agents",
        "DISCOVERING": "Run select-agents to pick team composition",
        "REVIEWING": "TeamCreate, spawn teammates, then run synthesize when complete",
        "EXECUTING": "Implement fixes, then run generate-uat",
        "UAT": "Execute UAT scenarios, then run finalize",
        "COMPLETE": "Shutdown team and review SUMMARY.md",
    }
    return steps.get(phase, "Unknown phase")


# ─── CONTROL COMMANDS ────────────────────────────────────────────────────────

def handle_control_command(command: str, state: dict, project_path: Path) -> dict:
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
    log_file = project_path / "decisions.log"
    try:
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
    except Exception as e:
        print(f"Warning: Failed to log decision: {e}", file=sys.stderr)


def notify(message: str):
    if NOTIFY_TOOL.exists():
        try:
            subprocess.run(
                ["python3", str(NOTIFY_TOOL), "--event", "complete", "--message", message],
                capture_output=True,
            )
        except Exception:
            pass


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QRALPH Orchestrator v3.0 - Team-Based")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize new project")
    init_parser.add_argument("request", help="The request to execute")
    init_parser.add_argument("--mode", choices=["coding", "planning", "work"], default="coding")

    # discover
    subparsers.add_parser("discover", help="Discover available plugins and skills")

    # select-agents
    select_parser = subparsers.add_parser("select-agents", help="Select best agents for team")
    select_parser.add_argument("--agents", help="Comma-separated agent list (override)")

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

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args.request, args.mode)
    elif args.command == "discover":
        cmd_discover()
    elif args.command == "select-agents":
        agents = args.agents.split(",") if args.agents else None
        cmd_select_agents(agents)
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
