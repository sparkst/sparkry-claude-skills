"""Import shim for requirements-tracer.py (Python cannot import hyphenated filenames)."""
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "requirements_tracer_impl",
    os.path.join(os.path.dirname(__file__), "requirements-tracer.py"),
)
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)

# Re-export public API
trace_requirements = _mod.trace_requirements
generate_coverage_report = _mod.generate_coverage_report
