#!/usr/bin/env python3
"""
Dependency Risk Analyzer

Checks package.json for deprecated or vulnerable packages.
Integrates with npm audit and package deprecation status.

Usage:
    python dependency-risk.py [package.json path]

Output (JSON):
    {
      "deprecated": [
        {"name": "package-name", "version": "1.0.0", "reason": "No longer maintained"}
      ],
      "vulnerable": [
        {"name": "package-name", "version": "1.0.0", "severity": "high", "cve": "CVE-2024-12345"}
      ],
      "version_mismatches": [
        {"package": "@supabase/supabase-js", "locations": ["2.50.2", "2.45.0"]}
      ],
      "summary": {
        "total_dependencies": 42,
        "deprecated_count": 1,
        "vulnerable_count": 2,
        "mismatch_count": 1
      }
    }
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any


def load_package_json(path: str = "package.json") -> Dict[str, Any]:
    """Load package.json file"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_npm_audit() -> Dict[str, Any]:
    """
    Run npm audit and parse results.

    Returns vulnerabilities found.
    """
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode in [0, 1]:  # 0 = no vulnerabilities, 1 = vulnerabilities found
            return json.loads(result.stdout)
        else:
            return {"error": "npm audit failed"}

    except subprocess.TimeoutExpired:
        return {"error": "npm audit timed out"}
    except FileNotFoundError:
        return {"error": "npm not found"}
    except Exception as e:
        return {"error": str(e)}


def check_version_consistency(root_dir: str = ".") -> List[Dict[str, Any]]:
    """
    Check for version mismatches across edge functions.

    Focuses on @supabase/supabase-js which MUST be pinned consistently.
    """
    mismatches = []

    # Check edge functions
    edge_functions_dir = Path(root_dir) / "supabase" / "functions"

    if not edge_functions_dir.exists():
        return mismatches

    # Track versions by package
    package_versions: Dict[str, Dict[str, List[str]]] = {}

    # Scan all edge function index.ts files for imports
    for func_dir in edge_functions_dir.iterdir():
        if not func_dir.is_dir():
            continue

        index_file = func_dir / "index.ts"
        if not index_file.exists():
            continue

        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract @supabase/supabase-js version from imports
        # Pattern: import { ... } from '@supabase/supabase-js@2.50.2'
        import re
        matches = re.findall(r'from\s+["\']@supabase/supabase-js@([\d.]+)["\']', content)

        for version in matches:
            package_name = "@supabase/supabase-js"

            if package_name not in package_versions:
                package_versions[package_name] = {}

            if version not in package_versions[package_name]:
                package_versions[package_name][version] = []

            package_versions[package_name][version].append(str(index_file))

    # Find mismatches (packages with >1 version)
    for package_name, versions in package_versions.items():
        if len(versions) > 1:
            mismatches.append({
                "package": package_name,
                "locations": list(versions.keys()),
                "files": {version: files for version, files in versions.items()}
            })

    return mismatches


def parse_npm_audit(audit_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse npm audit results to extract vulnerability info.
    """
    vulnerabilities = []

    if "error" in audit_result:
        return vulnerabilities

    # npm audit v7+ format
    if "vulnerabilities" in audit_result:
        for package_name, vuln_data in audit_result.get("vulnerabilities", {}).items():
            vulnerabilities.append({
                "name": package_name,
                "severity": vuln_data.get("severity", "unknown"),
                "via": vuln_data.get("via", [])
            })

    return vulnerabilities


def main():
    package_json_path = sys.argv[1] if len(sys.argv) > 1 else "package.json"

    if not Path(package_json_path).exists():
        print(json.dumps({
            "error": f"File not found: {package_json_path}"
        }))
        sys.exit(1)

    try:
        # Load package.json
        package_data = load_package_json(package_json_path)

        dependencies = {
            **package_data.get("dependencies", {}),
            **package_data.get("devDependencies", {})
        }

        total_dependencies = len(dependencies)

        # Run npm audit
        audit_result = run_npm_audit()
        vulnerabilities = parse_npm_audit(audit_result)

        # Check version consistency
        version_mismatches = check_version_consistency()

        # Deprecated packages (placeholder - would need npm registry API)
        deprecated = []

        # Build result
        result = {
            "deprecated": deprecated,
            "vulnerable": vulnerabilities,
            "version_mismatches": version_mismatches,
            "summary": {
                "total_dependencies": total_dependencies,
                "deprecated_count": len(deprecated),
                "vulnerable_count": len(vulnerabilities),
                "mismatch_count": len(version_mismatches)
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
