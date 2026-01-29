#!/usr/bin/env python3
"""
REQ-ID Extractor

Extracts requirements from requirements.lock.md.

Usage:
    python req-id-extractor.py \
      --lock-file requirements/requirements.lock.md \
      --output test-checklist.json

    Or for test-to-requirement mapping:
    python req-id-extractor.py \
      --lock-file requirements/requirements.lock.md \
      --test-dir src/ \
      --output req-coverage.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List


def extract_requirements(lock_file: Path) -> Dict[str, Any]:
    """
    Extract REQ-IDs and details from requirements.lock.md.

    Args:
        lock_file: Path to requirements.lock.md

    Returns:
        Dictionary mapping REQ-IDs to their details
    """
    # TODO: Implement requirement extraction
    # Parse markdown for:
    # - REQ-IDs (format: REQ-NNN)
    # - Descriptions
    # - Acceptance criteria
    # - Edge cases

    requirements = {}

    with open(lock_file) as f:
        content = f.read()

    # Simple regex to find REQ-IDs (TODO: improve parsing)
    req_pattern = r'##\s+(REQ-\d+):\s+(.+?)(?=\n##|\Z)'
    matches = re.finditer(req_pattern, content, re.DOTALL)

    for match in matches:
        req_id = match.group(1)
        req_content = match.group(2)

        # TODO: Parse acceptance criteria, edge cases
        requirements[req_id] = {
            'description': req_content.split('\n')[0].strip(),
            'acceptance': [],  # TODO: Extract from content
            'edge_cases': []   # TODO: Extract from content
        }

    return requirements


def map_tests_to_requirements(
    requirements: Dict[str, Any],
    test_dir: Path
) -> Dict[str, Any]:
    """
    Map test files to requirements.

    Args:
        requirements: Requirements dictionary
        test_dir: Directory containing test files

    Returns:
        Coverage mapping
    """
    # TODO: Implement test-to-requirement mapping
    # 1. Find all *.spec.ts files
    # 2. Parse for REQ-ID references
    # 3. Map tests to requirements

    return {
        req_id: {
            'tests': [],  # TODO: List of test files covering this REQ
            'coverage': 0  # TODO: Calculate coverage
        }
        for req_id in requirements
    }


def main():
    parser = argparse.ArgumentParser(
        description='Extract REQ-IDs from requirements.lock.md'
    )
    parser.add_argument('--lock-file', type=str, required=True,
                        help='Path to requirements.lock.md')
    parser.add_argument('--test-dir', type=str,
                        help='Directory containing test files (for coverage mapping)')
    parser.add_argument('--output', type=str, required=True,
                        help='Output JSON file path')

    args = parser.parse_args()

    lock_file = Path(args.lock_file)

    if not lock_file.exists():
        print(f"Error: Lock file not found: {lock_file}", file=sys.stderr)
        sys.exit(1)

    requirements = extract_requirements(lock_file)

    if args.test_dir:
        test_dir = Path(args.test_dir)
        if not test_dir.exists():
            print(f"Error: Test directory not found: {test_dir}", file=sys.stderr)
            sys.exit(1)
        result = map_tests_to_requirements(requirements, test_dir)
    else:
        result = requirements

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Results written to {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
