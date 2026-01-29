#!/usr/bin/env python3
"""
Cyclomatic Complexity Calculator for TypeScript/JavaScript

Calculates McCabe complexity for functions in TypeScript/JavaScript files.
Complexity > 10 is flagged as high risk.

Usage:
    python cyclomatic-complexity.py <file-path>

Output (JSON):
    {
      "file": "path/to/file.ts",
      "functions": [
        {"name": "functionName", "complexity": 5, "line": 42, "risk": "low"},
        {"name": "complexFunc", "complexity": 15, "line": 100, "risk": "high"}
      ],
      "summary": {
        "total_functions": 2,
        "avg_complexity": 10.0,
        "high_risk_count": 1
      }
    }
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any


def calculate_cyclomatic_complexity(content: str, start_line: int) -> int:
    """
    Calculate McCabe cyclomatic complexity for a function body.

    Counts decision points:
    - if, else if, while, for, case, catch, &&, ||, ?:

    Base complexity = 1 (single path)
    """
    complexity = 1

    # Count decision points
    decision_points = [
        r'\bif\b',           # if statements
        r'\belse\s+if\b',    # else if statements
        r'\bwhile\b',        # while loops
        r'\bfor\b',          # for loops
        r'\bcase\b',         # switch cases
        r'\bcatch\b',        # catch blocks
        r'&&',               # logical AND
        r'\|\|',             # logical OR
        r'\?',               # ternary operator
    ]

    for pattern in decision_points:
        complexity += len(re.findall(pattern, content))

    return complexity


def extract_functions(file_path: str) -> List[Dict[str, Any]]:
    """
    Extract functions from TypeScript/JavaScript file and calculate complexity.

    Returns:
        List of dicts with {name, complexity, line, risk}
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    functions = []

    # Regex patterns for function declarations
    patterns = [
        # Named functions: function name(...) { ... }
        r'function\s+(\w+)\s*\([^)]*\)\s*\{',
        # Arrow functions with name: const name = (...) => { ... }
        r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{',
        # Class methods: methodName(...) { ... }
        r'(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{',
    ]

    lines = content.split('\n')

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            function_name = match.group(1)

            # Find line number
            line_number = content[:match.start()].count('\n') + 1

            # Extract function body (simplified - assumes balanced braces)
            start_pos = match.end()
            brace_count = 1
            end_pos = start_pos

            while brace_count > 0 and end_pos < len(content):
                if content[end_pos] == '{':
                    brace_count += 1
                elif content[end_pos] == '}':
                    brace_count -= 1
                end_pos += 1

            function_body = content[start_pos:end_pos]

            # Calculate complexity
            complexity = calculate_cyclomatic_complexity(function_body, line_number)

            # Determine risk level
            if complexity > 10:
                risk = "high"
            elif complexity > 6:
                risk = "medium"
            else:
                risk = "low"

            functions.append({
                "name": function_name,
                "complexity": complexity,
                "line": line_number,
                "risk": risk
            })

    return functions


def main():
    if len(sys.argv) < 2:
        print("Usage: python cyclomatic-complexity.py <file-path>", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(json.dumps({
            "error": f"File not found: {file_path}"
        }))
        sys.exit(1)

    try:
        functions = extract_functions(file_path)

        # Calculate summary stats
        total_functions = len(functions)
        avg_complexity = sum(f["complexity"] for f in functions) / total_functions if total_functions > 0 else 0
        high_risk_count = sum(1 for f in functions if f["risk"] == "high")

        result = {
            "file": file_path,
            "functions": functions,
            "summary": {
                "total_functions": total_functions,
                "avg_complexity": round(avg_complexity, 2),
                "high_risk_count": high_risk_count
            }
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
