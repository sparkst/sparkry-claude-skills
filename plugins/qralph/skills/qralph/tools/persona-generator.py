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
_CLI_KEYWORDS = {"cli", "terminal", "command", "cli-tool", "plugin", "sdk", "shell", "argv"}
_API_KEYWORDS = {"api", "endpoint", "rest", "graphql", "server", "backend"}
_MOBILE_KEYWORDS = {"mobile", "ios", "android", "app", "react-native", "flutter"}
_SECURITY_KEYWORDS = {"security", "audit", "vulnerability", "compliance", "pentest"}
_CONTENT_KEYWORDS = {"content", "blog", "marketing", "landing", "seo", "copy"}

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

_CLI_ARCHETYPES = [
    {
        "name": "Dev",
        "role": "Developer Power User",
        "goals": ["Automate repetitive tasks", "Integrate tool into CI/CD pipeline"],
        "pain_points": ["Poor man-page documentation", "Inconsistent flag naming"],
        "tech_comfort": "high",
        "success_criteria": "Can run the tool non-interactively in a script without reading docs",
    },
    {
        "name": "Fen",
        "role": "First-Time Installer",
        "goals": ["Install and run successfully on first try", "Understand what the tool does"],
        "pain_points": ["Missing dependencies not surfaced clearly", "Cryptic error output"],
        "tech_comfort": "medium",
        "success_criteria": "Can install and execute a basic command within 5 minutes",
    },
]

_API_ARCHETYPES = [
    {
        "name": "Mira",
        "role": "API Consumer / Integrator",
        "goals": ["Integrate the API into their application quickly", "Handle errors gracefully"],
        "pain_points": ["Missing or outdated documentation", "Inconsistent response shapes"],
        "tech_comfort": "high",
        "success_criteria": "Can make an authenticated request and parse the response in under 30 minutes",
    },
    {
        "name": "Luca",
        "role": "API Maintainer",
        "goals": ["Maintain backward compatibility", "Monitor performance and error rates"],
        "pain_points": ["No versioning strategy", "Difficult to test breaking changes safely"],
        "tech_comfort": "high",
        "success_criteria": "Can deprecate an endpoint without breaking existing consumers",
    },
]

_MOBILE_ARCHETYPES = [
    {
        "name": "Cora",
        "role": "Mobile User on Slow Connection",
        "goals": ["Complete tasks with minimal data usage", "Recover gracefully from network drops"],
        "pain_points": ["Spinning loaders with no feedback", "Lost form data on reconnect"],
        "tech_comfort": "low",
        "success_criteria": "Can complete a core task on 3G without losing progress",
    },
    {
        "name": "Eli",
        "role": "Power User with Multiple Devices",
        "goals": ["Sync state seamlessly across phone and tablet", "Use advanced gestures and shortcuts"],
        "pain_points": ["Inconsistent sync", "Features missing on one platform"],
        "tech_comfort": "high",
        "success_criteria": "Can start a task on one device and finish it on another without data loss",
    },
]

_SECURITY_ARCHETYPES = [
    {
        "name": "Vera",
        "role": "Security Auditor",
        "goals": ["Identify vulnerabilities systematically", "Produce evidence-backed findings reports"],
        "pain_points": ["Tools that surface noise without prioritization", "No export for evidence artifacts"],
        "tech_comfort": "high",
        "success_criteria": "Can generate a prioritized findings report in one session",
    },
    {
        "name": "Raj",
        "role": "Compliance Officer",
        "goals": ["Map findings to regulatory controls (SOC 2, ISO 27001)", "Demonstrate remediation progress"],
        "pain_points": ["Jargon-heavy output not suited for exec reporting", "No audit trail on actions taken"],
        "tech_comfort": "medium",
        "success_criteria": "Can present findings to leadership mapped to compliance controls",
    },
]

_CONTENT_ARCHETYPES = [
    {
        "name": "Nia",
        "role": "Content Creator",
        "goals": ["Publish content quickly without developer help", "Optimize posts for search"],
        "pain_points": ["Slow publish workflow", "No built-in SEO guidance"],
        "tech_comfort": "low",
        "success_criteria": "Can write, preview, and publish a post in under 15 minutes",
    },
    {
        "name": "Felix",
        "role": "Marketing Manager",
        "goals": ["Track campaign performance", "A/B test landing page copy"],
        "pain_points": ["No analytics integration", "Hard to iterate on copy without re-deploying"],
        "tech_comfort": "medium",
        "success_criteria": "Can launch a campaign variant and measure results without engineering support",
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
    if tokens & _CLI_KEYWORDS:
        return [dict(a) for a in _CLI_ARCHETYPES]
    if tokens & _API_KEYWORDS:
        return [dict(a) for a in _API_ARCHETYPES]
    if tokens & _MOBILE_KEYWORDS:
        return [dict(a) for a in _MOBILE_ARCHETYPES]
    if tokens & _SECURITY_KEYWORDS:
        return [dict(a) for a in _SECURITY_ARCHETYPES]
    if tokens & _CONTENT_KEYWORDS:
        return [dict(a) for a in _CONTENT_ARCHETYPES]
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
