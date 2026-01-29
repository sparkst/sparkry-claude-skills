#!/usr/bin/env python3
"""
Voice Validator

Checks voice consistency against persona patterns.

Usage:
    python voice-validator.py <content_file> --persona strategic

Output (JSON):
    {
      "consistency_score": 82,
      "persona": "strategic",
      "flagged_phrases": [...],
      "vocabulary_match": 85,
      "sentence_structure_match": 80,
      "recommendations": [...]
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
import argparse


# Persona-specific patterns
PERSONA_PATTERNS = {
    'strategic': {
        'avoid': {
            'corporate_speak': ['leverage', 'synergy', 'alignment', 'stakeholder', 'holistic', 'robust'],
            'hedging': ['might', 'could', 'possibly', 'one might argue', 'it seems that'],
            'ai_tells': ["it's important to note", 'in today\'s landscape', 'as discussed', 'comprehensive']
        },
        'prefer': {
            'sentence_length': 15,  # max words
            'paragraph_sentences': 4,  # max sentences
            'voice': 'active',
            'proof_of_work': True,  # Look for specific numbers and stories
        }
    },
    'hank_green': {
        'avoid': {
            'ai_tells': ["it's important to note", 'as discussed', 'delve into'],
            'condescension': ['obviously', 'clearly', 'simply put', 'just']
        },
        'prefer': {
            'direct_address': True,  # Use "you"
            'varied_sentences': True,
            'technical_with_context': True,
        }
    },
    'how_to': {
        'avoid': {
            'fluff': ['in conclusion', 'to summarize', 'basically', 'essentially'],
            'fabrication_markers': ['imagine', 'let\'s say', 'for example (fictional)']
        },
        'prefer': {
            'step_by_step': True,
            'no_bs': True,
            'real_examples': True
        }
    }
}


def check_avoided_phrases(content: str, persona: str) -> List[Dict[str, Any]]:
    """Check for phrases that should be avoided for this persona."""
    flagged = []

    avoid_patterns = PERSONA_PATTERNS.get(persona, {}).get('avoid', {})

    for category, phrases in avoid_patterns.items():
        for phrase in phrases:
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            matches = list(pattern.finditer(content))

            for match in matches:
                # Find paragraph number
                para_num = content[:match.start()].count('\n\n') + 1

                flagged.append({
                    'phrase': phrase,
                    'category': category,
                    'location': f'paragraph {para_num}',
                    'issue': f'{category.replace("_", " ").title()}: "{phrase}"',
                    'fix': get_fix_suggestion(phrase, category, persona)
                })

    return flagged


def get_fix_suggestion(phrase: str, category: str, persona: str) -> str:
    """Get specific fix suggestion for flagged phrase."""
    if category == 'corporate_speak':
        return f'Replace "{phrase}" with concrete action or specific term'
    elif category == 'hedging':
        return 'State directly without qualifier'
    elif category == 'ai_tells':
        return 'Remove or rephrase naturally'
    elif category == 'condescension':
        return 'Remove - trust reader intelligence'
    elif category == 'fluff':
        return 'Remove filler, get to the point'
    else:
        return f'Revise to match {persona} persona voice patterns'


def check_sentence_structure(content: str, persona: str) -> Dict[str, Any]:
    """Check sentence structure matches persona requirements."""
    sentences = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]

    if not sentences:
        return {'match': 0, 'issues': []}

    avg_length = sum(len(s.split()) for s in sentences) / len(sentences)

    issues = []

    if persona == 'strategic':
        target_length = PERSONA_PATTERNS['strategic']['prefer']['sentence_length']
        if avg_length > target_length:
            issues.append(f'Average sentence length {avg_length:.1f} words (target: ≤{target_length})')

        # Check for passive voice
        passive_count = sum(1 for s in sentences if ' was ' in s or ' were ' in s)
        if passive_count > len(sentences) * 0.1:
            issues.append(f'Passive voice in {passive_count} sentences')

    elif persona == 'hank_green':
        # Check for sentence variety
        lengths = [len(s.split()) for s in sentences]
        has_short = any(l < 10 for l in lengths)
        has_long = any(l > 25 for l in lengths)

        if not (has_short and has_long):
            issues.append('Add sentence variety (mix short and long)')

        # Check for direct address ("you")
        you_count = sum(1 for s in sentences if 'you' in s.lower())
        if you_count < len(sentences) * 0.2:
            issues.append('Add more direct address ("you")')

    # Calculate match score
    match_score = 100 - (len(issues) * 10)
    match_score = max(0, match_score)

    return {
        'match': match_score,
        'issues': issues,
        'avg_sentence_length': avg_length
    }


def check_vocabulary_match(content: str, persona: str) -> Dict[str, Any]:
    """Check if vocabulary matches persona patterns."""
    issues = []

    if persona == 'strategic':
        # Check for proof-of-work (specific numbers)
        specific_numbers = len(re.findall(r'\d+[KMB]|→|\d+%|\d{4}', content))

        if specific_numbers < 3:
            issues.append('Add specific numbers/data (proof-of-work pattern)')

        # Check for physical analogies (common in strategic voice)
        analogy_markers = ['like a', 'similar to', 'imagine a', 'think of']
        has_analogy = any(marker in content.lower() for marker in analogy_markers)

        if not has_analogy and len(content) > 500:
            issues.append('Consider adding physical analogy')

    elif persona == 'hank_green':
        # Check for technical terms with context
        technical_terms = re.findall(r'\b[A-Z]{2,}\b|\b\w+tion\b', content)

        if technical_terms:
            # Good - but check they have context (appear in sentences with simpler words)
            pass

    # Calculate match score
    match_score = 100 - (len(issues) * 15)
    match_score = max(0, match_score)

    return {
        'match': match_score,
        'issues': issues
    }


def calculate_consistency_score(flagged_phrases: List, sentence_match: Dict, vocabulary_match: Dict) -> int:
    """Calculate overall voice consistency score."""
    # Start at 100, deduct for issues
    score = 100

    # Deduct for flagged phrases
    score -= len(flagged_phrases) * 3

    # Weight sentence structure
    score = (score * 0.4) + (sentence_match['match'] * 0.3) + (vocabulary_match['match'] * 0.3)

    return max(0, min(100, int(score)))


def validate_voice(content: str, persona: str = 'strategic') -> Dict[str, Any]:
    """
    Validate voice consistency against persona.

    Args:
        content: Content to validate
        persona: Persona to check against

    Returns:
        Dict with consistency score and recommendations
    """
    flagged_phrases = check_avoided_phrases(content, persona)
    sentence_structure = check_sentence_structure(content, persona)
    vocabulary = check_vocabulary_match(content, persona)

    consistency_score = calculate_consistency_score(
        flagged_phrases,
        sentence_structure,
        vocabulary
    )

    # Compile recommendations
    recommendations = []

    for flagged in flagged_phrases[:5]:  # Top 5 most critical
        recommendations.append(flagged['fix'])

    recommendations.extend(sentence_structure['issues'])
    recommendations.extend(vocabulary['issues'])

    return {
        'consistency_score': consistency_score,
        'persona': persona,
        'flagged_phrases': flagged_phrases,
        'sentence_structure_match': sentence_structure['match'],
        'vocabulary_match': vocabulary['match'],
        'recommendations': recommendations[:10]  # Top 10
    }


def main():
    parser = argparse.ArgumentParser(description='Validate voice consistency')
    parser.add_argument('content_file', help='Path to content file')
    parser.add_argument('--persona', default='strategic',
                       choices=['strategic', 'hank_green', 'how_to'],
                       help='Persona to validate against')

    args = parser.parse_args()

    content_path = Path(args.content_file)

    if not content_path.exists():
        print(json.dumps({
            'error': f'File not found: {args.content_file}'
        }))
        sys.exit(1)

    try:
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = validate_voice(content, persona=args.persona)

        print(json.dumps(result, indent=2))

        # Exit with error if consistency below threshold
        if result['consistency_score'] < 80:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
