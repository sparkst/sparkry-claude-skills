#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
QRALPH v6.0 Configuration — detect research tools, save preferences.

Commands:
    python3 .qralph/tools/qralph-config.py setup     # Interactive first-run setup
    python3 .qralph/tools/qralph-config.py detect     # Return detected tools as JSON (no interaction)
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Import shared state module
import importlib.util
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

PROJECT_ROOT = Path.cwd()
QRALPH_DIR = PROJECT_ROOT / ".qralph"
CONFIG_FILE = QRALPH_DIR / "config.json"

CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# Known research MCP plugins and how to identify them
KNOWN_RESEARCH_PLUGINS = {
    "context7": {
        "patterns": ["context7"],
        "category": "library_docs",
        "description": "Library documentation via Context7 MCP",
    },
    "tavily": {
        "patterns": ["tavily"],
        "category": "web_research",
        "description": "Web research via Tavily MCP",
    },
    "brave_search": {
        "patterns": ["brave-search", "brave_search"],
        "category": "web_research",
        "description": "Web search via Brave Search MCP",
    },
    "perplexity": {
        "patterns": ["perplexity"],
        "category": "web_research",
        "description": "AI-powered search via Perplexity MCP",
    },
}

# Built-in tools always available in Claude Code
BUILTIN_TOOLS = ["web_search", "web_fetch"]

DEFAULT_RESEARCH_PRIORITY = {
    "library_docs": ["context7", "web_search"],
    "web_research": ["tavily", "brave_search", "web_search"],
    "fallback": "web_search",
}


def detect_plugins() -> list[str]:
    """Read ~/.claude/settings.json and detect enabled research plugins."""
    if not CLAUDE_SETTINGS_PATH.exists():
        return []

    try:
        settings = json.loads(CLAUDE_SETTINGS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []

    enabled = settings.get("enabledPlugins", [])
    if not isinstance(enabled, list):
        return []

    detected = []
    for plugin_name in enabled:
        if not isinstance(plugin_name, str):
            continue
        plugin_lower = plugin_name.lower()
        for tool_id, info in KNOWN_RESEARCH_PLUGINS.items():
            if any(pattern in plugin_lower for pattern in info["patterns"]):
                if tool_id not in detected:
                    detected.append(tool_id)

    return detected


def build_research_priority(detected: list[str]) -> dict:
    """Build research tool priority tree based on detected plugins."""
    priority = {}

    for category, defaults in DEFAULT_RESEARCH_PRIORITY.items():
        if category == "fallback":
            priority["fallback"] = defaults
            continue
        if isinstance(defaults, list):
            available = [t for t in defaults if t in detected or t in BUILTIN_TOOLS]
            if not available:
                available = ["web_search"]
            priority[category] = available

    return priority


def cmd_detect() -> dict:
    """Detect available research tools without interaction."""
    plugins = detect_plugins()
    all_tools = plugins + BUILTIN_TOOLS

    result = {
        "detected_plugins": plugins,
        "builtin_tools": BUILTIN_TOOLS,
        "all_available": all_tools,
        "research_priority": build_research_priority(plugins),
    }
    return result


def cmd_setup() -> dict:
    """Interactive first-run setup — detect tools, write config."""
    detection = cmd_detect()

    config = {
        "version": "6.0.0",
        "research_tools": detection["research_priority"],
        "detected": detection["all_available"],
        "detected_plugins": detection["detected_plugins"],
        "configured_at": datetime.now().isoformat(),
    }

    QRALPH_DIR.mkdir(parents=True, exist_ok=True)
    qralph_state.safe_write_json(CONFIG_FILE, config)

    result = {
        "status": "configured",
        "config_path": str(CONFIG_FILE),
        "detected": detection["all_available"],
        "research_priority": detection["research_priority"],
    }
    return result


_ALLOWED_DETECTED = frozenset(KNOWN_RESEARCH_PLUGINS.keys()) | frozenset(BUILTIN_TOOLS)


def _validate_config(config: dict) -> dict:
    """Strip unknown keys and enforce expected types."""
    detected = config.get("detected", [])
    if not isinstance(detected, list):
        detected = []
    config["detected"] = [t for t in detected if isinstance(t, str) and t in _ALLOWED_DETECTED]
    return config


def load_config() -> dict:
    """Load existing config with validation, or return empty dict."""
    raw = qralph_state.safe_read_json(CONFIG_FILE, {})
    return _validate_config(raw) if raw else {}


def main():
    if len(sys.argv) < 2:
        print("Usage: qralph-config.py <setup|detect>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "detect":
        result = cmd_detect()
        print(json.dumps(result, indent=2))
    elif command == "setup":
        result = cmd_setup()
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
