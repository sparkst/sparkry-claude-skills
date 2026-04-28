#!/usr/bin/env python3
"""
Tests for cross-ranker.py

REQ-CR-001: Aggregate rankings from 5 angles using Borda count
REQ-CR-002: Apply consensus bonus for top-5 across 3+ angles
REQ-CR-003: Handle tie-breaking with defined priority
REQ-CR-004: Handle partial data and edge cases
"""

import pytest
import sys
from pathlib import Path

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class TestBordaCount:
    """Test Borda count aggregation logic."""

    # ==================== HAPPY PATH TESTS ====================

    def test_5_angles_rank_10_candidates_returns_top_10(self):
        """REQ-CR-001: 5 angles each rank 10 candidates, returns aggregated top 10."""
        from cross_ranker import aggregate_rankings

        rankings = {
            "emotional": [
                {"rank": 1, "candidate_id": "sb_001", "soundbite": "You Already Know"},
                {"rank": 2, "candidate_id": "sb_002", "soundbite": "Feel That"},
                {"rank": 3, "candidate_id": "sb_003", "soundbite": "Not Anymore"},
                {"rank": 4, "candidate_id": "sb_004", "soundbite": "This Is It"},
                {"rank": 5, "candidate_id": "sb_005", "soundbite": "You're Ready"},
                {"rank": 6, "candidate_id": "sb_006", "soundbite": "Enough"},
                {"rank": 7, "candidate_id": "sb_007", "soundbite": "Trust This"},
                {"rank": 8, "candidate_id": "sb_008", "soundbite": "Let Go"},
                {"rank": 9, "candidate_id": "sb_009", "soundbite": "Rise Up"},
                {"rank": 10, "candidate_id": "sb_010", "soundbite": "Own It"},
            ],
            "identity": [
                {"rank": 1, "candidate_id": "sb_001", "soundbite": "You Already Know"},
                {"rank": 2, "candidate_id": "sb_011", "soundbite": "Think Different"},
                {"rank": 3, "candidate_id": "sb_002", "soundbite": "Feel That"},
                {"rank": 4, "candidate_id": "sb_012", "soundbite": "Be More"},
                {"rank": 5, "candidate_id": "sb_003", "soundbite": "Not Anymore"},
                {"rank": 6, "candidate_id": "sb_013", "soundbite": "Builders Build"},
                {"rank": 7, "candidate_id": "sb_004", "soundbite": "This Is It"},
                {"rank": 8, "candidate_id": "sb_014", "soundbite": "Leaders Lead"},
                {"rank": 9, "candidate_id": "sb_005", "soundbite": "You're Ready"},
                {"rank": 10, "candidate_id": "sb_015", "soundbite": "We Create"},
            ],
            "action": [
                {"rank": 1, "candidate_id": "sb_016", "soundbite": "Just Do It"},
                {"rank": 2, "candidate_id": "sb_001", "soundbite": "You Already Know"},
                {"rank": 3, "candidate_id": "sb_017", "soundbite": "Start Now"},
                {"rank": 4, "candidate_id": "sb_002", "soundbite": "Feel That"},
                {"rank": 5, "candidate_id": "sb_018", "soundbite": "Ship It"},
                {"rank": 6, "candidate_id": "sb_003", "soundbite": "Not Anymore"},
                {"rank": 7, "candidate_id": "sb_019", "soundbite": "Move"},
                {"rank": 8, "candidate_id": "sb_004", "soundbite": "This Is It"},
                {"rank": 9, "candidate_id": "sb_020", "soundbite": "Build First"},
                {"rank": 10, "candidate_id": "sb_005", "soundbite": "You're Ready"},
            ],
            "contrarian": [
                {"rank": 1, "candidate_id": "sb_003", "soundbite": "Not Anymore"},
                {"rank": 2, "candidate_id": "sb_001", "soundbite": "You Already Know"},
                {"rank": 3, "candidate_id": "sb_021", "soundbite": "Question Everything"},
                {"rank": 4, "candidate_id": "sb_002", "soundbite": "Feel That"},
                {"rank": 5, "candidate_id": "sb_022", "soundbite": "You're Wrong"},
                {"rank": 6, "candidate_id": "sb_004", "soundbite": "This Is It"},
                {"rank": 7, "candidate_id": "sb_023", "soundbite": "Not That"},
                {"rank": 8, "candidate_id": "sb_005", "soundbite": "You're Ready"},
                {"rank": 9, "candidate_id": "sb_024", "soundbite": "Stop Believing"},
                {"rank": 10, "candidate_id": "sb_006", "soundbite": "Enough"},
            ],
            "simplifier": [
                {"rank": 1, "candidate_id": "sb_001", "soundbite": "You Already Know"},
                {"rank": 2, "candidate_id": "sb_025", "soundbite": "Less Is More"},
                {"rank": 3, "candidate_id": "sb_026", "soundbite": "Just. Start."},
                {"rank": 4, "candidate_id": "sb_002", "soundbite": "Feel That"},
                {"rank": 5, "candidate_id": "sb_027", "soundbite": "One Thing"},
                {"rank": 6, "candidate_id": "sb_003", "soundbite": "Not Anymore"},
                {"rank": 7, "candidate_id": "sb_028", "soundbite": "That's It"},
                {"rank": 8, "candidate_id": "sb_004", "soundbite": "This Is It"},
                {"rank": 9, "candidate_id": "sb_029", "soundbite": "Simple Works"},
                {"rank": 10, "candidate_id": "sb_005", "soundbite": "You're Ready"},
            ],
        }

        result = aggregate_rankings(rankings)

        assert len(result) == 10
        # sb_001 "You Already Know" should be top - ranked #1 by 3 angles, #2 by 2 angles
        assert result[0]["candidate_id"] == "sb_001"
        # All results should have borda_points
        for item in result:
            assert "borda_points" in item
            assert item["borda_points"] > 0

    def test_candidate_ranked_1_by_all_5_angles_max_points(self):
        """REQ-CR-001: Candidate ranked #1 by all 5 angles gets 50 points + bonus."""
        from cross_ranker import aggregate_rankings, calculate_borda_points

        # Candidate gets 10 points from each angle (rank 1) = 50 points
        # Plus consensus bonus of +5 for being in top-5 of 3+ angles
        rankings = {
            "emotional": [{"rank": 1, "candidate_id": "sb_001", "soundbite": "Unanimous Winner"}],
            "identity": [{"rank": 1, "candidate_id": "sb_001", "soundbite": "Unanimous Winner"}],
            "action": [{"rank": 1, "candidate_id": "sb_001", "soundbite": "Unanimous Winner"}],
            "contrarian": [{"rank": 1, "candidate_id": "sb_001", "soundbite": "Unanimous Winner"}],
            "simplifier": [{"rank": 1, "candidate_id": "sb_001", "soundbite": "Unanimous Winner"}],
        }

        result = aggregate_rankings(rankings)

        # 50 base points + 5 consensus bonus = 55
        assert result[0]["borda_points"] == 55
        assert result[0]["consensus_bonus"] is True

    def test_diverse_rankings_aggregates_to_consensus(self):
        """REQ-CR-001: Diverse rankings from angles resolve to consensus winners."""
        from cross_ranker import aggregate_rankings

        rankings = {
            "emotional": [
                {"rank": 1, "candidate_id": "sb_a", "soundbite": "A"},
                {"rank": 2, "candidate_id": "sb_b", "soundbite": "B"},
                {"rank": 3, "candidate_id": "sb_c", "soundbite": "C"},
            ],
            "identity": [
                {"rank": 1, "candidate_id": "sb_b", "soundbite": "B"},
                {"rank": 2, "candidate_id": "sb_a", "soundbite": "A"},
                {"rank": 3, "candidate_id": "sb_d", "soundbite": "D"},
            ],
            "action": [
                {"rank": 1, "candidate_id": "sb_c", "soundbite": "C"},
                {"rank": 2, "candidate_id": "sb_b", "soundbite": "B"},
                {"rank": 3, "candidate_id": "sb_a", "soundbite": "A"},
            ],
            "contrarian": [
                {"rank": 1, "candidate_id": "sb_a", "soundbite": "A"},
                {"rank": 2, "candidate_id": "sb_c", "soundbite": "C"},
                {"rank": 3, "candidate_id": "sb_b", "soundbite": "B"},
            ],
            "simplifier": [
                {"rank": 1, "candidate_id": "sb_b", "soundbite": "B"},
                {"rank": 2, "candidate_id": "sb_a", "soundbite": "A"},
                {"rank": 3, "candidate_id": "sb_c", "soundbite": "C"},
            ],
        }

        result = aggregate_rankings(rankings)

        # A: 10+9+8+10+9 = 46
        # B: 9+10+9+8+10 = 46
        # C: 8+0+10+9+8 = 35
        # With tiebreakers, one of A or B should be first
        top_ids = [r["candidate_id"] for r in result[:2]]
        assert "sb_a" in top_ids
        assert "sb_b" in top_ids

    # ==================== EDGE CASE TESTS ====================

    def test_tie_scores_apply_tiebreakers(self):
        """REQ-CR-003: Tie scores apply tiebreakers (authenticity > brevity > rank_count > emotional)."""
        from cross_ranker import aggregate_rankings

        # Two candidates with same Borda points but different tiebreaker values
        rankings = {
            "emotional": [
                {"rank": 1, "candidate_id": "sb_x", "soundbite": "X Test",
                 "scores": {"authenticity": 90, "brevity": 80, "emotional_resonance": 85}},
                {"rank": 2, "candidate_id": "sb_y", "soundbite": "Y Test",
                 "scores": {"authenticity": 85, "brevity": 90, "emotional_resonance": 90}},
            ],
            "identity": [
                {"rank": 1, "candidate_id": "sb_y", "soundbite": "Y Test",
                 "scores": {"authenticity": 85, "brevity": 90, "emotional_resonance": 90}},
                {"rank": 2, "candidate_id": "sb_x", "soundbite": "X Test",
                 "scores": {"authenticity": 90, "brevity": 80, "emotional_resonance": 85}},
            ],
        }

        result = aggregate_rankings(rankings)

        # Both have 19 points (10+9), but X has higher authenticity (90 > 85)
        assert result[0]["candidate_id"] == "sb_x"

    def test_candidate_ranked_by_only_1_angle(self):
        """REQ-CR-004: Candidate ranked by only 1 angle gets only that angle's points."""
        from cross_ranker import aggregate_rankings

        rankings = {
            "emotional": [
                {"rank": 1, "candidate_id": "sb_unique", "soundbite": "Unique"},
                {"rank": 2, "candidate_id": "sb_common", "soundbite": "Common"},
            ],
            "identity": [
                {"rank": 1, "candidate_id": "sb_common", "soundbite": "Common"},
            ],
            "action": [
                {"rank": 1, "candidate_id": "sb_common", "soundbite": "Common"},
            ],
            "contrarian": [
                {"rank": 1, "candidate_id": "sb_common", "soundbite": "Common"},
            ],
            "simplifier": [
                {"rank": 1, "candidate_id": "sb_common", "soundbite": "Common"},
            ],
        }

        result = aggregate_rankings(rankings)

        # Find sb_unique in results
        unique_result = next((r for r in result if r["candidate_id"] == "sb_unique"), None)
        assert unique_result is not None
        assert unique_result["borda_points"] == 10  # Only 1 first-place vote
        assert unique_result["angles_ranked"] == 1

    def test_all_angles_rank_same_candidate_1_consensus_bonus(self):
        """REQ-CR-002: All angles rank same candidate #1 gets consensus bonus."""
        from cross_ranker import aggregate_rankings

        rankings = {
            "emotional": [{"rank": 1, "candidate_id": "sb_winner", "soundbite": "Winner"}],
            "identity": [{"rank": 1, "candidate_id": "sb_winner", "soundbite": "Winner"}],
            "action": [{"rank": 1, "candidate_id": "sb_winner", "soundbite": "Winner"}],
            "contrarian": [{"rank": 1, "candidate_id": "sb_winner", "soundbite": "Winner"}],
            "simplifier": [{"rank": 1, "candidate_id": "sb_winner", "soundbite": "Winner"}],
        }

        result = aggregate_rankings(rankings)

        # 5 * 10 = 50 base + 5 consensus bonus = 55
        assert result[0]["borda_points"] == 55
        assert result[0]["consensus_bonus"] is True
        assert result[0]["top_5_count"] == 5  # In top 5 of all 5 angles

    def test_only_3_angles_provide_rankings(self):
        """REQ-CR-004: System works with only 3 angles providing rankings."""
        from cross_ranker import aggregate_rankings

        rankings = {
            "emotional": [
                {"rank": 1, "candidate_id": "sb_a", "soundbite": "A"},
                {"rank": 2, "candidate_id": "sb_b", "soundbite": "B"},
            ],
            "identity": [
                {"rank": 1, "candidate_id": "sb_b", "soundbite": "B"},
                {"rank": 2, "candidate_id": "sb_a", "soundbite": "A"},
            ],
            "action": [
                {"rank": 1, "candidate_id": "sb_a", "soundbite": "A"},
                {"rank": 2, "candidate_id": "sb_b", "soundbite": "B"},
            ],
            # contrarian and simplifier missing
        }

        result = aggregate_rankings(rankings)

        assert len(result) >= 1
        # A: 10+9+10 = 29, B: 9+10+9 = 28
        assert result[0]["candidate_id"] == "sb_a"
        assert result[0]["borda_points"] == 34  # 29 base + 5 consensus bonus (top-5 in 3+ angles)

    def test_empty_rankings_from_one_angle_excluded(self):
        """REQ-CR-004: Empty rankings from one angle are excluded from aggregation."""
        from cross_ranker import aggregate_rankings

        rankings = {
            "emotional": [
                {"rank": 1, "candidate_id": "sb_a", "soundbite": "A"},
            ],
            "identity": [],  # Empty
            "action": [
                {"rank": 1, "candidate_id": "sb_a", "soundbite": "A"},
            ],
        }

        result = aggregate_rankings(rankings)

        # Should work with 2 angles
        assert len(result) >= 1
        assert result[0]["borda_points"] == 20  # 10 + 10 from 2 angles

    # ==================== FAILURE PATH TESTS ====================

    def test_duplicate_candidate_in_same_angle_raises_error(self):
        """REQ-CR-004: Duplicate candidate IDs in same angle's ranking raises DuplicateError."""
        from cross_ranker import aggregate_rankings, DuplicateError

        rankings = {
            "emotional": [
                {"rank": 1, "candidate_id": "sb_dup", "soundbite": "Duplicate"},
                {"rank": 2, "candidate_id": "sb_dup", "soundbite": "Duplicate"},  # Duplicate!
            ],
        }

        with pytest.raises(DuplicateError, match="(?i)duplicate candidate"):
            aggregate_rankings(rankings)

    def test_invalid_rank_number_raises_error(self):
        """REQ-CR-004: Invalid rank number (>10 or <1) raises RangeError."""
        from cross_ranker import aggregate_rankings, RangeError

        rankings = {
            "emotional": [
                {"rank": 0, "candidate_id": "sb_invalid", "soundbite": "Invalid"},
            ],
        }

        with pytest.raises(RangeError, match="rank must be between 1 and 10"):
            aggregate_rankings(rankings)

        rankings_over = {
            "emotional": [
                {"rank": 11, "candidate_id": "sb_invalid", "soundbite": "Invalid"},
            ],
        }

        with pytest.raises(RangeError, match="rank must be between 1 and 10"):
            aggregate_rankings(rankings_over)

    def test_missing_angle_identifier_raises_keyerror(self):
        """REQ-CR-004: Rankings without proper structure raises KeyError."""
        from cross_ranker import aggregate_rankings

        # Missing required fields in ranking entry
        rankings = {
            "emotional": [
                {"rank": 1, "soundbite": "Missing ID"},  # Missing candidate_id
            ],
        }

        with pytest.raises(KeyError, match="candidate_id"):
            aggregate_rankings(rankings)


class TestBordaPointCalculation:
    """Test Borda point calculation logic."""

    def test_rank_1_gets_10_points(self):
        """Rank 1 should get 10 Borda points."""
        from cross_ranker import calculate_borda_points

        assert calculate_borda_points(1) == 10

    def test_rank_10_gets_1_point(self):
        """Rank 10 should get 1 Borda point."""
        from cross_ranker import calculate_borda_points

        assert calculate_borda_points(10) == 1

    def test_unranked_gets_0_points(self):
        """Unranked candidates get 0 points."""
        from cross_ranker import calculate_borda_points

        assert calculate_borda_points(None) == 0

    def test_all_ranks_1_through_10(self):
        """Verify point values for all ranks 1-10."""
        from cross_ranker import calculate_borda_points

        expected = {1: 10, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}

        for rank, expected_points in expected.items():
            assert calculate_borda_points(rank) == expected_points


class TestConsensusBonus:
    """Test consensus bonus logic."""

    def test_bonus_when_top_5_in_3_plus_angles(self):
        """REQ-CR-002: +5 bonus if in top-5 of 3+ angles."""
        from cross_ranker import calculate_consensus_bonus

        # In top 5 of 4 angles
        top_5_counts = {"sb_test": 4}

        bonus = calculate_consensus_bonus("sb_test", top_5_counts)
        assert bonus == 5

    def test_no_bonus_when_top_5_in_2_angles(self):
        """No bonus if in top-5 of only 2 angles."""
        from cross_ranker import calculate_consensus_bonus

        top_5_counts = {"sb_test": 2}

        bonus = calculate_consensus_bonus("sb_test", top_5_counts)
        assert bonus == 0

    def test_bonus_exactly_3_angles(self):
        """Bonus applies at exactly 3 angles threshold."""
        from cross_ranker import calculate_consensus_bonus

        top_5_counts = {"sb_test": 3}

        bonus = calculate_consensus_bonus("sb_test", top_5_counts)
        assert bonus == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
