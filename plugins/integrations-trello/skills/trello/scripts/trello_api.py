#!/usr/bin/env python3
"""
Trello API Integration Tool
REQ-008: Enhanced Trello API with caching, rate limiting, and new commands.

Provides CLI access to Trello API for:
- Creating cards
- Listing boards and lists
- Finding boards/lists by name
- Updating cards
- Archiving/unarchiving cards
- Getting card details
- Searching cards
- Getting all cards in a list

Usage:
    python trello_api.py <command> [options]

Commands:
    list-boards             List all boards for the authenticated user
    list-lists              List all lists on a board
    find-board              Find a board by name
    find-list               Find a list by name on a board
    create-card             Create a new card
    update-card             Update an existing card
    archive-card            Archive (close) a card
    unarchive-card          Unarchive (reopen) a card
    get-card                Get card details including closed status
    search-cards            Search for cards on a board
    get-all-cards           Get all cards in a list

Environment Variables Required:
    TRELLO_API_KEY          Your Trello API key
    TRELLO_TOKEN            Your Trello OAuth token
"""

import argparse
import json
import os
import random
import re
import sys
import time
from threading import Lock
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


class Cache:
    """
    REQ-008-007: In-memory cache with TTL.

    Thread-safe cache for API responses to reduce redundant calls.
    """

    def __init__(self, ttl_seconds: int = 60):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() > entry['expires']:
                del self._cache[key]
                return None

            return entry['value']

    def set(self, key: str, value: Any) -> None:
        """Store value in cache with TTL."""
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires': time.time() + self._ttl
            }

    def invalidate(self, key: str) -> None:
        """Remove entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def invalidate_pattern(self, pattern: str) -> None:
        """Remove all entries matching pattern."""
        with self._lock:
            keys_to_delete = [k for k in self._cache if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()


class RateLimiter:
    """
    REQ-008-005: Rate limiter with exponential backoff and jitter.

    Prevents hitting Trello API rate limits (300 requests/10 seconds).
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 10):
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: list = []
        self._lock = Lock()
        self._base_delay = 1.0
        self._max_delay = 60.0

    def acquire(self) -> bool:
        """Try to acquire permission to make a request."""
        with self._lock:
            now = time.time()
            # Remove old requests outside the window
            self._requests = [t for t in self._requests if now - t < self._window]

            if len(self._requests) >= self._max_requests:
                return False

            self._requests.append(now)
            return True

    def get_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay with jitter.

        Formula: delay = min(base * 2^attempt + jitter, max_delay)
        """
        delay = min(self._base_delay * (2 ** attempt), self._max_delay)
        # Add jitter (0-25% of delay)
        jitter = random.uniform(0, delay * 0.25)
        return delay + jitter

    def wait_if_needed(self) -> None:
        """Wait until a request can be made."""
        while not self.acquire():
            time.sleep(0.1)


def sanitize_error(error: str) -> str:
    """
    REQ-008-006: Remove sensitive information from error messages.

    Removes API keys and tokens from error strings.
    """
    # Pattern to match key= or token= followed by alphanumeric values
    patterns = [
        (r'key=[a-zA-Z0-9]+', 'key=[REDACTED]'),
        (r'token=[a-zA-Z0-9]+', 'token=[REDACTED]'),
        (r'TRELLO_API_KEY=[^\s&]+', 'TRELLO_API_KEY=[REDACTED]'),
        (r'TRELLO_TOKEN=[^\s&]+', 'TRELLO_TOKEN=[REDACTED]'),
    ]

    result = error
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)

    return result


# Global cache and rate limiter instances
_cache = Cache(ttl_seconds=60)
_rate_limiter = RateLimiter(max_requests=100, window_seconds=10)


def get_credentials():
    """Get Trello API credentials from environment"""
    api_key = os.environ.get('TRELLO_API_KEY')
    token = os.environ.get('TRELLO_TOKEN')

    if not api_key or not token:
        return None, "Missing TRELLO_API_KEY or TRELLO_TOKEN environment variables"

    return {'key': api_key, 'token': token}, None


def api_request(
    method: str,
    endpoint: str,
    params: dict = None,
    data: dict = None,
    use_cache: bool = True,
    max_retries: int = 3
):
    """
    Make a request to the Trello API with rate limiting and caching.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        endpoint: API endpoint path
        params: Query parameters
        data: Request body data
        use_cache: Whether to use cache for GET requests
        max_retries: Maximum retry attempts for rate limit errors
    """
    creds, error = get_credentials()
    if error:
        return {'success': False, 'error': error}

    # Check cache for GET requests
    cache_key = f"{method}:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
    if method == 'GET' and use_cache:
        cached = _cache.get(cache_key)
        if cached is not None:
            return {'success': True, 'data': cached, 'cached': True}

    base_url = 'https://api.trello.com/1'
    url = f"{base_url}/{endpoint}"

    # Merge credentials with params
    all_params = {**creds}
    if params:
        all_params.update(params)

    if method == 'GET':
        url = f"{url}?{urlencode(all_params)}"
        request = Request(url, method='GET')
    else:
        # POST, PUT, DELETE
        if data:
            all_params.update(data)
        url = f"{url}?{urlencode(all_params)}"
        request = Request(url, method=method)

    request.add_header('Accept', 'application/json')

    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        # Wait for rate limiter
        _rate_limiter.wait_if_needed()

        try:
            with urlopen(request, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))

                # Cache successful GET responses
                if method == 'GET' and use_cache:
                    _cache.set(cache_key, result)

                return {'success': True, 'data': result}

        except HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            sanitized = sanitize_error(f"HTTP {e.code}: {error_body}")

            # Retry on rate limit (429) with backoff
            if e.code == 429 and attempt < max_retries - 1:
                delay = _rate_limiter.get_backoff_delay(attempt)
                time.sleep(delay)
                continue

            return {'success': False, 'error': sanitized}

        except URLError as e:
            return {'success': False, 'error': sanitize_error(f"URL Error: {str(e)}")}

        except Exception as e:
            return {'success': False, 'error': sanitize_error(str(e))}

    return {'success': False, 'error': 'Max retries exceeded'}


def list_boards():
    """List all boards for the authenticated user"""
    result = api_request('GET', 'members/me/boards', {'fields': 'name,url,closed'})

    if result['success']:
        # Filter to open boards only
        boards = [b for b in result['data'] if not b.get('closed', False)]
        result['data'] = boards

    return result


def list_lists(board_id: str):
    """List all lists on a board"""
    result = api_request('GET', f'boards/{board_id}/lists', {'fields': 'name,closed'})

    if result['success']:
        # Filter to open lists only
        lists = [l for l in result['data'] if not l.get('closed', False)]
        result['data'] = lists

    return result


def find_board(name: str):
    """Find a board by name (case-insensitive)"""
    result = list_boards()

    if not result['success']:
        return result

    name_lower = name.lower()
    for board in result['data']:
        if board['name'].lower() == name_lower:
            return {'success': True, 'data': board}

    # Try partial match
    for board in result['data']:
        if name_lower in board['name'].lower():
            return {'success': True, 'data': board}

    return {'success': False, 'error': f"Board not found: {name}"}


def find_list(board_id: str, name: str):
    """Find a list by name on a board (case-insensitive)"""
    result = list_lists(board_id)

    if not result['success']:
        return result

    name_lower = name.lower()
    for lst in result['data']:
        if lst['name'].lower() == name_lower:
            return {'success': True, 'data': lst}

    # Try partial match
    for lst in result['data']:
        if name_lower in lst['name'].lower():
            return {'success': True, 'data': lst}

    return {'success': False, 'error': f"List not found: {name}"}


def create_card(list_id: str, title: str, description: str = None, due: str = None, labels: str = None):
    """Create a new card on a list"""
    data = {
        'idList': list_id,
        'name': title,
    }

    if description:
        data['desc'] = description

    if due:
        data['due'] = due

    if labels:
        data['idLabels'] = labels

    result = api_request('POST', 'cards', data=data)

    if result['success']:
        # Return simplified response
        card = result['data']
        result['data'] = {
            'id': card.get('id'),
            'name': card.get('name'),
            'url': card.get('shortUrl') or card.get('url'),
            'desc': card.get('desc'),
        }

    return result


def update_card(card_id: str, title: str = None, description: str = None, due: str = None, move_to_list: str = None):
    """Update an existing card"""
    data = {}

    if title:
        data['name'] = title

    if description:
        data['desc'] = description

    if due:
        data['due'] = due

    if move_to_list:
        data['idList'] = move_to_list

    if not data:
        return {'success': False, 'error': 'No fields to update'}

    result = api_request('PUT', f'cards/{card_id}', data=data)

    if result['success']:
        card = result['data']
        result['data'] = {
            'id': card.get('id'),
            'name': card.get('name'),
            'url': card.get('shortUrl') or card.get('url'),
        }

    return result


def archive_card(card_id: str):
    """Archive (close) a card"""
    result = api_request('PUT', f'cards/{card_id}', data={'closed': 'true'})

    if result['success']:
        # Invalidate cache for this card
        _cache.invalidate_pattern(f'cards/{card_id}')
        result['data'] = {'id': card_id, 'archived': True}

    return result


def get_card(card_id: str):
    """
    REQ-008-001: Get card details including closed status.

    Returns card data with id, name, desc, closed, url, and idList.
    """
    result = api_request(
        'GET',
        f'cards/{card_id}',
        params={'fields': 'name,desc,closed,shortUrl,url,idList'}
    )

    if result['success']:
        card = result['data']
        result['data'] = {
            'id': card.get('id'),
            'name': card.get('name'),
            'desc': card.get('desc', ''),
            'closed': card.get('closed', False),
            'url': card.get('shortUrl') or card.get('url'),
            'idList': card.get('idList'),
        }

    return result


def unarchive_card(card_id: str):
    """
    REQ-008-002: Unarchive (reopen) a card.

    Sets closed=false to restore an archived card.
    """
    result = api_request('PUT', f'cards/{card_id}', data={'closed': 'false'})

    if result['success']:
        # Invalidate cache for this card
        _cache.invalidate_pattern(f'cards/{card_id}')
        result['data'] = {'id': card_id, 'unarchived': True}

    return result


def search_cards(board_id: str, query: str):
    """
    REQ-008-003: Search for cards on a board.

    Uses Trello search API to find cards matching query.
    Returns list of cards with id, name, closed status.
    """
    result = api_request(
        'GET',
        'search',
        params={
            'query': query,
            'idBoards': board_id,
            'modelTypes': 'cards',
            'card_fields': 'name,closed,shortUrl,idList',
            'cards_limit': 100,
        },
        use_cache=False  # Search results shouldn't be cached
    )

    if result['success']:
        cards = result['data'].get('cards', [])
        result['data'] = [
            {
                'id': card.get('id'),
                'name': card.get('name'),
                'closed': card.get('closed', False),
                'url': card.get('shortUrl'),
                'idList': card.get('idList'),
            }
            for card in cards
        ]

    return result


def get_all_cards(list_id: str, include_archived: bool = False):
    """
    REQ-008-004: Get all cards in a list.

    Args:
        list_id: The list ID to get cards from
        include_archived: If True, includes archived cards

    Returns list of cards with id, name, closed status.
    """
    params = {
        'fields': 'name,desc,closed,shortUrl,idList',
    }

    # Trello's filter parameter for cards
    if include_archived:
        params['filter'] = 'all'
    else:
        params['filter'] = 'open'

    result = api_request('GET', f'lists/{list_id}/cards', params=params)

    if result['success']:
        cards = result['data']
        result['data'] = [
            {
                'id': card.get('id'),
                'name': card.get('name'),
                'desc': card.get('desc', ''),
                'closed': card.get('closed', False),
                'url': card.get('shortUrl'),
            }
            for card in cards
        ]

    return result


def main():
    parser = argparse.ArgumentParser(description='Trello API CLI')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # list-boards
    subparsers.add_parser('list-boards', help='List all boards')

    # list-lists
    list_lists_parser = subparsers.add_parser('list-lists', help='List all lists on a board')
    list_lists_parser.add_argument('--board-id', required=True, help='Board ID')

    # find-board
    find_board_parser = subparsers.add_parser('find-board', help='Find a board by name')
    find_board_parser.add_argument('--name', required=True, help='Board name')

    # find-list
    find_list_parser = subparsers.add_parser('find-list', help='Find a list by name')
    find_list_parser.add_argument('--board-id', required=True, help='Board ID')
    find_list_parser.add_argument('--name', required=True, help='List name')

    # create-card
    create_card_parser = subparsers.add_parser('create-card', help='Create a new card')
    create_card_parser.add_argument('--list-id', required=True, help='List ID')
    create_card_parser.add_argument('--title', required=True, help='Card title')
    create_card_parser.add_argument('--description', help='Card description')
    create_card_parser.add_argument('--due', help='Due date (ISO format)')
    create_card_parser.add_argument('--labels', help='Comma-separated label IDs')

    # update-card
    update_card_parser = subparsers.add_parser('update-card', help='Update an existing card')
    update_card_parser.add_argument('--card-id', required=True, help='Card ID')
    update_card_parser.add_argument('--title', help='New title')
    update_card_parser.add_argument('--description', help='New description')
    update_card_parser.add_argument('--due', help='New due date')
    update_card_parser.add_argument('--move-to-list', help='Move to list ID')

    # archive-card
    archive_card_parser = subparsers.add_parser('archive-card', help='Archive a card')
    archive_card_parser.add_argument('--card-id', required=True, help='Card ID')

    # get-card (REQ-008-001)
    get_card_parser = subparsers.add_parser('get-card', help='Get card details')
    get_card_parser.add_argument('--card-id', required=True, help='Card ID')

    # unarchive-card (REQ-008-002)
    unarchive_card_parser = subparsers.add_parser('unarchive-card', help='Unarchive a card')
    unarchive_card_parser.add_argument('--card-id', required=True, help='Card ID')

    # search-cards (REQ-008-003)
    search_cards_parser = subparsers.add_parser('search-cards', help='Search for cards')
    search_cards_parser.add_argument('--board-id', required=True, help='Board ID')
    search_cards_parser.add_argument('--query', required=True, help='Search query')

    # get-all-cards (REQ-008-004)
    get_all_cards_parser = subparsers.add_parser('get-all-cards', help='Get all cards in a list')
    get_all_cards_parser.add_argument('--list-id', required=True, help='List ID')
    get_all_cards_parser.add_argument('--include-archived', action='store_true', help='Include archived cards')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'list-boards':
        result = list_boards()
    elif args.command == 'list-lists':
        result = list_lists(args.board_id)
    elif args.command == 'find-board':
        result = find_board(args.name)
    elif args.command == 'find-list':
        result = find_list(args.board_id, args.name)
    elif args.command == 'create-card':
        result = create_card(
            args.list_id,
            args.title,
            args.description,
            args.due,
            args.labels
        )
    elif args.command == 'update-card':
        result = update_card(
            args.card_id,
            args.title,
            args.description,
            args.due,
            args.move_to_list
        )
    elif args.command == 'archive-card':
        result = archive_card(args.card_id)
    elif args.command == 'get-card':
        result = get_card(args.card_id)
    elif args.command == 'unarchive-card':
        result = unarchive_card(args.card_id)
    elif args.command == 'search-cards':
        result = search_cards(args.board_id, args.query)
    elif args.command == 'get-all-cards':
        result = get_all_cards(args.list_id, args.include_archived)
    else:
        result = {'success': False, 'error': f'Unknown command: {args.command}'}

    # Output result as JSON
    print(json.dumps(result, indent=2))

    # Exit with error code if not successful
    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
