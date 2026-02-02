#!/usr/bin/env python3
"""
Tests for standalone Trello skill CLI.
REQ-013: Standalone Trello Skill

Run with: python -m pytest test_trello_skill.py -v
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import argparse

sys.path.insert(0, str(Path(__file__).parent))

from trello_skill import (
    cmd_create,
    cmd_get,
    cmd_update,
    cmd_close,
    cmd_reopen,
    cmd_list,
    cmd_sync,
)


class TestStandaloneCreate:
    """REQ-013: Standalone create command tests."""

    @patch('trello_skill.create_card')
    @patch('trello_skill.load_config')
    def test_create_uses_config_list_id(self, mock_config, mock_create):
        """REQ-013-001: Create uses config list_id when not provided."""
        mock_config.return_value = {'list_id': 'config_list_123'}
        mock_create.return_value = {'success': True, 'data': {'id': 'card123'}}

        args = argparse.Namespace(
            title="Test Card",
            description="Test description",
            list_id=None,
            labels=None,
        )

        result = cmd_create(args)

        assert result['success'] is True
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args[1]['list_id'] == 'config_list_123'


class TestStandaloneGet:
    """REQ-013: Standalone get command tests."""

    @patch('trello_skill.get_card')
    def test_get_returns_card_data(self, mock_get):
        """REQ-013-002: Get returns card data."""
        mock_get.return_value = {
            'success': True,
            'data': {'id': 'card123', 'name': 'Test', 'closed': False}
        }

        args = argparse.Namespace(card_id='card123')
        result = cmd_get(args)

        assert result['success'] is True
        assert result['data']['id'] == 'card123'


class TestStandaloneUpdate:
    """REQ-013: Standalone update command tests."""

    @patch('trello_skill.update_card')
    @patch('trello_skill.get_card')
    def test_update_with_append(self, mock_get, mock_update):
        """REQ-013-003: Update with append flag appends to description."""
        mock_get.return_value = {
            'success': True,
            'data': {'desc': 'Original text'}
        }
        mock_update.return_value = {'success': True}

        args = argparse.Namespace(
            card_id='card123',
            title=None,
            description='Appended text',
            append=True,
        )

        result = cmd_update(args)

        assert result['success'] is True
        call_args = mock_update.call_args
        assert 'Original text' in call_args[1]['description']
        assert 'Appended text' in call_args[1]['description']


class TestStandaloneClose:
    """REQ-013: Standalone close command tests."""

    @patch('trello_skill.archive_card')
    def test_close_archives_card(self, mock_archive):
        """REQ-013-004: Close archives the card."""
        mock_archive.return_value = {'success': True, 'data': {'archived': True}}

        args = argparse.Namespace(card_id='card123')
        result = cmd_close(args)

        assert result['success'] is True
        mock_archive.assert_called_once_with('card123')


class TestStandaloneList:
    """REQ-013: Standalone list command tests."""

    @patch('trello_skill.get_all_cards')
    @patch('trello_skill.load_config')
    def test_list_uses_config_list_id(self, mock_config, mock_get_all):
        """REQ-013-005: List uses config list_id when not provided."""
        mock_config.return_value = {'list_id': 'config_list_123'}
        mock_get_all.return_value = {
            'success': True,
            'data': [{'id': 'card1'}, {'id': 'card2'}]
        }

        args = argparse.Namespace(list_id=None, include_archived=False)
        result = cmd_list(args)

        assert result['success'] is True
        assert len(result['data']) == 2


class TestStandaloneSync:
    """REQ-013: Standalone sync command tests."""

    @patch('trello_skill.sync_projects')
    @patch('trello_skill.load_config')
    def test_sync_returns_report(self, mock_config, mock_sync):
        """REQ-013-006: Sync returns summary report."""
        mock_config.return_value = {'list_id': 'list123'}
        mock_sync.return_value = {
            'success': True,
            'summary': {'synced': 5, 'local_only': 2, 'trello_only': 1}
        }

        args = argparse.Namespace(projects_dir='/test/projects')
        result = cmd_sync(args)

        assert result['success'] is True
        assert result['summary']['synced'] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
