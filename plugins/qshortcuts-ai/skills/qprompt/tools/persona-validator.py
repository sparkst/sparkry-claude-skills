#!/usr/bin/env python3
"""
Persona Validator - Check prompt alignment with persona patterns

Validates prompt consistency against persona traits, vocabulary, and tone.

Usage:
    python persona-validator.py --prompt prompt.txt --persona strategic_advisor

Output (JSON):
    {
      "persona": "strategic_advisor",
      "consistency_score": 82,
      "voice_analysis": {
        "traits_present": ["direct", "systems_thinking"],
        "traits_missing": ["proof_of_work"],
        "vocabulary_match": 0.85,
        "tone_alignment": 0.80
      },
      "flagged_issues": [
        {
          "issue": "Corporate jargon detected",
          "location": "line 42",
          "phrase": "leverage synergies",
          "fix": "Use concrete action verb instead"
        }
      ],
      "recommendations": [
        "Add proof-of-work example",
        "Replace 'leverage' with specific action"
      ]
    }
"""

import json
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, Any, List


# Anti-patterns (corporate jargon, hedging)
CORPORATE_JARGON = [
    "leverage synergies",
    "low-hanging fruit",
    "move the needle",
    "circle back",
    "touch base",
    "paradigm shift",
    "synergy",
    "value-add"
]

HEDGE_PHRASES = [
    "it might be argued that",
    "one could say",
    "perhaps",
    "possibly",
    "it seems that",
    "kind of",
    "sort of"
]


def load_persona_patterns(persona_name: str) -> Dict[str, Any]:
    """
    Load persona patterns.

    Stub implementation - returns default patterns.
    In production, would load from .claude/agents/ or persona/ directory.

    Returns:
        Dict with persona traits, vocabulary, tone
    """
    # Default strategic_advisor persona
    return {
        "traits": ["direct", "systems_thinking", "proof_of_work"],
        "vocabulary": ["scale", "leverage", "iterate", "systems", "second-order"],
        "tone": "analytical",
        "anti_patterns": {
            "jargon": CORPORATE_JARGON,
            "hedging": HEDGE_PHRASES
        }
    }


def analyze_traits(prompt_text: str, persona_patterns: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze trait presence in prompt.

    Returns:
        Dict with traits_present, traits_missing
    """
    traits = persona_patterns["traits"]

    # Stub implementation - simple keyword matching
    traits_present = []
    traits_missing = []

    for trait in traits:
        # Check if trait keywords are present
        if trait.lower() in prompt_text.lower():
            traits_present.append(trait)
        else:
            traits_missing.append(trait)

    return {
        "traits_present": traits_present,
        "traits_missing": traits_missing
    }


def analyze_vocabulary(prompt_text: str, persona_patterns: Dict[str, Any]) -> float:
    """
    Analyze vocabulary match.

    Returns:
        Vocabulary match score (0-1)
    """
    vocabulary = persona_patterns["vocabulary"]

    # Count vocabulary matches
    matches = 0
    for word in vocabulary:
        if word.lower() in prompt_text.lower():
            matches += 1

    # Calculate match ratio
    match_ratio = matches / len(vocabulary) if vocabulary else 0.0

    return round(match_ratio, 2)


def detect_anti_patterns(prompt_text: str, persona_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detect anti-patterns (jargon, hedging).

    Returns:
        List of flagged issues
    """
    issues = []
    lines = prompt_text.split('\n')

    # Check for corporate jargon
    for jargon in persona_patterns["anti_patterns"]["jargon"]:
        for i, line in enumerate(lines, 1):
            if jargon.lower() in line.lower():
                issues.append({
                    "issue": "Corporate jargon detected",
                    "location": f"line {i}",
                    "phrase": jargon,
                    "fix": "Use concrete action verb instead"
                })

    # Check for hedging
    for hedge in persona_patterns["anti_patterns"]["hedging"]:
        for i, line in enumerate(lines, 1):
            if hedge.lower() in line.lower():
                issues.append({
                    "issue": "Hedging language",
                    "location": f"line {i}",
                    "phrase": hedge,
                    "fix": "State directly"
                })

    return issues


def calculate_consistency_score(
    traits_analysis: Dict[str, Any],
    vocabulary_match: float,
    tone_alignment: float,
    issues_count: int
) -> int:
    """
    Calculate overall consistency score.

    Returns:
        Score (0-100)
    """
    # Weighted scoring
    trait_score = (len(traits_analysis["traits_present"]) /
                   (len(traits_analysis["traits_present"]) + len(traits_analysis["traits_missing"])))

    vocabulary_score = vocabulary_match
    tone_score = tone_alignment

    # Penalty for issues
    issue_penalty = min(issues_count * 5, 30)  # Max 30 point penalty

    # Calculate weighted average
    raw_score = (trait_score * 30 + vocabulary_score * 35 + tone_score * 35)
    final_score = max(0, raw_score - issue_penalty)

    return int(final_score)


def generate_recommendations(
    traits_analysis: Dict[str, Any],
    vocabulary_match: float,
    issues: List[Dict[str, Any]]
) -> List[str]:
    """
    Generate recommendations for improvement.

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Trait recommendations
    if traits_analysis["traits_missing"]:
        for trait in traits_analysis["traits_missing"]:
            recommendations.append(f"Add {trait} example or reference")

    # Vocabulary recommendations
    if vocabulary_match < 0.7:
        recommendations.append("Increase use of persona vocabulary")

    # Issue-specific recommendations
    for issue in issues:
        if issue["phrase"] not in [r["phrase"] for r in recommendations if isinstance(r, dict)]:
            recommendations.append(f"Replace '{issue['phrase']}' - {issue['fix']}")

    return recommendations[:5]  # Limit to top 5


def main():
    parser = argparse.ArgumentParser(description="Validate prompt against persona patterns")
    parser.add_argument("--prompt", required=True, help="Prompt file to validate")
    parser.add_argument("--persona", required=True, help="Persona name to validate against")

    args = parser.parse_args()

    try:
        # Read prompt
        prompt_path = Path(args.prompt)
        if not prompt_path.exists():
            print(json.dumps({"error": f"File not found: {args.prompt}"}), file=sys.stderr)
            sys.exit(1)

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_text = f.read()

        # Load persona patterns
        persona_patterns = load_persona_patterns(args.persona)

        # Analyze traits
        traits_analysis = analyze_traits(prompt_text, persona_patterns)

        # Analyze vocabulary
        vocabulary_match = analyze_vocabulary(prompt_text, persona_patterns)

        # Detect anti-patterns
        issues = detect_anti_patterns(prompt_text, persona_patterns)

        # Tone alignment (stub - would be more sophisticated in production)
        tone_alignment = 0.80

        # Calculate consistency score
        consistency_score = calculate_consistency_score(
            traits_analysis,
            vocabulary_match,
            tone_alignment,
            len(issues)
        )

        # Generate recommendations
        recommendations = generate_recommendations(
            traits_analysis,
            vocabulary_match,
            issues
        )

        # Build result
        result = {
            "persona": args.persona,
            "consistency_score": consistency_score,
            "voice_analysis": {
                **traits_analysis,
                "vocabulary_match": vocabulary_match,
                "tone_alignment": tone_alignment
            },
            "flagged_issues": issues,
            "recommendations": recommendations
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
