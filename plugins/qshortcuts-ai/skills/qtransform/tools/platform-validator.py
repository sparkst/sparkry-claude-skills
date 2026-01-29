#!/usr/bin/env python3
"""
Platform Validator - Validate platform requirements

Validates content against platform-specific constraints including length,
formatting, tone, and structural requirements.

Usage:
    python platform-validator.py --content post.md --platform linkedin

Output (JSON):
    {
      "platform": "linkedin",
      "valid": false,
      "violations": [
        {
          "constraint": "hook_length",
          "expected": "≤25 words",
          "actual": "32 words",
          "priority": "P0"
        }
      ],
      "warnings": [],
      "metrics": {
        "word_count": 1850,
        "hook_words": 32,
        "paragraphs": 28,
        "avg_sentence_length": 14
      },
      "recommendations": []
    }
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List


# Platform constraints
PLATFORM_CONSTRAINTS = {
    "linkedin": {
        "hook_max_words": 25,
        "max_length_words": 2000,
        "min_length_words": 100,
        "formality_min": 0.6,
        "hashtags_recommended": [3, 5]
    },
    "twitter": {
        "max_chars": 280,
        "optimal_chars": [40, 80],
        "hashtags_max": 2,
        "formality_max": 0.6
    },
    "instagram": {
        "caption_min_words": 125,
        "caption_max_words": 200,
        "hashtags_optimal": [3, 5],
        "formality_max": 0.5
    },
    "substack": {
        "min_length_words": 800,
        "max_length_words": 3000,
        "formality_min": 0.5
    },
    "email": {
        "subject_required": True,
        "max_paragraphs": 10,
        "cta_required": True,
        "formality_range": [0.5, 0.7]
    }
}


def load_platform_constraints(platform: str) -> Dict[str, Any]:
    """
    Load platform constraints.

    Returns:
        Dict with platform-specific constraints
    """
    return PLATFORM_CONSTRAINTS.get(platform, {})


def analyze_content(content: str) -> Dict[str, Any]:
    """
    Analyze content metrics.

    Returns:
        Dict with word_count, hook_words, paragraphs, avg_sentence_length, char_count
    """
    lines = content.strip().split('\n')
    paragraphs = [p for p in lines if p.strip()]

    # Extract hook (first line or paragraph)
    hook = paragraphs[0] if paragraphs else ""
    hook_words = len(hook.split())

    # Count words
    word_count = len(content.split())

    # Count characters (no whitespace)
    char_count = len(content.replace('\n', '').replace(' ', ''))

    # Estimate average sentence length
    sentences = content.replace('!', '.').replace('?', '.').split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0

    return {
        "word_count": word_count,
        "char_count": char_count,
        "hook_words": hook_words,
        "paragraphs": len(paragraphs),
        "avg_sentence_length": round(avg_sentence_length, 1)
    }


def validate_constraints(
    metrics: Dict[str, Any],
    constraints: Dict[str, Any],
    platform: str
) -> tuple[bool, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Validate content against constraints.

    Returns:
        Tuple of (valid, violations, warnings)
    """
    violations = []
    warnings = []

    # LinkedIn constraints
    if platform == "linkedin":
        if metrics["hook_words"] > constraints["hook_max_words"]:
            violations.append({
                "constraint": "hook_length",
                "expected": f"≤{constraints['hook_max_words']} words",
                "actual": f"{metrics['hook_words']} words",
                "priority": "P0"
            })

        if metrics["word_count"] > constraints["max_length_words"]:
            violations.append({
                "constraint": "max_length",
                "expected": f"≤{constraints['max_length_words']} words",
                "actual": f"{metrics['word_count']} words",
                "priority": "P1"
            })

    # Twitter constraints
    elif platform == "twitter":
        if metrics["char_count"] > constraints["max_chars"]:
            violations.append({
                "constraint": "max_chars",
                "expected": f"≤{constraints['max_chars']} chars",
                "actual": f"{metrics['char_count']} chars",
                "priority": "P0"
            })

        optimal_min, optimal_max = constraints["optimal_chars"]
        if metrics["char_count"] < optimal_min or metrics["char_count"] > optimal_max:
            warnings.append({
                "constraint": "optimal_length",
                "message": f"Optimal length is {optimal_min}-{optimal_max} chars"
            })

    # Instagram constraints
    elif platform == "instagram":
        if metrics["word_count"] < constraints["caption_min_words"]:
            violations.append({
                "constraint": "min_length",
                "expected": f"≥{constraints['caption_min_words']} words",
                "actual": f"{metrics['word_count']} words",
                "priority": "P1"
            })

        if metrics["word_count"] > constraints["caption_max_words"]:
            violations.append({
                "constraint": "max_length",
                "expected": f"≤{constraints['caption_max_words']} words",
                "actual": f"{metrics['word_count']} words",
                "priority": "P1"
            })

    # Substack constraints
    elif platform == "substack":
        if metrics["word_count"] < constraints["min_length_words"]:
            violations.append({
                "constraint": "min_length",
                "expected": f"≥{constraints['min_length_words']} words",
                "actual": f"{metrics['word_count']} words",
                "priority": "P0"
            })

        if metrics["word_count"] > constraints["max_length_words"]:
            warnings.append({
                "constraint": "max_length",
                "message": f"Content exceeds recommended max ({constraints['max_length_words']} words)"
            })

    # Email constraints
    elif platform == "email":
        if metrics["paragraphs"] > constraints.get("max_paragraphs", 10):
            warnings.append({
                "constraint": "paragraph_count",
                "message": f"Consider reducing paragraphs (current: {metrics['paragraphs']})"
            })

    valid = len(violations) == 0

    return valid, violations, warnings


def generate_recommendations(
    violations: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    platform: str
) -> List[str]:
    """
    Generate recommendations based on validation results.

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Address violations
    for violation in violations:
        if violation["constraint"] == "hook_length":
            recommendations.append(f"Shorten hook to {violation['expected']}")
        elif violation["constraint"] == "max_length":
            recommendations.append(f"Reduce content length to {violation['expected']}")
        elif violation["constraint"] == "max_chars":
            recommendations.append(f"Reduce to {violation['expected']}")
        elif violation["constraint"] == "min_length":
            recommendations.append(f"Expand content to {violation['expected']}")

    # Address warnings
    for warning in warnings:
        if "optimal_length" in warning["constraint"]:
            recommendations.append("Aim for optimal length range")
        elif "paragraph_count" in warning["constraint"]:
            recommendations.append("Consider breaking into shorter paragraphs")

    return recommendations


def main():
    parser = argparse.ArgumentParser(description="Validate content against platform requirements")
    parser.add_argument("--content", required=True, help="Content file to validate")
    parser.add_argument("--platform", required=True,
                        choices=["linkedin", "twitter", "instagram", "substack", "email"],
                        help="Target platform")

    args = parser.parse_args()

    try:
        # Read content
        content_path = Path(args.content)
        if not content_path.exists():
            print(json.dumps({"error": f"File not found: {args.content}"}), file=sys.stderr)
            sys.exit(1)

        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Load platform constraints
        constraints = load_platform_constraints(args.platform)

        # Analyze content
        metrics = analyze_content(content)

        # Validate constraints
        valid, violations, warnings = validate_constraints(metrics, constraints, args.platform)

        # Generate recommendations
        recommendations = generate_recommendations(violations, warnings, args.platform)

        # Build result
        result = {
            "platform": args.platform,
            "valid": valid,
            "violations": violations,
            "warnings": warnings,
            "metrics": metrics,
            "recommendations": recommendations
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
