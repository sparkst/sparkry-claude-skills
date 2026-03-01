#!/usr/bin/env python3
"""
Unit tests for QRALPH Registry - shared agent registry and domain classification.

REQ-QRALPH-030: AGENT_REGISTRY contains required agents with correct schema
REQ-QRALPH-031: DOMAIN_KEYWORDS covers required domains with sufficient keywords
REQ-QRALPH-032: classify_domains returns ranked domains for known requests
REQ-QRALPH-033: score_capability returns 0.0-1.0, handles edge cases
"""

import sys
from pathlib import Path

import importlib.util
sys.path.insert(0, str(Path(__file__).parent))

# Load qralph-registry.py
registry_path = Path(__file__).parent / "qralph-registry.py"
spec_reg = importlib.util.spec_from_file_location("qralph_registry", registry_path)
qralph_registry = importlib.util.module_from_spec(spec_reg)
spec_reg.loader.exec_module(qralph_registry)

AGENT_REGISTRY = qralph_registry.AGENT_REGISTRY
DOMAIN_KEYWORDS = qralph_registry.DOMAIN_KEYWORDS
classify_domains = qralph_registry.classify_domains
score_capability = qralph_registry.score_capability


# ============================================================================
# AGENT_REGISTRY
# ============================================================================


def test_agent_registry_has_required_agents():
    """REQ-QRALPH-030: Registry includes critical agents."""
    required = ["sde-iii", "security-reviewer", "architecture-advisor", "pe-reviewer",
                "test-writer", "debugger", "release-manager"]
    for agent in required:
        assert agent in AGENT_REGISTRY, f"Missing required agent: {agent}"


def test_agent_registry_schema():
    """REQ-QRALPH-030: Each agent has domains (list), model (str), category (str)."""
    for name, info in AGENT_REGISTRY.items():
        assert "domains" in info, f"{name} missing 'domains'"
        assert isinstance(info["domains"], list), f"{name} domains not a list"
        assert len(info["domains"]) >= 1, f"{name} has no domains"
        assert "model" in info, f"{name} missing 'model'"
        assert info["model"] in ("haiku", "sonnet", "opus"), f"{name} invalid model: {info['model']}"
        assert "category" in info, f"{name} missing 'category'"


def test_agent_registry_has_all_model_tiers():
    """REQ-QRALPH-030: Registry uses all three model tiers."""
    models = {info["model"] for info in AGENT_REGISTRY.values()}
    assert models == {"haiku", "sonnet", "opus"}


# ============================================================================
# DOMAIN_KEYWORDS
# ============================================================================


def test_domain_keywords_has_required_domains():
    """REQ-QRALPH-031: All 12 domains present."""
    required = ["security", "frontend", "backend", "architecture", "testing",
                "devops", "content", "research", "strategy", "data",
                "performance", "compliance"]
    for domain in required:
        assert domain in DOMAIN_KEYWORDS, f"Missing domain: {domain}"


def test_domain_keywords_minimum_keywords():
    """REQ-QRALPH-031: Each domain has at least 3 keywords."""
    for domain, keywords in DOMAIN_KEYWORDS.items():
        assert len(keywords) >= 3, f"Domain '{domain}' has only {len(keywords)} keywords"


# ============================================================================
# classify_domains
# ============================================================================


def test_classify_domains_security_request():
    """REQ-QRALPH-032: Security-related request ranks security first."""
    domains = classify_domains("Fix the authentication vulnerability and add CSRF protection")
    assert len(domains) > 0
    assert domains[0] == "security"


def test_classify_domains_frontend_request():
    """REQ-QRALPH-032: Frontend request ranks frontend first."""
    domains = classify_domains("Build a responsive dashboard with dark mode and CSS animations")
    assert len(domains) > 0
    assert domains[0] == "frontend"


def test_classify_domains_multi_domain():
    """REQ-QRALPH-032: Request touching multiple domains returns all relevant ones."""
    domains = classify_domains("Deploy the API server with monitoring and logging")
    assert "backend" in domains
    assert "devops" in domains


def test_classify_domains_empty_request():
    """REQ-QRALPH-032: Empty request returns empty list."""
    assert classify_domains("") == []


def test_classify_domains_no_match():
    """REQ-QRALPH-032: Unrelated text returns empty list."""
    assert classify_domains("xyzzy foobar baz") == []


# ============================================================================
# score_capability
# ============================================================================


def test_score_capability_range():
    """REQ-QRALPH-033: Score is always between 0.0 and 1.0."""
    cap = {"name": "security-reviewer", "domains": ["security"], "description": "Reviews security"}
    score = score_capability(cap, ["security"], "Fix security vulnerability")
    assert 0.0 <= score <= 1.0


def test_score_capability_high_relevance():
    """REQ-QRALPH-033: Matching domains + name gives high score."""
    cap = {"name": "security-reviewer", "domains": ["security", "compliance"], "description": "Reviews security"}
    score = score_capability(cap, ["security", "compliance"], "security review of compliance code")
    assert score > 0.3


def test_score_capability_no_overlap():
    """REQ-QRALPH-033: No domain overlap gives low score."""
    cap = {"name": "docs-writer", "domains": ["content"], "description": "Write documentation"}
    score = score_capability(cap, ["security"], "Fix authentication bug")
    assert score < 0.3


def test_score_capability_empty_inputs():
    """REQ-QRALPH-033: Empty capability returns 0.0."""
    assert score_capability({}, [], "") == 0.0


def test_score_capability_no_domains():
    """REQ-QRALPH-033: Capability with no domains scores only on name/description."""
    cap = {"name": "security-reviewer", "domains": [], "description": ""}
    score = score_capability(cap, ["security"], "security review")
    assert 0.0 <= score <= 1.0
