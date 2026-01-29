#!/usr/bin/env python3
"""
Quality Gate Checker
Runs quality gates (lint, typecheck, test) and reports results in JSON format.

Usage:
    python quality-gate-checker.py [--config=.qgit.json]

Output:
    JSON with gate results:
    {
        "lint": {"status": "pass", "errors": 0},
        "typecheck": {"status": "pass", "errors": 0},
        "test": {"status": "fail", "errors": 2, "details": "..."}
    }
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class QualityGate:
    """Represents a single quality gate check."""

    def __init__(self, name: str, command: str, required: bool = True):
        self.name = name
        self.command = command
        self.required = required

    def run(self) -> Dict[str, any]:
        """
        Run the quality gate command.

        Returns:
            Dict with status, errors, and details
        """
        try:
            result = subprocess.run(
                self.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return {
                    "status": "pass",
                    "errors": 0,
                    "output": result.stdout
                }
            else:
                return {
                    "status": "fail",
                    "errors": result.returncode,
                    "output": result.stdout,
                    "details": result.stderr
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "errors": 1,
                "details": f"Command timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "status": "error",
                "errors": 1,
                "details": str(e)
            }


def load_config(config_path: Optional[str] = None) -> List[QualityGate]:
    """
    Load quality gates from config file.

    Args:
        config_path: Path to .qgit.json config file

    Returns:
        List of QualityGate objects
    """
    # Default gates
    default_gates = [
        QualityGate("Lint", "npm run lint", required=True),
        QualityGate("Typecheck", "npm run typecheck", required=True),
        QualityGate("Test", "npm run test", required=True),
    ]

    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            if 'quality_gates' in config:
                gates = []
                for gate_config in config['quality_gates']:
                    gates.append(QualityGate(
                        name=gate_config['name'],
                        command=gate_config['command'],
                        required=gate_config.get('required', True)
                    ))
                return gates
        except Exception as e:
            print(f"Warning: Failed to load config: {e}", file=sys.stderr)
            return default_gates

    return default_gates


def run_quality_gates(gates: List[QualityGate]) -> Dict[str, Dict]:
    """
    Run all quality gates.

    Args:
        gates: List of QualityGate objects

    Returns:
        Dict mapping gate name to results
    """
    results = {}

    for gate in gates:
        print(f"Running {gate.name}...", file=sys.stderr)
        result = gate.run()
        results[gate.name.lower().replace(' ', '_')] = result

        # Stop on first required gate failure
        if gate.required and result['status'] != 'pass':
            print(f"❌ {gate.name} failed (required gate)", file=sys.stderr)
            break
        elif result['status'] == 'pass':
            print(f"✅ {gate.name} passed", file=sys.stderr)
        else:
            print(f"⚠️  {gate.name} failed (optional)", file=sys.stderr)

    return results


def main():
    """Main entry point."""
    # Parse arguments
    config_path = None
    for arg in sys.argv[1:]:
        if arg.startswith('--config='):
            config_path = arg.split('=', 1)[1]

    # Load gates
    gates = load_config(config_path)

    # Run gates
    results = run_quality_gates(gates)

    # Output JSON
    output = {
        "results": results,
        "all_passed": all(
            r['status'] == 'pass'
            for r in results.values()
        )
    }

    print(json.dumps(output, indent=2))

    # Exit with error if any required gate failed
    if not output['all_passed']:
        sys.exit(1)


if __name__ == '__main__':
    main()
