#!/usr/bin/env python3
"""
Diversity Tracker

Tracks creative profiles to avoid repetition across user's infographics.
Stores fingerprints and calculates diversity scores.

Usage:
    # Log new creative profile
    python diversity-tracker.py log <user-id> <creative-profile-json>

    # Check diversity vs. history
    python diversity-tracker.py check <user-id> <candidate-profile-json> [--window 5]

Output (JSON):
    {
      "diversity_score": 0.82,
      "repeated_elements": [],
      "recommendations": ["Vary icon_system next time"],
      "history_count": 3
    }
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def get_history_file(user_id: str) -> Path:
    """Get path to user's history file."""
    history_dir = Path.home() / ".claude" / "data" / "infographic-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / f"{user_id}.json"


def load_history(user_id: str) -> List[Dict[str, Any]]:
    """Load user's creative profile history."""
    history_file = get_history_file(user_id)

    if not history_file.exists():
        return []

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_history(user_id: str, history: List[Dict[str, Any]]):
    """Save user's creative profile history."""
    history_file = get_history_file(user_id)

    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)


def log_profile(user_id: str, creative_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log new creative profile to user's history.

    Args:
        user_id: User identifier
        creative_profile: Creative profile to log

    Returns:
        Result dict
    """
    history = load_history(user_id)

    # Add timestamp
    entry = creative_profile.copy()
    entry["timestamp"] = datetime.utcnow().isoformat()

    # Create fingerprint
    entry["fingerprint"] = create_fingerprint(creative_profile)

    history.append(entry)

    # Limit history size (keep last 20)
    if len(history) > 20:
        history = history[-20:]

    save_history(user_id, history)

    return {
        "status": "logged",
        "history_count": len(history),
        "fingerprint": entry["fingerprint"]
    }


def create_fingerprint(profile: Dict[str, Any]) -> str:
    """
    Create fingerprint from creative profile.

    Args:
        profile: Creative profile

    Returns:
        Fingerprint string
    """
    pattern = profile.get("pattern", "")
    metaphor = profile.get("visual_metaphor", "")
    icon_system = profile.get("icon_system", "")
    shape = profile.get("shape_language", "")
    headline = profile.get("headline_pattern", "")

    return f"{pattern}+{metaphor}+{icon_system}+{shape}+{headline}"


def calculate_diversity_score(candidate: Dict[str, Any], history: List[Dict[str, Any]], window: int = 5) -> Dict[str, Any]:
    """
    Calculate diversity score for candidate vs. history.

    Args:
        candidate: Candidate creative profile
        history: User's history
        window: Number of recent profiles to check

    Returns:
        Diversity result dict
    """
    if not history:
        return {
            "diversity_score": 1.0,
            "repeated_elements": [],
            "recommendations": [],
            "history_count": 0
        }

    recent_history = history[-window:] if len(history) > window else history

    # Check repetitions
    repeated_elements = []
    recommendations = []

    # Pattern + metaphor combo
    candidate_combo = f"{candidate.get('pattern', '')}+{candidate.get('visual_metaphor', '')}"
    past_combos = [f"{h.get('pattern', '')}+{h.get('visual_metaphor', '')}" for h in recent_history]

    if candidate_combo in past_combos:
        repeated_elements.append("pattern+metaphor combo")
        recommendations.append("Use different visual metaphor")

    # Headline pattern
    candidate_headline = candidate.get("headline_pattern", "")
    past_headlines = [h.get("headline_pattern", "") for h in recent_history]

    headline_count = past_headlines.count(candidate_headline)
    if headline_count >= 2:
        repeated_elements.append("headline pattern (used 2+ times)")
        recommendations.append("Rotate to different headline pattern")

    # Icon system
    candidate_icons = candidate.get("icon_system", "")
    past_icons = [h.get("icon_system", "") for h in recent_history[-2:]]  # Check last 2

    if candidate_icons in past_icons:
        repeated_elements.append("icon system")
        recommendations.append("Vary icon system")

    # Shape language
    candidate_shape = candidate.get("shape_language", "")
    past_shapes = [h.get("shape_language", "") for h in recent_history[-3:]]  # Check last 3

    shape_count = past_shapes.count(candidate_shape)
    if shape_count >= 2:
        repeated_elements.append("shape language (used 2+ times)")
        recommendations.append("Try different shape language")

    # Calculate overall diversity score
    # Pattern+metaphor: 40%, headline: 30%, icons: 15%, shape: 15%
    pattern_metaphor_score = 0.0 if candidate_combo in past_combos else 1.0
    headline_score = max(0.0, 1.0 - (headline_count / len(recent_history)))
    icon_score = 0.0 if candidate_icons in past_icons else 1.0
    shape_score = max(0.0, 1.0 - (shape_count / len(recent_history)))

    diversity_score = (
        pattern_metaphor_score * 0.4 +
        headline_score * 0.3 +
        icon_score * 0.15 +
        shape_score * 0.15
    )

    return {
        "diversity_score": diversity_score,
        "repeated_elements": repeated_elements,
        "recommendations": recommendations,
        "history_count": len(history),
        "recent_window_size": len(recent_history),
        "breakdown": {
            "pattern_metaphor_score": pattern_metaphor_score,
            "headline_score": headline_score,
            "icon_score": icon_score,
            "shape_score": shape_score
        }
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python diversity-tracker.py <log|check> <user-id> <profile-json> [--window N]", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]
    user_id = sys.argv[2]

    if command == "log":
        if len(sys.argv) < 4:
            print("Usage: python diversity-tracker.py log <user-id> <creative-profile-json>", file=sys.stderr)
            sys.exit(1)

        profile_file = sys.argv[3]

        if not Path(profile_file).exists():
            print(json.dumps({
                "error": f"Profile file not found: {profile_file}"
            }))
            sys.exit(1)

        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)

            # Extract creative_profile if nested
            if "creative_profile" in profile_data:
                profile = profile_data["creative_profile"]
            else:
                profile = profile_data

            result = log_profile(user_id, profile)

            print(json.dumps(result, indent=2))

        except Exception as e:
            print(json.dumps({
                "error": str(e)
            }), file=sys.stderr)
            sys.exit(1)

    elif command == "check":
        if len(sys.argv) < 4:
            print("Usage: python diversity-tracker.py check <user-id> <candidate-profile-json> [--window N]", file=sys.stderr)
            sys.exit(1)

        profile_file = sys.argv[3]
        window = 5

        # Parse optional window
        if len(sys.argv) > 4 and sys.argv[4] == '--window':
            window = int(sys.argv[5]) if len(sys.argv) > 5 else window

        if not Path(profile_file).exists():
            print(json.dumps({
                "error": f"Profile file not found: {profile_file}"
            }))
            sys.exit(1)

        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)

            # Extract creative_profile if nested
            if "creative_profile" in profile_data:
                candidate = profile_data["creative_profile"]
            else:
                candidate = profile_data

            history = load_history(user_id)

            result = calculate_diversity_score(candidate, history, window)

            print(json.dumps(result, indent=2))

            # Warn if diversity score very low (but don't fail)
            if result["diversity_score"] < 0.3:
                print(f"WARNING: Low diversity score ({result['diversity_score']:.2f})", file=sys.stderr)

        except Exception as e:
            print(json.dumps({
                "error": str(e)
            }), file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Use 'log' or 'check'", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
