#!/usr/bin/env python3
"""
QRALPH Watchdog - Health checks, agent monitoring, and phase precondition validation.

Commands:
    python3 qralph-watchdog.py check                         # Run all health checks
    python3 qralph-watchdog.py check-agents                  # Check agent execution status
    python3 qralph-watchdog.py check-state                   # Validate state integrity
    python3 qralph-watchdog.py check-preconditions <phase>   # Pre-transition validation
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import shared state module
import importlib.util
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

safe_read_json = qralph_state.safe_read_json

# Constants
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
CURRENT_PROJECT_FILE = QRALPH_DIR / "current-project.json"

# Configurable agent timeouts (seconds)
AGENT_TIMEOUTS = {
    "haiku": 120,
    "sonnet": 300,
    "opus": 600,
    "default": 300,
}

# Agent criticality levels
CRITICAL_AGENTS = {"security-reviewer", "architecture-advisor", "sde-iii"}
NON_CRITICAL_AGENTS = {"docs-writer", "code-quality-auditor"}

# Escalation path for stuck agents
ESCALATION_STEPS = ["timeout", "retry_once", "skip_if_non_critical", "defer", "alert_user"]

# Phase preconditions
PHASE_PRECONDITIONS = {
    "DISCOVERING": ["project_path_exists", "request_non_empty"],
    "REVIEWING": ["discovery_results_exist", "at_least_one_capability"],
    "EXECUTING": ["synthesis_exists"],
    "UAT": ["execution_artifacts_exist"],
    "COMPLETE": ["uat_exists"],
}


def _get_project_path(state: dict) -> Optional[Path]:
    """Get project path from state."""
    path_str = state.get("project_path", "")
    if path_str:
        path = Path(path_str)
        return path if path.exists() else None
    return None


def check_agent_health(state: dict, project_path: Path) -> List[Dict[str, Any]]:
    """
    Check health of each agent's output.

    For each agent, checks:
    - Output file exists
    - Modification time vs timeout
    - File size (empty = failed silently)
    """
    issues = []
    agents = state.get("agents", [])
    outputs_dir = project_path / "agent-outputs"

    if not outputs_dir.exists():
        issues.append({
            "level": "error",
            "agent": "all",
            "message": "agent-outputs directory missing",
        })
        return issues

    for agent_name in agents:
        output_file = outputs_dir / f"{agent_name}.md"

        if not output_file.exists():
            issues.append({
                "level": "warning",
                "agent": agent_name,
                "message": "Output file not found (agent may still be running)",
            })
            continue

        # Check file size
        file_size = output_file.stat().st_size
        if file_size == 0:
            criticality = "critical" if agent_name in CRITICAL_AGENTS else "warning"
            issues.append({
                "level": criticality,
                "agent": agent_name,
                "message": "Output file is empty (agent failed silently)",
                "action": "retry" if agent_name in CRITICAL_AGENTS else "skip",
            })
            continue

        # Check modification time
        mtime = output_file.stat().st_mtime
        age_seconds = (datetime.now().timestamp() - mtime)

        # Determine timeout based on agent's model tier
        from importlib.util import spec_from_file_location, module_from_spec
        orch_path = Path(__file__).parent / "qralph-orchestrator.py"
        orch_spec = spec_from_file_location("qralph_orchestrator_wd", orch_path)
        orch_mod = module_from_spec(orch_spec)
        orch_spec.loader.exec_module(orch_mod)
        agent_info = orch_mod.AGENT_REGISTRY.get(agent_name, {})
        model = agent_info.get("model", "default")
        timeout = AGENT_TIMEOUTS.get(model, AGENT_TIMEOUTS["default"])

        if age_seconds > timeout and file_size < 100:
            issues.append({
                "level": "warning",
                "agent": agent_name,
                "message": f"Output appears stale ({age_seconds:.0f}s old, {file_size} bytes)",
                "timeout": timeout,
            })

    return issues


def check_state_integrity(state: dict, project_path: Path) -> List[Dict[str, Any]]:
    """
    Validate state consistency against filesystem.

    Checks:
    - project_path exists
    - project_id matches directory name
    - phase is valid
    - agents match files in agent-outputs/
    - circuit_breakers are non-negative
    - created_at is valid ISO timestamp
    """
    issues = []

    # Check project_path exists
    if not project_path.exists():
        issues.append({
            "level": "critical",
            "check": "project_path",
            "message": f"Project directory does not exist: {project_path}",
        })
        return issues  # Can't do further checks

    # Check project_id matches directory
    project_id = state.get("project_id", "")
    if project_id and project_path.name != project_id:
        issues.append({
            "level": "warning",
            "check": "project_id",
            "message": f"project_id '{project_id}' doesn't match directory '{project_path.name}'",
        })

    # Check phase validity
    phase = state.get("phase", "")
    valid_phases = {"INIT", "DISCOVERING", "REVIEWING", "EXECUTING", "UAT", "COMPLETE",
                    "PLANNING", "USER_REVIEW", "ESCALATE"}
    if phase and phase not in valid_phases:
        issues.append({
            "level": "error",
            "check": "phase",
            "message": f"Unknown phase: {phase}",
        })

    # Check agents match output files
    agents = state.get("agents", [])
    outputs_dir = project_path / "agent-outputs"
    if outputs_dir.exists():
        output_files = {f.stem for f in outputs_dir.glob("*.md")}
        agent_set = set(agents)
        orphan_outputs = output_files - agent_set
        if orphan_outputs:
            issues.append({
                "level": "info",
                "check": "agent_outputs",
                "message": f"Orphan output files (not in agents list): {orphan_outputs}",
            })

    # Check circuit_breakers non-negative
    cb = state.get("circuit_breakers", {})
    if isinstance(cb, dict):
        if cb.get("total_tokens", 0) < 0:
            issues.append({
                "level": "error",
                "check": "circuit_breakers",
                "message": "total_tokens is negative",
            })
        if cb.get("total_cost_usd", 0.0) < 0:
            issues.append({
                "level": "error",
                "check": "circuit_breakers",
                "message": "total_cost_usd is negative",
            })

    # Check created_at timestamp
    created_at = state.get("created_at", "")
    if created_at:
        try:
            datetime.fromisoformat(created_at)
        except (ValueError, TypeError):
            issues.append({
                "level": "warning",
                "check": "created_at",
                "message": f"Invalid ISO timestamp: {created_at}",
            })

    return issues


def check_phase_preconditions(phase: str, state: dict, project_path: Path) -> List[Dict[str, Any]]:
    """
    Check preconditions before a phase transition.

    Returns list of unmet preconditions.
    """
    issues = []
    preconditions = PHASE_PRECONDITIONS.get(phase, [])

    for precond in preconditions:
        if precond == "project_path_exists":
            if not project_path.exists():
                issues.append({
                    "precondition": precond,
                    "met": False,
                    "message": "Project directory does not exist",
                })

        elif precond == "request_non_empty":
            request = state.get("request", "")
            if not request or not request.strip():
                issues.append({
                    "precondition": precond,
                    "met": False,
                    "message": "Request is empty",
                })

        elif precond == "discovery_results_exist":
            discovery_file = project_path / "discovered-plugins.json"
            if not discovery_file.exists():
                issues.append({
                    "precondition": precond,
                    "met": False,
                    "message": "Discovery results file not found",
                })

        elif precond == "at_least_one_capability":
            domains = state.get("domains", [])
            if not domains:
                issues.append({
                    "precondition": precond,
                    "met": False,
                    "message": "No relevant domains/capabilities detected",
                })

        elif precond == "synthesis_exists":
            if not (project_path / "SYNTHESIS.md").exists():
                issues.append({
                    "precondition": precond,
                    "met": False,
                    "message": "SYNTHESIS.md not found",
                })

        elif precond == "execution_artifacts_exist":
            # Check for agent outputs or implementation artifacts
            outputs_dir = project_path / "agent-outputs"
            if not outputs_dir.exists() or not list(outputs_dir.glob("*.md")):
                issues.append({
                    "precondition": precond,
                    "met": False,
                    "message": "No execution artifacts found in agent-outputs/",
                })

        elif precond == "uat_exists":
            if not (project_path / "UAT.md").exists():
                issues.append({
                    "precondition": precond,
                    "met": False,
                    "message": "UAT.md not found",
                })

    return issues


def get_escalation_action(agent_name: str, issue: dict) -> str:
    """Determine escalation action for a stuck/failed agent."""
    if agent_name in CRITICAL_AGENTS:
        return "retry_then_alert"
    elif agent_name in NON_CRITICAL_AGENTS:
        return "skip"
    else:
        return "retry_once"


def cmd_check():
    """Run all health checks."""
    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    if not state:
        print(json.dumps({"error": "No active project"}))
        return

    project_path = _get_project_path(state)
    if not project_path:
        print(json.dumps({"error": "Project path not found"}))
        return

    agent_issues = check_agent_health(state, project_path)
    state_issues = check_state_integrity(state, project_path)

    all_issues = agent_issues + state_issues
    critical_count = sum(1 for i in all_issues if i.get("level") == "critical")
    error_count = sum(1 for i in all_issues if i.get("level") == "error")

    output = {
        "status": "healthy" if not critical_count else "unhealthy",
        "project_id": state.get("project_id"),
        "phase": state.get("phase"),
        "critical_issues": critical_count,
        "error_issues": error_count,
        "warning_issues": sum(1 for i in all_issues if i.get("level") == "warning"),
        "issues": all_issues,
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_check_agents():
    """Check agent execution status."""
    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    if not state:
        print(json.dumps({"error": "No active project"}))
        return

    project_path = _get_project_path(state)
    if not project_path:
        print(json.dumps({"error": "Project path not found"}))
        return

    issues = check_agent_health(state, project_path)

    # Build agent status summary
    agents = state.get("agents", [])
    outputs_dir = project_path / "agent-outputs"
    agent_statuses = []
    for agent in agents:
        output_file = outputs_dir / f"{agent}.md" if outputs_dir.exists() else None
        status = "pending"
        size = 0
        if output_file and output_file.exists():
            size = output_file.stat().st_size
            status = "complete" if size > 100 else ("empty" if size == 0 else "partial")

        agent_statuses.append({
            "agent": agent,
            "status": status,
            "output_size": size,
            "critical": agent in CRITICAL_AGENTS,
        })

    output = {
        "status": "checked",
        "agents": agent_statuses,
        "issues": issues,
        "total_agents": len(agents),
        "complete": sum(1 for a in agent_statuses if a["status"] == "complete"),
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_check_state():
    """Validate state integrity."""
    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    if not state:
        print(json.dumps({"error": "No active project"}))
        return

    project_path = _get_project_path(state)
    if not project_path:
        # State says project exists but it doesn't
        output = {
            "status": "corrupt",
            "issues": [{"level": "critical", "check": "project_path",
                        "message": f"Project path does not exist: {state.get('project_path')}"}],
        }
        print(json.dumps(output, indent=2))
        return output

    issues = check_state_integrity(state, project_path)

    # Also run validation from shared state module
    validation_errors = qralph_state.validate_state(state)
    for err in validation_errors:
        issues.append({"level": "error", "check": "schema_validation", "message": err})

    output = {
        "status": "valid" if not issues else "issues_found",
        "project_id": state.get("project_id"),
        "issues": issues,
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_check_preconditions(phase: str):
    """Check preconditions for a phase transition."""
    state = safe_read_json(CURRENT_PROJECT_FILE, {})
    if not state:
        print(json.dumps({"error": "No active project"}))
        return

    project_path = _get_project_path(state)
    if not project_path:
        print(json.dumps({"error": "Project path not found"}))
        return

    unmet = check_phase_preconditions(phase, state, project_path)
    can_proceed = len(unmet) == 0

    output = {
        "status": "ready" if can_proceed else "blocked",
        "target_phase": phase,
        "current_phase": state.get("phase"),
        "can_proceed": can_proceed,
        "unmet_preconditions": unmet,
    }
    print(json.dumps(output, indent=2))
    return output


def main():
    parser = argparse.ArgumentParser(description="QRALPH Watchdog")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("check", help="Run all health checks")
    subparsers.add_parser("check-agents", help="Check agent execution status")
    subparsers.add_parser("check-state", help="Validate state integrity")

    precond_parser = subparsers.add_parser("check-preconditions", help="Check phase preconditions")
    precond_parser.add_argument("phase", help="Target phase")

    args = parser.parse_args()

    if args.command == "check":
        cmd_check()
    elif args.command == "check-agents":
        cmd_check_agents()
    elif args.command == "check-state":
        cmd_check_state()
    elif args.command == "check-preconditions":
        cmd_check_preconditions(args.phase)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
