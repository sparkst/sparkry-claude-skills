"""Tests for confidence-scorer.py — consensus detection and backtrack logic."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))


def test_consensus_all_high_no_p0():
    from confidence_scorer import detect_consensus
    results = [
        {"agent": "security", "findings": [{"severity": "P2", "confidence": "high"}]},
        {"agent": "code-review", "findings": [{"severity": "P2", "confidence": "high"}]},
    ]
    result = detect_consensus(results)
    assert result["consensus"] is True
    assert result["recommendation"] == "early_terminate"


def test_consensus_empty_findings_high_confidence():
    from confidence_scorer import detect_consensus
    results = [
        {"agent": "security", "findings": []},
        {"agent": "code-review", "findings": []},
    ]
    result = detect_consensus(results)
    assert result["consensus"] is True
    assert result["recommendation"] == "early_terminate"


def test_no_consensus_with_p0():
    from confidence_scorer import detect_consensus
    results = [
        {"agent": "security", "findings": [{"severity": "P0", "confidence": "high"}]},
        {"agent": "code-review", "findings": []},
    ]
    result = detect_consensus(results)
    assert result["consensus"] is False


def test_no_consensus_mixed_confidence():
    from confidence_scorer import detect_consensus
    results = [
        {"agent": "security", "findings": [{"severity": "P2", "confidence": "low"}]},
        {"agent": "code-review", "findings": [{"severity": "P2", "confidence": "high"}]},
    ]
    result = detect_consensus(results)
    assert result["consensus"] is False


def test_escalate_when_disagreement():
    from confidence_scorer import detect_consensus
    results = [
        {"agent": "security", "findings": [{"severity": "P0", "confidence": "high"}]},
        {"agent": "code-review", "findings": []},  # Found nothing
        {"agent": "pe-architect", "findings": []},  # Found nothing
    ]
    result = detect_consensus(results)
    assert result["recommendation"] == "escalate"


def test_should_backtrack_round3_with_p0():
    from confidence_scorer import should_backtrack
    assert should_backtrack(round_num=3, p0_count=1, replan_count=0) is True


def test_should_not_backtrack_early_round():
    from confidence_scorer import should_backtrack
    assert should_backtrack(round_num=2, p0_count=1, replan_count=0) is False


def test_should_not_backtrack_max_replans():
    from confidence_scorer import should_backtrack
    assert should_backtrack(round_num=3, p0_count=1, replan_count=2) is False


def test_should_not_backtrack_no_p0():
    from confidence_scorer import should_backtrack
    assert should_backtrack(round_num=3, p0_count=0, replan_count=0) is False


def test_should_backtrack_round5():
    from confidence_scorer import should_backtrack
    assert should_backtrack(round_num=5, p0_count=2, replan_count=1) is True
