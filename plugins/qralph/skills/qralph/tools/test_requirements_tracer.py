#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""Tests for requirements-tracer.py — maps REQ-IDs to tests."""
import os
import sys
import tempfile

# Add tools directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_trace_requirements_to_tests():
    """Should find which tests reference which REQ-IDs."""
    from requirements_tracer import trace_requirements

    with tempfile.TemporaryDirectory() as tmp:
        test_file = os.path.join(tmp, "auth.spec.ts")
        with open(test_file, "w") as f:
            f.write('test("REQ-101 — user can login", () => { expect(true).toBe(true); });\n')
            f.write('test("REQ-102 — user can logout", () => { expect(true).toBe(true); });\n')

        requirements = ["REQ-101", "REQ-102", "REQ-103"]
        result = trace_requirements(tmp, requirements)
        assert result["REQ-101"]["covered"] is True
        assert result["REQ-102"]["covered"] is True
        assert result["REQ-103"]["covered"] is False
        assert "auth.spec.ts" in result["REQ-101"]["test_files"]


def test_trace_multiple_file_types():
    """Should scan .spec.ts, .test.ts, .spec.py, .test.py files."""
    from requirements_tracer import trace_requirements

    with tempfile.TemporaryDirectory() as tmp:
        for name, req_id in [("a.spec.ts", "REQ-201"), ("b.test.py", "REQ-202")]:
            with open(os.path.join(tmp, name), "w") as f:
                f.write(f'test("{req_id} — something", () => {{}});\n')

        result = trace_requirements(tmp, ["REQ-201", "REQ-202"])
        assert result["REQ-201"]["covered"] is True
        assert result["REQ-202"]["covered"] is True


def test_trace_empty_directory():
    """Should handle directory with no test files."""
    from requirements_tracer import trace_requirements

    with tempfile.TemporaryDirectory() as tmp:
        result = trace_requirements(tmp, ["REQ-301"])
        assert result["REQ-301"]["covered"] is False


def test_generate_coverage_report():
    """Should generate a markdown coverage report."""
    from requirements_tracer import generate_coverage_report

    trace_result = {
        "REQ-101": {"covered": True, "test_files": ["auth.spec.ts"]},
        "REQ-102": {"covered": False, "test_files": []},
    }
    report = generate_coverage_report(trace_result)
    assert "REQ-101" in report
    assert "REQ-102" in report
    assert "COVERED" in report.upper() or "covered" in report.lower()
    assert "MISSING" in report.upper() or "missing" in report.lower() or "NOT COVERED" in report.upper() or "not covered" in report.lower()


def test_trace_nested_directories():
    """Should recursively scan subdirectories."""
    from requirements_tracer import trace_requirements

    with tempfile.TemporaryDirectory() as tmp:
        sub = os.path.join(tmp, "src", "auth")
        os.makedirs(sub)
        with open(os.path.join(sub, "login.spec.ts"), "w") as f:
            f.write('test("REQ-401 — nested test", () => {});\n')

        result = trace_requirements(tmp, ["REQ-401"])
        assert result["REQ-401"]["covered"] is True
