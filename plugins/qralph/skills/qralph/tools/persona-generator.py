"""Persona generator for the QRALPH pipeline.

Generates user persona templates, review prompts with severity classification,
and suggests archetype personas based on project type keywords.
"""

from __future__ import annotations

import json
import re
import sys


# ---------------------------------------------------------------------------
# 1. Generate markdown persona template
# ---------------------------------------------------------------------------

def generate_persona_template(persona: dict) -> str:
    """Generate a markdown persona file from a persona dict.

    Expected keys: name, role, goals (list), pain_points (list),
    tech_comfort, success_criteria.
    """
    name = persona.get("name", "Unknown")
    role = persona.get("role", "User")
    goals = persona.get("goals", [])
    pain_points = persona.get("pain_points", [])
    tech_comfort = persona.get("tech_comfort", "medium")
    success_criteria = persona.get("success_criteria", "")

    goals_md = "\n".join(f"- {g}" for g in goals) if goals else "- (none specified)"
    pains_md = "\n".join(f"- {p}" for p in pain_points) if pain_points else "- (none specified)"

    return f"""# Persona: {name}

## Role
{role}

## Goals
{goals_md}

## Pain Points
{pains_md}

## Tech Comfort
{tech_comfort}

## Success Criteria
{success_criteria}
""".strip() + "\n"


# ---------------------------------------------------------------------------
# 2. Generate persona-based review prompt
# ---------------------------------------------------------------------------

def generate_persona_review_prompt(persona_md: str, request: str) -> str:
    """Generate an agent review prompt from a persona markdown and project request.

    The prompt instructs the reviewer to evaluate from the persona's perspective
    using P0/P1/P2 severity and confidence scoring.
    """
    # Extract persona name from first heading
    name_match = re.search(r"#\s+(?:Persona:\s*)?(.+)", persona_md)
    persona_name = name_match.group(1).strip() if name_match else "the persona"

    return f"""You are reviewing the following project request as **{persona_name}**.

## Project Request
{request}

## Persona Context
{persona_md}

## Review Instructions

Evaluate the project from {persona_name}'s perspective. For every issue you
identify, classify it with a severity level and a confidence score.

### Severity Levels
- **P0** — Blocker: prevents the persona from achieving their primary goal.
- **P1** — Major: significantly degrades the persona's experience.
- **P2** — Minor: a rough edge that could be improved but is not blocking.

### Confidence Scoring
For each finding, state your **confidence** level:
- **high** — strong evidence from the request or persona context.
- **medium** — reasonable inference but not explicitly stated.
- **low** — speculative; worth flagging but uncertain.

### Output Format

For each finding provide:
1. A short title.
2. Severity (P0 / P1 / P2).
3. Confidence (high / medium / low).
4. A concrete suggestion or fix — do not give vague feedback.

End with a summary of the top three changes that would most improve the
experience for {persona_name}.
""".strip() + "\n"


# ---------------------------------------------------------------------------
# 3. Suggest archetype personas based on project type
# ---------------------------------------------------------------------------

_SAAS_KEYWORDS = {"saas", "b2b", "dashboard", "subscription", "multi-tenant", "tenant"}
_ECOMMERCE_KEYWORDS = {"ecommerce", "e-commerce", "store", "shop", "cart", "checkout", "marketplace"}

_SAAS_ARCHETYPES = [
    {
        "name": "Jordan",
        "role": "Admin / Power User",
        "goals": ["Configure the product for their team", "Monitor usage and billing"],
        "pain_points": ["Complex permission models", "Unclear audit trails"],
        "tech_comfort": "high",
        "success_criteria": "Can onboard a new team member in under 10 minutes",
    },
    {
        "name": "Priya",
        "role": "End User",
        "goals": ["Complete daily tasks efficiently", "Find features without training"],
        "pain_points": ["Feature overload", "Slow load times"],
        "tech_comfort": "medium",
        "success_criteria": "Can complete core workflow without consulting docs",
    },
    {
        "name": "Dana",
        "role": "Evaluator / Decision Maker",
        "goals": ["Assess ROI quickly", "Compare with alternatives"],
        "pain_points": ["Hidden pricing", "No free trial"],
        "tech_comfort": "medium",
        "success_criteria": "Can determine product fit in one demo session",
    },
]

_ECOMMERCE_ARCHETYPES = [
    {
        "name": "Casey",
        "role": "Casual Shopper",
        "goals": ["Browse and discover products", "Check out quickly"],
        "pain_points": ["Forced account creation", "Slow mobile experience"],
        "tech_comfort": "low",
        "success_criteria": "Can find and purchase a product in under 3 minutes",
    },
    {
        "name": "Morgan",
        "role": "Comparison Shopper",
        "goals": ["Compare specs and prices", "Read reviews"],
        "pain_points": ["Missing product details", "No side-by-side comparison"],
        "tech_comfort": "medium",
        "success_criteria": "Can compare three products without leaving the site",
    },
]

_DEFAULT_ARCHETYPES = [
    {
        "name": "Riley",
        "role": "Primary User",
        "goals": ["Accomplish their main task", "Get reliable results"],
        "pain_points": ["Unclear error messages", "Steep learning curve"],
        "tech_comfort": "medium",
        "success_criteria": "Can complete the core use case on first attempt",
    },
    {
        "name": "Sam",
        "role": "New User",
        "goals": ["Understand what the product does", "Get started without help"],
        "pain_points": ["Missing onboarding", "Jargon-heavy docs"],
        "tech_comfort": "low",
        "success_criteria": "Can finish onboarding in under 5 minutes",
    },
]


def suggest_archetypes(request: str) -> list[dict]:
    """Suggest default persona archetypes based on project-type keywords."""
    tokens = set(re.findall(r"[a-z0-9\-]+", request.lower()))

    if tokens & _SAAS_KEYWORDS:
        return [dict(a) for a in _SAAS_ARCHETYPES]
    if tokens & _ECOMMERCE_KEYWORDS:
        return [dict(a) for a in _ECOMMERCE_ARCHETYPES]
    return [dict(a) for a in _DEFAULT_ARCHETYPES]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Simple CLI for quick testing."""
    if len(sys.argv) < 2:
        print("Usage: persona-generator.py <command> [args]")
        print("Commands:")
        print("  template <json-persona>   Generate persona markdown")
        print("  prompt <persona.md> <request>  Generate review prompt")
        print("  archetypes <request>      Suggest archetype personas")
        sys.exit(1)

    command = sys.argv[1]

    if command == "template":
        if len(sys.argv) < 3:
            print("Error: provide persona as JSON string", file=sys.stderr)
            sys.exit(1)
        persona = json.loads(sys.argv[2])
        print(generate_persona_template(persona))

    elif command == "prompt":
        if len(sys.argv) < 4:
            print("Error: provide persona markdown path and request string", file=sys.stderr)
            sys.exit(1)
        with open(sys.argv[2]) as f:
            persona_md = f.read()
        print(generate_persona_review_prompt(persona_md, sys.argv[3]))

    elif command == "archetypes":
        if len(sys.argv) < 3:
            print("Error: provide request string", file=sys.stderr)
            sys.exit(1)
        archetypes = suggest_archetypes(sys.argv[2])
        for a in archetypes:
            print(generate_persona_template(a))
            print("---\n")

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
