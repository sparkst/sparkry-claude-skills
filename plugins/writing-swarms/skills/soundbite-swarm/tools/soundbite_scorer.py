#!/usr/bin/env python3
"""
Soundbite Scorer

Scores soundbites on 7 weighted dimensions:
- Memorability (25%): Sticks after one exposure
- Emotional Resonance (20%): Triggers feeling
- Brevity (15%): Word count optimization (ideal 2-5 words)
- Rhythm/Cadence (10%): Musical quality
- Universality (10%): Broad applicability
- Action Potential (10%): Inspires action
- Authenticity (10%): Genuine, not salesy

Usage:
    python soundbite_scorer.py <soundbite> --scores '{"memorability": 90, ...}'

Output (JSON):
    {
      "soundbite": "Just Do It",
      "word_count": 3,
      "overall": 89.3,
      "tier": "excellent",
      "scores": {...}
    }
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


# Dimension weights (must sum to 1.0)
DIMENSION_WEIGHTS: Dict[str, float] = {
    "memorability": 0.25,
    "emotional_resonance": 0.20,
    "brevity": 0.15,
    "rhythm": 0.10,
    "universality": 0.10,
    "action_potential": 0.10,
    "authenticity": 0.10
}

# Required dimensions
REQUIRED_DIMENSIONS = list(DIMENSION_WEIGHTS.keys())

# Brevity score mapping by word count
BREVITY_SCORES: Dict[int, int] = {
    1: 95,
    2: 95,
    3: 100,  # Ideal
    4: 90,
    5: 75,
    6: 60,
    7: 40,
}
BREVITY_8_PLUS = 20


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


def calculate_brevity_score(soundbite: str) -> int:
    """
    Calculate brevity score based on word count.

    Args:
        soundbite: The soundbite text

    Returns:
        Brevity score (0-100)
    """
    if not soundbite:
        return 0

    word_count = len(soundbite.split())

    if word_count >= 8:
        return BREVITY_8_PLUS

    return BREVITY_SCORES.get(word_count, BREVITY_8_PLUS)


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


def score_soundbite(soundbite: Optional[str], scores: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a soundbite on all 7 dimensions.

    Args:
        soundbite: The soundbite text
        scores: Dict with scores for each dimension

    Returns:
        Dict with overall score, tier, and metadata

    Raises:
        TypeError: If soundbite is None
        KeyError: If required dimension is missing
        ValueError: If score is not numeric
    """
    # Validate soundbite
    if soundbite is None:
        raise TypeError("soundbite cannot be None")

    # Handle empty scores
    if not scores:
        return {
            "soundbite": soundbite,
            "word_count": len(soundbite.split()) if soundbite else 0,
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
        "soundbite": soundbite,
        "word_count": len(soundbite.split()) if soundbite else 0,
        "overall": overall,
        "tier": tier,
        "scores": validated_scores
    }


def score_multiple_soundbites(soundbites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score multiple soundbites and return sorted by overall score.

    Args:
        soundbites: List of dicts with 'soundbite' and 'scores' keys

    Returns:
        List of scored soundbites sorted by overall score descending
    """
    results = []

    for item in soundbites:
        soundbite_text = item.get("soundbite", "")
        scores = item.get("scores", {})

        try:
            result = score_soundbite(soundbite_text, scores)
            results.append(result)
        except (TypeError, KeyError, ValueError) as e:
            # Include failed scoring with error
            results.append({
                "soundbite": soundbite_text,
                "word_count": len(soundbite_text.split()) if soundbite_text else 0,
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

    parser = argparse.ArgumentParser(description="Score a soundbite on 7 dimensions")
    parser.add_argument("soundbite", help="The soundbite text to score")
    parser.add_argument("--scores", required=True, help="JSON string with dimension scores")

    args = parser.parse_args()

    try:
        scores = json.loads(args.scores)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    try:
        result = score_soundbite(args.soundbite, scores)
        print(json.dumps(result, indent=2))

        # Exit with error if below threshold
        if result.get("tier") == "below_threshold":
            sys.exit(1)

    except (TypeError, KeyError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
