#!/usr/bin/env python3
"""
Tests for headline_scorer.py
"""

import pytest
from headline_scorer import (
    score_headline,
    score_multiple_headlines,
    calculate_brevity_score,
    determine_tier,
    validate_score,
    DIMENSION_WEIGHTS
)


class TestValidateScore:
    """Tests for validate_score function."""

    def test_valid_integer(self):
        assert validate_score(85) == 85

    def test_valid_float(self):
        assert validate_score(85.5) == 85

    def test_clamp_high(self):
        assert validate_score(150) == 100

    def test_clamp_low(self):
        assert validate_score(-10) == 0

    def test_none_value(self):
        assert validate_score(None) == 0

    def test_string_value(self):
        assert validate_score("85") == 0


class TestCalculateBrevityScore:
    """Tests for calculate_brevity_score function."""

    def test_optimal_8_words(self):
        headline = "The Honest AI Conversation Your Engineers Are Waiting"
        assert calculate_brevity_score(headline) == 100

    def test_7_words(self):
        headline = "What Real Leaders Say About AI"
        # 6 words actually
        assert calculate_brevity_score("One Two Three Four Five Six Seven") == 95

    def test_very_short(self):
        headline = "AI"
        assert calculate_brevity_score(headline) == 60

    def test_too_long(self):
        headline = "This Is A Very Long Headline That Goes On And On And On And On And On And More"
        assert calculate_brevity_score(headline) == 40

    def test_empty_string(self):
        assert calculate_brevity_score("") == 0


class TestDetermineTier:
    """Tests for determine_tier function."""

    def test_excellent(self):
        assert determine_tier(95) == "excellent"
        assert determine_tier(90) == "excellent"

    def test_good(self):
        assert determine_tier(89) == "good"
        assert determine_tier(85) == "good"

    def test_acceptable(self):
        assert determine_tier(84) == "acceptable"
        assert determine_tier(75) == "acceptable"

    def test_below_threshold(self):
        assert determine_tier(74) == "below_threshold"
        assert determine_tier(50) == "below_threshold"


class TestScoreHeadline:
    """Tests for score_headline function."""

    def test_valid_headline(self):
        headline = "The Honest AI Conversation Your Engineers Are Waiting For"
        scores = {
            "curiosity": 88,
            "clarity": 92,
            "promise": 90,
            "brevity": 95,
            "authenticity": 95,
            "seo_potential": 80
        }

        result = score_headline(headline, scores)

        assert result["headline"] == headline
        assert result["word_count"] == 9
        assert result["overall"] > 0
        assert result["tier"] in ["excellent", "good", "acceptable", "below_threshold"]

    def test_none_headline_raises_error(self):
        with pytest.raises(TypeError):
            score_headline(None, {"curiosity": 80})

    def test_empty_scores_returns_error(self):
        result = score_headline("Test Headline Here", {})
        assert result["error"] == True
        assert result["overall"] == 0

    def test_missing_dimension_raises_error(self):
        with pytest.raises(KeyError):
            score_headline("Test Headline", {"curiosity": 80})

    def test_non_numeric_score_raises_error(self):
        with pytest.raises(ValueError):
            score_headline("Test Headline", {
                "curiosity": "high",
                "clarity": 80,
                "promise": 80,
                "brevity": 80,
                "authenticity": 80,
                "seo_potential": 80
            })

    def test_weighted_calculation(self):
        headline = "Test Headline For Scoring"
        scores = {
            "curiosity": 100,
            "clarity": 100,
            "promise": 100,
            "brevity": 100,
            "authenticity": 100,
            "seo_potential": 100
        }

        result = score_headline(headline, scores)
        assert result["overall"] == 100.0


class TestScoreMultipleHeadlines:
    """Tests for score_multiple_headlines function."""

    def test_multiple_headlines(self):
        headlines = [
            {
                "headline": "First Headline Test",
                "scores": {
                    "curiosity": 70,
                    "clarity": 70,
                    "promise": 70,
                    "brevity": 70,
                    "authenticity": 70,
                    "seo_potential": 70
                }
            },
            {
                "headline": "Second Headline Better",
                "scores": {
                    "curiosity": 90,
                    "clarity": 90,
                    "promise": 90,
                    "brevity": 90,
                    "authenticity": 90,
                    "seo_potential": 90
                }
            }
        ]

        results = score_multiple_headlines(headlines)

        assert len(results) == 2
        # Should be sorted by score descending
        assert results[0]["overall"] > results[1]["overall"]

    def test_handles_errors_in_batch(self):
        headlines = [
            {
                "headline": "Valid Headline Test",
                "scores": {
                    "curiosity": 80,
                    "clarity": 80,
                    "promise": 80,
                    "brevity": 80,
                    "authenticity": 80,
                    "seo_potential": 80
                }
            },
            {
                "headline": "Invalid Missing Scores",
                "scores": {}
            }
        ]

        results = score_multiple_headlines(headlines)

        assert len(results) == 2
        # First should be valid, second should have error
        assert "error" not in results[0] or results[0].get("error") == False
        assert results[1].get("error") == True


class TestWeightsSum:
    """Verify dimension weights sum to 1.0."""

    def test_weights_sum_to_one(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
