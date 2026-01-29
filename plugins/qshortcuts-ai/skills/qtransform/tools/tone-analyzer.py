#!/usr/bin/env python3
"""
Tone Analyzer - Analyze tone consistency across transformations

Analyzes tone dimensions (formality, energy, directness, emotion) and
tracks tone shifts across platform transformations.

Usage:
    python tone-analyzer.py --source article.md --transformed linkedin.md twitter.md

Output (JSON):
    {
      "source_tone": {
        "formality": 0.7,
        "energy": 0.5,
        "directness": 0.8,
        "emotion": 0.4
      },
      "transformations": [
        {
          "platform": "linkedin",
          "file": "linkedin.md",
          "tone": {...},
          "tone_shift": {...},
          "consistency_score": 0.85
        }
      ],
      "message_preservation": 0.92,
      "recommendations": []
    }
"""

import json
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, Any, List


def analyze_tone(text: str) -> Dict[str, float]:
    """
    Analyze tone dimensions.

    Stub implementation using simple heuristics.
    In production, would use NLP models.

    Returns:
        Dict with formality, energy, directness, emotion scores (0-1)
    """
    # Formality indicators
    formal_words = ["therefore", "consequently", "furthermore", "however", "moreover"]
    casual_words = ["yeah", "cool", "awesome", "great", "lol", "hey"]

    formal_count = sum(1 for word in formal_words if word in text.lower())
    casual_count = sum(1 for word in casual_words if word in text.lower())

    # Formality score (higher = more formal)
    formality = 0.5 + (formal_count - casual_count) * 0.05
    formality = max(0.0, min(1.0, formality))

    # Energy indicators (exclamation marks, caps, energetic words)
    exclamations = text.count('!')
    caps_words = len([w for w in text.split() if w.isupper() and len(w) > 1])
    energy_words = ["exciting", "amazing", "incredible", "powerful", "revolutionary"]

    energy_count = exclamations + caps_words + sum(1 for word in energy_words if word in text.lower())
    energy = min(1.0, 0.3 + energy_count * 0.05)

    # Directness (active voice, imperative)
    imperative_pattern = r'\b(do|use|try|avoid|consider|start|stop|create)\b'
    imperative_count = len(re.findall(imperative_pattern, text.lower()))

    directness = min(1.0, 0.5 + imperative_count * 0.02)

    # Emotion (personal pronouns, emotional words)
    personal_pronouns = ["I", "my", "we", "our"]
    emotional_words = ["love", "hate", "fear", "hope", "excited", "worried"]

    personal_count = sum(text.count(p) for p in personal_pronouns)
    emotional_count = sum(1 for word in emotional_words if word in text.lower())

    emotion = min(1.0, 0.3 + (personal_count + emotional_count) * 0.03)

    return {
        "formality": round(formality, 2),
        "energy": round(energy, 2),
        "directness": round(directness, 2),
        "emotion": round(emotion, 2)
    }


def calculate_tone_shift(source_tone: Dict[str, float], target_tone: Dict[str, float]) -> Dict[str, str]:
    """
    Calculate tone shift from source to target.

    Returns:
        Dict with shift descriptions
    """
    shifts = {}

    for dimension, source_value in source_tone.items():
        target_value = target_tone[dimension]
        diff = target_value - source_value

        if abs(diff) < 0.1:
            shifts[dimension] = "No change (appropriate)"
        elif diff > 0:
            shifts[dimension] = f"+{diff:.1f} (more {dimension})"
        else:
            shifts[dimension] = f"{diff:.1f} (less {dimension})"

    return shifts


def calculate_consistency_score(source_tone: Dict[str, float], target_tone: Dict[str, float]) -> float:
    """
    Calculate tone consistency score.

    Returns:
        Consistency score (0-1)
    """
    # Calculate weighted difference
    differences = [abs(source_tone[dim] - target_tone[dim]) for dim in source_tone.keys()]
    avg_diff = sum(differences) / len(differences)

    # Convert to score (lower difference = higher score)
    consistency = 1.0 - avg_diff

    return round(consistency, 2)


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
    elif "substack" in filename_lower:
        return "substack"
    else:
        return "unknown"


def calculate_message_preservation(source: str, target: str) -> float:
    """
    Calculate message preservation score.

    Stub implementation using word overlap.
    In production, would use semantic similarity.

    Returns:
        Preservation score (0-1)
    """
    # Simple word overlap
    source_words = set(source.lower().split())
    target_words = set(target.lower().split())

    if not source_words:
        return 0.0

    overlap = len(source_words.intersection(target_words))
    preservation = overlap / len(source_words)

    return round(min(1.0, preservation * 1.2), 2)  # Boost score slightly


def generate_recommendations(
    transformations: List[Dict[str, Any]],
    message_preservation: float
) -> List[str]:
    """
    Generate recommendations based on analysis.

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Check message preservation
    if message_preservation < 0.80:
        recommendations.append(f"Message preservation low ({message_preservation:.0%}) - verify core message preserved")

    # Check tone shifts
    for trans in transformations:
        platform = trans["platform"]
        consistency = trans["consistency_score"]

        if consistency < 0.70:
            recommendations.append(f"{platform.title()}: Large tone shift - verify appropriateness")
        elif consistency > 0.95:
            recommendations.append(f"{platform.title()}: Tone unchanged - consider platform adaptation")

    # Platform-specific recommendations
    for trans in transformations:
        platform = trans["platform"]
        tone = trans["tone"]

        if platform == "linkedin" and tone["formality"] < 0.6:
            recommendations.append("LinkedIn: Consider increasing formality for professional audience")
        elif platform == "twitter" and tone["energy"] < 0.5:
            recommendations.append("Twitter: Consider increasing energy for engagement")
        elif platform == "instagram" and tone["emotion"] < 0.5:
            recommendations.append("Instagram: Consider more personal/emotional tone")

    return recommendations[:5]  # Limit to top 5


def main():
    parser = argparse.ArgumentParser(description="Analyze tone consistency across transformations")
    parser.add_argument("--source", required=True, help="Source content file")
    parser.add_argument("--transformed", nargs="+", required=True, help="Transformed content files")

    args = parser.parse_args()

    try:
        # Read source
        source_path = Path(args.source)
        if not source_path.exists():
            print(json.dumps({"error": f"Source file not found: {args.source}"}), file=sys.stderr)
            sys.exit(1)

        with open(source_path, 'r', encoding='utf-8') as f:
            source_text = f.read()

        # Analyze source tone
        source_tone = analyze_tone(source_text)

        # Analyze transformations
        transformations = []
        message_preservations = []

        for trans_file in args.transformed:
            trans_path = Path(trans_file)
            if not trans_path.exists():
                print(json.dumps({"error": f"Transformed file not found: {trans_file}"}), file=sys.stderr)
                continue

            with open(trans_path, 'r', encoding='utf-8') as f:
                trans_text = f.read()

            # Analyze tone
            trans_tone = analyze_tone(trans_text)

            # Calculate tone shift
            tone_shift = calculate_tone_shift(source_tone, trans_tone)

            # Calculate consistency
            consistency = calculate_consistency_score(source_tone, trans_tone)

            # Calculate message preservation
            preservation = calculate_message_preservation(source_text, trans_text)
            message_preservations.append(preservation)

            # Detect platform
            platform = detect_platform(trans_file)

            transformations.append({
                "platform": platform,
                "file": trans_file,
                "tone": trans_tone,
                "tone_shift": tone_shift,
                "consistency_score": consistency
            })

        # Overall message preservation
        avg_preservation = sum(message_preservations) / len(message_preservations) if message_preservations else 0.0

        # Generate recommendations
        recommendations = generate_recommendations(transformations, avg_preservation)

        # Build result
        result = {
            "source_tone": source_tone,
            "transformations": transformations,
            "message_preservation": round(avg_preservation, 2),
            "recommendations": recommendations
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
