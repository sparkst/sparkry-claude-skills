#!/usr/bin/env python3
"""
Google Docs Publisher

Publish markdown content to Google Docs via n8n webhook with registry management.

Usage:
    python publish-to-google-docs.py --file <path> --category <category> [--mode <mode>] [--force-new] [--dry-run]

Output (JSON):
    {
      "success": true,
      "doc_id": "1a2b3c4d5e6f...",
      "doc_url": "https://docs.google.com/document/d/...",
      "doc_name": "Substack: Article Title",
      "operation": "created|updated",
      "mode": "overwrite|append",
      "file_path": "content/articles/week-02/W02-THU-article.md"
    }
"""

import json
import sys
import argparse
import time
import re
import os
from base64 import b64encode
from pathlib import Path
from typing import Dict, Any, Optional
import urllib.request
import urllib.error

# Webhook endpoint
WEBHOOK_URL = "https://n8n.sparkry.ai/webhook/cru-google-doc"

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


def get_existing_doc_id(registry: Dict[str, Any], file_path: str) -> Optional[str]:
    """Get existing doc_id from registry for file path."""
    return registry.get("articles", {}).get(file_path, {}).get("doc_id")


def extract_title_from_markdown(content: str, file_path: str) -> str:
    """Extract title from markdown content (first H1) or use filename."""
    # Try to find first H1
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    # Fallback to filename
    return Path(file_path).stem


def get_auth_header() -> Optional[str]:
    """
    Get authentication header from environment or config.

    Uses same mechanism as webhook-sender.py:
    - CLAUDE_WEBHOOK_AUTH env var with base64-encoded credentials, or
    - ~/.claude/config.json (base64_auth or username/password)
    """
    # Try environment variable first
    auth = os.getenv("CLAUDE_WEBHOOK_AUTH")
    if auth:
        return f"Basic {auth}"

    # Try config file
    config_path = Path.home() / ".claude" / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)

                # Check for pre-encoded base64 auth
                base64_auth = config.get("webhook", {}).get("base64_auth", "")
                if base64_auth and base64_auth != "PASTE_YOUR_BASE64_CREDENTIAL_HERE":
                    return f"Basic {base64_auth}"

                # Fall back to username/password (config keys, not hardcoded credentials)
                username = config.get("webhook", {}).get("username", "")
                password = config.get("webhook", {}).get("password", "")
                if username and password:
                    credentials = f"{username}:{password}"
                    encoded = b64encode(credentials.encode()).decode()
                    return f"Basic {encoded}"
        except Exception as e:
            print(json.dumps({
                "warning": f"Failed to read config: {e}"
            }), file=sys.stderr)

    return None


def call_webhook(doc_id: Optional[str], doc_name: str, content: str, mode: str, retries: int = 3) -> Dict[str, Any]:
    """Call n8n webhook with exponential backoff retry logic."""
    payload = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "content": content,
        "mode": mode
    }

    # Get authentication
    auth_header = get_auth_header()
    headers = {'Content-Type': 'application/json'}
    if auth_header:
        headers['Authorization'] = auth_header

    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                WEBHOOK_URL,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                return response_data

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else "No error body"
            if attempt < retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(json.dumps({
                    "warning": f"HTTP {e.code} error, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})",
                    "error_body": error_body
                }), file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise Exception(f"HTTP {e.code} error after {retries} attempts: {error_body}")

        except urllib.error.URLError as e:
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                print(json.dumps({
                    "warning": f"Network error, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})",
                    "error": str(e)
                }), file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise Exception(f"Network error after {retries} attempts: {e}")

        except Exception as e:
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                print(json.dumps({
                    "warning": f"Unexpected error, retrying in {wait_time}s... (attempt {attempt + 1}/{retries})",
                    "error": str(e)
                }), file=sys.stderr)
                time.sleep(wait_time)
            else:
                raise

    raise Exception(f"Failed to call webhook after {retries} attempts")


def publish_to_google_docs(
    file_path: str,
    category: str,
    mode: str = "overwrite",
    force_new: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Publish markdown content to Google Docs via n8n webhook.

    Args:
        file_path: Path to markdown file
        category: Category prefix (Substack, LinkedIn, etc.)
        mode: Update mode (overwrite or append)
        force_new: Force create new doc even if registry entry exists
        dry_run: Show what would be published without sending

    Returns:
        Dict with success, doc_id, doc_url, doc_name, operation, mode, file_path
    """
    # Validate file exists
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Read markdown content
    with open(file_path_obj, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract title
    title = extract_title_from_markdown(content, file_path)
    doc_name = f"{category}: {title}"

    # Load registry
    registry = load_registry()

    # Check for existing doc_id
    existing_doc_id = None if force_new else get_existing_doc_id(registry, file_path)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "doc_id": existing_doc_id or "NEW",
            "doc_name": doc_name,
            "operation": "update" if existing_doc_id else "create",
            "mode": mode,
            "file_path": file_path,
            "content_length": len(content)
        }

    # Call webhook
    try:
        response = call_webhook(existing_doc_id, doc_name, content, mode)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "file_path": file_path
        }

    # Update registry
    if file_path not in registry["articles"]:
        # New entry
        registry["articles"][file_path] = {
            "doc_id": response["doc_id"],
            "doc_url": response["doc_url"],
            "doc_name": response["doc_name"],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": category,
            "version": 1
        }
    else:
        # Update existing entry
        registry["articles"][file_path]["doc_id"] = response["doc_id"]
        registry["articles"][file_path]["doc_url"] = response["doc_url"]
        registry["articles"][file_path]["doc_name"] = response["doc_name"]
        registry["articles"][file_path]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        registry["articles"][file_path]["category"] = category
        registry["articles"][file_path]["version"] = registry["articles"][file_path].get("version", 1) + 1

    save_registry(registry)

    return {
        "success": True,
        "doc_id": response["doc_id"],
        "doc_url": response["doc_url"],
        "doc_name": response["doc_name"],
        "operation": response.get("operation", "updated" if existing_doc_id else "created"),
        "mode": mode,
        "file_path": file_path
    }


def main():
    parser = argparse.ArgumentParser(
        description="Publish markdown content to Google Docs via n8n webhook"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to markdown file"
    )
    parser.add_argument(
        "--category",
        required=True,
        help="Category prefix (Substack, LinkedIn, etc.)"
    )
    parser.add_argument(
        "--mode",
        choices=["overwrite", "append"],
        default="overwrite",
        help="Update mode (default: overwrite)"
    )
    parser.add_argument(
        "--force-new",
        action="store_true",
        help="Force create new doc even if registry entry exists"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be published without sending"
    )

    args = parser.parse_args()

    try:
        result = publish_to_google_docs(
            file_path=args.file,
            category=args.category,
            mode=args.mode,
            force_new=args.force_new,
            dry_run=args.dry_run
        )

        print(json.dumps(result, indent=2))

        if not result.get("success", False):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
