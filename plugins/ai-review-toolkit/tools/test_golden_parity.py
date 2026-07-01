"""Golden-fixture parity tests — the JS<->Python drift lock (Python side).

Step 1 of the ultracode refactor: freeze the deterministic adjudication
contract as a committed JSON corpus generated from the Python oracle. This
test asserts the current Python still reproduces the committed corpus. The JS
port (step 2) will assert against the SAME committed file, so any divergence
on either side fails CI.

See ~/.claude/plans/ai-review-ultracode-refactor.md (step 1).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

gen = load_sibling("gen-golden-fixtures.py")
finding_parser = load_sibling("finding-parser.py")

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "adjudication.json"

TARGET_FUNCTIONS = [
    "validate_finding",
    "deduplicate_findings",
    "count_by_severity",
    "check_convergence",
    "synthesize_findings",
    "resolve_reviewer_model",
    "check_fix_completeness",
]


@pytest.fixture(scope="module")
def corpus() -> dict:
    assert FIXTURES.exists(), f"golden corpus missing: {FIXTURES}"
    return json.loads(FIXTURES.read_text())


class TestCorpusStructure:
    def test_all_target_functions_present(self, corpus):
        for fn in TARGET_FUNCTIONS:
            assert fn in corpus["cases"], f"corpus missing function group: {fn}"

    def test_every_group_has_cases(self, corpus):
        for fn in TARGET_FUNCTIONS:
            assert len(corpus["cases"][fn]) >= 3, f"{fn}: need >=3 cases for coverage"

    def test_cases_have_name_input_expected(self, corpus):
        for fn, cases in corpus["cases"].items():
            for c in cases:
                assert {"name", "input", "expected"} <= set(c), f"{fn}/{c.get('name')}"


class TestPythonReproducesCorpus:
    """Replay each committed input through the live Python; must match expected."""

    def test_all_cases_reproduce(self, corpus):
        mismatches: list[str] = []
        for fn, cases in corpus["cases"].items():
            for c in cases:
                actual = gen.run_case(fn, c["input"])
                if actual != c["expected"]:
                    mismatches.append(f"{fn}/{c['name']}: {actual!r} != {c['expected']!r}")
        assert not mismatches, "Python drifted from committed corpus:\n" + "\n".join(mismatches)


class TestCommittedMatchesGenerator:
    """The committed file must equal a fresh regeneration (no stale fixtures)."""

    def test_committed_equals_regenerated(self, corpus):
        assert corpus == gen.build_corpus(), (
            "fixtures/adjudication.json is stale — run "
            "`python3 gen-golden-fixtures.py --write` and commit."
        )


class TestIntentAnchors:
    """Independent invariant checks — catch a generator that captured wrong behavior."""

    def test_max_severity_wins_on_dedup(self):
        # A lone P0 and a P2 with the same title must merge to P0.
        merged = finding_parser.deduplicate_findings([
            {"id": "P2-aaa", "severity": "P2", "title": "Same Bug", "source": "r1"},
            {"id": "P0-bbb", "severity": "P0", "title": "same bug", "source": "r2"},
        ])
        assert len(merged) == 1
        assert merged[0]["severity"] == "P0"

    def test_convergence_blocks_on_p1(self):
        findings = [{"id": "P1-xyz", "severity": "P1", "title": "t"}]
        converged, _ = finding_parser.check_convergence(findings, threshold=0)
        assert converged is False
