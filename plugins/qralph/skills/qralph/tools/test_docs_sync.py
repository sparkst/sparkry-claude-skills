"""Tests that README and installation guide stay in sync with the pipeline.

These tests fail CI when someone bumps the pipeline version or changes phases
but forgets to update the docs — which we do often.
"""

import os
import re
import pytest

# Paths relative to repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
README = os.path.join(REPO_ROOT, "README.md")
INSTALL_GUIDE = os.path.join(REPO_ROOT, "docs", "QRALPH-INSTALLATION-GUIDE.md")

# Import pipeline source of truth
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "qralph_pipeline",
    os.path.join(os.path.dirname(__file__), "qralph-pipeline.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

PIPELINE_VERSION = _mod.__version__
PIPELINE_PHASES = _mod.PHASES


def _read(path):
    with open(path) as f:
        return f.read()


# ── README checks ──────────────────────────────────────────────────────


class TestReadmeSync:
    """README.md must reflect the current pipeline version and phases."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.text = _read(README)

    def test_version_mentioned(self):
        """README must mention the current pipeline version (e.g. v6.8.0)."""
        assert f"v{PIPELINE_VERSION}" in self.text, (
            f"README.md does not mention v{PIPELINE_VERSION}. "
            f"Update the version references after bumping __version__."
        )

    def test_phase_count(self):
        """README must state the correct number of pipeline phases."""
        expected = len(PIPELINE_PHASES)
        pattern = r"(\d+)-phase"
        matches = re.findall(pattern, self.text)
        counts = [int(m) for m in matches]
        assert expected in counts, (
            f"README.md says {counts}-phase but pipeline has {expected} phases. "
            f"Update the phase count references."
        )

    def test_all_phases_in_table(self):
        """Every phase from PHASES must appear in the README pipeline table."""
        for phase in PIPELINE_PHASES:
            assert phase in self.text, (
                f"README.md is missing phase '{phase}' from the pipeline table. "
                f"Add a row for it."
            )

    def test_pipeline_diagram_complete(self):
        """The ASCII pipeline diagram must list all phases."""
        # Find the fenced code block with the pipeline diagram
        diagram_match = re.search(
            r"```\n((?:.*→.*\n)+)```", self.text
        )
        assert diagram_match, "README.md is missing the pipeline ASCII diagram."
        diagram = diagram_match.group(1)
        for phase in PIPELINE_PHASES:
            assert phase in diagram, (
                f"Pipeline diagram in README.md is missing '{phase}'. "
                f"Update the diagram."
            )


# ── Installation guide checks ──────────────────────────────────────────


class TestInstallGuideSync:
    """QRALPH-INSTALLATION-GUIDE.md must reflect the current pipeline phases."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.text = _read(INSTALL_GUIDE)

    def test_phase_count(self):
        """Installation guide must state the correct number of phases."""
        expected = len(PIPELINE_PHASES)
        pattern = r"(\d+)-phase"
        matches = re.findall(pattern, self.text)
        counts = [int(m) for m in matches]
        assert expected in counts, (
            f"QRALPH-INSTALLATION-GUIDE.md says {counts}-phase but pipeline "
            f"has {expected} phases. Update the phase count references."
        )

    def test_all_phases_in_table(self):
        """Every phase must appear in the installation guide's phase table."""
        for phase in PIPELINE_PHASES:
            assert phase in self.text, (
                f"QRALPH-INSTALLATION-GUIDE.md is missing phase '{phase}'. "
                f"Add it to the phase table."
            )
