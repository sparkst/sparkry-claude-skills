#!/usr/bin/env python3
"""Detect which plugins/skills are relevant for a QRALPH project.

Analyzes the user's request text and/or target codebase to determine
which plugins should be activated for the project.
"""

import json
import os
import re
import sys
from typing import Optional


# ---------------------------------------------------------------------------
# Plugin signal mappings: keyword → plugin name
# ---------------------------------------------------------------------------

REQUEST_SIGNALS: dict[str, list[str]] = {
    "frontend-design": [
        "landing page", "hero", "ui", "ux", "interface", "component",
        "layout", "dashboard", "form", "modal", "navigation", "responsive",
        "mobile", "css", "tailwind", "design", "webpage", "website",
        "storefront", "homepage", "page", "screen", "view",
    ],
    "stripe": [
        "payment", "billing", "subscription", "checkout", "stripe",
        "invoice", "pricing", "plan", "charge", "refund", "ecommerce",
        "cart", "purchase",
    ],
    "context7": [
        "react", "vue", "svelte", "angular", "next", "nuxt", "remix",
        "express", "fastapi", "django", "flask", "prisma", "drizzle",
        "tanstack", "tailwind", "shadcn", "radix", "zod", "trpc",
    ],
    "playwright": [
        "e2e", "end-to-end", "browser test", "integration test",
        "visual test", "screenshot", "ui test",
    ],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_plugins_for_request(request: str) -> list[str]:
    """Keyword-match the request text against plugin signal mappings."""
    request_lower = request.lower()
    detected: list[str] = []

    for plugin, keywords in REQUEST_SIGNALS.items():
        for keyword in keywords:
            if keyword in request_lower:
                detected.append(plugin)
                break

    return detected


def detect_plugins_from_codebase(target_dir: str) -> list[str]:
    """Analyze manifest files in target_dir to infer relevant plugins."""
    detected: list[str] = []
    pkg_path = os.path.join(target_dir, "package.json")

    has_package_json = False
    pkg: dict = {}

    if os.path.isfile(pkg_path):
        has_package_json = True
        with open(pkg_path) as f:
            pkg = json.load(f)

    # context7: any dependency manifest present
    manifest_files = [
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "Cargo.toml",
    ]
    for mf in manifest_files:
        if os.path.isfile(os.path.join(target_dir, mf)):
            if "context7" not in detected:
                detected.append("context7")
            break

    # stripe: "stripe" in package.json dependencies
    if has_package_json:
        all_deps = {
            **pkg.get("dependencies", {}),
            **pkg.get("devDependencies", {}),
        }
        if any("stripe" in dep for dep in all_deps):
            detected.append("stripe")

    # playwright: config file or devDependency
    pw_configs = ["playwright.config.ts", "playwright.config.js"]
    for cfg in pw_configs:
        if os.path.isfile(os.path.join(target_dir, cfg)):
            if "playwright" not in detected:
                detected.append("playwright")
            break

    if has_package_json:
        dev_deps = pkg.get("devDependencies", {})
        if any("playwright" in dep for dep in dev_deps):
            if "playwright" not in detected:
                detected.append("playwright")

    return detected


def detect_all_plugins(
    request: str, target_dir: Optional[str] = None
) -> list[str]:
    """Combine request-based and codebase-based detection, deduplicated."""
    plugins = detect_plugins_for_request(request)

    if target_dir and os.path.isdir(target_dir):
        for p in detect_plugins_from_codebase(target_dir):
            if p not in plugins:
                plugins.append(p)

    return plugins


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect relevant plugins for a QRALPH project."
    )
    parser.add_argument("request", help="User request text")
    parser.add_argument(
        "--target-dir",
        default=None,
        help="Path to target codebase directory",
    )
    args = parser.parse_args()

    result = detect_all_plugins(args.request, args.target_dir)
    print(json.dumps(result, indent=2))
