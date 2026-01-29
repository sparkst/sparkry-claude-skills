#!/usr/bin/env python3
"""
Template Selector

Selects appropriate template based on content type.

Usage:
    python template-selector.py --type substack-educational
"""

import json
import sys
import argparse

TEMPLATES = {
    'substack-educational': {
        'template': 'substack-educational',
        'path': 'references/templates/substack-educational.md',
        'structure': {
            'sections': ['Personal hook', 'Clear thesis', 'Core explanation', 'Application', 'Hope-based close'],
            'length_target': '800-2000 words',
            'persona': 'hank_green'
        }
    },
    'substack-strategic': {
        'template': 'substack-strategic',
        'path': 'references/templates/substack-strategic.md',
        'structure': {
            'sections': ['Reality validation', 'What broke', 'Pattern', 'Stress test + upside'],
            'length_target': '1000-2000 words',
            'persona': 'strategic'
        }
    },
    'linkedin-post': {
        'template': 'linkedin-post',
        'path': 'references/templates/linkedin-post.md',
        'structure': {
            'sections': ['Hook (25 words)', 'Key insights', 'Takeaway', 'CTA'],
            'length_target': '150-300 words',
            'persona': 'strategic'
        }
    }
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', required=True, help='Content type')
    args = parser.parse_args()

    template = TEMPLATES.get(args.type)

    if not template:
        print(json.dumps({'error': f'Unknown template type: {args.type}'}))
        sys.exit(1)

    print(json.dumps(template, indent=2))


if __name__ == '__main__':
    main()
