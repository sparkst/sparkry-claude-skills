#!/usr/bin/env python3
"""
Supabase RLS Policy Checker

Validates that all tables in SQL migrations have Row Level Security (RLS) enabled
and appropriate policies defined.

Usage:
    python supabase-rls-checker.py <migration-file.sql>

Output (JSON):
    {
      "tables": [
        {
          "name": "personas",
          "has_rls": true,
          "policies": ["Users can access their own personas"],
          "issues": []
        },
        {
          "name": "unsafe_table",
          "has_rls": false,
          "policies": [],
          "issues": ["Missing RLS policy", "No policies defined"]
        }
      ],
      "summary": {
        "total_tables": 2,
        "tables_with_rls": 1,
        "tables_without_rls": 1,
        "total_issues": 2
      }
    }
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any


def extract_table_definitions(sql_content: str) -> List[Dict[str, Any]]:
    """
    Extract CREATE TABLE statements from SQL migration.

    Returns list of table definitions with:
    - name
    - has_rls (whether ALTER TABLE ... ENABLE ROW LEVEL SECURITY exists)
    - policies (list of policy names from CREATE POLICY statements)
    """
    tables = []

    # Find all CREATE TABLE statements
    # Pattern: CREATE TABLE table_name ( ... );
    create_table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\s(]+)\s*\('

    table_names = re.findall(create_table_pattern, sql_content, re.IGNORECASE)

    for table_name in table_names:
        # Remove schema prefix if present (e.g., public.users -> users)
        clean_table_name = table_name.split('.')[-1]

        # Check if RLS is enabled for this table
        rls_pattern = rf'ALTER\s+TABLE\s+{re.escape(clean_table_name)}\s+ENABLE\s+ROW\s+LEVEL\s+SECURITY'
        has_rls = bool(re.search(rls_pattern, sql_content, re.IGNORECASE))

        # Find policies for this table
        # Pattern: CREATE POLICY "policy_name" ON table_name
        policy_pattern = rf'CREATE\s+POLICY\s+"([^"]+)"\s+ON\s+{re.escape(clean_table_name)}'
        policies = re.findall(policy_pattern, sql_content, re.IGNORECASE)

        # Identify issues
        issues = []
        if not has_rls:
            issues.append("Missing RLS: No 'ALTER TABLE ... ENABLE ROW LEVEL SECURITY' statement")

        if not policies:
            issues.append("No policies defined: Table has no CREATE POLICY statements")

        tables.append({
            "name": clean_table_name,
            "has_rls": has_rls,
            "policies": policies,
            "issues": issues
        })

    return tables


def main():
    if len(sys.argv) < 2:
        print("Usage: python supabase-rls-checker.py <migration-file.sql>", file=sys.stderr)
        sys.exit(1)

    migration_file = sys.argv[1]

    if not Path(migration_file).exists():
        print(json.dumps({
            "error": f"File not found: {migration_file}"
        }))
        sys.exit(1)

    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # Extract table definitions and RLS status
        tables = extract_table_definitions(sql_content)

        # Calculate summary
        total_tables = len(tables)
        tables_with_rls = sum(1 for t in tables if t["has_rls"])
        tables_without_rls = total_tables - tables_with_rls
        total_issues = sum(len(t["issues"]) for t in tables)

        result = {
            "file": migration_file,
            "tables": tables,
            "summary": {
                "total_tables": total_tables,
                "tables_with_rls": tables_with_rls,
                "tables_without_rls": tables_without_rls,
                "total_issues": total_issues
            }
        }

        print(json.dumps(result, indent=2))

        # Exit with error code if issues found
        if total_issues > 0:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
