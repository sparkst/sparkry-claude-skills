#!/usr/bin/env python3
"""
Tests for QRALPH orchestrator Trello integration.
REQ-011: QRALPH Orchestrator Integration

Run with: python -m pytest test_qralph_orchestrator.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent))

from qralph_trello_orchestrator import (
    QralphTrelloOrchestrator,
    handle_new_project,
    handle_resume_project,
    handle_project_status,
    handle_close_project,
    handle_sync,
    handle_help,
)


class TestOrchestratorNew:
    """REQ-011: QRALPH new project with Trello integration."""

    @patch('qralph_trello_orchestrator.create_project_card')
    @patch('qralph_trello_orchestrator.load_config')
    def test_new_project_creates_trello_card(self, mock_config, mock_create_card, tmp_path):
        """REQ-011-001: New project creates Trello card."""
        mock_config.return_value = {
            'list_id': 'list123456789012345678901',
            'board_id': 'board12345678901234567890',
            'github_repo': 'owner/repo',
        }
        mock_create_card.return_value = {
            'success': True,
            'data': {'id': 'card123', 'url': 'https://trello.com/c/abc'}
        }

        projects_dir = tmp_path / ".qralph" / "projects"
        projects_dir.mkdir(parents=True)

        result = handle_new_project(
            request="Build a new feature",
            projects_dir=str(projects_dir),
        )

        assert result['success'] is True
        mock_create_card.assert_called_once()


class TestOrchestratorResume:
    """REQ-011: QRALPH resume with closed card detection."""

    @patch('qralph_trello_orchestrator.check_card_status')
    def test_resume_detects_closed_card(self, mock_check_status, tmp_path):
        """REQ-011-002: Resume detects if card was closed."""
        mock_check_status.return_value = {
            'success': True,
            'closed': True,
            'needs_action': True,
            'message': 'Project was closed',
        }

        projects_dir = tmp_path / ".qralph" / "projects"
        project_dir = projects_dir / "012-test"
        project_dir.mkdir(parents=True)
        (project_dir / "CONTROL.md").write_text('''---
schema_version: 1
project_id: 012-test
github_repo: owner/repo
trello:
  card_id: card123456789012345678901
  card_url: https://trello.com/c/abc
  status: open
---
''')

        result = handle_resume_project(
            project_id="012-test",
            projects_dir=str(projects_dir),
        )

        assert result['needs_user_action'] is True
        assert result['closed'] is True


class TestOrchestratorStatus:
    """REQ-011: QRALPH status command."""

    @patch('qralph_trello_orchestrator.check_card_status')
    def test_status_shows_trello_info(self, mock_check_status, tmp_path):
        """REQ-011-003: Status shows Trello card info."""
        mock_check_status.return_value = {
            'success': True,
            'closed': False,
            'linked': True,
            'card_data': {'name': '[Q:CH] 012-test', 'url': 'https://trello.com/c/abc'}
        }

        projects_dir = tmp_path / ".qralph" / "projects"
        project_dir = projects_dir / "012-test"
        project_dir.mkdir(parents=True)
        (project_dir / "CONTROL.md").write_text('''---
schema_version: 1
project_id: 012-test
github_repo: owner/repo
trello:
  card_id: card123456789012345678901
  card_url: https://trello.com/c/abc
  status: open
---
''')

        result = handle_project_status(str(projects_dir))

        assert result['success'] is True
        assert len(result['projects']) > 0


class TestOrchestratorClose:
    """REQ-011: QRALPH close command."""

    @patch('qralph_trello_orchestrator.close_project')
    @patch('qralph_trello_orchestrator.git_commit_control_md')
    def test_close_archives_card(self, mock_commit, mock_close, tmp_path):
        """REQ-011-004: Close command archives Trello card."""
        mock_close.return_value = {'success': True}
        mock_commit.return_value = {'success': True}

        projects_dir = tmp_path / ".qralph" / "projects"
        project_dir = projects_dir / "012-test"
        project_dir.mkdir(parents=True)
        (project_dir / "CONTROL.md").write_text('''---
schema_version: 1
project_id: 012-test
github_repo: owner/repo
trello:
  card_id: card123456789012345678901
  card_url: https://trello.com/c/abc
  status: open
---
''')

        result = handle_close_project("012-test", str(projects_dir))

        assert result['success'] is True
        mock_close.assert_called_once()


class TestOrchestratorSync:
    """REQ-011: QRALPH sync command."""

    @patch('qralph_trello_orchestrator.sync_projects')
    @patch('qralph_trello_orchestrator.load_config')
    def test_sync_produces_report(self, mock_config, mock_sync, tmp_path):
        """REQ-011-005: Sync produces summary report."""
        mock_config.return_value = {'list_id': 'list123'}
        mock_sync.return_value = {
            'success': True,
            'summary': {'synced': 5, 'local_only': 2, 'trello_only': 1},
            'local_only': ['p1', 'p2'],
            'trello_only': ['p3'],
        }

        result = handle_sync(str(tmp_path / ".qralph" / "projects"))

        assert result['success'] is True
        assert result['summary']['synced'] == 5


class TestOrchestratorHelp:
    """REQ-011: QRALPH help command."""

    def test_help_shows_all_commands(self):
        """REQ-011-006: Help shows available commands."""
        result = handle_help()

        assert 'QRALPH' in result
        assert 'resume' in result
        assert 'status' in result
        assert 'sync' in result
        assert 'close' in result
        assert 'help' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
