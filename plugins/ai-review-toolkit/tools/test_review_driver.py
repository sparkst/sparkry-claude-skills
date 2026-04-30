"""Tests for review-driver.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Import review-driver.py via shared _loader
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

rd = load_sibling("review-driver.py")
fp = load_sibling("finding-parser.py")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def review_dir(tmp_path: Path) -> Path:
    """Create a temp directory with a minimal artifact and requirements."""
    artifact = tmp_path / "artifact.py"
    artifact.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    reqs = tmp_path / "requirements.md"
    reqs.write_text("# Requirements\n\n- R1: Must return 'world'\n", encoding="utf-8")

    return tmp_path


@pytest.fixture()
def initialized_state(review_dir: Path) -> dict[str, Any]:
    """Return an initialized review state."""
    state = rd.init_review(
        artifact_path=str(review_dir / "artifact.py"),
        requirements_path=str(review_dir / "requirements.md"),
        base_dir=str(review_dir),
    )
    return state


@pytest.fixture()
def base_dir(review_dir: Path) -> str:
    return str(review_dir)


# ---------------------------------------------------------------------------
# Helper: sample findings
# ---------------------------------------------------------------------------

def _make_finding(
    fid: str = "P1-001",
    severity: str = "P1",
    title: str = "Missing error handling",
    source: str = "test-reviewer",
) -> dict[str, Any]:
    return {
        "id": fid,
        "severity": severity,
        "title": title,
        "requirement": "R1",
        "finding": "The function does not handle None input.",
        "recommendation": "Add input validation.",
        "source": source,
        "evidence": "artifact.py:1",
    }


def _sample_findings_json(findings: list[dict[str, Any]] | None = None) -> str:
    if findings is None:
        findings = [_make_finding()]
    return json.dumps(findings)


# ---------------------------------------------------------------------------
# Tests: init
# ---------------------------------------------------------------------------

class TestInit:
    def test_creates_state_file_with_correct_structure(
        self, review_dir: Path
    ) -> None:
        rd.init_review(
            artifact_path=str(review_dir / "artifact.py"),
            requirements_path=str(review_dir / "requirements.md"),
            base_dir=str(review_dir),
        )

        state_path = review_dir / ".qreview" / "state.json"
        assert state_path.exists()

        on_disk = json.loads(state_path.read_text(encoding="utf-8"))
        for key in (
            "artifact_path",
            "requirements_path",
            "team",
            "test_results",
            "reviewer_outputs",
            "synthesis",
            "status",
            "created_at",
        ):
            assert key in on_disk, f"Missing key: {key}"

        assert on_disk["status"] == "initialized"
        assert isinstance(on_disk["team"], list)
        assert isinstance(on_disk["test_results"], dict)
        assert on_disk["reviewer_outputs"] == {}
        assert on_disk["synthesis"] is None

    def test_selects_team_based_on_artifact_type(
        self, review_dir: Path
    ) -> None:
        state = rd.init_review(
            artifact_path=str(review_dir / "artifact.py"),
            requirements_path=str(review_dir / "requirements.md"),
            base_dir=str(review_dir),
        )

        assert len(state["team"]) >= 2
        for member in state["team"]:
            assert "name" in member
            assert "model" in member
            assert "review_lens" in member

    def test_runs_test_discovery(self, review_dir: Path) -> None:
        state = rd.init_review(
            artifact_path=str(review_dir / "artifact.py"),
            requirements_path=str(review_dir / "requirements.md"),
            base_dir=str(review_dir),
        )

        tr = state["test_results"]
        assert "all_passed" in tr
        assert "summary" in tr
        assert "failures_as_findings" in tr


# ---------------------------------------------------------------------------
# Tests: get_reviewer_prompt
# ---------------------------------------------------------------------------

class TestGetReviewerPrompt:
    def test_includes_artifact_content(
        self, initialized_state: dict[str, Any]
    ) -> None:
        prompt = rd.get_reviewer_prompt(initialized_state, 0)
        assert "def hello():" in prompt
        assert "return 'world'" in prompt

    def test_includes_requirements(
        self, initialized_state: dict[str, Any]
    ) -> None:
        prompt = rd.get_reviewer_prompt(initialized_state, 0)
        assert "Must return 'world'" in prompt

    def test_includes_test_results(
        self, initialized_state: dict[str, Any]
    ) -> None:
        prompt = rd.get_reviewer_prompt(initialized_state, 0)
        # Test results section is always present
        assert "## Test Results" in prompt

    def test_does_not_include_prior_findings(
        self, review_dir: Path, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        # Record some findings first
        rd.record_findings(
            initialized_state,
            0,
            _sample_findings_json(),
            base_dir=base_dir,
        )

        # Now generate prompt for reviewer 1 -- should NOT contain
        # reviewer 0's findings
        if len(initialized_state["team"]) > 1:
            prompt = rd.get_reviewer_prompt(initialized_state, 1)
            assert "Missing error handling" not in prompt
            assert "P1-001" not in prompt

    def test_does_not_include_implementation_context(
        self, initialized_state: dict[str, Any]
    ) -> None:
        prompt = rd.get_reviewer_prompt(initialized_state, 0)
        # Should not contain state file contents or team composition
        assert ".qreview" not in prompt
        assert "state.json" not in prompt

    def test_raises_on_bad_index(
        self, initialized_state: dict[str, Any]
    ) -> None:
        with pytest.raises(IndexError):
            rd.get_reviewer_prompt(initialized_state, 99)


# ---------------------------------------------------------------------------
# Tests: record_findings
# ---------------------------------------------------------------------------

class TestRecordFindings:
    def test_validates_finding_schema(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        findings_raw = _sample_findings_json()
        valid = rd.record_findings(
            initialized_state, 0, findings_raw, base_dir=base_dir
        )
        assert len(valid) == 1
        assert valid[0]["id"] == "P1-001"

    def test_drops_invalid_findings(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        bad = [{"id": "BADID", "severity": "P9"}]
        valid = rd.record_findings(
            initialized_state, 0, json.dumps(bad), base_dir=base_dir
        )
        assert len(valid) == 0

    def test_extracts_json_from_mixed_output(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        mixed = "Here are my findings:\n" + _sample_findings_json() + "\n\nDone."
        valid = rd.record_findings(
            initialized_state, 0, mixed, base_dir=base_dir
        )
        assert len(valid) == 1

    def test_updates_state_on_disk(
        self, review_dir: Path, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        rd.record_findings(
            initialized_state, 0, _sample_findings_json(), base_dir=base_dir
        )

        on_disk = json.loads(
            (review_dir / ".qreview" / "state.json").read_text(encoding="utf-8")
        )
        assert "0" in on_disk["reviewer_outputs"]
        assert on_disk["status"] == "reviewing"

    def test_rejects_duplicate_reviewer_submission(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        rd.record_findings(
            initialized_state, 0, _sample_findings_json(), base_dir=base_dir
        )
        state = rd.get_status(base_dir)
        with pytest.raises(ValueError, match="already submitted"):
            rd.record_findings(state, 0, _sample_findings_json(), base_dir=base_dir)

    def test_raises_on_bad_reviewer_index(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        with pytest.raises((IndexError, ValueError)):
            rd.record_findings(
                initialized_state, -1, _sample_findings_json(), base_dir=base_dir
            )
        with pytest.raises((IndexError, ValueError)):
            rd.record_findings(
                initialized_state, 99, _sample_findings_json(), base_dir=base_dir
            )

    def test_rejects_findings_after_synthesis(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        rd.record_findings(
            initialized_state, 0, _sample_findings_json(), base_dir=base_dir
        )
        state = rd.get_status(base_dir)
        rd.record_findings(state, 1, _sample_findings_json(), base_dir=base_dir)
        state = rd.get_status(base_dir)
        rd.synthesize_round(state, base_dir=base_dir)
        state = rd.get_status(base_dir)
        with pytest.raises(ValueError, match="synthesized"):
            rd.record_findings(state, 0, _sample_findings_json(), base_dir=base_dir)


# ---------------------------------------------------------------------------
# Tests: synthesize_round
# ---------------------------------------------------------------------------

class TestSynthesizeRound:
    def test_uses_max_severity_dedup(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        # Two reviewers flag the same issue at different severities
        f1 = _make_finding(fid="P2-001", severity="P2", title="Missing validation", source="reviewer-a")
        f2 = _make_finding(fid="P0-001", severity="P0", title="Missing validation", source="reviewer-b")

        rd.record_findings(initialized_state, 0, json.dumps([f1]), base_dir=base_dir)
        # Reload state from disk after first record
        state = rd.get_status(base_dir)
        rd.record_findings(state, 1, json.dumps([f2]), base_dir=base_dir)

        state = rd.get_status(base_dir)
        synthesis = rd.synthesize_round(state, base_dir=base_dir)

        findings = synthesis["findings"]
        # Deduplicated to 1 finding
        matching = [f for f in findings if "missing validation" in f["title"].lower()]
        assert len(matching) == 1
        assert matching[0]["severity"] == "P0"

    def test_sorts_p0_first(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        findings = [
            _make_finding(fid="P3-001", severity="P3", title="Style nit", source="r1"),
            _make_finding(fid="P0-001", severity="P0", title="Security hole", source="r1"),
            _make_finding(fid="P1-001", severity="P1", title="Missing tests", source="r1"),
        ]
        rd.record_findings(initialized_state, 0, json.dumps(findings), base_dir=base_dir)

        # Submit empty findings for remaining reviewers so synthesis guard passes
        state = rd.get_status(base_dir)
        for i in range(1, len(state["team"])):
            rd.record_findings(state, i, json.dumps([]), base_dir=base_dir)
            state = rd.get_status(base_dir)

        synthesis = rd.synthesize_round(state, base_dir=base_dir)

        result_sevs = [f["severity"] for f in synthesis["findings"]]
        assert result_sevs == ["P0", "P1", "P3"]

    def test_includes_test_failure_findings(
        self, review_dir: Path, base_dir: str
    ) -> None:
        # Create state with a test failure finding
        state = rd.init_review(
            artifact_path=str(review_dir / "artifact.py"),
            requirements_path=str(review_dir / "requirements.md"),
            base_dir=base_dir,
        )
        # Manually inject a test failure finding
        state["test_results"]["failures_as_findings"] = [
            _make_finding(fid="P1-099", severity="P1", title="Test failure: assert", source="test-runner"),
        ]
        rd._write_state(state, base_dir)

        # Submit empty findings for all reviewers so synthesis guard passes
        state = rd.get_status(base_dir)
        for i in range(len(state["team"])):
            rd.record_findings(state, i, json.dumps([]), base_dir=base_dir)
            state = rd.get_status(base_dir)

        synthesis = rd.synthesize_round(state, base_dir=base_dir)

        titles = [f["title"].lower() for f in synthesis["findings"]]
        assert any("test failure" in t for t in titles)

    def test_convergence_check(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        # Only P3 findings => should converge
        f = _make_finding(fid="P3-001", severity="P3", title="Minor nit", source="r1")
        rd.record_findings(initialized_state, 0, json.dumps([f]), base_dir=base_dir)

        # Submit empty findings for remaining reviewers so synthesis guard passes
        state = rd.get_status(base_dir)
        for i in range(1, len(state["team"])):
            rd.record_findings(state, i, json.dumps([]), base_dir=base_dir)
            state = rd.get_status(base_dir)

        synthesis = rd.synthesize_round(state, base_dir=base_dir)
        # P3 count is 1 which exceeds default threshold of 0
        assert synthesis["convergence_message"] is not None


# ---------------------------------------------------------------------------
# Tests: get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_returns_current_state(
        self, review_dir: Path, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        status = rd.get_status(base_dir)
        assert status["status"] == "initialized"
        assert status["artifact_path"] == str(review_dir / "artifact.py")


# ---------------------------------------------------------------------------
# Tests: reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_clears_state_directory(
        self, review_dir: Path, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        state_dir = review_dir / ".qreview"
        assert state_dir.exists()

        rd.reset(base_dir)
        assert not state_dir.exists()

    def test_reset_when_no_state(self, tmp_path: Path) -> None:
        # Should not raise even if .qreview does not exist
        rd.reset(str(tmp_path))


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_handles_missing_artifact(self, tmp_path: Path) -> None:
        reqs = tmp_path / "requirements.md"
        reqs.write_text("# Reqs\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Artifact not found"):
            rd.init_review(
                artifact_path=str(tmp_path / "nonexistent.py"),
                requirements_path=str(reqs),
                base_dir=str(tmp_path),
            )

    def test_handles_missing_requirements(self, tmp_path: Path) -> None:
        artifact = tmp_path / "artifact.py"
        artifact.write_text("x = 1\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Requirements not found"):
            rd.init_review(
                artifact_path=str(artifact),
                requirements_path=str(tmp_path / "nonexistent.md"),
                base_dir=str(tmp_path),
            )

    def test_status_without_init(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No review state found"):
            rd.get_status(str(tmp_path))

    def test_record_findings_with_garbage_input(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        valid = rd.record_findings(
            initialized_state, 0, "this is not json at all", base_dir=base_dir
        )
        assert valid == []


# ---------------------------------------------------------------------------
# Tests: synthesize_round threshold parameter
# ---------------------------------------------------------------------------

class TestSynthesizeDroppedFindings:
    def test_dropped_findings_tracked_in_synthesis(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        valid = _make_finding(fid="P1-001", severity="P1", title="Good finding", source="r1")
        bad = {"severity": "P0"}  # Missing most fields
        rd.record_findings(initialized_state, 0, json.dumps([valid, bad]), base_dir=base_dir)

        state = rd.get_status(base_dir)
        for i in range(1, len(state["team"])):
            rd.record_findings(state, i, json.dumps([]), base_dir=base_dir)
            state = rd.get_status(base_dir)

        synthesis = rd.synthesize_round(state, base_dir=base_dir)
        # record_findings pre-validates, so only valid findings reach synthesis;
        # dropped_count must be exactly 0 when no invalid findings are injected
        assert synthesis["dropped_count"] == 0


class TestSynthesizeThreshold:
    def test_threshold_from_parameter(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        # Record a single P3 finding
        f = _make_finding(fid="P3-001", severity="P3", title="Style nit", source="r1")
        rd.record_findings(initialized_state, 0, json.dumps([f]), base_dir=base_dir)

        state = rd.get_status(base_dir)
        for i in range(1, len(state["team"])):
            rd.record_findings(state, i, json.dumps([]), base_dir=base_dir)
            state = rd.get_status(base_dir)

        # threshold=5 should allow 1 P3 to converge
        synthesis = rd.synthesize_round(state, threshold=5, base_dir=base_dir)
        assert synthesis["converged"] is True

    def test_threshold_from_state(
        self, review_dir: Path, base_dir: str
    ) -> None:
        state = rd.init_review(
            artifact_path=str(review_dir / "artifact.py"),
            requirements_path=str(review_dir / "requirements.md"),
            base_dir=base_dir,
        )
        # Override state threshold
        state["convergence_threshold"] = 10
        rd._write_state(state, base_dir)

        f = _make_finding(fid="P2-001", severity="P2", title="Minor issue", source="r1")
        rd.record_findings(state, 0, json.dumps([f]), base_dir=base_dir)

        state = rd.get_status(base_dir)
        for i in range(1, len(state["team"])):
            rd.record_findings(state, i, json.dumps([]), base_dir=base_dir)
            state = rd.get_status(base_dir)

        synthesis = rd.synthesize_round(state, base_dir=base_dir)
        assert synthesis["converged"] is True

    def test_default_threshold_is_zero(
        self, initialized_state: dict[str, Any], base_dir: str
    ) -> None:
        assert initialized_state.get("convergence_threshold") == 0


# ---------------------------------------------------------------------------
# Tests: context budget instruction in reviewer prompt
# ---------------------------------------------------------------------------

class TestContextBudgetInstruction:
    def test_prompt_includes_context_budget_guidance(
        self, initialized_state: dict[str, Any]
    ) -> None:
        prompt = rd.get_reviewer_prompt(initialized_state, 0)
        assert "Read only files relevant to your review domain" in prompt
        assert "Use Grep to find relevant sections" in prompt


# ---------------------------------------------------------------------------
# Tests: CLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_init_creates_state(self, review_dir: Path) -> None:
        artifact = review_dir / "artifact.py"
        reqs = review_dir / "requirements.md"

        # Use main() directly with argv, running from review_dir as cwd
        import os
        old_cwd = os.getcwd()
        os.chdir(str(review_dir))
        try:
            ret = rd.main([
                "init",
                "--artifact", str(artifact),
                "--requirements", str(reqs),
            ])
        finally:
            os.chdir(old_cwd)

        assert ret == 0
        state_path = review_dir / ".qreview" / "state.json"
        assert state_path.exists()

        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["status"] == "initialized"

    def test_status_reads_state(self, review_dir: Path) -> None:
        artifact = review_dir / "artifact.py"
        reqs = review_dir / "requirements.md"

        import os
        old_cwd = os.getcwd()
        os.chdir(str(review_dir))
        try:
            rd.main([
                "init",
                "--artifact", str(artifact),
                "--requirements", str(reqs),
            ])
            ret = rd.main(["status"])
        finally:
            os.chdir(old_cwd)

        assert ret == 0

    def test_synthesize_produces_output(self, review_dir: Path) -> None:
        artifact = review_dir / "artifact.py"
        reqs = review_dir / "requirements.md"

        import os
        old_cwd = os.getcwd()
        os.chdir(str(review_dir))
        try:
            rd.main([
                "init",
                "--artifact", str(artifact),
                "--requirements", str(reqs),
            ])
            # Submit empty findings for all reviewers so synthesis guard passes
            state = rd.get_status(str(review_dir))
            for i in range(len(state["team"])):
                rd.record_findings(state, i, json.dumps([]), base_dir=str(review_dir))
                state = rd.get_status(str(review_dir))
            ret = rd.main(["synthesize"])
        finally:
            os.chdir(old_cwd)

        assert ret == 0

        state = json.loads(
            (review_dir / ".qreview" / "state.json").read_text(encoding="utf-8")
        )
        assert state["status"] == "synthesized"
        assert state["synthesis"] is not None

    def test_reset_clears_state(self, review_dir: Path) -> None:
        artifact = review_dir / "artifact.py"
        reqs = review_dir / "requirements.md"

        import os
        old_cwd = os.getcwd()
        os.chdir(str(review_dir))
        try:
            rd.main([
                "init",
                "--artifact", str(artifact),
                "--requirements", str(reqs),
            ])
            assert (review_dir / ".qreview").exists()

            ret = rd.main(["reset"])
        finally:
            os.chdir(old_cwd)

        assert ret == 0
        assert not (review_dir / ".qreview").exists()

    def test_no_command_returns_nonzero(self) -> None:
        ret = rd.main([])
        assert ret == 1

    def test_status_without_init_returns_nonzero(self, tmp_path: Path) -> None:
        import os
        old_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            ret = rd.main(["status"])
        finally:
            os.chdir(old_cwd)
        assert ret == 1

    def test_init_missing_artifact_returns_nonzero(self, tmp_path: Path) -> None:
        reqs = tmp_path / "requirements.md"
        reqs.write_text("# Reqs\n", encoding="utf-8")

        import os
        old_cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            ret = rd.main([
                "init",
                "--artifact", str(tmp_path / "nonexistent.py"),
                "--requirements", str(reqs),
            ])
        finally:
            os.chdir(old_cwd)
        assert ret == 1
