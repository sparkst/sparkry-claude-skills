"""Generate the golden adjudication corpus from the Python oracle.

Step 1 of the ultracode refactor. Defines edge-case INPUTS for the
deterministic hot-loop functions and captures the Python outputs as a
committed JSON corpus. The JS port (step 2) must reproduce this same corpus,
so the two implementations can never silently diverge.

Usage:
    python3 gen-golden-fixtures.py --write    # (re)write fixtures/adjudication.json
    python3 gen-golden-fixtures.py --check     # fail if committed file is stale

`run_case(fn, input)` is the single source of "how to invoke each function and
JSON-shape its result" — used both here and by test_golden_parity.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

finding_parser = load_sibling("finding-parser.py")
team_selector = load_sibling("team-selector.py")

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "adjudication.json"


# ---------------------------------------------------------------------------
# Invocation adapters — run one function, return a JSON-serializable result.
# (Tuple returns are flattened into objects so they round-trip through JSON.)
# ---------------------------------------------------------------------------

def run_case(fn: str, inp: dict) -> object:
    if fn == "validate_finding":
        valid, errors = finding_parser.validate_finding(inp["finding"])
        return {"valid": valid, "errors": errors}

    if fn == "deduplicate_findings":
        return finding_parser.deduplicate_findings(inp["findings"])

    if fn == "count_by_severity":
        return finding_parser.count_by_severity(inp["findings"])

    if fn == "check_convergence":
        converged, message = finding_parser.check_convergence(
            inp["findings"],
            threshold=inp.get("threshold", 0),
            min_findings=inp.get("min_findings", 0),
        )
        return {"converged": converged, "message": message}

    if fn == "synthesize_findings":
        warnings: list[dict] = []
        result = finding_parser.synthesize_findings(inp["reviewer_results"], warnings)
        return {"findings": result, "dropped": warnings}

    if fn == "resolve_reviewer_model":
        agent = team_selector.AgentDef(**inp["agent"])
        complexity = team_selector.Complexity(**inp["complexity"])
        return team_selector.resolve_reviewer_model(agent, complexity)

    if fn == "check_fix_completeness":
        complete, missing = finding_parser.check_fix_completeness(
            inp["findings"], inp["resolutions"]
        )
        return {"complete": complete, "missing": missing}

    raise ValueError(f"unknown function: {fn}")


# ---------------------------------------------------------------------------
# Case inputs — chosen to exercise the tricky, drift-prone behaviors.
# ---------------------------------------------------------------------------

def _finding(fid, sev, title, source="r1", **extra):
    base = {
        "id": fid, "severity": sev, "title": title,
        "requirement": "REQ-1", "finding": "f", "recommendation": "fix it",
        "source": source,
    }
    base.update(extra)
    return base


def _agent(name, model="sonnet"):
    return {"name": name, "domains": ["backend"], "model": model,
            "description": "d", "review_lens": "lens"}


def _complexity(files=1, tools=1, ctx=0.0):
    return {"file_count": files, "tool_types": tools, "context_fraction": ctx}


_INPUTS: dict[str, list[dict]] = {
    "validate_finding": [
        {"name": "valid", "input": {"finding": _finding("P0-abc", "P0", "T")}},
        {"name": "missing_required_field", "input": {"finding": {"id": "P0-abc", "severity": "P0", "title": "T"}}},
        {"name": "empty_string_field", "input": {"finding": _finding("P0-abc", "P0", "   ")}},
        {"name": "bad_severity", "input": {"finding": _finding("P0-abc", "P9", "T")}},
        {"name": "malformed_id", "input": {"finding": _finding("XX", "P0", "T")}},
        {"name": "id_severity_mismatch", "input": {"finding": _finding("P1-abc", "P0", "T")}},
    ],
    "deduplicate_findings": [
        {"name": "empty", "input": {"findings": []}},
        {"name": "no_dupes", "input": {"findings": [_finding("P1-aaa", "P1", "A"), _finding("P2-bbb", "P2", "B")]}},
        {"name": "max_severity_wins", "input": {"findings": [
            _finding("P2-aaa", "P2", "Same Bug", "r1"),
            _finding("P0-bbb", "P0", "same bug", "r2"),
        ]}},
        {"name": "normalized_title_whitespace_case", "input": {"findings": [
            _finding("P1-aaa", "P1", "  SQL   Injection ", "r1"),
            _finding("P1-ccc", "P1", "sql injection", "r2"),
        ]}},
        {"name": "sources_and_evidence_aggregate", "input": {"findings": [
            _finding("P1-aaa", "P1", "Bug", "r1", evidence=["a.py:1"]),
            _finding("P1-bbb", "P1", "bug", "r2", evidence=["b.py:2"]),
        ]}},
    ],
    "count_by_severity": [
        {"name": "empty", "input": {"findings": []}},
        {"name": "mixed", "input": {"findings": [
            _finding("P0-a", "P0", "a"), _finding("P1-b", "P1", "b"),
            _finding("P2-c", "P2", "c"), _finding("P3-d", "P3", "d"),
            _finding("P0-e", "P0", "e"),
        ]}},
        {"name": "all_p2", "input": {"findings": [_finding("P2-a", "P2", "a"), _finding("P2-b", "P2", "b")]}},
    ],
    "check_convergence": [
        {"name": "zero_findings_converged", "input": {"findings": []}},
        {"name": "p0_blocks", "input": {"findings": [_finding("P0-a", "P0", "a")]}},
        {"name": "p1_blocks", "input": {"findings": [_finding("P1-a", "P1", "a")]}},
        {"name": "low_within_threshold", "input": {"findings": [_finding("P2-a", "P2", "a")], "threshold": 1}},
        {"name": "low_over_threshold", "input": {"findings": [_finding("P2-a", "P2", "a"), _finding("P3-b", "P3", "b")], "threshold": 1}},
        {"name": "min_findings_guard", "input": {"findings": [], "min_findings": 1}},
    ],
    "synthesize_findings": [
        {"name": "empty", "input": {"reviewer_results": [[], []]}},
        {"name": "dedup_and_sort_p0_first", "input": {"reviewer_results": [
            [_finding("P2-aaa", "P2", "Shared", "r1")],
            [_finding("P0-bbb", "P0", "shared", "r2"), _finding("P3-ccc", "P3", "Minor", "r2")],
        ]}},
        {"name": "invalid_findings_dropped", "input": {"reviewer_results": [
            [_finding("P1-ok", "P1", "Good", "r1"), {"id": "bad", "severity": "P9"}],
        ]}},
    ],
    "resolve_reviewer_model": [
        {"name": "security_always_opus", "input": {"agent": _agent("security-reviewer"), "complexity": _complexity()}},
        {"name": "architecture_always_opus", "input": {"agent": _agent("architecture-reviewer"), "complexity": _complexity()}},
        {"name": "simple_stays_sonnet", "input": {"agent": _agent("code-quality-reviewer"), "complexity": _complexity()}},
        {"name": "multi_file_escalates", "input": {"agent": _agent("ux-reviewer"), "complexity": _complexity(files=2)}},
        {"name": "three_tool_types_escalates", "input": {"agent": _agent("ux-reviewer"), "complexity": _complexity(tools=3)}},
        {"name": "two_tool_types_stays", "input": {"agent": _agent("ux-reviewer"), "complexity": _complexity(tools=2)}},
        {"name": "over_20pct_context_escalates", "input": {"agent": _agent("ux-reviewer"), "complexity": _complexity(ctx=0.21)}},
        {"name": "at_20pct_context_stays", "input": {"agent": _agent("ux-reviewer"), "complexity": _complexity(ctx=0.20)}},
    ],
    "check_fix_completeness": [
        {"name": "all_fixed_complete", "input": {
            "findings": [_finding("P1-aaa", "P1", "A")],
            "resolutions": [{"finding_id": "P1-aaa", "status": "FIXED", "evidence": "a.py:1"}],
        }},
        {"name": "missing_resolution", "input": {
            "findings": [_finding("P1-aaa", "P1", "A"), _finding("P2-bbb", "P2", "B")],
            "resolutions": [{"finding_id": "P1-aaa", "status": "FIXED", "evidence": "a.py:1"}],
        }},
        {"name": "prohibited_status_invalid", "input": {
            "findings": [_finding("P1-aaa", "P1", "A")],
            "resolutions": [{"finding_id": "P1-aaa", "status": "WONTFIX", "evidence": "x"}],
        }},
        {"name": "escalated_counts_as_resolved", "input": {
            "findings": [_finding("P1-aaa", "P1", "A")],
            "resolutions": [{"finding_id": "P1-aaa", "status": "ESCALATED", "evidence": "needs arch change"}],
        }},
        {"name": "fixed_without_evidence_invalid", "input": {
            "findings": [_finding("P1-aaa", "P1", "A")],
            "resolutions": [{"finding_id": "P1-aaa", "status": "FIXED", "evidence": ""}],
        }},
    ],
}


def build_corpus() -> dict:
    """Run every input through the Python oracle and return the full corpus."""
    cases: dict[str, list[dict]] = {}
    for fn, items in _INPUTS.items():
        cases[fn] = [
            {"name": item["name"], "input": item["input"], "expected": run_case(fn, item["input"])}
            for item in items
        ]
    return {
        "meta": {
            "purpose": "golden adjudication corpus generated from the Python oracle; "
                       "the JS port must reproduce it exactly",
            "regenerate": "python3 gen-golden-fixtures.py --write",
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate/check the golden adjudication corpus.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Write fixtures/adjudication.json")
    group.add_argument("--check", action="store_true", help="Fail if the committed file is stale")
    args = parser.parse_args(argv)

    corpus = build_corpus()
    serialized = json.dumps(corpus, indent=2, sort_keys=True) + "\n"

    if args.write:
        FIXTURES.parent.mkdir(parents=True, exist_ok=True)
        FIXTURES.write_text(serialized)
        total = sum(len(v) for v in corpus["cases"].values())
        print(f"wrote {FIXTURES} ({total} cases across {len(corpus['cases'])} functions)")
        return 0

    # --check
    if not FIXTURES.exists():
        print(f"missing: {FIXTURES} (run --write)", file=sys.stderr)
        return 1
    committed = FIXTURES.read_text()
    if committed != serialized:
        print("STALE: fixtures/adjudication.json differs from the Python oracle. "
              "Run `python3 gen-golden-fixtures.py --write` and commit.", file=sys.stderr)
        return 1
    print("golden corpus is in sync with the Python oracle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
