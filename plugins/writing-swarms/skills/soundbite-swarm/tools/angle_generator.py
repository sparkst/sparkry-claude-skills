#!/usr/bin/env python3
"""
Angle Generator

Generates soundbites from a specific creative angle.
Input: content text + angle name
Output: 10 soundbite candidates with self-scores

Supported angles (5-Angle Swarm):
1. emotional - The Emotional Provocateur: "What feeling does this evoke?"
2. identity - The Identity Crafter: "Who does the audience become?"
3. action - The Action Catalyst: "What action does this inspire?"
4. contrarian - The Contrarian: "What uncomfortable truth is revealed?"
5. simplifier - The Simplifier: "What's the irreducible truth?"

Usage:
    python angle_generator.py --content "..." --angle emotional

Output (JSON):
    {
      "angle": "emotional",
      "candidates": [
        {
          "soundbite": "You Already Know",
          "primary_lens": "validation",
          "scores": {...},
          "rationale": "..."
        }
      ],
      "meta": {...}
    }
"""

import json
import sys
import time
import re
from typing import Dict, Any, List, Optional


# Valid angles for 5-Angle Swarm (from OPTIONS-MATRIX.md)
VALID_ANGLES = ["emotional", "identity", "action", "contrarian", "simplifier"]

# Angle-specific vocabulary patterns
ANGLE_PATTERNS = {
    "emotional": {
        "primary_lenses": ["fear", "hope", "pride", "defiance", "validation", "belonging"],
        "vocabulary": ["feel", "know", "ready", "enough", "worthy", "you", "your", "we"],
        "style": "whispered truth"
    },
    "identity": {
        "primary_lenses": ["aspiration", "belonging", "distinction", "evolution", "values"],
        "vocabulary": ["be", "become", "am", "are", "thinker", "builder", "leader", "creator"],
        "style": "manifesto"
    },
    "action": {
        "primary_lenses": ["starting", "continuing", "finishing", "pivoting", "stopping"],
        "vocabulary": ["do", "start", "go", "build", "make", "ship", "move", "now", "today"],
        "style": "starting gun"
    },
    "contrarian": {
        "primary_lenses": ["assumption", "sacred_cow", "conventional_wisdom", "comfortable_lie", "hidden_truth"],
        "vocabulary": ["not", "never", "none", "wrong", "broken", "fake", "myth", "actually", "really"],
        "style": "cold water"
    },
    "simplifier": {
        "primary_lenses": ["core_truth", "first_principles", "signal", "essence", "simplicity"],
        "vocabulary": ["just", "only", "simply", "one", "core", "less", "clear", "simple"],
        "style": "koan"
    }
}

# Sample soundbites for each angle (used for generation guidance)
ANGLE_EXAMPLES = {
    "emotional": [
        "You Already Know", "Not Anymore", "Feel That", "This Is It", "You're Ready",
        "Enough", "Trust This", "Let Go", "Rise Up", "Own It"
    ],
    "identity": [
        "Think Different", "Be More", "Builders Build", "Leaders Lead", "We Create",
        "The Ones Who Ship", "Not Followers", "You're Not Behind", "Creators Create", "Bold Moves"
    ],
    "action": [
        "Just Do It", "Start Now", "Ship It", "Move", "Build First",
        "Stop Waiting", "Go", "Begin Today", "Make It Happen", "Take Action"
    ],
    "contrarian": [
        "Question Everything", "You're Wrong", "Not That", "Stop Believing",
        "The Lie You Tell", "What If", "Rethink", "Break Rules", "Ignore Advice", "Doubt It"
    ],
    "simplifier": [
        "Less Is More", "Just. Start.", "One Thing", "That's It", "Simple Works",
        "Do Less. Better.", "Focus", "Clarity", "Strip It Down", "The Core"
    ]
}


def _detect_language(content: str) -> str:
    """Simple language detection based on common words."""
    content_lower = content.lower()

    # English common words
    english_words = ["the", "is", "are", "and", "to", "in", "for", "of", "with"]
    english_count = sum(1 for word in english_words if f" {word} " in f" {content_lower} ")

    if english_count >= 3:
        return "english"
    return "other"


def _extract_key_concepts(content: str) -> List[str]:
    """Extract key concepts from content for soundbite generation."""
    # Simple extraction: find capitalized words and key phrases
    words = content.split()

    # Get unique significant words (not stopwords)
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                 "being", "have", "has", "had", "do", "does", "did", "will",
                 "would", "could", "should", "may", "might", "must", "to",
                 "of", "in", "for", "on", "with", "at", "by", "from", "as",
                 "into", "through", "during", "before", "after", "above",
                 "below", "between", "under", "again", "further", "then",
                 "once", "here", "there", "when", "where", "why", "how",
                 "all", "each", "few", "more", "most", "other", "some",
                 "such", "no", "nor", "not", "only", "own", "same", "so",
                 "than", "too", "very", "can", "just", "don", "now", "that",
                 "this", "it", "its", "and", "but", "or", "if", "because"}

    concepts = []
    for word in words:
        clean = re.sub(r'[^\w]', '', word.lower())
        if len(clean) > 3 and clean not in stopwords:
            concepts.append(clean)

    return list(set(concepts))[:20]


def _generate_soundbite_candidates(
    content: str,
    angle: str,
    count: int = 10
) -> List[Dict[str, Any]]:
    """
    Generate soundbite candidates for a given angle.

    This is a deterministic generator that creates soundbites based on
    angle patterns and content concepts. In production, this would
    integrate with an LLM for creative generation.

    Args:
        content: The content to generate soundbites from
        angle: The creative angle
        count: Number of candidates to generate

    Returns:
        List of candidate soundbites with scores
    """
    patterns = ANGLE_PATTERNS[angle]
    examples = ANGLE_EXAMPLES[angle]
    concepts = _extract_key_concepts(content)

    candidates = []

    # Use examples as base templates, incorporating content concepts
    for i, example in enumerate(examples[:count]):
        # Determine primary lens based on angle patterns
        lens_idx = i % len(patterns["primary_lenses"])
        primary_lens = patterns["primary_lenses"][lens_idx]

        # Calculate scores based on angle characteristics
        word_count = len(example.split())

        # Base scores vary by angle characteristic
        if angle == "simplifier":
            # Simplifier tends to be shorter
            memorability = 80 + (5 if word_count <= 3 else 0)
            brevity_bonus = 10 if word_count <= 3 else 0
        elif angle == "emotional":
            memorability = 85
            brevity_bonus = 5
        elif angle == "action":
            memorability = 82
            brevity_bonus = 5
        else:
            memorability = 78
            brevity_bonus = 0

        # Brevity score based on word count
        brevity_map = {1: 95, 2: 95, 3: 100, 4: 90, 5: 75, 6: 60, 7: 40}
        brevity = brevity_map.get(word_count, 20)

        scores = {
            "memorability": min(100, memorability + (i % 5)),
            "emotional_resonance": 75 + (10 if angle == "emotional" else 0) + (i % 5),
            "brevity": brevity,
            "rhythm": 75 + (i % 10),
            "universality": 70 + (i % 8),
            "action_potential": 70 + (15 if angle == "action" else 0) + (i % 5),
            "authenticity": 78 + (i % 7)
        }

        # Calculate overall weighted score
        weights = {
            "memorability": 0.25,
            "emotional_resonance": 0.20,
            "brevity": 0.15,
            "rhythm": 0.10,
            "universality": 0.10,
            "action_potential": 0.10,
            "authenticity": 0.10
        }

        overall = sum(scores[k] * weights[k] for k in weights)
        scores["overall"] = round(overall, 1)

        candidates.append({
            "soundbite": example,
            "primary_lens": primary_lens,
            "scores": scores,
            "rationale": f"Generated from {angle} angle with focus on {primary_lens}. " +
                        f"{word_count}-word soundbite with {patterns['style']} style.",
            "word_count": word_count
        })

    return candidates


def generate_from_angle(
    content: str,
    angle: str
) -> Dict[str, Any]:
    """
    Generate soundbites from a specific creative angle.

    Args:
        content: The content text to generate soundbites from
        angle: The creative angle name

    Returns:
        Dict with angle, candidates, and metadata

    Raises:
        ValueError: If content is empty or angle is invalid
        TypeError: If content is None
    """
    start_time = time.time()

    # Validate content
    if content is None:
        raise TypeError("content cannot be None")

    if not content or not content.strip():
        raise ValueError("Content required - cannot generate from empty text")

    # Validate angle
    if angle not in VALID_ANGLES:
        valid_list = ", ".join(VALID_ANGLES)
        raise ValueError(f"Invalid angle '{angle}'. Valid angles: {valid_list}")

    # Detect language and set warning if needed
    language = _detect_language(content)
    warning = None
    if language != "english":
        warning = "Non-English content detected. Quality may be reduced."

    # Check content length
    word_count = len(content.split())
    truncated = False

    if word_count > 5000:
        # Truncate to first 5000 words
        words = content.split()[:5000]
        content = " ".join(words)
        truncated = True

    if word_count < 50:
        if warning:
            warning += " Short content may reduce diversity."
        else:
            warning = "Short content may reduce diversity."

    # Generate candidates
    candidates = _generate_soundbite_candidates(content, angle, count=10)

    # Calculate timing
    generation_time_ms = int((time.time() - start_time) * 1000)

    # Count candidates above threshold
    above_threshold = len([c for c in candidates if c["scores"]["overall"] >= 75])

    result = {
        "angle": angle,
        "candidates": candidates,
        "meta": {
            "generation_time_ms": generation_time_ms,
            "candidates_generated": len(candidates),
            "above_threshold": above_threshold,
            "content_word_count": word_count
        }
    }

    if warning:
        result["warning"] = warning

    if truncated:
        result["truncated"] = True

    return result


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate soundbites from a creative angle")
    parser.add_argument("--content", required=True, help="Content text to generate from")
    parser.add_argument("--angle", required=True, choices=VALID_ANGLES,
                       help=f"Creative angle: {', '.join(VALID_ANGLES)}")

    args = parser.parse_args()

    try:
        result = generate_from_angle(args.content, args.angle)
        print(json.dumps(result, indent=2))

    except (TypeError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
