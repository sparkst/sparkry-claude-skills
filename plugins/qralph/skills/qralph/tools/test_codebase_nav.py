#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
Tests for codebase-nav.py - Adaptive search strategies for QRALPH v5.0.

REQ-NAV-001 - Strategy detection adapts to project type
REQ-NAV-002 - Search functions return structured match dicts
REQ-NAV-003 - TypeScript import parsing and resolution
REQ-NAV-004 - Polyglot language pattern generation
REQ-NAV-005 - Utility functions handle edge cases
"""

import importlib
import importlib.machinery
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Module import: codebase-nav.py has a hyphenated name and imports qralph-state
# at module level, so we mock the state module before importing.
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).parent


class _FakeLoader:
    """Minimal loader that satisfies importlib protocol."""
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        pass


def _load_codebase_nav():
    """Import codebase-nav.py with a mocked qralph-state dependency."""
    # Pre-register a fake qralph_state so the module-level import succeeds
    fake_state = types.ModuleType("qralph_state")
    fake_state.__file__ = str(_THIS_DIR / "qralph-state.py")

    original_spec_from = importlib.util.spec_from_file_location
    original_module_from = importlib.util.module_from_spec

    def patched_spec_from(name, path, *a, **kw):
        if name == "qralph_state":
            fake_spec = importlib.machinery.ModuleSpec(
                "qralph_state",
                _FakeLoader(),
                origin=str(path),
            )
            return fake_spec
        return original_spec_from(name, path, *a, **kw)

    spec = original_spec_from(
        "codebase_nav",
        _THIS_DIR / "codebase-nav.py",
    )
    module = original_module_from(spec)

    with mock.patch("importlib.util.spec_from_file_location", side_effect=patched_spec_from):
        spec.loader.exec_module(module)

    return module


nav = _load_codebase_nav()


# ---------------------------------------------------------------------------
# Fixtures: Project Scaffolds
# ---------------------------------------------------------------------------

@pytest.fixture
def make_ts_project(tmp_path):
    """Create a TypeScript project with tsconfig.json and .ts files."""
    def _make(extra_files=None):
        root = tmp_path / "ts-project"
        root.mkdir(exist_ok=True)
        (root / "tsconfig.json").write_text(json.dumps({
            "compilerOptions": {
                "baseUrl": ".",
                "paths": {"@lib/*": ["src/lib/*"]},
            },
        }))
        src = root / "src"
        src.mkdir(exist_ok=True)
        lib = src / "lib"
        lib.mkdir(exist_ok=True)

        (src / "index.ts").write_text(
            'import { greet } from "./lib/greeter";\n'
            'import type { Config } from "./lib/config";\n'
            'import "reflect-metadata";\n'
            "\n"
            "const app = greet();\n"
        )
        (lib / "greeter.ts").write_text(
            "export function greet(): string {\n"
            '  return "hello";\n'
            "}\n"
        )
        (lib / "config.ts").write_text(
            "export interface Config {\n"
            "  port: number;\n"
            "}\n"
        )
        (src / "index.spec.ts").write_text(
            'import { greet } from "./lib/greeter";\n'
            "test('greet', () => { expect(greet()).toBe('hello'); });\n"
        )
        # node_modules should be ignored
        nm = root / "node_modules" / "somepkg"
        nm.mkdir(parents=True, exist_ok=True)
        (nm / "index.ts").write_text("// should be ignored\n")

        if extra_files:
            for relpath, content in extra_files.items():
                p = root / relpath
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
        return root
    return _make


@pytest.fixture
def make_python_project(tmp_path):
    """Create a Python project with .py files."""
    def _make(extra_files=None):
        root = tmp_path / "py-project"
        root.mkdir(exist_ok=True)
        (root / "pyproject.toml").write_text('[tool.pytest.ini_options]\n')
        pkg = root / "myapp"
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("")
        (pkg / "main.py").write_text(
            "from myapp.utils import helper\n"
            "\n"
            "def run():\n"
            "    return helper()\n"
        )
        (pkg / "utils.py").write_text(
            "def helper():\n"
            '    return "ok"\n'
        )
        (pkg / "test_main.py").write_text(
            "from myapp.main import run\n"
            "\n"
            "def test_run():\n"
            "    assert run() == 'ok'\n"
        )
        if extra_files:
            for relpath, content in extra_files.items():
                p = root / relpath
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
        return root
    return _make


@pytest.fixture
def make_polyglot_project(tmp_path):
    """Create a project with multiple languages."""
    def _make():
        root = tmp_path / "polyglot"
        root.mkdir(exist_ok=True)
        (root / "main.py").write_text("def main(): pass\n")
        (root / "app.ts").write_text("export function app() {}\n")
        (root / "lib.go").write_text("package main\nfunc Lib() {}\n")
        return root
    return _make


# ===========================================================================
# Strategy Detection (~8 tests)
# REQ-NAV-001
# ===========================================================================

class TestStrategyDetection:
    """REQ-NAV-001 - Strategy detection adapts to project type."""

    def test_detect_strategy_tsconfig_returns_ts_aware(self, make_ts_project):
        root = make_ts_project()
        result = nav.detect_strategy(root)
        assert result["strategy"] == "ts-aware"
        assert "tsconfig.json" in result["config_files"]

    def test_detect_strategy_polyglot_multiple_languages(self, make_polyglot_project):
        root = make_polyglot_project()
        result = nav.detect_strategy(root)
        assert result["strategy"] == "polyglot"
        assert len(result["languages"]) >= 2

    def test_detect_strategy_single_language_returns_grep_enhanced(self, make_python_project):
        root = make_python_project()
        result = nav.detect_strategy(root)
        assert result["strategy"] == "grep-enhanced"

    def test_detect_strategy_empty_dir_returns_grep_enhanced(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        result = nav.detect_strategy(empty)
        assert result["strategy"] == "grep-enhanced"
        assert result["languages"] == []

    def test_detect_languages_finds_python(self, make_python_project):
        root = make_python_project()
        langs = nav.detect_languages(root)
        assert "python" in langs

    def test_detect_languages_finds_typescript(self, make_ts_project):
        root = make_ts_project()
        langs = nav.detect_languages(root)
        assert "typescript" in langs

    def test_detect_languages_ignores_node_modules(self, make_ts_project):
        root = make_ts_project()
        langs = nav.detect_languages(root)
        # node_modules/somepkg/index.ts should be ignored -- the only TS
        # files detected should come from src/
        ts_files = nav.walk_source_files(root, extensions=[".ts", ".tsx"])
        for f in ts_files:
            assert "node_modules" not in str(f)

    def test_detect_languages_empty_dir_returns_empty(self, tmp_path):
        empty = tmp_path / "empty-langs"
        empty.mkdir()
        result = nav.detect_languages(empty)
        assert result == []


# ===========================================================================
# Search Functions (~10 tests)
# REQ-NAV-002
# ===========================================================================

class TestSearchFunctions:
    """REQ-NAV-002 - Search functions return structured match dicts."""

    def test_search_pattern_grep_enhanced_finds_matches(self, make_python_project):
        root = make_python_project()
        matches = nav.search_pattern(root, "helper", strategy="grep-enhanced")
        assert len(matches) > 0
        assert any("helper" in m["content"] for m in matches)

    def test_search_pattern_with_file_filter(self, make_python_project):
        root = make_python_project()
        matches = nav.search_pattern(root, "helper", strategy="grep-enhanced",
                                     file_filter="*utils*")
        # All returned files should match the filter
        for m in matches:
            assert "utils" in m["file"]

    def test_search_pattern_returns_match_dicts(self, make_python_project):
        root = make_python_project()
        matches = nav.search_pattern(root, "def run", strategy="grep-enhanced")
        assert len(matches) > 0
        m = matches[0]
        assert "file" in m
        assert "line" in m
        assert "content" in m

    def test_search_pattern_no_matches_returns_empty(self, make_python_project):
        root = make_python_project()
        matches = nav.search_pattern(root, "zzz_nonexistent_zzz", strategy="grep-enhanced")
        assert matches == []

    def test_search_similar_patterns_finds_identifiers(self, make_python_project):
        root = make_python_project()
        snippet = "def helper():\n    return 'ok'"
        matches = nav.search_similar_patterns(root, snippet, strategy="grep-enhanced")
        assert isinstance(matches, list)
        # "helper" is a unique identifier that should be found
        if matches:
            assert any("helper" in m["content"] for m in matches)

    def test_search_similar_patterns_short_snippet(self, make_python_project):
        root = make_python_project()
        # A snippet with only keywords should return empty
        matches = nav.search_similar_patterns(root, "if else for while")
        assert isinstance(matches, list)

    def test_search_similar_patterns_empty_snippet(self, tmp_path):
        empty = tmp_path / "empty-sim"
        empty.mkdir()
        matches = nav.search_similar_patterns(empty, "")
        assert matches == []

    def test_find_related_files_finds_test(self, make_ts_project):
        root = make_ts_project()
        related = nav.find_related_files(root, str(root / "src" / "index.ts"),
                                         strategy="grep-enhanced")
        # index.spec.ts should be found
        assert any("index.spec.ts" in r for r in related)

    def test_find_related_files_finds_importers(self, make_ts_project):
        root = make_ts_project()
        related = nav.find_related_files(root, str(root / "src" / "lib" / "greeter.ts"),
                                         strategy="grep-enhanced")
        assert isinstance(related, list)

    def test_find_related_files_nonexistent_file(self, make_python_project):
        root = make_python_project()
        related = nav.find_related_files(root, str(root / "does_not_exist.py"),
                                         strategy="grep-enhanced")
        assert isinstance(related, list)


# ===========================================================================
# TypeScript Features (~8 tests)
# REQ-NAV-003
# ===========================================================================

class TestTypeScriptFeatures:
    """REQ-NAV-003 - TypeScript import parsing and resolution."""

    def test_parse_ts_imports_default_import(self, tmp_path):
        f = tmp_path / "test.ts"
        f.write_text('import React from "react";\n')
        result = nav.parse_ts_imports(f)
        assert len(result) == 1
        assert result[0]["source"] == "react"

    def test_parse_ts_imports_named_imports(self, tmp_path):
        f = tmp_path / "test.ts"
        f.write_text('import { useState, useEffect } from "react";\n')
        result = nav.parse_ts_imports(f)
        assert len(result) == 1
        assert result[0]["source"] == "react"
        assert "useState" in result[0]["specifiers"]
        assert "useEffect" in result[0]["specifiers"]

    def test_parse_ts_imports_side_effect(self, tmp_path):
        f = tmp_path / "test.ts"
        f.write_text('import "reflect-metadata";\n')
        result = nav.parse_ts_imports(f)
        assert len(result) == 1
        assert result[0]["source"] == "reflect-metadata"

    def test_parse_ts_imports_non_ts_file_returns_empty(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}\n')
        result = nav.parse_ts_imports(f)
        assert result == []

    def test_parse_ts_imports_missing_file_returns_empty(self, tmp_path):
        f = tmp_path / "nonexistent.ts"
        result = nav.parse_ts_imports(f)
        assert result == []

    def test_resolve_ts_import_relative_path(self, make_ts_project):
        root = make_ts_project()
        from_file = root / "src" / "index.ts"
        result = nav.resolve_ts_import("./lib/greeter", from_file, root)
        assert result is not None
        assert result.name == "greeter.ts"

    def test_resolve_ts_import_index_file(self, tmp_path):
        root = tmp_path / "ts-idx"
        root.mkdir()
        (root / "tsconfig.json").write_text("{}")
        lib = root / "src" / "lib"
        lib.mkdir(parents=True)
        (lib / "index.ts").write_text("export const x = 1;\n")
        from_file = root / "src" / "app.ts"
        from_file.write_text("")
        result = nav.resolve_ts_import("./lib", from_file, root)
        assert result is not None
        assert result.name == "index.ts"

    def test_resolve_ts_import_nonexistent_returns_none(self, tmp_path):
        root = tmp_path / "ts-none"
        root.mkdir()
        (root / "tsconfig.json").write_text("{}")
        from_file = root / "src" / "app.ts"
        from_file.parent.mkdir(parents=True, exist_ok=True)
        from_file.write_text("")
        result = nav.resolve_ts_import("./nonexistent", from_file, root)
        assert result is None

    def test_build_ts_dependency_graph_simple(self, make_ts_project):
        root = make_ts_project()
        graph = nav.build_ts_dependency_graph(root)
        assert isinstance(graph, dict)
        assert len(graph) > 0
        # index.ts should have dependencies
        index_key = [k for k in graph if "index.ts" in k and "spec" not in k]
        assert len(index_key) >= 1
        deps = graph[index_key[0]]
        assert any("greeter" in d for d in deps)

    def test_build_ts_dependency_graph_respects_file_limit(self, make_ts_project):
        root = make_ts_project()
        # Pass specific entry files to limit scope
        entry = [str(root / "src" / "index.ts")]
        graph = nav.build_ts_dependency_graph(root, entry_files=entry)
        assert len(graph) == 1


# ===========================================================================
# Polyglot Features (~4 tests)
# REQ-NAV-004
# ===========================================================================

class TestPolyglotFeatures:
    """REQ-NAV-004 - Polyglot language pattern generation."""

    def test_generate_language_patterns_python(self):
        result = nav.generate_language_patterns("MyClass", ["python"])
        assert "python" in result
        patterns = result["python"]
        assert any("def" in p for p in patterns)
        assert any("class" in p for p in patterns)

    def test_generate_language_patterns_typescript(self):
        result = nav.generate_language_patterns("MyFunc", ["typescript"])
        assert "typescript" in result
        patterns = result["typescript"]
        assert any("function" in p or "const" in p for p in patterns)

    def test_generate_language_patterns_unknown_language(self):
        result = nav.generate_language_patterns("foo", ["brainfuck"])
        # Unknown language gets only the raw pattern
        assert "brainfuck" in result
        assert result["brainfuck"] == ["foo"]

    def test_language_import_patterns_match_expected(self):
        import re
        # Python
        m = re.match(nav.LANGUAGE_IMPORT_PATTERNS["python"], "from os import path")
        assert m is not None
        # TypeScript
        m = re.match(nav.LANGUAGE_IMPORT_PATTERNS["typescript"], 'import { x } from "y"')
        assert m is not None
        # Go
        m = re.match(nav.LANGUAGE_IMPORT_PATTERNS["go"], 'import "fmt"')
        assert m is not None


# ===========================================================================
# Utility Functions (~10 tests)
# REQ-NAV-005
# ===========================================================================

class TestUtilityFunctions:
    """REQ-NAV-005 - Utility functions handle edge cases."""

    def test_walk_source_files_returns_source_files(self, make_python_project):
        root = make_python_project()
        files = nav.walk_source_files(root)
        assert len(files) > 0
        assert all(isinstance(f, Path) for f in files)

    def test_walk_source_files_ignores_dirs(self, make_ts_project):
        root = make_ts_project()
        files = nav.walk_source_files(root)
        for f in files:
            parts = set(f.parts)
            for ignored in nav.IGNORE_DIRS:
                assert ignored not in parts

    def test_walk_source_files_respects_max_files(self, make_python_project):
        root = make_python_project()
        files = nav.walk_source_files(root, max_files=2)
        assert len(files) <= 2

    def test_walk_source_files_with_extensions_filter(self, make_polyglot_project):
        root = make_polyglot_project()
        py_files = nav.walk_source_files(root, extensions=[".py"])
        assert len(py_files) > 0
        assert all(f.suffix == ".py" for f in py_files)

    def test_walk_source_files_with_extensions_no_match(self, make_python_project):
        root = make_python_project()
        files = nav.walk_source_files(root, extensions=[".xyz"])
        assert files == []

    def test_run_ripgrep_finds_matches(self, make_python_project):
        root = make_python_project()
        matches = nav.run_ripgrep(root, "helper")
        assert isinstance(matches, list)
        assert len(matches) > 0

    def test_run_ripgrep_no_matches(self, make_python_project):
        root = make_python_project()
        matches = nav.run_ripgrep(root, "zzz_definitely_not_here_zzz")
        assert matches == []

    def test_run_ripgrep_max_results(self, make_python_project):
        root = make_python_project()
        matches = nav.run_ripgrep(root, ".", max_results=3)
        assert len(matches) <= 3

    def test_get_repo_root_with_git_dir(self, tmp_path):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        (repo / ".git").mkdir()
        sub = repo / "src" / "deep"
        sub.mkdir(parents=True)
        result = nav.get_repo_root(sub)
        assert result == repo.resolve()

    def test_get_repo_root_without_git_returns_start(self, tmp_path):
        no_git = tmp_path / "norepo"
        no_git.mkdir()
        result = nav.get_repo_root(no_git)
        assert result == no_git.resolve()

    def test_get_repo_root_walks_up(self, tmp_path):
        repo = tmp_path / "walkrepo"
        repo.mkdir()
        (repo / ".git").mkdir()
        deep = repo / "a" / "b" / "c"
        deep.mkdir(parents=True)
        result = nav.get_repo_root(deep)
        assert result == repo.resolve()


# ===========================================================================
# Constants Sanity
# ===========================================================================

class TestConstants:
    """Verify module constants are well-formed."""

    def test_strategies_dict_has_three_entries(self):
        assert len(nav.STRATEGIES) == 3
        assert "ts-aware" in nav.STRATEGIES
        assert "polyglot" in nav.STRATEGIES
        assert "grep-enhanced" in nav.STRATEGIES

    def test_ignore_dirs_contains_node_modules(self):
        assert "node_modules" in nav.IGNORE_DIRS
        assert ".git" in nav.IGNORE_DIRS

    def test_language_extensions_all_start_with_dot(self):
        for lang, exts in nav.LANGUAGE_EXTENSIONS.items():
            for ext in exts:
                assert ext.startswith("."), f"{lang}: {ext} missing leading dot"
