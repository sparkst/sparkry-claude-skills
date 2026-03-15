"""Step-specific agentic rules for QRALPH CLI decision agents."""
from __future__ import annotations

_DEFAULT_RULES = (
    "You are reviewing an unfamiliar pipeline phase. "
    "Apply general quality judgment: does the output make sense, "
    "is it complete, and is it consistent with the project brief? "
    "If anything looks wrong or ambiguous, escalate to the user "
    "rather than guessing."
)

_RULES: dict[str, str] = {
    "IDEATE_BRAINSTORM": (
        "IDEATE_BRAINSTORM: The goal is to generate a diverse set of creative "
        "directions from the user's prompt. Good output has at least 3 distinct "
        "angles that interpret the brief differently — not minor variations of "
        "the same idea. Confirm when ideas are genuinely diverse and grounded "
        "in the prompt. Reject when ideas are too similar, off-topic, or when "
        "the prompt was misunderstood. Escalate to the user when the prompt is "
        "ambiguous enough that two reasonable people would brainstorm in "
        "completely different directions."
    ),
    "IDEATE_WAITING": (
        "IDEATE_WAITING: The pipeline is waiting for ideation agents to return. "
        "Monitor for timeouts and empty responses. Good state: all spawned "
        "agents have reported back with substantive content. Confirm when "
        "all agents return valid output. Reject if any agent returns empty or "
        "malformed results. Escalate to the user if an agent is stuck or "
        "returns an error that suggests a systemic issue."
    ),
    "IDEATE_REVIEW": (
        "IDEATE_REVIEW: Evaluate the collected brainstorm results and select "
        "the strongest direction. Good output: a clear winner with reasoning "
        "for why it best serves the user's intent. Confirm when the selected "
        "direction aligns with the brief and is actionable. Reject when the "
        "selection contradicts the brief or picks a weak idea over a strong one. "
        "Escalate to the user when two or more directions are equally strong "
        "and the choice is a matter of taste, not quality."
    ),
    "PERSONA_GEN": (
        "PERSONA_GEN: Generate domain-expert personas that will evaluate the "
        "project concept. Good personas are relevant to the project domain, "
        "have distinct viewpoints, and cover different concerns (technical, "
        "user experience, business). Confirm when personas are diverse and "
        "domain-appropriate. Reject when personas are generic or redundant. "
        "Escalate to the user when the project domain is unusual enough that "
        "standard persona archetypes may not apply."
    ),
    "PERSONA_REVIEW": (
        "PERSONA_REVIEW: Validate that generated personas are fit for purpose. "
        "Good personas have clear expertise areas, distinct evaluation angles, "
        "and no significant domain gaps. Confirm when the persona panel covers "
        "the key dimensions of the project. Reject if personas overlap heavily "
        "or miss a critical perspective. Escalate to the user when the project "
        "spans multiple domains and you are unsure which expertise matters most."
    ),
    "CONCEPT_SPAWN": (
        "CONCEPT_SPAWN: Launch concept-synthesis agents with the selected "
        "direction and personas. Good spawning: each agent gets the right "
        "context, the persona assignment is clear, and no duplicate work is "
        "requested. Confirm when agents are properly configured and launched. "
        "Reject if agent configuration is incomplete or mismatched. Escalate "
        "to the user if the concept scope seems too large for a single "
        "synthesis pass."
    ),
    "CONCEPT_WAITING": (
        "CONCEPT_WAITING: The pipeline is waiting for concept-synthesis agents "
        "to return. Monitor for timeouts, partial results, and agent failures. "
        "Good state: all agents return structured concept documents within the "
        "expected timeframe. Confirm when all agents report back successfully. "
        "Reject if any agent returns a malformed or empty concept. Escalate to "
        "the user if multiple agents fail or if results are contradictory in "
        "ways that suggest a flawed brief."
    ),
    "CONCEPT_REVIEW": (
        "CONCEPT_REVIEW: Evaluate synthesized concepts for completeness, "
        "coherence, and alignment with the user's intent. Good concepts have "
        "clear scope, realistic deliverables, and no internal contradictions. "
        "Confirm when the concept is solid and ready for planning. Reject when "
        "the concept is vague, over-scoped, or misaligned with the brief. "
        "Escalate to the user when the concept makes trade-offs that only the "
        "user can decide (e.g., scope vs. timeline)."
    ),
    "INIT": (
        "INIT: Template selection — this is a high-value decision. The "
        "pipeline's keyword heuristic frequently picks the wrong template, and "
        "a wrong template wastes ALL downstream work. Be deeply skeptical of "
        "the heuristic's choice. Good template selection matches the project's "
        "actual deliverable type (web app, CLI tool, documentation, marketing "
        "site, etc.), not just surface keywords. Confirm ONLY when the template "
        "clearly matches the project's true nature. Reject when the heuristic "
        "has latched onto a keyword that doesn't reflect the real deliverable. "
        "Escalate to the user when the project doesn't fit any available "
        "template cleanly — a human picking 'closest fit' is better than an "
        "algorithm guessing wrong."
    ),
    "PLAN_WAITING": (
        "PLAN_WAITING: The pipeline is waiting for the planning agent to "
        "produce a project plan. This is the most consequential wait in the "
        "pipeline — a bad plan poisons all execution. Monitor for timeouts "
        "and incomplete plans. Good state: the planner returns a structured "
        "plan with clear phases, deliverables, and acceptance criteria. "
        "Confirm when the plan arrives complete. Reject if the plan is "
        "truncated or missing sections. Escalate to the user if the planner "
        "is taking unusually long, which may indicate the project is too "
        "complex for automated planning."
    ),
    "PLAN_REVIEW": (
        "PLAN_REVIEW: This is the MOST CONSEQUENTIAL decision in the entire "
        "pipeline. A flawed plan that gets approved will produce flawed work "
        "across every downstream phase. Evaluate the plan for: (1) correct "
        "scope — does it match what the user actually asked for, not what the "
        "template assumes? (2) realistic effort — are story point estimates "
        "plausible? (3) completeness — are there missing phases or forgotten "
        "deliverables? (4) technical soundness — does the architecture make "
        "sense? Confirm ONLY when the plan is genuinely solid across all four "
        "dimensions. Reject when any dimension is weak and fixable by "
        "re-planning. Escalate to the user when the plan reveals that the "
        "project is more complex than the brief suggested, or when scope "
        "trade-offs require human judgment. When in doubt, ALWAYS escalate — "
        "approving a bad plan is the most expensive mistake in the pipeline."
    ),
}


def get_rules(sub_phase: str) -> str:
    """Return decision rules string for a given sub-phase.

    Falls back to default rules for unknown phases.
    """
    return _RULES.get(sub_phase, _DEFAULT_RULES)
