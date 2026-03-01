import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def test_generate_persona_template():
    from persona_generator import generate_persona_template
    persona = {
        "name": "Sarah",
        "role": "First-time user",
        "goals": ["Get started quickly", "Understand pricing"],
        "pain_points": ["Overwhelmed by options", "Not technical"],
        "tech_comfort": "low",
        "success_criteria": "Can complete onboarding in under 5 minutes",
    }
    template = generate_persona_template(persona)
    assert "Sarah" in template
    assert "First-time user" in template
    assert "Get started quickly" in template
    assert "low" in template.lower()


def test_generate_review_prompt_has_severity():
    from persona_generator import generate_persona_review_prompt
    persona_md = "# Sarah\n## Role: First-time user\n## Goals: Get started quickly"
    prompt = generate_persona_review_prompt(persona_md, "Build a task management SaaS app")
    assert "Sarah" in prompt
    assert "task management" in prompt.lower()
    assert "P0" in prompt
    assert "P1" in prompt
    assert "P2" in prompt
    assert "Confidence" in prompt or "confidence" in prompt


def test_suggest_archetypes_saas():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("build a B2B SaaS dashboard")
    assert len(archetypes) >= 2
    roles = [a["role"].lower() for a in archetypes]
    assert any("admin" in r or "power" in r for r in roles)


def test_suggest_archetypes_ecommerce():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("build an online store for bike parts")
    assert len(archetypes) >= 2


def test_suggest_archetypes_default():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("create a CLI tool for file processing")
    assert len(archetypes) >= 2


def test_persona_template_has_all_sections():
    from persona_generator import generate_persona_template
    persona = {
        "name": "Alex",
        "role": "Admin",
        "goals": ["Manage team"],
        "pain_points": ["Complex setup"],
        "tech_comfort": "high",
        "success_criteria": "Configure product in one session",
    }
    template = generate_persona_template(persona)
    assert "# Persona:" in template or "# " in template
    assert "Role" in template
    assert "Goals" in template
    assert "Pain Points" in template
    assert "Tech Comfort" in template or "Comfort" in template
    assert "Success" in template


def test_review_prompt_requests_concrete_suggestions():
    from persona_generator import generate_persona_review_prompt
    persona_md = "# Test User\n## Role: Tester"
    prompt = generate_persona_review_prompt(persona_md, "build an app")
    assert "suggest" in prompt.lower() or "fix" in prompt.lower() or "concrete" in prompt.lower()
