#!/usr/bin/env python3
"""
Tests for GitHub repo detection.
REQ-012: GitHub Repo Context

Run with: python -m pytest test_github_repo.py -v
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from github_repo import (
    parse_github_url,
    get_repo_from_origin,
    get_repo_from_any_remote,
    detect_github_repo,
)


class TestParseGitHubUrl:
    """REQ-012-001: Parse various GitHub URL formats."""

    def test_parse_ssh_url(self):
        """REQ-012-001: Parse SSH URL format."""
        result = parse_github_url("git@github.com:owner/repo.git")
        assert result == "owner/repo"

    def test_parse_ssh_url_without_git_suffix(self):
        """REQ-012-001: Parse SSH URL without .git suffix."""
        result = parse_github_url("git@github.com:owner/repo")
        assert result == "owner/repo"

    def test_parse_https_url_with_git_suffix(self):
        """REQ-012-001: Parse HTTPS URL with .git suffix."""
        result = parse_github_url("https://github.com/owner/repo.git")
        assert result == "owner/repo"

    def test_parse_https_url_without_suffix(self):
        """REQ-012-001: Parse HTTPS URL without .git suffix."""
        result = parse_github_url("https://github.com/owner/repo")
        assert result == "owner/repo"

    def test_parse_handles_hyphenated_names(self):
        """REQ-012-001: Parse repo names with hyphens."""
        result = parse_github_url("git@github.com:sparkst/cardinal-health.git")
        assert result == "sparkst/cardinal-health"

    def test_parse_handles_underscores(self):
        """REQ-012-001: Parse repo names with underscores."""
        result = parse_github_url("https://github.com/org/my_repo.git")
        assert result == "org/my_repo"

    def test_parse_returns_none_for_invalid_url(self):
        """REQ-012-001: Return None for non-GitHub URLs."""
        result = parse_github_url("https://gitlab.com/owner/repo.git")
        assert result is None

    def test_parse_returns_none_for_empty_string(self):
        """REQ-012-001: Return None for empty string."""
        result = parse_github_url("")
        assert result is None


class TestGetRepoFromOrigin:
    """REQ-012-002: Get repo from origin remote."""

    @patch('github_repo.run_git_command')
    def test_get_from_origin_success(self, mock_git):
        """REQ-012-002: Get repo from origin remote URL."""
        mock_git.return_value = "git@github.com:sparkst/cardinal-health.git"

        result = get_repo_from_origin()

        assert result == "sparkst/cardinal-health"
        mock_git.assert_called_once_with(["git", "remote", "get-url", "origin"])

    @patch('github_repo.run_git_command')
    def test_get_from_origin_fails_gracefully(self, mock_git):
        """REQ-012-002: Return None when origin doesn't exist."""
        mock_git.return_value = None

        result = get_repo_from_origin()

        assert result is None


class TestGetRepoFromAnyRemote:
    """REQ-012-003: Fallback to any available remote."""

    @patch('github_repo.run_git_command')
    def test_get_from_first_remote(self, mock_git):
        """REQ-012-003: Get repo from first available remote."""
        def side_effect(cmd):
            if cmd == ["git", "remote"]:
                return "upstream\norigin\nfork"
            elif cmd == ["git", "remote", "get-url", "upstream"]:
                return "git@github.com:org/project.git"
            return None

        mock_git.side_effect = side_effect

        result = get_repo_from_any_remote()

        assert result == "org/project"

    @patch('github_repo.run_git_command')
    def test_get_from_any_returns_none_when_no_remotes(self, mock_git):
        """REQ-012-003: Return None when no remotes exist."""
        mock_git.return_value = ""

        result = get_repo_from_any_remote()

        assert result is None


class TestDetectGitHubRepo:
    """REQ-012-004: Full detection logic with fallback chain."""

    @patch('github_repo.get_repo_from_origin')
    @patch('github_repo.get_repo_from_any_remote')
    @patch('github_repo.load_config')
    def test_detect_uses_origin_first(self, mock_config, mock_any, mock_origin):
        """REQ-012-004: Use origin remote as first choice."""
        mock_origin.return_value = "sparkst/cardinal-health"

        result = detect_github_repo()

        assert result == "sparkst/cardinal-health"
        mock_origin.assert_called_once()
        mock_any.assert_not_called()
        mock_config.assert_not_called()

    @patch('github_repo.get_repo_from_origin')
    @patch('github_repo.get_repo_from_any_remote')
    @patch('github_repo.load_config')
    def test_detect_falls_back_to_any_remote(self, mock_config, mock_any, mock_origin):
        """REQ-012-004: Fall back to any remote if origin fails."""
        mock_origin.return_value = None
        mock_any.return_value = "org/other-repo"

        result = detect_github_repo()

        assert result == "org/other-repo"
        mock_origin.assert_called_once()
        mock_any.assert_called_once()
        mock_config.assert_not_called()

    @patch('github_repo.get_repo_from_origin')
    @patch('github_repo.get_repo_from_any_remote')
    @patch('github_repo.load_config')
    def test_detect_falls_back_to_config(self, mock_config, mock_any, mock_origin):
        """REQ-012-004: Fall back to config if no remotes work."""
        mock_origin.return_value = None
        mock_any.return_value = None
        mock_config.return_value = {"github_repo": "config/default-repo"}

        result = detect_github_repo()

        assert result == "config/default-repo"
        mock_config.assert_called_once()

    @patch('github_repo.get_repo_from_origin')
    @patch('github_repo.get_repo_from_any_remote')
    @patch('github_repo.load_config')
    def test_detect_returns_none_when_all_fail(self, mock_config, mock_any, mock_origin):
        """REQ-012-004: Return None when all methods fail."""
        mock_origin.return_value = None
        mock_any.return_value = None
        mock_config.side_effect = FileNotFoundError("No config")

        result = detect_github_repo()

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
