#!/usr/bin/env python3
"""
Platform Constraints Validator

Validates platform-specific requirements.

Usage:
    python platform-constraints.py <content_file> --platform linkedin
"""

import json
import sys
import argparse
from pathlib import Path

PLATFORM_CONSTRAINTS = {
    'linkedin': {
        'hook_max_words': 25,
        'article_length': (1900, 2000),
        'post_length': (150, 300)
    },
    'twitter': {
        'max_chars': 280,
        'optimal_chars': (40, 80)
    },
    'instagram': {
        'length_words': (125, 200),
        'hashtags': (3, 5)
    },
    'substack': {
        'length_words': (800, 3000)
    }
}


def validate_platform(content: str, platform: str):
    """Validate content against platform constraints."""
    constraints = PLATFORM_CONSTRAINTS.get(platform, {})
    violations = []

    word_count = len(content.split())
    char_count = len(content)

    if platform == 'linkedin' and 'hook_max_words' in constraints:
        first_para = content.split('\n\n')[0]
        hook_words = len(first_para.split())
        if hook_words > constraints['hook_max_words']:
            violations.append({
                'constraint': 'hook_length',
                'expected': f"≤{constraints['hook_max_words']} words",
                'actual': f'{hook_words} words',
                'priority': 'P0'
            })

    return {
        'platform': platform,
        'valid': len(violations) == 0,
        'violations': violations,
        'metrics': {'word_count': word_count, 'char_count': char_count}
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('content_file')
    parser.add_argument('--platform', required=True)
    args = parser.parse_args()

    with open(args.content_file, 'r') as f:
        content = f.read()

    result = validate_platform(content, args.platform)
    print(json.dumps(result, indent=2))

    if not result['valid']:
        sys.exit(1)


if __name__ == '__main__':
    main()
