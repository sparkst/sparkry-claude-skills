"""Tests for team-selector.py — deterministic review team selection."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Import via shared _loader.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling
team_selector = load_sibling("team-selector.py")

DomainScore = team_selector.DomainScore
AgentDef = team_selector.AgentDef
classify_domains = team_selector.classify_domains
load_catalog = team_selector.load_catalog
select_team = team_selector.select_team
main = team_selector.main


# ---------------------------------------------------------------------------
# Domain classification
# ---------------------------------------------------------------------------

class TestClassifyDomains:
    """Domain classification via keyword + extension matching."""

    def test_auth_token_validation_scores_security_high(self) -> None:
        scores = classify_domains("auth token validation endpoint")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "security" in domain_map
        assert domain_map["security"] >= 0.5
        # Should also pick up backend from "endpoint"
        assert "backend" in domain_map

    def test_react_component_styling_scores_frontend_high(self) -> None:
        scores = classify_domains("React component styling with CSS modules")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "frontend" in domain_map
        assert domain_map["frontend"] >= 0.5

    def test_database_migration_scores_data_high(self) -> None:
        scores = classify_domains("database migration for schema update")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "data" in domain_map
        assert domain_map["data"] >= 0.5

    def test_artifact_tsx_boosts_frontend(self) -> None:
        scores = classify_domains("refactor widget", artifact_path="src/Widget.tsx")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "frontend" in domain_map
        ext_signals = [s for s in next(
            ds.signals for ds in scores if ds.domain == "frontend"
        ) if s.startswith("extension:")]
        assert len(ext_signals) > 0

    def test_artifact_py_boosts_backend(self) -> None:
        scores = classify_domains("handler logic", artifact_path="lib/handler.py")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "backend" in domain_map
        assert domain_map["backend"] >= 0.25

    def test_artifact_md_boosts_content(self) -> None:
        scores = classify_domains("editorial review", artifact_path="docs/plan.md")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "content" in domain_map

    def test_scores_clamped_to_one(self) -> None:
        """Even with many signals, no score exceeds 1.0."""
        scores = classify_domains(
            "auth token credential secret encrypt password oauth jwt permission"
        )
        for ds in scores:
            assert ds.score <= 1.0

    def test_empty_description_returns_no_scores(self) -> None:
        scores = classify_domains("")
        assert scores == []

    def test_sorted_descending(self) -> None:
        scores = classify_domains("auth token api endpoint database schema")
        if len(scores) > 1:
            for i in range(len(scores) - 1):
                assert scores[i].score >= scores[i + 1].score

    def test_compliance_keywords(self) -> None:
        scores = classify_domains("GDPR compliance audit for PCI systems")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "compliance" in domain_map
        assert domain_map["compliance"] >= 0.5

    def test_devops_keywords(self) -> None:
        scores = classify_domains("deploy Docker container to k8s cluster")
        domain_map = {ds.domain: ds.score for ds in scores}
        assert "devops" in domain_map
        assert domain_map["devops"] >= 0.5


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------

class TestLoadCatalog:
    """Agent catalog loading from defaults and custom JSON."""

    def test_default_catalog_has_seven_agents(self) -> None:
        catalog = load_catalog()
        assert len(catalog) == 7

    def test_default_catalog_includes_requirements_reviewer(self) -> None:
        catalog = load_catalog()
        names = [a.name for a in catalog]
        assert "requirements-reviewer" in names

    def test_default_catalog_agent_types(self) -> None:
        catalog = load_catalog()
        agent_map = {a.name: a for a in catalog}
        assert agent_map["requirements-reviewer"].model == "sonnet"
        assert agent_map["ux-reviewer"].model == "haiku"
        assert agent_map["code-quality-reviewer"].model == "haiku"

    def test_custom_catalog_from_json(self, tmp_path: Path) -> None:
        custom: list[dict[str, Any]] = [
            {
                "name": "custom-reviewer",
                "domains": ["security", "backend"],
                "model": "opus",
                "description": "A custom reviewer",
                "review_lens": "custom lens",
            },
            {
                "name": "requirements-reviewer",
                "domains": ["security", "backend", "frontend"],
                "model": "sonnet",
                "description": "Custom requirements reviewer",
                "review_lens": "requirements coverage",
            },
        ]
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text(json.dumps(custom))
        catalog = load_catalog(str(catalog_file))
        assert len(catalog) == 2
        assert catalog[0].name == "custom-reviewer"
        assert catalog[0].model == "opus"


# ---------------------------------------------------------------------------
# Team selection
# ---------------------------------------------------------------------------

class TestSelectTeam:
    """Team selection algorithm."""

    def test_requirements_reviewer_always_included(self) -> None:
        team = select_team("some generic description")
        names = [a.name for a in team]
        assert "requirements-reviewer" in names

    def test_generic_description_still_returns_requirements_reviewer(self) -> None:
        team = select_team("a vague description of nothing in particular")
        names = [a.name for a in team]
        assert "requirements-reviewer" in names

    def test_min_reviewers_enforced(self) -> None:
        """Even for a narrow domain, we get at least min_reviewers."""
        team = select_team("GDPR compliance", min_reviewers=3)
        assert len(team) >= 3

    def test_max_reviewers_caps_team(self) -> None:
        """A broad description with many domains still caps at max."""
        team = select_team(
            "auth token api endpoint database schema deploy docker react component "
            "test coverage perf latency strategy roadmap GDPR research analysis content article",
            max_reviewers=5,
        )
        assert len(team) <= 5

    def test_narrow_domain_min_two(self) -> None:
        team = select_team("GDPR audit", min_reviewers=2)
        assert len(team) >= 2

    def test_min_reviewers_clamped_to_two_at_tool_level(self) -> None:
        """Even when caller passes min_reviewers=1, tool clamps to 2."""
        team = select_team("simple description", min_reviewers=1)
        assert len(team) >= 2

    def test_security_description_includes_security_reviewer(self) -> None:
        team = select_team("auth token credential encryption audit")
        names = [a.name for a in team]
        assert "security-reviewer" in names

    def test_frontend_description_includes_ux_reviewer(self) -> None:
        team = select_team("React component styling with CSS layout")
        names = [a.name for a in team]
        assert "ux-reviewer" in names

    def test_multi_domain_agent_ranks_higher(self) -> None:
        """An agent covering multiple high-scoring domains should rank above
        one covering only a single lower-scoring domain."""
        # This description hits backend, frontend, testing, performance --
        # all domains covered by code-quality-reviewer.
        team = select_team(
            "api endpoint React component test coverage perf latency",
            max_reviewers=5,
        )
        names = [a.name for a in team]
        # code-quality-reviewer covers backend+frontend+testing+performance
        assert "code-quality-reviewer" in names

    def test_empty_description_returns_minimum_team(self) -> None:
        team = select_team("", min_reviewers=2)
        assert len(team) >= 2
        names = [a.name for a in team]
        assert "requirements-reviewer" in names

    def test_custom_catalog_selection(self, tmp_path: Path) -> None:
        custom: list[dict[str, Any]] = [
            {
                "name": "requirements-reviewer",
                "domains": ["security"],
                "model": "sonnet",
                "description": "Req reviewer",
                "review_lens": "reqs",
            },
            {
                "name": "alpha",
                "domains": ["security"],
                "model": "haiku",
                "description": "Alpha",
                "review_lens": "alpha lens",
            },
            {
                "name": "beta",
                "domains": ["frontend"],
                "model": "haiku",
                "description": "Beta",
                "review_lens": "beta lens",
            },
        ]
        catalog_file = tmp_path / "catalog.json"
        catalog_file.write_text(json.dumps(custom))

        team = select_team(
            "auth token validation",
            min_reviewers=2,
            catalog_path=str(catalog_file),
        )
        names = [a.name for a in team]
        assert "requirements-reviewer" in names
        assert "alpha" in names  # security domain should score


# ---------------------------------------------------------------------------
# CLI output
# ---------------------------------------------------------------------------

class TestCLI:
    """CLI entry point formatting."""

    def test_markdown_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["auth token validation"])
        captured = capsys.readouterr()
        assert "## Detected Domains" in captured.out
        assert "## Selected Review Team" in captured.out
        assert "security" in captured.out.lower()

    def test_json_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["auth token validation", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "domains" in data
        assert "team" in data
        assert isinstance(data["domains"], list)
        assert isinstance(data["team"], list)
        # At least requirements-reviewer should be in team
        team_names = [t["name"] for t in data["team"]]
        assert "requirements-reviewer" in team_names

    def test_json_output_with_artifact(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["refactor widget", "--artifact", "src/Widget.tsx", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        domain_names = [d["domain"] for d in data["domains"]]
        assert "frontend" in domain_names

    def test_markdown_output_includes_all_agents(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["auth api database deploy react test perf strategy GDPR research content"])
        captured = capsys.readouterr()
        # Should list multiple agents
        assert "requirements-reviewer" in captured.out

    def test_json_output_min_max(self, capsys: pytest.CaptureFixture[str]) -> None:
        main(["auth token", "--min", "3", "--max", "4", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data["team"]) >= 3
        assert len(data["team"]) <= 4


# ---------------------------------------------------------------------------
# Catalog error paths
# ---------------------------------------------------------------------------

class TestLoadCatalogErrors:
    """Error handling for malformed or incomplete catalog files."""

    def test_malformed_json_raises(self, tmp_path: Path) -> None:
        catalog_file = tmp_path / "bad.json"
        catalog_file.write_text("this is not json {{{", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_catalog(str(catalog_file))

    def test_missing_required_field_raises_valueerror(self, tmp_path: Path) -> None:
        # Missing 'review_lens' field
        incomplete: list[dict[str, Any]] = [
            {
                "name": "incomplete-reviewer",
                "domains": ["security"],
                "model": "sonnet",
                "description": "Missing review_lens",
            },
        ]
        catalog_file = tmp_path / "incomplete.json"
        catalog_file.write_text(json.dumps(incomplete), encoding="utf-8")
        with pytest.raises(ValueError, match="missing required fields"):
            load_catalog(str(catalog_file))


# ---------------------------------------------------------------------------
# select_team insufficient catalog
# ---------------------------------------------------------------------------

class TestSelectTeamInsufficientCatalog:
    """select_team raises when catalog cannot satisfy min_reviewers."""

    def test_insufficient_catalog_raises(self, tmp_path: Path) -> None:
        # Catalog with only 1 agent, but min_reviewers=2
        tiny: list[dict[str, Any]] = [
            {
                "name": "solo-reviewer",
                "domains": ["security"],
                "model": "haiku",
                "description": "Only reviewer",
                "review_lens": "solo lens",
            },
        ]
        catalog_file = tmp_path / "tiny.json"
        catalog_file.write_text(json.dumps(tiny), encoding="utf-8")
        with pytest.raises(ValueError, match="Cannot assemble"):
            select_team(
                "auth token validation",
                min_reviewers=2,
                catalog_path=str(catalog_file),
            )
