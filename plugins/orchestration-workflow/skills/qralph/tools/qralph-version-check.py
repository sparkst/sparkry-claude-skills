#!/usr/bin/env python3
"""QRALPH version check — ensures the project uses the latest installed plugin version.

Compares:
  1. Plugin cache version (~/.claude/plugins/cache/sparkry-claude-skills/orchestration-workflow/<latest>/)
  2. Project-local SKILL.md (.claude/skills/project-orchestration/qralph/SKILL.md)
  3. Project VERSION file (.qralph/VERSION)

Usage:
  python3 .qralph/tools/qralph-version-check.py check
  python3 .qralph/tools/qralph-version-check.py sync       # Copy cache -> project-local
  python3 .qralph/tools/qralph-version-check.py --json      # Machine-readable output
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

PLUGIN_CACHE_BASE = Path.home() / ".claude" / "plugins" / "cache" / "sparkry-claude-skills" / "orchestration-workflow"
PLUGIN_NAME = "orchestration-workflow"
SKILL_SUBPATH = Path("skills") / "qralph"


def find_project_root() -> Path:
    """Walk up from CWD to find .qralph/ directory."""
    p = Path.cwd()
    while p != p.parent:
        if (p / ".qralph").is_dir():
            return p
        p = p.parent
    return Path.cwd()


def parse_semver(v: str) -> tuple:
    """Parse version string into comparable tuple."""
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", v.strip())
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def get_cache_latest() -> dict:
    """Find the latest version in the plugin cache."""
    if not PLUGIN_CACHE_BASE.is_dir():
        return {"version": None, "path": None, "error": "Plugin cache not found"}

    versions = []
    for d in PLUGIN_CACHE_BASE.iterdir():
        if d.is_dir() and re.match(r"\d+\.\d+\.\d+", d.name):
            versions.append((parse_semver(d.name), d.name, d))

    if not versions:
        return {"version": None, "path": None, "error": "No versions in cache"}

    versions.sort(reverse=True)
    best = versions[0]
    return {"version": best[1], "path": str(best[2]), "error": None}


def get_project_version(project_root: Path) -> dict:
    """Read the project's .qralph/VERSION file."""
    vfile = project_root / ".qralph" / "VERSION"
    if not vfile.is_file():
        return {"version": None, "path": str(vfile), "error": "VERSION file not found"}
    version = vfile.read_text().strip()
    return {"version": version, "path": str(vfile), "error": None}


def get_project_local_skill(project_root: Path) -> dict:
    """Check the project-local SKILL.md copy."""
    skill_dir = project_root / ".claude" / "skills" / "project-orchestration" / "qralph"
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        return {"exists": False, "path": str(skill_file), "version": None, "hash": None}

    content = skill_file.read_text()
    m = re.search(r"# QRALPH v(\d+\.\d+\.\d+)", content)
    version = m.group(1) if m else None
    h = hashlib.sha256(content.encode()).hexdigest()[:12]
    return {"exists": True, "path": str(skill_file), "version": version, "hash": h}


def get_cache_skill_hash(cache_path: str) -> str | None:
    """Hash the cache SKILL.md for comparison."""
    if not cache_path:
        return None
    skill_file = Path(cache_path) / SKILL_SUBPATH / "SKILL.md"
    if not skill_file.is_file():
        return None
    return hashlib.sha256(skill_file.read_text().encode()).hexdigest()[:12]


def check(project_root: Path, as_json: bool = False) -> dict:
    """Run version check and return status."""
    cache = get_cache_latest()
    project_ver = get_project_version(project_root)
    local_skill = get_project_local_skill(project_root)
    cache_hash = get_cache_skill_hash(cache.get("path"))

    result = {
        "cache_version": cache["version"],
        "cache_path": cache["path"],
        "project_version": project_ver["version"],
        "local_skill_version": local_skill["version"],
        "local_skill_exists": local_skill["exists"],
        "local_skill_path": local_skill["path"],
        "cache_skill_hash": cache_hash,
        "local_skill_hash": local_skill.get("hash"),
        "status": "unknown",
        "actions": [],
    }

    # Determine status
    if cache["error"]:
        result["status"] = "error"
        result["error"] = cache["error"]
        return result

    if not cache["version"]:
        result["status"] = "error"
        result["error"] = "No cached version found"
        return result

    issues = []

    # Check VERSION file vs cache
    if project_ver["version"] and parse_semver(project_ver["version"]) < parse_semver(cache["version"]):
        issues.append(f".qralph/VERSION ({project_ver['version']}) is behind cache ({cache['version']})")
        result["actions"].append("update_version_file")

    # Check local SKILL.md vs cache
    if local_skill["exists"]:
        if local_skill["version"] and parse_semver(local_skill["version"]) < parse_semver(cache["version"]):
            issues.append(f"Project-local SKILL.md ({local_skill['version']}) is behind cache ({cache['version']})")
            result["actions"].append("sync_skill")
        elif cache_hash and local_skill["hash"] and cache_hash != local_skill["hash"]:
            issues.append(f"Project-local SKILL.md content differs from cache (same version, different hash)")
            result["actions"].append("sync_skill")

    if not issues:
        result["status"] = "current"
    else:
        result["status"] = "outdated"
        result["issues"] = issues

    return result


def sync(project_root: Path) -> dict:
    """Sync cache -> project-local skill files."""
    cache = get_cache_latest()
    if cache["error"] or not cache["path"]:
        return {"success": False, "error": cache.get("error", "No cache path")}

    cache_skill_dir = Path(cache["path"]) / SKILL_SUBPATH
    local_skill_dir = project_root / ".claude" / "skills" / "project-orchestration" / "qralph"
    version_file = project_root / ".qralph" / "VERSION"

    synced = []

    # Sync SKILL.md
    src = cache_skill_dir / "SKILL.md"
    dst = local_skill_dir / "SKILL.md"
    if src.is_file():
        local_skill_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        synced.append(str(dst))

    # Sync tools
    cache_tools = cache_skill_dir / "tools"
    local_tools = project_root / ".qralph" / "tools"
    if cache_tools.is_dir():
        local_tools.mkdir(parents=True, exist_ok=True)
        for f in cache_tools.iterdir():
            if f.is_file() and f.suffix == ".py":
                shutil.copy2(str(f), str(local_tools / f.name))
                synced.append(str(local_tools / f.name))

    # Sync templates
    cache_templates = cache_skill_dir / "templates"
    local_templates = project_root / ".qralph" / "templates"
    if cache_templates.is_dir():
        local_templates.mkdir(parents=True, exist_ok=True)
        for f in cache_templates.iterdir():
            if f.is_file():
                shutil.copy2(str(f), str(local_templates / f.name))
                synced.append(str(local_templates / f.name))

    # Update VERSION
    if cache["version"]:
        version_file.write_text(cache["version"] + "\n")
        synced.append(str(version_file))

    return {"success": True, "version": cache["version"], "synced_files": synced}


def main():
    parser = argparse.ArgumentParser(description="QRALPH version check")
    parser.add_argument("command", nargs="?", default="check", choices=["check", "sync"])
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    project_root = find_project_root()

    if args.command == "check":
        result = check(project_root, as_json=args.json)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "current":
                print(f"QRALPH v{result['cache_version']} — project is current.")
            elif result["status"] == "outdated":
                print(f"QRALPH UPDATE AVAILABLE")
                print(f"  Cache:   v{result['cache_version']} ({result['cache_path']})")
                print(f"  Project: v{result['project_version'] or 'unknown'}")
                if result.get("local_skill_exists"):
                    print(f"  Local SKILL.md: v{result['local_skill_version'] or 'unknown'} (hash: {result['local_skill_hash']})")
                for issue in result.get("issues", []):
                    print(f"  ! {issue}")
                print(f"\nRun: python3 .qralph/tools/qralph-version-check.py sync")
            elif result["status"] == "error":
                print(f"ERROR: {result.get('error', 'unknown')}")
            sys.exit(0 if result["status"] == "current" else 1)

    elif args.command == "sync":
        result = sync(project_root)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Synced to v{result['version']}")
                for f in result["synced_files"]:
                    print(f"  -> {f}")
            else:
                print(f"Sync failed: {result['error']}")
            sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
