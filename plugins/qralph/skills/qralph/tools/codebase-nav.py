#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""
Codebase Navigation Module - Adaptive search strategies for QRALPH v5.0.

Provides smart codebase search that adapts its strategy based on project type.
Used by pe-overlay.py for pattern sweeps and by the orchestrator for codebase
exploration during DISCOVER.

Strategies:
    ts-aware      - TypeScript-aware navigation using import/export patterns
    polyglot      - Multi-language navigation with language-specific patterns
    grep-enhanced - Smart grep with context-aware pattern generation (default)
"""

import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import shared state module
_state_path = Path(__file__).parent / "qralph-state.py"
_state_spec = importlib.util.spec_from_file_location("qralph_state", _state_path)
qralph_state = importlib.util.module_from_spec(_state_spec)
_state_spec.loader.exec_module(qralph_state)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STRATEGIES = {
    "ts-aware": "TypeScript-aware navigation using import/export patterns",
    "polyglot": "Multi-language navigation with language-specific patterns",
    "grep-enhanced": "Smart grep with context-aware pattern generation",
}

IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".next", "dist", "build",
    "vendor", "target", ".qralph", ".wrangler", "coverage", ".pytest_cache",
}

LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "go": [".go"],
    "rust": [".rs"],
    "java": [".java"],
    "ruby": [".rb"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx", ".mjs", ".cjs"],
}

LANGUAGE_IMPORT_PATTERNS = {
    "python": r'^(?:from\s+(\S+)\s+)?import\s+(.+)',
    "go": r'^import\s+(?:\(\s*)?["\']([^"\']+)',
    "rust": r'^use\s+(\S+)',
    "java": r'^import\s+(\S+)',
    "ruby": r'^require\s+["\']([^"\']+)',
    "typescript": r'^import\s+.*from\s+["\']([^"\']+)',
    "javascript": r'^(?:import\s+.*from\s+|require\s*\()["\']([^"\']+)',
}

_EXT_TO_LANG = {}
for lang, exts in LANGUAGE_EXTENSIONS.items():
    for ext in exts:
        _EXT_TO_LANG[ext] = lang

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------


def get_repo_root(start_path: Path) -> Path:
    """Find git repo root by walking up from start_path. Returns start_path if no .git found."""
    current = start_path.resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return start_path.resolve()


def walk_source_files(project_path: Path, extensions: list = None, max_files: int = 5000) -> list:
    """Walk project directory yielding source files, respecting ignore dirs."""
    results = []
    project_path = project_path.resolve()
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if extensions and not any(f.endswith(ext) for ext in extensions):
                continue
            results.append(Path(root) / f)
            if len(results) >= max_files:
                return results
    return results


def _ripgrep_available() -> bool:
    """Check if ripgrep is available on the system."""
    try:
        subprocess.run(["rg", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


_HAS_RG = _ripgrep_available()


def run_ripgrep(project_path: Path, pattern: str, file_filter: str = None,
                context_lines: int = 2, max_results: int = 100) -> list:
    """Run ripgrep subprocess for fast searching. Falls back to Python regex if rg unavailable."""
    project_path = project_path.resolve()

    if _HAS_RG:
        return _run_rg_subprocess(project_path, pattern, file_filter, context_lines, max_results)
    return _run_python_search(project_path, pattern, file_filter, context_lines, max_results)


def _run_rg_subprocess(project_path: Path, pattern: str, file_filter: str,
                       context_lines: int, max_results: int) -> list:
    """Execute ripgrep and parse JSON output."""
    cmd = [
        "rg", "--json", "-C", str(context_lines),
        "--max-count", str(max_results),
    ]
    for d in IGNORE_DIRS:
        cmd.extend(["--glob", f"!{d}"])
    if file_filter:
        cmd.extend(["--glob", file_filter])
    cmd.extend([pattern, str(project_path)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return []

    matches = []
    for line in result.stdout.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("type") != "match":
            continue
        data = entry["data"]
        path_text = data.get("path", {}).get("text", "")
        line_number = data.get("line_number", 0)
        lines_data = data.get("lines", {})
        content = lines_data.get("text", "").rstrip("\n")
        matches.append({
            "file": path_text,
            "line": line_number,
            "content": content,
            "context": "",
        })
        if len(matches) >= max_results:
            break
    return matches


def _run_python_search(project_path: Path, pattern: str, file_filter: str,
                       context_lines: int, max_results: int) -> list:
    """Fallback pure-Python regex search."""
    import fnmatch

    all_exts = [ext for exts in LANGUAGE_EXTENSIONS.values() for ext in exts]
    source_files = walk_source_files(project_path, extensions=all_exts)

    if file_filter:
        source_files = [f for f in source_files if fnmatch.fnmatch(f.name, file_filter)]

    try:
        compiled = re.compile(pattern)
    except re.error:
        return []

    matches = []
    for fpath in source_files:
        try:
            lines = fpath.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            if compiled.search(line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                ctx = "\n".join(lines[start:end])
                matches.append({
                    "file": str(fpath),
                    "line": i + 1,
                    "content": line.rstrip(),
                    "context": ctx,
                })
                if len(matches) >= max_results:
                    return matches
    return matches


# ---------------------------------------------------------------------------
# Strategy Detection
# ---------------------------------------------------------------------------


def detect_languages(project_path: Path) -> list:
    """Detect programming languages by scanning file extensions."""
    found = set()
    project_path = project_path.resolve()
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            ext = Path(f).suffix
            if ext in _EXT_TO_LANG:
                found.add(_EXT_TO_LANG[ext])
        if len(found) >= len(LANGUAGE_EXTENSIONS):
            break
    return sorted(found)


def detect_strategy(project_path: Path) -> dict:
    """Auto-detect the best navigation strategy for a project."""
    project_path = project_path.resolve()
    languages = detect_languages(project_path)

    config_files = []
    for name in ("tsconfig.json", "package.json", "Cargo.toml", "go.mod",
                 "pyproject.toml", "setup.py", "Gemfile", "pom.xml", "build.gradle"):
        if (project_path / name).exists():
            config_files.append(name)

    if "tsconfig.json" in config_files:
        strategy = "ts-aware"
    elif sum(1 for l in languages if l in ("python", "go", "rust", "java", "ruby", "typescript", "javascript")) >= 2:
        strategy = "polyglot"
    else:
        strategy = "grep-enhanced"

    return {"strategy": strategy, "languages": languages, "config_files": config_files}


# ---------------------------------------------------------------------------
# TypeScript-Aware Features
# ---------------------------------------------------------------------------

_TS_IMPORT_RE = re.compile(
    r'''import\s+(?:(?:type\s+)?(?:\{[^}]*\}|[\w*]+(?:\s*,\s*\{[^}]*\})?)\s+from\s+)?['"](.*?)['"]'''
)


def parse_ts_imports(file_path: Path) -> list:
    """Extract import sources from a TypeScript/JavaScript file using regex."""
    try:
        text = file_path.read_text(errors="replace")
    except OSError:
        return []

    results = []
    for line in text.splitlines():
        stripped = line.strip()
        m = _TS_IMPORT_RE.search(stripped)
        if m:
            source = m.group(1)
            specifiers = []
            spec_match = re.search(r'\{([^}]+)\}', stripped)
            if spec_match:
                specifiers = [s.strip().split(" as ")[0].strip()
                              for s in spec_match.group(1).split(",") if s.strip()]
            results.append({"source": source, "specifiers": specifiers})
    return results


def resolve_ts_import(import_source: str, from_file: Path, project_path: Path) -> Optional[Path]:
    """Resolve a TypeScript import to an actual file path."""
    project_path = project_path.resolve()

    if import_source.startswith("."):
        base = from_file.parent / import_source
        for candidate in [
            base.with_suffix(".ts"), base.with_suffix(".tsx"),
            base.with_suffix(".js"), base.with_suffix(".jsx"),
            base / "index.ts", base / "index.tsx",
            base / "index.js",
        ]:
            if candidate.exists():
                return candidate.resolve()
        return None

    # Try tsconfig paths
    tsconfig_path = project_path / "tsconfig.json"
    if tsconfig_path.exists():
        try:
            tsconfig = json.loads(tsconfig_path.read_text(errors="replace"))
            paths = tsconfig.get("compilerOptions", {}).get("paths", {})
            base_url = tsconfig.get("compilerOptions", {}).get("baseUrl", ".")
            base_dir = project_path / base_url
            for alias, targets in paths.items():
                alias_prefix = alias.replace("/*", "")
                if import_source.startswith(alias_prefix):
                    remainder = import_source[len(alias_prefix):].lstrip("/")
                    for target in targets:
                        target_prefix = target.replace("/*", "")
                        candidate_base = base_dir / target_prefix / remainder
                        for ext in [".ts", ".tsx", ".js"]:
                            candidate = candidate_base.with_suffix(ext)
                            if candidate.exists():
                                return candidate.resolve()
                        idx = candidate_base / "index.ts"
                        if idx.exists():
                            return idx.resolve()
        except (json.JSONDecodeError, OSError):
            pass

    return None


def build_ts_dependency_graph(project_path: Path, entry_files: list = None) -> dict:
    """Build a simplified dependency graph for TypeScript files."""
    project_path = project_path.resolve()
    ts_files = walk_source_files(project_path, extensions=[".ts", ".tsx", ".js", ".jsx"], max_files=500)

    if entry_files:
        ts_files = [Path(f).resolve() for f in entry_files if Path(f).exists()]

    graph = {}
    for fpath in ts_files:
        imports = parse_ts_imports(fpath)
        resolved = []
        for imp in imports:
            target = resolve_ts_import(imp["source"], fpath, project_path)
            if target:
                resolved.append(str(target))
        graph[str(fpath)] = resolved
    return graph


# ---------------------------------------------------------------------------
# Polyglot Features
# ---------------------------------------------------------------------------


def generate_language_patterns(pattern: str, languages: list) -> dict:
    """Generate language-specific search patterns from a generic pattern."""
    results = {}
    for lang in languages:
        specific = [pattern]
        if lang == "python":
            specific.append(rf"def\s+{pattern}")
            specific.append(rf"class\s+{pattern}")
        elif lang in ("typescript", "javascript"):
            specific.append(rf"(?:export\s+)?(?:function|const|class|interface|type)\s+{pattern}")
        elif lang == "go":
            specific.append(rf"func\s+(?:\([^)]*\)\s+)?{pattern}")
            specific.append(rf"type\s+{pattern}\s+(?:struct|interface)")
        elif lang == "rust":
            specific.append(rf"(?:pub\s+)?(?:fn|struct|enum|trait|type)\s+{pattern}")
        elif lang == "java":
            specific.append(rf"(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|enum)\s+{pattern}")
        elif lang == "ruby":
            specific.append(rf"(?:def|class|module)\s+{pattern}")
        results[lang] = specific
    return results


# ---------------------------------------------------------------------------
# Search Functions
# ---------------------------------------------------------------------------


def search_pattern(project_path: Path, pattern: str, strategy: str = "grep-enhanced",
                   scope: str = "repo", file_filter: str = None) -> list:
    """Search for a pattern in the codebase using the selected strategy."""
    project_path = project_path.resolve()

    if strategy == "ts-aware":
        enhanced_patterns = [pattern]
        enhanced_patterns.append(rf"import\s+.*{pattern}")
        enhanced_patterns.append(rf"export\s+.*{pattern}")
        combined = "|".join(f"(?:{p})" for p in enhanced_patterns)
        ts_filter = file_filter or "*.{ts,tsx,js,jsx}"
        return run_ripgrep(project_path, combined, file_filter=ts_filter)

    if strategy == "polyglot":
        languages = detect_languages(project_path)
        lang_patterns = generate_language_patterns(pattern, languages)
        all_matches = []
        for lang, patterns in lang_patterns.items():
            exts = LANGUAGE_EXTENSIONS.get(lang, [])
            for ext in exts:
                for p in patterns:
                    matches = run_ripgrep(project_path, p, file_filter=f"*{ext}",
                                          max_results=20)
                    all_matches.extend(matches)
        seen = set()
        deduped = []
        for m in all_matches:
            key = (m["file"], m["line"])
            if key not in seen:
                seen.add(key)
                deduped.append(m)
        return deduped[:100]

    # grep-enhanced (default)
    return run_ripgrep(project_path, pattern, file_filter=file_filter)


def search_similar_patterns(project_path: Path, reference_code: str,
                            strategy: str = "grep-enhanced") -> list:
    """Find code similar to the reference snippet."""
    identifiers = re.findall(r'\b[a-zA-Z_]\w{2,}\b', reference_code)
    if not identifiers:
        return []

    from collections import Counter
    counts = Counter(identifiers)
    keywords = {"import", "from", "const", "let", "var", "function", "return",
                "class", "def", "self", "this", "if", "else", "for", "while",
                "export", "async", "await", "type", "interface", "pub", "fn",
                "use", "mod", "struct", "enum", "impl", "None", "True", "False"}
    top = [word for word, _ in counts.most_common(10) if word not in keywords]

    if not top:
        return []

    pattern = "|".join(re.escape(t) for t in top[:5])
    return search_pattern(project_path, pattern, strategy=strategy)


def find_related_files(project_path: Path, file_path: str,
                       strategy: str = "grep-enhanced") -> list:
    """Find files related to a given file (imports, exports, tests, config)."""
    project_path = project_path.resolve()
    target = Path(file_path).resolve()
    related = set()

    stem = target.stem
    # Find test files
    for suffix in [".spec", ".test", "_test", "_spec"]:
        for ext in [".ts", ".tsx", ".js", ".py", ".go", ".rs"]:
            candidate = target.parent / f"{stem}{suffix}{ext}"
            if candidate.exists():
                related.add(str(candidate))

    if strategy == "ts-aware" and target.suffix in (".ts", ".tsx", ".js", ".jsx"):
        imports = parse_ts_imports(target)
        for imp in imports:
            resolved = resolve_ts_import(imp["source"], target, project_path)
            if resolved:
                related.add(str(resolved))
        # Find files that import this one
        rel = target.relative_to(project_path)
        import_ref = str(rel.with_suffix("")).replace("\\", "/")
        matches = run_ripgrep(project_path, re.escape(import_ref),
                              file_filter="*.{ts,tsx,js,jsx}", max_results=20)
        for m in matches:
            if m["file"] != str(target):
                related.add(m["file"])

    elif strategy == "polyglot":
        basename = target.name
        matches = run_ripgrep(project_path, re.escape(stem), max_results=30)
        for m in matches:
            if m["file"] != str(target):
                related.add(m["file"])

    else:
        matches = run_ripgrep(project_path, re.escape(stem), max_results=30)
        for m in matches:
            if m["file"] != str(target):
                related.add(m["file"])

    return sorted(related)


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def main():
    """CLI entry point for standalone usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Codebase navigation for QRALPH")
    sub = parser.add_subparsers(dest="command")

    detect_cmd = sub.add_parser("detect", help="Detect project strategy")
    detect_cmd.add_argument("path", type=str, help="Project path")

    search_cmd = sub.add_parser("search", help="Search for a pattern")
    search_cmd.add_argument("path", type=str, help="Project path")
    search_cmd.add_argument("pattern", type=str, help="Regex pattern")
    search_cmd.add_argument("--strategy", default=None, help="Search strategy")
    search_cmd.add_argument("--filter", default=None, help="File glob filter")

    related_cmd = sub.add_parser("related", help="Find related files")
    related_cmd.add_argument("path", type=str, help="Project path")
    related_cmd.add_argument("file", type=str, help="File to find relations for")
    related_cmd.add_argument("--strategy", default=None, help="Search strategy")

    graph_cmd = sub.add_parser("graph", help="Build TS dependency graph")
    graph_cmd.add_argument("path", type=str, help="Project path")

    args = parser.parse_args()

    if args.command == "detect":
        result = detect_strategy(Path(args.path))
        print(json.dumps(result, indent=2))

    elif args.command == "search":
        project = Path(args.path)
        strategy = args.strategy or detect_strategy(project)["strategy"]
        matches = search_pattern(project, args.pattern, strategy=strategy,
                                 file_filter=args.filter)
        print(json.dumps(matches, indent=2))

    elif args.command == "related":
        project = Path(args.path)
        strategy = args.strategy or detect_strategy(project)["strategy"]
        files = find_related_files(project, args.file, strategy=strategy)
        print(json.dumps(files, indent=2))

    elif args.command == "graph":
        graph = build_ts_dependency_graph(Path(args.path))
        print(json.dumps(graph, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
