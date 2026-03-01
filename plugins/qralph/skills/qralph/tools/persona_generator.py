# Re-export from persona-generator.py for Python import compatibility.
# The canonical file uses the project's hyphenated naming convention.

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "persona_generator_impl",
    Path(__file__).parent / "persona-generator.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

generate_persona_template = _mod.generate_persona_template
generate_persona_review_prompt = _mod.generate_persona_review_prompt
suggest_archetypes = _mod.suggest_archetypes
