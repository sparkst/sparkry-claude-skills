#!/usr/bin/env python3
"""
Comment Extractor - Extract feedback comments from source files

Extracts TODO, FIXME, NOTE, and FEEDBACK comments from code and documents.

Usage:
    python comment-extractor.py <file-or-directory>

Output (JSON):
    {
      "extractions": [
        {
          "id": "EXT-001",
          "source": "path/to/file.ts:42",
          "type": "TODO",
          "content": "Add better error handling",
          "context": "function validateInput()",
          "timestamp": "2026-01-28T10:30:00Z"
        }
      ],
      "summary": {
        "total_extractions": 10,
        "by_type": {"TODO": 5, "FIXME": 2, "NOTE": 3},
        "by_source": {"project-x": 7, "project-y": 3}
      }
    }
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


# Comment patterns for different file types
PATTERNS = {
    'js': [
        r'//\s*(TODO|FIXME|NOTE|FEEDBACK):\s*(.+)$',
        r'/\*\s*(TODO|FIXME|NOTE|FEEDBACK):\s*(.+?)\s*\*/',
    ],
    'py': [
        r'#\s*(TODO|FIXME|NOTE|FEEDBACK):\s*(.+)$',
        r'"""\s*(TODO|FIXME|NOTE|FEEDBACK):\s*(.+?)\s*"""',
    ],
    'md': [
        r'<!--\s*(TODO|FIXME|NOTE|FEEDBACK):\s*(.+?)\s*-->',
    ],
}

# File extensions mapping
FILE_EXTENSIONS = {
    '.js': 'js',
    '.ts': 'js',
    '.jsx': 'js',
    '.tsx': 'js',
    '.py': 'py',
    '.md': 'md',
    '.txt': 'md',
}


def extract_comments_from_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract feedback comments from a single file.

    Args:
        file_path: Path to file to extract from

    Returns:
        List of extracted comments with metadata
    """
    extractions = []

    # Determine file type
    file_type = FILE_EXTENSIONS.get(file_path.suffix)
    if not file_type:
        return extractions

    patterns = PATTERNS.get(file_type, [])

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, start=1):
            for pattern in patterns:
                matches = re.finditer(pattern, line, re.MULTILINE)
                for match in matches:
                    comment_type = match.group(1)
                    content = match.group(2).strip()

                    # Get context (function/class name if available)
                    context = extract_context(lines, line_num)

                    extractions.append({
                        "source": f"{file_path}:{line_num}",
                        "type": comment_type,
                        "content": content,
                        "context": context,
                        "timestamp": datetime.utcnow().isoformat() + 'Z',
                    })
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)

    return extractions


def extract_context(lines: List[str], line_num: int) -> str:
    """
    Extract context for a comment (e.g., function or class name).

    Args:
        lines: All lines in the file
        line_num: Current line number

    Returns:
        Context string or empty
    """
    # Look backwards for function/class definition
    for i in range(line_num - 1, max(0, line_num - 10), -1):
        line = lines[i].strip()

        # Function patterns
        func_match = re.search(r'(?:function|def|const|let|var)\s+(\w+)', line)
        if func_match:
            return f"function {func_match.group(1)}()"

        # Class patterns
        class_match = re.search(r'class\s+(\w+)', line)
        if class_match:
            return f"class {class_match.group(1)}"

    return ""


def extract_comments_from_directory(directory: Path) -> List[Dict[str, Any]]:
    """
    Recursively extract comments from all files in directory.

    Args:
        directory: Directory to scan

    Returns:
        List of all extracted comments
    """
    all_extractions = []

    # Exclude patterns
    exclude_dirs = {'node_modules', '.git', 'dist', 'build', '__pycache__'}

    for file_path in directory.rglob('*'):
        # Skip excluded directories
        if any(excluded in file_path.parts for excluded in exclude_dirs):
            continue

        # Skip non-files
        if not file_path.is_file():
            continue

        # Extract from file
        extractions = extract_comments_from_file(file_path)
        all_extractions.extend(extractions)

    return all_extractions


def generate_summary(extractions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics for extractions.

    Args:
        extractions: List of extracted comments

    Returns:
        Summary dictionary
    """
    summary = {
        "total_extractions": len(extractions),
        "by_type": {},
        "by_source": {},
    }

    for extraction in extractions:
        # Count by type
        comment_type = extraction['type']
        summary['by_type'][comment_type] = summary['by_type'].get(comment_type, 0) + 1

        # Count by source (file without line number)
        source_file = extraction['source'].split(':')[0]
        source_project = Path(source_file).parts[0] if Path(source_file).parts else 'unknown'
        summary['by_source'][source_project] = summary['by_source'].get(source_project, 0) + 1

    return summary


def main():
    if len(sys.argv) < 2:
        print("Usage: python comment-extractor.py <file-or-directory>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(json.dumps({
            "error": f"Path not found: {path}"
        }))
        sys.exit(1)

    try:
        # Extract comments
        if path.is_file():
            extractions = extract_comments_from_file(path)
        else:
            extractions = extract_comments_from_directory(path)

        # Add IDs
        for i, extraction in enumerate(extractions, start=1):
            extraction['id'] = f"EXT-{i:03d}"

        # Generate summary
        summary = generate_summary(extractions)

        # Output result
        result = {
            "extractions": extractions,
            "summary": summary
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
