#!/usr/bin/env python3
"""
GitHub repository detection for QRALPH integration.
REQ-012: GitHub Repo Context

Detects the GitHub repository from git remotes with fallback chain.
"""

import re
import subprocess
from typing import Optional
from pathlib import Path

# Import config loader from sibling module
try:
    from trello_config import load_config
except ImportError:
    # Handle case where module is run directly
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from trello_config import load_config


def run_git_command(cmd: list) -> Optional[str]:
    """
    Run a git command and return output or None on failure.

    Args:
        cmd: Command as list of strings (e.g., ["git", "remote", "-v"])

    Returns:
        Command output stripped of whitespace, or None on error
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return None


def parse_github_url(url: str) -> Optional[str]:
    """
    Parse a GitHub URL into owner/repo format.

    REQ-012: Supports multiple URL formats:
    - git@github.com:owner/repo.git → owner/repo
    - https://github.com/owner/repo.git → owner/repo
    - https://github.com/owner/repo → owner/repo

    Args:
        url: The remote URL to parse

    Returns:
        owner/repo string, or None if not a GitHub URL
    """
    if not url:
        return None

    # Pattern for SSH format: git@github.com:owner/repo.git
    ssh_pattern = r'^git@github\.com:([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$'
    match = re.match(ssh_pattern, url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"

    # Pattern for HTTPS format: https://github.com/owner/repo.git
    https_pattern = r'^https://github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+?)(?:\.git)?$'
    match = re.match(https_pattern, url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"

    return None


def get_repo_from_origin() -> Optional[str]:
    """
    REQ-012-002: Get repo from origin remote.

    Returns:
        owner/repo string from origin remote, or None if not available
    """
    url = run_git_command(["git", "remote", "get-url", "origin"])
    if url:
        return parse_github_url(url)
    return None


def get_repo_from_any_remote() -> Optional[str]:
    """
    REQ-012-003: Fallback to any available remote.

    Tries each remote in order until a GitHub repo is found.

    Returns:
        owner/repo string from first GitHub remote, or None
    """
    remotes_output = run_git_command(["git", "remote"])
    if not remotes_output:
        return None

    remotes = [r.strip() for r in remotes_output.split('\n') if r.strip()]

    for remote in remotes:
        url = run_git_command(["git", "remote", "get-url", remote])
        if url:
            repo = parse_github_url(url)
            if repo:
                return repo

    return None


def detect_github_repo() -> Optional[str]:
    """
    REQ-012-004: Detect GitHub repo with fallback chain.

    Fallback order:
    1. Try git remote get-url origin
    2. If fails, try first available remote
    3. If fails, use config default
    4. If no config, return None (caller should prompt user)

    Returns:
        owner/repo string, or None if detection failed
    """
    # Try origin first
    repo = get_repo_from_origin()
    if repo:
        return repo

    # Try any remote
    repo = get_repo_from_any_remote()
    if repo:
        return repo

    # Try config file
    try:
        config = load_config()
        if config.get("github_repo"):
            return config["github_repo"]
    except (FileNotFoundError, Exception):
        pass

    return None


def get_repo_initials(github_repo: str) -> str:
    """
    Get initials from repo name for card title prefix.

    REQ-002: Card title format uses repo initials.

    Examples:
        "sparkst/cardinal-health" -> "CH"
        "user/my-project" -> "MP"
        "org/simple" -> "S"

    Args:
        github_repo: Full repo path (owner/repo)

    Returns:
        Uppercase initials from repo name
    """
    # Get repo name (after /)
    repo_name = github_repo.split("/")[-1]

    # Split on hyphens and underscores
    parts = re.split(r'[-_]', repo_name)

    # Get first letter of each part, uppercase
    initials = ''.join(part[0].upper() for part in parts if part)

    return initials or repo_name[0].upper()


if __name__ == "__main__":
    # Quick test
    print("Testing GitHub repo detection...")

    repo = detect_github_repo()
    if repo:
        print(f"Detected repo: {repo}")
        print(f"Initials: {get_repo_initials(repo)}")
    else:
        print("Could not detect GitHub repo")

    # Test URL parsing
    test_urls = [
        "git@github.com:sparkst/cardinal-health.git",
        "https://github.com/sparkst/cardinal-health.git",
        "https://github.com/sparkst/cardinal-health",
        "https://gitlab.com/other/repo.git",
    ]

    print("\nURL parsing tests:")
    for url in test_urls:
        result = parse_github_url(url)
        print(f"  {url} -> {result}")
