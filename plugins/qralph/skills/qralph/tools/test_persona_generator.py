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
    # When NO domain keywords match, falls back to Riley/Sam
    archetypes = suggest_archetypes("make something nice happen")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" in names
    assert "Sam" in names


# ---------------------------------------------------------------------------
# REQ-201: CLI/DevTools domain personas
# ---------------------------------------------------------------------------

def test_suggest_archetypes_cli_tool():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("build a CLI tool for deployments")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    # Must NOT fall back to generic Riley/Sam
    assert "Riley" not in names
    assert "Sam" not in names


def test_suggest_archetypes_cli_via_plugin_keyword():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("create a plugin sdk for editors")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


# ---------------------------------------------------------------------------
# REQ-202: API/Backend domain personas
# ---------------------------------------------------------------------------

def test_suggest_archetypes_api_backend():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("design a REST API with graphql endpoints")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


def test_suggest_archetypes_backend_server_keyword():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("build a backend server for data processing")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


# ---------------------------------------------------------------------------
# REQ-203: Mobile domain personas
# ---------------------------------------------------------------------------

def test_suggest_archetypes_mobile():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("build a mobile app for iOS and Android")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


def test_suggest_archetypes_mobile_via_flutter():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("create a flutter cross-platform app")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


# ---------------------------------------------------------------------------
# REQ-204: Security/Audit domain personas
# ---------------------------------------------------------------------------

def test_suggest_archetypes_security():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("build a vulnerability audit tool for compliance")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


def test_suggest_archetypes_security_via_pentest():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("create a pentest reporting dashboard")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


# ---------------------------------------------------------------------------
# REQ-205: Content/Marketing domain personas
# ---------------------------------------------------------------------------

def test_suggest_archetypes_content_marketing():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("build a blog and landing page with seo optimization")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


def test_suggest_archetypes_marketing_via_copy():
    from persona_generator import suggest_archetypes
    archetypes = suggest_archetypes("write marketing copy for a campaign")
    assert len(archetypes) >= 2
    names = [a["name"] for a in archetypes]
    assert "Riley" not in names
    assert "Sam" not in names


# ---------------------------------------------------------------------------
# REQ-206: All returned personas have required fields
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = ["name", "role", "goals", "pain_points", "tech_comfort", "success_criteria"]

def _assert_valid_persona(persona: dict) -> None:
    for field in _REQUIRED_FIELDS:
        assert field in persona, f"Persona missing field: {field}"
    assert isinstance(persona["goals"], list) and len(persona["goals"]) > 0
    assert isinstance(persona["pain_points"], list) and len(persona["pain_points"]) > 0
    assert persona["tech_comfort"] in ("low", "medium", "high")
    assert isinstance(persona["success_criteria"], str) and persona["success_criteria"]


def test_all_domain_personas_have_required_fields():
    from persona_generator import suggest_archetypes
    requests = [
        "build a CLI tool",
        "design a REST API",
        "create a mobile app",
        "build a security audit tool",
        "write marketing content for seo",
        "build a SaaS dashboard",
        "create an ecommerce store with cart",
        "make something nice happen",  # fallback
    ]
    for req in requests:
        archetypes = suggest_archetypes(req)
        assert len(archetypes) >= 2, f"Too few archetypes for: {req}"
        for persona in archetypes:
            _assert_valid_persona(persona)


# ---------------------------------------------------------------------------
# REQ-207: Import shim works
# ---------------------------------------------------------------------------

def test_import_shim_works():
    import importlib
    import persona_generator as pg
    assert callable(pg.suggest_archetypes)
    assert callable(pg.generate_persona_template)
    assert callable(pg.generate_persona_review_prompt)


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
