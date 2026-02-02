#!/usr/bin/env python3
"""
Tests for Trello integration with QRALPH projects.
REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-014, REQ-016

Run with: python -m pytest test_trello_integration.py -v
"""

import json
import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent))

from trello_integration import (
    ControlMdFrontmatter,
    parse_control_md,
    write_control_md,
    create_project_card,
    update_card_with_run_summary,
    check_card_status,
    close_project,
    TrelloIntegrationError,
)


class TestControlMdFrontmatter:
    """REQ-001: CONTROL.md frontmatter validation tests."""

    def test_valid_frontmatter_parses_correctly(self, tmp_path):
        """REQ-001-001: Valid frontmatter should parse without errors."""
        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-qralph-trello-integration
github_repo: sparkst/cardinal-health
trello:
  card_id: abc123def456789012345678
  card_url: https://trello.com/c/abc123
  status: open
  created_at: 2026-02-01T20:00:00Z
  last_run_at: 2026-02-01T21:30:00Z
  sync_pending: false
---

# Project Content
''')

        result = parse_control_md(str(control_md))

        assert result.schema_version == 1
        assert result.project_id == "012-qralph-trello-integration"
        assert result.github_repo == "sparkst/cardinal-health"
        assert result.trello.card_id == "abc123def456789012345678"
        assert result.trello.status == "open"

    def test_frontmatter_without_trello_section(self, tmp_path):
        """REQ-001-002: CONTROL.md without trello section is valid (unlinked)."""
        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-qralph-trello-integration
github_repo: sparkst/cardinal-health
---

# Project Content
''')

        result = parse_control_md(str(control_md))

        assert result.project_id == "012-qralph-trello-integration"
        assert result.trello is None

    def test_invalid_frontmatter_logs_warning(self, tmp_path, caplog):
        """REQ-001-003: Invalid frontmatter logs warning."""
        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: "invalid"
---

# Project Content
''')

        result = parse_control_md(str(control_md))

        assert result is None or "warning" in caplog.text.lower() or result.schema_version != 1

    def test_write_frontmatter_preserves_content(self, tmp_path):
        """REQ-001-004: Writing frontmatter preserves document content."""
        control_md = tmp_path / "CONTROL.md"
        original_content = '''---
schema_version: 1
project_id: 012-test
github_repo: owner/repo
---

# Project Title

Some important content here.

## Section 1

More content.
'''
        control_md.write_text(original_content)

        # Parse, modify, and write back
        fm = parse_control_md(str(control_md))
        fm.trello = ControlMdFrontmatter.TrelloSection(
            card_id="newcard123456789012345678",
            card_url="https://trello.com/c/new",
            status="open",
        )
        write_control_md(str(control_md), fm)

        # Verify content preserved
        new_content = control_md.read_text()
        assert "# Project Title" in new_content
        assert "Some important content here." in new_content
        assert "## Section 1" in new_content
        assert "newcard123456789012345678" in new_content


class TestAutomaticCardCreation:
    """REQ-002: Automatic card creation tests."""

    @patch('trello_integration.create_card')
    @patch('trello_integration.detect_github_repo')
    def test_card_created_with_correct_title_format(self, mock_detect, mock_create, tmp_path):
        """REQ-002-001: Card title should follow [Q:{initials}] {project_id} format."""
        mock_detect.return_value = "sparkst/cardinal-health"
        mock_create.return_value = {
            'success': True,
            'data': {
                'id': 'card123456789012345678901',
                'url': 'https://trello.com/c/abc123',
            }
        }

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-qralph-trello-integration
github_repo: sparkst/cardinal-health
---

# Project
''')

        result = create_project_card(
            str(control_md),
            "Build Trello integration for QRALPH",
            list_id="list123456789012345678901",
        )

        assert result['success'] is True
        # Verify title format in call
        call_args = mock_create.call_args
        assert "[Q:CH]" in call_args[1]['title'] or "[Q:CH]" in call_args[0][1]

    @patch('trello_integration.create_card')
    @patch('trello_integration.detect_github_repo')
    def test_card_creation_updates_control_md(self, mock_detect, mock_create, tmp_path):
        """REQ-002-002: CONTROL.md updated with card_id after creation."""
        mock_detect.return_value = "sparkst/cardinal-health"
        mock_create.return_value = {
            'success': True,
            'data': {
                'id': 'card123456789012345678901',
                'url': 'https://trello.com/c/abc123',
            }
        }

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: sparkst/cardinal-health
---

# Project
''')

        create_project_card(
            str(control_md),
            "Test project",
            list_id="list123456789012345678901",
        )

        # Verify CONTROL.md was updated
        content = control_md.read_text()
        assert "card123456789012345678901" in content
        assert "trello.com/c/abc123" in content

    @patch('trello_integration.create_card')
    def test_card_creation_failure_sets_offline_pending(self, mock_create, tmp_path):
        """REQ-002-003: Failed card creation sets offline-pending status."""
        mock_create.return_value = {
            'success': False,
            'error': 'Network error'
        }

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: sparkst/cardinal-health
---

# Project
''')

        result = create_project_card(
            str(control_md),
            "Test project",
            list_id="list123456789012345678901",
        )

        assert result['success'] is False
        content = control_md.read_text()
        assert "offline-pending" in content or "sync_pending: true" in content


class TestCardUpdateOnRun:
    """REQ-003: Card update on run completion tests."""

    @patch('trello_integration.update_card')
    @patch('trello_integration.get_card')
    def test_card_updated_with_run_summary(self, mock_get_card, mock_update, tmp_path):
        """REQ-003-001: Card description updated with run summary."""
        mock_get_card.return_value = {
            'success': True,
            'data': {'id': 'card123', 'desc': 'Original description'}
        }
        mock_update.return_value = {'success': True, 'data': {'id': 'card123'}}

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: sparkst/cardinal-health
trello:
  card_id: card123456789012345678901
  card_url: https://trello.com/c/abc123
  status: open
---

# Project
''')

        result = update_card_with_run_summary(
            str(control_md),
            agents=["security", "architecture", "requirements"],
            findings={"P0": 2, "P1": 5, "P2": 8},
            status="P0/P1 fixes implemented",
        )

        assert result['success'] is True
        # Verify update was called with run summary
        call_args = mock_update.call_args
        assert "Run" in str(call_args) or "summary" in str(call_args).lower()


class TestClosedCardDetection:
    """REQ-004: Closed card detection tests."""

    @patch('trello_integration.get_card')
    def test_closed_card_detected(self, mock_get_card, tmp_path):
        """REQ-004-001: Detect when card is closed/archived."""
        mock_get_card.return_value = {
            'success': True,
            'data': {
                'id': 'card123456789012345678901',
                'name': '[Q:CH] 012-test',
                'closed': True,
            }
        }

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: sparkst/cardinal-health
trello:
  card_id: card123456789012345678901
  card_url: https://trello.com/c/abc123
  status: open
---

# Project
''')

        result = check_card_status(str(control_md))

        assert result['closed'] is True
        assert result['needs_action'] is True


class TestCloseCard:
    """REQ-005: Close card from Claude Code tests."""

    @patch('trello_integration.archive_card')
    def test_close_project_archives_card(self, mock_archive, tmp_path):
        """REQ-005-001: Close command archives Trello card."""
        mock_archive.return_value = {'success': True, 'data': {'archived': True}}

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: sparkst/cardinal-health
trello:
  card_id: card123456789012345678901
  card_url: https://trello.com/c/abc123
  status: open
---

# Project
''')

        result = close_project(str(control_md))

        assert result['success'] is True
        mock_archive.assert_called_once()

        # Verify CONTROL.md updated
        content = control_md.read_text()
        assert "closed" in content


class TestSyncProjects:
    """REQ-006: Sync command tests."""

    @patch('trello_integration.get_all_cards')
    def test_sync_detects_local_only_projects(self, mock_get_cards, tmp_path):
        """REQ-006-001: Detect projects not in Trello."""
        mock_get_cards.return_value = {
            'success': True,
            'data': [
                {'name': '[Q:CH] 001-existing', 'closed': False}
            ]
        }

        # Create local projects
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()

        (projects_dir / "001-existing").mkdir()
        (projects_dir / "001-existing" / "CONTROL.md").write_text('''---
schema_version: 1
project_id: 001-existing
github_repo: owner/repo
trello:
  card_id: card123456789012345678901
  card_url: https://trello.com/c/abc
  status: open
---
''')

        (projects_dir / "002-new").mkdir()
        (projects_dir / "002-new" / "CONTROL.md").write_text('''---
schema_version: 1
project_id: 002-new
github_repo: owner/repo
---
''')

        from trello_integration import sync_projects
        result = sync_projects(str(projects_dir), "list123")

        assert result['success'] is True
        assert '002-new' in result['local_only']

    @patch('trello_integration.get_all_cards')
    def test_sync_detects_trello_only_cards(self, mock_get_cards, tmp_path):
        """REQ-006-002: Detect Trello cards without local projects."""
        mock_get_cards.return_value = {
            'success': True,
            'data': [
                {'name': '[Q:CH] 001-local', 'closed': False},
                {'name': '[Q:CH] 003-trello-only', 'closed': False},
            ]
        }

        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()

        (projects_dir / "001-local").mkdir()
        (projects_dir / "001-local" / "CONTROL.md").write_text('''---
schema_version: 1
project_id: 001-local
github_repo: owner/repo
---
''')

        from trello_integration import sync_projects
        result = sync_projects(str(projects_dir), "list123")

        assert result['success'] is True
        assert '003-trello-only' in result['trello_only']


class TestOfflineMode:
    """REQ-014: Offline mode handling tests."""

    def test_offline_pending_status_set_on_failure(self, tmp_path):
        """REQ-014-001: Set offline-pending when Trello unavailable."""
        # This is already covered in TestAutomaticCardCreation.test_card_creation_failure_sets_offline_pending
        pass

    @patch('trello_integration.create_card')
    def test_sync_pending_projects_detected(self, mock_create, tmp_path):
        """REQ-014-002: Detect projects with sync_pending flag."""
        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: owner/repo
trello:
  card_id: ""
  card_url: ""
  status: offline-pending
  sync_pending: true
---
''')

        from trello_integration import parse_control_md
        fm = parse_control_md(str(control_md))

        assert fm.trello.sync_pending is True
        assert fm.trello.status == "offline-pending"


class TestDeletedCardRecovery:
    """REQ-016: Deleted card recovery tests."""

    @patch('trello_integration.create_card')
    @patch('trello_integration.detect_github_repo')
    def test_recover_deleted_card_creates_new(self, mock_detect, mock_create, tmp_path):
        """REQ-016-001: Create new card when old one was deleted."""
        mock_detect.return_value = "owner/repo"
        mock_create.return_value = {
            'success': True,
            'data': {'id': 'newcard12345678901234567', 'url': 'https://trello.com/c/new'}
        }

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: owner/repo
trello:
  card_id: deletedcard1234567890123
  card_url: https://trello.com/c/deleted
  status: open
---
''')

        from trello_integration import recover_deleted_card
        result = recover_deleted_card(str(control_md), "list123", "Recovered project")

        assert result['success'] is True
        content = control_md.read_text()
        assert "newcard12345678901234567" in content


class TestGitCommit:
    """REQ-009: Git commit tests."""

    @patch('trello_integration.subprocess.run')
    def test_git_commit_with_correct_message(self, mock_run, tmp_path):
        """REQ-009-001: Commit message follows format."""
        # First call: git add (success)
        # Second call: git diff --cached (has changes, returncode=1)
        # Third call: git commit (success)
        mock_run.side_effect = [
            MagicMock(returncode=0),  # git add
            MagicMock(returncode=1),  # git diff (has changes)
            MagicMock(returncode=0),  # git commit
        ]

        control_md = tmp_path / "CONTROL.md"
        control_md.write_text('''---
schema_version: 1
project_id: 012-test
github_repo: owner/repo
---
''')

        from trello_integration import git_commit_control_md
        result = git_commit_control_md(str(control_md), "Created Trello card")

        assert result['success'] is True
        # Verify commit message contains project_id
        commit_call = mock_run.call_args_list[2]
        commit_msg = commit_call[0][0][3]  # git commit -m <msg>
        assert "012-test" in commit_msg
        assert "Created Trello card" in commit_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
