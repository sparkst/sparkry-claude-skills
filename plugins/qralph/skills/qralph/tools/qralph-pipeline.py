#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
QRALPH v6.1 Pipeline — deterministic multi-agent orchestration.

3-phase pipeline: PLAN → EXECUTE → VERIFY
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

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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

PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
PROJECTS_DIR = QRALPH_DIR / "projects"
STATE_FILE = QRALPH_DIR / "current-project.json"

# Pipeline phases
PHASES = ["PLAN", "EXECUTE", "VERIFY", "COMPLETE"]

# Max concurrent worktree agents
MAX_PARALLEL_AGENTS = 4

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


def suggest_template(request: str) -> tuple[str, dict[str, int]]:
    """Suggest a template based on keyword matching. Returns (template_name, scores)."""
    request_lower = request.lower()
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


def generate_plan_agent_prompt(agent_type: str, request: str, project_path: str, config: dict) -> dict:
    """Generate a deterministic prompt for a plan-phase agent."""
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


def detect_quality_gate() -> str:
    """Detect project test infrastructure and return quality gate command."""
    pkg_json = PROJECT_ROOT / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            parts = []
            if "typecheck" in scripts:
                parts.append("npm run typecheck")
            if "lint" in scripts:
                parts.append("npm run lint")
            if "test" in scripts:
                parts.append("npm run test")
            if parts:
                return " && ".join(parts)
        except (json.JSONDecodeError, OSError):
            pass

    if (PROJECT_ROOT / "pytest.ini").exists() or (PROJECT_ROOT / "pyproject.toml").exists():
        return "python3 -m pytest"

    if (PROJECT_ROOT / "Cargo.toml").exists():
        return "cargo test"

    if (PROJECT_ROOT / "go.mod").exists():
        return "go test ./..."

    if (PROJECT_ROOT / "Makefile").exists():
        return "make test"

    return ""


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

    # Create project directories
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "agent-outputs").mkdir(exist_ok=True)
    (project_path / "execution-outputs").mkdir(exist_ok=True)
    (project_path / "verification").mkdir(exist_ok=True)
    (project_path / "checkpoints").mkdir(exist_ok=True)

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
        "pipeline_version": "6.1.0",
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


# ─── Pipeline Commands ───────────────────────────────────────────────────────

def cmd_plan(request: str, target_dir: Optional[str] = None) -> dict:
    """Initialize project, suggest template, generate plan agent configs."""
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

    # Suggest template
    suggested, scores = suggest_template(request)
    template = TASK_TEMPLATES[suggested]

    # Generate agent configs — enforce critical agents are always present
    plan_agent_types = _enforce_critical_agents(template["plan_agents"])
    agents = []
    for agent_type in plan_agent_types:
        agent_config = generate_plan_agent_prompt(agent_type, request, str(project_path), config)
        agents.append(agent_config)

    # Update state with agent names and pipeline sub-phase
    state["agents"] = [a["name"] for a in agents]
    state["template"] = suggested
    state["pipeline"] = {
        "sub_phase": "INIT",
        "plan_agents": agents,
        "execution_groups": [],
        "current_group_index": 0,
    }
    with qralph_state.exclusive_state_lock():
        qralph_state.save_state(state)

    _save_checkpoint(project_path, state)
    _log_decision(project_path, f"PLAN: Template '{suggested}' suggested (scores: {scores})")

    return {
        "status": "plan_ready",
        "project_id": state["project_id"],
        "project_path": str(project_path),
        "suggested_template": suggested,
        "template_description": template["description"],
        "all_templates": {k: v["description"] for k, v in TASK_TEMPLATES.items()},
        "scores": scores,
        "agents": agents,
        "research_config": config.get("research_tools", {}),
    }


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
        "quality_gate_cmd": quality_gate,
        "created_at": datetime.now().isoformat(),
    }

    # Write agent analyses summary for Claude to parse
    analyses_summary = "## Agent Analyses\n\n"
    for name, content in agent_analyses.items():
        analyses_summary += f"### {name}\n\n{content}\n\n---\n\n"

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

    project_path = Path(state["project_path"])
    manifest_path = project_path / "manifest.json"

    if not manifest_path.exists():
        return {"error": "No manifest.json found. Run plan-collect first."}

    manifest = qralph_state.safe_read_json(manifest_path, {})
    tasks = manifest.get("tasks", [])

    if not tasks:
        return {"error": "No tasks defined in manifest.json. Define tasks before finalizing."}

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

    project_path = Path(state["project_path"])
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
                "name": f"impl-{tid}",
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

    return prompt


def cmd_execute_collect() -> dict:
    """Read execution-outputs/, check completeness."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project."}

    if state.get("phase") != "EXECUTE":
        return {"error": f"Cannot execute-collect in phase {state.get('phase')}. Must be in EXECUTE."}

    project_path = Path(state["project_path"])
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

    project_path = Path(state["project_path"])
    manifest_path = project_path / "manifest.json"
    manifest = qralph_state.safe_read_json(manifest_path, {})

    # Gather changed files from execution outputs
    outputs_dir = project_path / "execution-outputs"
    execution_results = ""
    if outputs_dir.exists():
        for f in sorted(outputs_dir.glob("*.md")):
            execution_results += f"### {f.stem}\n\n{_sanitize_agent_output(f.read_text().strip())}\n\n---\n\n"

    # Build acceptance criteria summary
    criteria = []
    for task in manifest.get("tasks", []):
        for ac in task.get("acceptance_criteria", []):
            criteria.append(f"- [{task['id']}] {ac}")

    criteria_text = "\n".join(criteria) if criteria else "No acceptance criteria defined."
    quality_gate = manifest.get("quality_gate_cmd", "")

    working_dir = manifest.get("target_directory", state.get("target_directory", str(PROJECT_ROOT)))
    prompt = (
        f"You are a fresh-context verification agent. You have NO knowledge of how "
        f"the implementation was done. Your job is to independently verify the work.\n\n"
        f"## Working Directory\n"
        f"The project codebase is at: {working_dir}\n"
        f"Read files from this directory to verify the implementation.\n\n"
        f"## Original Request\n{manifest.get('request', state.get('request', ''))}\n\n"
        f"## Acceptance Criteria\n{criteria_text}\n\n"
        f"## What Was Reported Done\n{execution_results}\n\n"
    )

    if quality_gate:
        prompt += f"## Quality Gate\nRun: `{quality_gate}`\n\n"

    prompt += (
        "## Your Job\n"
        "1. Read the changed files directly from the codebase\n"
        "2. For each acceptance criterion, verify it is actually met (not just claimed)\n"
        "3. Run the quality gate command\n"
        "4. Report your verdict:\n\n"
        "```json\n"
        '{"verdict": "PASS" or "FAIL", "criteria_results": [{"criterion": "...", "status": "pass/fail", "evidence": "..."}], "quality_gate": "pass/fail", "issues": ["..."]}\n'
        "```\n"
    )

    _log_decision(project_path, "VERIFY: Verification agent prepared")

    return {
        "status": "verify_ready",
        "project_id": state["project_id"],
        "agent": {
            "name": "verifier",
            "model": "sonnet",
            "prompt": prompt,
        },
    }


def cmd_finalize() -> dict:
    """Write SUMMARY.md, mark COMPLETE."""
    state = qralph_state.load_state()
    if not state:
        return {"error": "No active project."}

    if state.get("phase") != "VERIFY":
        return {"error": f"Cannot finalize in phase {state.get('phase')}. Must be in VERIFY."}

    project_path = Path(state["project_path"])

    # Check verification result exists
    verify_result = project_path / "verification" / "result.md"
    if not verify_result.exists():
        return {"error": "No verification result. Write verification output to verification/result.md first."}

    verification_content = verify_result.read_text().strip()

    # Check for FAIL verdict
    if re.search(r'"verdict"\s*:\s*"FAIL"', verification_content, re.IGNORECASE):
        return {
            "error": "Verification FAILED. Review verification/result.md before finalizing.",
            "verification_path": str(verify_result),
        }

    # Read manifest for summary
    manifest = qralph_state.safe_read_json(project_path / "manifest.json", {})

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

    # Verification
    summary += f"## Verification\n\n{verification_content}\n\n"

    # Quality gate
    if manifest.get("quality_gate_cmd"):
        summary += f"## Quality Gate\n\n```\n{manifest['quality_gate_cmd']}\n```\n"

    summary_path = project_path / "SUMMARY.md"
    qralph_state.safe_write(summary_path, summary)

    # Mark COMPLETE
    with qralph_state.exclusive_state_lock():
        state = qralph_state.load_state()
        state["phase"] = "COMPLETE"
        state["completed_at"] = datetime.now().isoformat()
        qralph_state.save_state(state)

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

    project_path = Path(state["project_path"])
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


def cmd_status() -> dict:
    """Return current project state."""
    state = qralph_state.load_state()
    if not state:
        return {"status": "no_active_project"}

    project_path = Path(state["project_path"])

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
    "INIT", "PLAN_WAITING", "PLAN_REVIEW",
    "EXEC_WAITING", "VERIFY_WAIT", "COMPLETE",
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

    if sub_phase == "INIT":
        return _next_init(state, pipeline, project_path, confirm)
    elif sub_phase == "PLAN_WAITING":
        return _next_plan_waiting(state, pipeline, project_path)
    elif sub_phase == "PLAN_REVIEW":
        return _next_plan_review(state, pipeline, project_path, confirm)
    elif sub_phase == "EXEC_WAITING":
        return _next_exec_waiting(state, pipeline, project_path)
    elif sub_phase == "VERIFY_WAIT":
        return _next_verify_wait(state, pipeline, project_path)
    elif sub_phase == "COMPLETE":
        return {"action": "complete", "summary_path": str(project_path / "SUMMARY.md")}
    else:
        return {"action": "error", "message": f"Unknown sub_phase: {sub_phase}"}


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
        return {
            "action": "confirm_template",
            "template": state.get("template", ""),
            "template_description": TASK_TEMPLATES.get(state.get("template", ""), {}).get("description", ""),
            "agents": [{"name": a["name"], "model": a["model"]} for a in agents],
            "project_path": str(project_path),
        }

    # --confirm: advance to PLAN_WAITING, return spawn_agents
    pipeline["sub_phase"] = "PLAN_WAITING"
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
    for name in expected:
        output_file = outputs_dir / f"{name}.md"
        if not output_file.exists() or not output_file.read_text().strip():
            missing.append(name)

    if missing:
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
        return {
            "action": "confirm_plan",
            "plan_path": str(plan_path),
            "manifest_path": str(manifest_path),
            "tasks": [{"id": t["id"], "summary": t.get("summary", "")} for t in tasks],
        }

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
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, f"NEXT: Plan finalized, {len(groups)} execution groups ready")

    first_group = groups[0]
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
        output_file = outputs_dir / f"{tid}.md"
        if not output_file.exists() or not output_file.read_text().strip():
            missing.append(tid)

    if missing:
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
        _save_pipeline_state(state, pipeline, project_path)
        _log_decision(project_path, f"NEXT: Group {idx + 1}/{len(groups)} complete, spawning group {next_idx + 1}")

        next_group = groups[next_idx]
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

    # Run quality gate BEFORE verification — pipeline enforces this
    manifest = qralph_state.safe_read_json(project_path / "manifest.json", {})
    quality_gate_cmd = manifest.get("quality_gate_cmd", "")
    if quality_gate_cmd:
        working_dir = manifest.get("target_directory", str(PROJECT_ROOT))
        _log_decision(project_path, f"QUALITY-GATE: Running '{quality_gate_cmd}' in {working_dir}")
        try:
            gate_result = subprocess.run(
                quality_gate_cmd, shell=True, cwd=working_dir,
                capture_output=True, text=True, timeout=120,
            )
            gate_passed = gate_result.returncode == 0
            gate_output = (gate_result.stdout + gate_result.stderr)[-2000:]  # last 2000 chars
            _log_decision(project_path, f"QUALITY-GATE: {'PASSED' if gate_passed else 'FAILED'} (exit {gate_result.returncode})")
            if not gate_passed:
                return {
                    "action": "error",
                    "message": f"Quality gate FAILED (exit {gate_result.returncode}). Fix issues before verification.",
                    "quality_gate_cmd": quality_gate_cmd,
                    "quality_gate_output": gate_output,
                }
        except subprocess.TimeoutExpired:
            _log_decision(project_path, "QUALITY-GATE: TIMEOUT (120s)")
            return {"action": "error", "message": "Quality gate timed out after 120s."}
        except OSError as e:
            _log_decision(project_path, f"QUALITY-GATE: OS ERROR — {e}")
            return {"action": "error", "message": f"Quality gate command failed: {e}"}

    # Auto-run verify to get verifier config
    verify_result = cmd_verify()
    if "error" in verify_result:
        return {"action": "error", "message": verify_result["error"]}

    # Reload state — cmd_execute_collect/cmd_verify modified it on disk
    state = qralph_state.load_state()
    pipeline = state.get("pipeline", {})
    pipeline["sub_phase"] = "VERIFY_WAIT"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "NEXT: All execution groups complete, spawning verifier")

    verifier = verify_result.get("agent", {})
    return {
        "action": "spawn_agents",
        "agents": [verifier],
        "output_dir": str(project_path / "verification"),
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

    # Parse verdict — block finalize on FAIL
    verification_content = verify_file.read_text().strip()
    fail_match = re.search(r'"verdict"\s*:\s*"FAIL"', verification_content, re.IGNORECASE)
    if fail_match:
        _log_decision(project_path, "VERIFY: Verdict is FAIL — blocking finalize")
        return {
            "action": "error",
            "message": "Verification verdict is FAIL. Fix issues and re-run verification.",
            "verification_path": str(verify_file),
        }

    # Require explicit PASS verdict — don't accept ambiguous output
    pass_match = re.search(r'"verdict"\s*:\s*"PASS"', verification_content, re.IGNORECASE)
    if not pass_match:
        _log_decision(project_path, "VERIFY: No PASS/FAIL verdict found — blocking finalize")
        return {
            "action": "error",
            "message": "Verification output has no clear verdict. Must contain '\"verdict\": \"PASS\"' to proceed.",
            "verification_path": str(verify_file),
        }

    _log_decision(project_path, "VERIFY: Verdict is PASS — proceeding to finalize")

    # Auto-run finalize
    finalize_result = cmd_finalize()
    if "error" in finalize_result:
        return {"action": "error", "message": finalize_result["error"]}

    # Reload state — cmd_finalize modified it on disk
    state = qralph_state.load_state()
    pipeline = state.get("pipeline", {})
    pipeline["sub_phase"] = "COMPLETE"
    _save_pipeline_state(state, pipeline, project_path)
    _log_decision(project_path, "NEXT: Verification complete, project finalized")

    return {
        "action": "complete",
        "summary_path": finalize_result.get("summary_path", str(project_path / "SUMMARY.md")),
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QRALPH v6.1 Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    plan_parser = subparsers.add_parser("plan", help="Init project and generate plan agent configs")
    plan_parser.add_argument("request", help="The user's request")
    plan_parser.add_argument("--target-dir", dest="target_dir", default=None, help="Directory for implementation files (relative to PROJECT_ROOT or absolute)")
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
        "plan": lambda: cmd_plan(args.request, target_dir=args.target_dir) if not args.dry_run else _dry_run_plan(args.request),
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
