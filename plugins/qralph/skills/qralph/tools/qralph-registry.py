#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
QRALPH Registry - Shared agent registry, domain keywords, and classification functions.

Extracted from qralph-orchestrator.py to avoid forcing consumers (subteam, watchdog)
to load the entire orchestrator just for these symbols.
"""

from typing import Any, Dict, List

# Domain keywords for request classification
DOMAIN_KEYWORDS = {
    "security": ["security", "auth", "authentication", "authorization", "encrypt",
                  "token", "password", "vulnerability", "owasp", "xss", "injection",
                  "csrf", "cors", "ssl", "tls", "secret", "credential"],
    "frontend": ["ui", "ux", "page", "component", "form", "button", "modal",
                  "dashboard", "layout", "responsive", "mobile", "css", "html",
                  "react", "vue", "angular", "svelte", "tailwind", "design",
                  "dark mode", "theme", "animation", "accessibility", "a11y"],
    "backend": ["api", "endpoint", "server", "database", "query", "migration",
                "rest", "graphql", "webhook", "middleware", "cron", "worker",
                "microservice", "queue", "cache", "redis", "postgres", "sql"],
    "architecture": ["architecture", "system design", "scalability", "pattern",
                     "refactor", "restructure", "monolith", "modular", "dependency",
                     "interface", "contract", "coupling", "cohesion"],
    "testing": ["test", "qa", "validation", "coverage", "e2e", "unit test",
                "integration test", "mock", "fixture", "assertion", "regression"],
    "devops": ["deploy", "ci", "cd", "pipeline", "docker", "kubernetes",
               "terraform", "infrastructure", "monitoring", "logging", "release"],
    "content": ["write", "article", "blog", "content", "copy", "documentation",
                "readme", "guide", "tutorial", "newsletter", "post"],
    "research": ["research", "analyze", "compare", "investigate", "evaluate",
                 "benchmark", "survey", "study", "report", "assessment"],
    "strategy": ["strategy", "plan", "roadmap", "business", "market", "pricing",
                 "growth", "acquisition", "retention", "monetization", "roi"],
    "data": ["data", "analytics", "metrics", "dashboard", "chart", "visualization",
             "etl", "pipeline", "warehouse", "reporting", "tracking"],
    "performance": ["performance", "optimize", "speed", "latency", "throughput",
                    "memory", "cpu", "profiling", "bottleneck", "benchmark"],
    "compliance": ["compliance", "gdpr", "ccpa", "hipaa", "sox", "regulation",
                   "privacy", "consent", "audit", "legal", "license"],
}

# Agent capabilities registry - maps agent types to their domains and model tiers
AGENT_REGISTRY = {
    # Core development agents
    "security-reviewer": {"domains": ["security", "compliance"], "model": "sonnet", "category": "security"},
    "architecture-advisor": {"domains": ["architecture", "backend", "performance"], "model": "sonnet", "category": "architecture"},
    "sde-iii": {"domains": ["backend", "architecture", "testing"], "model": "sonnet", "category": "implementation"},
    "requirements-analyst": {"domains": ["strategy", "architecture"], "model": "sonnet", "category": "planning"},
    "ux-designer": {"domains": ["frontend", "data"], "model": "sonnet", "category": "design"},
    "code-quality-auditor": {"domains": ["testing", "architecture"], "model": "haiku", "category": "quality"},
    "pe-reviewer": {"domains": ["architecture", "security", "performance"], "model": "sonnet", "category": "quality"},
    "pe-designer": {"domains": ["architecture", "backend"], "model": "sonnet", "category": "architecture"},
    "test-writer": {"domains": ["testing"], "model": "sonnet", "category": "testing"},
    "debugger": {"domains": ["backend", "testing", "performance"], "model": "sonnet", "category": "implementation"},
    "perf-optimizer": {"domains": ["performance", "backend"], "model": "sonnet", "category": "performance"},
    "integration-specialist": {"domains": ["backend", "devops", "architecture"], "model": "sonnet", "category": "integration"},
    "api-schema": {"domains": ["backend", "architecture"], "model": "haiku", "category": "api"},
    "migration-refactorer": {"domains": ["architecture", "backend"], "model": "sonnet", "category": "implementation"},
    "validation-specialist": {"domains": ["testing", "quality"], "model": "sonnet", "category": "testing"},
    "ux-tester": {"domains": ["frontend", "testing"], "model": "sonnet", "category": "testing"},
    # Planning & strategy agents
    "pm": {"domains": ["strategy", "research"], "model": "sonnet", "category": "planning"},
    "strategic-advisor": {"domains": ["strategy", "research"], "model": "sonnet", "category": "strategy"},
    "finance-consultant": {"domains": ["strategy", "data"], "model": "haiku", "category": "strategy"},
    "legal-expert": {"domains": ["compliance", "strategy"], "model": "sonnet", "category": "compliance"},
    "cos": {"domains": ["strategy"], "model": "opus", "category": "strategy"},
    # Research agents
    "research-director": {"domains": ["research"], "model": "sonnet", "category": "research"},
    "fact-checker": {"domains": ["research", "content"], "model": "haiku", "category": "research"},
    "source-evaluator": {"domains": ["research"], "model": "haiku", "category": "research"},
    "industry-signal-scout": {"domains": ["research", "strategy"], "model": "sonnet", "category": "research"},
    "dissent-moderator": {"domains": ["research", "strategy"], "model": "opus", "category": "research"},
    # Content agents
    "synthesis-writer": {"domains": ["content", "research"], "model": "opus", "category": "content"},
    "docs-writer": {"domains": ["content"], "model": "haiku", "category": "content"},
    # Operations agents
    "release-manager": {"domains": ["devops"], "model": "haiku", "category": "devops"},
}


def classify_domains(request: str) -> List[str]:
    """Classify which domains a request touches."""
    request_lower = request.lower()
    domain_scores: Dict[str, int] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in request_lower)
        if score > 0:
            domain_scores[domain] = score

    # Sort by score descending, return domain names
    ranked = sorted(domain_scores.items(), key=lambda x: -x[1])
    return [d for d, _ in ranked]


def score_capability(capability: Dict[str, Any], domains: List[str], request: str) -> float:
    """Score a capability's relevance to the request (0.0 - 1.0)."""
    score = 0.0
    cap_name = capability.get("name", "")
    cap_domains = capability.get("domains", [])
    cap_description = capability.get("description", "")

    # Domain overlap (primary signal)
    if cap_domains and domains:
        overlap = len(set(cap_domains) & set(domains))
        score += (overlap / max(len(domains), 1)) * 0.6

    # Name keyword match
    request_lower = request.lower()
    name_words = cap_name.replace("-", " ").replace("_", " ").lower().split()
    name_matches = sum(1 for w in name_words if w in request_lower)
    if name_words:
        score += (name_matches / len(name_words)) * 0.25

    # Description keyword match
    if cap_description:
        desc_words = cap_description.lower().split()
        desc_matches = sum(1 for w in desc_words if w in request_lower)
        if desc_words:
            score += (desc_matches / len(desc_words)) * 0.15

    return min(score, 1.0)
