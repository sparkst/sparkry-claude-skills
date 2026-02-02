#!/usr/bin/env python3
"""
Tests for Trello API enhancements.
REQ-008: Trello API Enhancement

Run with: python -m pytest test_trello_api.py -v
"""

import json
import os
import time
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

# Import module under test (will be enhanced)
from trello_api import (
    get_card,
    unarchive_card,
    search_cards,
    get_all_cards,
    api_request,
    sanitize_error,
    RateLimiter,
    Cache,
)


class TestGetCard:
    """REQ-008-001: get-card command tests."""

    @patch('trello_api.urlopen')
    def test_get_card_returns_card_data(self, mock_urlopen, mock_env):
        """REQ-008-001: get-card should return card data including closed status."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'id': 'card123',
            'name': 'Test Card',
            'desc': 'Description',
            'closed': False,
            'shortUrl': 'https://trello.com/c/abc123',
            'idList': 'list456',
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_card('card123')

        assert result['success'] is True
        assert result['data']['id'] == 'card123'
        assert result['data']['name'] == 'Test Card'
        assert result['data']['closed'] is False
        assert 'url' in result['data']

    @patch('trello_api.urlopen')
    def test_get_card_returns_closed_status(self, mock_urlopen, mock_env):
        """REQ-008-001: get-card should indicate when card is archived."""
        # Clear cache to avoid interference from previous test
        from trello_api import _cache
        _cache.clear()

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'id': 'card456',
            'name': 'Archived Card',
            'closed': True,
            'shortUrl': 'https://trello.com/c/abc456',
            'idList': 'list456',
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_card('card456')

        assert result['success'] is True
        assert result['data']['closed'] is True


class TestUnarchiveCard:
    """REQ-008-002: unarchive-card command tests."""

    @patch('trello_api.urlopen')
    def test_unarchive_card_reopens_card(self, mock_urlopen, mock_env):
        """REQ-008-002: unarchive-card should reopen archived card."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'id': 'card123',
            'name': 'Reopened Card',
            'closed': False,
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = unarchive_card('card123')

        assert result['success'] is True
        assert result['data']['unarchived'] is True


class TestSearchCards:
    """REQ-008-003: search-cards command tests."""

    @patch('trello_api.urlopen')
    def test_search_cards_finds_matching_cards(self, mock_urlopen, mock_env):
        """REQ-008-003: search-cards should find cards by query."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'cards': [
                {'id': 'card1', 'name': '[Q:CH] Project 001', 'closed': False},
                {'id': 'card2', 'name': '[Q:CH] Project 002', 'closed': True},
            ]
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = search_cards('board123', '[Q:CH]')

        assert result['success'] is True
        assert len(result['data']) == 2


class TestGetAllCards:
    """REQ-008-004: get-all-cards command tests."""

    @patch('trello_api.urlopen')
    def test_get_all_cards_returns_list_cards(self, mock_urlopen, mock_env):
        """REQ-008-004: get-all-cards should return all cards in a list."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            {'id': 'card1', 'name': 'Card 1', 'closed': False},
            {'id': 'card2', 'name': 'Card 2', 'closed': False},
        ]).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_all_cards('list123')

        assert result['success'] is True
        assert len(result['data']) == 2

    @patch('trello_api.urlopen')
    def test_get_all_cards_includes_archived_when_requested(self, mock_urlopen, mock_env):
        """REQ-008-004: get-all-cards should optionally include archived cards."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            {'id': 'card1', 'name': 'Card 1', 'closed': False},
            {'id': 'card2', 'name': 'Card 2', 'closed': True},
        ]).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = get_all_cards('list123', include_archived=True)

        assert result['success'] is True
        assert len(result['data']) == 2


class TestRateLimiting:
    """REQ-008-005: Rate limiting with exponential backoff tests."""

    def test_rate_limiter_allows_initial_request(self):
        """REQ-008-005: Rate limiter should allow first request."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        assert limiter.acquire() is True

    def test_rate_limiter_blocks_after_limit(self):
        """REQ-008-005: Rate limiter should block after limit reached."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        assert limiter.acquire() is False

    def test_exponential_backoff_increases_delay(self):
        """REQ-008-005: Backoff should increase exponentially."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        delays = []
        for attempt in range(5):
            delay = limiter.get_backoff_delay(attempt)
            delays.append(delay)

        # Each delay should be roughly 2x previous (with jitter)
        for i in range(1, len(delays)):
            assert delays[i] > delays[i - 1]


class TestErrorSanitization:
    """REQ-008-006: Error message sanitization tests."""

    def test_sanitize_removes_api_key(self):
        """REQ-008-006: API key should be removed from error messages."""
        error = "HTTP 401: Invalid key=abc123def456&token=secret789"
        result = sanitize_error(error)

        assert 'abc123' not in result
        assert 'secret789' not in result
        assert 'key=' in result or '[REDACTED]' in result

    def test_sanitize_removes_token(self):
        """REQ-008-006: Token should be removed from error messages."""
        error = "URL contains token=mysecrettoken123"
        result = sanitize_error(error)

        assert 'mysecrettoken123' not in result

    def test_sanitize_preserves_useful_info(self):
        """REQ-008-006: Sanitization should preserve HTTP status codes."""
        error = "HTTP 429: Rate limit exceeded key=secret"
        result = sanitize_error(error)

        assert '429' in result
        assert 'Rate limit' in result


class TestCaching:
    """REQ-008-007: In-memory caching tests."""

    def test_cache_stores_value(self):
        """REQ-008-007: Cache should store and retrieve values."""
        cache = Cache(ttl_seconds=60)
        cache.set('key1', {'data': 'test'})

        result = cache.get('key1')
        assert result == {'data': 'test'}

    def test_cache_expires_after_ttl(self):
        """REQ-008-007: Cache should expire entries after TTL."""
        cache = Cache(ttl_seconds=0.1)  # 100ms TTL
        cache.set('key1', {'data': 'test'})

        time.sleep(0.15)  # Wait for expiry

        result = cache.get('key1')
        assert result is None

    def test_cache_invalidation(self):
        """REQ-008-007: Cache should support manual invalidation."""
        cache = Cache(ttl_seconds=60)
        cache.set('key1', {'data': 'test'})
        cache.invalidate('key1')

        result = cache.get('key1')
        assert result is None


class TestErrorResponses:
    """REQ-008-008: Canonical error response schema tests."""

    @patch('trello_api.urlopen')
    def test_error_response_has_required_fields(self, mock_urlopen, mock_env):
        """REQ-008-008: Error responses should have success=false and error field."""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            'http://example.com', 404, 'Not Found', {}, None
        )

        result = api_request('GET', 'cards/invalid')

        assert result['success'] is False
        assert 'error' in result
        assert isinstance(result['error'], str)

    @patch('trello_api.urlopen')
    def test_error_response_sanitizes_credentials(self, mock_urlopen, mock_env):
        """REQ-008-008: Error responses should not contain credentials."""
        from urllib.error import HTTPError

        # Simulate error that might contain credentials
        error_body = "Invalid API key: abc123"
        mock_error = HTTPError('http://example.com', 401, 'Unauthorized', {}, None)
        mock_error.read = MagicMock(return_value=error_body.encode())
        mock_error.fp = True
        mock_urlopen.side_effect = mock_error

        result = api_request('GET', 'cards/test')

        # Error should be present but sanitized
        assert result['success'] is False
        assert os.environ.get('TRELLO_API_KEY', '') not in result['error']


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables for tests."""
    monkeypatch.setenv('TRELLO_API_KEY', 'test_api_key_12345')
    monkeypatch.setenv('TRELLO_TOKEN', 'test_token_67890')
    return monkeypatch


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
