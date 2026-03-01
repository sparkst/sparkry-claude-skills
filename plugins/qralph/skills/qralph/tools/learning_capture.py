"""Import shim for learning-capture.py (Python cannot import hyphenated filenames)."""
import importlib.util
import os
spec = importlib.util.spec_from_file_location(
    "learning_capture_impl",
    os.path.join(os.path.dirname(__file__), "learning-capture.py"),
)
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)
# Re-export public API
extract_learnings = _mod.extract_learnings
detect_cross_project_patterns = _mod.detect_cross_project_patterns
generate_claude_md_proposal = _mod.generate_claude_md_proposal
generate_learning_summary = _mod.generate_learning_summary
