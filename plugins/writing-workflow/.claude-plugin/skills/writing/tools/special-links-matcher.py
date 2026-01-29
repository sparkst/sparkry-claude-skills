#!/usr/bin/env python3
"""
Special Links Matcher

Matches content to special_links and suggests natural insertions.

Usage:
    python special-links-matcher.py <content_file>
"""

import json
import sys
import re
from pathlib import Path


def fetch_special_links():
    """Fetch special_links (mock - would call webhook in production)."""
    return {
        'ai_tools': [
            {'name': 'Claude', 'url': 'https://claude.ai'},
            {'name': 'n8n', 'url': 'https://n8n.io'},
            {'name': 'Lovable', 'url': 'https://lovable.dev'}
        ],
        'books': [],
        'services': []
    }


def find_mentions(content: str, entity_name: str):
    """Find mentions of entity in content."""
    pattern = re.compile(r'\b' + re.escape(entity_name) + r'\b', re.IGNORECASE)
    return list(pattern.finditer(content))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('content_file')
    args = parser.parse_args()

    with open(args.content_file, 'r') as f:
        content = f.read()

    special_links = fetch_special_links()
    suggestions = []

    for category in special_links:
        for entity in special_links[category]:
            mentions = find_mentions(content, entity['name'])
            for mention in mentions:
                suggestions.append({
                    'entity': entity['name'],
                    'url': entity['url'],
                    'category': category,
                    'confidence': 0.9
                })

    print(json.dumps({'suggestions': suggestions, 'integrated_count': 0}, indent=2))


if __name__ == '__main__':
    import argparse
    main()
