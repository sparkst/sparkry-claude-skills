"""Loop driver for /qloop skill.

State machine that orchestrates iterative review-fix-verify cycles.
Enforces minimum 2 rounds, fix-ALL gate, stuck detection, and
max-round escalation. Pure state transitions -- no LLM calls.

Usage:
    python tools/loop-driver.py init --artifact PATH --requirements PATH [--reviewers N] [--threshold N] [--max-rounds N]
    python tools/loop-driver.py next
    python tools/loop-driver.py status
    python tools/loop-driver.py record-review --round N --reviewer INDEX --findings-file PATH
    python tools/loop-driver.py record-fixes --round N --resolutions-file PATH
    python tools/loop-driver.py reset
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve sibling tools for imports (hyphenated filenames)
# ---------------------------------------------------------------------------

try:
    from tools._loader import load_sibling as _load_sibling
    from tools._state_io import load_json_state, now_iso, write_state_atomic
except ImportError:
    from _loader import load_sibling as _load_sibling
    from _state_io import load_json_state, now_iso, write_state_atomic


_team_selector_mod: Any = None
_finding_parser_mod: Any = None


def _get_team_selector() -> Any:
    global _team_selector_mod
    if _team_selector_mod is None:
        _team_selector_mod = _load_sibling("team-selector.py")
    return _team_selector_mod


def _get_finding_parser() -> Any:
    global _finding_parser_mod
    if _finding_parser_mod is None:
        _finding_parser_mod = _load_sibling("finding-parser.py")
    return _finding_parser_mod

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR_NAME = ".qloop"
STATE_FILE_NAME = "state.json"
MIN_ROUNDS_HARD = 2


# ---------------------------------------------------------------------------
# State I/O
# ---------------------------------------------------------------------------

def _state_dir(base: str = ".") -> Path:
    return Path(base) / STATE_DIR_NAME


def _state_path(base: str = ".") -> Path:
    return _state_dir(base) / STATE_FILE_NAME


def _read_state(base: str = ".") -> dict[str, Any]:
    path = _state_path(base)
    return load_json_state(path, "Run 'init' first.")


def _write_state(state: dict[str, Any], base: str = ".") -> None:
    target = _state_path(base)
    target.parent.mkdir(parents=True, exist_ok=True)
    write_state_atomic(target, state)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_round(state: dict[str, Any], num: int) -> dict[str, Any] | None:
    """Return the round dict for the given round number, or None."""
    for r in state.get("rounds", []):
        if r["round_num"] == num:
            return r
    return None


def _get_current_round(state: dict[str, Any]) -> dict[str, Any] | None:
    """Return the round dict for current_round, or None."""
    return _get_round(state, state.get("current_round", 0))


def _new_round(round_num: int) -> dict[str, Any]:
    return {
        "round_num": round_num,
        "phase": "initialized",
        "findings": [],
        "reviewer_findings": [],
        "test_results": {},
        "fix_resolutions": [],
        "synthesis": {},
        "timestamp": now_iso(),
    }


def _extract_p0_p1_titles(findings: list[dict[str, Any]]) -> set[str]:
    """Extract normalized titles of P0/P1 findings for stuck detection."""
    titles: set[str] = set()
    for f in findings:
        sev = str(f.get("severity", ""))
        if sev in ("P0", "P1"):
            titles.add(re.sub(r'\s+', ' ', str(f.get("title", "")).strip().lower()))
    return titles


def _count_p0_p1(findings: list[dict[str, Any]]) -> int:
    return sum(1 for f in findings if str(f.get("severity", "")) in ("P0", "P1"))


# ---------------------------------------------------------------------------
# init_loop
# ---------------------------------------------------------------------------

def init_loop(
    artifact_path: str,
    requirements_path: str,
    reviewer_count: int | None = None,
    threshold: int = 0,
    max_rounds: int = 5,
    base: str = ".",
) -> dict[str, Any]:
    """Create loop state. Select team. Return state."""
    artifact_abs = str(Path(artifact_path).resolve())
    requirements_abs = str(Path(requirements_path).resolve())

    if not Path(artifact_abs).is_file():
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")
    if not Path(requirements_abs).is_file():
        raise FileNotFoundError(f"Requirements not found: {requirements_path}")

    # Read artifact for domain classification
    try:
        with open(artifact_abs, "r", encoding="utf-8", errors="replace") as fh:
            artifact_content = fh.read()
    except OSError:
        artifact_content = ""

    # Select team — enforce minimum 2 reviewers (R3: N clean-context agents)
    description = artifact_content[:2000] if artifact_content else artifact_path
    min_rev = max(reviewer_count or 2, 2)
    max_rev = max(reviewer_count or 5, min_rev)
    team_agents = _get_team_selector().select_team(
        description=description,
        artifact_path=artifact_abs,
        min_reviewers=min_rev,
        max_reviewers=max_rev,
    )
    team = [
        {
            "name": a.name,
            "domains": a.domains,
            "model": a.model,
            "description": a.description,
            "review_lens": a.review_lens,
        }
        for a in team_agents
    ]

    state: dict[str, Any] = {
        "artifact_path": artifact_abs,
        "requirements_path": requirements_abs,
        "threshold": threshold,
        "max_rounds": max(max_rounds, MIN_ROUNDS_HARD),
        "min_rounds": MIN_ROUNDS_HARD,
        "current_round": 1,
        "team": team,
        "rounds": [_new_round(1)],
        "status": "initialized",
        "created_at": now_iso(),
    }

    _write_state(state, base)
    return state


# ---------------------------------------------------------------------------
# next_action
# ---------------------------------------------------------------------------

def next_action(state: dict[str, Any], base_dir: str = ".", confirm: bool = False) -> dict[str, Any]:
    """State machine transition. Returns an action dict.

    Persists state to *base_dir* before returning any action that
    mutates state (converged, escalated, round advancement).

    When *confirm* is True and status is ``escalation_pending``,
    accepts the escalated findings and advances to the next round.
    """
    status = state.get("status", "initialized")
    current_round_num = state.get("current_round", 1)
    current_round = _get_current_round(state)

    if current_round is None:
        return {"action": "gate", "message": "No current round found. Run init first."}

    phase = current_round.get("phase", "initialized")

    # --- Terminal states ---
    if status == "converged":
        synthesis = current_round.get("synthesis", {})
        return {"action": "converged", "summary": synthesis.get("summary", "All findings resolved.")}

    if status == "escalated":
        return {
            "action": "escalated",
            "reason": state.get("escalation_reason", "Max rounds reached without convergence."),
            "unresolved": state.get("escalation_unresolved", []),
        }

    if status == "escalation_pending":
        if confirm:
            current_round["phase"] = "resolved"
            next_round_num = current_round_num + 1
            state["current_round"] = next_round_num
            state["rounds"].append(_new_round(next_round_num))
            state["status"] = "initialized"
            _write_state(state, base_dir)
            return {"action": "run_tests", "round": next_round_num}
        else:
            escalated = [
                r for r in current_round.get("fix_resolutions", [])
                if str(r.get("status", "")) == "ESCALATED"
            ]
            return {
                "action": "escalation_review",
                "escalated_resolutions": escalated,
                "message": "ESCALATED findings require user decision. Re-resolve findings and call record-fixes, or call next with --confirm to accept and advance.",
            }

    # --- Phase transitions within a round ---

    # Phase: initialized -> run tests
    if phase == "initialized":
        return {"action": "run_tests", "round": current_round_num}

    # Phase: tests_done -> spawn reviewers
    if phase == "tests_done":
        prompts = []
        for i, agent in enumerate(state.get("team", [])):
            prompt = get_reviewer_prompt(state, i, current_round_num)
            prompts.append(prompt)
        return {"action": "spawn_reviewers", "prompts": prompts}

    # Phase: reviewing -> waiting for all reviewers
    if phase == "reviewing":
        # Check if all reviewers have reported
        reviewer_findings = current_round.get("reviewer_findings", [])
        expected = len(state.get("team", []))
        reported = len(reviewer_findings)
        if reported < expected:
            return {
                "action": "gate",
                "message": f"Waiting for reviewers: {reported}/{expected} reported.",
            }
        # All reported -> synthesize
        return {"action": "synthesize"}

    # Phase: synthesized -> spawn fixer (or check convergence for min_rounds)
    if phase == "synthesized":
        findings = current_round.get("findings", [])
        converged, reason = _get_finding_parser().check_convergence(findings, state.get("threshold", 0))

        if converged and current_round_num >= state.get("min_rounds", MIN_ROUNDS_HARD):
            state["status"] = "converged"
            current_round["phase"] = "resolved"
            synthesis_summary = (
                f"Converged after {current_round_num} round(s). "
                f"{reason}. "
                f"Severity counts: {json.dumps(_get_finding_parser().count_by_severity(findings))}"
            )
            current_round["synthesis"]["summary"] = synthesis_summary
            _write_state(state, base_dir)
            return {"action": "converged", "summary": synthesis_summary}

        if converged and current_round_num < state.get("min_rounds", MIN_ROUNDS_HARD):
            # Must still do more rounds even if converged early
            # Advance to next round for re-review
            next_round_num = current_round_num + 1
            state["current_round"] = next_round_num
            state["rounds"].append(_new_round(next_round_num))
            state["status"] = "initialized"
            _write_state(state, base_dir)
            return {"action": "run_tests", "round": state["current_round"]}

        # Not converged -- check max rounds
        if current_round_num >= state.get("max_rounds", 5):
            unresolved = [
                f for f in findings
                if str(f.get("severity", "")) in ("P0", "P1")
            ]
            state["status"] = "escalated"
            state["escalation_reason"] = f"Max rounds ({state['max_rounds']}) reached without convergence. {reason}."
            state["escalation_unresolved"] = unresolved
            _write_state(state, base_dir)
            return {
                "action": "escalated",
                "reason": state["escalation_reason"],
                "unresolved": unresolved,
            }

        # Not converged, rounds remaining -> fix
        prompt = get_fixer_prompt(state, current_round_num)
        return {"action": "spawn_fixer", "prompt": prompt}

    # Phase: fixing -> waiting for fix resolutions
    if phase == "fixing":
        resolutions = current_round.get("fix_resolutions", [])
        findings = current_round.get("findings", [])
        if not resolutions:
            return {"action": "gate", "message": "Waiting for fix resolutions."}

        complete, missing = check_fix_completeness(findings, resolutions)
        if not complete:
            return {
                "action": "validate_fixes",
                "required_findings": missing,
            }

        # Check for ESCALATED resolutions — pause for user input
        escalated = [
            r for r in resolutions
            if str(r.get("status", "")) == "ESCALATED"
        ]
        if escalated:
            state["status"] = "escalation_pending"
            _write_state(state, base_dir)
            return {
                "action": "escalation_review",
                "escalated_resolutions": escalated,
                "message": "ESCALATED findings require user decision. Options: accept escalation (call next with --confirm), or re-resolve the findings and call record-fixes again.",
            }

        # Fixes complete -> advance to next round
        current_round["phase"] = "resolved"
        next_round_num = current_round_num + 1

        # Stuck detection: compare with previous round
        prev_round = _get_round(state, current_round_num - 1)
        if prev_round is not None:
            prev_titles = _extract_p0_p1_titles(prev_round.get("findings", []))
            curr_titles = _extract_p0_p1_titles(findings)
            prev_count = _count_p0_p1(prev_round.get("findings", []))
            curr_count = _count_p0_p1(findings)
            if curr_count > 0 and prev_titles == curr_titles and prev_count == curr_count:
                stuck_findings = [
                    f for f in findings
                    if str(f.get("severity", "")) in ("P0", "P1")
                ]
                state["status"] = "escalated"
                state["escalation_reason"] = (
                    f"Stuck: identical P0/P1 findings in rounds "
                    f"{current_round_num - 1} and {current_round_num}. "
                    f"Fix approach is not working."
                )
                state["escalation_unresolved"] = stuck_findings
                _write_state(state, base_dir)
                return {
                    "action": "escalated",
                    "reason": state["escalation_reason"],
                    "unresolved": stuck_findings,
                }

        # Advance
        state["current_round"] = next_round_num
        state["rounds"].append(_new_round(next_round_num))
        state["status"] = "initialized"
        _write_state(state, base_dir)
        return {"action": "run_tests", "round": state["current_round"]}

    # Phase: resolved (should not reach here via next_action in normal flow)
    if phase == "resolved":
        findings = current_round.get("findings", [])
        resolutions = current_round.get("fix_resolutions", [])
        if findings and not resolutions:
            return {
                "action": "error",
                "message": (
                    f"Round {current_round_num} has {len(findings)} finding(s) "
                    f"but no fix_resolutions. Cannot advance."
                ),
            }
        # Check if loop is done or needs another round
        if status == "converged":
            return {"action": "converged", "summary": "Loop completed."}
        return {"action": "gate", "message": "Round resolved. Run next to advance."}

    return {"action": "gate", "message": f"Unknown phase: {phase}"}


# ---------------------------------------------------------------------------
# record_test_results
# ---------------------------------------------------------------------------

def record_test_results(
    state: dict[str, Any],
    round_num: int,
    test_results: dict[str, Any],
) -> dict[str, Any]:
    """Record test results for a round, transitioning phase to tests_done.

    Mutates state in-memory and returns it; caller must persist via _write_state().
    """
    rnd = _get_round(state, round_num)
    if rnd is None:
        raise ValueError(f"Round {round_num} not found in state.")

    if rnd["phase"] != "initialized":
        raise ValueError(
            f"Round {round_num} is in phase {rnd['phase']!r}; "
            f"can only record tests when phase is 'initialized'."
        )

    rnd["test_results"] = test_results

    # Round > 1: upgrade test failure findings from P1 to P0 (regressions)
    if round_num > 1:
        failures = test_results.get("failures_as_findings", [])
        for finding in failures:
            if str(finding.get("severity", "")) == "P1":
                old_id = str(finding.get("id", ""))
                finding["severity"] = "P0"
                if old_id.startswith("P1-"):
                    finding["id"] = "P0-" + old_id[3:]

    rnd["phase"] = "tests_done"
    state["status"] = "tests_done"
    return state


# ---------------------------------------------------------------------------
# record_review
# ---------------------------------------------------------------------------

def record_review(
    state: dict[str, Any],
    round_num: int,
    reviewer_index: int,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Record a reviewer's findings for a given round.

    Mutates state in-memory and returns it; caller must persist via _write_state().
    """
    current = state.get("current_round", 0)
    if round_num != current:
        raise ValueError(
            f"Round {round_num} is not the current round ({current})."
        )

    reviewer_count = len(state.get("team", []))
    if reviewer_count < 2:
        raise ValueError(
            f"reviewer_count must be at least 2; got {reviewer_count}."
        )
    if reviewer_index < 0 or reviewer_index >= reviewer_count:
        raise ValueError(
            f"reviewer_index {reviewer_index} out of bounds "
            f"(reviewer_count={reviewer_count})."
        )

    rnd = _get_round(state, round_num)
    if rnd is None:
        raise ValueError(f"Round {round_num} not found in state.")

    # Check for duplicate reviewer submission
    existing_findings = rnd.get("reviewer_findings", [])
    for rf in existing_findings:
        if rf.get("reviewer_index") == reviewer_index:
            raise ValueError(
                f"Reviewer {reviewer_index} already submitted findings "
                f"for round {round_num}."
            )

    if rnd["phase"] not in ("tests_done", "reviewing"):
        raise ValueError(
            f"Round {round_num} is in phase {rnd['phase']!r}; "
            f"can only accept reviews when phase is 'tests_done' or 'reviewing'."
        )

    # Store per-reviewer
    reviewer_findings = rnd.get("reviewer_findings", [])
    reviewer_findings.append({
        "reviewer_index": reviewer_index,
        "findings": findings,
        "timestamp": now_iso(),
    })
    rnd["reviewer_findings"] = reviewer_findings
    rnd["phase"] = "reviewing"
    state["status"] = "reviewing"

    # Check if all reviewers reported -> auto-synthesize
    expected = len(state.get("team", []))
    if len(reviewer_findings) >= expected:
        # Synthesize — pass test findings as separate reviewer list
        fp = _get_finding_parser()
        all_reviewer_lists = [rf["findings"] for rf in reviewer_findings]
        test_findings = rnd.get("test_results", {}).get("failures_as_findings", [])
        if test_findings:
            all_reviewer_lists.append(test_findings)
        warnings: list[dict[str, object]] = []
        synthesized = fp.synthesize_findings(all_reviewer_lists, warnings=warnings)

        rnd["findings"] = synthesized
        rnd["synthesis"] = {
            "counts": fp.count_by_severity(synthesized),
            "finding_count": len(synthesized),
            "dropped_count": len(warnings),
            "timestamp": now_iso(),
        }
        if warnings:
            rnd["synthesis"]["dropped_findings"] = warnings
        rnd["phase"] = "synthesized"

    return state


# ---------------------------------------------------------------------------
# record_fixes
# ---------------------------------------------------------------------------

def record_fixes(
    state: dict[str, Any],
    round_num: int,
    resolutions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Record fix resolutions. Validates ALL findings addressed.

    Mutates state in-memory and returns it; caller must persist via _write_state().
    """
    current = state.get("current_round", 0)
    if round_num != current:
        raise ValueError(
            f"Round {round_num} is not the current round ({current})."
        )

    rnd = _get_round(state, round_num)
    if rnd is None:
        raise ValueError(f"Round {round_num} not found in state.")

    if rnd["phase"] not in ("synthesized", "fixing"):
        raise ValueError(
            f"Round {round_num} is in phase {rnd['phase']!r}; "
            f"can only record fixes when phase is 'synthesized' or 'fixing'."
        )

    if not isinstance(resolutions, list):
        raise ValueError(
            f"resolutions must be a list, got {type(resolutions).__name__}"
        )
    rnd["fix_resolutions"] = resolutions
    rnd["phase"] = "fixing"
    state["status"] = "fixing"

    return state


# ---------------------------------------------------------------------------
# Prompt generation
# ---------------------------------------------------------------------------

def get_reviewer_prompt(
    state: dict[str, Any],
    reviewer_index: int,
    round_num: int,
) -> str:
    """Generate reviewer prompt. Round 2+ includes prior findings + diff summary."""
    team = state.get("team", [])
    if reviewer_index < 0 or reviewer_index >= len(team):
        raise ValueError(f"Reviewer index {reviewer_index} out of range (team size {len(team)}).")

    agent = team[reviewer_index]
    artifact_path = state.get("artifact_path", "")
    requirements_path = state.get("requirements_path", "")

    # Read artifact
    try:
        with open(artifact_path, "r", encoding="utf-8", errors="replace") as fh:
            artifact_content = fh.read()
    except OSError:
        artifact_content = f"[Could not read artifact at {artifact_path}]"

    # Read requirements
    try:
        with open(requirements_path, "r", encoding="utf-8", errors="replace") as fh:
            requirements_content = fh.read()
    except OSError:
        requirements_content = f"[Could not read requirements at {requirements_path}]"

    # Test results
    current_round = _get_round(state, round_num)
    test_summary = "No test results available."
    if current_round:
        tr = current_round.get("test_results", {})
        if tr:
            test_summary = tr.get("summary", "No test results available.")

    reviewer_name = agent["name"]
    review_lens = agent["review_lens"]

    prompt_parts = [
        f"You are a {reviewer_name} reviewing an artifact.",
        "",
        f"Your review lens: {review_lens}",
        "",
        "## Artifact",
        "",
        artifact_content,
        "",
        "## Requirements",
        "",
        requirements_content,
        "",
        "## Test Results",
        "",
        test_summary,
    ]

    # Round 2+ additions
    if round_num > 1:
        prev_round = _get_round(state, round_num - 1)
        if prev_round:
            prev_findings = prev_round.get("findings", [])
            if prev_findings:
                findings_text = _get_finding_parser().format_findings(prev_findings, fmt="markdown")
                prompt_parts.extend([
                    "",
                    f"## Prior Round Findings (Round {round_num - 1})",
                    "",
                    findings_text,
                ])

            prev_resolutions = prev_round.get("fix_resolutions", [])
            if prev_resolutions:
                res_lines = []
                for res in prev_resolutions:
                    fid = res.get("finding_id", "?")
                    status = res.get("status", "?")
                    desc = res.get("description", "")
                    evidence = res.get("evidence", "")
                    res_lines.append(f"- **{fid}**: {status} -- {desc}")
                    if evidence:
                        res_lines.append(f"  Evidence: {evidence}")
                prompt_parts.extend([
                    "",
                    "## Fix Resolutions Applied",
                    "",
                    "\n".join(res_lines),
                ])

            prompt_parts.extend([
                "",
                "## Verification Instructions",
                "",
                f"The artifact content above is the POST-FIX version (after round {round_num - 1} fixes). "
                "For each fix resolution listed above, navigate to the cited evidence location "
                "in the artifact and verify the fix is correct. Also check for NEW issues "
                "introduced by the fixes — regressions, broken logic, incomplete changes.",
            ])

    fp = _get_finding_parser()
    output_instructions = fp.REVIEWER_OUTPUT_INSTRUCTIONS.format(reviewer_name=reviewer_name)
    prompt_parts.extend([
        "",
        "## Instructions",
        "",
        f"Review the artifact against the requirements through your lens of {review_lens}.",
        "",
        output_instructions,
    ])

    return "\n".join(prompt_parts)


def get_fixer_prompt(state: dict[str, Any], round_num: int) -> str:
    """Generate fixer prompt with all findings and recommendations."""
    artifact_path = state.get("artifact_path", "")
    requirements_path = state.get("requirements_path", "")

    try:
        with open(artifact_path, "r", encoding="utf-8", errors="replace") as fh:
            artifact_content = fh.read()
    except OSError:
        artifact_content = f"[Could not read artifact at {artifact_path}]"

    try:
        with open(requirements_path, "r", encoding="utf-8", errors="replace") as fh:
            requirements_content = fh.read()
    except OSError:
        requirements_content = f"[Could not read requirements at {requirements_path}]"

    current_round = _get_round(state, round_num)
    findings: list[dict[str, Any]] = []
    test_summary = ""
    if current_round:
        findings = current_round.get("findings", [])
        tr = current_round.get("test_results", {})
        test_summary = tr.get("summary", "") if tr else ""

    findings_text = _get_finding_parser().format_findings(findings, fmt="markdown")

    prompt = f"""You are a fixer agent. Your job is to fix ALL findings from the review.

## Artifact

{artifact_content}

## Requirements

{requirements_content}

## Test Results

{test_summary}

## Findings to Fix (ALL must be addressed)

{findings_text}

## Instructions

Fix EVERY finding listed above. Every single one, regardless of severity (P0 through P3).

For each finding, produce a resolution with these fields:
- finding_id: the ID of the finding being resolved (e.g., P0-001)
- status: MUST be "FIXED" with evidence of the fix. No WONTFIX, DEFERRED, or OUT_OF_SCOPE.
- evidence: what changed and where (file:line for code, section:quote for content)
- description: brief explanation of the fix

If a finding is genuinely unfixable (requires external dependency, architectural constraint, or user decision), set status to "ESCALATED" with justification.

Output a JSON array of resolution objects. No other text."""

    return prompt


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

ALLOWED_STATUSES: set[str] = {"FIXED", "ESCALATED"}
PROHIBITED_STATUSES: set[str] = {"WONTFIX", "DEFERRED", "OUT_OF_SCOPE"}


def check_fix_completeness(
    findings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Returns (complete, missing_or_invalid_finding_ids).

    Every finding must have a corresponding resolution whose status is
    FIXED or ESCALATED.  Prohibited statuses (WONTFIX, DEFERRED,
    OUT_OF_SCOPE) are treated as invalid.
    """
    finding_ids: set[str] = {str(f["id"]) for f in findings if f.get("id")}

    valid_resolved_ids: set[str] = set()
    invalid_ids: list[str] = []
    for r in resolutions:
        fid = r.get("finding_id")
        if not fid:
            continue
        status = str(r.get("status", ""))
        if status not in ALLOWED_STATUSES:
            invalid_ids.append(str(fid))
        else:
            evidence = r.get("evidence")
            if not evidence or (isinstance(evidence, str) and not evidence.strip()):
                invalid_ids.append(str(fid))
            else:
                valid_resolved_ids.add(str(fid))

    missing = sorted((finding_ids - valid_resolved_ids) | (set(invalid_ids) - valid_resolved_ids))
    return (not missing, missing)


# ---------------------------------------------------------------------------
# Status / Reset
# ---------------------------------------------------------------------------

def get_status(base: str = ".") -> dict[str, Any]:
    """Read state, return summary."""
    try:
        state = _read_state(base)
    except (OSError, json.JSONDecodeError):
        return {"status": "no_state", "message": "No qloop state found. Run init first."}

    current_round = _get_current_round(state)
    phase = current_round.get("phase", "unknown") if current_round else "unknown"
    findings_count = len(current_round.get("findings", [])) if current_round else 0
    synthesis = current_round.get("synthesis", {}) if current_round else {}

    return {
        "status": state.get("status", "unknown"),
        "current_round": state.get("current_round", 0),
        "max_rounds": state.get("max_rounds", 0),
        "min_rounds": state.get("min_rounds", 0),
        "threshold": state.get("threshold", 0),
        "phase": phase,
        "reviewer_count": len(state.get("team", [])),
        "findings_count": findings_count,
        "severity_counts": synthesis.get("counts", {}),
        "team": [t.get("name", "") for t in state.get("team", [])],
        "artifact_path": state.get("artifact_path", ""),
        "total_rounds_completed": len([
            r for r in state.get("rounds", [])
            if r.get("phase") == "resolved"
        ]),
    }


def reset(base: str = ".") -> dict[str, str]:
    """Clear .qloop/ directory."""
    d = _state_dir(base)
    if d.is_dir():
        shutil.rmtree(d)
    return {"status": "reset", "message": "qloop state cleared."}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Loop driver for /qloop skill.")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # init
    init_p = subparsers.add_parser("init", help="Initialize a new review loop")
    init_p.add_argument("--artifact", required=True, help="Path to artifact")
    init_p.add_argument("--requirements", required=True, help="Path to requirements")
    init_p.add_argument("--reviewers", type=int, default=None, help="Number of reviewers")
    init_p.add_argument("--threshold", type=int, default=0, help="Convergence threshold for P2+P3")
    init_p.add_argument("--max-rounds", type=int, default=5, help="Maximum review rounds")

    # next
    next_parser = subparsers.add_parser("next", help="Get next action from state machine")
    next_parser.add_argument("--confirm", action="store_true", help="Confirm escalation_pending gate to advance")

    # status
    subparsers.add_parser("status", help="Show current loop status")

    # record-tests
    rec_test = subparsers.add_parser("record-tests", help="Record test results for a round")
    rec_test.add_argument("--round", type=int, required=True, help="Round number")
    rec_test.add_argument("--results-file", required=True, help="Path to test results JSON file")

    # record-review
    rec_rev = subparsers.add_parser("record-review", help="Record a reviewer's findings")
    rec_rev.add_argument("--round", type=int, required=True, help="Round number")
    rec_rev.add_argument("--reviewer", type=int, required=True, help="Reviewer index")
    rec_rev.add_argument("--findings-file", required=True, help="Path to findings JSON file")

    # record-fixes
    rec_fix = subparsers.add_parser("record-fixes", help="Record fix resolutions")
    rec_fix.add_argument("--round", type=int, required=True, help="Round number")
    rec_fix.add_argument("--resolutions-file", required=True, help="Path to resolutions JSON file")

    # reset
    subparsers.add_parser("reset", help="Clear loop state")

    args = parser.parse_args(argv)

    if args.command == "init":
        state = init_loop(
            artifact_path=args.artifact,
            requirements_path=args.requirements,
            reviewer_count=args.reviewers,
            threshold=args.threshold,
            max_rounds=args.max_rounds,
        )
        print(json.dumps(state, indent=2, default=str))
        return 0

    if args.command == "next":
        try:
            state = _read_state()
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        action = next_action(state, base_dir=".", confirm=getattr(args, "confirm", False))
        print(json.dumps(action, indent=2, default=str))
        return 0

    if args.command == "status":
        result = get_status()
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "record-tests":
        try:
            state = _read_state()
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        try:
            with open(args.results_file, "r", encoding="utf-8") as fh:
                test_results = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error reading results file: {exc}", file=sys.stderr)
            return 1
        try:
            state = record_test_results(state, args.round, test_results)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        _write_state(state)
        print(json.dumps({"status": "recorded", "round": args.round, "phase": "tests_done"}, indent=2))
        return 0

    if args.command == "record-review":
        try:
            state = _read_state()
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        try:
            with open(args.findings_file, "r", encoding="utf-8") as fh:
                findings = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error reading findings file: {exc}", file=sys.stderr)
            return 1
        try:
            state = record_review(state, args.round, args.reviewer, findings)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        _write_state(state)
        print(json.dumps({"status": "recorded", "round": args.round, "reviewer": args.reviewer}, indent=2))
        return 0

    if args.command == "record-fixes":
        try:
            state = _read_state()
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        try:
            with open(args.resolutions_file, "r", encoding="utf-8") as fh:
                resolutions = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error reading resolutions file: {exc}", file=sys.stderr)
            return 1
        try:
            state = record_fixes(state, args.round, resolutions)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        _write_state(state)
        print(json.dumps({"status": "recorded", "round": args.round}, indent=2))
        return 0

    if args.command == "reset":
        result = reset()
        print(json.dumps(result, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
