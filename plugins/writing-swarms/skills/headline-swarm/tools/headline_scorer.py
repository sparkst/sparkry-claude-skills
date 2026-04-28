#!/usr/bin/env python3
"""
Headline Scorer

Scores headlines on 6 weighted dimensions:
- Curiosity/Hook (25%): Creates intrigue, demands click
- Clarity (20%): Instantly understandable
- Promise/Value (20%): Clear benefit to reader
- Brevity (15%): Word count optimization (ideal 6-10 words)
- Authenticity (10%): Genuine, not clickbait
- SEO Potential (10%): Keyword relevance

Usage:
    python headline_scorer.py <headline> --scores '{"curiosity": 90, ...}'

Output (JSON):
    {
      "headline": "The Honest AI Conversation Your Engineers Are Waiting For",
      "word_count": 9,
      "overall": 87.3,
      "tier": "good",
      "scores": {...}
    }
"""

import json
import sys
from typing import Dict, Any, List, Optional


# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS: Dict[str, float] = {
    "curiosity": 0.25,
    "clarity": 0.20,
    "promise": 0.20,
    "brevity": 0.15,
    "authenticity": 0.10,
    "seo_potential": 0.10
}

# Required dimensions
REQUIRED_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())

# Brevity score mapping by word count (optimized for headlines)
BREVITY_SCORES: Dict[int, int] = {
    4: 70,
    5: 75,
    6: 90,
    7: 95,
    8: 100,  # Ideal for headlines
    9: 95,
    10: 90,
    11: 80,
    12: 70,
    13: 60,
    14: 55,
    15: 50,
}
BREVITY_16_PLUS = 40
BREVITY_3_OR_LESS = 60


def validate_score(score: Any) -> int:
    """
    Validate and clamp a score to 0-100 range.

    Args:
        score: Score value to validate

    Returns:
        Clamped score between 0 and 100
    """
    if score is None:
        return 0

    if isinstance(score, (int, float)):
        return max(0, min(100, int(score)))

    return 0


def calculate_brevity_score(headline: str) -> int:
    """
    Calculate brevity score based on word count.

    Args:
        headline: The headline text

    Returns:
        Brevity score (0-100)
    """
    if not headline:
        return 0

    word_count = len(headline.split())

    if word_count <= 3:
        return BREVITY_3_OR_LESS

    if word_count >= 16:
        return BREVITY_16_PLUS

    return BREVITY_SCORES.get(word_count, 50)


def determine_tier(overall_score: float) -> str:
    """
    Determine quality tier based on overall score.

    Args:
        overall_score: Weighted composite score

    Returns:
        Tier name: excellent, good, acceptable, or below_threshold
    """
    if overall_score >= 90:
        return "excellent"
    elif overall_score >= 85:
        return "good"
    elif overall_score >= 75:
        return "acceptable"
    else:
        return "below_threshold"


def score_headline(headline: Optional[str], scores: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a headline on all 6 dimensions.

    Args:
        headline: The headline text
        scores: Dict with scores for each dimension

    Returns:
        Dict with overall score, tier, and metadata

    Raises:
        TypeError: If headline is None
        KeyError: If required dimension is missing
        ValueError: If score is not numeric
    """
    # Validate headline
    if headline is None:
        raise TypeError("headline cannot be None")

    # Handle empty scores
    if not scores:
        return {
            "headline": headline,
            "word_count": len(headline.split()) if headline else 0,
            "overall": 0,
            "tier": "below_threshold",
            "scores": {},
            "error": True,
            "error_message": "Empty scores dict provided"
        }

    # Validate all required dimensions present
    for dim in REQUIRED_DIMENSIONS:
        if dim not in scores:
            raise KeyError(f"Missing required dimension: {dim}")

    # Validate all scores are numeric
    for dim, score in scores.items():
        if dim in REQUIRED_DIMENSIONS:
            if not isinstance(score, (int, float)):
                raise ValueError(f"{dim} score must be numeric, got {type(score).__name__}")

    # Calculate weighted composite
    weighted_sum = 0.0
    validated_scores = {}

    for dim, weight in DIMENSION_WEIGHTS.items():
        raw_score = scores.get(dim, 0)
        validated = validate_score(raw_score)
        validated_scores[dim] = validated
        weighted_sum += validated * weight

    overall = round(weighted_sum, 1)
    tier = determine_tier(overall)

    return {
        "headline": headline,
        "word_count": len(headline.split()) if headline else 0,
        "overall": overall,
        "tier": tier,
        "scores": validated_scores
    }


def score_multiple_headlines(headlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score multiple headlines and return sorted by overall score.

    Args:
        headlines: List of dicts with 'headline' and 'scores' keys

    Returns:
        List of scored headlines sorted by overall score descending
    """
    results = []

    for item in headlines:
        headline_text = item.get("headline", "")
        scores = item.get("scores", {})

        try:
            result = score_headline(headline_text, scores)
            results.append(result)
        except (TypeError, KeyError, ValueError) as e:
            # Include failed scoring with error
            results.append({
                "headline": headline_text,
                "word_count": len(headline_text.split()) if headline_text else 0,
                "overall": 0,
                "tier": "error",
                "error": True,
                "error_message": str(e)
            })

    # Sort by overall score descending
    results.sort(key=lambda x: x.get("overall", 0), reverse=True)

    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Score a headline on 6 dimensions")
    parser.add_argument("headline", help="The headline text to score")
    parser.add_argument("--scores", required=True, help="JSON string with dimension scores")

    args = parser.parse_args()

    try:
        scores = json.loads(args.scores)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    try:
        result = score_headline(args.headline, scores)
        print(json.dumps(result, indent=2))

        # Exit with error if below threshold
        if result.get("tier") == "below_threshold":
            sys.exit(1)

    except (TypeError, KeyError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
