"""Golden prompt-construction parity (Python side).

Locks the reviewer/fixer prompt builders against the committed
fixtures/prompts.json so the Python oracle and the JS port (js/prompts.mjs)
can never silently diverge. See gen-prompt-fixtures.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling

gen = load_sibling("gen-prompt-fixtures.py", "gen_prompt_fixtures")

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "prompts.json"


def test_prompt_fixtures_exist():
    assert FIXTURES.exists(), f"golden prompt corpus missing: {FIXTURES}"


def test_committed_equals_regenerated():
    committed = json.loads(FIXTURES.read_text())
    assert committed == gen.build_corpus(), (
        "fixtures/prompts.json is stale — run "
        "`python3 gen-prompt-fixtures.py --write` and commit."
    )
