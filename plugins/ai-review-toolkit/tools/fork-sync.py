"""Fork-sync: upgrade a manual (non-marketplace) ai-review-toolkit install.

Travis runs the pipeline from a FLAT fork at ~/.claude/ai-review-tools (runtime py
at the root, generated workflows in js/) plus SKILLs installed at ~/.claude/skills/.
This tool copies the current marketplace source into that fork so the live install
matches `main` — the concrete "help me upgrade" path the self-version-check points
manual installs at.

It syncs three things:
  1. runtime tools/*.py  →  <fork>/            (flat; excludes tests, generators,
                                                and maintainer-only tools)
  2. js/*.workflow.js    →  <fork>/js/         (generated workflows only)
  3. skills/<name>/SKILL.md → <skills>/<name>/SKILL.md, with `<plugin>` rewritten to
     the fork's absolute path (`<plugin>/tools` → <fork> because the fork is flat;
     `<plugin>/js` → <fork>/js). The `<tools>` runtime placeholder is left intact.

Pure logic (`fork_skill_transform`, `tool_files_to_sync`) is unit-tested; the CLI
does the filesystem I/O and supports `--dry-run`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

DEFAULT_MARKETPLACE = os.path.expanduser(
    "~/.claude/plugins/marketplaces/sparkry-claude-skills/plugins/ai-review-toolkit"
)
DEFAULT_FORK = os.path.expanduser("~/.claude/ai-review-tools")
DEFAULT_SKILLS = os.path.expanduser("~/.claude/skills")
SKILL_NAMES = ("qreview", "qloop", "qpipeline")

# Maintainer-only tools that must never ship into the runtime fork.
MAINTAINER_ONLY = frozenset({"check-version-bump.py", "fork-sync.py"})


def fork_skill_transform(text: str, fork_root: str) -> str:
    """Rewrite marketplace `<plugin>` paths to the flat fork's absolute paths.

    `<plugin>/tools` → <fork_root> (the fork is flat, so /tools is absorbed);
    `<plugin>/js` → <fork_root>/js; any bare `<plugin>` → <fork_root>. The
    angle-bracket `<tools>` runtime placeholder is a DIFFERENT token and is left
    untouched. Idempotent — re-running finds no `<plugin>` and changes nothing.
    """
    text = text.replace("<plugin>/tools", fork_root)
    text = text.replace("<plugin>/js", f"{fork_root}/js")
    text = text.replace("<plugin>", fork_root)
    return text


def tool_files_to_sync(filenames: list[str]) -> list[str]:
    """The runtime .py tools to copy into the fork (sorted).

    Excludes tests (`test_*`), fixture generators (`gen-*`), and maintainer-only
    tools (the version-bump gate + fork-sync itself), plus anything non-.py.
    """
    return sorted(
        fn for fn in filenames
        if fn.endswith(".py")
        and not fn.startswith("test_")
        and not fn.startswith("gen-")
        and fn not in MAINTAINER_ONLY
    )


# ---------------------------------------------------------------------------
# I/O (CLI only)
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync the marketplace source into a manual ai-review-toolkit fork.")
    parser.add_argument("--marketplace", default=DEFAULT_MARKETPLACE, help="Marketplace plugin dir (source of truth)")
    parser.add_argument("--fork", default=DEFAULT_FORK, help="Flat fork dir (runtime install)")
    parser.add_argument("--skills", default=DEFAULT_SKILLS, help="Installed skills dir")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing")
    args = parser.parse_args(argv)

    fork = os.path.abspath(args.fork)
    tools_src = os.path.join(args.marketplace, "tools")
    js_src = os.path.join(args.marketplace, "js")
    skills_src = os.path.join(args.marketplace, "skills")

    if not os.path.isdir(tools_src):
        print(f"fork-sync: marketplace tools dir not found: {tools_src}", file=sys.stderr)
        return 2

    def act(msg: str, fn) -> None:
        print(("[dry-run] " if args.dry_run else "") + msg)
        if not args.dry_run:
            fn()

    # 1. runtime tools → flat fork root
    for name in tool_files_to_sync(os.listdir(tools_src)):
        src, dst = os.path.join(tools_src, name), os.path.join(fork, name)
        act(f"tool  {name} → {dst}", lambda s=src, d=dst: shutil.copy2(s, d))

    # 1b. stamp the synced version so the flat fork's version-check.py can read it
    #     (the fork has no .claude-plugin/plugin.json).
    import json as _json
    try:
        with open(os.path.join(args.marketplace, ".claude-plugin", "plugin.json"), "r", encoding="utf-8") as fh:
            synced_version = str(_json.load(fh).get("version", "")).strip()
    except Exception:
        synced_version = ""
    if synced_version:
        act(f"stamp VERSION={synced_version} → {os.path.join(fork, 'VERSION')}",
            lambda: open(os.path.join(fork, "VERSION"), "w", encoding="utf-8").write(synced_version + "\n"))

    # 2. generated workflows → fork/js
    fork_js = os.path.join(fork, "js")
    if os.path.isdir(js_src):
        for name in sorted(n for n in os.listdir(js_src) if n.endswith(".workflow.js")):
            src, dst = os.path.join(js_src, name), os.path.join(fork_js, name)
            act(f"wf    {name} → {dst}", lambda s=src, d=dst: (os.makedirs(fork_js, exist_ok=True), shutil.copy2(s, d)))

    # 3. SKILLs (path-rewritten) → skills dir
    for skill in SKILL_NAMES:
        src = os.path.join(skills_src, skill, "SKILL.md")
        if not os.path.isfile(src):
            print(f"fork-sync: skill source missing, skipping: {src}", file=sys.stderr)
            continue
        dst_dir = os.path.join(args.skills, skill)
        dst = os.path.join(dst_dir, "SKILL.md")
        with open(src, "r", encoding="utf-8") as fh:
            transformed = fork_skill_transform(fh.read(), fork)

        def write(d_dir=dst_dir, d=dst, t=transformed):
            os.makedirs(d_dir, exist_ok=True)
            with open(d, "w", encoding="utf-8") as out:
                out.write(t)

        act(f"skill {skill}/SKILL.md → {dst} (<plugin>→{fork})", write)

    print("fork-sync: " + ("dry run complete (nothing written)." if args.dry_run else "done."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
