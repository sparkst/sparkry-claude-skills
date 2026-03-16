#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""Tests for qralph-git.py — silent git automation for QRALPH pipeline."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

# ─── Import hyphenated module via importlib ──────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent))

_mod_path = Path(__file__).parent / "qralph-git.py"
_mod_spec = importlib.util.spec_from_file_location("qralph_git", _mod_path)
qralph_git = importlib.util.module_from_spec(_mod_spec)
_mod_spec.loader.exec_module(qralph_git)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def git_repo(tmp_path):
    """Create a real git repo in tmp_path with an initial commit."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "t@t.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "t@t.com"
    run = lambda args: subprocess.run(
        args, cwd=str(tmp_path), capture_output=True, check=True, env=env,
    )
    run(["git", "init"])
    run(["git", "config", "user.name", "Test"])
    run(["git", "config", "user.email", "t@t.com"])
    # Create initial commit so HEAD exists
    readme = tmp_path / "README.md"
    readme.write_text("init")
    run(["git", "add", "README.md"])
    run(["git", "commit", "-m", "initial"])
    return tmp_path


# ─── _sanitize_branch_name ───────────────────────────────────────────────────


class TestSanitizeBranchName:
    """REQ-GIT-001 — Branch name sanitization."""

    def test_spaces_replaced(self):
        """REQ-GIT-001 — spaces become dashes."""
        assert qralph_git._sanitize_branch_name("hello world") == "hello-world"

    def test_parens_replaced(self):
        """REQ-GIT-001 — parentheses become dashes."""
        assert qralph_git._sanitize_branch_name("foo(bar)baz") == "foo-bar-baz"

    def test_multiple_dashes_collapsed(self):
        """REQ-GIT-001 — multiple consecutive dashes collapse to one."""
        assert qralph_git._sanitize_branch_name("a---b") == "a-b"

    def test_slashes_preserved(self):
        """REQ-GIT-001 — slashes are valid in branch names."""
        assert qralph_git._sanitize_branch_name("qralph/my-branch") == "qralph/my-branch"

    def test_underscores_preserved(self):
        """REQ-GIT-001 — underscores are valid in branch names."""
        assert qralph_git._sanitize_branch_name("foo_bar") == "foo_bar"

    def test_trailing_leading_dashes_stripped(self):
        """REQ-GIT-001 — leading/trailing dashes stripped."""
        result = qralph_git._sanitize_branch_name("--hello--")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_special_characters(self):
        """REQ-GIT-001 — special characters removed."""
        result = qralph_git._sanitize_branch_name("feat: add $tuff! @home")
        assert "$" not in result
        assert "!" not in result
        assert "@" not in result
        assert ":" not in result


# ─── _run_git ────────────────────────────────────────────────────────────────


class TestRunGit:
    """REQ-GIT-002 — Git subprocess runner."""

    def test_returns_tuple(self, git_repo):
        """REQ-GIT-002 — returns (returncode, output) tuple."""
        rc, out = qralph_git._run_git(["status"], cwd=str(git_repo))
        assert rc == 0
        assert isinstance(out, str)

    def test_captures_output(self, git_repo):
        """REQ-GIT-002 — captures stdout from git."""
        rc, out = qralph_git._run_git(["branch", "--show-current"], cwd=str(git_repo))
        assert rc == 0
        # Should be on main or master
        assert out.strip() in ("main", "master")

    def test_nonzero_returncode(self, git_repo):
        """REQ-GIT-002 — returns nonzero rc for invalid commands."""
        rc, out = qralph_git._run_git(["log", "--oneline", "nonexistent-ref"], cwd=str(git_repo))
        assert rc != 0

    def test_file_not_found(self):
        """REQ-GIT-002 — handles missing git binary gracefully."""
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            rc, out = qralph_git._run_git(["status"], cwd="/tmp")
            assert rc == -1
            assert "not found" in out.lower() or "FileNotFoundError" in out

    def test_timeout_expired(self):
        """REQ-GIT-002 — handles timeout gracefully."""
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=30)):
            rc, out = qralph_git._run_git(["status"], cwd="/tmp")
            assert rc == -1
            assert "timeout" in out.lower()

    def test_shell_false(self, git_repo):
        """REQ-GIT-002 — subprocess uses shell=False."""
        with mock.patch("subprocess.run", wraps=subprocess.run) as spy:
            qralph_git._run_git(["status"], cwd=str(git_repo))
            call_kwargs = spy.call_args
            # shell should not be True (either absent or False)
            assert call_kwargs.kwargs.get("shell", False) is False


# ─── is_git_repo ─────────────────────────────────────────────────────────────


class TestIsGitRepo:
    """REQ-GIT-010 — Detect git repository."""

    def test_valid_repo(self, git_repo):
        """REQ-GIT-010 — returns True for a valid git repo."""
        assert qralph_git.is_git_repo(str(git_repo)) is True

    def test_non_repo(self, tmp_path):
        """REQ-GIT-010 — returns False for a non-repo directory."""
        assert qralph_git.is_git_repo(str(tmp_path)) is False

    def test_returns_bool(self, git_repo):
        """REQ-GIT-010 — return type is bool."""
        result = qralph_git.is_git_repo(str(git_repo))
        assert isinstance(result, bool)


# ─── get_default_branch ─────────────────────────────────────────────────────


class TestGetDefaultBranch:
    """REQ-GIT-020 — Detect default branch name."""

    def test_returns_string(self, git_repo):
        """REQ-GIT-020 — returns a string."""
        result = qralph_git.get_default_branch(str(git_repo))
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_to_main_or_master(self, git_repo):
        """REQ-GIT-020 — without remote, falls back to main or master."""
        result = qralph_git.get_default_branch(str(git_repo))
        assert result in ("main", "master")

    def test_main_preferred_when_exists(self, git_repo):
        """REQ-GIT-020 — if 'main' branch exists, prefer it."""
        # Rename current branch to main if not already
        rc, current = qralph_git._run_git(["branch", "--show-current"], cwd=str(git_repo))
        if current.strip() != "main":
            subprocess.run(
                ["git", "branch", "-m", current.strip(), "main"],
                cwd=str(git_repo), capture_output=True,
            )
        result = qralph_git.get_default_branch(str(git_repo))
        assert result == "main"

    def test_master_fallback(self, git_repo):
        """REQ-GIT-020 — if only 'master' exists, returns master."""
        rc, current = qralph_git._run_git(["branch", "--show-current"], cwd=str(git_repo))
        if current.strip() != "master":
            subprocess.run(
                ["git", "branch", "-m", current.strip(), "master"],
                cwd=str(git_repo), capture_output=True,
            )
        result = qralph_git.get_default_branch(str(git_repo))
        assert result == "master"


# ─── create_branch ───────────────────────────────────────────────────────────


class TestCreateBranch:
    """REQ-GIT-030 — Branch creation for projects."""

    def test_creates_branch(self, git_repo):
        """REQ-GIT-030 — creates a new branch with qralph/ prefix."""
        result = qralph_git.create_branch("042-secureclaw-app", cwd=str(git_repo))
        assert result["success"] is True
        assert result["branch"] == "qralph/042-secureclaw-app"
        assert result["error"] == ""

    def test_switches_to_existing_branch(self, git_repo):
        """REQ-GIT-030 — if branch exists, switches to it."""
        qralph_git.create_branch("042-secureclaw-app", cwd=str(git_repo))
        # Call again — should switch, not fail
        result = qralph_git.create_branch("042-secureclaw-app", cwd=str(git_repo))
        assert result["success"] is True
        assert result["branch"] == "qralph/042-secureclaw-app"

    def test_sanitizes_project_id(self, git_repo):
        """REQ-GIT-030 — sanitizes special chars in project ID."""
        result = qralph_git.create_branch(
            "043-our secureclaw (findings) report", cwd=str(git_repo)
        )
        assert result["success"] is True
        assert " " not in result["branch"]
        assert "(" not in result["branch"]
        assert ")" not in result["branch"]

    def test_returns_dict_with_required_keys(self, git_repo):
        """REQ-GIT-030 — returns dict with success, branch, error."""
        result = qralph_git.create_branch("test-proj", cwd=str(git_repo))
        assert "success" in result
        assert "branch" in result
        assert "error" in result

    def test_actually_on_new_branch(self, git_repo):
        """REQ-GIT-030 — after create, HEAD is on the new branch."""
        qralph_git.create_branch("050-new-feature", cwd=str(git_repo))
        rc, current = qralph_git._run_git(["branch", "--show-current"], cwd=str(git_repo))
        assert current.strip() == "qralph/050-new-feature"

    def test_error_on_non_repo(self, tmp_path):
        """REQ-GIT-030 — returns error if not a git repo."""
        result = qralph_git.create_branch("test", cwd=str(tmp_path))
        assert result["success"] is False
        assert result["error"] != ""


# ─── commit_changes ──────────────────────────────────────────────────────────


class TestCommitChanges:
    """REQ-GIT-040 — Commit staged changes."""

    def test_commits_new_file(self, git_repo):
        """REQ-GIT-040 — stages and commits a new file in target_dir."""
        target = git_repo / "projects" / "042"
        target.mkdir(parents=True)
        (target / "PLAN.md").write_text("# Plan")
        result = qralph_git.commit_changes(
            target_dir=str(target),
            message="add plan",
            cwd=str(git_repo),
        )
        assert result["success"] is True
        assert result["committed"] is True
        assert result["error"] == ""

    def test_nothing_to_commit(self, git_repo):
        """REQ-GIT-040 — committed=False when nothing changed (not an error)."""
        result = qralph_git.commit_changes(
            target_dir=str(git_repo),
            message="no changes",
            cwd=str(git_repo),
        )
        assert result["success"] is True
        assert result["committed"] is False

    def test_only_stages_target_dir(self, git_repo):
        """REQ-GIT-040 — only stages files in target_dir, not unrelated files."""
        # Create file in target dir
        target = git_repo / "projects" / "042"
        target.mkdir(parents=True)
        (target / "output.md").write_text("results")
        # Create file OUTSIDE target dir
        (git_repo / "unrelated.txt").write_text("should not be staged")

        qralph_git.commit_changes(
            target_dir=str(target),
            message="scoped commit",
            cwd=str(git_repo),
        )

        # Check that unrelated.txt is still untracked
        rc, out = qralph_git._run_git(["status", "--porcelain"], cwd=str(git_repo))
        # unrelated.txt should appear as untracked (??)
        assert "?? unrelated.txt" in out

    def test_returns_dict_with_required_keys(self, git_repo):
        """REQ-GIT-040 — returns dict with success, committed, error."""
        result = qralph_git.commit_changes(
            target_dir=str(git_repo),
            message="test",
            cwd=str(git_repo),
        )
        assert "success" in result
        assert "committed" in result
        assert "error" in result

    def test_commits_modified_file(self, git_repo):
        """REQ-GIT-040 — commits modifications to existing tracked files."""
        target = git_repo / "projects"
        target.mkdir(parents=True)
        f = target / "data.txt"
        f.write_text("v1")
        # First commit
        qralph_git.commit_changes(str(target), "v1", cwd=str(git_repo))
        # Modify
        f.write_text("v2")
        result = qralph_git.commit_changes(str(target), "v2", cwd=str(git_repo))
        assert result["success"] is True
        assert result["committed"] is True


# ─── push_and_create_pr ─────────────────────────────────────────────────────


class TestPushAndCreatePr:
    """REQ-GIT-050 — Push branch and create pull request."""

    def test_success_path(self):
        """REQ-GIT-050 — happy path: push succeeds, PR created."""
        with mock.patch.object(
            qralph_git, "_run_git", return_value=(0, "")
        ), mock.patch.object(
            qralph_git, "_run_gh",
            return_value=(0, "https://github.com/org/repo/pull/42\n"),
        ):
            result = qralph_git.push_and_create_pr(
                branch="qralph/042-test",
                project_id="042-test",
                request="Fix the widget",
                cwd="/fake",
            )
        assert result["success"] is True
        assert "pull/42" in result["pr_url"]

    def test_gh_not_installed(self):
        """REQ-GIT-050 — gh missing returns success with manual-PR message."""
        with mock.patch.object(
            qralph_git, "_run_git", return_value=(0, "")
        ), mock.patch.object(
            qralph_git, "_run_gh", side_effect=FileNotFoundError("gh not found"),
        ):
            result = qralph_git.push_and_create_pr(
                branch="qralph/042-test",
                project_id="042-test",
                request="Fix widget",
                cwd="/fake",
            )
        assert result["success"] is True
        assert "manual" in result["message"].lower() or "manually" in result["message"].lower()

    def test_push_failure(self):
        """REQ-GIT-050 — push failure returns success=False."""
        with mock.patch.object(
            qralph_git, "_run_git", return_value=(128, "fatal: no remote")
        ):
            result = qralph_git.push_and_create_pr(
                branch="qralph/042-test",
                project_id="042-test",
                request="Fix widget",
                cwd="/fake",
            )
        assert result["success"] is False
        assert result["error"] != ""

    def test_pr_already_exists(self):
        """REQ-GIT-050 — if PR already exists, retrieves its URL."""
        gh_call_count = {"n": 0}

        def fake_run_gh(args, cwd, timeout=60):
            idx = gh_call_count["n"]
            gh_call_count["n"] += 1
            if idx == 0:
                return (1, "already exists")  # gh pr create fails
            if idx == 1:
                return (0, "https://github.com/org/repo/pull/99\n")  # gh pr view
            return (0, "")

        with mock.patch.object(
            qralph_git, "_run_git", return_value=(0, "")
        ), mock.patch.object(
            qralph_git, "_run_gh", side_effect=fake_run_gh,
        ):
            result = qralph_git.push_and_create_pr(
                branch="qralph/042-test",
                project_id="042-test",
                request="Fix widget",
                cwd="/fake",
            )
        assert result["success"] is True
        assert "pull/99" in result["pr_url"]

    def test_returns_dict_with_required_keys(self):
        """REQ-GIT-050 — returns dict with success, pr_url, error, message."""
        with mock.patch.object(
            qralph_git, "_run_git", return_value=(0, "")
        ), mock.patch.object(
            qralph_git, "_run_gh", return_value=(0, "https://github.com/x/y/pull/1\n"),
        ):
            result = qralph_git.push_and_create_pr(
                branch="qralph/test",
                project_id="test",
                request="test",
                cwd="/fake",
            )
        assert "success" in result
        assert "pr_url" in result
        assert "error" in result
        assert "message" in result

    def test_version_in_pr_body(self):
        """REQ-GIT-050 — version string appears in PR body when provided."""
        captured_gh_args = []

        def fake_run_gh(args, cwd, timeout=60):
            captured_gh_args.append(args)
            return (0, "https://github.com/org/repo/pull/1\n")

        with mock.patch.object(
            qralph_git, "_run_git", return_value=(0, "")
        ), mock.patch.object(
            qralph_git, "_run_gh", side_effect=fake_run_gh,
        ):
            qralph_git.push_and_create_pr(
                branch="qralph/042-test",
                project_id="042-test",
                request="Fix widget",
                cwd="/fake",
                version="6.8.0",
            )
        # The gh pr create call should contain the version somewhere in args
        assert len(captured_gh_args) > 0
        args_str = " ".join(str(a) for a in captured_gh_args[0])
        assert "6.8.0" in args_str


# ─── Module-level checks ────────────────────────────────────────────────────


class TestModuleMetadata:
    """REQ-GIT-000 — Module structure and metadata."""

    def test_module_docstring(self):
        """REQ-GIT-000 — module has correct docstring."""
        assert "Silent git automation" in (qralph_git.__doc__ or "")

    def test_all_public_functions_exist(self):
        """REQ-GIT-000 — all required public functions are defined."""
        assert callable(getattr(qralph_git, "is_git_repo", None))
        assert callable(getattr(qralph_git, "get_default_branch", None))
        assert callable(getattr(qralph_git, "create_branch", None))
        assert callable(getattr(qralph_git, "commit_changes", None))
        assert callable(getattr(qralph_git, "push_and_create_pr", None))

    def test_helper_functions_exist(self):
        """REQ-GIT-000 — helper functions are defined."""
        assert callable(getattr(qralph_git, "_run_git", None))
        assert callable(getattr(qralph_git, "_sanitize_branch_name", None))
