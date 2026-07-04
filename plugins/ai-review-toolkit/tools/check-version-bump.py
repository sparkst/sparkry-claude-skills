"""Version-bump gate for the ai-review-toolkit plugin.

If a push/PR changes any of the plugin's shipped source, its version MUST be
bumped in BOTH `plugins/ai-review-toolkit/.claude-plugin/plugin.json` and the
`ai-review-toolkit` entry of the root `.claude-plugin/marketplace.json` — and the
two must agree. A stale `marketplace.json` makes `/plugin marketplace update`
silently no-op, so both are load-bearing.

Pure logic (`requires_bump`, `check_bump`) is unit-tested; the CLI gathers the
git diff + the base/head versions and shells the logic. Used by both the CI check
(.github/workflows/tests.yml) and the local pre-push hook (.githooks/pre-push).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

PLUGIN_PREFIX = "plugins/ai-review-toolkit/"
# Files under the plugin that do NOT constitute a shippable change on their own.
IGNORED_SUFFIXES = ("CHANGELOG.md",)

PLUGIN_JSON = "plugins/ai-review-toolkit/.claude-plugin/plugin.json"
MARKET_JSON = ".claude-plugin/marketplace.json"


def requires_bump(changed_paths: list[str]) -> bool:
    """True if any changed path is shippable plugin source (not just the CHANGELOG)."""
    for path in changed_paths:
        if not path.startswith(PLUGIN_PREFIX):
            continue
        if any(path.endswith(sfx) for sfx in IGNORED_SUFFIXES):
            continue
        return True
    return False


def check_bump(
    changed_paths: list[str],
    old_plugin: str,
    new_plugin: str,
    old_market: str,
    new_market: str,
) -> dict[str, Any]:
    """Returns {ok, bump_required, violations}.

    When shippable source changed, BOTH version files must differ from the base
    AND agree with each other.
    """
    if not requires_bump(changed_paths):
        return {"ok": True, "bump_required": False, "violations": []}

    violations: list[str] = []
    if new_plugin == old_plugin:
        violations.append(
            f"plugin.json version unchanged ({new_plugin}) despite ai-review-toolkit source changes — bump it"
        )
    if new_market == old_market:
        violations.append(
            f"marketplace.json version unchanged ({new_market}) despite ai-review-toolkit source changes — bump it"
        )
    if new_plugin != new_market:
        violations.append(
            f"plugin.json ({new_plugin}) and marketplace.json ({new_market}) versions disagree — they must match"
        )
    return {"ok": not violations, "bump_required": True, "violations": violations}


# ---------------------------------------------------------------------------
# git plumbing (CLI only)
# ---------------------------------------------------------------------------

def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def _changed_paths(base: str) -> list[str]:
    out = _git("diff", "--name-only", f"{base}...HEAD")
    return [p for p in out.splitlines() if p.strip()]


def _plugin_version_at(ref: str | None) -> str:
    text = _git("show", f"{ref}:{PLUGIN_JSON}") if ref else _read(PLUGIN_JSON)
    return str(json.loads(text).get("version", ""))


def _market_version_at(ref: str | None) -> str:
    text = _git("show", f"{ref}:{MARKET_JSON}") if ref else _read(MARKET_JSON)
    entry = next((p for p in json.loads(text).get("plugins", []) if p.get("name") == "ai-review-toolkit"), {})
    return str(entry.get("version", ""))


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enforce an ai-review-toolkit version bump on source changes.")
    parser.add_argument("--base", default="origin/main", help="Base ref to diff against (default origin/main)")
    args = parser.parse_args(argv)

    try:
        changed = _changed_paths(args.base)
        res = check_bump(
            changed_paths=changed,
            old_plugin=_plugin_version_at(args.base),
            new_plugin=_plugin_version_at(None),
            old_market=_market_version_at(args.base),
            new_market=_market_version_at(None),
        )
    except subprocess.CalledProcessError as exc:
        print(f"version-bump gate: could not diff against {args.base} ({exc}) — skipping", file=sys.stderr)
        return 0  # fail-open on git plumbing errors (e.g. base ref absent locally)

    if not res["bump_required"]:
        print("version-bump gate: no shippable ai-review-toolkit change — OK")
        return 0
    if res["ok"]:
        print(f"version-bump gate: version bumped to {_plugin_version_at(None)} — OK")
        return 0
    print("version-bump gate: BLOCKED", file=sys.stderr)
    for viol in res["violations"]:
        print(f"  - {viol}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
