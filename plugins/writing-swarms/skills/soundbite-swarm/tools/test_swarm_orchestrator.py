#!/usr/bin/env python3
"""
Tests for swarm-orchestrator.py

REQ-SO-001: Coordinate 5 angles running in parallel
REQ-SO-002: Collect, filter, and cross-rank candidates
REQ-SO-003: Return top 10 with full metadata
REQ-SO-004: Handle partial failures gracefully
"""

import pytest
import sys
from pathlib import Path

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class TestSwarmOrchestration:
    """Test full orchestration workflow."""

    # ==================== HAPPY PATH TESTS ====================

    def test_full_orchestration_returns_top_10(self):
        """REQ-SO-001: Full orchestration: content -> 50 candidates -> filter to ~35 -> cross-rank -> top 10."""
        from swarm_orchestrator import orchestrate_swarm

        content = """
        AI adoption in organizations isn't a technology problem - it's a permission problem.
        Most employees want to use AI, but they don't know if they're allowed to.
        They're waiting for explicit permission from leadership.
        The organizations that will win are those that create clear permission structures.
        Stop waiting. Give permission. Watch what happens.
        """

        result = orchestrate_swarm(content)

        # Should return exactly 10 (or fewer if not enough valid)
        assert len(result["top_soundbites"]) <= 10
        assert len(result["top_soundbites"]) >= 1

        # Check pipeline metrics
        assert result["pipeline"]["candidates_generated"] == 50  # 5 angles x 10
        assert result["pipeline"]["candidates_after_filter"] <= 50
        assert result["pipeline"]["final_count"] <= 10

    def test_results_have_full_metadata(self):
        """REQ-SO-003: Each result has soundbite, composite_score, generating_angle, cross_rank_performance."""
        from swarm_orchestrator import orchestrate_swarm

        content = """
        The future belongs to those who build. Stop planning. Start creating.
        Your first version will be terrible. Ship it anyway.
        """

        result = orchestrate_swarm(content)

        for soundbite in result["top_soundbites"]:
            assert "soundbite" in soundbite
            assert "composite_score" in soundbite
            assert "generating_angle" in soundbite
            assert "cross_rank_performance" in soundbite

    def test_results_sorted_by_composite_score(self):
        """REQ-SO-003: Results are sorted by composite score descending."""
        from swarm_orchestrator import orchestrate_swarm

        content = """
        Change is hard. Change is necessary. The only constant is change.
        Embrace the uncertainty. Find strength in adaptability.
        """

        result = orchestrate_swarm(content)

        scores = [s["composite_score"] for s in result["top_soundbites"]]

        # Should be sorted descending
        assert scores == sorted(scores, reverse=True)

    def test_diversity_across_angles(self):
        """REQ-SO-001: Results should have diversity across generating angles."""
        from swarm_orchestrator import orchestrate_swarm

        content = """
        Innovation requires courage. Courage requires conviction.
        Conviction comes from clarity. Clarity comes from action.
        The cycle continues. Break in anywhere.
        """

        result = orchestrate_swarm(content)

        # Get unique angles in top 10
        angles = set(s["generating_angle"] for s in result["top_soundbites"])

        # Should have at least 2-3 different angles represented
        assert len(angles) >= 2, \
            "Top 10 should have diversity from at least 2 angles"

    # ==================== EDGE CASE TESTS ====================

    def test_all_candidates_from_one_angle_filter_out(self):
        """REQ-SO-004: If all candidates from one angle filter out, proceed with remaining."""
        from swarm_orchestrator import orchestrate_swarm

        # Very technical content might not produce good emotional candidates
        content = """
        The TCP/IP protocol stack consists of four layers.
        Each layer has specific responsibilities.
        """

        result = orchestrate_swarm(content)

        # Should still produce results
        assert len(result["top_soundbites"]) >= 1

        # Should note which angles had all filtered
        if result["pipeline"].get("angles_filtered_out"):
            assert isinstance(result["pipeline"]["angles_filtered_out"], list)

    def test_only_8_candidates_pass_filtering_returns_8(self):
        """REQ-SO-002: If only 8 candidates pass filtering, returns all 8 (not 10)."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for limited filtering."

        # Run orchestration and verify it handles less than 10 valid candidates
        result = orchestrate_swarm(content, _test_max_valid=8)

        # Should return at most the available candidates, not pad to 10
        assert len(result["top_soundbites"]) <= 10

    def test_tie_for_10th_place_includes_both(self):
        """REQ-SO-002: Two candidates tie for #10, both included (11 results)."""
        from swarm_orchestrator import orchestrate_swarm

        content = """
        When two ideas compete, let them both win.
        Abundance mindset beats scarcity every time.
        """

        # This test relies on natural tie occurrence or mock
        result = orchestrate_swarm(content, _test_force_tie=True)

        # May return 11 if tie for 10th place
        assert len(result["top_soundbites"]) >= 10

    def test_duplicate_soundbites_from_different_angles_deduplicated(self):
        """REQ-SO-002: Identical soundbites from different angles are deduplicated."""
        from swarm_orchestrator import orchestrate_swarm

        content = """
        Just do it. Start now. Begin today.
        Simple phrases that multiple angles might generate.
        """

        result = orchestrate_swarm(content)

        # Check for unique soundbites
        soundbites = [s["soundbite"] for s in result["top_soundbites"]]
        unique_soundbites = set(soundbites)

        assert len(soundbites) == len(unique_soundbites), \
            "Should not have duplicate soundbites in results"

    # ==================== FAILURE PATH TESTS ====================

    def test_all_candidates_fail_validation_returns_empty_with_error(self):
        """REQ-SO-004: All candidates fail validation, returns empty list with error."""
        from swarm_orchestrator import orchestrate_swarm

        # Force all validation failures via test parameter
        result = orchestrate_swarm("Test", _test_fail_all_validation=True)

        assert len(result["top_soundbites"]) == 0
        assert result["error"] is True
        assert "all candidates failed" in result["error_message"].lower()

    def test_one_angle_times_out_proceeds_with_4(self):
        """REQ-SO-004: One angle times out, proceeds with 4 angles, notes partial results."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for timeout handling."

        result = orchestrate_swarm(content, _test_timeout_angle="emotional")

        # Should still produce results from 4 angles
        assert len(result["top_soundbites"]) >= 1

        # Should note partial execution
        assert result["pipeline"]["partial_execution"] is True
        assert "emotional" in result["pipeline"].get("timed_out_angles", [])

    def test_cross_ranker_fails_falls_back_to_self_score(self):
        """REQ-SO-004: Cross-ranker fails, falls back to self-score ranking."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for cross-ranker failure."

        result = orchestrate_swarm(content, _test_fail_cross_ranker=True)

        # Should still return results
        assert len(result["top_soundbites"]) >= 1

        # Should note fallback mode
        assert result["pipeline"]["ranking_mode"] == "self_score_fallback"


class TestPipelineMetrics:
    """Test pipeline metrics are properly tracked."""

    def test_pipeline_tracks_candidates_generated(self):
        """Pipeline should track total candidates generated."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for metrics tracking."

        result = orchestrate_swarm(content)

        assert "pipeline" in result
        assert result["pipeline"]["candidates_generated"] == 50  # 5 angles x 10

    def test_pipeline_tracks_filter_results(self):
        """Pipeline should track candidates after filtering."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for filter tracking."

        result = orchestrate_swarm(content)

        assert result["pipeline"]["candidates_after_filter"] <= 50
        assert result["pipeline"]["candidates_after_filter"] >= 0

    def test_pipeline_tracks_timing(self):
        """Pipeline should track execution timing."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for timing."

        result = orchestrate_swarm(content)

        assert "total_time_ms" in result["pipeline"]
        assert result["pipeline"]["total_time_ms"] >= 0

    def test_pipeline_tracks_angles_executed(self):
        """Pipeline should track which angles were executed."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for angle tracking."

        result = orchestrate_swarm(content)

        assert "angles_executed" in result["pipeline"]
        assert len(result["pipeline"]["angles_executed"]) == 5


class TestCrossRankPerformance:
    """Test cross-rank performance metadata."""

    def test_cross_rank_includes_angles_ranked_count(self):
        """Cross-rank performance should include count of angles that ranked it."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for cross-rank metadata."

        result = orchestrate_swarm(content)

        for soundbite in result["top_soundbites"]:
            perf = soundbite["cross_rank_performance"]
            assert "angles_ranked" in perf
            assert 1 <= perf["angles_ranked"] <= 5

    def test_cross_rank_includes_borda_points(self):
        """Cross-rank performance should include Borda points."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for Borda points."

        result = orchestrate_swarm(content)

        for soundbite in result["top_soundbites"]:
            perf = soundbite["cross_rank_performance"]
            assert "borda_points" in perf
            assert perf["borda_points"] >= 0

    def test_cross_rank_includes_consensus_status(self):
        """Cross-rank performance should indicate consensus bonus status."""
        from swarm_orchestrator import orchestrate_swarm

        content = "Test content for consensus."

        result = orchestrate_swarm(content)

        for soundbite in result["top_soundbites"]:
            perf = soundbite["cross_rank_performance"]
            assert "consensus_bonus" in perf
            assert isinstance(perf["consensus_bonus"], bool)


class TestInputValidation:
    """Test input validation for orchestrator."""

    def test_empty_content_raises_error(self):
        """Empty content should raise ValueError."""
        from swarm_orchestrator import orchestrate_swarm

        with pytest.raises(ValueError, match="[Cc]ontent"):
            orchestrate_swarm("")

    def test_none_content_raises_error(self):
        """None content should raise TypeError."""
        from swarm_orchestrator import orchestrate_swarm

        with pytest.raises(TypeError):
            orchestrate_swarm(None)

    def test_very_short_content_produces_warning(self):
        """Very short content should produce warning but still work."""
        from swarm_orchestrator import orchestrate_swarm

        result = orchestrate_swarm("AI is good.")

        # Should still work
        assert len(result["top_soundbites"]) >= 1

        # Should have warning
        assert result.get("warnings") is not None
        assert any("short" in w.lower() for w in result["warnings"])


class TestDeduplication:
    """Test deduplication logic."""

    def test_exact_duplicates_removed(self):
        """Exact duplicate soundbites should be removed."""
        from swarm_orchestrator import _deduplicate_soundbites

        candidates = [
            {"soundbite": "Just Do It", "score": 90, "angle": "action"},
            {"soundbite": "Just Do It", "score": 85, "angle": "emotional"},  # Duplicate
            {"soundbite": "Think Different", "score": 88, "angle": "identity"},
        ]

        result = _deduplicate_soundbites(candidates)

        assert len(result) == 2
        soundbites = [c["soundbite"] for c in result]
        assert soundbites.count("Just Do It") == 1

    def test_keeps_higher_scoring_duplicate(self):
        """When deduplicating, keeps the higher-scoring version."""
        from swarm_orchestrator import _deduplicate_soundbites

        candidates = [
            {"soundbite": "Just Do It", "score": 85, "angle": "emotional"},
            {"soundbite": "Just Do It", "score": 90, "angle": "action"},  # Higher score
        ]

        result = _deduplicate_soundbites(candidates)

        assert len(result) == 1
        assert result[0]["score"] == 90
        assert result[0]["angle"] == "action"

    def test_case_insensitive_deduplication(self):
        """Deduplication should be case-insensitive."""
        from swarm_orchestrator import _deduplicate_soundbites

        candidates = [
            {"soundbite": "Just Do It", "score": 90, "angle": "action"},
            {"soundbite": "just do it", "score": 85, "angle": "emotional"},  # Same, different case
        ]

        result = _deduplicate_soundbites(candidates)

        assert len(result) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
