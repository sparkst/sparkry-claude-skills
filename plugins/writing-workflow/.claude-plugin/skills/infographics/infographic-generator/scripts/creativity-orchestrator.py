#!/usr/bin/env python3
"""
Creativity Orchestrator

Generates creative profile with visual metaphor, icon system, shape language.
Ensures diversity by tracking past infographics to avoid repetition.

Usage:
    python creativity-orchestrator.py <framework-json> <strategy-json> \\
      --brand-colors "#1a1a2e,#0f3460" --user-id "user_123"

Output (JSON):
    {
      "creative_profile": {
        "visual_metaphor": "mountain_climb",
        "icon_system": "flat_duotone",
        "shape_language": "pill_steps",
        "divider_style": "rail_with_numbered_nodes",
        "accent_motif": "corner_brackets",
        "headline_pattern": "[FRAMEWORK_NAME]: [N] Steps",
        "novelty_score": 0.78
      }
    }
"""

import json
import sys
import random
from pathlib import Path
from typing import List, Dict, Any


# Load visual metaphors reference
VISUAL_METAPHORS = {
    "steps": ["roadmap", "ladder", "mountain_climb", "assembly_line", "staircase"],
    "pillars": ["columns", "control_panel", "foundation_blocks", "support_beams"],
    "layers": ["stacked_blocks", "pyramid", "elevation_chart", "tiered_cake"],
    "principles": ["compass", "core_values", "guideposts", "foundation_stones"],
    "stages": ["timeline_path", "evolution_chart", "growth_stages", "maturity_model"],
    "loops": ["orbit_model", "loop_track", "circular_flow", "feedback_cycle"]
}

ICON_SYSTEMS = [
    "flat_duotone",
    "outline",
    "filled_circle_nodes",
    "solid_bold",
    "line_minimal"
]

SHAPE_LANGUAGES = [
    "rounded_cards",
    "sharp_rectangles",
    "pill_steps",
    "nodes_and_connectors",
    "organic_blobs"
]

DIVIDER_STYLES = [
    "dotted_line",
    "rail_with_numbered_nodes",
    "stepped_progress_bar",
    "gradient_wave",
    "simple_line"
]

ACCENT_MOTIFS = [
    "subtle_dots",
    "grid_background",
    "corner_brackets",
    "side_rail",
    "geometric_pattern"
]

HEADLINE_PATTERNS = [
    "[FRAMEWORK_NAME]: [OUTCOME]",
    "Your [TOPIC] Stack: [N] [ELEMENTS]",
    "How to Move From [STATE_A] to [STATE_B] in [N] Moves",
    "[N] [ELEMENTS] Every [AUDIENCE] Needs",
    "The [N] [ELEMENTS] of [TOPIC]"
]


def load_user_history(user_id: str, window: int = 5) -> List[Dict[str, Any]]:
    """
    Load user's past creative profiles for diversity checking.

    Args:
        user_id: User identifier
        window: Number of past profiles to load

    Returns:
        List of past creative profiles
    """
    history_file = Path.home() / ".claude" / "data" / "infographic-history" / f"{user_id}.json"

    if not history_file.exists():
        return []

    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        return history[-window:] if len(history) > window else history
    except Exception:
        return []


def calculate_novelty_score(profile: Dict[str, Any], history: List[Dict[str, Any]]) -> float:
    """
    Calculate novelty score vs. past profiles (0-1, higher = more novel).

    Args:
        profile: Candidate creative profile
        history: List of past profiles

    Returns:
        Novelty score (0-1)
    """
    if not history:
        return 1.0

    # Check uniqueness of key elements
    pattern_metaphor_combo = f"{profile.get('pattern', '')}+{profile['visual_metaphor']}"
    past_combos = [f"{h.get('pattern', '')}+{h.get('visual_metaphor', '')}" for h in history]

    pattern_metaphor_uniqueness = 0.0 if pattern_metaphor_combo in past_combos else 1.0

    # Check headline pattern repetition
    headline = profile['headline_pattern']
    past_headlines = [h.get('headline_pattern', '') for h in history]
    headline_uniqueness = 1.0 - (past_headlines.count(headline) / len(history))

    # Check icon system repetition
    icon_system = profile['icon_system']
    past_icons = [h.get('icon_system', '') for h in history]
    icon_uniqueness = 1.0 - (past_icons.count(icon_system) / len(history))

    # Check shape language repetition
    shape = profile['shape_language']
    past_shapes = [h.get('shape_language', '') for h in history]
    shape_uniqueness = 1.0 - (past_shapes.count(shape) / len(history))

    # Weighted combination
    novelty_score = (
        pattern_metaphor_uniqueness * 0.4 +
        headline_uniqueness * 0.3 +
        icon_uniqueness * 0.15 +
        shape_uniqueness * 0.15
    )

    return novelty_score


def generate_creative_profile(
    framework: Dict[str, Any],
    strategy: Dict[str, Any],
    brand_colors: List[str],
    user_id: str,
    history_window: int = 5
) -> Dict[str, Any]:
    """
    Generate creative profile with diversity checking.

    Args:
        framework: Validated framework
        strategy: Infographic strategy
        brand_colors: List of hex color codes
        user_id: User identifier
        history_window: Number of past profiles to check

    Returns:
        Creative profile dict
    """
    framework_type = framework["type"]
    pattern = strategy["pattern"]

    # Load user history
    history = load_user_history(user_id, history_window)

    # Get past metaphors to avoid
    past_metaphors = [h.get('visual_metaphor', '') for h in history[-3:]]  # Check last 3

    # Select visual metaphor
    possible_metaphors = VISUAL_METAPHORS.get(framework_type, ["dashboard"])
    available_metaphors = [m for m in possible_metaphors if m not in past_metaphors]

    if not available_metaphors:
        # All used recently, pick randomly
        visual_metaphor = random.choice(possible_metaphors)
    else:
        visual_metaphor = random.choice(available_metaphors)

    # Select other elements (vary from recent history)
    past_icon_systems = [h.get('icon_system', '') for h in history[-2:]]
    available_icon_systems = [i for i in ICON_SYSTEMS if i not in past_icon_systems]
    icon_system = random.choice(available_icon_systems if available_icon_systems else ICON_SYSTEMS)

    past_shapes = [h.get('shape_language', '') for h in history[-2:]]
    available_shapes = [s for s in SHAPE_LANGUAGES if s not in past_shapes]
    shape_language = random.choice(available_shapes if available_shapes else SHAPE_LANGUAGES)

    divider_style = random.choice(DIVIDER_STYLES)
    accent_motif = random.choice(ACCENT_MOTIFS)

    # Select headline pattern (avoid last 2)
    past_patterns = [h.get('headline_pattern', '') for h in history[-2:]]
    available_patterns = [p for p in HEADLINE_PATTERNS if p not in past_patterns]
    headline_pattern = random.choice(available_patterns if available_patterns else HEADLINE_PATTERNS)

    # Build profile
    profile = {
        "visual_metaphor": visual_metaphor,
        "icon_system": icon_system,
        "shape_language": shape_language,
        "divider_style": divider_style,
        "accent_motif": accent_motif,
        "headline_pattern": headline_pattern,
        "pattern": pattern  # Include for novelty calculation
    }

    # Calculate novelty score
    novelty_score = calculate_novelty_score(profile, history)

    return {
        "creative_profile": profile,
        "novelty_score": novelty_score,
        "diversity_notes": f"Avoided {len(past_metaphors)} recent metaphors, {len(past_patterns)} recent headline patterns",
        "past_profiles_checked": len(history),
        "brand_constraints": ["primary_color_override"] if brand_colors else []
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python creativity-orchestrator.py <framework-json> <strategy-json> [--brand-colors COLORS] [--user-id ID]", file=sys.stderr)
        sys.exit(1)

    framework_file = sys.argv[1]
    strategy_file = sys.argv[2]

    brand_colors = []
    user_id = "default_user"

    # Parse optional arguments
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--brand-colors' and i + 1 < len(sys.argv):
            brand_colors = sys.argv[i + 1].split(',')
            i += 2
        elif sys.argv[i] == '--user-id' and i + 1 < len(sys.argv):
            user_id = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not Path(framework_file).exists():
        print(json.dumps({
            "error": f"Framework file not found: {framework_file}"
        }))
        sys.exit(1)

    if not Path(strategy_file).exists():
        print(json.dumps({
            "error": f"Strategy file not found: {strategy_file}"
        }))
        sys.exit(1)

    try:
        # Load framework
        with open(framework_file, 'r', encoding='utf-8') as f:
            framework_data = json.load(f)
        framework = framework_data.get("framework_validated") or framework_data.get("framework")

        # Load strategy
        with open(strategy_file, 'r', encoding='utf-8') as f:
            strategy = json.load(f)

        # Generate creative profile
        result = generate_creative_profile(framework, strategy, brand_colors, user_id)

        print(json.dumps(result, indent=2))

        # Warn if novelty score too low (but don't fail)
        if result["novelty_score"] < 0.3:
            print(f"WARNING: Low novelty score ({result['novelty_score']:.2f}). Consider forcing new metaphor.", file=sys.stderr)

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
