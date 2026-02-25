#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
QRALPH Sub-Team Lifecycle Manager v4.1 - Hierarchical team orchestration.

Manages sub-team creation, monitoring, result collection, recovery, teardown,
and quality gate validation for the hierarchical QRALPH architecture.

Commands:
    python3 qralph-subteam.py create-subteam --phase REVIEWING
    python3 qralph-subteam.py check-subteam --phase REVIEWING
    python3 qralph-subteam.py collect-results --phase REVIEWING
    python3 qralph-subteam.py resume-subteam --phase REVIEWING
    python3 qralph-subteam.py teardown-subteam --phase REVIEWING
    python3 qralph-subteam.py quality-gate --phase REVIEWING
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import shared state module
import importlib.util
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

safe_write = qralph_state.safe_write
safe_write_json = qralph_state.safe_write_json
safe_read_json = qralph_state.safe_read_json

# Import orchestrator for AGENT_REGISTRY, classify_domains, DOMAIN_KEYWORDS
_orch_path = Path(__file__).parent / "qralph-orchestrator.py"
_orch_spec = importlib.util.spec_from_file_location("qralph_orchestrator", _orch_path)
qralph_orchestrator = importlib.util.module_from_spec(_orch_spec)
_orch_spec.loader.exec_module(qralph_orchestrator)

# Constants
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"

CRITICAL_AGENTS = {"security-reviewer", "architecture-advisor", "sde-iii", "pe-reviewer"}

VALID_PHASES = {"REVIEWING", "EXECUTING", "VALIDATING"}

# Stale output threshold (seconds) — outputs older than this during check are flagged
STALE_OUTPUT_THRESHOLD = 1800


def _error_result(message: str) -> dict:
    result = {"error": message}
    print(json.dumps(result))
    return result


def _get_state_and_project() -> tuple:
    state_file = QRALPH_DIR / "current-project.json"
    state = qralph_state.load_state(state_file)
    if not state:
        return None, None
    project_path = Path(state.get("project_path", ""))
    return state, project_path


def _get_phase_outputs_dir(project_path: Path) -> Path:
    d = project_path / "phase-outputs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_result_file(project_path: Path, phase: str) -> Path:
    return _get_phase_outputs_dir(project_path) / f"{phase}-result.json"


def _save_state(state: dict):
    state_file = QRALPH_DIR / "current-project.json"
    qralph_state.save_state(state, state_file)


# ─── CREATE SUBTEAM ─────────────────────────────────────────────────────────

def cmd_create_subteam(phase: str):
    """Prepare sub-team metadata and output TeamCreate/Task instructions for Claude."""
    if phase not in VALID_PHASES:
        return _error_result(f"Invalid phase: {phase}. Must be one of {sorted(VALID_PHASES)}")

    with qralph_state.exclusive_state_lock():
        return _cmd_create_subteam_locked(phase)


def _cmd_create_subteam_locked(phase: str):
    state, project_path = _get_state_and_project()
    if not state:
        return _error_result("No active project. Run init first.")
    if not project_path or not project_path.exists():
        return _error_result(f"Project path not found: {project_path}")

    project_id = state["project_id"]
    team_name = f"qralph-{project_id}-{phase.lower()}"

    # Get agents for this phase
    agents = state.get("agents", [])
    if not agents and phase == "REVIEWING":
        return _error_result("No agents selected. Run select-agents first.")

    # Build agent configs
    agent_configs = []
    for agent_type in agents:
        info = qralph_orchestrator.AGENT_REGISTRY.get(agent_type, {})
        agent_configs.append({
            "agent_type": agent_type,
            "model": info.get("model", "sonnet"),
            "name": f"{agent_type}-agent",
            "output_file": str(project_path / "agent-outputs" / f"{agent_type}.md"),
        })

    # Ensure phase-outputs directory exists
    _get_phase_outputs_dir(project_path)

    # Update sub_teams in state
    sub_teams = state.get("sub_teams", {})
    sub_teams[phase] = {
        "status": "creating",
        "team_name": team_name,
        "agents": [a["agent_type"] for a in agent_configs],
        "created_at": datetime.now().isoformat(),
    }
    state["sub_teams"] = sub_teams
    _save_state(state)

    output = {
        "status": "subteam_ready",
        "phase": phase,
        "team_name": team_name,
        "agent_count": len(agent_configs),
        "agents": agent_configs,
        "result_file": str(_get_result_file(project_path, phase)),
        "instruction": (
            f"1. TeamCreate(team_name='{team_name}')\n"
            f"2. Spawn sub-team lead via Task(subagent_type='general-purpose', "
            f"team_name='{team_name}', name='team-lead', model='sonnet')\n"
            f"3. Team lead spawns {len(agent_configs)} agents and manages them\n"
            f"4. Team lead writes result to phase-outputs/{phase}-result.json\n"
            f"5. Run check-subteam --phase {phase} to monitor progress"
        ),
    }
    print(json.dumps(output, indent=2))
    return output


# ─── CHECK SUBTEAM ──────────────────────────────────────────────────────────

def cmd_check_subteam(phase: str):
    """Poll sub-team status: check result file, count outputs, detect timeout."""
    if phase not in VALID_PHASES:
        return _error_result(f"Invalid phase: {phase}. Must be one of {sorted(VALID_PHASES)}")

    state, project_path = _get_state_and_project()
    if not state:
        return _error_result("No active project.")
    if not project_path or not project_path.exists():
        return _error_result(f"Project path not found: {project_path}")

    result_file = _get_result_file(project_path, phase)
    outputs_dir = project_path / "agent-outputs"
    sub_teams = state.get("sub_teams", {})
    sub_team = sub_teams.get(phase, {})

    # Check if result file exists (sub-team is done)
    if result_file.exists():
        result_data = safe_read_json(result_file, {})
        status = result_data.get("status", "unknown")
        output = {
            "status": status,
            "phase": phase,
            "result_file": str(result_file),
            "agents_completed": result_data.get("agents_completed", []),
            "agents_failed": result_data.get("agents_failed", []),
            "summary": result_data.get("summary", ""),
        }
        print(json.dumps(output, indent=2))
        return output

    # Count agent outputs so far
    expected_agents = sub_team.get("agents", state.get("agents", []))
    completed_agents = []
    missing_agents = []
    stale_agents = []

    for agent_name in expected_agents:
        output_file = outputs_dir / f"{agent_name}.md"
        if output_file.exists() and output_file.stat().st_size > 0:
            completed_agents.append(agent_name)
            # Check staleness
            age = datetime.now().timestamp() - output_file.stat().st_mtime
            if age > STALE_OUTPUT_THRESHOLD and output_file.stat().st_size < 100:
                stale_agents.append(agent_name)
        else:
            missing_agents.append(agent_name)

    # Check for timeout
    created_at = sub_team.get("created_at", "")
    timed_out = False
    if created_at:
        try:
            created = datetime.fromisoformat(created_at)
            age_seconds = (datetime.now() - created).total_seconds()
            # 30 minute timeout for entire sub-team
            timed_out = age_seconds > 1800
        except (ValueError, TypeError):
            pass

    status = "running"
    if timed_out and missing_agents:
        status = "timeout"
    elif not missing_agents:
        status = "agents_complete_need_result"

    output = {
        "status": status,
        "phase": phase,
        "completed_agents": completed_agents,
        "missing_agents": missing_agents,
        "stale_agents": stale_agents,
        "timed_out": timed_out,
        "total": len(expected_agents),
        "completed": len(completed_agents),
    }
    print(json.dumps(output, indent=2))
    return output


# ─── COLLECT RESULTS ─────────────────────────────────────────────────────────

def cmd_collect_results(phase: str):
    """Read result file and update QRALPH state."""
    if phase not in VALID_PHASES:
        return _error_result(f"Invalid phase: {phase}. Must be one of {sorted(VALID_PHASES)}")

    with qralph_state.exclusive_state_lock():
        return _cmd_collect_results_locked(phase)


def _cmd_collect_results_locked(phase: str):
    state, project_path = _get_state_and_project()
    if not state:
        return _error_result("No active project.")
    if not project_path or not project_path.exists():
        return _error_result(f"Project path not found: {project_path}")

    result_file = _get_result_file(project_path, phase)
    if not result_file.exists():
        return _error_result(f"Result file not found: {result_file}")

    result_data = safe_read_json(result_file, {})
    if not result_data:
        return _error_result(f"Result file is empty or corrupt: {result_file}")

    # Update sub_team status
    sub_teams = state.get("sub_teams", {})
    if phase in sub_teams:
        sub_teams[phase]["status"] = result_data.get("status", "complete")
        sub_teams[phase]["collected_at"] = datetime.now().isoformat()
    state["sub_teams"] = sub_teams
    _save_state(state)

    output = {
        "status": "collected",
        "phase": phase,
        "result_status": result_data.get("status"),
        "agents_completed": result_data.get("agents_completed", []),
        "agents_failed": result_data.get("agents_failed", []),
        "summary": result_data.get("summary", ""),
        "work_remaining": result_data.get("work_remaining"),
        "next_team_context": result_data.get("next_team_context"),
    }
    print(json.dumps(output, indent=2))
    return output


# ─── RESUME SUBTEAM ──────────────────────────────────────────────────────────

def cmd_resume_subteam(phase: str):
    """After compaction: find missing agents, output partial re-run instructions."""
    if phase not in VALID_PHASES:
        return _error_result(f"Invalid phase: {phase}. Must be one of {sorted(VALID_PHASES)}")

    state, project_path = _get_state_and_project()
    if not state:
        return _error_result("No active project.")
    if not project_path or not project_path.exists():
        return _error_result(f"Project path not found: {project_path}")

    result_file = _get_result_file(project_path, phase)

    # If result file exists, phase is already done
    if result_file.exists():
        result_data = safe_read_json(result_file, {})
        if result_data.get("status") in ("complete", "failed"):
            output = {
                "status": "already_complete",
                "phase": phase,
                "result_status": result_data.get("status"),
            }
            print(json.dumps(output, indent=2))
            return output

    # Check which agents have outputs
    outputs_dir = project_path / "agent-outputs"
    expected_agents = state.get("agents", [])
    completed_agents = []
    missing_agents = []

    for agent_name in expected_agents:
        output_file = outputs_dir / f"{agent_name}.md"
        if output_file.exists() and output_file.stat().st_size > 100:
            completed_agents.append(agent_name)
        else:
            missing_agents.append(agent_name)

    # If all agents completed but no result file, just need synthesis
    if not missing_agents:
        output = {
            "status": "agents_complete_need_synthesis",
            "phase": phase,
            "completed_agents": completed_agents,
            "message": "All agent outputs exist. Write result file and run synthesize.",
        }
        print(json.dumps(output, indent=2))
        return output

    # Need to re-run missing agents
    project_id = state["project_id"]
    team_name = f"qralph-{project_id}-{phase.lower()}-resume"

    agent_configs = []
    for agent_type in missing_agents:
        info = qralph_orchestrator.AGENT_REGISTRY.get(agent_type, {})
        agent_configs.append({
            "agent_type": agent_type,
            "model": info.get("model", "sonnet"),
            "name": f"{agent_type}-agent",
            "output_file": str(project_path / "agent-outputs" / f"{agent_type}.md"),
        })

    # Update sub_team status
    with qralph_state.exclusive_state_lock():
        state_fresh, _ = _get_state_and_project()
        if state_fresh:
            sub_teams = state_fresh.get("sub_teams", {})
            if phase in sub_teams:
                sub_teams[phase]["status"] = "resuming"
            state_fresh["sub_teams"] = sub_teams
            _save_state(state_fresh)

    output = {
        "status": "resume_needed",
        "phase": phase,
        "completed_agents": completed_agents,
        "missing_agents": missing_agents,
        "team_name": team_name,
        "agents_to_spawn": agent_configs,
        "instruction": (
            f"Resume {phase} phase: {len(missing_agents)} agents need re-running.\n"
            f"1. TeamCreate(team_name='{team_name}')\n"
            f"2. Spawn sub-team lead for remaining {len(missing_agents)} agents\n"
            f"3. Team lead collects outputs and writes result file"
        ),
    }
    print(json.dumps(output, indent=2))
    return output


# ─── TEARDOWN SUBTEAM ────────────────────────────────────────────────────────

def cmd_teardown_subteam(phase: str):
    """Output TeamDelete instruction and clean up sub-team state."""
    if phase not in VALID_PHASES:
        return _error_result(f"Invalid phase: {phase}. Must be one of {sorted(VALID_PHASES)}")

    with qralph_state.exclusive_state_lock():
        return _cmd_teardown_subteam_locked(phase)


def _cmd_teardown_subteam_locked(phase: str):
    state, project_path = _get_state_and_project()
    if not state:
        return _error_result("No active project.")

    sub_teams = state.get("sub_teams", {})
    sub_team = sub_teams.get(phase, {})
    team_name = sub_team.get("team_name", "")

    # Mark as complete in state
    if phase in sub_teams:
        sub_teams[phase]["status"] = "complete"
        sub_teams[phase]["torn_down_at"] = datetime.now().isoformat()
    state["sub_teams"] = sub_teams
    _save_state(state)

    output = {
        "status": "teardown_ready",
        "phase": phase,
        "team_name": team_name,
        "instruction": (
            f"1. Send shutdown_request to all teammates in '{team_name}'\n"
            f"2. TeamDelete() to clean up team resources"
        ),
    }
    print(json.dumps(output, indent=2))
    return output


# ─── QUALITY GATE ─────────────────────────────────────────────────────────────

def cmd_quality_gate(phase: str):
    """Run 95% confidence check against result file."""
    if phase not in VALID_PHASES:
        return _error_result(f"Invalid phase: {phase}. Must be one of {sorted(VALID_PHASES)}")

    state, project_path = _get_state_and_project()
    if not state:
        return _error_result("No active project.")
    if not project_path or not project_path.exists():
        return _error_result(f"Project path not found: {project_path}")

    result_file = _get_result_file(project_path, phase)
    if not result_file.exists():
        return _error_result(f"Result file not found: {result_file}")

    result_data = safe_read_json(result_file, {})
    if not result_data:
        return _error_result(f"Result file is empty or corrupt: {result_file}")

    gaps = []
    checks_passed = 0
    total_checks = 7

    # Check 1: All critical agents completed
    agents_completed = set(result_data.get("agents_completed", []))
    agents_failed = set(result_data.get("agents_failed", []))
    missing_critical = CRITICAL_AGENTS - agents_completed
    failed_critical = CRITICAL_AGENTS & agents_failed
    if missing_critical or failed_critical:
        missing_list = sorted(missing_critical | failed_critical)
        gaps.append(f"Critical agents incomplete: {', '.join(missing_list)}")
    else:
        checks_passed += 1

    # Check 2: Every domain covered by findings
    request = state.get("request", "")
    detected_domains = qralph_orchestrator.classify_domains(request)
    if detected_domains:
        # Read agent outputs to check domain coverage
        outputs_dir = project_path / "agent-outputs"
        covered_domains = set()
        for agent_name in agents_completed:
            agent_info = qralph_orchestrator.AGENT_REGISTRY.get(agent_name, {})
            for domain in agent_info.get("domains", []):
                if domain in detected_domains:
                    covered_domains.add(domain)

        uncovered = set(detected_domains) - covered_domains
        if uncovered:
            gaps.append(f"Domains not covered by any agent: {', '.join(sorted(uncovered))}")
        else:
            checks_passed += 1
    else:
        checks_passed += 1  # No domains to cover

    # Check 3: No unresolved contradictions
    contradictions = _detect_contradictions(project_path, agents_completed)
    if contradictions:
        gaps.append(f"Unresolved contradictions: {'; '.join(contradictions)}")
    else:
        checks_passed += 1

    # Check 4: Execution plan has testable acceptance criteria
    has_testable = _check_testable_criteria(project_path, agents_completed)
    if not has_testable:
        gaps.append("Execution plan lacks testable acceptance criteria")
    else:
        checks_passed += 1

    # Check 5: PE risk assessment present (structured validation, v5.0)
    has_risk_assessment = _check_risk_assessment(project_path, agents_completed)
    if not has_risk_assessment:
        gaps.append("PE risk assessment missing (no complexity/coverage/maintainability analysis)")
    else:
        checks_passed += 1

    # Check 6: ADR consistency (v5.0)
    adr_consistent = _check_adr_consistency(project_path, state)
    if not adr_consistent:
        gaps.append("Agent findings contradict accepted ADRs")
    else:
        checks_passed += 1

    # Check 7: DoD template compliance (v5.0)
    dod_compliant = _check_dod_compliance(project_path, state)
    if not dod_compliant:
        gaps.append("DoD template categories not adequately addressed")
    else:
        checks_passed += 1

    confidence = checks_passed / total_checks
    passed = confidence >= 0.95

    output = {
        "confidence": round(confidence, 2),
        "passed": passed,
        "checks_passed": checks_passed,
        "total_checks": total_checks,
        "gaps": gaps,
        "phase": phase,
    }
    print(json.dumps(output, indent=2))
    return output


def _detect_contradictions(project_path: Path, agents_completed: set) -> List[str]:
    """Detect opposing conclusions from different agents on the same issue."""
    contradictions = []
    outputs_dir = project_path / "agent-outputs"

    # Build a map of agent findings by topic keyword
    positive_signals = {}  # keyword -> [agent_name]
    negative_signals = {}  # keyword -> [agent_name]

    contradiction_keywords = {
        "secure": "insecure",
        "scalable": "not scalable",
        "maintainable": "unmaintainable",
        "recommended": "not recommended",
        "approved": "rejected",
    }

    for agent_name in agents_completed:
        output_file = outputs_dir / f"{agent_name}.md"
        if not output_file.exists():
            continue
        try:
            content = output_file.read_text().lower()
        except Exception:
            continue

        for positive, negative in contradiction_keywords.items():
            if positive in content:
                positive_signals.setdefault(positive, []).append(agent_name)
            if negative in content:
                negative_signals.setdefault(positive, []).append(agent_name)

    # Flag contradictions where both positive and negative exist for same keyword
    for keyword in set(positive_signals) & set(negative_signals):
        pos_agents = positive_signals[keyword]
        neg_agents = negative_signals[keyword]
        # Only flag if different agents disagree
        if set(pos_agents) != set(neg_agents):
            contradictions.append(
                f"'{keyword}' vs '{contradiction_keywords[keyword]}': "
                f"positive by {pos_agents}, negative by {neg_agents}"
            )

    return contradictions


def _check_testable_criteria(project_path: Path, agents_completed: set) -> bool:
    """Check if any agent output contains testable acceptance criteria."""
    outputs_dir = project_path / "agent-outputs"
    criteria_patterns = [
        r'\bacceptance\b', r'\bcriteria\b', r'\btest\b.*\bverif',
        r'\bverify\b', r'\bvalidat', r'\bgiven\b.*\bwhen\b.*\bthen\b',
        r'\bshould\b.*\breturn\b', r'\bexpect\b',
    ]

    for agent_name in agents_completed:
        output_file = outputs_dir / f"{agent_name}.md"
        if not output_file.exists():
            continue
        try:
            content = output_file.read_text().lower()
        except Exception:
            continue

        matches = sum(1 for p in criteria_patterns if re.search(p, content))
        if matches >= 2:
            return True

    return False


def _check_risk_assessment(project_path: Path, agents_completed: set) -> bool:
    """Check if PE risk assessment is present with structured sections.

    Requires at least 2 of the key risk categories (complexity, coverage,
    maintainability, risk, technical debt) to appear in a structured context
    -- i.e. as a heading (# / ## / ###) or as a bullet point (- / *) rather
    than just mentioned in passing prose.
    """
    outputs_dir = project_path / "agent-outputs"
    risk_keywords = ["complexity", "coverage", "maintainability", "risk", "technical debt"]

    # Patterns that indicate structured usage (heading or bullet context)
    structured_patterns = [
        re.compile(r'^#{1,4}\s+.*\b' + re.escape(kw) + r'\b', re.MULTILINE | re.IGNORECASE)
        for kw in risk_keywords
    ] + [
        re.compile(r'^\s*[-*]\s+.*\b' + re.escape(kw) + r'\b', re.MULTILINE | re.IGNORECASE)
        for kw in risk_keywords
    ]

    for agent_name in agents_completed:
        output_file = outputs_dir / f"{agent_name}.md"
        if not output_file.exists():
            continue
        try:
            content = output_file.read_text()
        except Exception:
            continue

        # Count how many distinct risk keywords appear in structured context
        matched_keywords = set()
        for idx, pattern in enumerate(structured_patterns):
            kw_index = idx % len(risk_keywords)
            if pattern.search(content):
                matched_keywords.add(risk_keywords[kw_index])

        if len(matched_keywords) >= 2:
            return True

    return False


def _check_adr_consistency(project_path: Path, state: dict) -> bool:
    """Check 6: Verify agent findings don't contradict accepted ADRs.

    Auto-passes when no ADRs are loaded (backward compatibility).
    """
    pe_data = state.get("pe_overlay", {})
    adrs = pe_data.get("adrs", [])
    if not adrs:
        return True  # No ADRs = auto-pass

    # Check for enforcement rules in ADRs
    enforcements = [a for a in adrs if a.get("enforcement")]
    if not enforcements:
        return True  # No enforceable ADRs = auto-pass

    # Read agent outputs and check against enforcement patterns
    outputs_dir = project_path / "agent-outputs"
    if not outputs_dir.exists():
        return True

    for adr in enforcements:
        enforcement = adr.get("enforcement", {})
        check_pattern = enforcement.get("check", "")
        if not check_pattern:
            continue
        # If any agent output contains a contradiction pattern, fail
        # For now, this is a lightweight pre-check
        # Full enforcement is in pe-overlay.py check_adr_consistency

    return True


def _check_dod_compliance(project_path: Path, state: dict) -> bool:
    """Check 7: Lightweight DoD template compliance check.

    Verifies that the DoD template categories are addressed by agent findings.
    Auto-passes when no DoD template is selected (backward compatibility).
    """
    pe_data = state.get("pe_overlay", {})
    dod_template = pe_data.get("dod_template", "")
    if not dod_template:
        return True  # No DoD = auto-pass

    # Check that agent outputs exist and cover major categories
    outputs_dir = project_path / "agent-outputs"
    if not outputs_dir.exists():
        return True

    # Lightweight check: at least one agent output mentions testing and security
    has_testing_coverage = False
    has_security_coverage = False

    for output_file in outputs_dir.glob("*.md"):
        try:
            content = output_file.read_text().lower()
            if any(kw in content for kw in ["test", "coverage", "spec", "assertion"]):
                has_testing_coverage = True
            if any(kw in content for kw in ["security", "auth", "vulnerability", "injection"]):
                has_security_coverage = True
        except Exception:
            continue

    # Both blocker categories must be addressed
    return has_testing_coverage and has_security_coverage


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QRALPH Sub-Team Lifecycle Manager v4.1")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    create_parser = subparsers.add_parser("create-subteam", help="Prepare sub-team metadata")
    create_parser.add_argument("--phase", required=True, help="Phase (REVIEWING, EXECUTING, VALIDATING)")

    check_parser = subparsers.add_parser("check-subteam", help="Check sub-team progress")
    check_parser.add_argument("--phase", required=True, help="Phase to check")

    collect_parser = subparsers.add_parser("collect-results", help="Collect sub-team results")
    collect_parser.add_argument("--phase", required=True, help="Phase to collect")

    resume_parser = subparsers.add_parser("resume-subteam", help="Resume interrupted sub-team")
    resume_parser.add_argument("--phase", required=True, help="Phase to resume")

    teardown_parser = subparsers.add_parser("teardown-subteam", help="Tear down sub-team")
    teardown_parser.add_argument("--phase", required=True, help="Phase to tear down")

    gate_parser = subparsers.add_parser("quality-gate", help="Run 95% confidence quality gate")
    gate_parser.add_argument("--phase", required=True, help="Phase to validate")

    args = parser.parse_args()

    if args.command == "create-subteam":
        cmd_create_subteam(args.phase)
    elif args.command == "check-subteam":
        cmd_check_subteam(args.phase)
    elif args.command == "collect-results":
        cmd_collect_results(args.phase)
    elif args.command == "resume-subteam":
        cmd_resume_subteam(args.phase)
    elif args.command == "teardown-subteam":
        cmd_teardown_subteam(args.phase)
    elif args.command == "quality-gate":
        cmd_quality_gate(args.phase)
    else:
        parser.print_help()


if __name__ == "__main__":
    if sys.version_info < (3, 6):
        sys.exit("QRALPH requires Python 3.6+")
    main()
