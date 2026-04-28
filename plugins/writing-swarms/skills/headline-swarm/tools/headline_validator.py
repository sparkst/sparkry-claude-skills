#!/usr/bin/env python3
"""
Headline Validator

Validates headlines against quality gates:
- Authenticity >= 60 (hard gate - no clickbait)
- Clarity >= 60 (must be understandable)
- Overall >= 75 (to advance to cross-ranking)
- Word count 5-15 (headline length requirement)
- No banned cliches or clickbait patterns

Usage:
    python headline_validator.py --headline '<json_headline>'

Output (JSON):
    {
      "valid": true,
      "failed_gates": [],
      "headline": "The Honest AI Conversation Your Engineers Are Waiting For"
    }
"""

import json
import re
import sys
from typing import Dict, Any, List, Optional


class ValidationError(Exception):
    """Raised when headline structure is invalid."""
    pass


# Quality gate thresholds
GATES = {
    "authenticity": 60,
    "clarity": 60,
    "overall": 75
}

# Word count bounds
MIN_WORDS = 5
MAX_WORDS = 15

# Cliche blocklist - banned phrases that fail authenticity
CLICHE_BLOCKLIST = [
    # Clickbait patterns
    "you won't believe",
    "this one simple trick",
    "everything you know is wrong",
    "mind-blowing",
    "shocking",
    "insane",
    "jaw-dropping",
    "game-changing",
    "what happened next",
    "doctors hate",
    "experts don't want you to know",
    "the secret",
    "hack your",
    "10x your",
    # Corporate buzzwords
    "leverage",
    "synergy",
    "synergize",
    "paradigm shift",
    "thought leadership",
    # Self-help cliches
    "unlock potential",
    "unlock your potential",
    "be the best you",
    "be your best self",
    "live your best life",
    "level up",
    "crushing it",
    "hustle harder",
    "rise and grind",
    # Overused templates
    "the only guide you'll ever need",
    "the ultimate guide to",
    "everything you need to know about",
    # Vague superlatives
    "revolutionary",
    "groundbreaking",
    "disruptive",
    "world-class",
    "best-in-class",
    "game-changer",
    # AI tells
    "delve into",
    "deep dive",
    "holistic approach",
    "in today's fast-paced"
]

# Pattern checks
PATTERN_CHECKS = [
    {
        "name": "excessive_punctuation",
        "pattern": r"[!?]{2,}",
        "message": "Multiple exclamation/question marks detected"
    },
    {
        "name": "all_caps_words",
        "pattern": r"\b[A-Z]{5,}\b",
        "message": "All-caps words detected (5+ letters, excluding acronyms)"
    }
]


def _check_cliches(headline: str) -> Optional[str]:
    """
    Check if headline contains banned cliches.

    Args:
        headline: The headline text

    Returns:
        Matched cliche if found, None otherwise
    """
    headline_lower = headline.lower()

    for cliche in CLICHE_BLOCKLIST:
        if cliche.lower() in headline_lower:
            return cliche

    return None


def _check_patterns(headline: str) -> Optional[Dict[str, str]]:
    """
    Check if headline matches problematic patterns.

    Args:
        headline: The headline text

    Returns:
        Dict with pattern name and message if matched, None otherwise
    """
    for check in PATTERN_CHECKS:
        if re.search(check["pattern"], headline):
            return {
                "pattern": check["name"],
                "message": check["message"]
            }

    return None


def validate_headline(headline_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a headline against quality gates.

    Args:
        headline_data: Dict with 'headline' text and 'scores' dict

    Returns:
        Dict with validation result and failed gates

    Raises:
        ValidationError: If scores object is missing
        TypeError: If scores are not numeric
        ValueError: If headline text is None
    """
    # Validate structure
    if "scores" not in headline_data:
        raise ValidationError("Missing required field: scores")

    headline_text = headline_data.get("headline")
    scores = headline_data["scores"]

    # Check for None headline
    if headline_text is None:
        raise ValueError("headline text cannot be None")

    # Validate scores are numeric
    for key, value in scores.items():
        if not isinstance(value, (int, float)):
            raise TypeError(f"Score '{key}' must be numeric, got {type(value).__name__}")

    failed_gates: List[Dict[str, Any]] = []

    # Check quality gates
    for gate, threshold in GATES.items():
        score = scores.get(gate, 0)
        if score < threshold:
            failed_gates.append({
                "gate": gate,
                "threshold": threshold,
                "actual": score,
                "message": f"{gate} score {score} is below threshold {threshold}"
            })

    # Check word count
    word_count = len(headline_text.split()) if headline_text else 0
    if word_count < MIN_WORDS:
        failed_gates.append({
            "gate": "word_count_min",
            "threshold": MIN_WORDS,
            "actual": word_count,
            "message": f"Word count {word_count} is below minimum {MIN_WORDS}"
        })
    elif word_count > MAX_WORDS:
        failed_gates.append({
            "gate": "word_count_max",
            "threshold": MAX_WORDS,
            "actual": word_count,
            "message": f"Word count {word_count} exceeds maximum {MAX_WORDS}"
        })

    # Check for cliches
    matched_cliche = _check_cliches(headline_text)
    if matched_cliche:
        failed_gates.append({
            "gate": "cliche",
            "matched_cliche": matched_cliche,
            "message": f"Contains banned cliche: '{matched_cliche}'"
        })

    # Check for problematic patterns
    matched_pattern = _check_patterns(headline_text)
    if matched_pattern:
        failed_gates.append({
            "gate": "pattern",
            "pattern": matched_pattern["pattern"],
            "message": matched_pattern["message"]
        })

    return {
        "valid": len(failed_gates) == 0,
        "headline": headline_text,
        "word_count": word_count,
        "failed_gates": failed_gates,
        "gates_checked": list(GATES.keys()) + ["word_count", "cliche", "pattern"]
    }


def validate_batch(headlines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of headlines.

    Args:
        headlines: List of headline dicts to validate

    Returns:
        Dict with validation summary and lists of valid/invalid headlines
    """
    valid_headlines = []
    invalid_headlines = []

    for headline in headlines:
        try:
            result = validate_headline(headline)
            if result["valid"]:
                valid_headlines.append({
                    **headline,
                    "validation_result": result
                })
            else:
                invalid_headlines.append({
                    **headline,
                    "validation_result": result
                })
        except (ValidationError, TypeError, ValueError) as e:
            invalid_headlines.append({
                **headline,
                "validation_result": {
                    "valid": False,
                    "error": str(e)
                }
            })

    return {
        "total": len(headlines),
        "valid_count": len(valid_headlines),
        "invalid_count": len(invalid_headlines),
        "valid_headlines": valid_headlines,
        "invalid_headlines": invalid_headlines
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate headlines against quality gates")
    parser.add_argument("--headline", required=True, help="JSON string with headline data")
    parser.add_argument("--batch", action="store_true", help="Validate a batch of headlines")

    args = parser.parse_args()

    try:
        data = json.loads(args.headline)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    try:
        if args.batch:
            result = validate_batch(data)
        else:
            result = validate_headline(data)

        print(json.dumps(result, indent=2))

        # Exit with error if invalid
        if not result.get("valid", True):
            sys.exit(1)

    except (ValidationError, TypeError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
