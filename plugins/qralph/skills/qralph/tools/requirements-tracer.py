#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
Requirements Tracer - Maps REQ-IDs to test files for coverage validation.

Scans test files for REQ-ID references and reports which requirements
have test coverage and which are missing.
"""

import os
import re
from pathlib import Path
from typing import Dict, List


# Pattern to match REQ-NNN references in test files
REQ_PATTERN = re.compile(r'(REQ-\d+)')

# Test file patterns to scan
TEST_FILE_PATTERNS = {'.spec.ts', '.test.ts', '.spec.py', '.test.py', '.spec.js', '.test.js'}


def _is_test_file(filename: str) -> bool:
    """Check if filename matches a test file pattern."""
    return any(filename.endswith(pattern) for pattern in TEST_FILE_PATTERNS)


def trace_requirements(directory: str, requirements: List[str]) -> Dict:
    """
    Scan test files for REQ-ID references and map to requirements.

    Args:
        directory: Root directory to scan for test files
        requirements: List of REQ-IDs to trace

    Returns:
        Dict mapping REQ-ID -> {covered: bool, test_files: list}
    """
    result = {req: {"covered": False, "test_files": []} for req in requirements}
    req_set = set(requirements)

    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if not _is_test_file(filename):
                continue

            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except (OSError, IOError):
                continue

            found_reqs = REQ_PATTERN.findall(content)
            for req_id in found_reqs:
                if req_id in req_set:
                    result[req_id]["covered"] = True
                    rel_path = os.path.relpath(filepath, directory)
                    if rel_path not in result[req_id]["test_files"]:
                        result[req_id]["test_files"].append(rel_path)

    return result


def generate_coverage_report(trace_result: Dict) -> str:
    """
    Generate a markdown coverage report from trace results.

    Args:
        trace_result: Output from trace_requirements()

    Returns:
        Markdown string with coverage summary
    """
    covered = [r for r, v in trace_result.items() if v["covered"]]
    missing = [r for r, v in trace_result.items() if not v["covered"]]
    total = len(trace_result)

    lines = ["## Requirements Coverage Report\n"]
    lines.append(f"**Coverage:** {len(covered)}/{total} requirements covered\n")

    if covered:
        lines.append("### Covered Requirements\n")
        for req_id in sorted(covered):
            files = ", ".join(trace_result[req_id]["test_files"])
            lines.append(f"- {req_id}: covered in {files}")

    if missing:
        lines.append("\n### Missing Coverage (NOT COVERED)\n")
        for req_id in sorted(missing):
            lines.append(f"- {req_id}: **not covered** — needs test")

    return "\n".join(lines)
