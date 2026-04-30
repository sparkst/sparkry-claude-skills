"""Shared module loader for hyphenated Python filenames.

All driver and test modules import from here instead of reimplementing
their own spec_from_file_location boilerplate.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_TOOLS_DIR = Path(__file__).resolve().parent


def load_sibling(filename: str, module_name: str | None = None) -> Any:
    """Import a sibling tool module by filename (cached in sys.modules).

    Args:
        filename: e.g. "finding-parser.py"
        module_name: Override for sys.modules key. Defaults to
            filename with hyphens replaced by underscores, minus .py.
    """
    if module_name is None:
        module_name = filename.replace("-", "_").replace(".py", "")
    if module_name in sys.modules:
        return sys.modules[module_name]
    mod_path = _TOOLS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, str(mod_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {mod_path}")
    mod = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass decorator can find the module (Python 3.14+)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return mod
