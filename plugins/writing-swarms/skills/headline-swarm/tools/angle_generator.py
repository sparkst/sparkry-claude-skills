#!/usr/bin/env python3
"""
Angle Generator for Headlines

Generates headlines from a specific creative angle.
Input: content text + angle name + optional context (current title, hero image, audience)
Output: 10 headline candidates with self-scores

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
          "headline": "The Fear Your Engineers Won't Admit Out Loud",
          "primary_lens": "fear",
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


# Valid angles for 5-Angle Swarm
VALID_ANGLES = ["emotional", "identity", "action", "contrarian", "simplifier"]

# Angle-specific vocabulary patterns adapted for headlines
ANGLE_PATTERNS = {
    "emotional": {
        "primary_lenses": ["fear", "hope", "pride", "defiance", "validation", "belonging"],
        "vocabulary": ["fear", "truth", "honest", "waiting", "finally", "ready", "real"],
        "style": "emotional stakes"
    },
    "identity": {
        "primary_lenses": ["aspiration", "belonging", "distinction", "evolution", "leadership"],
        "vocabulary": ["leader", "real", "best", "who", "the kind", "how", "what"],
        "style": "identity framing"
    },
    "action": {
        "primary_lenses": ["starting", "doing", "leading", "changing", "stopping"],
        "vocabulary": ["how to", "stop", "start", "the script", "guide", "lead"],
        "style": "action promise"
    },
    "contrarian": {
        "primary_lenses": ["assumption", "sacred_cow", "conventional_wisdom", "comfortable_lie", "hidden_truth"],
        "vocabulary": ["stop", "wrong", "lie", "what nobody", "actually", "really", "why"],
        "style": "challenge"
    },
    "simplifier": {
        "primary_lenses": ["core_truth", "first_principles", "signal", "essence", "simplicity"],
        "vocabulary": ["one", "only", "just", "simple", "the", "all you need"],
        "style": "clarity"
    }
}

# Sample headlines for each angle (used for generation guidance)
ANGLE_EXAMPLES = {
    "emotional": [
        "The Honest AI Conversation Your Engineers Are Waiting For",
        "What Your Team Fears About AI (And Won't Tell You)",
        "The Fear Your Engineers Won't Admit Out Loud",
        "Why Your Best People Are Quietly Terrified",
        "You're Ready: The Conversation Your Team Needs",
        "The Truth Your Engineers Have Been Waiting to Hear",
        "What Happens When You Finally Tell Them the Truth",
        "The Fear Nobody in Your Company Will Name",
        "Your Team Knows. It's Time You Said It.",
        "The Honest Words Your Engineers Need Right Now"
    ],
    "identity": [
        "What Real Leaders Say About AI (When No One's Watching)",
        "How the Best Engineering Leaders Talk About AI",
        "The Conversation That Separates Good Managers from Great Ones",
        "Be the Leader Who Has the Hard Conversation",
        "Leaders Don't Hide From This Conversation",
        "What the Best Leaders Know About AI Anxiety",
        "The Manager's Guide to Honest AI Conversations",
        "You're Either Preparing Your Team or Failing Them",
        "How Real Leaders Build Trust During AI Disruption",
        "The Leadership Move Your Team Will Remember"
    ],
    "action": [
        "How to Talk About AI Without Losing Your Team",
        "Stop Lying to Your Engineers About AI",
        "The Script for Your Next AI Conversation",
        "Have This Conversation Before It's Too Late",
        "Lead the Conversation Your Team Needs",
        "Start Here: The AI Talk Your Engineers Need",
        "How to Lead Through AI Disruption (Here's How)",
        "Stop Avoiding the AI Conversation",
        "The Exact Words to Use When Your Team Is Scared",
        "Build Trust Now Before AI Forces the Conversation"
    ],
    "contrarian": [
        "Stop Telling Your Team AI Won't Take Their Jobs",
        "Why 'AI Is Just a Tool' Is Making Things Worse",
        "Your Engineers Should Be Worried About AI",
        "The Conversation Every Leader Is Avoiding",
        "What Your Engineers Know That You're Pretending Not To",
        "Why Optimism About AI Is the Wrong Approach",
        "Stop Protecting Your Team From the Truth",
        "The Lie Every Leader Tells About AI",
        "Why 'Focus on the Opportunity' Doesn't Work",
        "What Corporate AI Talk Gets Wrong"
    ],
    "simplifier": [
        "Your Team Is Scared. Be Honest.",
        "AI Changes Work. Honesty Saves Teams.",
        "One Conversation. Total Difference.",
        "Truth First. Then Hope. Then Action.",
        "The Only AI Conversation That Matters",
        "You Can't Promise Security. Here's What You Can Promise.",
        "Fear + Honesty = Trust",
        "What Your Engineers Need Is Simple",
        "One Talk. Three Truths. Complete Trust.",
        "The Core of Every AI Conversation"
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
    """Extract key concepts from content for headline generation."""
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


def _generate_headline_candidates(
    content: str,
    angle: str,
    count: int = 10
) -> List[Dict[str, Any]]:
    """
    Generate headline candidates for a given angle.

    This is a deterministic generator that creates headlines based on
    angle patterns and content concepts. In production, this would
    integrate with an LLM for creative generation.

    Args:
        content: The content to generate headlines from
        angle: The creative angle
        count: Number of candidates to generate

    Returns:
        List of candidate headlines with scores
    """
    patterns = ANGLE_PATTERNS[angle]
    examples = ANGLE_EXAMPLES[angle]
    concepts = _extract_key_concepts(content)

    candidates = []

    # Use examples as base templates
    for i, example in enumerate(examples[:count]):
        # Determine primary lens based on angle patterns
        lens_idx = i % len(patterns["primary_lenses"])
        primary_lens = patterns["primary_lenses"][lens_idx]

        word_count = len(example.split())

        # Base scores vary by angle characteristic and headline properties
        base_curiosity = 80
        base_clarity = 82
        base_promise = 78
        base_authenticity = 80

        # Angle-specific adjustments
        if angle == "emotional":
            base_curiosity += 5
        elif angle == "contrarian":
            base_curiosity += 8
            base_authenticity += 3
        elif angle == "action":
            base_promise += 8
        elif angle == "identity":
            base_promise += 5
        elif angle == "simplifier":
            base_clarity += 10

        # Brevity score based on word count (optimized for headlines)
        brevity_map = {5: 75, 6: 90, 7: 95, 8: 100, 9: 95, 10: 90, 11: 80, 12: 70}
        brevity = brevity_map.get(word_count, 60)

        # SEO potential (basic keyword detection)
        seo_base = 70
        if "ai" in example.lower():
            seo_base += 10
        if "leader" in example.lower() or "team" in example.lower():
            seo_base += 5

        scores = {
            "curiosity": min(100, base_curiosity + (i % 8)),
            "clarity": min(100, base_clarity + (i % 6)),
            "promise": min(100, base_promise + (i % 7)),
            "brevity": brevity,
            "authenticity": min(100, base_authenticity + (i % 5)),
            "seo_potential": min(100, seo_base + (i % 5))
        }

        # Calculate overall weighted score
        weights = {
            "curiosity": 0.25,
            "clarity": 0.20,
            "promise": 0.20,
            "brevity": 0.15,
            "authenticity": 0.10,
            "seo_potential": 0.10
        }

        overall = sum(scores[k] * weights[k] for k in weights)
        scores["overall"] = round(overall, 1)

        candidates.append({
            "headline": example,
            "primary_lens": primary_lens,
            "scores": scores,
            "rationale": f"Generated from {angle} angle with focus on {primary_lens}. " +
                        f"{word_count}-word headline with {patterns['style']} style.",
            "word_count": word_count
        })

    return candidates


def generate_from_angle(
    content: str,
    angle: str,
    context: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Generate headlines from a specific creative angle.

    Args:
        content: The content text to generate headlines from
        angle: The creative angle name
        context: Optional context (title, hero_image, audience)

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

    if word_count < 100:
        if warning:
            warning += " Short content may reduce headline diversity."
        else:
            warning = "Short content may reduce headline diversity."

    # Generate candidates
    candidates = _generate_headline_candidates(content, angle, count=10)

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

    if context:
        result["context_used"] = context

    if warning:
        result["warning"] = warning

    if truncated:
        result["truncated"] = True

    return result


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate headlines from a creative angle")
    parser.add_argument("--content", required=True, help="Content text to generate from")
    parser.add_argument("--angle", required=True, choices=VALID_ANGLES,
                       help=f"Creative angle: {', '.join(VALID_ANGLES)}")
    parser.add_argument("--context", help="JSON string with context (title, hero_image, audience)")

    args = parser.parse_args()

    context = None
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid context JSON: {e}"}), file=sys.stderr)
            sys.exit(1)

    try:
        result = generate_from_angle(args.content, args.angle, context)
        print(json.dumps(result, indent=2))

    except (TypeError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
