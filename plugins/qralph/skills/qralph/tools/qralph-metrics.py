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

    @staticmethod
    def _timestamp_entry(**extras: object) -> dict:
        """Create a dict with start timestamp and any extra fields."""
        now = datetime.now()
        return {"start": now.isoformat(), "_start_ts": now.timestamp(), **extras}

    @staticmethod
    def _close_entry(entry: dict, **extras: object) -> None:
        """Set end timestamp, compute duration_s, and merge extras."""
        now = datetime.now()
        entry["end"] = now.isoformat()
        entry["duration_s"] = now.timestamp() - entry["_start_ts"]
        entry.update(extras)

    def phase_start(self, phase: str) -> None:
        self._phases[phase] = self._timestamp_entry()

    def phase_end(self, phase: str) -> None:
        if phase not in self._phases:
            raise KeyError(f"Phase '{phase}' was never started")
        self._close_entry(self._phases[phase])

    def agent_start(self, name: str, model: str = "", phase: str = "") -> None:
        self._agents[name] = self._timestamp_entry(model=model, phase=phase)

    def agent_end(
        self,
        name: str,
        committed: bool = False,
        duration_override: float | None = None,
    ) -> None:
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' was never started")
        entry = self._agents[name]
        self._close_entry(entry, committed=committed)
        if duration_override is not None:
            entry["duration_s"] = duration_override

    def group_start(self, index: int, task_ids: list[str]) -> None:
        self._groups[index] = self._timestamp_entry(task_ids=task_ids)

    def group_end(self, index: int) -> None:
        if index not in self._groups:
            raise KeyError(f"Group {index} was never started")
        self._close_entry(self._groups[index])

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

    @staticmethod
    def _strip_internal(data: dict) -> dict:
        """Return a copy of data without keys starting with underscore."""
        return {k: v for k, v in data.items() if not k.startswith("_")}

    def to_dict(self) -> dict:
        phases = {name: self._strip_internal(d) for name, d in self._phases.items()}
        agents = {name: self._strip_internal(d) for name, d in self._agents.items()}
        groups = [
            self._strip_internal(self._groups[idx])
            for idx in sorted(self._groups.keys())
        ]

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
