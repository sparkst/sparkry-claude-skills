"""Tests for check-version-bump.py — the version-bump gate (pure logic)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

c = load_sibling("check-version-bump.py")


class TestRequiresBump:
    def test_source_change_requires_bump(self):
        assert c.requires_bump(["plugins/ai-review-toolkit/tools/prod-tail.py"]) is True

    def test_workflow_change_requires_bump(self):
        assert c.requires_bump(["plugins/ai-review-toolkit/js/pipeline-auto.workflow.js"]) is True

    def test_changelog_only_does_not_require_bump(self):
        assert c.requires_bump(["plugins/ai-review-toolkit/CHANGELOG.md"]) is False

    def test_other_plugin_change_does_not_require_bump(self):
        assert c.requires_bump(["plugins/qralph/skills/qralph/tools/x.py"]) is False

    def test_repo_root_change_does_not_require_bump(self):
        # A pure marketplace.json/CI change with no plugin source is not gated here.
        assert c.requires_bump([".github/workflows/tests.yml"]) is False

    def test_mixed_changes_require_bump_if_any_source(self):
        assert c.requires_bump([
            "README.md",
            "plugins/ai-review-toolkit/CHANGELOG.md",
            "plugins/ai-review-toolkit/tools/tdd-harness.py",
        ]) is True


class TestCheckBump:
    def test_no_source_change_passes_without_bump(self):
        res = c.check_bump(
            changed_paths=["plugins/ai-review-toolkit/CHANGELOG.md"],
            old_plugin="1.5.2", new_plugin="1.5.2",
            old_market="1.5.2", new_market="1.5.2",
        )
        assert res["ok"] is True
        assert res["bump_required"] is False

    def test_source_change_with_matching_bump_passes(self):
        res = c.check_bump(
            changed_paths=["plugins/ai-review-toolkit/tools/prod-tail.py"],
            old_plugin="1.5.2", new_plugin="1.6.0",
            old_market="1.5.2", new_market="1.6.0",
        )
        assert res["ok"] is True
        assert res["bump_required"] is True

    def test_source_change_without_bump_fails(self):
        res = c.check_bump(
            changed_paths=["plugins/ai-review-toolkit/tools/prod-tail.py"],
            old_plugin="1.5.2", new_plugin="1.5.2",
            old_market="1.5.2", new_market="1.5.2",
        )
        assert res["ok"] is False
        assert any("plugin.json" in v for v in res["violations"])
        assert any("marketplace.json" in v for v in res["violations"])

    def test_only_one_file_bumped_fails_on_mismatch(self):
        res = c.check_bump(
            changed_paths=["plugins/ai-review-toolkit/tools/prod-tail.py"],
            old_plugin="1.5.2", new_plugin="1.6.0",
            old_market="1.5.2", new_market="1.5.2",  # forgot marketplace.json
        )
        assert res["ok"] is False
        # marketplace.json unchanged AND the two disagree
        assert any("marketplace.json" in v for v in res["violations"])
        assert any("disagree" in v for v in res["violations"])

    def test_bumped_but_versions_disagree_fails(self):
        res = c.check_bump(
            changed_paths=["plugins/ai-review-toolkit/js/pipeline-auto.workflow.js"],
            old_plugin="1.5.2", new_plugin="1.6.0",
            old_market="1.5.2", new_market="1.6.1",  # both bumped but not equal
        )
        assert res["ok"] is False
        assert any("disagree" in v for v in res["violations"])
