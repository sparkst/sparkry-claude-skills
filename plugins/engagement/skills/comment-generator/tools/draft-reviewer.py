#!/usr/bin/env python3
"""
Draft Reviewer - Score and validate comment drafts.

Usage:
    python draft-reviewer.py <draft-id>
    python draft-reviewer.py --all
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

OUTBOX_DIR = Path('./content/n8n/outbox')

# AI-tell phrases to detect
AI_TELLS = [
    "this really resonated",
    "great article",
    "in my experience",
    "i love how you",
    "thanks for sharing",
    "you make such a great point",
    "this is so true",
    "couldn't agree more",
    "well said",
    "spot on",
    "love this",
    "this hits home",
    "so relatable",
    "nailed it",
    "great post",
    "awesome article",
    "brilliant insight",
]

# Human-tell signals to reward
HUMAN_TELLS = [
    r'\$\d+',           # Dollar amounts
    r'\d+%',            # Percentages
    r'\d+ (weeks?|months?|years?|days?|hours?)',  # Timeframes
    r'still (figuring|working|learning)',  # Vulnerability
    r'we (tried|failed|struggled)',  # Honest failures
    r'(honestly|actually|specifically)',  # Authenticity markers
]


def load_job(job_file: str) -> Dict[str, Any] | None:
    """Load a job by filename."""
    filepath = OUTBOX_DIR / job_file
    if not filepath.exists():
        # Try with .json extension
        filepath = OUTBOX_DIR / f"{job_file}.json"
        if not filepath.exists():
            return None
    with open(filepath, 'r') as f:
        return json.load(f)


def check_ai_tells(text: str) -> List[str]:
    """Check for AI-tell phrases."""
    text_lower = text.lower()
    found = []
    for phrase in AI_TELLS:
        if phrase in text_lower:
            found.append(phrase)
    return found


def check_human_tells(text: str) -> int:
    """Count human-tell signals."""
    import re
    count = 0
    for pattern in HUMAN_TELLS:
        if re.search(pattern, text, re.IGNORECASE):
            count += 1
    return count


def score_specificity(text: str) -> int:
    """Score specificity (0-100)."""
    import re
    score = 50  # Base score

    # Numbers increase specificity
    numbers = re.findall(r'\d+', text)
    score += min(len(numbers) * 10, 30)

    # Quotes increase specificity
    quotes = re.findall(r'"[^"]+"', text)
    score += min(len(quotes) * 10, 20)

    # Names/proper nouns (capitalized words not at start)
    words = text.split()
    proper_nouns = [w for w in words[1:] if w[0].isupper() and len(w) > 2]
    score += min(len(proper_nouns) * 5, 15)

    return min(score, 100)


def score_authenticity(text: str) -> int:
    """Score authenticity (0-100)."""
    score = 70  # Base score

    # Penalize AI tells
    ai_tells = check_ai_tells(text)
    score -= len(ai_tells) * 20

    # Reward human tells
    human_tells = check_human_tells(text)
    score += human_tells * 10

    return max(0, min(score, 100))


def score_value_add(text: str, approach: str) -> int:
    """Score value-add based on approach (0-100)."""
    word_count = len(text.split())

    if approach == 'minimalist':
        # Minimalist should be short but punchy
        if 15 <= word_count <= 50:
            return 80
        elif word_count < 15:
            return 60
        else:
            return 50
    elif approach == 'question-first':
        # Should contain a question
        if '?' in text:
            return 85
        else:
            return 50
    elif approach == 'experience-matcher':
        # Should have story elements
        has_numbers = bool(check_human_tells(text))
        has_outcome = any(word in text.lower() for word in ['result', 'outcome', 'learned', 'worked', 'failed'])
        score = 50
        if has_numbers:
            score += 25
        if has_outcome:
            score += 25
        return score
    else:
        return 70  # Default


def check_length(text: str, target: Dict[str, int]) -> bool:
    """Check if text is within word count target."""
    word_count = len(text.split())
    return target['min'] <= word_count <= target['max']


def review_job(job: Dict[str, Any]) -> Dict[str, Any]:
    """Review a single comment job."""
    comment = job.get('comment', '')
    gen_context = job.get('generation_context', {})
    approach = gen_context.get('approach', 'unknown')
    target = gen_context.get('word_count_target', {'min': 50, 'max': 150})

    if not comment:
        return {
            'status': 'no_comment',
            'message': 'Draft has no generated comment yet'
        }

    # Score the comment
    specificity = score_specificity(comment)
    authenticity = score_authenticity(comment)
    value_add = score_value_add(comment, approach)
    ai_tells = check_ai_tells(comment)
    length_ok = check_length(comment, target)

    # Calculate overall score
    overall = (specificity + authenticity + value_add) / 3

    # Determine issues
    issues = []
    if ai_tells:
        issues.append(f"AI-tell phrases detected: {', '.join(ai_tells)}")
    if not length_ok:
        word_count = len(comment.split())
        issues.append(f"Word count {word_count} outside target {target['min']}-{target['max']}")
    if specificity < 60:
        issues.append("Low specificity - add concrete details")
    if authenticity < 70:
        issues.append("Low authenticity - sounds generic")

    # Recommendation
    if overall >= 80 and not ai_tells and length_ok:
        recommendation = 'approve'
    elif overall >= 60:
        recommendation = 'needs_edit'
    else:
        recommendation = 'reject'

    return {
        'scores': {
            'specificity': specificity,
            'authenticity': authenticity,
            'value_add': value_add,
            'overall': round(overall),
            'phrase_check': 100 if not ai_tells else 0,
            'length_check': length_ok
        },
        'ai_tells_found': ai_tells,
        'human_tells_count': check_human_tells(comment),
        'word_count': len(comment.split()),
        'issues': issues,
        'recommendation': recommendation
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python draft-reviewer.py <job-file>")
        print("       python draft-reviewer.py --all")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--all':
        # Review all draft comment jobs
        if not OUTBOX_DIR.exists():
            print(json.dumps({'error': 'No outbox directory'}))
            sys.exit(1)

        results = []
        for filepath in OUTBOX_DIR.glob('*.json'):
            job = json.load(open(filepath))
            # Only review substack_comment jobs with draft status
            if (job.get('job_metadata', {}).get('type') == 'substack_comment' and
                job.get('status') == 'draft'):
                review = review_job(job)
                gen_context = job.get('generation_context', {})
                results.append({
                    'job_id': job.get('job_metadata', {}).get('id', 'unknown'),
                    'filename': filepath.name,
                    'article': job.get('title', '')[:50],
                    'approach': gen_context.get('approach', 'unknown'),
                    **review
                })

        print(json.dumps(results, indent=2))
    else:
        # Review single job
        job = load_job(arg)
        if not job:
            print(json.dumps({'error': f'Job not found: {arg}'}))
            sys.exit(1)

        review = review_job(job)
        print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
