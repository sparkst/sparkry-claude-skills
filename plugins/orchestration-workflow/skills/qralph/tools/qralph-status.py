#!/usr/bin/env python3
"""
QRALPH Status Monitor

Displays real-time status of QRALPH orchestration projects.

Usage:
    python3 qralph-status.py                  # List all projects
    python3 qralph-status.py <project-id>     # Detailed status for one project
    python3 qralph-status.py --watch          # Watch mode (refresh every 5s)
    python3 qralph-status.py <id> --watch     # Watch specific project
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"

    @staticmethod
    def disable():
        """Disable colors for non-terminal output"""
        Colors.RESET = ""
        Colors.BOLD = ""
        Colors.GREEN = ""
        Colors.YELLOW = ""
        Colors.RED = ""
        Colors.CYAN = ""
        Colors.GRAY = ""


def get_qralph_root() -> Path:
    """Get the .qralph directory path"""
    # From ${CLAUDE_PLUGIN_ROOT}/skills/qralph/tools -> repo root
    # Go up 4 levels: tools -> qralph -> skills -> plugin_root -> .claude -> repo root
    repo_root = Path(__file__).parent.parent.parent.parent.parent
    return repo_root / ".qralph"


def load_current_project() -> Optional[Dict]:
    """Load current project metadata"""
    qralph_root = get_qralph_root()
    current_file = qralph_root / "current-project.json"

    if not current_file.exists():
        return None

    try:
        with open(current_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading current project: {e}", file=sys.stderr)
        return None


def load_project_state(project_id: str) -> Optional[Dict]:
    """Load project state from checkpoint"""
    qralph_root = get_qralph_root()
    state_file = qralph_root / "projects" / project_id / "checkpoints" / "state.json"

    if not state_file.exists():
        return None

    try:
        with open(state_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading project state: {e}", file=sys.stderr)
        return None


def list_all_projects() -> List[str]:
    """List all project IDs"""
    qralph_root = get_qralph_root()
    projects_dir = qralph_root / "projects"

    if not projects_dir.exists():
        return []

    return [d.name for d in projects_dir.iterdir() if d.is_dir()]


def format_duration(start_time: str) -> str:
    """Format duration from start time to now"""
    try:
        start = datetime.fromisoformat(start_time)
        now = datetime.now()
        delta = now - start

        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60

        if delta.days > 0:
            return f"{delta.days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return "unknown"


def count_findings_by_priority(findings: List[Dict]) -> Dict[str, int]:
    """Count findings by priority level"""
    counts = {"P0": 0, "P1": 0, "P2": 0}
    for finding in findings:
        priority = finding.get("priority", "P2")
        counts[priority] = counts.get(priority, 0) + 1
    return counts


def format_percentage(value: float, max_value: float) -> str:
    """Format value as percentage of max"""
    if max_value == 0:
        return "0%"
    pct = (value / max_value) * 100
    return f"{pct:.0f}%"


def get_phase_progress(phase: str) -> tuple:
    """Get phase progress (current, total)"""
    phases = ["INIT", "PLANNING", "AGENT_SELECTION", "REVIEWING", "SYNTHESIS", "UAT", "COMPLETE"]
    if phase in phases:
        return (phases.index(phase) + 1, len(phases))
    return (0, len(phases))


def get_agent_status_icon(agent: Dict) -> str:
    """Get status icon for agent"""
    status = agent.get("status", "pending")
    if status == "complete":
        return f"{Colors.GREEN}✓{Colors.RESET}"
    elif status == "running":
        return f"{Colors.YELLOW}◐{Colors.RESET}"
    elif status == "error":
        return f"{Colors.RED}✗{Colors.RESET}"
    else:
        return f"{Colors.GRAY}○{Colors.RESET}"


def display_list_view():
    """Display list of all projects"""
    projects = list_all_projects()
    current = load_current_project()
    current_id = current.get("project_id") if current else None

    print(f"{Colors.BOLD}QRALPH Projects Status{Colors.RESET}")
    print("=" * 80)

    if not projects:
        print("No projects found.")
        return

    # Header
    print(f"{'ID':<25} | {'Phase':<12} | {'Mode':<10} | {'Agents':<7} | {'P0':<4} | {'P1':<4} | {'Cost':<8}")
    print("-" * 80)

    for project_id in sorted(projects):
        state = load_project_state(project_id)

        if not state:
            # Minimal display for projects without state
            marker = f"{Colors.CYAN}▶{Colors.RESET} " if project_id == current_id else "  "
            print(f"{marker}{project_id:<23} | {'NO STATE':<12} | {'-':<10} | {'-':<7} | {'-':<4} | {'-':<4} | {'-':<8}")
            continue

        phase = state.get("phase", "UNKNOWN")
        mode = state.get("mode", "unknown")
        agents = state.get("agents", [])
        findings = state.get("findings", [])
        circuit_breakers = state.get("circuit_breakers", {})

        priority_counts = count_findings_by_priority(findings)
        cost = circuit_breakers.get("total_cost_usd", 0.0)

        # Color code phase
        if phase == "COMPLETE":
            phase_str = f"{Colors.GREEN}{phase}{Colors.RESET}"
        elif phase in ["REVIEWING", "SYNTHESIS", "UAT"]:
            phase_str = f"{Colors.YELLOW}{phase}{Colors.RESET}"
        elif phase == "ERROR":
            phase_str = f"{Colors.RED}{phase}{Colors.RESET}"
        else:
            phase_str = phase

        marker = f"{Colors.CYAN}▶{Colors.RESET} " if project_id == current_id else "  "

        print(f"{marker}{project_id:<23} | {phase_str:<20} | {mode:<10} | {len(agents):<7} | {priority_counts['P0']:<4} | {priority_counts['P1']:<4} | ${cost:<7.2f}")

    print()
    if current_id:
        print(f"{Colors.CYAN}▶{Colors.RESET} = Current project")


def display_detailed_view(project_id: str):
    """Display detailed status for a single project"""
    state = load_project_state(project_id)

    if not state:
        print(f"{Colors.RED}Error:{Colors.RESET} No state found for project {project_id}")
        return

    phase = state.get("phase", "UNKNOWN")
    mode = state.get("mode", "unknown")
    created_at = state.get("created_at", "unknown")
    agents = state.get("agents", [])
    findings = state.get("findings", [])
    heal_attempts = state.get("heal_attempts", 0)
    request = state.get("request", "")

    circuit_breakers = state.get("circuit_breakers", {})
    tokens = circuit_breakers.get("total_tokens", 0)
    cost = circuit_breakers.get("total_cost_usd", 0.0)
    error_counts = circuit_breakers.get("error_counts", {})

    # Header
    print(f"{Colors.BOLD}QRALPH Status: {project_id}{Colors.RESET}")
    print("=" * 80)

    # Phase and progress
    current_phase, total_phases = get_phase_progress(phase)
    if phase == "COMPLETE":
        phase_str = f"{Colors.GREEN}{phase}{Colors.RESET} ({current_phase}/{total_phases})"
    elif phase in ["REVIEWING", "SYNTHESIS", "UAT"]:
        phase_str = f"{Colors.YELLOW}{phase}{Colors.RESET} ({current_phase}/{total_phases})"
    elif phase == "ERROR":
        phase_str = f"{Colors.RED}{phase}{Colors.RESET}"
    else:
        phase_str = f"{phase} ({current_phase}/{total_phases})"

    print(f"Phase: {phase_str}")
    print(f"Mode: {mode}")
    print(f"Request: {request}")
    print(f"Started: {created_at}")
    print(f"Elapsed: {format_duration(created_at)}")
    print()

    # Circuit Breakers
    print(f"{Colors.BOLD}Circuit Breakers:{Colors.RESET}")
    print(f"  Tokens: {tokens:,} / 500,000 ({format_percentage(tokens, 500000)})")
    print(f"  Cost: ${cost:.2f} / $40.00 ({format_percentage(cost, 40.0)})")
    print(f"  Errors: {len(error_counts)} unique")
    print(f"  Heals: {heal_attempts} / 5")
    print()

    # Agents
    if agents:
        print(f"{Colors.BOLD}Agents:{Colors.RESET}")
        agent_line = []
        for agent in agents:
            name = agent.get("name", "unknown")
            icon = get_agent_status_icon(agent)
            agent_line.append(f"[{icon}] {name}")
        print("  " + "  ".join(agent_line))
        print()

    # Findings
    priority_counts = count_findings_by_priority(findings)
    print(f"{Colors.BOLD}Findings:{Colors.RESET} ", end="")
    print(f"{Colors.RED}{priority_counts['P0']} P0{Colors.RESET}, ", end="")
    print(f"{Colors.YELLOW}{priority_counts['P1']} P1{Colors.RESET}, ", end="")
    print(f"{priority_counts['P2']} P2")
    print()

    # Errors (if any)
    if error_counts:
        print(f"{Colors.BOLD}Recent Errors:{Colors.RESET}")
        for error_msg, count in list(error_counts.items())[:3]:
            print(f"  [{count}x] {error_msg[:60]}...")
        print()

    # Last activity indicator
    if phase == "COMPLETE":
        print(f"{Colors.GREEN}Status: Project complete{Colors.RESET}")
    elif phase == "ERROR":
        print(f"{Colors.RED}Status: Project encountered errors{Colors.RESET}")
    elif agents and any(a.get("status") == "running" for a in agents):
        print(f"{Colors.YELLOW}Status: Agents running...{Colors.RESET}")
    else:
        print(f"{Colors.GRAY}Status: Waiting for agent outputs...{Colors.RESET}")


def clear_screen():
    """Clear terminal screen (safe - uses static argument only)"""
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    parser = argparse.ArgumentParser(
        description="QRALPH Status Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 qralph-status.py                  # List all projects
  python3 qralph-status.py 001-foo          # Detailed status for project
  python3 qralph-status.py --watch          # Watch all projects
  python3 qralph-status.py 001-foo --watch  # Watch specific project
        """
    )

    parser.add_argument(
        "project_id",
        nargs="?",
        help="Project ID for detailed view (optional)"
    )

    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch mode: refresh every 5 seconds"
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output"
    )

    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    try:
        if args.watch:
            # Watch mode
            while True:
                clear_screen()

                if args.project_id:
                    display_detailed_view(args.project_id)
                else:
                    display_list_view()

                print(f"\n{Colors.GRAY}Refreshing every 5s... (Ctrl+C to exit){Colors.RESET}")
                time.sleep(5)
        else:
            # Single display
            if args.project_id:
                display_detailed_view(args.project_id)
            else:
                display_list_view()

    except KeyboardInterrupt:
        print(f"\n{Colors.GRAY}Exiting...{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}Error:{Colors.RESET} {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
