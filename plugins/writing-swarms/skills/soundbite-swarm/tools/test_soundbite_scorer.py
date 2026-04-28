#!/usr/bin/env python3
"""
Tests for soundbite-scorer.py

REQ-SBS-001: Score soundbites on 7 weighted dimensions
REQ-SBS-002: Return weighted composite score
REQ-SBS-003: Handle edge cases (single word, 7+ words)
REQ-SBS-004: Validate input types and ranges
"""

import pytest
import sys
from pathlib import Path

# Add tools directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


class TestSoundbiteScorer:
    """Test suite for soundbite scoring functionality."""

    # ==================== HAPPY PATH TESTS ====================

    def test_score_3_word_soundbite_high_emotional(self):
        """REQ-SBS-001: Score a 3-word soundbite with high emotional resonance."""
        from soundbite_scorer import score_soundbite

        scores = {
            "memorability": 90,
            "emotional_resonance": 95,
            "brevity": 100,  # 3 words = 100
            "rhythm": 85,
            "universality": 80,
            "action_potential": 75,
            "authenticity": 88
        }

        result = score_soundbite("You Already Know", scores)

        # Check weighted composite is calculated correctly
        # (90*0.25) + (95*0.20) + (100*0.15) + (85*0.10) + (80*0.10) + (75*0.10) + (88*0.10)
        # = 22.5 + 19.0 + 15.0 + 8.5 + 8.0 + 7.5 + 8.8 = 89.3
        assert result["overall"] == pytest.approx(89.3, rel=0.01)
        assert result["soundbite"] == "You Already Know"
        assert result["word_count"] == 3

    def test_score_just_do_it_style_soundbite(self):
        """REQ-SBS-001: 'Just Do It' style soundbite scores 85+."""
        from soundbite_scorer import score_soundbite

        scores = {
            "memorability": 95,
            "emotional_resonance": 90,
            "brevity": 100,  # 3 words
            "rhythm": 92,
            "universality": 95,
            "action_potential": 98,
            "authenticity": 90
        }

        result = score_soundbite("Just Do It", scores)

        assert result["overall"] >= 85
        assert result["tier"] == "excellent"

    def test_score_multiple_soundbites_returns_sorted(self):
        """REQ-SBS-002: Score multiple soundbites, return sorted by overall score."""
        from soundbite_scorer import score_multiple_soundbites

        soundbites = [
            {
                "soundbite": "Be More",
                "scores": {
                    "memorability": 70, "emotional_resonance": 75,
                    "brevity": 95, "rhythm": 70,
                    "universality": 70, "action_potential": 75,
                    "authenticity": 72
                }
            },
            {
                "soundbite": "Think Different",
                "scores": {
                    "memorability": 95, "emotional_resonance": 90,
                    "brevity": 95, "rhythm": 88,
                    "universality": 92, "action_potential": 85,
                    "authenticity": 90
                }
            },
            {
                "soundbite": "Feel That",
                "scores": {
                    "memorability": 80, "emotional_resonance": 88,
                    "brevity": 95, "rhythm": 78,
                    "universality": 75, "action_potential": 70,
                    "authenticity": 82
                }
            }
        ]

        results = score_multiple_soundbites(soundbites)

        # Should be sorted descending by overall score
        assert len(results) == 3
        assert results[0]["soundbite"] == "Think Different"
        assert results[0]["overall"] > results[1]["overall"]
        assert results[1]["overall"] > results[2]["overall"]

    # ==================== EDGE CASE TESTS ====================

    def test_single_word_soundbite_brevity_score(self):
        """REQ-SBS-003: Single word soundbite gets brevity score of 95."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("Now")
        assert score == 95

    def test_2_word_soundbite_brevity_score(self):
        """REQ-SBS-003: 2-word soundbite gets brevity score of 95."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("Start Now")
        assert score == 95

    def test_3_word_soundbite_brevity_score(self):
        """REQ-SBS-003: 3-word soundbite gets brevity score of 100 (ideal)."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("Just Do It")
        assert score == 100

    def test_4_word_soundbite_brevity_score(self):
        """REQ-SBS-003: 4-word soundbite gets brevity score of 90."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("Because You Are Worth")
        assert score == 90

    def test_5_word_soundbite_brevity_score(self):
        """REQ-SBS-003: 5-word soundbite gets brevity score of 75."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("Because You Are Worth It")
        assert score == 75

    def test_6_word_soundbite_brevity_score(self):
        """REQ-SBS-003: 6-word soundbite gets brevity score of 60."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("This Is What We Live For")
        assert score == 60

    def test_7_word_soundbite_brevity_penalty(self):
        """REQ-SBS-003: 7-word soundbite gets brevity score of 40."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("This Is What We All Live For")
        assert score == 40

    def test_8_plus_words_hard_penalty(self):
        """REQ-SBS-003: 8+ word soundbite gets brevity score of 20."""
        from soundbite_scorer import calculate_brevity_score

        score = calculate_brevity_score("This Is What We Are All Living For Now")
        assert score == 20

    def test_empty_scores_returns_zero_with_error(self):
        """REQ-SBS-003: Empty scores dict returns 0 with error flag."""
        from soundbite_scorer import score_soundbite

        result = score_soundbite("Test", {})

        assert result["overall"] == 0
        assert result["error"] is True
        assert "empty scores" in result["error_message"].lower()

    def test_threshold_boundary_exactly_75(self):
        """REQ-SBS-003: Score of exactly 75 (threshold boundary) is handled."""
        from soundbite_scorer import score_soundbite, determine_tier

        scores = {
            "memorability": 75,
            "emotional_resonance": 75,
            "brevity": 75,
            "rhythm": 75,
            "universality": 75,
            "action_potential": 75,
            "authenticity": 75
        }

        result = score_soundbite("Test Boundary", scores)

        assert result["overall"] == 75
        tier = determine_tier(75)
        assert tier == "acceptable"  # >= 75 passes threshold

    # ==================== FAILURE PATH TESTS ====================

    def test_invalid_score_type_raises_valueerror(self):
        """REQ-SBS-004: Invalid score type (string instead of int) raises ValueError."""
        from soundbite_scorer import score_soundbite

        scores = {
            "memorability": "ninety",  # Invalid: string instead of number
            "emotional_resonance": 75,
            "brevity": 75,
            "rhythm": 75,
            "universality": 75,
            "action_potential": 75,
            "authenticity": 75
        }

        with pytest.raises(ValueError, match="score must be numeric"):
            score_soundbite("Test", scores)

    def test_missing_required_dimension_raises_keyerror(self):
        """REQ-SBS-004: Missing required dimension raises KeyError."""
        from soundbite_scorer import score_soundbite

        scores = {
            "memorability": 75,
            "emotional_resonance": 75,
            # Missing: brevity
            "rhythm": 75,
            "universality": 75,
            "action_potential": 75,
            "authenticity": 75
        }

        with pytest.raises(KeyError, match="brevity"):
            score_soundbite("Test", scores)

    def test_score_over_100_clamps_or_raises(self):
        """REQ-SBS-004: Score over 100 is clamped to 100."""
        from soundbite_scorer import validate_score

        # Should clamp to 100
        result = validate_score(150)
        assert result == 100

    def test_score_below_0_clamps_or_raises(self):
        """REQ-SBS-004: Score below 0 is clamped to 0."""
        from soundbite_scorer import validate_score

        # Should clamp to 0
        result = validate_score(-10)
        assert result == 0

    def test_none_soundbite_raises_typeerror(self):
        """REQ-SBS-004: None soundbite input raises TypeError."""
        from soundbite_scorer import score_soundbite

        scores = {
            "memorability": 75,
            "emotional_resonance": 75,
            "brevity": 75,
            "rhythm": 75,
            "universality": 75,
            "action_potential": 75,
            "authenticity": 75
        }

        with pytest.raises(TypeError, match="soundbite cannot be None"):
            score_soundbite(None, scores)

    # ==================== WEIGHT VALIDATION TESTS ====================

    def test_weights_sum_to_100(self):
        """REQ-SBS-002: Weights should sum to 100% (1.0)."""
        from soundbite_scorer import DIMENSION_WEIGHTS

        total = sum(DIMENSION_WEIGHTS.values())
        assert total == pytest.approx(1.0, rel=0.001)

    def test_correct_weights_per_dimension(self):
        """REQ-SBS-002: Verify correct weights for each dimension."""
        from soundbite_scorer import DIMENSION_WEIGHTS

        assert DIMENSION_WEIGHTS["memorability"] == 0.25
        assert DIMENSION_WEIGHTS["emotional_resonance"] == 0.20
        assert DIMENSION_WEIGHTS["brevity"] == 0.15
        assert DIMENSION_WEIGHTS["rhythm"] == 0.10
        assert DIMENSION_WEIGHTS["universality"] == 0.10
        assert DIMENSION_WEIGHTS["action_potential"] == 0.10
        assert DIMENSION_WEIGHTS["authenticity"] == 0.10


class TestTierDetermination:
    """Test tier classification based on scores."""

    def test_excellent_tier_90_plus(self):
        """Scores 90+ should be 'excellent' tier."""
        from soundbite_scorer import determine_tier

        assert determine_tier(95) == "excellent"
        assert determine_tier(90) == "excellent"

    def test_good_tier_85_to_89(self):
        """Scores 85-89 should be 'good' tier."""
        from soundbite_scorer import determine_tier

        assert determine_tier(85) == "good"
        assert determine_tier(89) == "good"

    def test_acceptable_tier_75_to_84(self):
        """Scores 75-84 should be 'acceptable' tier."""
        from soundbite_scorer import determine_tier

        assert determine_tier(75) == "acceptable"
        assert determine_tier(84) == "acceptable"

    def test_below_threshold_under_75(self):
        """Scores under 75 should be 'below_threshold' tier."""
        from soundbite_scorer import determine_tier

        assert determine_tier(74) == "below_threshold"
        assert determine_tier(50) == "below_threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
