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
from dataclasses import asdict, dataclass, field, replace
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


@dataclass
class Complexity:
    """Deterministic change-complexity signals used to tier reviewer models.

    file_count        -- number of files the change/artifact spans.
    tool_types        -- distinct tool-execution types the review is expected
                         to need (heuristic; orchestrator may override).
    context_fraction  -- fraction of the reviewer's context the artifact
                         consumes at start (0.0-1.0).
    """

    file_count: int = 1
    tool_types: int = 1
    context_fraction: float = 0.0

    @classmethod
    def from_signals(
        cls,
        file_count: int = 1,
        tool_types: int = 1,
        artifact_bytes: int = 0,
        context_window: int = 200_000,
    ) -> "Complexity":
        """Build Complexity, deriving context_fraction from artifact size.

        Uses the standard ~4 bytes/token estimate.
        """
        window = context_window if context_window > 0 else 200_000
        est_tokens = artifact_bytes / 4
        fraction = est_tokens / window
        return cls(
            file_count=file_count,
            tool_types=tool_types,
            context_fraction=fraction,
        )

    def escalates(self) -> bool:
        """True if change complexity alone warrants Opus.

        OPT-005: raised from the hair-trigger (files>1 OR tool_types>2 OR
        ctx>0.20, which fired on virtually every real review) to a
        genuinely-large-change bar. The tool_types trigger is dropped — it
        added no signal a multi-file/big-context change didn't already carry.
        """
        return (
            self.file_count > 3
            or self.context_fraction > 0.40
        )


# Lenses eligible for the domain-score-gated high-stakes opus seat.
# OPT-006: architecture-reviewer dropped (it reaches opus via the per-reviewer
# complexity path when architecture genuinely dominates). Membership here is
# only *eligibility*: select_team_with_scores still gates the seat on the
# security/compliance domain actually scoring (>0.3) or an explicit override.
HIGH_STAKES_REVIEWERS: frozenset[str] = frozenset({"security-reviewer"})

# Hard cap on paid opus seats per team (OPT-005).
MAX_OPUS_SEATS: int = 2


def resolve_reviewer_model(
    agent: "AgentDef",
    complexity: "Complexity | None" = None,
    *,
    escalation_eligible: bool = False,
    high_stakes: bool = False,
) -> str:
    """Pick the model for a reviewer under the revised tiering policy.

    Sonnet 5 is the default. This is a *pure* function of explicit per-reviewer
    signals — the team-level decisions of *who* is eligible (top-2 domain lens)
    and *who* is high-stakes (security domain scored / --high-stakes flag) are
    made by :func:`select_team_with_scores`, so the JS mirror can stay a dumb,
    parity-locked unit.

    - ``high_stakes`` -> opus, regardless of complexity (OPT-006).
    - ``escalation_eligible`` AND the change is genuinely large (OPT-005) -> opus.
    - otherwise the agent's catalog model (never escalates a non-eligible seat).

    A catalog may pin a cheaper base model (e.g. haiku); escalation only ever
    pushes the model *up* to opus.
    """
    if high_stakes:
        return "opus"
    if escalation_eligible and complexity is not None and complexity.escalates():
        return "opus"
    return agent.model


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
        "model": "sonnet",
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
        "model": "sonnet",
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


def _security_domain_score(domain_scores: list[DomainScore]) -> float:
    """Highest score across the security-shaped domains (OPT-006 gate)."""
    return max(
        (ds.score for ds in domain_scores if ds.domain in ("security", "compliance")),
        default=0.0,
    )


def select_team_with_scores(
    description: str,
    artifact_path: str | None = None,
    min_reviewers: int = 2,
    max_reviewers: int = 3,
    catalog_path: str | None = None,
    complexity: "Complexity | None" = None,
    high_stakes: bool = False,
) -> tuple[list[AgentDef], list[DomainScore]]:
    """Select team and return (team, domain_scores) to avoid re-classification.

    Seating (OPT-014): every lens — including requirements-reviewer — competes
    on its domain score; there is no unconditional seat. The default team size
    is 3, sized by how many lenses clear the 0.5 relevance bar, floored at
    ``min_reviewers`` (>= 2) and capped at ``max_reviewers``.

    Model tiering (OPT-005/006): opus is spent per-reviewer, not team-wide. The
    security lens earns opus only when the security/compliance domain scored
    (>0.3) or ``high_stakes`` is set; complexity escalation reaches only the
    top-2 domain-scoring *specialist* lenses; and no team carries more than
    ``MAX_OPUS_SEATS`` opus seats. The shared catalog is not mutated.
    """
    if min_reviewers < 2:
        min_reviewers = 2
    if max_reviewers < min_reviewers:
        max_reviewers = min_reviewers

    catalog = load_catalog(catalog_path)
    domain_scores = classify_domains(description, artifact_path)

    # Rank every lens by domain relevance; ties keep catalog order (stable).
    ranked = sorted(
        ((_score_agent(agent, domain_scores), idx, agent)
         for idx, agent in enumerate(catalog)),
        key=lambda t: (-t[0], t[1]),
    )

    above_threshold = sum(1 for score, _, _ in ranked if score > 0.5)
    desired = max(min_reviewers, min(max_reviewers, above_threshold))

    team = [agent for _score, _idx, agent in ranked[:desired]]

    if len(team) < min_reviewers:
        raise ValueError(
            f"Cannot assemble {min_reviewers} reviewers from catalog; "
            f"only {len(team)} available"
        )

    # --- per-reviewer model tiering -------------------------------------
    # Complexity escalates only the top-2 domain-scoring SPECIALIST lenses;
    # the requirements-reviewer generalist covers ALL_DOMAINS and is never a
    # specialist seat, so it is excluded from that ranking.
    specialists = sorted(
        ((_score_agent(agent, domain_scores), i, agent)
         for i, agent in enumerate(team)
         if agent.name != "requirements-reviewer"),
        key=lambda t: (-t[0], t[1]),
    )
    escalation_eligible = {agent.name for _s, _i, agent in specialists[:2]}

    sec_score = _security_domain_score(domain_scores)

    def _is_high_stakes(agent: AgentDef) -> bool:
        if high_stakes and agent.name in HIGH_STAKES_REVIEWERS:
            return True
        return agent.name in HIGH_STAKES_REVIEWERS and sec_score > 0.3

    resolved = [
        replace(agent, model=resolve_reviewer_model(
            agent,
            complexity,
            escalation_eligible=agent.name in escalation_eligible,
            high_stakes=_is_high_stakes(agent),
        ))
        for agent in team
    ]

    # Hard cap on opus seats: keep high-stakes seats first, then the strongest
    # domain-scoring lenses; demote the rest back to their catalog model.
    opus_idxs = [i for i, a in enumerate(resolved) if a.model == "opus"]
    if len(opus_idxs) > MAX_OPUS_SEATS:
        opus_idxs.sort(key=lambda i: (
            0 if _is_high_stakes(team[i]) else 1,
            -_score_agent(team[i], domain_scores),
            i,
        ))
        for i in opus_idxs[MAX_OPUS_SEATS:]:
            resolved[i] = replace(resolved[i], model=team[i].model)

    return resolved, domain_scores


def select_team(
    description: str,
    artifact_path: str | None = None,
    min_reviewers: int = 2,
    max_reviewers: int = 3,
    catalog_path: str | None = None,
    complexity: "Complexity | None" = None,
    high_stakes: bool = False,
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
        complexity=complexity,
        high_stakes=high_stakes,
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
    parser.add_argument("--max", dest="max_reviewers", type=int, default=3, help="Maximum reviewers (default: 3; pass --max 5 for high-stakes reviews)")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Output as JSON instead of Markdown")
    parser.add_argument("--files", type=int, default=1, help="Number of files the change spans (escalates the top-2 domain lenses to Opus if >3)")
    parser.add_argument("--tool-types", dest="tool_types", type=int, default=1, help="Distinct tool-execution types expected (retained for signal; no longer a model trigger)")
    parser.add_argument("--context-fraction", dest="context_fraction", type=float, default=None, help="Fraction of context the artifact consumes at start (escalates the top-2 domain lenses if >0.40)")
    parser.add_argument("--context-window", dest="context_window", type=int, default=200_000, help="Context window for deriving context-fraction from artifact size (default: 200000)")
    parser.add_argument("--high-stakes", dest="high_stakes", action="store_true", help="Force the security lens to Opus regardless of domain score (explicit override)")

    args = parser.parse_args(argv)

    if args.context_fraction is not None:
        complexity = Complexity(
            file_count=args.files,
            tool_types=args.tool_types,
            context_fraction=args.context_fraction,
        )
    else:
        artifact_bytes = 0
        if args.artifact:
            try:
                artifact_bytes = Path(args.artifact).stat().st_size
            except OSError:
                artifact_bytes = 0
        complexity = Complexity.from_signals(
            file_count=args.files,
            tool_types=args.tool_types,
            artifact_bytes=artifact_bytes,
            context_window=args.context_window,
        )

    try:
        team, domain_scores = select_team_with_scores(
            args.description,
            artifact_path=args.artifact,
            min_reviewers=args.min_reviewers,
            max_reviewers=args.max_reviewers,
            catalog_path=args.catalog,
            complexity=complexity,
            high_stakes=args.high_stakes,
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
