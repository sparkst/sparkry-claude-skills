#!/usr/bin/env python3
"""
QRALPH Orchestrator v2.1 - State management for multi-agent parallel execution.

This orchestrator MANAGES STATE. Claude spawns parallel agents via Task tool.

Commands:
    python3 qralph-orchestrator.py init "<request>" [--mode planning]
    python3 qralph-orchestrator.py select-agents
    python3 qralph-orchestrator.py synthesize
    python3 qralph-orchestrator.py checkpoint <phase>
    python3 qralph-orchestrator.py generate-uat
    python3 qralph-orchestrator.py finalize
    python3 qralph-orchestrator.py resume <project-id>
    python3 qralph-orchestrator.py status [<project-id>]
    python3 qralph-orchestrator.py heal <error-details>
"""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Constants
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
PROJECTS_DIR = QRALPH_DIR / "projects"
AGENTS_REGISTRY = PROJECT_ROOT / ".claude" / "agents" / "registry.json"
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

# Default agent sets by request type
DEFAULT_AGENT_SETS = {
    "code_review": [
        ("security-reviewer", "sonnet"),
        ("code-quality-auditor", "haiku"),
        ("architecture-advisor", "sonnet"),
        ("requirements-analyst", "sonnet"),
        ("pe-reviewer", "sonnet"),
    ],
    "feature_dev": [
        ("architecture-advisor", "sonnet"),
        ("security-reviewer", "sonnet"),
        ("ux-designer", "sonnet"),
        ("requirements-analyst", "sonnet"),
        ("sde-iii", "sonnet"),
    ],
    "planning": [
        ("pm", "sonnet"),
        ("pe-designer", "sonnet"),
        ("requirements-analyst", "sonnet"),
        ("finance-consultant", "haiku"),
        ("strategic-advisor", "sonnet"),
    ],
    "research": [
        ("research-director", "sonnet"),
        ("fact-checker", "haiku"),
        ("source-evaluator", "haiku"),
        ("industry-signal-scout", "sonnet"),
        ("synthesis-writer", "opus"),
    ],
    "content": [
        ("synthesis-writer", "opus"),
        ("ux-designer", "sonnet"),
        ("pm", "sonnet"),
        ("strategic-advisor", "sonnet"),
        ("research-director", "sonnet"),
    ],
    "testing": [
        ("test-writer", "sonnet"),
        ("ux-tester", "sonnet"),
        ("validation-specialist", "sonnet"),
        ("security-reviewer", "sonnet"),
        ("code-quality-auditor", "haiku"),
    ],
}


def get_state_file() -> Path:
    """Get current project state file."""
    return QRALPH_DIR / "current-project.json"


def load_state() -> dict:
    """Load current project state with file locking."""
    state_file = get_state_file()
    if not state_file.exists():
        return {}

    try:
        with open(state_file, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                content = f.read()
                return json.loads(content) if content else {}
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in state file: {e}", file=sys.stderr)
                return {}
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        print(f"Warning: Error loading state: {e}", file=sys.stderr)
        return {}


def save_state(state: dict):
    """Save project state with file locking."""
    QRALPH_DIR.mkdir(parents=True, exist_ok=True)
    state_file = get_state_file()

    try:
        with open(state_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(state, indent=2))
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        print(f"Error: Failed to save state: {e}", file=sys.stderr)
        raise


def validate_request(request: str) -> bool:
    """Validate request is non-empty and reasonable."""
    if not request or not isinstance(request, str):
        return False
    if not request.strip():
        return False
    if len(request.strip()) < 3:
        return False
    return True


def validate_agent_name(agent: str) -> bool:
    """Validate agent name exists in default sets or registry."""
    # Check if agent is in any default set
    for agent_set in DEFAULT_AGENT_SETS.values():
        if any(a[0] == agent for a in agent_set):
            return True

    # Check agent registry if it exists
    if AGENTS_REGISTRY.exists():
        try:
            registry = json.loads(AGENTS_REGISTRY.read_text())
            return agent in registry.get("agents", {})
        except (json.JSONDecodeError, KeyError):
            pass

    return False


def validate_phase_transition(current_phase: str, next_phase: str) -> bool:
    """Validate phase transition is legal."""
    valid_transitions = {
        "INIT": ["REVIEWING"],
        "REVIEWING": ["EXECUTING", "COMPLETE"],  # COMPLETE if planning mode
        "EXECUTING": ["UAT"],
        "UAT": ["COMPLETE"],
        "COMPLETE": [],
    }
    return next_phase in valid_transitions.get(current_phase, [])


def generate_slug(request: str) -> str:
    """Generate short slug from request."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', request.lower())
    stop_words = {'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into'}
    slug_words = [w for w in words if w not in stop_words][:3]
    return "-".join(slug_words)[:30] or "project"


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough: 1 token ≈ 4 chars)."""
    return len(text) // 4


def estimate_cost(tokens: int, model: str) -> float:
    """Estimate cost in USD for token usage."""
    cost_per_million = MODEL_COSTS.get(model, MODEL_COSTS["sonnet"])
    return (tokens / 1_000_000) * cost_per_million


def check_circuit_breakers(state: dict) -> Optional[str]:
    """Check if any circuit breakers should halt execution.

    Returns error message if circuit breaker tripped, None otherwise.
    """
    breakers = state.get("circuit_breakers", {})

    # Check token limit
    total_tokens = breakers.get("total_tokens", 0)
    if total_tokens > MAX_TOKENS:
        return f"Circuit breaker: Token limit exceeded ({total_tokens:,} > {MAX_TOKENS:,})"

    # Check cost limit
    total_cost = breakers.get("total_cost_usd", 0.0)
    if total_cost > MAX_COST_USD:
        return f"Circuit breaker: Cost limit exceeded (${total_cost:.2f} > ${MAX_COST_USD:.2f})"

    # Check same error count
    error_counts = breakers.get("error_counts", {})
    for error, count in error_counts.items():
        if count >= MAX_SAME_ERROR:
            return f"Circuit breaker: Same error occurred {count} times: {error[:100]}"

    # Check heal attempts
    heal_attempts = state.get("heal_attempts", 0)
    if heal_attempts >= MAX_HEAL_ATTEMPTS:
        return f"Circuit breaker: Max heal attempts exceeded ({heal_attempts} >= {MAX_HEAL_ATTEMPTS})"

    return None


def update_circuit_breakers(state: dict, tokens: int = 0, model: str = "sonnet", error: str = None):
    """Update circuit breaker tracking."""
    if "circuit_breakers" not in state:
        state["circuit_breakers"] = {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "error_counts": {},
        }

    breakers = state["circuit_breakers"]

    # Update tokens and cost
    breakers["total_tokens"] += tokens
    breakers["total_cost_usd"] += estimate_cost(tokens, model)

    # Update error tracking
    if error:
        error_key = error[:100]  # Truncate for storage
        breakers["error_counts"][error_key] = breakers["error_counts"].get(error_key, 0) + 1


def check_control_commands(project_path: Path) -> Optional[str]:
    """Check CONTROL.md for user intervention commands.

    Returns command if found, None otherwise.
    """
    control_file = project_path / "CONTROL.md"
    if not control_file.exists():
        return None

    try:
        content = control_file.read_text().upper()

        # Check for commands (case-insensitive)
        if "PAUSE" in content:
            return "PAUSE"
        elif "SKIP" in content:
            return "SKIP"
        elif "ABORT" in content:
            return "ABORT"
        elif "STATUS" in content:
            return "STATUS"

    except Exception as e:
        print(f"Warning: Could not read CONTROL.md: {e}", file=sys.stderr)

    return None


def detect_request_type(request: str) -> str:
    """Detect request type for agent selection."""
    request_lower = request.lower()

    if any(w in request_lower for w in ["review", "audit", "check", "security"]):
        return "code_review"
    elif any(w in request_lower for w in ["plan", "design", "strategy", "roadmap"]):
        return "planning"
    elif any(w in request_lower for w in ["research", "analyze", "compare", "investigate"]):
        return "research"
    elif any(w in request_lower for w in ["write", "article", "content", "blog", "polish"]):
        return "content"
    elif any(w in request_lower for w in ["test", "qa", "validation", "coverage"]):
        return "testing"
    else:
        return "feature_dev"


def cmd_init(request: str, mode: str = "coding"):
    """Initialize a new QRALPH project."""
    # Validate input
    if not validate_request(request):
        error = {"error": "Invalid request: must be non-empty string with at least 3 characters"}
        print(json.dumps(error))
        return error

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    # Get next project number
    existing = list(PROJECTS_DIR.glob("[0-9][0-9][0-9]-*"))
    next_num = max([int(p.name[:3]) for p in existing], default=0) + 1

    # Create project
    slug = generate_slug(request)
    project_id = f"{next_num:03d}-{slug}"
    project_path = PROJECTS_DIR / project_id

    # Create directory structure
    (project_path / "agent-outputs").mkdir(parents=True)
    (project_path / "checkpoints").mkdir(parents=True)
    (project_path / "healing-attempts").mkdir(parents=True)

    # Create initial files
    (project_path / "CONTROL.md").write_text(
        "# QRALPH Control\n\n"
        "Write commands here:\n"
        "- PAUSE - stop after current step\n"
        "- SKIP - skip current operation\n"
        "- ABORT - graceful shutdown\n"
        "- STATUS - force status dump\n"
    )

    (project_path / "decisions.log").write_text(
        f"[{datetime.now().strftime('%H:%M:%S')}] Project initialized: {project_id}\n"
        f"[{datetime.now().strftime('%H:%M:%S')}] Request: {request}\n"
        f"[{datetime.now().strftime('%H:%M:%S')}] Mode: {mode}\n"
    )

    # Save state with circuit breaker initialization
    state = {
        "project_id": project_id,
        "project_path": str(project_path),
        "request": request,
        "mode": mode,
        "phase": "INIT",
        "created_at": datetime.now().isoformat(),
        "agents": [],
        "findings": [],
        "heal_attempts": 0,
        "circuit_breakers": {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "error_counts": {},
        },
    }
    save_state(state)

    # Also save to project checkpoint
    (project_path / "checkpoints" / "state.json").write_text(json.dumps(state, indent=2))

    # Output for Claude
    output = {
        "status": "initialized",
        "project_id": project_id,
        "project_path": str(project_path),
        "mode": mode,
        "next_step": "Run select-agents to get agent configurations",
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_select_agents(custom_agents: Optional[list] = None):
    """Select agents and generate prompts for parallel execution."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project. Run init first."}))
        return

    project_path = Path(state["project_path"])

    # Check control commands
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)

    # Check circuit breakers
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        print(json.dumps({"error": breaker_error}))
        return

    request = state["request"]

    # Select agents
    if custom_agents:
        # Validate custom agents
        invalid_agents = [a for a in custom_agents if not validate_agent_name(a)]
        if invalid_agents:
            error = {"error": f"Invalid agent names: {', '.join(invalid_agents)}"}
            print(json.dumps(error))
            return error

        # User specified agents - add default model tier
        agents = [(a, "sonnet") for a in custom_agents[:5]]
    else:
        request_type = detect_request_type(request)
        agents = DEFAULT_AGENT_SETS.get(request_type, DEFAULT_AGENT_SETS["feature_dev"])

    # Validate phase transition
    if not validate_phase_transition(state["phase"], "REVIEWING"):
        error = {"error": f"Invalid phase transition: {state['phase']} -> REVIEWING"}
        print(json.dumps(error))
        return error

    # Generate prompts for each agent
    agent_configs = []
    total_tokens = 0
    for agent_type, model_tier in agents:
        prompt = generate_agent_prompt(agent_type, request, state["project_id"], project_path)
        tokens = estimate_tokens(prompt)
        total_tokens += tokens

        agent_configs.append({
            "agent_type": agent_type,
            "model": model_tier,
            "description": f"{agent_type.replace('-', ' ').title()} review",
            "prompt": prompt,
            "output_file": str(project_path / "agent-outputs" / f"{agent_type}.md"),
        })

    # Update circuit breakers with estimated token usage
    update_circuit_breakers(state, total_tokens, "sonnet")

    # Update state
    state["agents"] = [a["agent_type"] for a in agent_configs]
    state["phase"] = "REVIEWING"
    save_state(state)

    # Log
    log_decision(project_path, f"Selected agents: {', '.join(state['agents'])}")

    # Output for Claude to use with Task tool
    output = {
        "status": "agents_selected",
        "project_id": state["project_id"],
        "agent_count": len(agent_configs),
        "agents": agent_configs,
        "instruction": (
            "Spawn these agents IN PARALLEL using the Task tool. "
            "Include ALL agent configs in a SINGLE message with multiple Task calls."
        ),
    }
    print(json.dumps(output, indent=2))
    return output


def generate_agent_prompt(agent_type: str, request: str, project_id: str, project_path: Path) -> str:
    """Generate a review prompt for a specific agent."""
    base_prompt = f"""You are {agent_type.replace('-', ' ')} reviewing project {project_id}.

REQUEST: {request}

PROJECT PATH: {project_path}

## Your Task

Analyze this request from your specialized perspective and provide findings.

## Output Format

Write your findings to: {project_path}/agent-outputs/{agent_type}.md

Use this structure:

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
[Numbered list of specific actions to take]

---
*Review completed at: {datetime.now().isoformat()}*
"""

    # Add agent-specific context
    agent_context = {
        "security-reviewer": "\n## Focus Areas\n- Authentication/authorization issues\n- Input validation\n- Sensitive data exposure\n- Injection vulnerabilities\n- OWASP Top 10",
        "architecture-advisor": "\n## Focus Areas\n- System design patterns\n- Scalability concerns\n- Technical debt\n- Dependency management\n- Interface contracts",
        "code-quality-auditor": "\n## Focus Areas\n- Code style consistency\n- Error handling\n- Test coverage\n- Documentation\n- CLAUDE.md compliance",
        "requirements-analyst": "\n## Focus Areas\n- Requirement clarity\n- Acceptance criteria\n- Edge cases\n- Dependencies between requirements\n- Story point estimates",
        "ux-designer": "\n## Focus Areas\n- User flows\n- Accessibility\n- Error states\n- Loading states\n- Mobile responsiveness",
        "sde-iii": "\n## Focus Areas\n- Implementation complexity\n- Performance implications\n- Integration points\n- Testing strategy\n- Deployment considerations",
        "pm": "\n## Focus Areas\n- Market fit\n- User value\n- Prioritization\n- Success metrics\n- Stakeholder impact",
        "synthesis-writer": "\n## Focus Areas\n- Content clarity\n- Voice consistency\n- Structure\n- Audience alignment\n- Call to action effectiveness",
    }

    return base_prompt + agent_context.get(agent_type, "")


def cmd_synthesize():
    """Synthesize findings from all agent outputs."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project. Run init first."}))
        return

    project_path = Path(state["project_path"])

    # Check control commands
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)

    # Check circuit breakers
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        print(json.dumps({"error": breaker_error}))
        return

    outputs_dir = project_path / "agent-outputs"

    # Collect all findings
    all_findings = {"P0": [], "P1": [], "P2": []}
    agent_summaries = []

    for agent in state.get("agents", []):
        output_file = outputs_dir / f"{agent}.md"
        if output_file.exists():
            content = output_file.read_text()
            agent_summaries.append(f"### {agent}\n{extract_summary(content)}")

            # Track tokens for synthesis
            tokens = estimate_tokens(content)
            update_circuit_breakers(state, tokens, "haiku")

            # Extract findings by priority
            for priority in ["P0", "P1", "P2"]:
                findings = extract_findings(content, priority)
                for f in findings:
                    all_findings[priority].append({"agent": agent, "finding": f})

    # Create synthesis report
    synthesis = f"""# QRALPH Synthesis Report: {state['project_id']}

## Request
{state['request']}

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
"""

    # Save synthesis
    (project_path / "SYNTHESIS.md").write_text(synthesis)

    # Update state with phase transition validation
    next_phase = "EXECUTING" if state["mode"] == "coding" else "COMPLETE"
    if not validate_phase_transition(state["phase"], next_phase):
        error = {"error": f"Invalid phase transition: {state['phase']} -> {next_phase}"}
        print(json.dumps(error))
        return error

    state["findings"] = all_findings
    state["phase"] = next_phase
    save_state(state)

    log_decision(project_path, f"Synthesis complete: {len(all_findings['P0'])} P0, {len(all_findings['P1'])} P1, {len(all_findings['P2'])} P2")

    output = {
        "status": "synthesized",
        "project_id": state["project_id"],
        "synthesis_file": str(project_path / "SYNTHESIS.md"),
        "p0_count": len(all_findings["P0"]),
        "p1_count": len(all_findings["P1"]),
        "p2_count": len(all_findings["P2"]),
        "next_phase": state["phase"],
    }
    print(json.dumps(output, indent=2))
    return output


def extract_summary(content: str) -> str:
    """Extract summary section from agent output."""
    match = re.search(r'## Summary\s*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    return match.group(1).strip() if match else "(No summary found)"


def extract_findings(content: str, priority: str) -> list:
    """Extract findings for a specific priority level."""
    pattern = rf'### {priority}[^\n]*\n(.*?)(?=\n###|\n##|\Z)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        findings_text = match.group(1)
        findings = re.findall(r'^[-*]\s*(.+)$', findings_text, re.MULTILINE)
        return [f.strip() for f in findings if f.strip() and not f.startswith('(')]
    return []


def format_findings(findings: list) -> str:
    """Format findings list for synthesis."""
    if not findings:
        return "- None identified"

    lines = []
    for f in findings:
        lines.append(f"- **[{f['agent']}]** {f['finding']}")
    return "\n".join(lines)


def generate_action_plan(findings: dict) -> str:
    """Generate action plan from findings."""
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


def handle_control_command(command: str, state: dict, project_path: Path) -> dict:
    """Handle CONTROL.md intervention commands."""
    output = {"status": "control_command", "command": command}

    if command == "PAUSE":
        log_decision(project_path, "PAUSE command detected - waiting for user")
        output["action"] = "paused"
        output["message"] = "Execution paused. Remove PAUSE from CONTROL.md to continue."
        print(json.dumps(output, indent=2))
        sys.exit(0)

    elif command == "SKIP":
        log_decision(project_path, "SKIP command detected - skipping current operation")
        output["action"] = "skipped"
        output["message"] = "Operation skipped. Remove SKIP from CONTROL.md for next operation."

    elif command == "ABORT":
        log_decision(project_path, "ABORT command detected - graceful shutdown")
        cmd_checkpoint(state["phase"])
        output["action"] = "aborted"
        output["message"] = "Execution aborted. Checkpoint saved. Use 'resume' to continue."
        print(json.dumps(output, indent=2))
        sys.exit(0)

    elif command == "STATUS":
        log_decision(project_path, "STATUS command detected - forcing status dump")
        write_status_file(state, project_path)
        output["action"] = "status_written"
        output["message"] = "Status written to STATUS.md"

    print(json.dumps(output, indent=2))
    return output


def write_status_file(state: dict, project_path: Path):
    """Write detailed status to STATUS.md."""
    breakers = state.get("circuit_breakers", {})

    status_content = f"""# QRALPH Status: {state.get('project_id', 'unknown')}

## Current State
- **Phase**: {state.get('phase', 'unknown')}
- **Mode**: {state.get('mode', 'unknown')}
- **Heal Attempts**: {state.get('heal_attempts', 0)} / {MAX_HEAL_ATTEMPTS}

## Circuit Breakers
- **Total Tokens**: {breakers.get('total_tokens', 0):,} / {MAX_TOKENS:,}
- **Total Cost**: ${breakers.get('total_cost_usd', 0.0):.2f} / ${MAX_COST_USD:.2f}
- **Error Counts**: {len(breakers.get('error_counts', {}))} unique errors

## Agents
{', '.join(state.get('agents', []))}

## Findings Summary
- P0: {len(state.get('findings', {}).get('P0', []))}
- P1: {len(state.get('findings', {}).get('P1', []))}
- P2: {len(state.get('findings', {}).get('P2', []))}

---
*Status generated at: {datetime.now().isoformat()}*
"""

    (project_path / "STATUS.md").write_text(status_content)


def cmd_heal(error_details: str):
    """Self-healing with model escalation."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project. Run init first."}))
        return

    project_path = Path(state["project_path"])

    # Check control commands
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)

    # Increment heal attempts
    state["heal_attempts"] = state.get("heal_attempts", 0) + 1
    heal_attempt = state["heal_attempts"]

    # Track error in circuit breakers
    update_circuit_breakers(state, 0, "haiku", error_details)

    # Check if we've exceeded max attempts
    if heal_attempt > MAX_HEAL_ATTEMPTS:
        # Create DEFERRED.md and continue
        deferred_content = f"""# Deferred Issue

## Error
{error_details}

## Attempts
Failed after {MAX_HEAL_ATTEMPTS} healing attempts.

## Model Escalation History
- Attempts 1-2: haiku
- Attempts 3-4: sonnet
- Attempt 5: opus

## Resolution
Issue deferred for manual review. Continuing with remaining work.

---
*Deferred at: {datetime.now().isoformat()}*
"""
        (project_path / "DEFERRED.md").write_text(deferred_content)
        log_decision(project_path, f"Issue deferred after {MAX_HEAL_ATTEMPTS} attempts")

        output = {
            "status": "deferred",
            "heal_attempts": heal_attempt,
            "deferred_file": str(project_path / "DEFERRED.md"),
            "message": "Max heal attempts exceeded. Issue deferred. Continuing.",
        }
        print(json.dumps(output, indent=2))
        save_state(state)
        return output

    # Determine model tier based on attempt number
    if heal_attempt <= 2:
        model = "haiku"
    elif heal_attempt <= 4:
        model = "sonnet"
    else:
        model = "opus"

    # Save healing attempt details
    heal_file = project_path / "healing-attempts" / f"attempt-{heal_attempt:02d}.md"
    heal_file.write_text(f"""# Healing Attempt {heal_attempt}

## Model
{model}

## Error
{error_details}

## Timestamp
{datetime.now().isoformat()}

## Strategy
Model escalation: Retry with {model} model.
""")

    log_decision(project_path, f"Heal attempt {heal_attempt} using {model}")

    # Save state
    save_state(state)

    # Output healing strategy
    output = {
        "status": "healing",
        "heal_attempt": heal_attempt,
        "model": model,
        "error_summary": error_details[:200],
        "heal_file": str(heal_file),
        "instruction": (
            f"Retry the failed operation using {model} model tier. "
            f"This is attempt {heal_attempt}/{MAX_HEAL_ATTEMPTS}."
        ),
    }
    print(json.dumps(output, indent=2))
    return output


def cmd_checkpoint(phase: str):
    """Save checkpoint at current phase."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    project_path = Path(state["project_path"])

    # Check control commands
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)

    state["phase"] = phase
    state["checkpoint_at"] = datetime.now().isoformat()
    save_state(state)

    # Save to project checkpoints
    checkpoint_file = project_path / "checkpoints" / f"{phase.lower()}-{datetime.now().strftime('%H%M%S')}.json"
    checkpoint_file.write_text(json.dumps(state, indent=2))

    log_decision(project_path, f"Checkpoint saved: {phase}")

    print(json.dumps({
        "status": "checkpointed",
        "phase": phase,
        "checkpoint_file": str(checkpoint_file),
    }))


def cmd_generate_uat():
    """Generate UAT scenarios."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    project_path = Path(state["project_path"])

    # Check control commands
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)

    # Check circuit breakers
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        print(json.dumps({"error": breaker_error}))
        return

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
- [ ] No regressions in existing functionality
- [ ] Performance acceptable
- [ ] Documentation updated

---
*Generated at: {datetime.now().isoformat()}*
"""

    (project_path / "UAT.md").write_text(uat_content)

    # Validate phase transition
    if not validate_phase_transition(state["phase"], "UAT"):
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
    """Finalize project and generate summary."""
    state = load_state()
    if not state:
        print(json.dumps({"error": "No active project."}))
        return

    project_path = Path(state["project_path"])

    # Check control commands
    control_cmd = check_control_commands(project_path)
    if control_cmd:
        return handle_control_command(control_cmd, state, project_path)

    # Check circuit breakers
    breaker_error = check_circuit_breakers(state)
    if breaker_error:
        print(json.dumps({"error": breaker_error}))
        return

    summary = f"""# QRALPH Summary: {state['project_id']}

## Request
{state['request']}

## Execution Details
- **Mode**: {state['mode']}
- **Started**: {state['created_at']}
- **Completed**: {datetime.now().isoformat()}
- **Agents**: {', '.join(state.get('agents', []))}
- **Self-Heal Attempts**: {state.get('heal_attempts', 0)}

## Results
- P0 Issues: {len(state.get('findings', {}).get('P0', []))}
- P1 Issues: {len(state.get('findings', {}).get('P1', []))}
- P2 Issues: {len(state.get('findings', {}).get('P2', []))}

## Files Generated
- SYNTHESIS.md - Consolidated findings
- UAT.md - Acceptance test scenarios
- agent-outputs/ - Individual agent reviews

## Next Steps
1. Review SYNTHESIS.md for action items
2. Execute UAT scenarios
3. Archive or delete project directory when complete

---
*QRALPH v2.0 - Parallel Multi-Agent Swarm*
"""

    (project_path / "SUMMARY.md").write_text(summary)

    # Validate phase transition
    if not validate_phase_transition(state["phase"], "COMPLETE"):
        error = {"error": f"Invalid phase transition: {state['phase']} -> COMPLETE"}
        print(json.dumps(error))
        return error

    state["phase"] = "COMPLETE"
    state["completed_at"] = datetime.now().isoformat()
    save_state(state)

    log_decision(project_path, "Project finalized")

    # Send notification
    notify(f"QRALPH complete: {state['project_id']}")

    print(json.dumps({
        "status": "complete",
        "project_id": state["project_id"],
        "summary_file": str(project_path / "SUMMARY.md"),
    }))


def cmd_resume(project_id: str):
    """Resume a project from checkpoint."""
    # Find project
    matches = list(PROJECTS_DIR.glob(f"{project_id}*"))
    if not matches:
        print(json.dumps({"error": f"No project found matching: {project_id}"}))
        return

    project_path = matches[0]

    # Load latest checkpoint
    checkpoint_dir = project_path / "checkpoints"
    state_file = checkpoint_dir / "state.json"

    if state_file.exists():
        state = json.loads(state_file.read_text())
    else:
        # Try to find any checkpoint
        checkpoints = sorted(checkpoint_dir.glob("*.json"))
        if checkpoints:
            state = json.loads(checkpoints[-1].read_text())
        else:
            print(json.dumps({"error": "No checkpoint found"}))
            return

    # Restore state
    save_state(state)

    log_decision(project_path, f"Resumed from phase: {state['phase']}")

    print(json.dumps({
        "status": "resumed",
        "project_id": state["project_id"],
        "phase": state["phase"],
        "next_step": get_next_step(state["phase"]),
    }))


def cmd_status(project_id: Optional[str] = None):
    """Show status of project(s)."""
    if project_id:
        # Show specific project
        matches = list(PROJECTS_DIR.glob(f"{project_id}*"))
        if matches:
            project_path = matches[0]
            state_file = project_path / "checkpoints" / "state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                print(json.dumps(state, indent=2))
            else:
                print(json.dumps({"project": project_path.name, "status": "no state file"}))
        else:
            print(json.dumps({"error": f"Project not found: {project_id}"}))
    else:
        # Show all projects
        projects = []
        for p in sorted(PROJECTS_DIR.glob("[0-9][0-9][0-9]-*")):
            state_file = p / "checkpoints" / "state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                projects.append({
                    "id": p.name,
                    "phase": state.get("phase", "unknown"),
                    "mode": state.get("mode", "unknown"),
                    "created": state.get("created_at", "unknown"),
                })
            else:
                projects.append({"id": p.name, "phase": "no state"})

        print(json.dumps({"projects": projects}, indent=2))


def get_next_step(phase: str) -> str:
    """Get next step instruction for a phase."""
    steps = {
        "INIT": "Run select-agents to choose review agents",
        "REVIEWING": "Spawn agents via Task tool, then run synthesize",
        "EXECUTING": "Implement fixes, then run generate-uat",
        "UAT": "Execute UAT scenarios, then run finalize",
        "COMPLETE": "Project complete. Review SUMMARY.md",
    }
    return steps.get(phase, "Unknown phase")


def log_decision(project_path: Path, message: str):
    """Log a decision to the project log."""
    log_file = project_path / "decisions.log"
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")


def notify(message: str):
    """Send notification via webhook."""
    if NOTIFY_TOOL.exists():
        try:
            subprocess.run([
                "python3", str(NOTIFY_TOOL),
                "--event", "complete",
                "--message", message
            ], capture_output=True)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="QRALPH Orchestrator v2.1")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize new project")
    init_parser.add_argument("request", help="The request to execute")
    init_parser.add_argument("--mode", choices=["coding", "planning"], default="coding")

    # select-agents
    select_parser = subparsers.add_parser("select-agents", help="Select and configure agents")
    select_parser.add_argument("--agents", help="Comma-separated agent list")

    # synthesize
    subparsers.add_parser("synthesize", help="Synthesize agent findings")

    # checkpoint
    checkpoint_parser = subparsers.add_parser("checkpoint", help="Save checkpoint")
    checkpoint_parser.add_argument("phase", help="Current phase name")

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

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args.request, args.mode)
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
