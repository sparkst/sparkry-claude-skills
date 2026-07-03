"""Deterministic end-of-run scorecard for the ai-review-toolkit.

Produces a consistent report of how a review/loop/pipeline run performed:

  1. Process steps   -- per-step status and counts (team, tests, reviewers, synthesis)
  2. Issues found    -- totals by severity (P0-P3) plus validation-dropped count
  3. Token costs     -- per-model token breakdown + USD via an overridable pricing table
  4. Model execution -- sum of per-request durationMs (NOT wall clock)

Data sources:
  * a state file (.qreview/.qloop/.qpipeline state.json) for findings/tests/team
  * a session transcript JSONL for token usage + durationMs (grouped by model)

No LLM calls. Pure aggregation over data already on disk, so the output is
reproducible from the same inputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Pricing (USD per 1,000,000 tokens). Rates as of 2026-06; override with
# --pricing PATH (JSON: {"sonnet": {"input":.., "output":.., "cache_read":..,
# "cache_write":..}, ...}).
# ---------------------------------------------------------------------------

_DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "opus":   {"input": 15.0, "cache_read": 1.50, "cache_write": 18.75, "output": 75.0},
    "sonnet": {"input": 3.0,  "cache_read": 0.30, "cache_write": 3.75,  "output": 15.0},
    "haiku":  {"input": 1.0,  "cache_read": 0.10, "cache_write": 1.25,  "output": 5.0},
}

_MILLION = 1_000_000


def load_pricing(path: str | None = None) -> dict[str, dict[str, float]]:
    """Return the pricing table, overlaying a custom JSON file if given."""
    pricing = {k: dict(v) for k, v in _DEFAULT_PRICING.items()}
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            override = json.load(fh)
        for model, rates in override.items():
            pricing[model] = {**pricing.get(model, {}), **rates}
    return pricing


def normalize_model(raw: str) -> str:
    """Map a concrete model id to a pricing tier key.

    Unknown ids are returned unchanged so nothing is silently lost.
    """
    if not raw:
        return "unknown"
    low = raw.lower()
    if "opus" in low:
        return "opus"
    if "sonnet" in low:
        return "sonnet"
    if "haiku" in low:
        return "haiku"
    return raw


def token_cost(usage: dict[str, Any], model: str, pricing: dict[str, dict[str, float]]) -> float:
    """USD cost for a single usage record under the given (normalized) model.

    Unknown models cost 0.0 (tokens still counted elsewhere) rather than crash.
    """
    rates = pricing.get(model)
    if not rates:
        return 0.0
    inp = usage.get("input_tokens", 0) or 0
    cr = usage.get("cache_read_input_tokens", 0) or 0
    cc = usage.get("cache_creation_input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    return (
        inp * rates.get("input", 0.0)
        + cr * rates.get("cache_read", 0.0)
        + cc * rates.get("cache_write", 0.0)
        + out * rates.get("output", 0.0)
    ) / _MILLION


# ---------------------------------------------------------------------------
# Transcript aggregation
# ---------------------------------------------------------------------------

def _empty_bucket() -> dict[str, Any]:
    return {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0,
            "duration_ms": 0, "requests": 0, "agents": 0}


def aggregate_transcript(
    lines: Iterable[dict[str, Any]],
    since: str | None = None,
) -> dict[str, Any]:
    """Aggregate token usage + durationMs per (normalized) model.

    Only lines carrying ``message.usage`` are counted; sidechain (subagent)
    lines are included. ``since`` (ISO-8601) bounds aggregation to lines whose
    ``timestamp`` is >= since (string compare is valid for ISO-8601/Zulu).
    """
    by_model: dict[str, dict[str, Any]] = {}
    total = _empty_bucket()

    for line in lines:
        msg = line.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if not isinstance(usage, dict):
            continue
        ts = line.get("timestamp")
        if since is not None and ts is not None and ts < since:
            continue

        model = normalize_model(msg.get("model", ""))
        bucket = by_model.setdefault(model, _empty_bucket())

        inp = usage.get("input_tokens", 0) or 0
        cr = usage.get("cache_read_input_tokens", 0) or 0
        cc = usage.get("cache_creation_input_tokens", 0) or 0
        out = usage.get("output_tokens", 0) or 0
        dur = line.get("durationMs", 0) or 0

        for key, val in (("input", inp), ("cache_read", cr), ("cache_write", cc),
                         ("output", out), ("duration_ms", dur)):
            bucket[key] += val
            total[key] += val
        bucket["requests"] += 1
        total["requests"] += 1

    return {"by_model": by_model, "total": total, "since": since}


# ---------------------------------------------------------------------------
# Workflow aggregation (ultracode Workflow runs)
# ---------------------------------------------------------------------------
#
# A Workflow run does NOT record per-request durationMs the way a single
# session transcript does: the per-subagent ``agent-*.jsonl`` files carry token
# usage but no duration, and the journal has none either. Per-agent execution
# time is recovered as each agent's wall-clock span (last - first line
# timestamp) and rolled up per model. The authoritative *workflow* wall clock
# (agents run in parallel, so summed per-agent time overcounts it) comes from
# ``workflows/<runId>.json``. See memory: project_workflow_scorecard_sources.

def _parse_iso_ms(ts: Any) -> int | None:
    """Parse an ISO-8601 timestamp to epoch milliseconds, or None."""
    if not isinstance(ts, str) or not ts:
        return None
    try:
        normalized = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
        return int(datetime.fromisoformat(normalized).timestamp() * 1000)
    except (ValueError, OverflowError):
        return None


def aggregate_workflow(
    agent_transcripts: dict[str, Iterable[dict[str, Any]]],
    workflow_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate token usage + per-agent wall-clock over a Workflow's subagents.

    *agent_transcripts* maps agentId -> that agent's ``agent-*.jsonl`` lines.
    Tokens are summed per (normalized) model from each usage-bearing line;
    duration for an agent is its last-minus-first line timestamp, credited to
    the model of its usage lines. *workflow_meta* is the parsed
    ``workflows/<runId>.json`` (for the true wall-clock total + phase timings).
    """
    by_model: dict[str, dict[str, Any]] = {}
    total = _empty_bucket()

    for lines in agent_transcripts.values():
        agent_model: str | None = None
        min_ms: int | None = None
        max_ms: int | None = None

        for line in lines:
            ts_ms = _parse_iso_ms(line.get("timestamp"))
            if ts_ms is not None:
                min_ms = ts_ms if min_ms is None else min(min_ms, ts_ms)
                max_ms = ts_ms if max_ms is None else max(max_ms, ts_ms)

            msg = line.get("message")
            if not isinstance(msg, dict):
                continue
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue

            model = normalize_model(msg.get("model", ""))
            agent_model = model
            bucket = by_model.setdefault(model, _empty_bucket())

            inp = usage.get("input_tokens", 0) or 0
            cr = usage.get("cache_read_input_tokens", 0) or 0
            cc = usage.get("cache_creation_input_tokens", 0) or 0
            out = usage.get("output_tokens", 0) or 0
            for key, val in (("input", inp), ("cache_read", cr),
                             ("cache_write", cc), ("output", out)):
                bucket[key] += val
                total[key] += val
            bucket["requests"] += 1
            total["requests"] += 1

        if agent_model is not None and min_ms is not None and max_ms is not None:
            delta = max_ms - min_ms
            by_model[agent_model]["duration_ms"] += delta
            by_model[agent_model]["agents"] += 1
            total["duration_ms"] += delta
            total["agents"] += 1

    workflow: dict[str, Any] = {}
    if workflow_meta:
        phases = []
        for entry in workflow_meta.get("workflowProgress", []):
            if isinstance(entry, dict) and entry.get("durationMs") is not None \
                    and entry.get("type") == "workflow_phase":
                phases.append({"title": entry.get("title"),
                               "duration_ms": entry["durationMs"]})
        workflow = {
            "run_id": workflow_meta.get("runId"),
            "wall_clock_ms": workflow_meta.get("durationMs"),
            "agent_count": workflow_meta.get("agentCount"),
            "status": workflow_meta.get("status"),
            "total_tokens": workflow_meta.get("totalTokens"),
            "phases": phases,
        }

    return {"by_model": by_model, "total": total, "workflow": workflow}


# ---------------------------------------------------------------------------
# State readers (tolerant of qreview / qloop / qpipeline schemas)
# ---------------------------------------------------------------------------

def _latest_synthesis(state: dict[str, Any]) -> dict[str, Any]:
    """Return the run's synthesis dict from whichever schema is present."""
    if isinstance(state.get("synthesis"), dict):
        return state["synthesis"]
    rounds = state.get("rounds")
    if isinstance(rounds, list) and rounds:
        for r in reversed(rounds):
            syn = r.get("synthesis")
            if isinstance(syn, dict) and syn:
                return syn
    return {}


def _process_steps(state: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []

    team = state.get("team", [])
    if team:
        models = ", ".join(f"{a.get('name')}={a.get('model')}" for a in team)
        steps.append({"name": "Team selection", "detail": f"{len(team)} reviewers ({models})"})

    tr = state.get("test_results", {})
    if tr:
        steps.append({
            "name": "Deterministic tests",
            "detail": tr.get("summary", "n/a"),
            "all_passed": tr.get("all_passed"),
        })

    outputs = state.get("reviewer_outputs", {})
    if outputs:
        dropped = state.get("validation_dropped", {})
        per = []
        for idx, findings in outputs.items():
            d = dropped.get(str(idx), 0)
            per.append(f"#{idx}: {len(findings)} findings" + (f" ({d} dropped)" if d else ""))
        steps.append({"name": "Reviewers", "detail": "; ".join(per)})

    syn = _latest_synthesis(state)
    if syn:
        counts = syn.get("counts", {})
        steps.append({
            "name": "Synthesis",
            "detail": f"{syn.get('total', 0)} findings "
                      f"(P0={counts.get('P0', 0)} P1={counts.get('P1', 0)} "
                      f"P2={counts.get('P2', 0)} P3={counts.get('P3', 0)})",
        })

    rounds = state.get("rounds")
    if isinstance(rounds, list) and rounds:
        steps.append({"name": "Rounds", "detail": f"{len(rounds)} round(s) run"})

    return steps


def _deploy_section(state: dict[str, Any]) -> dict[str, Any] | None:
    """Surface the prod GUARDRAIL GATE verdict (Phase F2) when a run produced one.

    Returns None for the common case (no deploy tail), so the scorecard only grows
    a Deploy section for `/qpipeline auto prod` runs. See prod-tail.py `deploy_gate`.
    """
    gate = state.get("deploy_gate")
    if not isinstance(gate, dict):
        return None
    section: dict[str, Any] = {
        "allowed": bool(gate.get("allowed")),
        "blockers": list(gate.get("blockers", []) or []),
        "checklist": gate.get("checklist", {}) or {},
    }
    for key in ("staging_smoke", "prod_smoke"):
        smoke = state.get(key)
        if isinstance(smoke, dict):
            section[key] = {
                "ok": bool(smoke.get("ok")),
                "total": int(smoke.get("total", 0) or 0),
                "passed": int(smoke.get("passed", 0) or 0),
                "failed": list(smoke.get("failed", []) or []),
            }
    return section


def build_scorecard(
    state: dict[str, Any],
    transcript_agg: dict[str, Any],
    pricing: dict[str, dict[str, float]],
) -> dict[str, Any]:
    """Assemble the structured scorecard from state + transcript aggregate."""
    syn = _latest_synthesis(state)
    counts = syn.get("counts", {}) if syn else {}

    # Tokens: attach USD cost per model + total.
    tokens_by_model: dict[str, Any] = {}
    total_cost = 0.0
    for model, b in transcript_agg.get("by_model", {}).items():
        usage = {
            "input_tokens": b["input"],
            "cache_read_input_tokens": b["cache_read"],
            "cache_creation_input_tokens": b["cache_write"],
            "output_tokens": b["output"],
        }
        cost = token_cost(usage, model, pricing)
        total_cost += cost
        tokens_by_model[model] = {
            "input": b["input"], "cache_read": b["cache_read"],
            "cache_write": b["cache_write"], "output": b["output"],
            "requests": b["requests"], "cost_usd": round(cost, 4),
        }

    tot = transcript_agg.get("total", _empty_bucket())
    time_by_model = {m: b["duration_ms"] for m, b in transcript_agg.get("by_model", {}).items()}

    # Workflow runs report per-agent wall-clock (last-first line timestamp)
    # rolled per model, plus the authoritative parallel wall-clock total.
    wf = transcript_agg.get("workflow") or {}
    if wf:
        time_section = {
            "by_model_ms": time_by_model,
            "by_model_agents": {m: b.get("agents", 0) for m, b in transcript_agg.get("by_model", {}).items()},
            "total_ms": tot["duration_ms"],
            "workflow_wall_clock_ms": wf.get("wall_clock_ms"),
            "phases": wf.get("phases", []),
            "note": "per-model time = sum of per-agent wall-clock spans (agents run "
                    "in parallel, so this exceeds the workflow wall-clock total)",
        }
    else:
        time_section = {
            "by_model_ms": time_by_model,
            "total_ms": tot["duration_ms"],
            "note": "model execution time = sum of per-request durations, not wall clock",
        }

    report: dict[str, Any] = {
        "process": {
            "status": state.get("status"),
            "converged": syn.get("converged") if syn else None,
            "convergence_message": syn.get("convergence_message") if syn else None,
            "steps": _process_steps(state),
        },
        "issues": {
            "total": syn.get("total", 0) if syn else 0,
            "by_severity": {
                "P0": counts.get("P0", 0), "P1": counts.get("P1", 0),
                "P2": counts.get("P2", 0), "P3": counts.get("P3", 0),
            },
            "dropped": syn.get("dropped_count", 0) if syn else 0,
        },
        "tokens": {
            "by_model": tokens_by_model,
            "total": {
                "input": tot["input"], "cache_read": tot["cache_read"],
                "cache_write": tot["cache_write"], "output": tot["output"],
                "requests": tot["requests"], "cost_usd": round(total_cost, 4),
            },
            "available": tot["requests"] > 0,
        },
        "time": time_section,
    }

    deploy = _deploy_section(state)
    if deploy is not None:
        report["deploy"] = deploy
    return report


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _fmt_ms(ms: int) -> str:
    secs = ms / 1000.0
    if secs < 60:
        return f"{secs:.1f}s"
    return f"{int(secs // 60)}m {secs % 60:.1f}s"


def _fmt_tokens(n: int) -> str:
    return f"{n:,}"


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    proc = report["process"]
    lines.append("# Review Scorecard\n")

    lines.append("## Process\n")
    lines.append(f"- Status: **{proc.get('status')}**")
    conv = proc.get("converged")
    if conv is not None:
        verdict = "CONVERGED (safe to ship)" if conv else "NOT CONVERGED"
        lines.append(f"- Convergence: **{verdict}**"
                     + (f" — {proc.get('convergence_message')}" if proc.get('convergence_message') else ""))
    for i, step in enumerate(proc.get("steps", []), 1):
        lines.append(f"  {i}. **{step['name']}** — {step.get('detail', '')}")
    lines.append("")

    iss = report["issues"]
    bysev = iss["by_severity"]
    lines.append("## Issues Found\n")
    lines.append(f"- Total: **{iss['total']}**  "
                 f"(P0={bysev['P0']}, P1={bysev['P1']}, P2={bysev['P2']}, P3={bysev['P3']})")
    if iss.get("dropped"):
        lines.append(f"- Dropped (schema-invalid): {iss['dropped']}")
    lines.append("")

    tok = report["tokens"]
    lines.append("## Token Cost\n")
    if not tok.get("available"):
        lines.append("- Token/cost data unavailable (no transcript matched).")
    else:
        lines.append("| Model | Input | Cache rd | Cache wr | Output | Reqs | Cost (USD) |")
        lines.append("|---|--:|--:|--:|--:|--:|--:|")
        for model, b in sorted(tok["by_model"].items()):
            lines.append(f"| {model} | {_fmt_tokens(b['input'])} | {_fmt_tokens(b['cache_read'])} "
                         f"| {_fmt_tokens(b['cache_write'])} | {_fmt_tokens(b['output'])} "
                         f"| {b['requests']} | ${b['cost_usd']:.4f} |")
        t = tok["total"]
        lines.append(f"| **total** | {_fmt_tokens(t['input'])} | {_fmt_tokens(t['cache_read'])} "
                     f"| {_fmt_tokens(t['cache_write'])} | {_fmt_tokens(t['output'])} "
                     f"| {t['requests']} | **${t['cost_usd']:.4f}** |")
    lines.append("")

    tm = report["time"]
    lines.append("## Model Execution Time\n")
    lines.append(f"_{tm['note']}._\n")
    is_workflow = "workflow_wall_clock_ms" in tm
    if tm["total_ms"] or (is_workflow and tm.get("workflow_wall_clock_ms")):
        agents = tm.get("by_model_agents", {})
        for model, ms in sorted(tm["by_model_ms"].items()):
            suffix = ""
            if model in agents:
                n = agents[model]
                suffix = f" ({n} agent{'s' if n != 1 else ''})"
            lines.append(f"- {model}: {_fmt_ms(ms)}{suffix}")
        if is_workflow:
            for ph in tm.get("phases", []):
                lines.append(f"- phase _{ph.get('title')}_: {_fmt_ms(ph.get('duration_ms', 0))}")
            wall = tm.get("workflow_wall_clock_ms")
            if wall is not None:
                lines.append(f"- **workflow total (wall-clock): {_fmt_ms(wall)}**")
        else:
            lines.append(f"- **total: {_fmt_ms(tm['total_ms'])}**")
    else:
        lines.append("- unavailable (no transcript matched)")
    lines.append("")

    dep = report.get("deploy")
    if dep is not None:
        verdict = "ALLOWED (prod publish authorized)" if dep.get("allowed") else "REFUSED (prod blocked)"
        lines.append("## Deploy Gate\n")
        lines.append(f"- Guardrail gate: **{verdict}**")
        for b in dep.get("blockers", []):
            lines.append(f"  - blocker: {b}")
        for label, key in (("Staging smoke", "staging_smoke"), ("Prod smoke", "prod_smoke")):
            smoke = dep.get(key)
            if smoke:
                mark = "PASS" if smoke.get("ok") else "FAIL"
                line = f"- {label}: **{mark}** ({smoke.get('passed', 0)}/{smoke.get('total', 0)})"
                if smoke.get("failed"):
                    line += f" — failed: {', '.join(str(f) for f in smoke['failed'])}"
                lines.append(line)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _autodetect_state(cwd: Path) -> Path | None:
    for sub in (".qreview", ".qloop", ".qpipeline"):
        p = cwd / sub / "state.json"
        if p.exists():
            return p
    return None


def _project_slug(cwd: Path) -> str:
    # Claude Code names project transcript dirs after the abs path with
    # '/' and '.' replaced by '-'.
    return str(cwd).replace("/", "-").replace(".", "-")


def _autodetect_transcript(cwd: Path) -> Path | None:
    projects = Path.home() / ".claude" / "projects" / _project_slug(cwd)
    if not projects.is_dir():
        return None
    candidates = sorted(projects.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def load_workflow_run(
    workflow_json_path: Path,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Load a Workflow run's metadata + per-agent transcripts from disk.

    Given ``<session>/workflows/<runId>.json``, reads the sibling subagent
    transcripts at ``<session>/subagents/workflows/<runId>/agent-*.jsonl``.
    """
    with open(workflow_json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    run_id = meta.get("runId") or workflow_json_path.stem
    session_dir = workflow_json_path.parent.parent
    agents_dir = session_dir / "subagents" / "workflows" / run_id

    agent_transcripts: dict[str, list[dict[str, Any]]] = {}
    if agents_dir.is_dir():
        for af in sorted(agents_dir.glob("agent-*.jsonl")):
            agent_id = af.stem[len("agent-"):]
            agent_transcripts[agent_id] = list(_read_jsonl(af))
    return meta, agent_transcripts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic review scorecard.")
    parser.add_argument("--state", default=None, help="Path to state.json (auto-detected if omitted)")
    parser.add_argument("--transcript", default=None, help="Path to session transcript JSONL (auto-detected if omitted)")
    parser.add_argument("--since", default=None, help="Only count transcript lines with timestamp >= this ISO-8601 value")
    parser.add_argument("--pricing", default=None, help="Path to a pricing override JSON")
    parser.add_argument("--workflow", default=None, help="Path to a Workflow's workflows/<runId>.json (tokens/time from its subagents)")
    parser.add_argument("--json", dest="json_output", action="store_true", help="Emit JSON instead of Markdown")
    args = parser.parse_args(argv)

    cwd = Path.cwd()

    if args.workflow:
        # Workflow (ultracode) run: tokens + per-agent wall-clock from the run's
        # subagent transcripts; wall-clock total from its metadata. State
        # (findings/process) is optional here — step 4's workflow writes one.
        wf_path = Path(args.workflow)
        if not wf_path.exists():
            print(f"Error: workflow file not found: {wf_path}", file=sys.stderr)
            return 1
        meta, agent_transcripts = load_workflow_run(wf_path)
        agg = aggregate_workflow(agent_transcripts, meta)

        state_path = Path(args.state) if args.state else _autodetect_state(cwd)
        if state_path is not None and state_path.exists():
            with open(state_path, "r", encoding="utf-8") as fh:
                state = json.load(fh)
        else:
            state = {}
    else:
        state_path = Path(args.state) if args.state else _autodetect_state(cwd)
        if state_path is None or not state_path.exists():
            print("Error: no state file found (.qreview/.qloop/.qpipeline). Use --state or --workflow.", file=sys.stderr)
            return 1
        with open(state_path, "r", encoding="utf-8") as fh:
            state = json.load(fh)

        # Default --since to the run's start so we scope to this review, not the
        # whole session, unless the caller overrides it.
        since = args.since if args.since is not None else state.get("created_at")

        transcript_path = Path(args.transcript) if args.transcript else _autodetect_transcript(cwd)
        if transcript_path and transcript_path.exists():
            agg = aggregate_transcript(_read_jsonl(transcript_path), since=since)
        else:
            agg = aggregate_transcript([], since=since)

    pricing = load_pricing(args.pricing)
    report = build_scorecard(state, agg, pricing)

    if args.json_output:
        sys.stdout.write(json.dumps(report, indent=2) + "\n")
    else:
        sys.stdout.write(render_markdown(report) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
