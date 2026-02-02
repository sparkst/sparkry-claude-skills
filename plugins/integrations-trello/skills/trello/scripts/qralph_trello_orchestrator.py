#!/usr/bin/env python3
"""
QRALPH orchestrator with Trello integration.
REQ-011: QRALPH Orchestrator Integration

Provides commands for managing QRALPH projects with Trello sync.
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import sibling modules
try:
    from trello_integration import (
        parse_control_md,
        write_control_md,
        create_project_card,
        update_card_with_run_summary,
        check_card_status,
        close_project,
        reopen_project,
        sync_projects,
        recover_deleted_card,
        git_commit_control_md,
        ControlMdFrontmatter,
    )
    from trello_config import load_config
    from github_repo import detect_github_repo
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from trello_integration import (
        parse_control_md,
        write_control_md,
        create_project_card,
        update_card_with_run_summary,
        check_card_status,
        close_project,
        reopen_project,
        sync_projects,
        recover_deleted_card,
        git_commit_control_md,
        ControlMdFrontmatter,
    )
    from trello_config import load_config
    from github_repo import detect_github_repo


class QralphTrelloOrchestrator:
    """
    REQ-011: Orchestrates QRALPH commands with Trello integration.
    """

    def __init__(self, projects_dir: Optional[str] = None):
        """
        Initialize orchestrator.

        Args:
            projects_dir: Path to .qralph/projects directory
        """
        if projects_dir:
            self.projects_dir = Path(projects_dir)
        else:
            # Find .qralph directory
            self.projects_dir = self._find_projects_dir()

        self.config = None
        try:
            self.config = load_config()
        except FileNotFoundError:
            pass

    def _find_projects_dir(self) -> Path:
        """Find .qralph/projects directory."""
        current = Path.cwd()
        while current != current.parent:
            projects_path = current / ".qralph" / "projects"
            if projects_path.exists():
                return projects_path
            current = current.parent
        return Path.cwd() / ".qralph" / "projects"

    def _get_next_project_id(self, prefix: str = "") -> str:
        """Get next available project ID number."""
        if not self.projects_dir.exists():
            return f"001-{prefix}" if prefix else "001"

        existing = [d.name for d in self.projects_dir.iterdir() if d.is_dir()]
        numbers = []
        for name in existing:
            match = re.match(r'^(\d+)-', name)
            if match:
                numbers.append(int(match.group(1)))

        next_num = max(numbers) + 1 if numbers else 1
        return f"{next_num:03d}-{prefix}" if prefix else f"{next_num:03d}"


def handle_new_project(
    request: str,
    projects_dir: str,
    label_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    REQ-011: Handle QRALPH "<request>" command.

    Creates new project directory and Trello card.

    Args:
        request: Project request text
        projects_dir: Path to projects directory
        label_ids: Optional label IDs for card

    Returns:
        Result dict with project info
    """
    # Load config
    try:
        config = load_config()
    except FileNotFoundError:
        return {'success': False, 'error': 'Trello config not found. Create .qralph/trello-config.json'}

    projects_path = Path(projects_dir)
    projects_path.mkdir(parents=True, exist_ok=True)

    # Generate project ID from request
    slug = re.sub(r'[^a-z0-9]+', '-', request.lower())[:30].strip('-')

    # Find next number
    orchestrator = QralphTrelloOrchestrator(projects_dir)
    project_id = orchestrator._get_next_project_id(slug)

    # Check if project already exists
    project_dir = projects_path / project_id
    if project_dir.exists():
        return {'success': False, 'error': f'Project {project_id} already exists'}

    # Create project directory
    project_dir.mkdir()

    # Get GitHub repo
    github_repo = config.get('github_repo') or detect_github_repo()
    if not github_repo:
        return {'success': False, 'error': 'Could not detect GitHub repo'}

    # Create CONTROL.md
    control_md_path = project_dir / "CONTROL.md"
    control_content = f"""---
schema_version: 1
project_id: {project_id}
github_repo: {github_repo}
---

# Project: {project_id}

## Request

{request}

## Status

- Phase: PLANNING
- Created: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
"""
    control_md_path.write_text(control_content)

    # Create Trello card
    result = create_project_card(
        str(control_md_path),
        request,
        config['list_id'],
        label_ids,
    )

    if result['success']:
        # Commit
        git_commit_control_md(str(control_md_path), "Created Trello card")

        return {
            'success': True,
            'project_id': project_id,
            'project_dir': str(project_dir),
            'card_url': result['data'].get('url'),
        }
    else:
        # Card creation failed but project created locally
        return {
            'success': True,
            'project_id': project_id,
            'project_dir': str(project_dir),
            'offline_pending': True,
            'warning': result.get('error', 'Trello card creation failed'),
        }


def handle_resume_project(
    project_id: str,
    projects_dir: str,
) -> Dict[str, Any]:
    """
    REQ-011: Handle QRALPH resume <id> command.

    Checks card status and handles closed cards.

    Args:
        project_id: Project ID to resume
        projects_dir: Path to projects directory

    Returns:
        Result dict with status and any required actions
    """
    projects_path = Path(projects_dir)

    # Find project directory
    project_dir = None
    for d in projects_path.iterdir():
        if d.is_dir() and (d.name == project_id or d.name.startswith(f"{project_id}-")):
            project_dir = d
            break

    if not project_dir:
        return {'success': False, 'error': f'Project not found: {project_id}'}

    control_md_path = project_dir / "CONTROL.md"
    if not control_md_path.exists():
        return {'success': False, 'error': f'CONTROL.md not found in {project_dir}'}

    # Check card status
    status = check_card_status(str(control_md_path))

    if status.get('deleted'):
        return {
            'success': True,
            'needs_user_action': True,
            'deleted': True,
            'project_id': project_id,
            'project_dir': str(project_dir),
            'message': status['message'],
            'options': [
                {'id': 1, 'label': 'Create new card (Recommended)'},
                {'id': 2, 'label': 'Clear trello metadata'},
                {'id': 3, 'label': 'Cancel'},
            ]
        }

    if status.get('closed'):
        fm = parse_control_md(str(control_md_path))
        return {
            'success': True,
            'needs_user_action': True,
            'closed': True,
            'project_id': project_id,
            'project_dir': str(project_dir),
            'message': status['message'],
            'context': {
                'last_run': fm.trello.last_run_at if fm and fm.trello else None,
            },
            'options': [
                {'id': 1, 'label': f'Re-open project {project_id} and continue (Recommended)'},
                {'id': 2, 'label': f'Create new project {project_id}-v2'},
                {'id': 3, 'label': 'Cancel'},
            ]
        }

    return {
        'success': True,
        'needs_user_action': False,
        'project_id': project_id,
        'project_dir': str(project_dir),
        'can_proceed': True,
    }


def handle_project_status(projects_dir: str) -> Dict[str, Any]:
    """
    REQ-011: Handle QRALPH status command.

    Shows all projects and their Trello status.

    Args:
        projects_dir: Path to projects directory

    Returns:
        Result dict with project list
    """
    projects_path = Path(projects_dir)
    if not projects_path.exists():
        return {'success': True, 'projects': [], 'message': 'No projects found'}

    projects = []
    for project_dir in sorted(projects_path.iterdir()):
        if not project_dir.is_dir():
            continue

        control_md_path = project_dir / "CONTROL.md"
        if not control_md_path.exists():
            continue

        fm = parse_control_md(str(control_md_path))
        if not fm:
            continue

        project_info = {
            'project_id': fm.project_id,
            'github_repo': fm.github_repo,
            'path': str(project_dir),
        }

        if fm.trello:
            project_info['trello'] = {
                'status': fm.trello.status,
                'card_url': fm.trello.card_url,
                'last_run': fm.trello.last_run_at,
                'sync_pending': fm.trello.sync_pending,
            }

            # Check live status if linked
            if fm.trello.card_id:
                status = check_card_status(str(control_md_path))
                if status.get('success'):
                    project_info['trello']['live_status'] = 'closed' if status.get('closed') else 'open'
        else:
            project_info['trello'] = None

        projects.append(project_info)

    return {'success': True, 'projects': projects}


def handle_close_project(project_id: str, projects_dir: str) -> Dict[str, Any]:
    """
    REQ-011: Handle QRALPH close <id> command.

    Archives Trello card and updates local status.

    Args:
        project_id: Project ID to close
        projects_dir: Path to projects directory

    Returns:
        Result dict with close status
    """
    projects_path = Path(projects_dir)

    # Find project directory
    project_dir = None
    for d in projects_path.iterdir():
        if d.is_dir() and (d.name == project_id or d.name.startswith(f"{project_id}-")):
            project_dir = d
            break

    if not project_dir:
        return {'success': False, 'error': f'Project not found: {project_id}'}

    control_md_path = project_dir / "CONTROL.md"
    if not control_md_path.exists():
        return {'success': False, 'error': f'CONTROL.md not found'}

    # Close project
    result = close_project(str(control_md_path))

    if result['success']:
        # Commit
        git_commit_control_md(str(control_md_path), "Closed project")

    return result


def handle_sync(projects_dir: str) -> Dict[str, Any]:
    """
    REQ-011: Handle QRALPH sync command.

    Syncs local projects with Trello.

    Args:
        projects_dir: Path to projects directory

    Returns:
        Sync report
    """
    try:
        config = load_config()
    except FileNotFoundError:
        return {'success': False, 'error': 'Trello config not found'}

    return sync_projects(projects_dir, config['list_id'])


def handle_help() -> str:
    """
    REQ-011: Handle QRALPH help command.

    Returns help text with available commands.
    """
    return """QRALPH Commands:
  QRALPH "<request>"     - Create new project with 5-agent review
  QRALPH resume <id>     - Resume existing project
  QRALPH status          - Show all projects and their status
  QRALPH sync            - Reconcile local projects with Trello
  QRALPH close <id>      - Close project and archive Trello card
  QRALPH help            - Show this help

Examples:
  QRALPH "Build user authentication"
  QRALPH resume 012
  QRALPH close 012-auth-feature
"""


def handle_user_choice(
    project_id: str,
    projects_dir: str,
    choice: int,
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Handle user's choice from closed/deleted card prompts.

    Args:
        project_id: Project ID
        projects_dir: Path to projects directory
        choice: User's choice (1, 2, or 3)
        context: Additional context (e.g., whether card was deleted)

    Returns:
        Result of the chosen action
    """
    projects_path = Path(projects_dir)

    # Find project directory
    project_dir = None
    for d in projects_path.iterdir():
        if d.is_dir() and (d.name == project_id or d.name.startswith(f"{project_id}-")):
            project_dir = d
            break

    if not project_dir:
        return {'success': False, 'error': f'Project not found: {project_id}'}

    control_md_path = project_dir / "CONTROL.md"
    is_deleted = context and context.get('deleted')

    if choice == 1:
        if is_deleted:
            # Create new card
            config = load_config()
            return recover_deleted_card(str(control_md_path), config['list_id'])
        else:
            # Re-open card
            result = reopen_project(str(control_md_path))
            if result['success']:
                git_commit_control_md(str(control_md_path), "Reopened project")
            return result

    elif choice == 2:
        if is_deleted:
            # Clear metadata
            fm = parse_control_md(str(control_md_path))
            fm.trello = None
            write_control_md(str(control_md_path), fm)
            return {'success': True, 'message': 'Trello metadata cleared'}
        else:
            # Create new project version
            fm = parse_control_md(str(control_md_path))
            new_id = f"{project_id}-v2"
            return handle_new_project(
                f"Continue: {fm.project_id}",
                projects_dir,
            )

    elif choice == 3:
        return {'success': True, 'cancelled': True}

    return {'success': False, 'error': 'Invalid choice'}


if __name__ == "__main__":
    print(handle_help())
