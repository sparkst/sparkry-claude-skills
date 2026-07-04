"""Tests for version-check.py — the skill self-version-check (pure logic)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

v = load_sibling("version-check.py")


class TestParseSemver:
    def test_parses_dotted(self):
        assert v.parse_semver("1.6.0") == (1, 6, 0)

    def test_tolerates_v_prefix_and_whitespace(self):
        assert v.parse_semver(" v1.5.2 ") == (1, 5, 2)

    def test_short_versions_zero_padded(self):
        assert v.parse_semver("2") == (2, 0, 0)
        assert v.parse_semver("2.1") == (2, 1, 0)


class TestCompareVersions:
    def test_behind(self):
        assert v.compare_versions("1.5.2", "1.6.0") == "behind"

    def test_ahead(self):
        assert v.compare_versions("1.6.0", "1.5.2") == "ahead"

    def test_equal(self):
        assert v.compare_versions("1.6.0", "1.6.0") == "equal"

    def test_patch_level_behind(self):
        assert v.compare_versions("1.6.0", "1.6.1") == "behind"


class TestUpgradeNotice:
    def test_no_notice_when_current(self):
        assert v.upgrade_notice("1.6.0", "1.6.0", "marketplace") is None

    def test_no_notice_when_ahead(self):
        assert v.upgrade_notice("1.7.0", "1.6.0", "marketplace") is None

    def test_marketplace_notice_names_plugin_command(self):
        msg = v.upgrade_notice("1.5.2", "1.6.0", "marketplace")
        assert msg is not None
        assert "1.5.2" in msg and "1.6.0" in msg
        assert "/plugin marketplace update" in msg

    def test_fork_notice_points_at_resync_not_plugin_command(self):
        msg = v.upgrade_notice("1.5.2", "1.6.0", "fork")
        assert msg is not None
        assert "/plugin marketplace update" not in msg
        assert "sync" in msg.lower()


class TestCacheFreshness:
    def test_fresh_within_ttl(self):
        assert v.cache_is_fresh(stamp_epoch=1000, now_epoch=1000 + 3600, ttl=86400) is True

    def test_stale_past_ttl(self):
        assert v.cache_is_fresh(stamp_epoch=1000, now_epoch=1000 + 90000, ttl=86400) is False

    def test_missing_stamp_is_stale(self):
        assert v.cache_is_fresh(stamp_epoch=None, now_epoch=1000, ttl=86400) is False


class TestDetectInstallKind:
    def test_fork_path_detected(self):
        assert v.detect_install_kind("/Users/x/.claude/ai-review-tools/version-check.py") == "fork"

    def test_marketplace_path_detected(self):
        p = "/Users/x/.claude/plugins/marketplaces/sparkry-claude-skills/plugins/ai-review-toolkit/tools/version-check.py"
        assert v.detect_install_kind(p) == "marketplace"
