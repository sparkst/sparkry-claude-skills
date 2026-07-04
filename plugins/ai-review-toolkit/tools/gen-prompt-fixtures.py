"""Generate the golden prompt-construction corpus from the Python oracle.

Step 2 of the ultracode refactor. The reviewer/fixer prompt builders are part
of the hot-loop but are NOT in the adjudication corpus (they build strings, not
adjudication verdicts). This freezes their exact output so the JS port
(js/prompts.mjs) can be validated byte-for-byte and neither side drifts.

Each case is {name, input, expected} where *input* is the content the JS port
receives directly (the workflow reads files and passes content in), and
*expected* is the string the Python driver produces for that same content.

Usage:
    python3 gen-prompt-fixtures.py --write    # (re)write fixtures/prompts.json
    python3 gen-prompt-fixtures.py --check     # fail if committed file is stale
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

finding_parser = load_sibling("finding-parser.py")

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "prompts.json"


# ---------------------------------------------------------------------------
# Deterministic inputs — exercise round 1 (fresh) and round 2 (verification).
# ---------------------------------------------------------------------------

AGENT = {
    "name": "security-reviewer",
    "domains": ["security", "compliance", "backend"],
    "model": "opus",
    "description": "Security vulnerability and data protection reviewer",
    "review_lens": "security vulnerabilities, auth, data protection",
}

ARTIFACT_CONTENT = "def login(user, pw):\n    return pw == 'admin'\n"
REQUIREMENTS_CONTENT = "## REQ-1: Authentication\n- Acceptance: no hardcoded credentials\n"
TEST_SUMMARY_R1 = "2 passed, 1 failed"
TEST_SUMMARY_R2 = "3 passed, 0 failed"

ROUND1_FINDINGS = [
    {
        "id": "P0-abc",
        "severity": "P0",
        "title": "Hardcoded credential",
        "requirement": "REQ-1",
        "finding": "Password compared against literal 'admin'.",
        "recommendation": "Hash and compare against a stored credential.",
        "source": "security-reviewer",
        "sources": ["security-reviewer"],
        "evidence": ["auth.py:2"],
    },
    {
        "id": "P2-def",
        "severity": "P2",
        "title": "Missing type hints",
        "requirement": "REQ-1",
        "finding": "login() lacks type annotations.",
        "recommendation": "Add parameter and return type hints.",
        "source": "code-quality-reviewer",
        "sources": ["code-quality-reviewer"],
        "evidence": [],
    },
]

ROUND1_RESOLUTIONS = [
    {
        "finding_id": "P0-abc",
        "status": "FIXED",
        "description": "Replaced literal check with bcrypt verify.",
        "evidence": "auth.py:2",
    },
    {
        "finding_id": "P2-def",
        "status": "ESCALATED",
        "description": "Type-hint rollout tracked separately.",
        "evidence": "needs project-wide typing pass",
    },
]


def _build_state(artifact_path: str, requirements_path: str) -> dict:
    """A minimal 2-round state carrying only what the prompt builders read."""
    return {
        "team": [AGENT],
        "artifact_path": artifact_path,
        "requirements_path": requirements_path,
        "rounds": [
            {
                "round_num": 1,
                "test_results": {"summary": TEST_SUMMARY_R1},
                "findings": ROUND1_FINDINGS,
                "fix_resolutions": ROUND1_RESOLUTIONS,
            },
            {
                "round_num": 2,
                "test_results": {"summary": TEST_SUMMARY_R2},
                "findings": [],
                "fix_resolutions": [],
            },
        ],
    }


def build_corpus() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        artifact_path = str(Path(tmp) / "artifact.py")
        requirements_path = str(Path(tmp) / "requirements.md")
        Path(artifact_path).write_text(ARTIFACT_CONTENT, encoding="utf-8")
        Path(requirements_path).write_text(REQUIREMENTS_CONTENT, encoding="utf-8")
        state = _build_state(artifact_path, requirements_path)

        cases = {
            "format_findings": [
                {
                    "name": "empty",
                    "input": {"findings": []},
                    "expected": finding_parser.format_findings([], fmt="markdown"),
                },
                {
                    "name": "with_evidence_and_sources",
                    "input": {"findings": ROUND1_FINDINGS},
                    "expected": finding_parser.format_findings(ROUND1_FINDINGS, fmt="markdown"),
                },
            ],
            "reviewer_prompt": [
                {
                    "name": "round1_fresh",
                    "input": {
                        "agent": AGENT,
                        "artifact_content": ARTIFACT_CONTENT,
                        "requirements_content": REQUIREMENTS_CONTENT,
                        "test_summary": TEST_SUMMARY_R1,
                        "round_num": 1,
                        "prior_findings": [],
                        "prior_resolutions": [],
                    },
                    "expected": finding_parser.get_reviewer_prompt(state, 0, 1),
                },
                {
                    "name": "round2_verification",
                    "input": {
                        "agent": AGENT,
                        "artifact_content": ARTIFACT_CONTENT,
                        "requirements_content": REQUIREMENTS_CONTENT,
                        "test_summary": TEST_SUMMARY_R2,
                        "round_num": 2,
                        "prior_findings": ROUND1_FINDINGS,
                        "prior_resolutions": ROUND1_RESOLUTIONS,
                    },
                    "expected": finding_parser.get_reviewer_prompt(state, 0, 2),
                },
            ],
            "fixer_prompt": [
                {
                    "name": "round1",
                    "input": {
                        "artifact_content": ARTIFACT_CONTENT,
                        "requirements_content": REQUIREMENTS_CONTENT,
                        "test_summary": TEST_SUMMARY_R1,
                        "findings": ROUND1_FINDINGS,
                    },
                    "expected": finding_parser.get_fixer_prompt(state, 1),
                },
            ],
        }

    return {
        "meta": {
            "purpose": "golden prompt-construction corpus from the Python oracle; "
                       "js/prompts.mjs must reproduce it exactly",
            "regenerate": "python3 gen-prompt-fixtures.py --write",
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate/check the golden prompt corpus.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Write fixtures/prompts.json")
    group.add_argument("--check", action="store_true", help="Fail if the committed file is stale")
    args = parser.parse_args(argv)

    corpus = build_corpus()
    serialized = json.dumps(corpus, indent=2, sort_keys=True) + "\n"

    if args.write:
        FIXTURES.parent.mkdir(parents=True, exist_ok=True)
        FIXTURES.write_text(serialized)
        total = sum(len(v) for v in corpus["cases"].values())
        print(f"wrote {FIXTURES} ({total} cases across {len(corpus['cases'])} builders)")
        return 0

    if not FIXTURES.exists():
        print(f"missing: {FIXTURES} (run --write)", file=sys.stderr)
        return 1
    committed = FIXTURES.read_text()
    if committed != serialized:
        print("STALE: fixtures/prompts.json differs from the Python oracle. "
              "Run `python3 gen-prompt-fixtures.py --write` and commit.", file=sys.stderr)
        return 1
    print("golden prompt corpus is in sync with the Python oracle.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
