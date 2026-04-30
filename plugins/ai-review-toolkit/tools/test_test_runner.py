"""Tests for test-runner.py — discovery, execution, finding generation, and CLI."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

# Import the module under test via shared _loader.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools._loader import load_sibling
test_runner = load_sibling("test-runner.py")

# Aliases for readability
discover_tests = test_runner.discover_tests
run_tests = test_runner.run_tests
failures_to_findings = test_runner.failures_to_findings
RunSpec = test_runner.RunSpec
RunResult = test_runner.RunResult
RunResults = test_runner.RunResults
main = test_runner.main


# -----------------------------------------------------------------------
# Discovery tests
# -----------------------------------------------------------------------


class TestDiscoveryPytest:
    """Discovery finds *_test.py and test_*.py files."""

    def test_finds_suffix_test_py(self, tmp_path: Path) -> None:
        (tmp_path / "widget_test.py").write_text("def test_x(): pass")
        specs = discover_tests(str(tmp_path / "widget.py"))
        assert any(s.type == "pytest" and "widget_test.py" in s.path for s in specs)

    def test_finds_prefix_test_py(self, tmp_path: Path) -> None:
        (tmp_path / "test_widget.py").write_text("def test_x(): pass")
        specs = discover_tests(str(tmp_path / "widget.py"))
        assert any(s.type == "pytest" and "test_widget.py" in s.path for s in specs)

    def test_finds_tests_in_tests_subdir(self, tmp_path: Path) -> None:
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_smoke.py").write_text("def test_s(): pass")
        specs = discover_tests(str(tmp_path / "app.py"))
        assert any(s.type == "pytest" and "test_smoke.py" in s.path for s in specs)


class TestDiscoveryVitest:
    """Discovery finds *.spec.ts and *.test.ts files."""

    def test_finds_spec_ts(self, tmp_path: Path) -> None:
        (tmp_path / "widget.spec.ts").write_text("test('works', () => {})")
        specs = discover_tests(str(tmp_path / "widget.ts"))
        assert any(s.type == "vitest" and "widget.spec.ts" in s.path for s in specs)

    def test_finds_test_ts(self, tmp_path: Path) -> None:
        (tmp_path / "widget.test.ts").write_text("test('works', () => {})")
        specs = discover_tests(str(tmp_path / "widget.ts"))
        assert any(s.type == "vitest" and "widget.test.ts" in s.path for s in specs)


class TestDiscoveryMakefile:
    """Discovery finds Makefile with a test target."""

    def test_finds_makefile_with_test_target(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("test:\n\techo ok\n")
        specs = discover_tests(str(tmp_path / "module.py"))
        assert any(s.type == "make" for s in specs)

    def test_ignores_makefile_without_test_target(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("build:\n\techo build\n")
        specs = discover_tests(str(tmp_path / "module.py"))
        assert not any(s.type == "make" for s in specs)


class TestDiscoveryRubric:
    """Rubric file discovery for non-code artifacts."""

    def test_finds_rubric_md(self, tmp_path: Path) -> None:
        (tmp_path / "article.rubric.md").write_text("# Rubric\n- Clear\n")
        specs = discover_tests(str(tmp_path / "article.md"))
        assert any(s.type == "rubric" and "article.rubric.md" in s.path for s in specs)

    def test_finds_rubric_json(self, tmp_path: Path) -> None:
        (tmp_path / "schema.rubric.json").write_text('{"criteria": []}')
        specs = discover_tests(str(tmp_path / "schema.json"))
        assert any(s.type == "rubric" and "schema.rubric.json" in s.path for s in specs)


class TestDiscoveryEmpty:
    """Discovery returns empty list when no tests found."""

    def test_no_tests_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("x = 1")
        specs = discover_tests(str(tmp_path / "module.py"))
        assert specs == []

    def test_nonexistent_path_returns_empty(self) -> None:
        specs = discover_tests("/nonexistent/path/module.py")
        assert specs == []


class TestDiscoveryScripts:
    """Discovery finds executable test/validate/check scripts."""

    def test_finds_executable_test_script(self, tmp_path: Path) -> None:
        script = tmp_path / "test_integration.sh"
        script.write_text("#!/bin/bash\necho ok")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        specs = discover_tests(str(tmp_path))
        assert any(s.type == "script" and "test_integration.sh" in s.path for s in specs)

    def test_finds_validate_script(self, tmp_path: Path) -> None:
        script = tmp_path / "validate_output.sh"
        script.write_text("#!/bin/bash\necho ok")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        specs = discover_tests(str(tmp_path))
        assert any(s.type == "script" and "validate_output.sh" in s.path for s in specs)


class TestDiscoveryPathQuoting:
    """Paths with spaces are properly quoted in commands."""

    def test_pytest_command_quotes_path_with_spaces(self, tmp_path: Path) -> None:
        spaced_dir = tmp_path / "my project"
        spaced_dir.mkdir()
        (spaced_dir / "test_widget.py").write_text("def test_x(): pass")
        specs = discover_tests(str(spaced_dir / "widget.py"))
        pytest_specs = [s for s in specs if s.type == "pytest"]
        assert len(pytest_specs) == 1
        # Path should be quoted (single-quoted by shlex.quote)
        assert "'" in pytest_specs[0].command or '"' in pytest_specs[0].command

    def test_makefile_command_quotes_path_with_spaces(self, tmp_path: Path) -> None:
        spaced_dir = tmp_path / "my project"
        spaced_dir.mkdir()
        (spaced_dir / "Makefile").write_text("test:\n\techo ok\n")
        specs = discover_tests(str(spaced_dir / "module.py"))
        make_specs = [s for s in specs if s.type == "make"]
        assert len(make_specs) == 1
        assert "'" in make_specs[0].command or '"' in make_specs[0].command


class TestDiscoveryExplicitCmd:
    """Explicit --test-cmd override takes precedence."""

    def test_explicit_cmd_returns_single_spec(self, tmp_path: Path) -> None:
        specs = discover_tests(str(tmp_path), test_cmd="echo ok")
        assert len(specs) == 1
        assert specs[0].type == "script"
        assert specs[0].command == "echo ok"


# -----------------------------------------------------------------------
# Execution tests
# -----------------------------------------------------------------------


class TestExecution:
    """Execution runs tests and captures output."""

    def test_passing_test(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("def test_pass(): assert True")
        spec = RunSpec(
            path=str(test_file),
            type="pytest",
            command=f"{sys.executable} -m pytest {test_file} -v",
            description="pytest: test_ok.py",
        )
        results = run_tests([spec])
        assert results.all_passed is True
        assert results.results[0].passed is True
        assert results.results[0].exit_code == 0

    def test_failing_test_captures_output(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_fail.py"
        test_file.write_text('def test_bad(): assert False, "deliberate failure"')
        spec = RunSpec(
            path=str(test_file),
            type="pytest",
            command=f"{sys.executable} -m pytest {test_file} -v",
            description="pytest: test_fail.py",
        )
        results = run_tests([spec])
        assert results.all_passed is False
        assert results.results[0].passed is False
        assert results.results[0].exit_code != 0
        combined = results.results[0].stdout + results.results[0].stderr
        assert "deliberate failure" in combined or "AssertionError" in combined or "FAILED" in combined

    def test_timeout_respected(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_slow.py"
        test_file.write_text("import time\ndef test_hang(): time.sleep(30)")
        spec = RunSpec(
            path=str(test_file),
            type="pytest",
            command=f"{sys.executable} -m pytest {test_file} -v",
            description="pytest: test_slow.py",
        )
        results = run_tests([spec], timeout=2)
        assert results.all_passed is False
        assert results.results[0].passed is False
        assert results.results[0].exit_code == -1
        assert "timed out" in results.results[0].stderr.lower()

    def test_rubric_reads_content(self, tmp_path: Path) -> None:
        rubric = tmp_path / "style.rubric.md"
        rubric.write_text("# Style\n- Be clear\n- Be concise\n")
        spec = RunSpec(
            path=str(rubric),
            type="rubric",
            command=f"cat {rubric}",
            description="rubric: style.rubric.md",
        )
        results = run_tests([spec])
        assert results.all_passed is True
        assert "Be clear" in results.results[0].stdout


# -----------------------------------------------------------------------
# TestResults aggregate behavior
# -----------------------------------------------------------------------


class TestResultsAggregation:
    """RunResults.all_passed and summary correctness."""

    def test_all_passed_true_when_all_pass(self) -> None:
        r1 = RunResult(
            spec=RunSpec("a", "pytest", "echo ok", "t1"),
            passed=True, exit_code=0, stdout="", stderr="", duration_seconds=0.1,
        )
        r2 = RunResult(
            spec=RunSpec("b", "pytest", "echo ok", "t2"),
            passed=True, exit_code=0, stdout="", stderr="", duration_seconds=0.2,
        )
        tr = RunResults(results=[r1, r2], all_passed=True, summary="2/2 passed")
        assert tr.all_passed is True

    def test_all_passed_false_when_any_fail(self) -> None:
        r1 = RunResult(
            spec=RunSpec("a", "pytest", "echo ok", "t1"),
            passed=True, exit_code=0, stdout="", stderr="", duration_seconds=0.1,
        )
        r2 = RunResult(
            spec=RunSpec("b", "pytest", "echo fail", "t2"),
            passed=False, exit_code=1, stdout="", stderr="error", duration_seconds=0.2,
        )
        tr = RunResults(results=[r1, r2], all_passed=False, summary="1/2 passed, 1 failed")
        assert tr.all_passed is False

    def test_summary_format(self, tmp_path: Path) -> None:
        pass_file = tmp_path / "test_a.py"
        pass_file.write_text("def test_a(): pass")
        fail_file = tmp_path / "test_b.py"
        fail_file.write_text("def test_b(): assert False")
        specs = [
            RunSpec(str(pass_file), "pytest", f"{sys.executable} -m pytest {pass_file} -v", "t1"),
            RunSpec(str(fail_file), "pytest", f"{sys.executable} -m pytest {fail_file} -v", "t2"),
        ]
        results = run_tests(specs)
        assert results.summary == "1/2 passed, 1 failed"

    def test_empty_specs_all_passed(self) -> None:
        results = run_tests([])
        assert results.all_passed is True
        assert results.summary == "0/0 passed"


# -----------------------------------------------------------------------
# Finding generation
# -----------------------------------------------------------------------


class TestFindingGeneration:
    """Failures auto-classified as findings with correct schema."""

    def _make_failing_results(self) -> RunResults:
        r = RunResult(
            spec=RunSpec("mod.py", "pytest", "pytest mod.py", "pytest: mod.py"),
            passed=False,
            exit_code=1,
            stdout="",
            stderr='File "mod.py", line 42\nAssertionError: expected True',
            duration_seconds=0.5,
        )
        return RunResults(results=[r], all_passed=False, summary="0/1 passed, 1 failed")

    def test_finding_schema_keys(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=1)
        assert len(findings) == 1
        f = findings[0]
        required_keys = {"id", "severity", "title", "requirement", "finding", "recommendation", "source", "evidence", "round"}
        assert required_keys.issubset(f.keys())

    def test_round_1_is_p1(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=1)
        assert findings[0]["severity"] == "P1"

    def test_round_2_is_p0_regression(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=2)
        assert findings[0]["severity"] == "P0"

    def test_source_is_test_runner(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=1)
        assert findings[0]["source"] == "test-runner"

    def test_evidence_extracted_from_traceback(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=1)
        assert findings[0]["evidence"] == "mod.py:42"

    def test_requirement_is_r5(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=1)
        assert findings[0]["requirement"] == "R5"

    def test_finding_id_uses_t_prefix(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=1)
        assert findings[0]["id"] == "P1-T001"

    def test_finding_id_p0_uses_t_prefix(self) -> None:
        tr = self._make_failing_results()
        findings = failures_to_findings(tr, round_num=2)
        assert findings[0]["id"] == "P0-T001"

    def test_run_tests_respects_round_num(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_fail.py"
        test_file.write_text('def test_bad(): assert False, "fail"')
        spec = RunSpec(
            path=str(test_file),
            type="pytest",
            command=f"{sys.executable} -m pytest {test_file} -v",
            description="pytest: test_fail.py",
        )
        results = run_tests([spec], round_num=2)
        assert results.failures_as_findings[0]["severity"] == "P0"
        assert results.failures_as_findings[0]["id"].startswith("P0-T")

    def test_rubric_over_512kb_fails(self, tmp_path: Path) -> None:
        rubric = tmp_path / "big.rubric.md"
        rubric.write_text("x" * (513 * 1024))
        spec = RunSpec(
            path=str(rubric),
            type="rubric",
            command=f"cat {rubric}",
            description="rubric: big.rubric.md",
        )
        results = run_tests([spec])
        assert results.all_passed is False
        assert "512KB" in results.results[0].stderr

    def test_missing_binary_caught(self, tmp_path: Path) -> None:
        spec = RunSpec(
            path=str(tmp_path),
            type="pytest",
            command="/nonexistent/binary arg1 arg2",
            description="pytest: missing binary",
        )
        results = run_tests([spec])
        assert results.all_passed is False
        assert results.results[0].exit_code == -2
        assert "Failed to start" in results.results[0].stderr

    def test_passing_results_produce_no_findings(self) -> None:
        r = RunResult(
            spec=RunSpec("ok.py", "pytest", "pytest ok.py", "pytest: ok.py"),
            passed=True, exit_code=0, stdout="ok", stderr="", duration_seconds=0.1,
        )
        tr = RunResults(results=[r], all_passed=True, summary="1/1 passed")
        findings = failures_to_findings(tr, round_num=1)
        assert findings == []


# -----------------------------------------------------------------------
# CLI tests
# -----------------------------------------------------------------------


class TestCLI:
    """CLI exit code and output behavior."""

    def test_exit_code_0_on_all_pass(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("def test_pass(): assert True")
        artifact = tmp_path / "mod.py"
        artifact.write_text("x = 1")
        exit_code = main([str(artifact)])
        assert exit_code == 0

    def test_exit_code_1_on_failure(self, tmp_path: Path) -> None:
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("def test_fail(): assert False")
        artifact = tmp_path / "mod.py"
        artifact.write_text("x = 1")
        exit_code = main([str(artifact)])
        assert exit_code == 1

    def test_json_output_is_valid(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("def test_pass(): assert True")
        artifact = tmp_path / "mod.py"
        artifact.write_text("x = 1")
        main([str(artifact), "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["all_passed"] is True
        assert "summary" in data

    def test_no_tests_found_exit_0(self, tmp_path: Path) -> None:
        artifact = tmp_path / "mod.py"
        artifact.write_text("x = 1")
        exit_code = main([str(artifact)])
        assert exit_code == 0
