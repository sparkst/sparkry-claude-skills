"""Confidence scorer for QRALPH quality loop.

Detects agent consensus and determines when to backtrack/replan.
Used by the orchestrator to decide early termination, continuation,
or escalation during multi-agent review rounds.
"""

from __future__ import annotations


def detect_consensus(agent_results: list[dict]) -> dict:
    """Detect whether agents agree on their findings.

    Args:
        agent_results: List of {agent: str, findings: list[{severity, confidence}]}

    Returns:
        {consensus: bool, recommendation: "early_terminate" | "continue" | "escalate"}

    Rules:
        - consensus=True when all agents have high confidence AND zero P0 findings
        - Empty findings count as high confidence (nothing found, agent is sure)
        - "escalate" when agents disagree significantly (some find P0, others find nothing)
        - "early_terminate" when consensus is True
        - "continue" otherwise
    """
    has_p0 = False
    all_high_confidence = True
    agents_with_p0: list[str] = []
    agents_with_nothing: list[str] = []

    for entry in agent_results:
        agent = entry["agent"]
        findings = entry.get("findings", [])

        if not findings:
            agents_with_nothing.append(agent)
            continue

        for finding in findings:
            if finding.get("severity") == "P0":
                has_p0 = True
                if agent not in agents_with_p0:
                    agents_with_p0.append(agent)
            if finding.get("confidence") != "high":
                all_high_confidence = False

    consensus = all_high_confidence and not has_p0

    if consensus:
        return {"consensus": True, "recommendation": "early_terminate"}

    # Escalate when some agents find P0 but others find nothing
    if agents_with_p0 and agents_with_nothing:
        return {"consensus": False, "recommendation": "escalate"}

    return {"consensus": False, "recommendation": "continue"}


def should_backtrack(round_num: int, p0_count: int, replan_count: int) -> bool:
    """Determine whether the quality loop should backtrack to replan.

    Args:
        round_num: Current review round number.
        p0_count: Number of P0 (critical) findings still open.
        replan_count: How many times we have already replanned.

    Returns:
        True if backtracking is warranted.

    Rules:
        - True when: round_num >= 3 AND p0_count > 0 AND replan_count < 2
        - False when: round < 3 (give more time), or replan_count >= 2
          (max replans reached), or p0_count == 0 (no critical issues)
    """
    return round_num >= 3 and p0_count > 0 and replan_count < 2
