"""Tests for fork-sync.py — the manual-install fork upgrade tool (pure logic)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

f = load_sibling("fork-sync.py")

FORK = "/Users/travis/.claude/ai-review-tools"


class TestForkSkillTransform:
    def test_plugin_tools_becomes_flat_fork_root(self):
        # The fork is FLAT (py at root, no tools/ subdir), so <plugin>/tools loses /tools.
        assert f.fork_skill_transform('"toolsDir": "<plugin>/tools",', FORK) == '"toolsDir": "/Users/travis/.claude/ai-review-tools",'

    def test_plugin_js_becomes_fork_js(self):
        assert f.fork_skill_transform("scriptPath=<plugin>/js/x.workflow.js", FORK) == \
            "scriptPath=/Users/travis/.claude/ai-review-tools/js/x.workflow.js"

    def test_bare_plugin_becomes_fork_root(self):
        assert f.fork_skill_transform("see the <plugin> dir", FORK) == "see the /Users/travis/.claude/ai-review-tools dir"

    def test_tools_placeholder_left_untouched(self):
        # <tools> (angle-bracket runtime placeholder) is NOT <plugin> — it must survive verbatim.
        assert f.fork_skill_transform("python3 <tools>/version-check.py check", FORK) == "python3 <tools>/version-check.py check"

    def test_idempotent(self):
        once = f.fork_skill_transform("<plugin>/js/x and <plugin>/tools", FORK)
        assert f.fork_skill_transform(once, FORK) == once


class TestToolFilesToSync:
    def test_includes_runtime_py(self):
        got = f.tool_files_to_sync(["finding-parser.py", "version-check.py", "_loader.py", "__init__.py"])
        assert "finding-parser.py" in got and "version-check.py" in got and "_loader.py" in got

    def test_excludes_tests(self):
        got = f.tool_files_to_sync(["prod-tail.py", "test_prod_tail.py"])
        assert got == ["prod-tail.py"]

    def test_excludes_generators(self):
        got = f.tool_files_to_sync(["team-selector.py", "gen-golden-fixtures.py", "gen-prompt-fixtures.py"])
        assert got == ["team-selector.py"]

    def test_excludes_maintainer_only_tools(self):
        # The version-bump gate and fork-sync itself are maintainer tools — not runtime.
        got = f.tool_files_to_sync(["scorecard.py", "check-version-bump.py", "fork-sync.py"])
        assert got == ["scorecard.py"]

    def test_excludes_non_py(self):
        assert f.tool_files_to_sync(["prod-tail.py", "fixtures", "README.md"]) == ["prod-tail.py"]

    def test_sorted_deterministic(self):
        assert f.tool_files_to_sync(["b.py", "a.py"]) == ["a.py", "b.py"]
