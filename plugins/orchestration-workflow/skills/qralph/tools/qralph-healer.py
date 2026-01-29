#!/usr/bin/env python3
"""
QRALPH Healer v1.0 - Self-healing coordinator for error analysis and recovery.

This tool analyzes errors, suggests fixes, tracks healing attempts, and provides
rollback capabilities for QRALPH multi-agent workflows.

Commands:
    python3 qralph-healer.py analyze "<error>"       # Analyze error and suggest fix
    python3 qralph-healer.py attempt "<error>"       # Record healing attempt
    python3 qralph-healer.py rollback                # Rollback to last checkpoint
    python3 qralph-healer.py history                 # Show healing history
    python3 qralph-healer.py clear                   # Clear error counts
    python3 qralph-healer.py status                  # Show healer status

Error Categories:
    - ImportError: Missing module imports
    - SyntaxError: Python syntax issues
    - TypeError: Type mismatches
    - FileNotFoundError: Missing files/paths
    - PermissionError: Access denied (manual intervention required)
    - NetworkError: Connection/API failures
    - UnknownError: Unclassified errors (escalate to opus)

Model Escalation:
    - Attempts 1-2: haiku ($0.25/1M tokens) - simple fixes
    - Attempts 3-4: sonnet ($3/1M tokens) - complex fixes
    - Attempt 5: opus ($15/1M tokens) - architectural issues
    - Attempt 6+: manual intervention (deferred)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Constants
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"

# Error pattern matching
ERROR_PATTERNS = {
    "import_error": {
        "patterns": [
            r"No module named ['\"](.+?)['\"]",
            r"cannot import name ['\"](.+?)['\"]",
            r"ImportError: (.+)",
        ],
        "severity": "recoverable",
        "default_model": "haiku",
        "description": "Missing Python module or import",
    },
    "syntax_error": {
        "patterns": [
            r"SyntaxError: (.+)",
            r"invalid syntax",
            r"unexpected EOF",
            r"IndentationError: (.+)",
        ],
        "severity": "recoverable",
        "default_model": "sonnet",
        "description": "Python syntax issue",
    },
    "type_error": {
        "patterns": [
            r"TypeError: (.+)",
            r"expected .+ but got .+",
            r"takes .+ positional argument",
        ],
        "severity": "recoverable",
        "default_model": "sonnet",
        "description": "Type mismatch or argument error",
    },
    "file_not_found": {
        "patterns": [
            r"FileNotFoundError: (.+)",
            r"No such file or directory: ['\"](.+?)['\"]",
            r"\[Errno 2\] (.+)",
        ],
        "severity": "recoverable",
        "default_model": "haiku",
        "description": "Missing file or directory",
    },
    "permission_error": {
        "patterns": [
            r"PermissionError: (.+)",
            r"Permission denied",
            r"\[Errno 13\] (.+)",
        ],
        "severity": "manual",
        "default_model": "opus",
        "description": "Access denied - requires manual intervention",
    },
    "network_error": {
        "patterns": [
            r"ConnectionError: (.+)",
            r"TimeoutError: (.+)",
            r"Connection refused",
            r"Failed to establish connection",
            r"HTTP Error \d+",
        ],
        "severity": "retry",
        "default_model": "haiku",
        "description": "Network or API connection failure",
    },
    "json_decode_error": {
        "patterns": [
            r"JSONDecodeError: (.+)",
            r"Expecting value: (.+)",
            r"Invalid JSON",
        ],
        "severity": "recoverable",
        "default_model": "haiku",
        "description": "Invalid JSON parsing",
    },
    "attribute_error": {
        "patterns": [
            r"AttributeError: (.+)",
            r"has no attribute ['\"](.+?)['\"]",
        ],
        "severity": "recoverable",
        "default_model": "sonnet",
        "description": "Missing object attribute",
    },
}


def get_state_file() -> Path:
    """Get current project state file."""
    return QRALPH_DIR / "current-project.json"


def load_state() -> Dict[str, Any]:
    """Load current project state."""
    state_file = get_state_file()
    if not state_file.exists():
        return {}

    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_state(state: Dict[str, Any]):
    """Save project state."""
    QRALPH_DIR.mkdir(parents=True, exist_ok=True)
    state_file = get_state_file()
    state_file.write_text(json.dumps(state, indent=2))


def get_healing_dir() -> Path:
    """Get healing attempts directory for current project."""
    state = load_state()
    if not state:
        return QRALPH_DIR / "healing-attempts"

    project_path = Path(state.get("project_path", ""))
    if project_path.exists():
        return project_path / "healing-attempts"
    return QRALPH_DIR / "healing-attempts"


def classify_error(error_message: str) -> Dict[str, Any]:
    """
    Classify error message and return analysis.

    Returns:
        dict: {
            "error_type": str,
            "severity": str,
            "match": str,
            "pattern_used": str,
        }
    """
    for error_type, config in ERROR_PATTERNS.items():
        for pattern in config["patterns"]:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return {
                    "error_type": error_type,
                    "severity": config["severity"],
                    "default_model": config["default_model"],
                    "description": config["description"],
                    "match": match.group(0) if match else error_message[:100],
                    "pattern_used": pattern,
                }

    # Unknown error
    return {
        "error_type": "unknown_error",
        "severity": "escalate",
        "default_model": "opus",
        "description": "Unclassified error - requires expert analysis",
        "match": error_message[:100],
        "pattern_used": None,
    }


def count_similar_errors(error_message: str) -> int:
    """Count how many times similar error has occurred in history."""
    healing_dir = get_healing_dir()
    if not healing_dir.exists():
        return 0

    # Normalize error for comparison
    normalized_error = error_message[:100].lower()

    count = 0
    for attempt_file in sorted(healing_dir.glob("attempt-*.md")):
        try:
            content = attempt_file.read_text()
            if "## Error" in content:
                error_section = content.split("## Error")[1].split("##")[0]
                if normalized_error in error_section.lower():
                    count += 1
        except Exception:
            continue

    return count


def generate_healing_prompt(error_analysis: Dict[str, Any], attempt_number: int) -> str:
    """
    Generate Claude-compatible healing prompt.

    Args:
        error_analysis: Output from classify_error()
        attempt_number: Current healing attempt number (1-5)

    Returns:
        str: Prompt for Claude to fix the error
    """
    error_type = error_analysis["error_type"]
    severity = error_analysis["severity"]
    match = error_analysis["match"]
    description = error_analysis["description"]

    # Base prompt
    prompt = f"""You are fixing a {error_type.replace('_', ' ')} in the QRALPH workflow.

## Error Details

**Type**: {error_type}
**Severity**: {severity}
**Description**: {description}
**Error Message**: {match}

## Your Task

This is healing attempt {attempt_number}/5. """

    # Add type-specific instructions
    if error_type == "import_error":
        prompt += """
Fix the missing import by:
1. Identifying the required module
2. Adding the import statement at the top of the file
3. If module is not installed, note this in your response

**Example Fix:**
```python
import json
from pathlib import Path
```
"""

    elif error_type == "syntax_error":
        prompt += """
Fix the syntax error by:
1. Locating the line with invalid syntax
2. Correcting the syntax according to Python rules
3. Ensuring proper indentation and bracket matching

**Common Fixes:**
- Missing colons after if/for/while/def
- Unmatched parentheses/brackets
- Incorrect indentation
"""

    elif error_type == "type_error":
        prompt += """
Fix the type error by:
1. Identifying the type mismatch
2. Adding type conversion or validation
3. Updating function signatures if needed

**Example Fix:**
```python
# Before: func(value)
# After: func(str(value))  # or int(value), etc.
```
"""

    elif error_type == "file_not_found":
        prompt += """
Fix the missing file by:
1. Creating the file if it should exist
2. Correcting the file path if it's wrong
3. Adding existence checks before file operations

**Example Fix:**
```python
file_path = Path("path/to/file.json")
if not file_path.exists():
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps({}))
```
"""

    elif error_type == "permission_error":
        prompt += """
This requires manual intervention. Suggest one of:
1. Run with appropriate permissions (sudo/admin)
2. Change file permissions (chmod/chown)
3. Use different file location with write access

DO NOT attempt automatic fix for permission errors.
"""

    elif error_type == "network_error":
        prompt += """
Fix the network error by:
1. Adding retry logic with exponential backoff
2. Adding timeout handling
3. Adding error messages for users

**Example Fix:**
```python
import time
for attempt in range(3):
    try:
        result = api_call()
        break
    except ConnectionError:
        if attempt < 2:
            time.sleep(2 ** attempt)
        else:
            raise
```
"""

    else:  # unknown_error
        prompt += """
Analyze this unknown error:
1. Review the full error message and stack trace
2. Identify the root cause
3. Propose a fix with explanation
4. If unsure, recommend manual investigation

This is an unclassified error requiring expert analysis.
"""

    prompt += f"""

## Context

- **Current Attempt**: {attempt_number}/5
- **Model Tier**: {error_analysis['default_model']}
- **Severity**: {severity}

## Output Format

Provide a concise fix in this format:

**Problem**: [1 sentence explanation]
**Solution**: [Code change or action to take]
**Verification**: [How to verify fix worked]

Focus on the minimal change needed to resolve the error.
"""

    return prompt


def cmd_analyze(error_message: str):
    """Analyze error and suggest fix strategy."""
    if not error_message or not error_message.strip():
        output = {"error": "Error message cannot be empty"}
        print(json.dumps(output, indent=2))
        return output

    # Classify error
    error_analysis = classify_error(error_message)

    # Count similar errors
    similar_count = count_similar_errors(error_message)

    # Determine suggested model (escalate if repeated)
    suggested_model = error_analysis["default_model"]
    if similar_count >= 2:
        suggested_model = "sonnet"
    if similar_count >= 4:
        suggested_model = "opus"

    # Generate healing prompt
    heal_prompt = generate_healing_prompt(error_analysis, similar_count + 1)

    # Build output
    output = {
        "status": "analyzed",
        "error_type": error_analysis["error_type"],
        "severity": error_analysis["severity"],
        "description": error_analysis["description"],
        "suggested_model": suggested_model,
        "similar_errors": similar_count,
        "suggested_fix": get_suggested_fix(error_analysis["error_type"]),
        "heal_prompt": heal_prompt,
        "action": get_action_for_severity(error_analysis["severity"]),
    }

    print(json.dumps(output, indent=2))
    return output


def get_suggested_fix(error_type: str) -> str:
    """Get one-line suggested fix for error type."""
    fixes = {
        "import_error": "Add missing import statement at top of file",
        "syntax_error": "Correct syntax error (missing colon, bracket, indentation)",
        "type_error": "Add type conversion or fix function signature",
        "file_not_found": "Create missing file or correct file path",
        "permission_error": "MANUAL: Adjust file permissions or run with elevated privileges",
        "network_error": "Add retry logic with timeout handling",
        "json_decode_error": "Validate and fix JSON formatting",
        "attribute_error": "Add missing attribute or fix object reference",
        "unknown_error": "ESCALATE: Requires expert analysis with opus model",
    }
    return fixes.get(error_type, "Analyze error and apply appropriate fix")


def get_action_for_severity(severity: str) -> str:
    """Get recommended action based on severity."""
    actions = {
        "recoverable": "AUTO_FIX: Apply healing prompt with suggested model",
        "retry": "RETRY: Wait and retry operation",
        "manual": "MANUAL: User intervention required",
        "escalate": "ESCALATE: Use opus model for expert analysis",
    }
    return actions.get(severity, "UNKNOWN: Review error manually")


def cmd_attempt(error_message: str):
    """Record healing attempt and integrate with orchestrator."""
    if not error_message or not error_message.strip():
        output = {"error": "Error message cannot be empty"}
        print(json.dumps(output, indent=2))
        return output

    state = load_state()
    if not state:
        output = {"error": "No active project. Run qralph-orchestrator.py init first."}
        print(json.dumps(output, indent=2))
        return output

    project_path = Path(state.get("project_path", ""))
    if not project_path.exists():
        output = {"error": f"Project path not found: {project_path}"}
        print(json.dumps(output, indent=2))
        return output

    # Increment heal attempts
    heal_attempts = state.get("heal_attempts", 0) + 1
    state["heal_attempts"] = heal_attempts

    # Classify error
    error_analysis = classify_error(error_message)

    # Determine model tier
    if heal_attempts <= 2:
        model = "haiku"
    elif heal_attempts <= 4:
        model = "sonnet"
    else:
        model = "opus"

    # Generate healing prompt
    heal_prompt = generate_healing_prompt(error_analysis, heal_attempts)

    # Save attempt record
    healing_dir = project_path / "healing-attempts"
    healing_dir.mkdir(exist_ok=True)

    attempt_file = healing_dir / f"attempt-{heal_attempts:02d}.md"
    attempt_content = f"""# Healing Attempt {heal_attempts}

## Error Analysis

**Type**: {error_analysis['error_type']}
**Severity**: {error_analysis['severity']}
**Model**: {model}

## Error Message

```
{error_message}
```

## Classification

{error_analysis['description']}

## Healing Prompt

{heal_prompt}

## Timestamp

{datetime.now().isoformat()}

## Status

Pending execution by {model} model.

---
*Generated by qralph-healer.py v1.0*
"""

    attempt_file.write_text(attempt_content)

    # Update circuit breakers
    if "circuit_breakers" not in state:
        state["circuit_breakers"] = {"error_counts": {}}

    error_key = error_message[:100]
    error_counts = state["circuit_breakers"].get("error_counts", {})
    error_counts[error_key] = error_counts.get(error_key, 0) + 1
    state["circuit_breakers"]["error_counts"] = error_counts

    # Save state
    save_state(state)

    # Log to decisions
    log_file = project_path / "decisions.log"
    with open(log_file, "a") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Healing attempt {heal_attempts} recorded: {error_analysis['error_type']}\n")

    # Build output
    output = {
        "status": "attempt_recorded",
        "heal_attempt": heal_attempts,
        "error_type": error_analysis["error_type"],
        "model": model,
        "severity": error_analysis["severity"],
        "attempt_file": str(attempt_file),
        "heal_prompt": heal_prompt,
        "instruction": f"Execute healing using {model} model. Prompt saved to {attempt_file}",
    }

    print(json.dumps(output, indent=2))
    return output


def cmd_rollback():
    """Rollback to last checkpoint."""
    state = load_state()
    if not state:
        output = {"error": "No active project"}
        print(json.dumps(output, indent=2))
        return output

    project_path = Path(state.get("project_path", ""))
    if not project_path.exists():
        output = {"error": f"Project path not found: {project_path}"}
        print(json.dumps(output, indent=2))
        return output

    # Find latest checkpoint
    checkpoints_dir = project_path / "checkpoints"
    if not checkpoints_dir.exists():
        output = {"error": "No checkpoints directory found"}
        print(json.dumps(output, indent=2))
        return output

    checkpoints = sorted(checkpoints_dir.glob("*.json"))
    if not checkpoints:
        output = {"error": "No checkpoints found"}
        print(json.dumps(output, indent=2))
        return output

    latest_checkpoint = checkpoints[-1]

    try:
        checkpoint_state = json.loads(latest_checkpoint.read_text())

        # Restore state
        save_state(checkpoint_state)

        # Log rollback
        log_file = project_path / "decisions.log"
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Rolled back to checkpoint: {latest_checkpoint.name}\n")

        output = {
            "status": "rolled_back",
            "checkpoint_file": str(latest_checkpoint),
            "phase": checkpoint_state.get("phase", "unknown"),
            "heal_attempts": checkpoint_state.get("heal_attempts", 0),
            "message": "State restored to last checkpoint",
        }

        print(json.dumps(output, indent=2))
        return output

    except (json.JSONDecodeError, KeyError) as e:
        output = {"error": f"Failed to load checkpoint: {str(e)}"}
        print(json.dumps(output, indent=2))
        return output


def cmd_history():
    """Show healing history for current project."""
    state = load_state()
    if not state:
        output = {"error": "No active project"}
        print(json.dumps(output, indent=2))
        return output

    project_path = Path(state.get("project_path", ""))
    healing_dir = project_path / "healing-attempts" if project_path.exists() else get_healing_dir()

    if not healing_dir.exists():
        output = {
            "status": "no_history",
            "project_id": state.get("project_id", "unknown"),
            "heal_attempts": 0,
            "attempts": [],
        }
        print(json.dumps(output, indent=2))
        return output

    # Collect healing attempts
    attempts = []
    for attempt_file in sorted(healing_dir.glob("attempt-*.md")):
        try:
            content = attempt_file.read_text()

            # Extract key info
            error_type = "unknown"
            model = "unknown"
            timestamp = "unknown"

            if "**Type**: " in content:
                error_type = content.split("**Type**: ")[1].split("\n")[0].strip()
            if "**Model**: " in content:
                model = content.split("**Model**: ")[1].split("\n")[0].strip()
            if "## Timestamp" in content:
                timestamp = content.split("## Timestamp")[1].split("\n")[1].strip()

            attempts.append({
                "attempt_number": int(attempt_file.stem.split("-")[1]),
                "file": str(attempt_file),
                "error_type": error_type,
                "model": model,
                "timestamp": timestamp,
            })
        except Exception:
            continue

    output = {
        "status": "history",
        "project_id": state.get("project_id", "unknown"),
        "heal_attempts": len(attempts),
        "attempts": attempts,
    }

    print(json.dumps(output, indent=2))
    return output


def cmd_clear():
    """Clear error counts (reset circuit breaker)."""
    state = load_state()
    if not state:
        output = {"error": "No active project"}
        print(json.dumps(output, indent=2))
        return output

    # Clear error counts
    if "circuit_breakers" in state:
        state["circuit_breakers"]["error_counts"] = {}

    # Reset heal attempts
    state["heal_attempts"] = 0

    save_state(state)

    project_path = Path(state.get("project_path", ""))
    if project_path.exists():
        log_file = project_path / "decisions.log"
        with open(log_file, "a") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Error counts cleared - circuit breaker reset\n")

    output = {
        "status": "cleared",
        "message": "Error counts cleared and heal attempts reset to 0",
    }

    print(json.dumps(output, indent=2))
    return output


def cmd_status():
    """Show healer status for current project."""
    state = load_state()
    if not state:
        output = {"error": "No active project"}
        print(json.dumps(output, indent=2))
        return output

    project_path = Path(state.get("project_path", ""))
    healing_dir = project_path / "healing-attempts" if project_path.exists() else get_healing_dir()

    # Count attempts
    attempt_count = len(list(healing_dir.glob("attempt-*.md"))) if healing_dir.exists() else 0

    # Get error counts
    breakers = state.get("circuit_breakers", {})
    error_counts = breakers.get("error_counts", {})

    # Build status
    output = {
        "status": "active" if state else "no_project",
        "project_id": state.get("project_id", "unknown"),
        "phase": state.get("phase", "unknown"),
        "heal_attempts": state.get("heal_attempts", 0),
        "max_heal_attempts": 5,
        "attempt_files": attempt_count,
        "unique_errors": len(error_counts),
        "error_counts": error_counts,
        "healing_dir": str(healing_dir),
    }

    print(json.dumps(output, indent=2))
    return output


def main():
    parser = argparse.ArgumentParser(
        description="QRALPH Healer v1.0 - Self-healing coordinator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Analyze an error
    python3 qralph-healer.py analyze "No module named 'requests'"

    # Record healing attempt
    python3 qralph-healer.py attempt "TypeError: expected str, got int"

    # Show healing history
    python3 qralph-healer.py history

    # Rollback to last checkpoint
    python3 qralph-healer.py rollback

    # Clear error counts
    python3 qralph-healer.py clear

    # Show healer status
    python3 qralph-healer.py status
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze error and suggest fix")
    analyze_parser.add_argument("error", help="Error message to analyze")

    # attempt
    attempt_parser = subparsers.add_parser("attempt", help="Record healing attempt")
    attempt_parser.add_argument("error", help="Error message to heal")

    # rollback
    subparsers.add_parser("rollback", help="Rollback to last checkpoint")

    # history
    subparsers.add_parser("history", help="Show healing history")

    # clear
    subparsers.add_parser("clear", help="Clear error counts (reset circuit breaker)")

    # status
    subparsers.add_parser("status", help="Show healer status")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args.error)
    elif args.command == "attempt":
        cmd_attempt(args.error)
    elif args.command == "rollback":
        cmd_rollback()
    elif args.command == "history":
        cmd_history()
    elif args.command == "clear":
        cmd_clear()
    elif args.command == "status":
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
