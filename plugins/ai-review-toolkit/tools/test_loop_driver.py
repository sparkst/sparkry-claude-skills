"""Tests for loop-driver.py -- the /qloop state machine."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Setup: load hyphenated module via shared _loader
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

_ld = load_sibling("loop-driver.py", "loop_driver")
loop_driver = _ld
init_loop = _ld.init_loop
next_action = _ld.next_action
record_review = _ld.record_review
record_fixes = _ld.record_fixes
record_test_results = _ld.record_test_results
check_fix_completeness = _ld.check_fix_completeness
get_reviewer_prompt = _ld.get_reviewer_prompt
get_fixer_prompt = _ld.get_fixer_prompt
get_status = _ld.get_status
reset = _ld.reset
_read_state = _ld._read_state
_write_state = _ld._write_state
_get_round = _ld._get_round


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def artifact_file(tmp_path: Path) -> Path:
    """Create a minimal artifact file."""
    f = tmp_path / "artifact.py"
    f.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    return f


@pytest.fixture()
def requirements_file(tmp_path: Path) -> Path:
    """Create a minimal requirements file."""
    f = tmp_path / "requirements.md"
    f.write_text("# Requirements\n\n- REQ-001: Function must return 'world'\n", encoding="utf-8")
    return f


def _init(
    tmp_path: Path,
    artifact_file: Path,
    requirements_file: Path,
    **kwargs: Any,
) -> dict[str, Any]:
    """Helper to init a loop in a temp directory."""
    return init_loop(
        artifact_path=str(artifact_file),
        requirements_path=str(requirements_file),
        base=str(tmp_path),
        **kwargs,
    )


def _next(state: dict[str, Any], tmp_path: Path) -> dict[str, Any]:
    """Helper to call next_action with tmp_path as base_dir for disk isolation."""
    return next_action(state, base_dir=str(tmp_path))


def _make_findings(
    severities: list[str],
    prefix: str = "F",
) -> list[dict[str, Any]]:
    """Create minimal valid findings."""
    findings = []
    for i, sev in enumerate(severities, 1):
        findings.append({
            "id": f"{sev}-{i:03d}",
            "severity": sev,
            "title": f"{prefix} finding {i}",
            "requirement": "REQ-001",
            "finding": f"Issue {i} description",
            "recommendation": f"Fix {i}",
            "source": "test-reviewer",
            "evidence": f"file.py:{i}",
        })
    return findings


def _make_resolutions(
    findings: list[dict[str, Any]],
    status: str = "FIXED",
) -> list[dict[str, Any]]:
    """Create resolutions for all findings."""
    return [
        {
            "finding_id": f["id"],
            "status": status,
            "evidence": "file:1",
            "description": f"Fixed {f['id']}",
        }
        for f in findings
    ]


# ---------------------------------------------------------------------------
# Tests: init
# ---------------------------------------------------------------------------

class TestInit:
    def test_creates_state_with_correct_structure(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        assert "artifact_path" in state
        assert "requirements_path" in state
        assert len(state.get("team", [])) >= 2
        assert "threshold" in state
        assert "max_rounds" in state
        assert "min_rounds" in state
        assert "current_round" in state
        assert "team" in state
        assert "rounds" in state
        assert "status" in state
        assert "created_at" in state

    def test_selects_team(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        assert len(state["team"]) >= 2
        for agent in state["team"]:
            assert "name" in agent
            assert "review_lens" in agent
            assert "domains" in agent

    def test_enforces_min_rounds_2(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file, max_rounds=1)
        assert state["min_rounds"] == 2
        assert state["max_rounds"] >= 2

    def test_initial_status(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        assert state["status"] == "initialized"
        assert state["current_round"] == 1
        assert len(state["rounds"]) == 1
        assert state["rounds"][0]["round_num"] == 1

    def test_state_file_created(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        _init(tmp_path, artifact_file, requirements_file)
        state_path = tmp_path / ".qloop" / "state.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text(encoding="utf-8"))
        assert data["status"] == "initialized"


# ---------------------------------------------------------------------------
# Tests: next_action
# ---------------------------------------------------------------------------

class TestNextAction:
    def test_returns_run_tests_first(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        action = _next(state, tmp_path)
        assert action["action"] == "run_tests"

    def test_returns_spawn_reviewers_after_tests(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        # Simulate tests done
        state["rounds"][0]["phase"] = "tests_done"
        state["rounds"][0]["test_results"] = {"summary": "1/1 passed", "all_passed": True}
        action = _next(state, tmp_path)
        assert action["action"] == "spawn_reviewers"
        assert "prompts" in action
        assert len(action["prompts"]) == len(state["team"])

    def test_returns_spawn_fixer_after_review_synthesis(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        # Simulate round 1 synthesized with findings
        findings = _make_findings(["P1", "P2"])
        state["rounds"][0]["phase"] = "synthesized"
        state["rounds"][0]["findings"] = findings
        action = _next(state, tmp_path)
        assert action["action"] == "spawn_fixer"
        assert "prompt" in action

    def test_returns_validate_fixes_after_fixer_incomplete(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P1", "P2"])
        state["rounds"][0]["phase"] = "fixing"
        state["rounds"][0]["findings"] = findings
        # Only fix one of two
        state["rounds"][0]["fix_resolutions"] = [
            {"finding_id": findings[0]["id"], "status": "FIXED", "evidence": "f:1", "description": "ok"},
        ]
        action = _next(state, tmp_path)
        assert action["action"] == "validate_fixes"
        assert findings[1]["id"] in action["required_findings"]

    def test_refuses_to_advance_if_fixes_incomplete(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P0", "P1", "P2"])
        state["rounds"][0]["phase"] = "fixing"
        state["rounds"][0]["findings"] = findings
        # Fix only one
        state["rounds"][0]["fix_resolutions"] = [
            {"finding_id": findings[0]["id"], "status": "FIXED", "evidence": "f:1", "description": "ok"},
        ]
        action = _next(state, tmp_path)
        assert action["action"] == "validate_fixes"
        missing = action["required_findings"]
        assert len(missing) == 2
        assert findings[1]["id"] in missing
        assert findings[2]["id"] in missing

    def test_returns_run_tests_for_round_2(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P1"])
        state["rounds"][0]["phase"] = "fixing"
        state["rounds"][0]["findings"] = findings
        state["rounds"][0]["fix_resolutions"] = _make_resolutions(findings)
        action = _next(state, tmp_path)
        # Should advance to round 2 and ask to run tests
        assert action["action"] == "run_tests"
        assert state["current_round"] == 2
        assert len(state["rounds"]) == 2


# ---------------------------------------------------------------------------
# Tests: round 2 reviewer prompt
# ---------------------------------------------------------------------------

class TestRound2Prompts:
    def test_round_2_reviewer_prompt_includes_prior_findings(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P1", "P2"])
        state["rounds"][0]["phase"] = "resolved"
        state["rounds"][0]["findings"] = findings
        state["rounds"][0]["fix_resolutions"] = _make_resolutions(findings)

        # Create round 2
        round2 = {
            "round_num": 2,
            "phase": "tests_done",
            "findings": [],
            "reviewer_findings": [],
            "test_results": {"summary": "1/1 passed"},
            "fix_resolutions": [],
            "synthesis": {},
            "timestamp": "now",
        }
        state["rounds"].append(round2)
        state["current_round"] = 2

        prompt = get_reviewer_prompt(state, 0, 2)
        assert "Prior Round Findings" in prompt
        assert "Round 1" in prompt

    def test_round_2_reviewer_prompt_includes_verification_instructions(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P1"])
        state["rounds"][0]["phase"] = "resolved"
        state["rounds"][0]["findings"] = findings
        state["rounds"][0]["fix_resolutions"] = _make_resolutions(findings)

        round2 = {
            "round_num": 2,
            "phase": "tests_done",
            "findings": [],
            "reviewer_findings": [],
            "test_results": {"summary": "1/1 passed"},
            "fix_resolutions": [],
            "synthesis": {},
            "timestamp": "now",
        }
        state["rounds"].append(round2)
        state["current_round"] = 2

        prompt = get_reviewer_prompt(state, 0, 2)
        assert "Verification Instructions" in prompt
        assert "POST-FIX version" in prompt
        assert "verify the fix is correct" in prompt

    def test_round_1_prompt_does_not_include_prior_findings(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        prompt = get_reviewer_prompt(state, 0, 1)
        assert "Prior Round Findings" not in prompt
        assert "Diff Summary" not in prompt


# ---------------------------------------------------------------------------
# Tests: convergence
# ---------------------------------------------------------------------------

class TestConvergence:
    def test_converged_p0_0_p1_0_p2_0(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        # Set up round 1 resolved with findings, then round 2 clean
        findings_r1 = _make_findings(["P2"])
        state["rounds"][0]["phase"] = "resolved"
        state["rounds"][0]["findings"] = findings_r1
        state["rounds"][0]["fix_resolutions"] = _make_resolutions(findings_r1)

        round2 = {
            "round_num": 2,
            "phase": "synthesized",
            "findings": [],  # No findings!
            "reviewer_findings": [],
            "test_results": {},
            "fix_resolutions": [],
            "synthesis": {"counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0}},
            "timestamp": "now",
        }
        state["rounds"].append(round2)
        state["current_round"] = 2
        state["status"] = "reviewing"

        action = _next(state, tmp_path)
        assert action["action"] == "converged"

    def test_not_converged_p1_remains(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P1"])
        state["rounds"][0]["phase"] = "synthesized"
        state["rounds"][0]["findings"] = findings
        action = _next(state, tmp_path)
        # Should continue (spawn fixer), NOT converge
        assert action["action"] == "spawn_fixer"

    def test_not_converged_before_min_rounds(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        """Even with zero findings, must still do min_rounds."""
        state = _init(tmp_path, artifact_file, requirements_file)
        # Round 1 synthesized with zero findings
        state["rounds"][0]["phase"] = "synthesized"
        state["rounds"][0]["findings"] = []
        state["rounds"][0]["synthesis"] = {"counts": {"P0": 0, "P1": 0, "P2": 0, "P3": 0}}
        action = _next(state, tmp_path)
        # Should NOT converge (round 1 < min_rounds 2), should advance
        assert action["action"] == "run_tests"
        assert state["current_round"] == 2


# ---------------------------------------------------------------------------
# Tests: max rounds -> escalated
# ---------------------------------------------------------------------------

class TestMaxRounds:
    def test_max_rounds_reached_escalated(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file, max_rounds=2)
        # Round 1 resolved
        findings_r1 = _make_findings(["P1"])
        state["rounds"][0]["phase"] = "resolved"
        state["rounds"][0]["findings"] = findings_r1
        state["rounds"][0]["fix_resolutions"] = _make_resolutions(findings_r1)

        # Round 2 synthesized with P1 remaining
        round2 = {
            "round_num": 2,
            "phase": "synthesized",
            "findings": _make_findings(["P1"]),
            "reviewer_findings": [],
            "test_results": {},
            "fix_resolutions": [],
            "synthesis": {},
            "timestamp": "now",
        }
        state["rounds"].append(round2)
        state["current_round"] = 2
        state["status"] = "reviewing"

        action = _next(state, tmp_path)
        assert action["action"] == "escalated"
        assert "Max rounds" in action["reason"]
        assert len(action["unresolved"]) > 0
        assert state["status"] == "escalated"


# ---------------------------------------------------------------------------
# Tests: stuck detection
# ---------------------------------------------------------------------------

class TestStuckDetection:
    def test_same_findings_two_rounds_escalated(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        # Round 1: P0 finding
        findings_r1 = _make_findings(["P0"])
        state["rounds"][0]["phase"] = "resolved"
        state["rounds"][0]["findings"] = findings_r1
        state["rounds"][0]["fix_resolutions"] = _make_resolutions(findings_r1)

        # Round 2: same P0 finding (same title, same count)
        findings_r2 = _make_findings(["P0"])  # Same title prefix
        round2 = {
            "round_num": 2,
            "phase": "fixing",
            "findings": findings_r2,
            "reviewer_findings": [],
            "test_results": {},
            "fix_resolutions": _make_resolutions(findings_r2),
            "synthesis": {},
            "timestamp": "now",
        }
        state["rounds"].append(round2)
        state["current_round"] = 2

        action = _next(state, tmp_path)
        assert action["action"] == "escalated"
        assert "Stuck" in action["reason"]


# ---------------------------------------------------------------------------
# Tests: check_fix_completeness
# ---------------------------------------------------------------------------

class TestCheckFixCompleteness:
    def test_all_fixed_returns_true(self) -> None:
        findings = _make_findings(["P0", "P1", "P2"])
        resolutions = _make_resolutions(findings)
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is True
        assert missing == []

    def test_missing_fix_returns_false_with_ids(self) -> None:
        findings = _make_findings(["P0", "P1", "P2"])
        # Only fix the first one
        resolutions = [_make_resolutions(findings)[0]]
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is False
        assert len(missing) == 2
        assert findings[1]["id"] in missing
        assert findings[2]["id"] in missing

    def test_empty_findings_empty_resolutions(self) -> None:
        complete, missing = check_fix_completeness([], [])
        assert complete is True
        assert missing == []


# ---------------------------------------------------------------------------
# Tests: record_review
# ---------------------------------------------------------------------------

class TestRecordReview:
    def test_records_reviewer_findings(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        state["rounds"][0]["phase"] = "tests_done"
        findings = _make_findings(["P1"])
        state = record_review(state, 1, 0, findings)
        rnd = _get_round(state, 1)
        assert rnd is not None
        assert len(rnd["reviewer_findings"]) == 1
        assert rnd["reviewer_findings"][0]["reviewer_index"] == 0

    def test_auto_synthesizes_when_all_reviewers_report(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file, reviewer_count=2)
        state["rounds"][0]["phase"] = "tests_done"
        findings1 = _make_findings(["P1"], prefix="A")
        findings2 = _make_findings(["P2"], prefix="B")
        state = record_review(state, 1, 0, findings1)
        # Not yet synthesized
        rnd = _get_round(state, 1)
        assert rnd is not None
        assert rnd["phase"] == "reviewing"

        state = record_review(state, 1, 1, findings2)
        # Now synthesized
        rnd = _get_round(state, 1)
        assert rnd is not None
        assert rnd["phase"] == "synthesized"
        assert len(rnd["findings"]) > 0
        assert "counts" in rnd["synthesis"]


# ---------------------------------------------------------------------------
# Tests: record_fixes
# ---------------------------------------------------------------------------

class TestRecordFixes:
    def test_records_resolutions(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P1"])
        state["rounds"][0]["findings"] = findings
        state["rounds"][0]["phase"] = "synthesized"
        resolutions = _make_resolutions(findings)
        state = record_fixes(state, 1, resolutions)
        rnd = _get_round(state, 1)
        assert rnd is not None
        assert len(rnd["fix_resolutions"]) == 1
        assert rnd["phase"] == "fixing"
        assert state["status"] == "fixing"


# ---------------------------------------------------------------------------
# Tests: status and reset
# ---------------------------------------------------------------------------

class TestStatusAndReset:
    def test_status_returns_current_state(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        _init(tmp_path, artifact_file, requirements_file)
        result = get_status(str(tmp_path))
        assert result["status"] == "initialized"
        assert result["current_round"] == 1
        assert result["min_rounds"] == 2
        assert len(result["team"]) >= 2

    def test_status_no_state(self, tmp_path: Path) -> None:
        result = get_status(str(tmp_path))
        assert result["status"] == "no_state"

    def test_reset_clears_state(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        _init(tmp_path, artifact_file, requirements_file)
        state_dir = tmp_path / ".qloop"
        assert state_dir.exists()
        result = reset(str(tmp_path))
        assert result["status"] == "reset"
        assert not state_dir.exists()

    def test_reset_no_state(self, tmp_path: Path) -> None:
        """Reset on non-existent state should succeed silently."""
        result = reset(str(tmp_path))
        assert result["status"] == "reset"


# ---------------------------------------------------------------------------
# Tests: full round-trip scenario
# ---------------------------------------------------------------------------

class TestFullRoundTrip:
    def test_two_round_convergence(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        """Walk through a complete 2-round loop that converges."""
        state = _init(tmp_path, artifact_file, requirements_file, reviewer_count=2)

        # Round 1: run_tests
        action = _next(state, tmp_path)
        assert action["action"] == "run_tests"
        state["rounds"][0]["phase"] = "tests_done"
        state["rounds"][0]["test_results"] = {
            "summary": "1/1 passed",
            "all_passed": True,
            "failures_as_findings": [],
        }

        # Round 1: spawn reviewers
        action = _next(state, tmp_path)
        assert action["action"] == "spawn_reviewers"

        # Record reviewer findings
        findings_r1 = _make_findings(["P1", "P2"])
        state = record_review(state, 1, 0, findings_r1)
        state = record_review(state, 1, 1, [])  # Second reviewer found nothing new

        # Round 1 should be synthesized now
        rnd1 = _get_round(state, 1)
        assert rnd1 is not None
        assert rnd1["phase"] == "synthesized"

        # Round 1: spawn fixer
        action = _next(state, tmp_path)
        assert action["action"] == "spawn_fixer"

        # Record fixes
        resolutions = _make_resolutions(rnd1["findings"])
        state = record_fixes(state, 1, resolutions)

        # Advance to round 2
        action = _next(state, tmp_path)
        assert action["action"] == "run_tests"
        assert state["current_round"] == 2

        # Round 2: tests done
        rnd2 = _get_round(state, 2)
        assert rnd2 is not None
        rnd2["phase"] = "tests_done"
        rnd2["test_results"] = {
            "summary": "1/1 passed",
            "all_passed": True,
            "failures_as_findings": [],
        }

        # Round 2: spawn reviewers
        action = _next(state, tmp_path)
        assert action["action"] == "spawn_reviewers"

        # Round 2 reviewers find nothing
        state = record_review(state, 2, 0, [])
        state = record_review(state, 2, 1, [])

        rnd2 = _get_round(state, 2)
        assert rnd2 is not None
        assert rnd2["phase"] == "synthesized"

        # Round 2 should converge
        action = _next(state, tmp_path)
        assert action["action"] == "converged"
        assert state["status"] == "converged"


# ---------------------------------------------------------------------------
# Tests: status validation in check_fix_completeness (fixes 8-10)
# ---------------------------------------------------------------------------

class TestStatusValidation:
    def test_wontfix_status_rejected(self) -> None:
        """Resolution with status WONTFIX fails check_fix_completeness."""
        findings = _make_findings(["P1"])
        resolutions = _make_resolutions(findings, status="WONTFIX")
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is False
        assert findings[0]["id"] in missing

    def test_deferred_status_rejected(self) -> None:
        """Resolution with status DEFERRED fails check_fix_completeness."""
        findings = _make_findings(["P1"])
        resolutions = _make_resolutions(findings, status="DEFERRED")
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is False
        assert findings[0]["id"] in missing

    def test_escalated_status_accepted(self) -> None:
        """Resolution with status ESCALATED passes check_fix_completeness."""
        findings = _make_findings(["P1"])
        resolutions = _make_resolutions(findings, status="ESCALATED")
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is True
        assert missing == []


# ---------------------------------------------------------------------------
# Tests: resolved phase guard (fix 11)
# ---------------------------------------------------------------------------

class TestResolvedWithoutFixes:
    def test_resolved_without_fixes_rejected(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        """next_action at resolved phase with findings but no fix_resolutions returns error."""
        state = _init(tmp_path, artifact_file, requirements_file)
        findings = _make_findings(["P1", "P2"])
        state["rounds"][0]["phase"] = "resolved"
        state["rounds"][0]["findings"] = findings
        state["rounds"][0]["fix_resolutions"] = []
        action = _next(state, tmp_path)
        assert action["action"] == "error"
        assert "no fix_resolutions" in action["message"]


# ---------------------------------------------------------------------------
# Tests: record_review bounds and duplicate checks (fixes 12-13)
# ---------------------------------------------------------------------------

class TestRecordReviewValidation:
    def test_reviewer_index_out_of_bounds(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        """record_review with invalid index raises ValueError."""
        state = _init(tmp_path, artifact_file, requirements_file)
        state["rounds"][0]["phase"] = "tests_done"
        findings = _make_findings(["P1"])
        # reviewer_count is >= 2 from team selection; use an index beyond that
        bad_index = len(state["team"]) + 5
        with pytest.raises(ValueError, match="out of bounds"):
            record_review(state, 1, bad_index, findings)

        # Also test negative index
        with pytest.raises(ValueError, match="out of bounds"):
            record_review(state, 1, -1, findings)

    def test_duplicate_reviewer_rejected(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        """Same reviewer submitting twice raises ValueError."""
        state = _init(tmp_path, artifact_file, requirements_file)
        state["rounds"][0]["phase"] = "tests_done"
        findings = _make_findings(["P1"])
        state = record_review(state, 1, 0, findings)
        with pytest.raises(ValueError, match="already submitted"):
            record_review(state, 1, 0, findings)


# ---------------------------------------------------------------------------
# Tests: init_loop file validation (fix 14)
# ---------------------------------------------------------------------------

class TestInitFileValidation:
    def test_init_missing_requirements_file(
        self, tmp_path: Path, artifact_file: Path
    ) -> None:
        """init_loop with nonexistent requirements path raises FileNotFoundError."""
        fake_req = str(tmp_path / "nonexistent_requirements.md")
        with pytest.raises(FileNotFoundError, match="Requirements not found"):
            init_loop(
                artifact_path=str(artifact_file),
                requirements_path=fake_req,
                base=str(tmp_path),
            )

    def test_init_missing_artifact_file(
        self, tmp_path: Path, requirements_file: Path
    ) -> None:
        """init_loop with nonexistent artifact path raises FileNotFoundError."""
        fake_art = str(tmp_path / "nonexistent_artifact.py")
        with pytest.raises(FileNotFoundError, match="Artifact not found"):
            init_loop(
                artifact_path=fake_art,
                requirements_path=str(requirements_file),
                base=str(tmp_path),
            )


# ---------------------------------------------------------------------------
# Tests: CLI (P1-4 coverage)
# ---------------------------------------------------------------------------

_main = _ld.main


class TestModuleCaching:
    def test_load_sibling_uses_sys_modules_cache(self) -> None:
        """Repeated load_sibling calls return the same module object."""
        mod1 = load_sibling("finding-parser.py", "finding_parser")
        mod2 = load_sibling("finding-parser.py", "finding_parser")
        assert mod1 is mod2


class TestCLI:
    def test_init_creates_state(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        ret = _main([
            "init",
            "--artifact", str(artifact_file),
            "--requirements", str(requirements_file),
        ])
        assert ret == 0
        state_path = tmp_path / ".qloop" / "state.json"
        assert state_path.exists()

    def test_status_reads_state(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _main([
            "init",
            "--artifact", str(artifact_file),
            "--requirements", str(requirements_file),
        ])
        ret = _main(["status"])
        assert ret == 0

    def test_next_after_init(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _main([
            "init",
            "--artifact", str(artifact_file),
            "--requirements", str(requirements_file),
        ])
        ret = _main(["next"])
        assert ret == 0

    def test_next_without_init_returns_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        ret = _main(["next"])
        assert ret == 1

    def test_reset_clears_state(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _main([
            "init",
            "--artifact", str(artifact_file),
            "--requirements", str(requirements_file),
        ])
        assert (tmp_path / ".qloop").exists()
        ret = _main(["reset"])
        assert ret == 0
        assert not (tmp_path / ".qloop").exists()

    def test_record_review_with_findings(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _main([
            "init",
            "--artifact", str(artifact_file),
            "--requirements", str(requirements_file),
        ])
        # Advance round to tests_done before recording review
        test_results_file = tmp_path / "test_results.json"
        test_results_file.write_text(
            json.dumps({"all_passed": True, "summary": "0/0 passed", "failures_as_findings": []}),
            encoding="utf-8",
        )
        _main(["record-tests", "--round", "1", "--results-file", str(test_results_file)])
        findings_file = tmp_path / "findings.json"
        findings_file.write_text(
            json.dumps(_make_findings(["P1"])),
            encoding="utf-8",
        )
        ret = _main([
            "record-review",
            "--round", "1",
            "--reviewer", "0",
            "--findings-file", str(findings_file),
        ])
        assert ret == 0

    def test_record_review_missing_findings_file(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _main([
            "init",
            "--artifact", str(artifact_file),
            "--requirements", str(requirements_file),
        ])
        ret = _main([
            "record-review",
            "--round", "1",
            "--reviewer", "0",
            "--findings-file", str(tmp_path / "nonexistent.json"),
        ])
        assert ret == 1

    def test_record_fixes_with_resolutions(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _main([
            "init",
            "--artifact", str(artifact_file),
            "--requirements", str(requirements_file),
        ])
        # Advance round phase to synthesized so record-fixes is accepted
        state = _read_state()
        state["rounds"][0]["phase"] = "synthesized"
        _write_state(state)
        resolutions_file = tmp_path / "resolutions.json"
        resolutions_file.write_text(
            json.dumps([{"finding_id": "P1-001", "status": "FIXED", "evidence": "f:1", "description": "ok"}]),
            encoding="utf-8",
        )
        ret = _main([
            "record-fixes",
            "--round", "1",
            "--resolutions-file", str(resolutions_file),
        ])
        assert ret == 0

    def test_no_command_returns_nonzero(self) -> None:
        ret = _main([])
        assert ret == 1

    def test_status_without_init_succeeds_with_no_state(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        ret = _main(["status"])
        assert ret == 0  # get_status handles missing state gracefully


# ---------------------------------------------------------------------------
# Tests: synthesize_findings warnings observability (P1-1)
# ---------------------------------------------------------------------------

class TestSynthesizeWarnings:
    def test_invalid_findings_reported_in_synthesis(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        """Invalid findings should appear in synthesis dropped_count."""
        state = _init(tmp_path, artifact_file, requirements_file, reviewer_count=2)
        state["rounds"][0]["phase"] = "tests_done"

        valid_findings = _make_findings(["P1"], prefix="V")
        invalid_findings = [{"severity": "P0"}]  # Missing most fields

        state = record_review(state, 1, 0, valid_findings)
        state = record_review(state, 1, 1, invalid_findings)

        rnd = _get_round(state, 1)
        assert rnd is not None
        assert rnd["phase"] == "synthesized"
        assert rnd["synthesis"]["dropped_count"] >= 1


# ---------------------------------------------------------------------------
# Tests: record_test_results (P0-001 fix)
# ---------------------------------------------------------------------------

class TestRecordTestResults:
    def test_transitions_to_tests_done(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        assert state["rounds"][0]["phase"] == "initialized"
        state = record_test_results(state, 1, {"all_passed": True, "summary": "1/1"})
        assert state["rounds"][0]["phase"] == "tests_done"
        assert state["status"] == "tests_done"
        assert state["rounds"][0]["test_results"]["all_passed"] is True

    def test_rejects_non_initialized_phase(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        state["rounds"][0]["phase"] = "reviewing"
        with pytest.raises(ValueError, match="phase.*reviewing"):
            record_test_results(state, 1, {"all_passed": True})

    def test_cli_record_tests(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        _main(["init", "--artifact", str(artifact_file), "--requirements", str(requirements_file)])
        results_file = tmp_path / "test_results.json"
        results_file.write_text(json.dumps({"all_passed": True, "summary": "1/1"}), encoding="utf-8")
        ret = _main(["record-tests", "--round", "1", "--results-file", str(results_file)])
        assert ret == 0


# ---------------------------------------------------------------------------
# Tests: phase guards (Round 4 fixes)
# ---------------------------------------------------------------------------

class TestPhaseGuards:
    def test_record_review_rejects_synthesized_phase(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file, reviewer_count=2)
        state["rounds"][0]["phase"] = "synthesized"
        with pytest.raises(ValueError, match="synthesized"):
            record_review(state, 1, 0, _make_findings(["P1"]))

    def test_record_fixes_rejects_initialized_phase(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        with pytest.raises(ValueError, match="initialized"):
            record_fixes(state, 1, [{"finding_id": "P1-001", "status": "FIXED"}])

    def test_negative_reviewer_index_rejected(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        state["rounds"][0]["phase"] = "tests_done"
        with pytest.raises(ValueError, match="out of range"):
            get_reviewer_prompt(state, -1, 1)

    def test_min_reviewer_floor_enforced(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file, reviewer_count=1)
        assert len(state["team"]) >= 2

    def test_record_review_rejects_initialized_phase(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file, reviewer_count=2)
        with pytest.raises(ValueError, match="tests_done"):
            record_review(state, 1, 0, _make_findings(["P1"]))

    def test_record_fixes_rejects_non_current_round(
        self, tmp_path: Path, artifact_file: Path, requirements_file: Path
    ) -> None:
        state = _init(tmp_path, artifact_file, requirements_file)
        state["current_round"] = 2
        state["rounds"].append({"round_num": 2, "phase": "initialized"})
        state["rounds"][0]["phase"] = "synthesized"
        with pytest.raises(ValueError, match="not the current round"):
            record_fixes(state, 1, [{"finding_id": "P1-001", "status": "FIXED", "evidence": "fix.py:1"}])


class TestFixCompletenessEvidence:
    def test_fixed_without_evidence_is_incomplete(self) -> None:
        findings = [{"id": "P1-001"}]
        resolutions = [{"finding_id": "P1-001", "status": "FIXED", "evidence": ""}]
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is False
        assert "P1-001" in missing

    def test_fixed_with_evidence_is_complete(self) -> None:
        findings = [{"id": "P1-001"}]
        resolutions = [{"finding_id": "P1-001", "status": "FIXED", "evidence": "file.py:42 — added guard"}]
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is True

    def test_escalated_without_evidence_is_incomplete(self) -> None:
        findings = [{"id": "P1-001"}]
        resolutions = [{"finding_id": "P1-001", "status": "ESCALATED", "evidence": ""}]
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is False
        assert "P1-001" in missing

    def test_escalated_with_evidence_is_complete(self) -> None:
        findings = [{"id": "P1-001"}]
        resolutions = [{"finding_id": "P1-001", "status": "ESCALATED", "evidence": "Requires external API change"}]
        complete, missing = check_fix_completeness(findings, resolutions)
        assert complete is True
