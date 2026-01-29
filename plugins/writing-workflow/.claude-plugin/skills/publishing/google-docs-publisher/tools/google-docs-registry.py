#!/usr/bin/env python3
"""
Google Docs Registry Manager

CRUD operations for doc_id registry with backup management.

Usage:
    python google-docs-registry.py --action <action> [options]

Actions:
    get     - Retrieve doc_id for file path
    set     - Store/update doc_id mapping
    delete  - Remove registry entry
    list    - List all registered docs
    search  - Search by doc_id, doc_name, or category

Output (JSON):
    {
      "action": "get",
      "success": true,
      "data": {...}
    }
"""

import json
import sys
import argparse
import time
from pathlib import Path
from typing import Dict, Any, Optional, List


# Registry paths
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
REGISTRY_PATH = SKILL_DIR / "references" / "google-docs-registry.json"


def load_registry() -> Dict[str, Any]:
    """Load registry from JSON file."""
    if not REGISTRY_PATH.exists():
        return {
            "articles": {},
            "schema_version": "1.0",
            "last_updated": None
        }

    try:
        with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "error": f"Registry corrupted: {e}",
            "action": "Attempting to restore from backup"
        }), file=sys.stderr)
        return restore_registry_from_backup()


def restore_registry_from_backup() -> Dict[str, Any]:
    """Restore registry from most recent backup."""
    backup_dir = REGISTRY_PATH.parent
    backups = sorted(backup_dir.glob("google-docs-registry.json.backup_*"), reverse=True)

    for backup in backups:
        try:
            with open(backup, 'r', encoding='utf-8') as f:
                registry = json.load(f)
                print(json.dumps({
                    "info": f"Restored registry from backup: {backup.name}"
                }), file=sys.stderr)
                return registry
        except json.JSONDecodeError:
            continue

    # No valid backup found, initialize empty
    print(json.dumps({
        "warning": "No valid backup found, initializing empty registry"
    }), file=sys.stderr)
    return {
        "articles": {},
        "schema_version": "1.0",
        "last_updated": None
    }


def save_registry(registry: Dict[str, Any]) -> None:
    """Save registry to JSON file with backup."""
    # Create backup if registry exists
    if REGISTRY_PATH.exists():
        backup_name = f"google-docs-registry.json.backup_{time.strftime('%Y%m%d_%H%M%S')}"
        backup_path = REGISTRY_PATH.parent / backup_name

        with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(backup_content)

        # Clean old backups (keep last 10)
        backups = sorted(REGISTRY_PATH.parent.glob("google-docs-registry.json.backup_*"), reverse=True)
        for old_backup in backups[10:]:
            old_backup.unlink()

    # Update last_updated timestamp
    registry["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Save registry
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
        json.dump(registry, f, indent=2)


def action_get(file_path: str) -> Dict[str, Any]:
    """Get entry for file path."""
    registry = load_registry()
    entry = registry.get("articles", {}).get(file_path)

    if entry:
        return {
            "action": "get",
            "success": True,
            "file_path": file_path,
            "data": entry
        }
    else:
        return {
            "action": "get",
            "success": False,
            "file_path": file_path,
            "error": "No registry entry found for this file"
        }


def action_set(
    file_path: str,
    doc_id: str,
    doc_url: str,
    doc_name: str,
    category: str
) -> Dict[str, Any]:
    """Set/update entry for file path."""
    registry = load_registry()

    is_new = file_path not in registry.get("articles", {})

    if is_new:
        # New entry
        registry.setdefault("articles", {})[file_path] = {
            "doc_id": doc_id,
            "doc_url": doc_url,
            "doc_name": doc_name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": category,
            "version": 1
        }
    else:
        # Update existing entry
        entry = registry["articles"][file_path]
        entry["doc_id"] = doc_id
        entry["doc_url"] = doc_url
        entry["doc_name"] = doc_name
        entry["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        entry["category"] = category
        entry["version"] = entry.get("version", 1) + 1

    save_registry(registry)

    return {
        "action": "set",
        "success": True,
        "file_path": file_path,
        "operation": "created" if is_new else "updated",
        "data": registry["articles"][file_path]
    }


def action_delete(file_path: str) -> Dict[str, Any]:
    """Delete entry for file path."""
    registry = load_registry()

    if file_path in registry.get("articles", {}):
        deleted_entry = registry["articles"].pop(file_path)
        save_registry(registry)

        return {
            "action": "delete",
            "success": True,
            "file_path": file_path,
            "deleted_entry": deleted_entry
        }
    else:
        return {
            "action": "delete",
            "success": False,
            "file_path": file_path,
            "error": "No registry entry found for this file"
        }


def action_list() -> Dict[str, Any]:
    """List all registry entries."""
    registry = load_registry()
    articles = registry.get("articles", {})

    return {
        "action": "list",
        "success": True,
        "count": len(articles),
        "articles": articles
    }


def action_search(category: Optional[str] = None, query: Optional[str] = None) -> Dict[str, Any]:
    """Search registry by category or query."""
    registry = load_registry()
    articles = registry.get("articles", {})

    results = {}

    for file_path, entry in articles.items():
        match = True

        # Filter by category
        if category and entry.get("category") != category:
            match = False

        # Filter by query (search in file_path, doc_name, doc_id)
        if query:
            query_lower = query.lower()
            if not any([
                query_lower in file_path.lower(),
                query_lower in entry.get("doc_name", "").lower(),
                query_lower in entry.get("doc_id", "").lower()
            ]):
                match = False

        if match:
            results[file_path] = entry

    return {
        "action": "search",
        "success": True,
        "count": len(results),
        "filters": {
            "category": category,
            "query": query
        },
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(
        description="Google Docs Registry Manager - CRUD operations for doc_id registry"
    )
    parser.add_argument(
        "--action",
        required=True,
        choices=["get", "set", "delete", "list", "search"],
        help="Registry operation"
    )

    # Arguments for get, set, delete
    parser.add_argument(
        "--file",
        help="File path (for get/set/delete)"
    )

    # Arguments for set
    parser.add_argument(
        "--doc-id",
        help="Google Doc ID (for set)"
    )
    parser.add_argument(
        "--doc-url",
        help="Google Doc URL (for set)"
    )
    parser.add_argument(
        "--doc-name",
        help="Document name (for set)"
    )
    parser.add_argument(
        "--category",
        help="Category (for set/search)"
    )

    # Arguments for search
    parser.add_argument(
        "--query",
        help="Search query (for search)"
    )

    args = parser.parse_args()

    try:
        if args.action == "get":
            if not args.file:
                raise ValueError("--file required for 'get' action")
            result = action_get(args.file)

        elif args.action == "set":
            if not all([args.file, args.doc_id, args.doc_url, args.doc_name, args.category]):
                raise ValueError("--file, --doc-id, --doc-url, --doc-name, --category required for 'set' action")
            result = action_set(
                args.file,
                args.doc_id,
                args.doc_url,
                args.doc_name,
                args.category
            )

        elif args.action == "delete":
            if not args.file:
                raise ValueError("--file required for 'delete' action")
            result = action_delete(args.file)

        elif args.action == "list":
            result = action_list()

        elif args.action == "search":
            result = action_search(args.category, args.query)

        else:
            raise ValueError(f"Unknown action: {args.action}")

        print(json.dumps(result, indent=2))

        if not result.get("success", False):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "action": args.action,
            "success": False,
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
