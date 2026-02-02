#!/usr/bin/env python3
"""
Trello integration for QRALPH projects.
REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-014, REQ-016

Handles CONTROL.md frontmatter, card creation, updates, and sync.
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

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
    from github_repo import detect_github_repo, get_repo_initials
except ImportError:
    import sys
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
    from github_repo import detect_github_repo, get_repo_initials

logger = logging.getLogger(__name__)


class TrelloIntegrationError(Exception):
    """Raised when Trello integration fails."""
    pass


@dataclass
class ControlMdFrontmatter:
    """
    REQ-001: CONTROL.md frontmatter schema.

    Schema version 1 structure for project-Trello card mapping.
    """

    @dataclass
    class TrelloSection:
        """Trello-specific fields in frontmatter."""
        card_id: str
        card_url: str
        status: str = "open"  # open | closed | offline-pending
        created_at: Optional[str] = None
        last_run_at: Optional[str] = None
        sync_pending: bool = False

    schema_version: int = 1
    project_id: str = ""
    github_repo: str = ""
    trello: Optional[TrelloSection] = None

    # Store original content for preservation
    _original_content: str = field(default="", repr=False)


def parse_control_md(file_path: str) -> Optional[ControlMdFrontmatter]:
    """
    REQ-001: Parse CONTROL.md frontmatter.

    Args:
        file_path: Path to CONTROL.md

    Returns:
        ControlMdFrontmatter object, or None if invalid
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"CONTROL.md not found: {file_path}")
        return None

    content = path.read_text()

    # Extract YAML frontmatter between --- markers
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        logger.warning(f"No valid frontmatter in: {file_path}")
        return None

    yaml_content = match.group(1)
    body_content = match.group(2)

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        logger.warning(f"Invalid YAML frontmatter in {file_path}: {e}")
        return None

    if not isinstance(data, dict):
        logger.warning(f"Frontmatter is not a dict in: {file_path}")
        return None

    # Build frontmatter object
    fm = ControlMdFrontmatter(
        schema_version=data.get('schema_version', 1),
        project_id=data.get('project_id', ''),
        github_repo=data.get('github_repo', ''),
        _original_content=body_content,
    )

    # Parse trello section if present
    if 'trello' in data and isinstance(data['trello'], dict):
        trello_data = data['trello']
        fm.trello = ControlMdFrontmatter.TrelloSection(
            card_id=trello_data.get('card_id', ''),
            card_url=trello_data.get('card_url', ''),
            status=trello_data.get('status', 'open'),
            created_at=trello_data.get('created_at'),
            last_run_at=trello_data.get('last_run_at'),
            sync_pending=trello_data.get('sync_pending', False),
        )

    return fm


def write_control_md(file_path: str, fm: ControlMdFrontmatter) -> None:
    """
    REQ-001: Write CONTROL.md with updated frontmatter.

    Preserves original document content.

    Args:
        file_path: Path to CONTROL.md
        fm: Frontmatter object to write
    """
    # Build frontmatter dict
    data = {
        'schema_version': fm.schema_version,
        'project_id': fm.project_id,
        'github_repo': fm.github_repo,
    }

    if fm.trello:
        data['trello'] = {
            'card_id': fm.trello.card_id,
            'card_url': fm.trello.card_url,
            'status': fm.trello.status,
            'created_at': fm.trello.created_at,
            'last_run_at': fm.trello.last_run_at,
            'sync_pending': fm.trello.sync_pending,
        }
        # Remove None values
        data['trello'] = {k: v for k, v in data['trello'].items() if v is not None}

    # Format YAML
    yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)

    # Write file
    path = Path(file_path)
    content = f"---\n{yaml_content}---\n{fm._original_content}"
    path.write_text(content)


def create_project_card(
    control_md_path: str,
    request_summary: str,
    list_id: str,
    label_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    REQ-002: Create Trello card for a new QRALPH project.

    Args:
        control_md_path: Path to CONTROL.md
        request_summary: Project request summary (first 280 chars used)
        list_id: Trello list ID to create card in
        label_ids: Optional list of label IDs to apply

    Returns:
        Result dict with success status and card data or error
    """
    # Parse existing CONTROL.md
    fm = parse_control_md(control_md_path)
    if not fm:
        return {'success': False, 'error': 'Could not parse CONTROL.md'}

    # Get GitHub repo
    github_repo = fm.github_repo or detect_github_repo()
    if not github_repo:
        return {'success': False, 'error': 'Could not detect GitHub repo'}

    fm.github_repo = github_repo

    # Build card title
    initials = get_repo_initials(github_repo)
    title = f"[Q:{initials}] {fm.project_id}"

    # Build card description
    summary = request_summary[:280] if len(request_summary) > 280 else request_summary
    github_link = f"https://github.com/{github_repo}/blob/main/.qralph/projects/{fm.project_id}/CONTROL.md"

    description = f"""**Project**: {fm.project_id}
**Repo**: {github_repo}

## Summary
{summary}

## Links
- [CONTROL.md]({github_link})

---
*Created: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}*
"""

    # Create card
    result = create_card(
        list_id=list_id,
        title=title,
        description=description,
        labels=','.join(label_ids) if label_ids else None,
    )

    if result['success']:
        # Update CONTROL.md with card info
        card_data = result['data']
        fm.trello = ControlMdFrontmatter.TrelloSection(
            card_id=card_data['id'],
            card_url=card_data['url'],
            status='open',
            created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            sync_pending=False,
        )
        write_control_md(control_md_path, fm)
        return {'success': True, 'data': card_data}
    else:
        # Mark as offline-pending
        fm.trello = ControlMdFrontmatter.TrelloSection(
            card_id='',
            card_url='',
            status='offline-pending',
            sync_pending=True,
        )
        write_control_md(control_md_path, fm)
        return {'success': False, 'error': result.get('error', 'Card creation failed'), 'offline_pending': True}


def update_card_with_run_summary(
    control_md_path: str,
    agents: List[str],
    findings: Dict[str, int],
    status: str,
    artifact_links: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    REQ-003: Update Trello card with run summary.

    Args:
        control_md_path: Path to CONTROL.md
        agents: List of agent names that participated
        findings: Dict with P0, P1, P2 counts
        status: Current implementation status
        artifact_links: Optional dict of artifact name -> URL

    Returns:
        Result dict with success status
    """
    fm = parse_control_md(control_md_path)
    if not fm or not fm.trello or not fm.trello.card_id:
        return {'success': False, 'error': 'Project not linked to Trello card'}

    # Build run summary
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    agents_str = ', '.join(agents)
    findings_str = ', '.join(f"{count} {level}" for level, count in findings.items())

    summary = f"""

### Run {timestamp}
- **Agents**: {agents_str}
- **Findings**: {findings_str}
- **Status**: {status}
"""

    if artifact_links:
        summary += "- **Artifacts**: " + ', '.join(
            f"[{name}]({url})" for name, url in artifact_links.items()
        ) + "\n"

    # Get current card to append to description
    card_result = get_card(fm.trello.card_id)
    if not card_result['success']:
        return card_result

    current_desc = card_result['data'].get('desc', '')

    # Check description length limit (12,000 chars)
    new_desc = current_desc + summary
    if len(new_desc) > 12000:
        # Trim oldest runs
        lines = new_desc.split('\n')
        run_starts = [i for i, line in enumerate(lines) if line.startswith('### Run ')]
        if len(run_starts) > 1:
            # Remove oldest run (second one, keep the header)
            start = run_starts[1]
            end = run_starts[2] if len(run_starts) > 2 else len(lines)
            del lines[start:end]
            lines.insert(start, '... (older runs omitted)')
            new_desc = '\n'.join(lines)

    # Update card
    result = update_card(fm.trello.card_id, description=new_desc)

    if result['success']:
        # Update last_run_at in CONTROL.md
        fm.trello.last_run_at = timestamp
        write_control_md(control_md_path, fm)

    return result


def check_card_status(control_md_path: str, timeout: int = 10) -> Dict[str, Any]:
    """
    REQ-004: Check if Trello card is closed.

    Args:
        control_md_path: Path to CONTROL.md
        timeout: API timeout in seconds

    Returns:
        Dict with card status and recommended action
    """
    fm = parse_control_md(control_md_path)
    if not fm or not fm.trello or not fm.trello.card_id:
        return {
            'success': True,
            'linked': False,
            'closed': False,
            'needs_action': False,
            'message': 'Project not linked to Trello card',
        }

    result = get_card(fm.trello.card_id)

    if not result['success']:
        error = result.get('error', '')
        if '404' in error:
            # Card was deleted
            return {
                'success': True,
                'linked': True,
                'closed': False,
                'deleted': True,
                'needs_action': True,
                'message': 'Trello card was deleted externally',
            }
        # API error - allow proceeding with warning
        return {
            'success': False,
            'linked': True,
            'error': error,
            'needs_action': False,
            'message': f'Could not check card status: {error}',
        }

    card_data = result['data']
    is_closed = card_data.get('closed', False)

    if is_closed:
        return {
            'success': True,
            'linked': True,
            'closed': True,
            'needs_action': True,
            'card_data': card_data,
            'message': f"Project {fm.project_id} was closed in Trello",
        }

    return {
        'success': True,
        'linked': True,
        'closed': False,
        'needs_action': False,
        'card_data': card_data,
    }


def close_project(control_md_path: str) -> Dict[str, Any]:
    """
    REQ-005: Close project and archive Trello card.

    Args:
        control_md_path: Path to CONTROL.md

    Returns:
        Result dict with success status
    """
    fm = parse_control_md(control_md_path)
    if not fm or not fm.trello or not fm.trello.card_id:
        return {'success': False, 'error': 'Project not linked to Trello card'}

    # Archive the card
    result = archive_card(fm.trello.card_id)

    if result['success']:
        # Update CONTROL.md status
        fm.trello.status = 'closed'
        write_control_md(control_md_path, fm)
        return {'success': True, 'message': f'Project {fm.project_id} closed'}

    return result


def reopen_project(control_md_path: str) -> Dict[str, Any]:
    """
    REQ-004: Reopen a closed project.

    Args:
        control_md_path: Path to CONTROL.md

    Returns:
        Result dict with success status
    """
    fm = parse_control_md(control_md_path)
    if not fm or not fm.trello or not fm.trello.card_id:
        return {'success': False, 'error': 'Project not linked to Trello card'}

    # Unarchive the card
    result = unarchive_card(fm.trello.card_id)

    if result['success']:
        # Update CONTROL.md status
        fm.trello.status = 'open'
        write_control_md(control_md_path, fm)
        return {'success': True, 'message': f'Project {fm.project_id} reopened'}

    return result


def sync_projects(projects_dir: str, list_id: str) -> Dict[str, Any]:
    """
    REQ-006: Sync local projects with Trello.

    Args:
        projects_dir: Path to .qralph/projects directory
        list_id: Trello list ID

    Returns:
        Sync report with local-only, trello-only, and synced counts
    """
    projects_path = Path(projects_dir)
    if not projects_path.exists():
        return {'success': False, 'error': f'Projects directory not found: {projects_dir}'}

    # Get all local projects
    local_projects = {}
    for control_md in projects_path.glob('*/CONTROL.md'):
        fm = parse_control_md(str(control_md))
        if fm:
            local_projects[fm.project_id] = {
                'path': str(control_md),
                'frontmatter': fm,
                'card_id': fm.trello.card_id if fm.trello else None,
            }

    # Get all Trello cards with [Q: prefix
    cards_result = get_all_cards(list_id, include_archived=False)
    if not cards_result['success']:
        return {'success': False, 'error': cards_result.get('error', 'Failed to get Trello cards')}

    trello_cards = {}
    for card in cards_result['data']:
        name = card.get('name', '')
        if name.startswith('[Q:'):
            # Extract project_id from title
            match = re.search(r'\[Q:\w+\]\s*(.+)', name)
            if match:
                project_id = match.group(1).strip()
                trello_cards[project_id] = card

    # Compare
    local_only = []
    trello_only = []
    synced = []
    status_mismatch = []

    for project_id, local_data in local_projects.items():
        if project_id in trello_cards:
            synced.append(project_id)
            # Check for status mismatch
            card = trello_cards[project_id]
            fm = local_data['frontmatter']
            if fm.trello:
                local_status = fm.trello.status
                trello_closed = card.get('closed', False)
                if (local_status == 'open' and trello_closed) or (local_status == 'closed' and not trello_closed):
                    status_mismatch.append({
                        'project_id': project_id,
                        'local_status': local_status,
                        'trello_closed': trello_closed,
                    })
        else:
            local_only.append(project_id)

    for project_id in trello_cards:
        if project_id not in local_projects:
            trello_only.append(project_id)

    return {
        'success': True,
        'summary': {
            'synced': len(synced),
            'local_only': len(local_only),
            'trello_only': len(trello_only),
            'status_mismatch': len(status_mismatch),
        },
        'local_only': local_only,
        'trello_only': trello_only,
        'synced': synced,
        'status_mismatch': status_mismatch,
    }


def recover_deleted_card(control_md_path: str, list_id: str, request_summary: str = "") -> Dict[str, Any]:
    """
    REQ-016: Recover from deleted Trello card.

    Args:
        control_md_path: Path to CONTROL.md
        list_id: Trello list ID for new card
        request_summary: Summary for new card

    Returns:
        Result dict with new card data
    """
    fm = parse_control_md(control_md_path)
    if not fm:
        return {'success': False, 'error': 'Could not parse CONTROL.md'}

    # Clear old trello metadata
    fm.trello = None
    write_control_md(control_md_path, fm)

    # Create new card
    return create_project_card(control_md_path, request_summary or f"Recovered: {fm.project_id}", list_id)


def git_commit_control_md(control_md_path: str, action: str) -> Dict[str, Any]:
    """
    REQ-009: Commit CONTROL.md changes after Trello operations.

    Args:
        control_md_path: Path to CONTROL.md
        action: Description of the action (e.g., "Created Trello card")

    Returns:
        Result dict with commit status
    """
    fm = parse_control_md(control_md_path)
    if not fm:
        return {'success': False, 'error': 'Could not parse CONTROL.md'}

    try:
        # Stage the file
        subprocess.run(
            ['git', 'add', control_md_path],
            capture_output=True,
            check=True,
            timeout=30
        )

        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            capture_output=True,
            timeout=30
        )

        if result.returncode == 0:
            # No changes to commit
            return {'success': True, 'message': 'No changes to commit'}

        # Build commit message
        commit_msg = f"""feat(qralph): {fm.project_id} - {action}

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"""

        # Commit
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            capture_output=True,
            check=True,
            timeout=30
        )

        return {'success': True, 'message': f'Committed: {action}'}

    except subprocess.CalledProcessError as e:
        return {'success': False, 'error': f'Git error: {e.stderr.decode() if e.stderr else str(e)}'}
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Git command timed out'}


if __name__ == "__main__":
    # Quick test
    print("Trello Integration Module")
    print("Use parse_control_md() to parse CONTROL.md files")
    print("Use create_project_card() to create Trello cards")
