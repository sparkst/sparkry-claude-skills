#!/usr/bin/env python3
"""
Feedback Learner - Learn from feedback to improve future transformations

Learns patterns from engagement metrics to improve future content transformations.

Usage:
    python feedback-learner.py --transformations linkedin.md twitter.md --feedback feedback.json

Output (JSON):
    {
      "learning_summary": {
        "best_performing": "twitter",
        "metrics": {
          "linkedin": {...},
          "twitter": {...}
        }
      },
      "learned_patterns": [
        {
          "pattern": "twitter_hook_style",
          "finding": "Direct question hooks outperform statement hooks",
          "confidence": 0.82,
          "sample_size": 15
        }
      ],
      "recommendations": [],
      "next_experiments": []
    }
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List


def load_feedback(feedback_path: str) -> Dict[str, Any]:
    """
    Load feedback metrics from JSON file.

    Expected format:
    {
      "linkedin": {"engagement_rate": 0.12, "clicks": 45, "conversions": 3},
      "twitter": {"engagement_rate": 0.08, "clicks": 120, "conversions": 5}
    }

    Returns:
        Dict with feedback metrics per platform
    """
    feedback_path_obj = Path(feedback_path)

    if not feedback_path_obj.exists():
        return {}

    with open(feedback_path_obj, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_performance_score(metrics: Dict[str, Any]) -> float:
    """
    Calculate overall performance score from metrics.

    Returns:
        Performance score (0-1)
    """
    # Weighted scoring
    engagement_rate = metrics.get("engagement_rate", 0.0)
    clicks = metrics.get("clicks", 0)
    conversions = metrics.get("conversions", 0)

    # Normalize and weight
    score = (
        engagement_rate * 0.4 +
        min(clicks / 100.0, 1.0) * 0.3 +
        min(conversions / 10.0, 1.0) * 0.3
    )

    return round(score, 2)


def detect_platform(filename: str) -> str:
    """
    Detect platform from filename.

    Returns:
        Platform name or "unknown"
    """
    filename_lower = filename.lower()

    if "linkedin" in filename_lower:
        return "linkedin"
    elif "twitter" in filename_lower or "tweet" in filename_lower:
        return "twitter"
    elif "instagram" in filename_lower or "insta" in filename_lower:
        return "instagram"
    elif "email" in filename_lower:
        return "email"
    else:
        return "unknown"


def identify_patterns(
    transformations: List[str],
    feedback: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Identify learned patterns from feedback.

    Stub implementation - returns example patterns.
    In production, would use ML to identify real patterns.

    Returns:
        List of learned pattern dicts
    """
    patterns = []

    # Check if we have enough data
    if not feedback:
        return patterns

    # Example pattern 1: Twitter hooks
    if "twitter" in feedback:
        twitter_metrics = feedback["twitter"]
        if twitter_metrics.get("engagement_rate", 0) > 0.07:
            patterns.append({
                "pattern": "twitter_hook_style",
                "finding": "Direct question hooks outperform statement hooks",
                "confidence": 0.82,
                "sample_size": 15
            })

    # Example pattern 2: LinkedIn structure
    if "linkedin" in feedback:
        linkedin_metrics = feedback["linkedin"]
        if linkedin_metrics.get("engagement_rate", 0) > 0.10:
            patterns.append({
                "pattern": "linkedin_structure",
                "finding": "Bullet points increase engagement by 15%",
                "confidence": 0.75,
                "sample_size": 12
            })

    # Example pattern 3: Instagram emotion
    if "instagram" in feedback:
        instagram_metrics = feedback["instagram"]
        if instagram_metrics.get("engagement_rate", 0) > 0.05:
            patterns.append({
                "pattern": "instagram_emotion",
                "finding": "Personal stories increase engagement by 20%",
                "confidence": 0.68,
                "sample_size": 8
            })

    return patterns


def generate_recommendations(
    learning_summary: Dict[str, Any],
    patterns: List[Dict[str, Any]]
) -> List[str]:
    """
    Generate recommendations based on learning.

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Best performing platform
    best_platform = learning_summary.get("best_performing")
    if best_platform:
        recommendations.append(f"Prioritize {best_platform} - highest performance")

    # Pattern-based recommendations
    for pattern in patterns:
        if pattern["confidence"] > 0.75:
            recommendations.append(f"{pattern['pattern']}: {pattern['finding']}")

    # Performance-based recommendations
    metrics = learning_summary.get("metrics", {})
    for platform, platform_metrics in metrics.items():
        score = platform_metrics.get("performance_score", 0)
        if score < 0.5:
            recommendations.append(f"Improve {platform} performance (current score: {score:.2f})")

    return recommendations[:5]  # Limit to top 5


def suggest_experiments(
    transformations: List[str],
    patterns: List[Dict[str, Any]]
) -> List[str]:
    """
    Suggest next experiments.

    Returns:
        List of experiment suggestions
    """
    experiments = []

    # Based on platforms used
    platforms = [detect_platform(t) for t in transformations]

    if "linkedin" in platforms:
        experiments.append("A/B test: emoji usage on LinkedIn")

    if "twitter" in platforms:
        experiments.append("Test: thread vs single tweet on Twitter")

    if "instagram" in platforms:
        experiments.append("Test: carousel vs single image on Instagram")

    # Based on patterns
    for pattern in patterns:
        if pattern["confidence"] < 0.70:
            experiments.append(f"Validate {pattern['pattern']} with larger sample")

    return experiments[:3]  # Limit to top 3


def main():
    parser = argparse.ArgumentParser(description="Learn from feedback to improve transformations")
    parser.add_argument("--transformations", nargs="+", required=True,
                        help="Transformation files to analyze")
    parser.add_argument("--feedback", required=True,
                        help="Feedback JSON file with engagement metrics")

    args = parser.parse_args()

    try:
        # Load feedback
        feedback = load_feedback(args.feedback)

        # Build metrics summary
        metrics = {}
        for trans_file in args.transformations:
            platform = detect_platform(trans_file)
            if platform in feedback:
                platform_metrics = feedback[platform]
                performance_score = calculate_performance_score(platform_metrics)

                metrics[platform] = {
                    **platform_metrics,
                    "performance_score": performance_score
                }

        # Identify best performing
        best_performing = None
        best_score = 0.0
        for platform, platform_metrics in metrics.items():
            score = platform_metrics.get("performance_score", 0)
            if score > best_score:
                best_score = score
                best_performing = platform

        # Build learning summary
        learning_summary = {
            "best_performing": best_performing,
            "metrics": metrics
        }

        # Identify patterns
        patterns = identify_patterns(args.transformations, feedback)

        # Generate recommendations
        recommendations = generate_recommendations(learning_summary, patterns)

        # Suggest experiments
        experiments = suggest_experiments(args.transformations, patterns)

        # Build result
        result = {
            "learning_summary": learning_summary,
            "learned_patterns": patterns,
            "recommendations": recommendations,
            "next_experiments": experiments
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
