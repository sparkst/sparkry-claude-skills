"""Action handlers for QRALPH CLI."""
from __future__ import annotations

from pathlib import Path

_DETERMINISTIC_ACTIONS = frozenset({
    "define_tasks",
    "demo_feedback",
    "demo_replan",
    "backtrack_replan",
    "complete",
    "quality_dashboard",
    "learn_complete",
    "smoke_results",
})

_ALWAYS_ESCALATE_ACTIONS = frozenset({
    "escalate_to_user",
    "error",
})


def classify_action(action: dict) -> str:
    """Classify a pipeline response into a dispatch category.

    The *action* dict is the full pipeline response where the action type
    lives at ``action["action"]`` (a string like ``"spawn_agents"``).

    Returns one of: "deterministic", "work_agent", "decision_agent", "user_gate".
    """
    action_type: str = action.get("action", "")

    if action_type in _DETERMINISTIC_ACTIONS:
        return "deterministic"

    if action_type == "spawn_agents":
        return "work_agent"

    if action_type in _ALWAYS_ESCALATE_ACTIONS:
        return "decision_agent"

    if action_type.startswith("confirm_"):
        if should_escalate_gate(action):
            return "decision_agent"
        return "deterministic"

    # Unknown action -- escalate to be safe
    return "decision_agent"


def should_escalate_gate(action: dict) -> bool:
    """Determine if a confirm gate needs a decision agent.

    For confirm_template: escalate when top two scores differ by < 2.
    For all other confirm types: always escalate.
    """
    action_type: str = action.get("action", "")

    if action_type == "confirm_template":
        scores: dict = action.get("scores", {})
        if len(scores) < 2:
            return True
        sorted_values = sorted(scores.values(), reverse=True)
        return (sorted_values[0] - sorted_values[1]) < 2

    # confirm_concept, confirm_plan, confirm_ideation, confirm_personas,
    # and any unknown confirm type -- always escalate
    return True


def handle_spawn_agents(action: dict, working_dir: str = "") -> list[dict]:
    """Convert a spawn_agents action into command config dicts.

    Each dict contains: name, model, prompt, output_file.
    The working_dir parameter is accepted for caller compatibility but unused.
    """
    agents: list[dict] = action.get("agents", [])
    output_dir: str = action.get("output_dir", "")
    output_path = Path(output_dir)

    return [
        {
            "name": agent["name"],
            "model": agent["model"],
            "prompt": agent["prompt"],
            "output_file": str(output_path / f"{agent['name']}.md"),
        }
        for agent in agents
    ]
