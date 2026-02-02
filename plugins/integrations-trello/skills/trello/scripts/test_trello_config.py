#!/usr/bin/env python3
"""
Tests for Trello configuration validation.
REQ-010: Configuration File

Run with: python -m pytest trello-config.spec.py -v
"""

import json
import os
import tempfile
import pytest
from pathlib import Path

# Import the module under test (will be created)
import sys
sys.path.insert(0, str(Path(__file__).parent))

from trello_config import (
    load_config,
    validate_config,
    ConfigValidationError,
    get_config_path,
)


class TestConfigValidation:
    """REQ-010: Configuration file validation tests."""

    def test_valid_config_loads_successfully(self, tmp_path):
        """REQ-010-001: Valid config should load without errors."""
        config_file = tmp_path / "trello-config.json"
        config_file.write_text(json.dumps({
            "board_id": "6796a533657644663c573c66",
            "list_id": "697ff68d2bfe48c3ac61dc2a",
            "github_repo": "sparkst/cardinal-health",
            "labels": {
                "Automation": "6796a533657644663c573cb2"
            },
            "cache_ttl_seconds": 60
        }))

        config = load_config(str(config_file))

        assert config["board_id"] == "6796a533657644663c573c66"
        assert config["list_id"] == "697ff68d2bfe48c3ac61dc2a"
        assert config["github_repo"] == "sparkst/cardinal-health"
        assert config["cache_ttl_seconds"] == 60

    def test_board_id_must_be_24_char_hex(self, tmp_path):
        """REQ-010-002: board_id must be 24-character hex string."""
        config_file = tmp_path / "trello-config.json"
        config_file.write_text(json.dumps({
            "board_id": "invalid",  # Not 24 chars
            "list_id": "697ff68d2bfe48c3ac61dc2a",
            "github_repo": "owner/repo",
            "labels": {},
            "cache_ttl_seconds": 60
        }))

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        assert "board_id" in str(exc_info.value)

    def test_list_id_must_be_24_char_hex(self, tmp_path):
        """REQ-010-003: list_id must be 24-character hex string."""
        config_file = tmp_path / "trello-config.json"
        config_file.write_text(json.dumps({
            "board_id": "6796a533657644663c573c66",
            "list_id": "too-short",  # Not 24 chars
            "github_repo": "owner/repo",
            "labels": {},
            "cache_ttl_seconds": 60
        }))

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        assert "list_id" in str(exc_info.value)

    def test_github_repo_must_match_pattern(self, tmp_path):
        """REQ-010-004: github_repo must match owner/repo pattern."""
        config_file = tmp_path / "trello-config.json"
        config_file.write_text(json.dumps({
            "board_id": "6796a533657644663c573c66",
            "list_id": "697ff68d2bfe48c3ac61dc2a",
            "github_repo": "invalid-format",  # Missing /
            "labels": {},
            "cache_ttl_seconds": 60
        }))

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        assert "github_repo" in str(exc_info.value)

    def test_cache_ttl_must_be_positive_integer(self, tmp_path):
        """REQ-010-005: cache_ttl_seconds must be positive integer."""
        config_file = tmp_path / "trello-config.json"
        config_file.write_text(json.dumps({
            "board_id": "6796a533657644663c573c66",
            "list_id": "697ff68d2bfe48c3ac61dc2a",
            "github_repo": "owner/repo",
            "labels": {},
            "cache_ttl_seconds": -1  # Negative
        }))

        with pytest.raises(ConfigValidationError) as exc_info:
            load_config(str(config_file))

        assert "cache_ttl_seconds" in str(exc_info.value)

    def test_missing_config_file_raises_error(self):
        """REQ-010-006: Missing config file should raise clear error."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/trello-config.json")

    def test_invalid_json_raises_error(self, tmp_path):
        """REQ-010-007: Invalid JSON should raise clear error."""
        config_file = tmp_path / "trello-config.json"
        config_file.write_text("not valid json {")

        with pytest.raises(json.JSONDecodeError):
            load_config(str(config_file))

    def test_labels_are_optional(self, tmp_path):
        """REQ-010-008: Labels section is optional."""
        config_file = tmp_path / "trello-config.json"
        config_file.write_text(json.dumps({
            "board_id": "6796a533657644663c573c66",
            "list_id": "697ff68d2bfe48c3ac61dc2a",
            "github_repo": "owner/repo",
            "cache_ttl_seconds": 60
            # No labels key
        }))

        config = load_config(str(config_file))
        assert config.get("labels", {}) == {}


class TestConfigPath:
    """Tests for config path resolution."""

    def test_get_config_path_returns_qralph_path(self, tmp_path, monkeypatch):
        """Config should be in .qralph/trello-config.json."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".qralph").mkdir()

        path = get_config_path()

        assert path.endswith(".qralph/trello-config.json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
