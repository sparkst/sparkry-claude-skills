#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Travis Sparks
"""Structured telemetry for QRALPH pipeline."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class ProjectMetrics:
    """Collects and serializes structured telemetry for a QRALPH project run."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.created_at = datetime.now().isoformat()
        self._phases: dict[str, dict] = {}
        self._agents: dict[str, dict] = {}
        self._groups: dict[int, dict] = {}
        self._quality: list[dict] = []
        self._extras: dict[str, object] = {}

    def phase_start(self, phase: str) -> None:
        self._phases[phase] = {
            "start": datetime.now().isoformat(),
            "_start_ts": datetime.now().timestamp(),
        }

    def phase_end(self, phase: str) -> None:
        if phase not in self._phases:
            raise KeyError(f"Phase '{phase}' was never started")
        now = datetime.now()
        entry = self._phases[phase]
        entry["end"] = now.isoformat()
        entry["duration_s"] = now.timestamp() - entry["_start_ts"]

    def agent_start(self, name: str, model: str = "", phase: str = "") -> None:
        self._agents[name] = {
            "model": model,
            "phase": phase,
            "start": datetime.now().isoformat(),
            "_start_ts": datetime.now().timestamp(),
        }

    def agent_end(
        self,
        name: str,
        committed: bool = False,
        duration_override: float | None = None,
    ) -> None:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' was never started")
        now = datetime.now()
        entry = self._agents[name]
        entry["end"] = now.isoformat()
        entry["committed"] = committed
        if duration_override is not None:
            entry["duration_s"] = duration_override
        else:
            entry["duration_s"] = now.timestamp() - entry["_start_ts"]

    def group_start(self, index: int, task_ids: list[str]) -> None:
        self._groups[index] = {
            "task_ids": task_ids,
            "start": datetime.now().isoformat(),
            "_start_ts": datetime.now().timestamp(),
        }

    def group_end(self, index: int) -> None:
        if index not in self._groups:
            raise KeyError(f"Group {index} was never started")
        now = datetime.now()
        entry = self._groups[index]
        entry["end"] = now.isoformat()
        entry["duration_s"] = now.timestamp() - entry["_start_ts"]

    def quality_round(
        self, round_num: int, p0: int, p1: int, p2: int, converged: bool
    ) -> None:
        self._quality.append(
            {
                "round": round_num,
                "p0": p0,
                "p1": p1,
                "p2": p2,
                "converged": converged,
            }
        )

    def record(self, key: str, value: object) -> None:
        self._extras[key] = value

    def detect_bottlenecks(self, threshold: float = 2.0) -> list[dict]:
        bottlenecks: list[dict] = []
        for idx, group in self._groups.items():
            task_ids = group["task_ids"]
            if len(task_ids) < 2:
                continue
            durations = {}
            for tid in task_ids:
                if tid in self._agents and "duration_s" in self._agents[tid]:
                    durations[tid] = self._agents[tid]["duration_s"]
            if len(durations) < 2:
                continue
            avg = sum(durations.values()) / len(durations)
            if avg == 0:
                continue
            for agent_name, dur in durations.items():
                ratio = dur / avg
                if ratio > threshold:
                    bottlenecks.append(
                        {
                            "agent": agent_name,
                            "duration_s": dur,
                            "group_avg_s": avg,
                            "ratio": ratio,
                            "group_index": idx,
                        }
                    )
        return bottlenecks

    def to_dict(self) -> dict:
        # Clean phases: strip internal _start_ts
        phases = {}
        for name, data in self._phases.items():
            phases[name] = {k: v for k, v in data.items() if not k.startswith("_")}

        # Clean agents
        agents = {}
        for name, data in self._agents.items():
            agents[name] = {k: v for k, v in data.items() if not k.startswith("_")}

        # Clean groups, convert to list sorted by index
        groups = []
        for idx in sorted(self._groups.keys()):
            entry = {
                k: v for k, v in self._groups[idx].items() if not k.startswith("_")
            }
            groups.append(entry)

        total_phase_duration = sum(
            p.get("duration_s", 0) for p in phases.values()
        )

        bottlenecks = self.detect_bottlenecks()

        result = {
            "project_id": self.project_id,
            "created_at": self.created_at,
            "completed_at": datetime.now().isoformat(),
            "summary": {
                "phase_count": len(phases),
                "agent_count": len(agents),
                "group_count": len(groups),
                "quality_rounds": len(self._quality),
                "bottlenecks": bottlenecks,
                "total_phase_duration_s": total_phase_duration,
            },
            "phases": phases,
            "agents": agents,
            "execution_groups": groups,
            "quality_loop": list(self._quality),
        }

        for key, value in self._extras.items():
            result[key] = value

        return result

    def write(self, project_path: Path) -> None:
        project_path.mkdir(parents=True, exist_ok=True)
        out = project_path / "metrics.json"
        out.write_text(json.dumps(self.to_dict(), indent=2))
