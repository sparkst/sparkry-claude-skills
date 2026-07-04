"""Skill self-version-check for ai-review-toolkit.

The SKILLs (qreview/qloop/qpipeline) run `version-check.py check` at start. It
compares the locally-installed plugin version against the latest published on the
marketplace `main` and, when behind, prints a one-line upgrade notice with the
right command for the install kind. Best-effort: rate-limited to ~once/day via a
cache stamp, and fails silent-and-open on any network/parse error so it can never
block or slow a real run.

Pure logic (parse/compare/notice/cache/detect) is unit-tested; the CLI does the
I/O (read local version, fetch remote, read/write the stamp).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

RAW_MARKETPLACE_URL = (
    "https://raw.githubusercontent.com/sparkst/sparkry-claude-skills/main/.claude-plugin/marketplace.json"
)
CACHE_TTL_SECONDS = 86_400  # check the network at most once/day
STAMP_PATH = os.path.expanduser("~/.cache/ai-review-toolkit/version-check.json")


def parse_semver(value: str) -> tuple[int, int, int]:
    """Parse 'v1.6.0' / '1.5' / '2' → (major, minor, patch), zero-padded."""
    cleaned = value.strip().lstrip("vV")
    parts = (cleaned.split(".") + ["0", "0", "0"])[:3]
    out: list[int] = []
    for p in parts:
        digits = "".join(ch for ch in p if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return (out[0], out[1], out[2])


def compare_versions(local: str, remote: str) -> str:
    """'behind' | 'ahead' | 'equal' — local relative to remote."""
    lo, re = parse_semver(local), parse_semver(remote)
    if lo < re:
        return "behind"
    if lo > re:
        return "ahead"
    return "equal"


def upgrade_notice(local: str, remote: str, install_kind: str) -> str | None:
    """One-line notice when local is behind remote, else None."""
    if compare_versions(local, remote) != "behind":
        return None
    head = f"ai-review-toolkit {remote} is available (you have {local})."
    if install_kind == "fork":
        return (
            f"{head} Your install is a manual fork — upgrade by running "
            f"`python3 <marketplace>/plugins/ai-review-toolkit/tools/fork-sync.py` "
            f"(add --dry-run first to preview)."
        )
    return f"{head} Run `/plugin marketplace update` then update ai-review-toolkit to upgrade."


def cache_is_fresh(stamp_epoch: float | None, now_epoch: float, ttl: int = CACHE_TTL_SECONDS) -> bool:
    """True if a network check happened within `ttl` seconds of `now`."""
    if stamp_epoch is None:
        return False
    return (now_epoch - stamp_epoch) < ttl


def detect_install_kind(tool_path: str) -> str:
    """'marketplace' if the tool lives under a marketplaces/ install, else 'fork'."""
    return "marketplace" if "/plugins/marketplaces/" in tool_path else "fork"


# ---------------------------------------------------------------------------
# I/O (CLI only)
# ---------------------------------------------------------------------------

def _local_version(tool_path: str) -> str:
    """Installed version. Marketplace layout: tools/ → ../.claude-plugin/plugin.json.
    Flat fork layout: a sibling VERSION file (stamped by fork-sync). '' if neither."""
    tool_dir = os.path.dirname(os.path.abspath(tool_path))
    plugin_json = os.path.join(os.path.dirname(tool_dir), ".claude-plugin", "plugin.json")
    try:
        with open(plugin_json, "r", encoding="utf-8") as fh:
            return str(json.load(fh).get("version", ""))
    except Exception:
        pass
    try:  # flat fork: sibling VERSION file
        with open(os.path.join(tool_dir, "VERSION"), "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except Exception:
        return ""


def _remote_version(timeout: float = 3.0) -> str | None:
    import urllib.request
    try:
        with urllib.request.urlopen(RAW_MARKETPLACE_URL, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        entry = next((p for p in data.get("plugins", []) if p.get("name") == "ai-review-toolkit"), {})
        return str(entry.get("version", "")) or None
    except Exception:
        return None  # fail-open: never block a run on a network hiccup


def _read_stamp() -> dict[str, Any]:
    try:
        with open(STAMP_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _write_stamp(now_epoch: float, remote: str | None) -> None:
    try:
        os.makedirs(os.path.dirname(STAMP_PATH), exist_ok=True)
        with open(STAMP_PATH, "w", encoding="utf-8") as fh:
            json.dump({"checked_at": now_epoch, "remote": remote}, fh)
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ai-review-toolkit self-version-check (best-effort).")
    parser.add_argument("command", nargs="?", default="check", choices=["check"])
    parser.add_argument("--force", action="store_true", help="Ignore the 24h cache and re-check now")
    args = parser.parse_args(argv)

    try:
        now = time.time()
        local = _local_version(__file__)
        if not local:
            return 0  # can't determine local version → say nothing
        install_kind = detect_install_kind(os.path.abspath(__file__))

        stamp = _read_stamp()
        if not args.force and cache_is_fresh(stamp.get("checked_at"), now):
            remote = stamp.get("remote")  # reuse the cached remote; no network
        else:
            remote = _remote_version()
            _write_stamp(now, remote)

        if not remote:
            return 0  # unknown remote → say nothing (fail-open)

        notice = upgrade_notice(local, remote, install_kind)
        if notice:
            print(notice)
    except Exception:
        return 0  # best-effort: never let the check break or slow a real run
    return 0


if __name__ == "__main__":
    sys.exit(main())
