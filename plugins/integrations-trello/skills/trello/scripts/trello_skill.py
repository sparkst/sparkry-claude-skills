#!/usr/bin/env python3
"""
Standalone Trello skill CLI.
REQ-013: Standalone Trello Skill

Provides a simple CLI for Trello operations independent of QRALPH.

Usage:
    python trello_skill.py <command> [options]

Commands:
    create      Create a new card
    get         Get card details
    update      Update a card
    close       Archive a card
    reopen      Unarchive a card
    list        List cards in a list
    sync        Sync local projects with Trello
"""

import argparse
import json
import sys
from pathlib import Path

# Import sibling modules
try:
    from trello_api import (
        create_card,
        update_card,
        archive_card,
        unarchive_card,
        get_card,
        get_all_cards,
        search_cards,
    )
    from trello_config import load_config
    from trello_integration import sync_projects
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from trello_api import (
        create_card,
        update_card,
        archive_card,
        unarchive_card,
        get_card,
        get_all_cards,
        search_cards,
    )
    from trello_config import load_config
    from trello_integration import sync_projects


def cmd_create(args):
    """Create a new card."""
    list_id = args.list_id
    if not list_id:
        try:
            config = load_config()
            list_id = config.get('list_id')
        except FileNotFoundError:
            return {'success': False, 'error': 'No list-id provided and no config found'}

    result = create_card(
        list_id=list_id,
        title=args.title,
        description=args.description,
        labels=args.labels,
    )
    return result


def cmd_get(args):
    """Get card details."""
    return get_card(args.card_id)


def cmd_update(args):
    """Update a card."""
    description = args.description

    if args.append and description:
        # Get existing description and append
        card_result = get_card(args.card_id)
        if card_result['success']:
            existing = card_result['data'].get('desc', '')
            description = existing + '\n\n' + description

    return update_card(
        card_id=args.card_id,
        title=args.title,
        description=description,
    )


def cmd_close(args):
    """Archive a card."""
    return archive_card(args.card_id)


def cmd_reopen(args):
    """Unarchive a card."""
    return unarchive_card(args.card_id)


def cmd_list(args):
    """List cards in a list."""
    list_id = args.list_id
    if not list_id:
        try:
            config = load_config()
            list_id = config.get('list_id')
        except FileNotFoundError:
            return {'success': False, 'error': 'No list-id provided and no config found'}

    return get_all_cards(list_id, include_archived=args.include_archived)


def cmd_sync(args):
    """Sync local projects with Trello."""
    try:
        config = load_config()
    except FileNotFoundError:
        return {'success': False, 'error': 'Trello config not found'}

    projects_dir = args.projects_dir
    if not projects_dir:
        # Find .qralph/projects
        current = Path.cwd()
        while current != current.parent:
            projects_path = current / '.qralph' / 'projects'
            if projects_path.exists():
                projects_dir = str(projects_path)
                break
            current = current.parent

    if not projects_dir:
        return {'success': False, 'error': 'Projects directory not found'}

    return sync_projects(projects_dir, config['list_id'])


def main():
    parser = argparse.ArgumentParser(
        description='Standalone Trello skill CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trello_skill.py create --title "My Task" --description "Do something"
  python trello_skill.py get --card-id abc123
  python trello_skill.py list --list-id list123
  python trello_skill.py sync
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # create
    create_parser = subparsers.add_parser('create', help='Create a new card')
    create_parser.add_argument('--title', required=True, help='Card title')
    create_parser.add_argument('--description', help='Card description')
    create_parser.add_argument('--list-id', help='List ID (uses config default if not provided)')
    create_parser.add_argument('--labels', help='Comma-separated label IDs')

    # get
    get_parser = subparsers.add_parser('get', help='Get card details')
    get_parser.add_argument('--card-id', required=True, help='Card ID')

    # update
    update_parser = subparsers.add_parser('update', help='Update a card')
    update_parser.add_argument('--card-id', required=True, help='Card ID')
    update_parser.add_argument('--title', help='New title')
    update_parser.add_argument('--description', help='New description')
    update_parser.add_argument('--append', action='store_true', help='Append to existing description')

    # close
    close_parser = subparsers.add_parser('close', help='Archive a card')
    close_parser.add_argument('--card-id', required=True, help='Card ID')

    # reopen
    reopen_parser = subparsers.add_parser('reopen', help='Unarchive a card')
    reopen_parser.add_argument('--card-id', required=True, help='Card ID')

    # list
    list_parser = subparsers.add_parser('list', help='List cards in a list')
    list_parser.add_argument('--list-id', help='List ID (uses config default if not provided)')
    list_parser.add_argument('--include-archived', action='store_true', help='Include archived cards')

    # sync
    sync_parser = subparsers.add_parser('sync', help='Sync local projects with Trello')
    sync_parser.add_argument('--projects-dir', help='Path to projects directory')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    commands = {
        'create': cmd_create,
        'get': cmd_get,
        'update': cmd_update,
        'close': cmd_close,
        'reopen': cmd_reopen,
        'list': cmd_list,
        'sync': cmd_sync,
    }

    result = commands[args.command](args)

    # Output result as JSON
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get('success') else 1)


if __name__ == '__main__':
    main()
