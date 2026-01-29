#!/usr/bin/env python3
"""
Link Validator

Validates all URLs in content (checks HTTP status codes).

Usage:
    python link-validator.py <content_file>

Output (JSON):
    {
      "total_links": 12,
      "valid": 11,
      "broken": [{...}],
      "redirects": [],
      "warnings": []
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict
import argparse
import urllib.request
import urllib.error
from urllib.parse import urlparse

def validate_url(url: str, timeout: int = 10) -> Dict:
    """
    Validate URL by checking HTTP status code.

    Args:
        url: URL to validate
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Dict with validation results
    """
    try:
        # Parse URL to ensure it's valid
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return {
                'url': url,
                'status': None,
                'valid': False,
                'error': 'Invalid URL format'
            }

        # Create request with User-Agent header to avoid blocks
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )

        # Use HEAD request when possible (faster)
        req.get_method = lambda: 'HEAD'

        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status

            # Check for redirects
            final_url = response.geturl()
            redirect = final_url if final_url != url else None

            return {
                'url': url,
                'status': status,
                'valid': status in [200, 201, 202, 203, 204],
                'error': None,
                'redirect': redirect
            }

    except urllib.error.HTTPError as e:
        return {
            'url': url,
            'status': e.code,
            'valid': False,
            'error': f'HTTP {e.code}: {e.reason}'
        }
    except urllib.error.URLError as e:
        return {
            'url': url,
            'status': None,
            'valid': False,
            'error': f'Connection error: {str(e.reason)}'
        }
    except Exception as e:
        return {
            'url': url,
            'status': None,
            'valid': False,
            'error': f'Validation error: {str(e)}'
        }


def extract_links(content: str) -> List[Dict]:
    """Extract all links from markdown content."""
    links = []

    # Markdown links: [text](url)
    markdown_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    for match in re.finditer(markdown_pattern, content):
        links.append({
            'text': match.group(1),
            'url': match.group(2),
            'type': 'markdown',
            'position': match.start()
        })

    return links


def main():
    parser = argparse.ArgumentParser(description='Validate links in content')
    parser.add_argument('content_file', help='Path to content file')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('--verbose', action='store_true', help='Show progress during validation')
    args = parser.parse_args()

    content_path = Path(args.content_file)

    if not content_path.exists():
        print(json.dumps({'error': f'File not found: {args.content_file}'}))
        sys.exit(1)

    try:
        with open(content_path, 'r', encoding='utf-8') as f:
            content = f.read()

        links = extract_links(content)

        if args.verbose:
            print(f"Found {len(links)} links to validate...", file=sys.stderr)

        results = []
        for i, link in enumerate(links):
            if args.verbose:
                print(f"[{i+1}/{len(links)}] Checking {link['url']}...", file=sys.stderr)
            result = validate_url(link['url'], timeout=args.timeout)
            results.append(result)

        valid_count = sum(1 for r in results if r['valid'])
        broken = [r for r in results if not r['valid']]
        redirects = [r for r in results if r.get('redirect')]

        # Extract line numbers for broken links
        for broken_link in broken:
            url = broken_link['url']
            # Find line number in content
            for i, line in enumerate(content.split('\n'), 1):
                if url in line:
                    broken_link['location'] = f'line {i}'
                    break

        output = {
            'total_links': len(links),
            'valid': valid_count,
            'broken': broken,
            'redirects': redirects,
            'warnings': []
        }

        print(json.dumps(output, indent=2))

        if args.verbose:
            print(f"\nValidation complete: {valid_count}/{len(links)} valid", file=sys.stderr)

        if broken:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({'error': str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
