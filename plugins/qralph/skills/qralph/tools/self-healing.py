"""Self-healing rules for QRALPH pipeline resilience.

Rules are Python constants (not JSON) for determinism and testability.
Heal counters are stored in project state under state["heal_patterns"].
The LEARN phase can only update counters, not add or modify rules.

This module provides condition matching only. The pipeline dispatches
actions inline. qralph-healer.py remains the separate catastrophic
rollback tool.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


VALID_ACTIONS = frozenset({
    "RE_SPAWN_AGENT",
    "RETRY_WITH_MANIFEST_CWD",
    "RESUME_FROM_CHECKPOINT",
    "FORCE_ADVANCE",
    "ESCALATE_TO_USER",
})

SELF_HEAL_RULES: list[dict[str, Any]] = [
    {
        "id": "SH-001",
        "condition": "agent_timeout",
        "description": "Agent spawned but produced no output within model-tier timeout",
        "action": "RE_SPAWN_AGENT",
        "max_attempts": 1,
    },
    {
        "id": "SH-002",
        "condition": "quality_gate_wrong_cwd",
        "description": "Quality gate ran at repo root instead of project site_dir",
        "action": "RETRY_WITH_MANIFEST_CWD",
        "max_attempts": 1,
    },
    {
        "id": "SH-003",
        "condition": "session_stale",
        "description": "More than 30min since last pipeline activity in a waiting phase",
        "action": "RESUME_FROM_CHECKPOINT",
        "max_attempts": 1,
    },
    {
        "id": "SH-004",
        "condition": "convergence_regression",
        "description": "P0 count increased between quality review rounds",
        "action": "FORCE_ADVANCE",
        "max_attempts": 1,
    },
]

_KNOWN_RULE_IDS = frozenset(r["id"] for r in SELF_HEAL_RULES)

HEAL_COOLDOWN_SECONDS = 3600


def validate_rule(rule: dict) -> list[str]:
    """Validate a rule dict against the schema. Returns list of errors (empty = valid)."""
    errors = []
    for field in ("id", "condition", "action", "max_attempts"):
        if field not in rule:
            errors.append(f"Missing required field: {field}")
    if "action" in rule and rule["action"] not in VALID_ACTIONS:
        errors.append(f"Invalid action: {rule['action']}. Must be one of {sorted(VALID_ACTIONS)}")
    if "max_attempts" in rule and (not isinstance(rule["max_attempts"], int) or rule["max_attempts"] < 1):
        errors.append(f"max_attempts must be int >= 1, got {rule.get('max_attempts')}")
    return errors


def match_condition(condition_name: str, context: dict) -> dict | None:
    """Find a rule matching the given condition name. Returns rule dict or None."""
    for rule in SELF_HEAL_RULES:
        if rule["condition"] == condition_name:
            return dict(rule)
    return None


def learn_update_counters(rule_id: str, outcome: str, state: dict) -> bool:
    """Update success/failure counters for a known rule.

    Args:
        rule_id: Must be in _KNOWN_RULE_IDS
        outcome: "success" or "failure"
        state: Project state dict — modifies state["heal_patterns"] in place

    Returns True if updated, False if rule_id unknown or outcome invalid.
    """
    if rule_id not in _KNOWN_RULE_IDS:
        return False
    if outcome not in ("success", "failure"):
        return False

    patterns = state.setdefault("heal_patterns", {})
    counters = patterns.setdefault(rule_id, {"success_count": 0, "failure_count": 0})
    counters[f"{outcome}_count"] = counters.get(f"{outcome}_count", 0) + 1
    return True


def is_heal_on_cooldown(last_heal_at: str | None) -> bool:
    """Check if the heal cooldown period (60min) has not yet elapsed."""
    if not last_heal_at:
        return False
    try:
        last = datetime.fromisoformat(last_heal_at)
        elapsed = (datetime.now() - last).total_seconds()
        return elapsed < HEAL_COOLDOWN_SECONDS
    except (ValueError, TypeError):
        return False
