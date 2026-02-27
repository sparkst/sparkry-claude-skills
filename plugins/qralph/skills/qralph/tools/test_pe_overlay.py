#!/usr/bin/env python3
"""
Unit tests for PE Overlay Gate Module (pe-overlay.py).

REQ-PE-001: Gate checks for phase transitions
REQ-PE-002: ADR loading and consistency checks
REQ-PE-003: DoD template detection and validation
REQ-PE-004: Requirements inference from request text and dependencies
REQ-PE-005: Navigation strategy selection
REQ-PE-006: COE/5-Whys analysis validation
REQ-PE-007: Pattern sweep for remaining issues
REQ-PE-008: Backward compatibility with older state formats

Test Categories:
1. run_gate() - Main entry point
2. ADR Functions - load, check, propose, save
3. DoD Functions - detect, select, validate, sign-off
4. Requirements Inference - request text and dependency scanning
5. Navigation Strategy - language detection and strategy selection
6. COE System - template creation, validation, loading
7. Pattern Sweep - sweep execution and summary
8. Backward Compatibility - empty/old state handling
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import functions from pe-overlay.py (using importlib for hyphenated filenames)
import sys
import importlib.util

sys.path.insert(0, str(Path(__file__).parent))

pe_overlay_path = Path(__file__).parent / "pe-overlay.py"
spec_pe = importlib.util.spec_from_file_location("pe_overlay", pe_overlay_path)
pe_overlay = importlib.util.module_from_spec(spec_pe)
spec_pe.loader.exec_module(pe_overlay)

# Import all public functions
run_gate = pe_overlay.run_gate
load_adrs = pe_overlay.load_adrs
check_adr_consistency = pe_overlay.check_adr_consistency
propose_new_adrs = pe_overlay.propose_new_adrs
save_proposed_adrs = pe_overlay.save_proposed_adrs
adr_final_check = pe_overlay.adr_final_check
final_adr_compliance = pe_overlay.final_adr_compliance
detect_project_type = pe_overlay.detect_project_type
load_dod_template = pe_overlay.load_dod_template
select_dod_template = pe_overlay.select_dod_template
validate_dod_selected = pe_overlay.validate_dod_selected
validate_dod_completeness = pe_overlay.validate_dod_completeness
full_dod_check = pe_overlay.full_dod_check
dod_signoff = pe_overlay.dod_signoff
infer_requirements = pe_overlay.infer_requirements
confirm_inferred_requirements = pe_overlay.confirm_inferred_requirements
select_nav_strategy = pe_overlay.select_nav_strategy
validate_nav_strategy_selected = pe_overlay.validate_nav_strategy_selected
create_coe_template = pe_overlay.create_coe_template
validate_coe_analysis = pe_overlay.validate_coe_analysis
load_coe_analysis = pe_overlay.load_coe_analysis
pattern_sweep = pe_overlay.pattern_sweep
pattern_sweep_summary = pe_overlay.pattern_sweep_summary
store_learnings_to_memory = pe_overlay.store_learnings_to_memory

# Import constants
GATE_CHECKS = pe_overlay.GATE_CHECKS
COE_REQUIRED_FIELDS = pe_overlay.COE_REQUIRED_FIELDS
REQUIREMENT_PATTERNS = pe_overlay.REQUIREMENT_PATTERNS
DOD_TEMPLATES = pe_overlay.DOD_TEMPLATES
VERSION = pe_overlay.VERSION

# Import internal helpers for targeted tests
_gate_result = pe_overlay._gate_result
_parse_adr_file = pe_overlay._parse_adr_file
_parse_dod_markdown = pe_overlay._parse_dod_markdown
_default_dod_template = pe_overlay._default_dod_template
_resolve_repo_root = pe_overlay._resolve_repo_root


# ============================================================================
# Test Infrastructure - Helper Functions
# ============================================================================


def make_project(tmp_path, *, package_json=None, pyproject_toml=None,
                 tsconfig=False, wrangler=False, requirements_txt=None,
                 git=True):
    """Create a minimal project directory structure."""
    if git:
        (tmp_path / ".git").mkdir(exist_ok=True)
    if package_json is not None:
        (tmp_path / "package.json").write_text(
            json.dumps(package_json), encoding="utf-8"
        )
    if pyproject_toml is not None:
        (tmp_path / "pyproject.toml").write_text(pyproject_toml, encoding="utf-8")
    if tsconfig:
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
    if wrangler:
        (tmp_path / "wrangler.toml").write_text("", encoding="utf-8")
    if requirements_txt is not None:
        (tmp_path / "requirements.txt").write_text(requirements_txt, encoding="utf-8")
    return tmp_path


def make_state(*, request="", repo_root=None, **extra):
    """Create a minimal valid state dict."""
    state = {"request": request}
    if repo_root:
        state["repo_root"] = str(repo_root)
    state.update(extra)
    return state


def make_adr_file(path, *, adr_id="ADR-001", title="Test ADR",
                  status="Accepted", enforcement_rules=None):
    """Create a test ADR file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}\n"]
    lines.append(f"**Status**: {status}\n")
    lines.append("## Context\n\nSome context.\n")
    if enforcement_rules:
        lines.append("## Enforcement Rules\n")
        for rule in enforcement_rules:
            for key, value in rule.items():
                lines.append(f"- {key.capitalize()}: {value}")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def make_agent_output(path, agent_name, content):
    """Create test agent output file."""
    outputs_dir = path / "agent-outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_file = outputs_dir / f"{agent_name}.md"
    output_file.write_text(content, encoding="utf-8")
    return output_file


def make_coe_file(project_path, task_id, coe_data):
    """Create a COE analysis JSON file."""
    coe_dir = project_path / "coe-analyses"
    coe_dir.mkdir(parents=True, exist_ok=True)
    coe_file = coe_dir / f"{task_id}.json"
    coe_file.write_text(json.dumps(coe_data), encoding="utf-8")
    return coe_file


# ============================================================================
# 1. run_gate() TESTS
# ============================================================================


class TestRunGate:
    """REQ-PE-001: Gate checks for phase transitions."""

    def test_known_transition_returns_result_dict(self, tmp_path):
        """Gate with known transition returns result dict with all fields."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = run_gate("INIT", "DISCOVERING", state, project)

        assert "passed" in result
        assert "blockers" in result
        assert "warnings" in result
        assert "proposed_adrs" in result
        assert result["transition"] == "INIT -> DISCOVERING"
        assert result["checks_run"] > 0

    def test_unknown_transition_returns_passed_true(self, tmp_path):
        """Gate with unknown transition returns passed=True (no checks defined)."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = run_gate("UNKNOWN", "PHASE", state, project)

        assert result["passed"] is True
        assert result["blockers"] == []
        assert result["warnings"] == []
        assert result["checks_run"] == 0

    def test_gate_catches_exceptions_as_warnings(self, tmp_path):
        """Gate catches exceptions in individual checks and converts to warnings."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)

        def bad_check(s, p):
            raise ValueError("deliberate test error")

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [bad_check]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert result["passed"] is True
        assert any("deliberate test error" in w for w in result["warnings"])

    def test_gate_aggregates_blockers_from_multiple_checks(self, tmp_path):
        """Gate aggregates blockers from multiple failing checks."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)

        def blocker_a(s, p):
            return {"passed": False, "blockers": ["blocker A"], "warnings": []}

        def blocker_b(s, p):
            return {"passed": False, "blockers": ["blocker B"], "warnings": []}

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [blocker_a, blocker_b]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert result["passed"] is False
        assert "blocker A" in result["blockers"]
        assert "blocker B" in result["blockers"]

    def test_gate_aggregates_warnings_from_multiple_checks(self, tmp_path):
        """Gate aggregates warnings from multiple checks."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)

        def warn_a(s, p):
            return {"passed": True, "blockers": [], "warnings": ["warn A"]}

        def warn_b(s, p):
            return {"passed": True, "blockers": [], "warnings": ["warn B"]}

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [warn_a, warn_b]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert result["passed"] is True
        assert "warn A" in result["warnings"]
        assert "warn B" in result["warnings"]

    def test_gate_collects_proposed_adrs(self, tmp_path):
        """Gate collects proposed_adrs from checks that return them."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        proposal = {"id": "PROPOSED-001", "title": "Use Redis"}

        def proposer(s, p):
            return {"passed": True, "blockers": [], "warnings": [],
                    "proposed_adrs": [proposal]}

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [proposer]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert proposal in result["proposed_adrs"]

    def test_gate_all_checks_pass_returns_true(self, tmp_path):
        """Gate with all checks passing returns passed=True."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)

        def ok_check(s, p):
            return {"passed": True, "blockers": [], "warnings": []}

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [ok_check, ok_check]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert result["passed"] is True
        assert result["blockers"] == []

    def test_gate_any_blocker_returns_false(self, tmp_path):
        """Gate with any blocker returns passed=False."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)

        def ok_check(s, p):
            return {"passed": True, "blockers": [], "warnings": []}

        def fail_check(s, p):
            return {"passed": False, "blockers": ["critical issue"], "warnings": []}

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [ok_check, fail_check]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert result["passed"] is False
        assert "critical issue" in result["blockers"]

    def test_gate_non_dict_result_becomes_warning(self, tmp_path):
        """Gate check returning non-dict adds a warning."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)

        def bad_return(s, p):
            return "not a dict"

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [bad_return]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert result["passed"] is True
        assert any("non-dict" in w for w in result["warnings"])

    def test_gate_includes_check_results(self, tmp_path):
        """Gate includes individual check_results in output."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)

        def named_check(s, p):
            return {"passed": True, "blockers": [], "warnings": [], "extra": 42}

        named_check.__name__ = "named_check"

        with patch.dict(GATE_CHECKS, {("TEST", "PHASE"): [named_check]}):
            result = run_gate("TEST", "PHASE", state, project)

        assert "check_results" in result
        assert any(cr["check"] == "named_check" for cr in result["check_results"])


# ============================================================================
# 2. ADR FUNCTIONS
# ============================================================================


class TestLoadAdrs:
    """REQ-PE-002: ADR loading."""

    def test_no_adrs_dir_returns_passed(self, tmp_path):
        """load_adrs with no docs/adrs/ dir returns passed=True, adrs_loaded=0."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = load_adrs(state, project)

        assert result["passed"] is True
        assert result["adrs_loaded"] == 0
        assert result["adrs"] == []

    def test_valid_adr_files_parsed(self, tmp_path):
        """load_adrs with valid ADR files parses them correctly."""
        project = make_project(tmp_path)
        adrs_dir = project / "docs" / "adrs"
        make_adr_file(
            adrs_dir / "ADR-001-use-hono.md",
            title="Use Hono Framework",
            status="Accepted",
        )
        state = make_state(repo_root=project)
        result = load_adrs(state, project)

        assert result["passed"] is True
        assert result["adrs_loaded"] == 1
        assert result["adrs"][0]["title"] == "Use Hono Framework"
        assert result["adrs"][0]["status"] == "Accepted"

    def test_extracts_enforcement_sections(self, tmp_path):
        """load_adrs extracts enforcement sections from ADR files."""
        project = make_project(tmp_path)
        adrs_dir = project / "docs" / "adrs"
        make_adr_file(
            adrs_dir / "ADR-002-no-axios.md",
            title="No Axios Usage",
            status="Accepted",
            enforcement_rules=[{"pattern": "axios", "check": "block"}],
        )
        state = make_state(repo_root=project)
        result = load_adrs(state, project)

        assert result["adrs_loaded"] == 1
        rules = result["adrs"][0]["enforcement_rules"]
        assert len(rules) >= 1
        assert any(r.get("pattern") == "axios" for r in rules)

    def test_handles_malformed_adr_gracefully(self, tmp_path):
        """load_adrs handles malformed ADR files gracefully."""
        project = make_project(tmp_path)
        adrs_dir = project / "docs" / "adrs"
        adrs_dir.mkdir(parents=True, exist_ok=True)
        # Write an empty file
        (adrs_dir / "ADR-099-empty.md").write_text("", encoding="utf-8")
        state = make_state(repo_root=project)
        result = load_adrs(state, project)

        assert result["passed"] is True
        # Empty file produces empty dict from _parse_adr_file, so no ADRs loaded
        assert result["adrs_loaded"] == 0

    def test_stores_adrs_in_state(self, tmp_path):
        """load_adrs stores parsed ADRs in state['_pe_adrs']."""
        project = make_project(tmp_path)
        adrs_dir = project / "docs" / "adrs"
        make_adr_file(adrs_dir / "ADR-001-test.md", title="Test ADR")
        state = make_state(repo_root=project)
        load_adrs(state, project)

        assert "_pe_adrs" in state
        assert len(state["_pe_adrs"]) == 1

    def test_multiple_adr_files(self, tmp_path):
        """load_adrs loads multiple ADR files."""
        project = make_project(tmp_path)
        adrs_dir = project / "docs" / "adrs"
        make_adr_file(adrs_dir / "ADR-001-first.md", title="First")
        make_adr_file(adrs_dir / "ADR-002-second.md", title="Second")
        make_adr_file(adrs_dir / "ADR-003-third.md", title="Third")
        state = make_state(repo_root=project)
        result = load_adrs(state, project)

        assert result["adrs_loaded"] == 3


class TestCheckAdrConsistency:
    """REQ-PE-002: ADR consistency checks."""

    def test_no_adrs_returns_passed(self, tmp_path):
        """check_adr_consistency with no ADRs returns passed=True."""
        state = make_state(_pe_adrs=[])
        result = check_adr_consistency(state, tmp_path)
        assert result["passed"] is True

    def test_detects_contradictions(self, tmp_path):
        """check_adr_consistency detects contradictions between agent outputs and ADRs."""
        project = make_project(tmp_path)
        make_agent_output(project, "security-agent", "We recommend using axios for HTTP calls.")

        state = make_state(
            _pe_adrs=[{
                "id": "ADR-001",
                "title": "No Axios",
                "status": "Accepted",
                "enforcement_rules": [{"pattern": "axios", "check": "block"}],
            }]
        )
        result = check_adr_consistency(state, project)

        assert result["passed"] is False
        assert len(result.get("contradictions", [])) > 0

    def test_no_agent_outputs_returns_passed_with_warning(self, tmp_path):
        """check_adr_consistency with no agent outputs returns passed=True."""
        project = make_project(tmp_path)
        state = make_state(
            _pe_adrs=[{
                "id": "ADR-001",
                "title": "Test",
                "status": "Accepted",
                "enforcement_rules": [{"pattern": "test", "check": "warn"}],
            }]
        )
        result = check_adr_consistency(state, project)

        assert result["passed"] is True
        assert any("No agent outputs" in w for w in result["warnings"])

    def test_warn_check_adds_to_warnings(self, tmp_path):
        """check_adr_consistency with warn check adds to warnings, not blockers."""
        project = make_project(tmp_path)
        make_agent_output(project, "agent-a", "We use jQuery for DOM manipulation.")

        state = make_state(
            _pe_adrs=[{
                "id": "ADR-002",
                "title": "Prefer vanilla JS",
                "status": "Accepted",
                "enforcement_rules": [{"pattern": "jQuery", "check": "warn"}],
            }]
        )
        result = check_adr_consistency(state, project)

        assert result["passed"] is True
        assert any("jQuery" in w for w in result["warnings"])

    def test_skips_superseded_adrs(self, tmp_path):
        """check_adr_consistency skips superseded/deprecated ADRs."""
        project = make_project(tmp_path)
        make_agent_output(project, "agent-a", "We use axios.")

        state = make_state(
            _pe_adrs=[{
                "id": "ADR-001",
                "title": "No Axios",
                "status": "Superseded",
                "enforcement_rules": [{"pattern": "axios", "check": "block"}],
            }]
        )
        result = check_adr_consistency(state, project)

        assert result["passed"] is True
        assert len(result.get("contradictions", [])) == 0

    def test_invalid_regex_in_enforcement_warns(self, tmp_path):
        """check_adr_consistency handles invalid regex patterns gracefully."""
        project = make_project(tmp_path)
        make_agent_output(project, "agent-a", "Some output text.")

        state = make_state(
            _pe_adrs=[{
                "id": "ADR-001",
                "title": "Bad Regex",
                "status": "Accepted",
                "enforcement_rules": [{"pattern": "[invalid(regex", "check": "block"}],
            }]
        )
        result = check_adr_consistency(state, project)

        assert result["passed"] is True
        assert any("invalid regex" in w for w in result["warnings"])


class TestProposeNewAdrs:
    """REQ-PE-002: Proposing new ADRs from agent outputs."""

    def test_finds_architectural_keywords(self, tmp_path):
        """propose_new_adrs finds architectural keywords in agent outputs."""
        project = make_project(tmp_path)
        make_agent_output(
            project, "architect",
            "We should adopt a microservices architecture for better scaling."
        )
        state = make_state()
        result = propose_new_adrs(state, project)

        assert result["passed"] is True
        assert len(result["proposed_adrs"]) >= 1

    def test_no_agent_outputs_returns_empty(self, tmp_path):
        """propose_new_adrs with no agent outputs returns empty proposals."""
        project = make_project(tmp_path)
        state = make_state()
        result = propose_new_adrs(state, project)

        assert result["passed"] is True
        assert result["proposed_adrs"] == []

    def test_deduplicates_by_title(self, tmp_path):
        """propose_new_adrs deduplicates proposals with same title."""
        project = make_project(tmp_path)
        # Two agents recommending the same thing
        make_agent_output(project, "agent-a", "We should adopt TypeScript for type safety.")
        make_agent_output(project, "agent-b", "We should adopt TypeScript for type safety.")
        state = make_state()
        result = propose_new_adrs(state, project)

        titles = [p["title"].lower().strip() for p in result["proposed_adrs"]]
        assert len(titles) == len(set(titles))

    def test_stores_proposals_in_state(self, tmp_path):
        """propose_new_adrs stores proposals in state['_pe_proposed_adrs']."""
        project = make_project(tmp_path)
        make_agent_output(project, "arch", "We recommend using a queue system.")
        state = make_state()
        propose_new_adrs(state, project)

        assert "_pe_proposed_adrs" in state

    def test_proposals_have_required_fields(self, tmp_path):
        """propose_new_adrs proposals include id, title, context, source_agent."""
        project = make_project(tmp_path)
        make_agent_output(project, "arch-agent", "We should adopt Redis for caching.")
        state = make_state()
        result = propose_new_adrs(state, project)

        for p in result["proposed_adrs"]:
            assert "id" in p
            assert "title" in p
            assert "context" in p
            assert "source_agent" in p


class TestSaveProposedAdrs:
    """REQ-PE-002: Saving proposed ADRs to disk."""

    def test_creates_files_in_proposed_adrs_dir(self, tmp_path):
        """save_proposed_adrs creates files in proposed-adrs/ directory."""
        proposals = [
            {"id": "PROPOSED-001", "title": "Use Redis", "context": "Caching layer",
             "source_agent": "arch"},
        ]
        save_proposed_adrs(proposals, tmp_path)

        proposed_dir = tmp_path / "proposed-adrs"
        assert proposed_dir.is_dir()
        md_files = list(proposed_dir.glob("PROPOSED-*.md"))
        assert len(md_files) == 1

    def test_creates_index_file(self, tmp_path):
        """save_proposed_adrs creates an INDEX.md file."""
        proposals = [
            {"id": "PROPOSED-001", "title": "Use Redis", "context": "ctx",
             "source_agent": "arch"},
        ]
        save_proposed_adrs(proposals, tmp_path)

        index = tmp_path / "proposed-adrs" / "INDEX.md"
        assert index.is_file()
        content = index.read_text(encoding="utf-8")
        assert "PROPOSED-001" in content
        assert "Use Redis" in content

    def test_empty_proposals_does_nothing(self, tmp_path):
        """save_proposed_adrs with empty list does not create directory."""
        save_proposed_adrs([], tmp_path)
        assert not (tmp_path / "proposed-adrs").exists()


class TestAdrFinalCheck:
    """REQ-PE-002: Final ADR compliance."""

    def test_no_adrs_passes(self, tmp_path):
        """adr_final_check with no ADRs passes."""
        state = make_state()
        result = adr_final_check(state, tmp_path)
        assert result["passed"] is True

    def test_final_adr_compliance_no_enforceable_passes(self, tmp_path):
        """final_adr_compliance with no enforceable ADRs passes."""
        state = make_state(_pe_adrs=[{
            "id": "ADR-001",
            "title": "Informational",
            "status": "Accepted",
            "enforcement_rules": [],
        }])
        result = final_adr_compliance(state, tmp_path)

        assert result["passed"] is True
        assert result.get("signed_off") is True


# ============================================================================
# 3. DoD FUNCTIONS
# ============================================================================


class TestDetectProjectType:
    """REQ-PE-003: Project type detection."""

    def _detect(self, tmp_path):
        """Helper that patches _resolve_repo_root to return tmp_path."""
        with patch.object(pe_overlay, "_resolve_repo_root", return_value=tmp_path):
            return detect_project_type(tmp_path)

    def test_react_package_json_returns_webapp(self, tmp_path):
        """detect_project_type with React package.json returns 'webapp'."""
        make_project(tmp_path, package_json={
            "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"},
        })
        assert self._detect(tmp_path) == "webapp"

    def test_hono_package_json_returns_api(self, tmp_path):
        """detect_project_type with Hono package.json returns 'api'."""
        make_project(tmp_path, package_json={
            "dependencies": {"hono": "^4.0.0"},
        })
        assert self._detect(tmp_path) == "api"

    def test_exports_field_returns_library(self, tmp_path):
        """detect_project_type with exports field returns 'library'."""
        make_project(tmp_path, package_json={
            "name": "my-lib",
            "exports": {"./": "./dist/index.js"},
        })
        assert self._detect(tmp_path) == "library"

    def test_main_field_returns_library(self, tmp_path):
        """detect_project_type with main field returns 'library'."""
        make_project(tmp_path, package_json={
            "name": "my-lib",
            "main": "./dist/index.js",
        })
        assert self._detect(tmp_path) == "library"

    def test_pyproject_build_system_returns_library(self, tmp_path):
        """detect_project_type with pyproject.toml build-system returns 'library'."""
        make_project(tmp_path, pyproject_toml=(
            "[build-system]\n"
            'requires = ["setuptools"]\n'
            'build-backend = "setuptools.build_meta"\n'
        ))
        assert self._detect(tmp_path) == "library"

    def test_pyproject_with_flask_returns_api(self, tmp_path):
        """detect_project_type with pyproject.toml containing flask returns 'api'."""
        make_project(tmp_path, pyproject_toml=(
            "[build-system]\n"
            'requires = ["setuptools"]\n'
            "[project]\n"
            'dependencies = ["flask"]\n'
        ))
        assert self._detect(tmp_path) == "api"

    def test_no_package_json_returns_api(self, tmp_path):
        """detect_project_type with no package.json returns 'api' (default)."""
        make_project(tmp_path)
        assert self._detect(tmp_path) == "api"

    def test_wrangler_toml_returns_api(self, tmp_path):
        """detect_project_type with wrangler.toml returns 'api'."""
        make_project(tmp_path, wrangler=True)
        assert self._detect(tmp_path) == "api"

    def test_requirements_txt_with_django_returns_api(self, tmp_path):
        """detect_project_type with requirements.txt containing django returns 'api'."""
        make_project(tmp_path, requirements_txt="django==4.2\ncelery==5.3\n")
        assert self._detect(tmp_path) == "api"

    def test_vue_returns_webapp(self, tmp_path):
        """detect_project_type with Vue dependency returns 'webapp'."""
        make_project(tmp_path, package_json={
            "dependencies": {"vue": "^3.0.0"},
        })
        assert self._detect(tmp_path) == "webapp"


class TestSelectDodTemplate:
    """REQ-PE-003: DoD template selection."""

    def test_stores_result_in_state(self, tmp_path):
        """select_dod_template stores result in state."""
        project = make_project(tmp_path, package_json={"dependencies": {"hono": "^4.0"}})
        state = make_state(repo_root=project)
        result = select_dod_template(state, project)

        assert result["passed"] is True
        assert state["_pe_project_type"] == "api"
        assert state["_pe_dod_template"] == "dod-api.md"
        assert "_pe_dod" in state


class TestValidateDodSelected:
    """REQ-PE-003: DoD validation."""

    def test_passes_when_template_in_state(self, tmp_path):
        """validate_dod_selected passes when dod_template in state."""
        state = make_state(_pe_dod_template="dod-api.md")
        result = validate_dod_selected(state, tmp_path)
        assert result["passed"] is True
        assert result["warnings"] == []

    def test_warns_when_missing(self, tmp_path):
        """validate_dod_selected warns when DoD template missing and auto-selects."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        with patch.object(pe_overlay, "_resolve_repo_root", return_value=project):
            result = validate_dod_selected(state, project)

        assert result["passed"] is True
        assert any("not selected" in w for w in result["warnings"])
        # After auto-select, the template should now be in state
        assert "_pe_dod_template" in state


class TestValidateDodCompleteness:
    """REQ-PE-003: DoD completeness."""

    def test_passes_when_dod_absent(self, tmp_path):
        """validate_dod_completeness passes when DoD data absent (backward compat)."""
        state = make_state()
        result = validate_dod_completeness(state, tmp_path)
        assert result["passed"] is True

    def test_full_dod_check_no_template_passes(self, tmp_path):
        """full_dod_check with no template passes gracefully."""
        state = make_state()
        result = full_dod_check(state, tmp_path)
        assert result["passed"] is True
        assert any("No DoD loaded" in w for w in result["warnings"])

    def test_dod_signoff_no_template_passes(self, tmp_path):
        """dod_signoff with no template passes gracefully."""
        state = make_state()
        result = dod_signoff(state, tmp_path)
        assert result["passed"] is True
        assert result.get("signed_off") is True


class TestLoadDodTemplate:
    """REQ-PE-003: DoD template loading."""

    def test_valid_file_returns_parsed_categories(self, tmp_path):
        """load_dod_template with valid file returns parsed categories."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template = templates_dir / "dod-api.md"
        template.write_text(
            "## Code Quality\n"
            "- [ ] No lint errors\n"
            "- [ ] Type-safe code\n"
            "## Testing [BLOCKER]\n"
            "- [ ] Unit tests passing\n",
            encoding="utf-8",
        )
        with patch.object(pe_overlay, "SCRIPT_DIR", tmp_path):
            result = load_dod_template("dod-api.md")

        assert "categories" in result
        assert "Code Quality" in result["categories"]
        assert "Testing" in result["categories"]
        assert "Testing" in result["blockers"]

    def test_missing_file_returns_default(self):
        """load_dod_template with missing file returns default template."""
        result = load_dod_template("nonexistent-template.md")
        assert "categories" in result
        assert "blockers" in result
        assert "Testing" in result["blockers"]
        assert "Security" in result["blockers"]

    def test_identifies_blocker_categories(self, tmp_path):
        """load_dod_template identifies [BLOCKER] categories."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        template = templates_dir / "dod-test.md"
        template.write_text(
            "## Security [BLOCKER]\n"
            "- [ ] Input validated\n"
            "## Documentation\n"
            "- [ ] README updated\n",
            encoding="utf-8",
        )
        with patch.object(pe_overlay, "SCRIPT_DIR", tmp_path):
            result = load_dod_template("dod-test.md")

        assert "Security" in result["blockers"]
        assert "Documentation" not in result["blockers"]

    def test_default_dod_has_expected_structure(self):
        """Default DoD template has categories and blockers."""
        result = _default_dod_template()
        assert "Code Quality" in result["categories"]
        assert "Testing" in result["categories"]
        assert "Security" in result["categories"]
        assert "Documentation" in result["categories"]
        assert "Testing" in result["blockers"]
        assert "Security" in result["blockers"]


# ============================================================================
# 4. REQUIREMENTS INFERENCE
# ============================================================================


class TestInferRequirements:
    """REQ-PE-004: Requirements inference."""

    def test_stripe_in_request_returns_stripe_reqs(self, tmp_path):
        """infer_requirements with 'stripe' in request returns stripe-related reqs."""
        project = make_project(tmp_path)
        state = make_state(request="Integrate stripe payments", repo_root=project)
        result = infer_requirements(state, project)

        assert result["passed"] is True
        triggers = [r["trigger"] for r in result["inferred"]]
        assert "stripe" in triggers
        reqs = [r["requirement"] for r in result["inferred"]]
        assert "webhook signature validation" in reqs

    def test_cloudflare_worker_returns_cloudflare_reqs(self, tmp_path):
        """infer_requirements with 'cloudflare worker' returns cloudflare reqs."""
        project = make_project(tmp_path)
        state = make_state(request="Deploy to cloudflare workers", repo_root=project)
        result = infer_requirements(state, project)

        triggers = [r["trigger"] for r in result["inferred"]]
        assert "cloudflare" in triggers

    def test_empty_request_returns_empty(self, tmp_path):
        """infer_requirements with empty request returns empty list."""
        project = make_project(tmp_path)
        state = make_state(request="", repo_root=project)
        result = infer_requirements(state, project)

        assert result["passed"] is True
        assert result["inferred"] == []
        assert result["confidence"] == 1.0

    def test_scans_package_json_dependencies(self, tmp_path):
        """infer_requirements scans package.json for dependency-based inferences."""
        project = make_project(tmp_path, package_json={
            "dependencies": {"stripe": "^14.0.0", "resend": "^3.0.0"},
        })
        state = make_state(request="build a checkout page", repo_root=project)
        result = infer_requirements(state, project)

        triggers = [r["trigger"] for r in result["inferred"]]
        # stripe matches from request text, resend from dependency scan
        assert "resend" in triggers or "email" in [r["trigger"] for r in result["inferred"]
                                                    if r["source"] == "dependency"]

    def test_scans_requirements_txt(self, tmp_path):
        """infer_requirements scans requirements.txt for Python dependencies."""
        project = make_project(tmp_path, requirements_txt="flask==3.0\nsqlalchemy==2.0\n")
        state = make_state(request="build a web app", repo_root=project)
        result = infer_requirements(state, project)

        dep_triggers = [r["trigger"] for r in result["inferred"]
                        if r["source"] == "requirements.txt"]
        # sqlalchemy maps to "database"
        assert len(dep_triggers) > 0

    def test_confidence_calculation(self, tmp_path):
        """infer_requirements calculates overall confidence correctly."""
        project = make_project(tmp_path)
        state = make_state(request="integrate stripe and auth", repo_root=project)
        result = infer_requirements(state, project)

        assert 0.0 <= result["confidence"] <= 1.0
        # With request-text matches, confidence should be 0.8
        assert result["confidence"] == 0.8

    def test_stores_inferred_in_state(self, tmp_path):
        """infer_requirements stores results in state['_pe_inferred_requirements']."""
        project = make_project(tmp_path)
        state = make_state(request="use stripe", repo_root=project)
        infer_requirements(state, project)

        assert "_pe_inferred_requirements" in state
        assert len(state["_pe_inferred_requirements"]) > 0

    def test_no_duplicate_pattern_keys(self, tmp_path):
        """infer_requirements does not duplicate reqs when request and deps match same key."""
        project = make_project(tmp_path, package_json={
            "dependencies": {"stripe": "^14.0.0"},
        })
        # "stripe" in request AND in deps - should not double-count
        state = make_state(request="integrate stripe payments", repo_root=project)
        result = infer_requirements(state, project)

        stripe_reqs = [r for r in result["inferred"] if r["trigger"] == "stripe"]
        # Should match from request_text, not duplicated from dependency
        assert all(r["source"] == "request_text" for r in stripe_reqs)

    def test_multiple_patterns_in_request(self, tmp_path):
        """infer_requirements finds multiple pattern matches in request text."""
        project = make_project(tmp_path)
        state = make_state(
            request="Build a stripe checkout with database and email notifications",
            repo_root=project,
        )
        result = infer_requirements(state, project)

        triggers = set(r["trigger"] for r in result["inferred"])
        assert "stripe" in triggers
        assert "database" in triggers
        assert "email" in triggers

    def test_api_pattern_in_request(self, tmp_path):
        """infer_requirements detects api keyword in request."""
        project = make_project(tmp_path)
        state = make_state(request="build a REST api server", repo_root=project)
        result = infer_requirements(state, project)

        triggers = [r["trigger"] for r in result["inferred"]]
        assert "api" in triggers
        reqs = [r["requirement"] for r in result["inferred"]]
        assert "rate limiting" in reqs


class TestConfirmInferredRequirements:
    """REQ-PE-004: Confirming inferred requirements."""

    def test_passes_when_requirements_present(self, tmp_path):
        """confirm_inferred_requirements passes when requirements acknowledged."""
        state = make_state(
            _pe_inferred_requirements=[{"requirement": "test"}],
            _pe_requirements_acknowledged=True,
        )
        result = confirm_inferred_requirements(state, tmp_path)
        assert result["passed"] is True
        assert result.get("confirmed") == 1

    def test_warns_when_not_confirmed(self, tmp_path):
        """confirm_inferred_requirements warns when not confirmed."""
        state = make_state(
            _pe_inferred_requirements=[{"requirement": "test"}],
        )
        result = confirm_inferred_requirements(state, tmp_path)
        assert result["passed"] is True  # Not a blocker
        assert any("not been explicitly acknowledged" in w for w in result["warnings"])

    def test_no_inferred_passes_with_warning(self, tmp_path):
        """confirm_inferred_requirements with no inferred reqs passes."""
        state = make_state()
        result = confirm_inferred_requirements(state, tmp_path)
        assert result["passed"] is True
        assert any("No requirements" in w for w in result["warnings"])


# ============================================================================
# 5. NAVIGATION STRATEGY
# ============================================================================


class TestSelectNavStrategy:
    """REQ-PE-005: Navigation strategy selection."""

    def test_tsconfig_returns_ts_aware(self, tmp_path):
        """select_nav_strategy with tsconfig.json returns ts-aware."""
        project = make_project(tmp_path, tsconfig=True)
        state = make_state(repo_root=project)
        result = select_nav_strategy(state, project)

        assert result["passed"] is True
        assert result["strategy"] == "ts-aware"

    def test_multiple_languages_returns_polyglot(self, tmp_path):
        """select_nav_strategy with multiple languages returns polyglot."""
        project = make_project(tmp_path)
        # Create files in 3+ languages (no tsconfig to avoid ts-aware)
        (project / "app.py").write_text("print('hello')", encoding="utf-8")
        (project / "main.go").write_text("package main", encoding="utf-8")
        (project / "lib.rb").write_text("puts 'hello'", encoding="utf-8")
        state = make_state(repo_root=project)
        result = select_nav_strategy(state, project)

        assert result["strategy"] == "polyglot"
        assert len(result["detected_languages"]) >= 3

    def test_single_language_returns_grep_enhanced(self, tmp_path):
        """select_nav_strategy with single language returns grep-enhanced."""
        project = make_project(tmp_path)
        (project / "app.py").write_text("print('hello')", encoding="utf-8")
        state = make_state(repo_root=project)
        result = select_nav_strategy(state, project)

        assert result["strategy"] == "grep-enhanced"

    def test_stores_strategy_in_state(self, tmp_path):
        """select_nav_strategy stores strategy in state."""
        project = make_project(tmp_path, tsconfig=True)
        state = make_state(repo_root=project)
        select_nav_strategy(state, project)

        assert state["_pe_nav_strategy"] == "ts-aware"
        assert "_pe_detected_languages" in state

    def test_empty_project_returns_grep_enhanced(self, tmp_path):
        """select_nav_strategy with no source files returns grep-enhanced."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = select_nav_strategy(state, project)

        assert result["strategy"] == "grep-enhanced"
        assert result["detected_languages"] == []

    def test_skips_node_modules(self, tmp_path):
        """select_nav_strategy skips node_modules directory."""
        project = make_project(tmp_path)
        nm = project / "node_modules" / "some-pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}", encoding="utf-8")
        (nm / "extra.rb").write_text("class X; end", encoding="utf-8")
        (nm / "extra.go").write_text("package foo", encoding="utf-8")
        # Only source is a single .py file
        (project / "main.py").write_text("x = 1", encoding="utf-8")
        state = make_state(repo_root=project)
        result = select_nav_strategy(state, project)

        # Should NOT detect JS/Ruby/Go from node_modules
        assert result["strategy"] == "grep-enhanced"

    def test_two_languages_not_polyglot(self, tmp_path):
        """select_nav_strategy with only 2 languages returns grep-enhanced."""
        project = make_project(tmp_path)
        (project / "app.py").write_text("x = 1", encoding="utf-8")
        (project / "main.go").write_text("package main", encoding="utf-8")
        state = make_state(repo_root=project)
        result = select_nav_strategy(state, project)

        assert result["strategy"] == "grep-enhanced"
        assert len(result["detected_languages"]) == 2

    def test_tsconfig_takes_priority_over_polyglot(self, tmp_path):
        """select_nav_strategy prefers ts-aware even with 3+ languages."""
        project = make_project(tmp_path, tsconfig=True)
        (project / "app.py").write_text("x = 1", encoding="utf-8")
        (project / "main.go").write_text("package main", encoding="utf-8")
        (project / "lib.rb").write_text("x = 1", encoding="utf-8")
        (project / "index.ts").write_text("const x = 1", encoding="utf-8")
        state = make_state(repo_root=project)
        result = select_nav_strategy(state, project)

        assert result["strategy"] == "ts-aware"


class TestValidateNavStrategySelected:
    """REQ-PE-005: Nav strategy validation."""

    def test_passes_when_strategy_in_state(self, tmp_path):
        """validate_nav_strategy_selected passes when strategy in state."""
        state = make_state(_pe_nav_strategy="ts-aware")
        result = validate_nav_strategy_selected(state, tmp_path)
        assert result["passed"] is True
        assert result["strategy"] == "ts-aware"

    def test_warns_when_missing(self, tmp_path):
        """validate_nav_strategy_selected warns when missing and auto-selects."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        with patch.object(pe_overlay, "_resolve_repo_root", return_value=project):
            result = validate_nav_strategy_selected(state, project)

        assert result["passed"] is True
        assert any("not selected" in w for w in result["warnings"])
        # Should have auto-selected
        assert "_pe_nav_strategy" in state


# ============================================================================
# 6. COE SYSTEM
# ============================================================================


class TestCreateCoeTemplate:
    """REQ-PE-006: COE template creation."""

    def test_returns_all_required_fields(self):
        """create_coe_template returns all required fields."""
        template = create_coe_template("TASK-001", "Found SQL injection vulnerability")

        for field in COE_REQUIRED_FIELDS:
            assert field in template, f"Missing field: {field}"

        assert template["task_id"] == "TASK-001"
        assert template["finding"] == "Found SQL injection vulnerability"
        assert "created_at" in template

    def test_empty_fields_initialized(self):
        """create_coe_template initializes empty fields for analysis."""
        template = create_coe_template("T-1", "Finding")

        assert template["why_1"] == ""
        assert template["why_2"] == ""
        assert template["why_3"] == ""
        assert template["root_cause"] == ""
        assert template["fix_strategy"] == ""
        assert template["search_patterns"] == []

    def test_created_at_is_iso_format(self):
        """create_coe_template sets created_at in ISO format."""
        template = create_coe_template("T-1", "Finding")
        # Should not raise
        datetime.fromisoformat(template["created_at"])


class TestValidateCoeAnalysis:
    """REQ-PE-006: COE analysis validation."""

    def test_complete_coe_returns_valid(self, tmp_path):
        """validate_coe_analysis with complete COE returns valid=True."""
        coe = {
            "task_id": "T-1",
            "finding": "SQL injection",
            "why_1": "No input validation",
            "why_2": "No ORM usage",
            "why_3": "Legacy code pattern",
            "root_cause": "Lack of parameterized queries",
            "fix_strategy": "Migrate to ORM",
            "pattern_scope": "all SQL files",
            "search_patterns": ["execute_raw", "raw_sql"],
        }
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert result["valid"] is True
        assert result["missing_fields"] == []

    def test_missing_fields_returns_list(self, tmp_path):
        """validate_coe_analysis with missing fields returns missing_fields list."""
        coe = {"task_id": "T-1", "finding": "Something"}
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert result["valid"] is False
        assert "why_1" in result["missing_fields"]
        assert "root_cause" in result["missing_fields"]

    def test_empty_root_cause_returns_invalid(self, tmp_path):
        """validate_coe_analysis with empty root_cause returns invalid."""
        coe = {
            "task_id": "T-1",
            "finding": "Issue",
            "why_1": "Reason 1",
            "why_2": "Reason 2",
            "why_3": "Reason 3",
            "root_cause": "",
            "fix_strategy": "Fix it",
            "pattern_scope": "everywhere",
            "search_patterns": ["pattern"],
        }
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert result["valid"] is False
        assert "root_cause" in result["missing_fields"]

    def test_empty_search_patterns_warns(self, tmp_path):
        """validate_coe_analysis with empty search_patterns lists as missing."""
        coe = {
            "task_id": "T-1",
            "finding": "Issue",
            "why_1": "R1",
            "why_2": "R2",
            "why_3": "R3",
            "root_cause": "Root",
            "fix_strategy": "Fix",
            "pattern_scope": "scope",
            "search_patterns": [],
        }
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert result["valid"] is False
        assert "search_patterns" in result["missing_fields"]

    def test_shallow_analysis_warns(self, tmp_path):
        """validate_coe_analysis warns on shallow analysis (only 1 why)."""
        coe = {
            "task_id": "T-1",
            "finding": "Issue",
            "why_1": "Only one level",
            "why_2": "",
            "why_3": "",
            "root_cause": "Root",
            "fix_strategy": "Fix",
            "pattern_scope": "scope",
            "search_patterns": ["pat"],
        }
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert any("1 'why' level" in w for w in result["warnings"])

    def test_two_why_levels_warns(self, tmp_path):
        """validate_coe_analysis warns when only 2 why levels filled."""
        coe = {
            "task_id": "T-1",
            "finding": "Issue",
            "why_1": "R1",
            "why_2": "R2",
            "why_3": "",
            "root_cause": "Root",
            "fix_strategy": "Fix",
            "pattern_scope": "scope",
            "search_patterns": ["pat"],
        }
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert any("2 'why' levels" in w for w in result["warnings"])

    def test_nonexistent_file_returns_invalid(self, tmp_path):
        """validate_coe_analysis with nonexistent file returns invalid."""
        result = validate_coe_analysis(tmp_path / "no-such-file.json")

        assert result["valid"] is False
        assert len(result["missing_fields"]) == len(COE_REQUIRED_FIELDS)

    def test_invalid_search_pattern_entry_warns(self, tmp_path):
        """validate_coe_analysis warns on non-string search pattern entries."""
        coe = {
            "task_id": "T-1",
            "finding": "Issue",
            "why_1": "R1",
            "why_2": "R2",
            "why_3": "R3",
            "root_cause": "Root",
            "fix_strategy": "Fix",
            "pattern_scope": "scope",
            "search_patterns": ["valid", "", "also valid"],
        }
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert any("search_patterns[1]" in w for w in result["warnings"])

    def test_all_three_whys_no_shallow_warning(self, tmp_path):
        """validate_coe_analysis with all 3 whys filled has no shallow warning."""
        coe = {
            "task_id": "T-1",
            "finding": "Issue",
            "why_1": "R1",
            "why_2": "R2",
            "why_3": "R3",
            "root_cause": "Root",
            "fix_strategy": "Fix",
            "pattern_scope": "scope",
            "search_patterns": ["pat"],
        }
        coe_path = tmp_path / "coe.json"
        coe_path.write_text(json.dumps(coe), encoding="utf-8")
        result = validate_coe_analysis(coe_path)

        assert not any("why" in w.lower() for w in result["warnings"])


class TestLoadCoeAnalysis:
    """REQ-PE-006: COE analysis loading."""

    def test_existing_file_returns_dict(self, tmp_path):
        """load_coe_analysis with existing file returns dict."""
        coe_data = {"task_id": "T-1", "root_cause": "Bad input"}
        make_coe_file(tmp_path, "T-1", coe_data)
        result = load_coe_analysis(tmp_path, "T-1")

        assert result is not None
        assert result["task_id"] == "T-1"

    def test_missing_file_returns_none(self, tmp_path):
        """load_coe_analysis with missing file returns None."""
        result = load_coe_analysis(tmp_path, "nonexistent-task")
        assert result is None

    def test_missing_coe_dir_returns_none(self, tmp_path):
        """load_coe_analysis when coe-analyses dir missing returns None."""
        result = load_coe_analysis(tmp_path, "T-1")
        assert result is None


# ============================================================================
# 7. PATTERN SWEEP
# ============================================================================


class TestPatternSweep:
    """REQ-PE-007: Pattern sweep execution."""

    def test_no_search_patterns_returns_clean(self, tmp_path):
        """pattern_sweep with no search_patterns returns clean=True."""
        result = pattern_sweep(tmp_path, "T-1", {"search_patterns": []})

        assert result["clean"] is True
        assert result["remaining_instances"] == []

    def test_finds_remaining_instances(self, tmp_path):
        """pattern_sweep finds remaining instances of patterns in codebase."""
        project = make_project(tmp_path)
        # Create a source file with a matching pattern
        src_content = "conn.execute_raw('SELECT * FROM users WHERE id=' + user_id)"
        (project / "app.py").write_text(src_content, encoding="utf-8")
        coe = {"search_patterns": ["execute_raw"]}
        with patch.object(pe_overlay, "_resolve_repo_root", return_value=project):
            result = pattern_sweep(project, "T-1", coe)

        assert result["clean"] is False
        assert len(result["remaining_instances"]) >= 1
        assert result["patterns_checked"] == ["execute_raw"]

    def test_clean_when_no_matches(self, tmp_path):
        """pattern_sweep returns clean=True when patterns find nothing."""
        project = make_project(tmp_path)
        (project / "app.py").write_text("safe_code = True", encoding="utf-8")
        coe = {"search_patterns": ["dangerous_func"]}
        result = pattern_sweep(project, "T-1", coe)

        assert result["clean"] is True

    def test_invalid_regex_reported(self, tmp_path):
        """pattern_sweep reports invalid regex patterns."""
        project = make_project(tmp_path)
        coe = {"search_patterns": ["[invalid(regex"]}
        result = pattern_sweep(project, "T-1", coe)

        assert result["clean"] is False
        assert any(r.get("error") == "invalid regex" for r in result["remaining_instances"])

    def test_skips_binary_files(self, tmp_path):
        """pattern_sweep skips binary file extensions."""
        project = make_project(tmp_path)
        (project / "image.png").write_bytes(b"fake png with dangerous_func call")
        # .lock files should be skipped
        (project / "package.lock").write_text("dangerous_func", encoding="utf-8")
        coe = {"search_patterns": ["dangerous_func"]}
        result = pattern_sweep(project, "T-1", coe)

        file_matches = [r.get("file") for r in result["remaining_instances"]]
        assert not any("image.png" in (f or "") for f in file_matches)


class TestPatternSweepSummary:
    """REQ-PE-007: Pattern sweep summary."""

    def test_no_coe_dir_returns_passed(self, tmp_path):
        """pattern_sweep_summary with no coe-analyses dir returns passed=True."""
        state = make_state()
        result = pattern_sweep_summary(state, tmp_path)

        assert result["passed"] is True
        assert result["sweeps_run"] == 0

    def test_clean_sweeps_pass(self, tmp_path):
        """pattern_sweep_summary with clean sweeps returns passed=True."""
        project = make_project(tmp_path)
        # Create COE file with patterns that do not match anything
        coe_data = {
            "task_id": "T-1",
            "search_patterns": ["nonexistent_pattern_xyz123"],
        }
        make_coe_file(project, "T-1", coe_data)
        state = make_state(repo_root=project)
        result = pattern_sweep_summary(state, project)

        assert result["passed"] is True
        assert result["sweeps_run"] == 1

    def test_remaining_instances_block(self, tmp_path):
        """pattern_sweep_summary blocks when patterns still match files."""
        project = make_project(tmp_path)
        (project / "src.py").write_text("dangerous_func(user_input)", encoding="utf-8")
        coe_data = {
            "task_id": "T-1",
            "search_patterns": ["dangerous_func"],
        }
        make_coe_file(project, "T-1", coe_data)
        state = make_state(repo_root=project)
        with patch.object(pe_overlay, "_resolve_repo_root", return_value=project):
            result = pattern_sweep_summary(state, project)

        assert result["passed"] is False
        assert result["total_remaining"] > 0

    def test_multiple_coe_files_counted(self, tmp_path):
        """pattern_sweep_summary processes multiple COE files."""
        project = make_project(tmp_path)
        make_coe_file(project, "T-1", {
            "task_id": "T-1",
            "search_patterns": ["nonexistent_abc"],
        })
        make_coe_file(project, "T-2", {
            "task_id": "T-2",
            "search_patterns": ["nonexistent_def"],
        })
        state = make_state(repo_root=project)
        result = pattern_sweep_summary(state, project)

        assert result["sweeps_run"] == 2
        assert result["passed"] is True


# ============================================================================
# 8. BACKWARD COMPATIBILITY
# ============================================================================


class TestBackwardCompatibility:
    """REQ-PE-008: Backward compatibility with older state formats."""

    def test_empty_state_init_to_discovering(self, tmp_path):
        """All INIT->DISCOVERING gate checks pass with empty state."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = run_gate("INIT", "DISCOVERING", state, project)

        assert result["passed"] is True

    def test_empty_state_discovering_to_reviewing(self, tmp_path):
        """All DISCOVERING->REVIEWING gate checks pass with empty state."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = run_gate("DISCOVERING", "REVIEWING", state, project)

        assert result["passed"] is True

    def test_empty_state_reviewing_to_executing(self, tmp_path):
        """All REVIEWING->EXECUTING gate checks pass with empty state."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = run_gate("REVIEWING", "EXECUTING", state, project)

        assert result["passed"] is True

    def test_v416_state_format(self, tmp_path):
        """All gate checks pass with v4.1.6 state format (no new PE fields)."""
        project = make_project(tmp_path)
        state = {
            "project_id": "test-project",
            "request": "Analyze this codebase",
            "repo_root": str(project),
            "phase": "INIT",
            "agents": [],
            "findings": [],
        }
        result = run_gate("INIT", "DISCOVERING", state, project)
        assert result["passed"] is True

    def test_load_dod_template_no_templates_dir(self):
        """load_dod_template works when .qralph/templates/ doesn't exist."""
        result = load_dod_template("dod-api.md")
        assert "categories" in result
        assert "blockers" in result

    def test_load_adrs_no_docs_dir(self, tmp_path):
        """load_adrs works when target repo has no docs/adrs/."""
        project = make_project(tmp_path)
        state = make_state(repo_root=project)
        result = load_adrs(state, project)

        assert result["passed"] is True
        assert result["adrs_loaded"] == 0


# ============================================================================
# 9. ADDITIONAL EDGE CASES & HELPERS
# ============================================================================


class TestGateResult:
    """Test the _gate_result helper."""

    def test_basic_pass(self):
        result = _gate_result(True)
        assert result["passed"] is True
        assert result["blockers"] == []
        assert result["warnings"] == []

    def test_basic_fail_with_blockers(self):
        result = _gate_result(False, blockers=["b1", "b2"])
        assert result["passed"] is False
        assert len(result["blockers"]) == 2

    def test_extra_kwargs(self):
        result = _gate_result(True, extra_field="value")
        assert result["extra_field"] == "value"


class TestParseAdrFile:
    """Test the _parse_adr_file helper."""

    def test_extracts_title(self, tmp_path):
        adr_file = tmp_path / "ADR-001-test.md"
        adr_file.write_text("# My Great Decision\n\nSome content.", encoding="utf-8")
        result = _parse_adr_file(adr_file)
        assert result["title"] == "My Great Decision"

    def test_extracts_status(self, tmp_path):
        adr_file = tmp_path / "ADR-002-test.md"
        adr_file.write_text("# Title\n\n**Status**: Deprecated\n", encoding="utf-8")
        result = _parse_adr_file(adr_file)
        assert result["status"] == "Deprecated"

    def test_empty_file_returns_empty_dict(self, tmp_path):
        adr_file = tmp_path / "ADR-003-empty.md"
        adr_file.write_text("", encoding="utf-8")
        result = _parse_adr_file(adr_file)
        assert result == {}

    def test_id_from_filename(self, tmp_path):
        adr_file = tmp_path / "ADR-042-naming.md"
        adr_file.write_text("# Naming Convention\n", encoding="utf-8")
        result = _parse_adr_file(adr_file)
        assert result["id"] == "ADR-042-naming"


class TestResolveRepoRoot:
    """Test the _resolve_repo_root helper."""

    def test_uses_state_repo_root(self, tmp_path):
        project = make_project(tmp_path)
        state = {"repo_root": str(project)}
        result = _resolve_repo_root(state, project)
        assert result == project

    def test_fallback_when_repo_root_invalid(self, tmp_path):
        state = {"repo_root": "/nonexistent/path/xyz"}
        result = _resolve_repo_root(state, tmp_path)
        # Should fall back to cwd or walk up
        assert isinstance(result, Path)


class TestStoreLearnings:
    """Test store_learnings_to_memory."""

    def test_writes_learnings_file(self, tmp_path):
        """store_learnings_to_memory writes learnings.json."""
        project = make_project(tmp_path)
        state = make_state(
            project_id="test-proj",
            repo_root=project,
            _pe_project_type="api",
            _pe_nav_strategy="ts-aware",
            _pe_adrs=[],
            _pe_proposed_adrs=[],
            _pe_inferred_requirements=[],
        )
        result = store_learnings_to_memory(state, project)

        assert result["passed"] is True
        assert result["learnings_stored"] is True
        assert (project / "learnings.json").is_file()

    def test_includes_coe_summaries(self, tmp_path):
        """store_learnings_to_memory includes COE summaries."""
        project = make_project(tmp_path)
        coe_data = {
            "task_id": "T-1",
            "root_cause": "Missing validation",
            "fix_strategy": "Add input sanitization",
        }
        make_coe_file(project, "T-1", coe_data)

        state = make_state(
            project_id="test-proj",
            repo_root=project,
            _pe_adrs=[],
            _pe_proposed_adrs=[],
            _pe_inferred_requirements=[],
        )
        result = store_learnings_to_memory(state, project)

        assert result["coe_count"] == 1
        learnings = json.loads((project / "learnings.json").read_text(encoding="utf-8"))
        assert learnings["coe_analyses"][0]["root_cause"] == "Missing validation"

    def test_saves_proposed_adrs_on_completion(self, tmp_path):
        """store_learnings_to_memory saves proposed ADRs."""
        project = make_project(tmp_path)
        state = make_state(
            project_id="test-proj",
            repo_root=project,
            _pe_adrs=[],
            _pe_proposed_adrs=[{
                "id": "PROPOSED-001",
                "title": "Use Redis",
                "context": "Caching",
                "source_agent": "arch",
            }],
            _pe_inferred_requirements=[],
        )
        result = store_learnings_to_memory(state, project)

        assert result["proposed_adr_count"] == 1
        assert (project / "proposed-adrs").is_dir()


class TestParseDodMarkdown:
    """Test the _parse_dod_markdown helper."""

    def test_parses_categories_and_items(self):
        content = (
            "## Code Quality\n"
            "- [ ] No lint errors\n"
            "- [x] Type-safe code\n"
            "## Testing\n"
            "- [ ] Unit tests\n"
        )
        result = _parse_dod_markdown(content)

        assert "Code Quality" in result["categories"]
        assert "No lint errors" in result["categories"]["Code Quality"]
        assert "Testing" in result["categories"]

    def test_blocker_marker(self):
        content = (
            "## Security [BLOCKER]\n"
            "- [ ] Input validation\n"
        )
        result = _parse_dod_markdown(content)

        assert "Security" in result["blockers"]
        assert "Security" in result["categories"]

    def test_default_blockers_when_none_marked(self):
        content = (
            "## Testing\n"
            "- [ ] Tests pass\n"
            "## Security\n"
            "- [ ] No secrets\n"
            "## Docs\n"
            "- [ ] README\n"
        )
        result = _parse_dod_markdown(content)

        assert "Testing" in result["blockers"]
        assert "Security" in result["blockers"]
        assert "Docs" not in result["blockers"]


class TestFullDodCheck:
    """Test full_dod_check with agent outputs."""

    def test_satisfied_items_pass(self, tmp_path):
        """full_dod_check counts satisfied items from agent outputs."""
        project = make_project(tmp_path)
        make_agent_output(
            project, "code-review",
            "All unit tests for business logic are passing. "
            "No lint errors or warnings found. "
            "Input validation on all endpoints verified."
        )
        state = make_state(
            _pe_dod=_default_dod_template(),
        )
        result = full_dod_check(state, project)

        assert result["items_checked"] > 0
        assert result["items_satisfied"] > 0

    def test_missing_blocker_items_block(self, tmp_path):
        """full_dod_check blocks when blocker category items missing."""
        project = make_project(tmp_path)
        # No agent outputs - nothing satisfied
        state = make_state(
            _pe_dod={
                "categories": {
                    "Testing": ["All unit tests passing"],
                },
                "blockers": ["Testing"],
            },
        )
        result = full_dod_check(state, project)

        assert result["passed"] is False
        assert any("[Testing]" in b for b in result["blockers"])


class TestGateCheckRegistry:
    """Verify the GATE_CHECKS registry structure."""

    def test_all_transitions_have_callable_checks(self):
        """All gate check entries are callable functions."""
        for transition, checks in GATE_CHECKS.items():
            assert isinstance(transition, tuple)
            assert len(transition) == 2
            for check in checks:
                assert callable(check), f"{check} in {transition} is not callable"

    def test_known_transitions_present(self):
        """All expected phase transitions are registered."""
        expected = [
            ("INIT", "DISCOVERING"),
            ("DISCOVERING", "REVIEWING"),
            ("REVIEWING", "EXECUTING"),
            ("EXECUTING", "VALIDATING"),
            ("VALIDATING", "COMPLETE"),
        ]
        for t in expected:
            assert t in GATE_CHECKS, f"Missing transition: {t}"

    def test_version_is_semver(self):
        """Module VERSION follows semver format."""
        parts = VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
