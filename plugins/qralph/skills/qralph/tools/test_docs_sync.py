"""Tests that ALL version references and docs stay in sync with the pipeline.

Source of truth: qralph-pipeline.py __version__ and PHASES.

Every file that mentions the QRALPH version or phase count is checked here.
If you add a new file that references the version, add a test for it.

These tests fail CI when someone bumps the pipeline but forgets to update
any of the 8+ locations that reference the version — which we do often.
"""

import json
import os
import re

import pytest

# ── Setup: load source of truth ──────────────────────────────────────────

import importlib.util

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
# tools/ is at plugins/qralph/skills/qralph/tools/
_PLUGIN_DIR = os.path.abspath(os.path.join(_TOOLS_DIR, "../../.."))  # plugins/qralph
_REPO_ROOT = os.path.abspath(os.path.join(_TOOLS_DIR, "../../../../.."))  # repo root

_spec = importlib.util.spec_from_file_location(
    "qralph_pipeline",
    os.path.join(_TOOLS_DIR, "qralph-pipeline.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

VERSION = _mod.__version__           # e.g. "6.8.0"
PHASES = _mod.PHASES                 # e.g. ["IDEATE", ..., "COMPLETE"]
PHASE_COUNT = len(PHASES)            # e.g. 14


def _read(path):
    with open(path) as f:
        return f.read()


def _read_json(path):
    with open(path) as f:
        return json.load(f)


# ── 1. VERSION file ─────────────────────────────────────────────────────
# Already tested in test_qralph_pipeline.py::TestVersionSync, but included
# here for completeness so this file is the single checklist.


class TestVersionFile:
    """plugins/qralph/skills/qralph/VERSION must match __version__."""

    def test_version_file_matches(self):
        path = os.path.join(_TOOLS_DIR, "..", "VERSION")
        assert _read(path).strip() == VERSION, (
            f"VERSION file does not match __version__ ({VERSION}). "
            f"Run: echo '{VERSION}' > plugins/qralph/skills/qralph/VERSION"
        )


# ── 2. plugin.json ──────────────────────────────────────────────────────


class TestPluginJson:
    """plugins/qralph/.claude-plugin/plugin.json version must match."""

    def test_version_matches(self):
        path = os.path.join(_PLUGIN_DIR, ".claude-plugin", "plugin.json")
        data = _read_json(path)
        assert data["version"] == VERSION, (
            f"plugin.json version is {data['version']!r}, expected {VERSION!r}. "
            f"Update plugins/qralph/.claude-plugin/plugin.json"
        )


# ── 3. marketplace.json (qralph entry) ──────────────────────────────────


class TestMarketplaceJson:
    """The qralph entry in .claude-plugin/marketplace.json must match."""

    def test_version_matches(self):
        path = os.path.join(_REPO_ROOT, ".claude-plugin", "marketplace.json")
        data = _read_json(path)
        qralph_entry = None
        for plugin in data.get("plugins", []):
            if plugin.get("name") == "qralph":
                qralph_entry = plugin
                break
        assert qralph_entry is not None, (
            "No 'qralph' entry found in marketplace.json plugins array."
        )
        assert qralph_entry["version"] == VERSION, (
            f"marketplace.json qralph version is {qralph_entry['version']!r}, "
            f"expected {VERSION!r}. Update .claude-plugin/marketplace.json"
        )


# ── 4. SKILL.md ──────────────────────────────────────────────────────────


class TestSkillMd:
    """SKILL.md title must reference the current version."""

    def test_version_in_title(self):
        path = os.path.join(_TOOLS_DIR, "..", "SKILL.md")
        text = _read(path)
        # Find the first markdown heading (# ...), skipping YAML frontmatter
        heading = None
        for line in text.split("\n"):
            if line.startswith("# "):
                heading = line
                break
        assert heading is not None, "SKILL.md has no markdown heading (# ...)"
        assert f"v{VERSION}" in heading, (
            f"SKILL.md heading does not mention v{VERSION}. "
            f"Update the heading in plugins/qralph/skills/qralph/SKILL.md"
        )


# ── 5. CHANGELOG.md ─────────────────────────────────────────────────────


class TestChangelog:
    """CHANGELOG.md must have an entry for the current version."""

    def test_version_entry_exists(self):
        path = os.path.join(_TOOLS_DIR, "..", "CHANGELOG.md")
        text = _read(path)
        assert f"## v{VERSION}" in text, (
            f"CHANGELOG.md has no entry for v{VERSION}. "
            f"Add a ## v{VERSION} section to the changelog."
        )


# ── 6. Plugin README (plugins/qralph/README.md) ─────────────────────────


class TestPluginReadme:
    """plugins/qralph/README.md must reflect current version and phases."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.text = _read(os.path.join(_PLUGIN_DIR, "README.md"))

    def test_version_in_title(self):
        first_line = self.text.split("\n")[0]
        assert f"v{VERSION}" in first_line, (
            f"Plugin README title does not mention v{VERSION}. "
            f"Update the first line of plugins/qralph/README.md"
        )

    def test_phase_count(self):
        counts = [int(m) for m in re.findall(r"(\d+)-phase", self.text)]
        assert PHASE_COUNT in counts, (
            f"Plugin README says {counts}-phase but pipeline has {PHASE_COUNT}. "
            f"Update plugins/qralph/README.md"
        )

    def test_all_phases_in_diagram(self):
        for phase in PHASES:
            assert phase in self.text, (
                f"Plugin README is missing phase '{phase}'. "
                f"Update the pipeline diagram in plugins/qralph/README.md"
            )


# ── 7. Root README ───────────────────────────────────────────────────────


class TestRootReadme:
    """Root README.md must reflect current version and phases."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.text = _read(os.path.join(_REPO_ROOT, "README.md"))

    def test_version_mentioned(self):
        assert f"v{VERSION}" in self.text, (
            f"Root README does not mention v{VERSION}. "
            f"Update version references in README.md"
        )

    def test_phase_count(self):
        counts = [int(m) for m in re.findall(r"(\d+)-phase", self.text)]
        assert PHASE_COUNT in counts, (
            f"Root README says {counts}-phase but pipeline has {PHASE_COUNT}. "
            f"Update README.md"
        )

    def test_all_phases_in_table(self):
        for phase in PHASES:
            assert phase in self.text, (
                f"Root README is missing phase '{phase}'. Add it to the table."
            )

    def test_pipeline_diagram_complete(self):
        diagram_match = re.search(r"```\n((?:.*→.*\n)+)```", self.text)
        assert diagram_match, "Root README is missing the pipeline ASCII diagram."
        diagram = diagram_match.group(1)
        for phase in PHASES:
            assert phase in diagram, (
                f"Pipeline diagram in README.md is missing '{phase}'."
            )


# ── 8. Installation Guide ───────────────────────────────────────────────


class TestInstallGuide:
    """docs/QRALPH-INSTALLATION-GUIDE.md must reflect current version and phases."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.text = _read(
            os.path.join(_REPO_ROOT, "docs", "QRALPH-INSTALLATION-GUIDE.md")
        )

    def test_version_mentioned(self):
        assert f"v{VERSION}" in self.text, (
            f"Installation guide does not mention v{VERSION}. "
            f"Update docs/QRALPH-INSTALLATION-GUIDE.md"
        )

    def test_phase_count(self):
        counts = [int(m) for m in re.findall(r"(\d+)-phase", self.text)]
        assert PHASE_COUNT in counts, (
            f"Installation guide says {counts}-phase but pipeline has "
            f"{PHASE_COUNT}. Update docs/QRALPH-INSTALLATION-GUIDE.md"
        )

    def test_all_phases_in_table(self):
        for phase in PHASES:
            assert phase in self.text, (
                f"Installation guide is missing phase '{phase}'. "
                f"Add it to docs/QRALPH-INSTALLATION-GUIDE.md"
            )
