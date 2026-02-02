#!/usr/bin/env python3
"""
Trello configuration management for QRALPH integration.
REQ-010: Configuration File

Validates and loads .qralph/trello-config.json configuration.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def get_config_path(base_path: Optional[str] = None) -> str:
    """
    Get the path to trello-config.json.

    Searches for .qralph/trello-config.json starting from base_path
    or current directory, walking up to find project root.
    """
    if base_path:
        start = Path(base_path)
    else:
        start = Path.cwd()

    # Walk up looking for .qralph directory
    current = start
    while current != current.parent:
        config_path = current / ".qralph" / "trello-config.json"
        if config_path.exists():
            return str(config_path)
        current = current.parent

    # Default to expected location
    return str(start / ".qralph" / "trello-config.json")


def validate_hex_id(value: str, field_name: str) -> None:
    """Validate that value is a 24-character hex string."""
    if not isinstance(value, str):
        raise ConfigValidationError(f"{field_name} must be a string")

    if len(value) != 24:
        raise ConfigValidationError(
            f"{field_name} must be 24 characters, got {len(value)}"
        )

    if not re.match(r'^[0-9a-fA-F]{24}$', value):
        raise ConfigValidationError(
            f"{field_name} must be a valid hex string"
        )


def validate_github_repo(value: str) -> None:
    """Validate that value matches owner/repo pattern."""
    if not isinstance(value, str):
        raise ConfigValidationError("github_repo must be a string")

    # Pattern: owner/repo (alphanumeric, hyphens, underscores allowed)
    pattern = r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$'
    if not re.match(pattern, value):
        raise ConfigValidationError(
            f"github_repo must match 'owner/repo' pattern, got '{value}'"
        )


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration dictionary.

    REQ-010 Validation Rules:
    - board_id and list_id: 24-character hex strings
    - cache_ttl_seconds: Positive integer
    - github_repo: Matches pattern owner/repo

    Raises:
        ConfigValidationError: If validation fails
    """
    # Required fields
    required = ["board_id", "list_id", "github_repo", "cache_ttl_seconds"]
    for field in required:
        if field not in config:
            raise ConfigValidationError(f"Missing required field: {field}")

    # Validate board_id
    validate_hex_id(config["board_id"], "board_id")

    # Validate list_id
    validate_hex_id(config["list_id"], "list_id")

    # Validate github_repo
    validate_github_repo(config["github_repo"])

    # Validate cache_ttl_seconds
    ttl = config["cache_ttl_seconds"]
    if not isinstance(ttl, int) or ttl <= 0:
        raise ConfigValidationError(
            f"cache_ttl_seconds must be a positive integer, got {ttl}"
        )

    # Labels are optional, but if present must be dict
    if "labels" in config and not isinstance(config["labels"], dict):
        raise ConfigValidationError("labels must be a dictionary")


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and validate Trello configuration.

    Args:
        config_path: Path to config file. If None, searches for it.

    Returns:
        Validated configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
        ConfigValidationError: If config validation fails
    """
    if config_path is None:
        config_path = get_config_path()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path, 'r') as f:
        config = json.load(f)

    validate_config(config)

    # Set defaults for optional fields
    config.setdefault("labels", {})

    return config


def get_repo_initials(github_repo: str) -> str:
    """
    Get initials from repo name for card title prefix.

    Examples:
        "sparkst/cardinal-health" -> "CH"
        "user/my-project" -> "MP"
        "org/simple" -> "S"
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
    try:
        config = load_config()
        print(f"Config loaded successfully:")
        print(f"  Board: {config['board_id']}")
        print(f"  List: {config['list_id']}")
        print(f"  Repo: {config['github_repo']}")
        print(f"  Initials: {get_repo_initials(config['github_repo'])}")
    except Exception as e:
        print(f"Error: {e}")
