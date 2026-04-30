"""Deterministic review team selector.

Classifies artifact domains via keyword/pattern matching and selects
the optimal review team from an agent catalog.  No LLM calls -- pure
Runner logic.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DomainScore:
    """A single domain relevance score."""

    domain: str
    score: float
    signals: list[str] = field(default_factory=list)


@dataclass
class AgentDef:
    """One review agent from the catalog."""

    name: str
    domains: list[str]
    model: str
    description: str
    review_lens: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_DOMAINS: list[str] = [
    "security",
    "architecture",
    "frontend",
    "backend",
    "testing",
    "performance",
    "content",
    "strategy",
    "data",
    "compliance",
    "devops",
    "research",
]

# Keyword -> (domain, weight) mappings.
# Weights let strong signals (e.g. "gdpr") count more than weak ones.
_KEYWORD_RULES: list[tuple[str, str, float]] = [
    # security
    ("auth", "security", 0.40),
    ("token", "security", 0.35),
    ("credential", "security", 0.40),
    ("secret", "security", 0.30),
    ("encrypt", "security", 0.35),
    ("password", "security", 0.35),
    ("oauth", "security", 0.40),
    ("jwt", "security", 0.35),
    ("permission", "security", 0.30),
    # architecture
    ("architect", "architecture", 0.45),
    ("design", "architecture", 0.25),
    ("pattern", "architecture", 0.25),
    ("coupling", "architecture", 0.35),
    ("modular", "architecture", 0.30),
    ("interface", "architecture", 0.25),
    ("abstraction", "architecture", 0.30),
    # frontend
    ("react", "frontend", 0.45),
    ("component", "frontend", 0.30),
    ("css", "frontend", 0.40),
    ("styling", "frontend", 0.40),
    ("ui", "frontend", 0.35),
    ("ux", "frontend", 0.30),
    ("layout", "frontend", 0.30),
    ("responsive", "frontend", 0.30),
    ("html", "frontend", 0.35),
    # backend
    ("api", "backend", 0.40),
    ("endpoint", "backend", 0.40),
    ("route", "backend", 0.35),
    ("server", "backend", 0.30),
    ("middleware", "backend", 0.35),
    ("handler", "backend", 0.30),
    ("service", "backend", 0.25),
    # testing
    ("test", "testing", 0.40),
    ("spec", "testing", 0.35),
    ("coverage", "testing", 0.40),
    ("assert", "testing", 0.30),
    ("mock", "testing", 0.30),
    ("fixture", "testing", 0.30),
    # performance
    ("perf", "performance", 0.40),
    ("latency", "performance", 0.40),
    ("throughput", "performance", 0.40),
    ("cache", "performance", 0.35),
    ("optimize", "performance", 0.30),
    ("benchmark", "performance", 0.35),
    # content
    ("content", "content", 0.35),
    ("copy", "content", 0.25),
    ("editorial", "content", 0.35),
    ("article", "content", 0.30),
    ("blog", "content", 0.30),
    # strategy
    ("strategy", "strategy", 0.45),
    ("plan", "strategy", 0.30),
    ("roadmap", "strategy", 0.45),
    ("vision", "strategy", 0.30),
    ("objective", "strategy", 0.30),
    # data
    ("database", "data", 0.45),
    ("query", "data", 0.35),
    ("schema", "data", 0.40),
    ("migration", "data", 0.40),
    ("sql", "data", 0.40),
    ("model", "data", 0.25),
    # compliance
    ("gdpr", "compliance", 0.50),
    ("pci", "compliance", 0.50),
    ("hipaa", "compliance", 0.50),
    ("compliance", "compliance", 0.45),
    ("audit", "compliance", 0.35),
    ("regulation", "compliance", 0.40),
    # devops
    ("deploy", "devops", 0.40),
    ("ci", "devops", 0.35),
    ("docker", "devops", 0.45),
    ("k8s", "devops", 0.45),
    ("kubernetes", "devops", 0.45),
    ("pipeline", "devops", 0.30),
    ("terraform", "devops", 0.45),
    ("infrastructure", "devops", 0.35),
    # research
    ("research", "research", 0.45),
    ("analysis", "research", 0.30),
    ("investigation", "research", 0.35),
    ("study", "research", 0.25),
]

# File-extension -> (domain, weight) mappings.
_EXTENSION_RULES: list[tuple[str, str, float]] = [
    (".py", "backend", 0.25),
    (".ts", "backend", 0.20),
    (".ts", "frontend", 0.15),
    (".js", "backend", 0.15),
    (".js", "frontend", 0.15),
    (".tsx", "frontend", 0.40),
    (".jsx", "frontend", 0.40),
    (".css", "frontend", 0.40),
    (".scss", "frontend", 0.35),
    (".html", "frontend", 0.35),
    (".md", "content", 0.30),
    (".txt", "content", 0.25),
    (".doc", "content", 0.30),
    (".docx", "content", 0.30),
    (".sql", "data", 0.40),
    (".yml", "devops", 0.20),
    (".yaml", "devops", 0.20),
    ("Dockerfile", "devops", 0.40),
    (".tf", "devops", 0.40),
]


# ---------------------------------------------------------------------------
# Default catalog
# ---------------------------------------------------------------------------

_DEFAULT_CATALOG: list[dict[str, Any]] = [
    {
        "name": "requirements-reviewer",
        "domains": ALL_DOMAINS,
        "model": "sonnet",
        "description": "Universal requirements coverage reviewer",
        "review_lens": "requirements coverage and completeness",
    },
    {
        "name": "architecture-reviewer",
        "domains": ["architecture", "backend", "frontend", "data"],
        "model": "sonnet",
        "description": "Architectural soundness and design pattern reviewer",
        "review_lens": "architectural soundness, patterns, coupling",
    },
    {
        "name": "security-reviewer",
        "domains": ["security", "compliance", "backend"],
        "model": "sonnet",
        "description": "Security vulnerability and data protection reviewer",
        "review_lens": "security vulnerabilities, auth, data protection",
    },
    {
        "name": "ux-reviewer",
        "domains": ["frontend", "content"],
        "model": "haiku",
        "description": "User experience and accessibility reviewer",
        "review_lens": "user experience, accessibility, clarity",
    },
    {
        "name": "process-reviewer",
        "domains": ["strategy", "content", "compliance"],
        "model": "sonnet",
        "description": "Process integrity and completeness reviewer",
        "review_lens": "process integrity, completeness, rigor",
    },
    {
        "name": "code-quality-reviewer",
        "domains": ["backend", "frontend", "testing", "performance"],
        "model": "haiku",
        "description": "Code quality, testing, and performance reviewer",
        "review_lens": "code quality, test coverage, performance",
    },
    {
        "name": "domain-expert",
        "domains": ["data", "devops", "research"],
        "model": "sonnet",
        "description": "Domain-specific correctness and best practices reviewer",
        "review_lens": "domain-specific correctness and best practices",
    },
]


# ---------------------------------------------------------------------------
# Domain classification
# ---------------------------------------------------------------------------

def classify_domains(
    description: str,
    artifact_path: str | None = None,
) -> list[DomainScore]:
    """Score every domain based on keyword/pattern matching.

    Returns a list of ``DomainScore`` for each domain with score > 0,
    sorted descending by score (highest first).
    """
    scores: dict[str, float] = {d: 0.0 for d in ALL_DOMAINS}
    signals: dict[str, list[str]] = {d: [] for d in ALL_DOMAINS}

    desc_lower = description.lower()

    # --- keyword matching on description ---
    for keyword, domain, weight in _KEYWORD_RULES:
        if re.search(rf"\b{re.escape(keyword)}\b", desc_lower):
            scores[domain] += weight
            signals[domain].append(f"keyword:{keyword}")

    # --- file extension matching on artifact_path ---
    if artifact_path:
        path_obj = Path(artifact_path)
        ext = path_obj.suffix.lower()
        name = path_obj.name

        for rule_ext, domain, weight in _EXTENSION_RULES:
            if ext == rule_ext or name == rule_ext:
                scores[domain] += weight
                signals[domain].append(f"extension:{rule_ext}")

    # Clamp to [0, 1]
    for d in ALL_DOMAINS:
        scores[d] = min(scores[d], 1.0)

    result: list[DomainScore] = [
        DomainScore(domain=d, score=round(scores[d], 3), signals=signals[d])
        for d in ALL_DOMAINS
        if scores[d] > 0
    ]
    result.sort(key=lambda ds: ds.score, reverse=True)
    return result


# ---------------------------------------------------------------------------
# Agent catalog
# ---------------------------------------------------------------------------

def load_catalog(catalog_path: str | None = None) -> list[AgentDef]:
    """Load the agent catalog.

    If *catalog_path* points to a JSON file, read from it.
    Otherwise return the built-in default catalog.
    """
    if catalog_path:
        with open(catalog_path, "r", encoding="utf-8") as fh:
            raw: list[dict[str, Any]] = json.load(fh)
        required = ("name", "domains", "model", "description", "review_lens")
        agents: list[AgentDef] = []
        for i, entry in enumerate(raw):
            missing = [k for k in required if k not in entry]
            if missing:
                raise ValueError(
                    f"Catalog entry {i} missing required fields: {missing}"
                )
            agents.append(AgentDef(
                name=entry["name"],
                domains=entry["domains"],
                model=entry["model"],
                description=entry["description"],
                review_lens=entry["review_lens"],
            ))
        return agents

    return [
        AgentDef(
            name=entry["name"],
            domains=list(entry["domains"]),
            model=entry["model"],
            description=entry["description"],
            review_lens=entry["review_lens"],
        )
        for entry in _DEFAULT_CATALOG
    ]


# ---------------------------------------------------------------------------
# Team selection
# ---------------------------------------------------------------------------

def _score_agent(agent: AgentDef, domain_scores: list[DomainScore]) -> float:
    """Sum of domain scores for domains the agent covers."""
    domain_map = {ds.domain: ds.score for ds in domain_scores}
    return sum(domain_map.get(d, 0.0) for d in agent.domains)


def select_team_with_scores(
    description: str,
    artifact_path: str | None = None,
    min_reviewers: int = 2,
    max_reviewers: int = 5,
    catalog_path: str | None = None,
) -> tuple[list[AgentDef], list[DomainScore]]:
    """Select team and return (team, domain_scores) to avoid re-classification."""
    if min_reviewers < 2:
        min_reviewers = 2
    if max_reviewers < min_reviewers:
        max_reviewers = min_reviewers

    catalog = load_catalog(catalog_path)
    domain_scores = classify_domains(description, artifact_path)

    req_reviewer: AgentDef | None = None
    others: list[tuple[float, AgentDef]] = []

    for agent in catalog:
        score = _score_agent(agent, domain_scores)
        if agent.name == "requirements-reviewer":
            req_reviewer = agent
        else:
            others.append((score, agent))

    others.sort(key=lambda pair: pair[0], reverse=True)
    above_threshold = sum(1 for score, _ in others if score > 0.3)
    desired = max(min_reviewers, min(max_reviewers, above_threshold))

    team: list[AgentDef] = []
    if req_reviewer is not None:
        team.append(req_reviewer)

    slots_remaining = max(desired - len(team), 0)
    if len(team) < min_reviewers:
        slots_remaining = max(slots_remaining, min_reviewers - len(team))

    for _score, agent in others[:slots_remaining]:
        team.append(agent)

    team = team[:max_reviewers]

    if len(team) < min_reviewers:
        raise ValueError(
            f"Cannot assemble {min_reviewers} reviewers from catalog; "
            f"only {len(team)} available"
        )

    return team, domain_scores


def select_team(
    description: str,
    artifact_path: str | None = None,
    min_reviewers: int = 2,
    max_reviewers: int = 5,
    catalog_path: str | None = None,
) -> list[AgentDef]:
    """Select the optimal review team for the given artifact.

    R3 enforcement: min_reviewers is clamped to >= 2 at tool level.
    """
    team, _ = select_team_with_scores(
        description=description,
        artifact_path=artifact_path,
        min_reviewers=min_reviewers,
        max_reviewers=max_reviewers,
        catalog_path=catalog_path,
    )
    return team


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_markdown(
    team: list[AgentDef],
    domain_scores: list[DomainScore],
) -> str:
    lines: list[str] = []
    lines.append("## Detected Domains\n")
    if domain_scores:
        for ds in domain_scores:
            sig_str = ", ".join(ds.signals) if ds.signals else "none"
            lines.append(f"- **{ds.domain}** ({ds.score:.2f}) -- signals: {sig_str}")
    else:
        lines.append("- (none detected)")
    lines.append("")

    lines.append("## Selected Review Team\n")
    for i, agent in enumerate(team, 1):
        lines.append(f"{i}. **{agent.name}** ({agent.model})")
        lines.append(f"   - Lens: {agent.review_lens}")
        lines.append(f"   - Domains: {', '.join(agent.domains)}")
    lines.append("")
    return "\n".join(lines)


def _format_json(
    team: list[AgentDef],
    domain_scores: list[DomainScore],
) -> str:
    payload = {
        "domains": [asdict(ds) for ds in domain_scores],
        "team": [asdict(a) for a in team],
    }
    return json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select the optimal review team for an artifact.",
    )
    parser.add_argument("description", help="Description of the artifact to review")
    parser.add_argument("--artifact", default=None, help="Path to the artifact file")
    parser.add_argument("--catalog", default=None, help="Path to custom agent catalog JSON")
    parser.add_argument("--min", dest="min_reviewers", type=int, default=2, help="Minimum reviewers (default: 2)")
    parser.add_argument("--max", dest="max_reviewers", type=int, default=5, help="Maximum reviewers (default: 5)")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON instead of Markdown")

    args = parser.parse_args(argv)

    try:
        team, domain_scores = select_team_with_scores(
            args.description,
            artifact_path=args.artifact,
            min_reviewers=args.min_reviewers,
            max_reviewers=args.max_reviewers,
            catalog_path=args.catalog,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json_output:
        output = _format_json(team, domain_scores)
    else:
        output = _format_markdown(team, domain_scores)

    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
