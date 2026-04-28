#!/usr/bin/env python3
"""
Soundbite Validator

Validates soundbites against quality gates:
- Authenticity >= 60 (hard gate)
- Brevity >= 50 (max 7 words)
- Overall >= 75 (to advance to cross-ranking)
- No banned cliches ("unlock potential", "next level", etc.)

Usage:
    python soundbite_validator.py --soundbite '<json_soundbite>'

Output (JSON):
    {
      "valid": true,
      "failed_gates": [],
      "soundbite": "Think Different"
    }
"""

import json
import sys
from typing import Dict, Any, List, Optional


class ValidationError(Exception):
    """Raised when soundbite structure is invalid."""
    pass


# Quality gate thresholds
GATES = {
    "authenticity": 60,
    "brevity": 50,
    "overall": 75
}

# Maximum allowed word count
MAX_WORDS = 7

# Cliche blocklist - banned phrases that fail authenticity
CLICHE_BLOCKLIST = [
    "unlock potential",
    "unlock your potential",
    "next level",
    "take it to the next level",
    "be the best you",
    "be your best self",
    "game changer",
    "game-changer",
    "paradigm shift",
    "think outside the box",
    "move the needle",
    "low-hanging fruit",
    "synergy",
    "synergize",
    "leverage",
    "leverage your",
    "empower",
    "empower yourself",
    "best practices",
    "at the end of the day",
    "win-win",
    "circle back",
    "take ownership",
    "crushing it",
    "hustle harder",
    "rise and grind",
    "manifest your",
    "live your best life",
    "journey",
    "authentic self"
]


def _check_cliches(soundbite: str) -> Optional[str]:
    """
    Check if soundbite contains banned cliches.

    Args:
        soundbite: The soundbite text

    Returns:
        Matched cliche if found, None otherwise
    """
    soundbite_lower = soundbite.lower()

    for cliche in CLICHE_BLOCKLIST:
        if cliche.lower() in soundbite_lower:
            return cliche

    return None


def validate_soundbite(soundbite_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a soundbite against quality gates.

    Args:
        soundbite_data: Dict with 'soundbite' text and 'scores' dict

    Returns:
        Dict with validation result and failed gates

    Raises:
        ValidationError: If scores object is missing
        TypeError: If scores are not numeric
        ValueError: If soundbite text is None
    """
    # Validate structure
    if "scores" not in soundbite_data:
        raise ValidationError("Missing required field: scores")

    soundbite_text = soundbite_data.get("soundbite")
    scores = soundbite_data["scores"]

    # Check for None soundbite
    if soundbite_text is None:
        raise ValueError("soundbite text cannot be None")

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
    word_count = len(soundbite_text.split()) if soundbite_text else 0
    if word_count > MAX_WORDS or word_count == 0:
        failed_gates.append({
            "gate": "word_count",
            "threshold": MAX_WORDS,
            "actual": word_count,
            "message": f"Word count {word_count} exceeds maximum {MAX_WORDS}"
        })

    # Check for cliches
    matched_cliche = _check_cliches(soundbite_text)
    if matched_cliche:
        failed_gates.append({
            "gate": "cliche",
            "matched_cliche": matched_cliche,
            "message": f"Contains banned cliche: '{matched_cliche}'"
        })

    return {
        "valid": len(failed_gates) == 0,
        "soundbite": soundbite_text,
        "word_count": word_count,
        "failed_gates": failed_gates,
        "gates_checked": list(GATES.keys()) + ["word_count", "cliche"]
    }


def validate_batch(soundbites: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of soundbites.

    Args:
        soundbites: List of soundbite dicts to validate

    Returns:
        Dict with validation summary and lists of valid/invalid soundbites
    """
    valid_soundbites = []
    invalid_soundbites = []

    for soundbite in soundbites:
        try:
            result = validate_soundbite(soundbite)
            if result["valid"]:
                valid_soundbites.append({
                    **soundbite,
                    "validation_result": result
                })
            else:
                invalid_soundbites.append({
                    **soundbite,
                    "validation_result": result
                })
        except (ValidationError, TypeError, ValueError) as e:
            invalid_soundbites.append({
                **soundbite,
                "validation_result": {
                    "valid": False,
                    "error": str(e)
                }
            })

    return {
        "total": len(soundbites),
        "valid_count": len(valid_soundbites),
        "invalid_count": len(invalid_soundbites),
        "valid_soundbites": valid_soundbites,
        "invalid_soundbites": invalid_soundbites
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate soundbites against quality gates")
    parser.add_argument("--soundbite", required=True, help="JSON string with soundbite data")
    parser.add_argument("--batch", action="store_true", help="Validate a batch of soundbites")

    args = parser.parse_args()

    try:
        data = json.loads(args.soundbite)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    try:
        if args.batch:
            result = validate_batch(data)
        else:
            result = validate_soundbite(data)

        print(json.dumps(result, indent=2))

        # Exit with error if invalid
        if not result.get("valid", True):
            sys.exit(1)

    except (ValidationError, TypeError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
