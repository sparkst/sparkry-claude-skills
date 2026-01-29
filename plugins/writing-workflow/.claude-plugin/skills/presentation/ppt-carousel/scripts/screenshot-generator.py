#!/usr/bin/env python3
"""
Screenshot Generator

Capture HTML slides as PNG images using Playwright for professional quality.

Usage:
    python screenshot-generator.py html/*.html --output-dir screenshots/

Output:
    PNG images (1080×1080) for each HTML slide
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import glob


def screenshot_slides(html_files: List[Path], output_dir: Path) -> List[Dict[str, Any]]:
    """
    Screenshot HTML slides using Playwright.

    Args:
        html_files: List of HTML file paths
        output_dir: Output directory for PNG files

    Returns:
        List of screenshot info dicts
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "Playwright not installed. Install with:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    screenshots = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1080, 'height': 1080})

        for html_file in sorted(html_files):
            # Extract slide number from filename (e.g., "slide-3.html" -> 3)
            import re
            match = re.search(r'slide-(\d+)', html_file.stem)
            slide_num = int(match.group(1)) if match else None

            if slide_num is None:
                # Fallback: use sequential numbering if no slide number in filename
                slide_num = len(screenshots) + 1

            # Navigate to HTML file
            file_url = f'file://{html_file.resolve()}'
            page.goto(file_url, wait_until='networkidle')

            # Wait for web fonts to load
            page.wait_for_timeout(1000)  # 1 second for font rendering

            # Screenshot
            output_file = output_dir / f"slide-{slide_num}.png"
            page.screenshot(path=str(output_file), full_page=False)

            screenshots.append({
                'slide_number': slide_num,
                'html_source': str(html_file),
                'png_output': str(output_file),
                'dimensions': '1080×1080',
                'size_bytes': output_file.stat().st_size
            })

        browser.close()

    return screenshots


def main():
    if len(sys.argv) < 2:
        print("Usage: python screenshot-generator.py <html-pattern> [--output-dir screenshots/]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python screenshot-generator.py html/*.html", file=sys.stderr)
        print("  python screenshot-generator.py html/slide-*.html --output-dir carousel/", file=sys.stderr)
        sys.exit(1)

    # Parse arguments
    output_dir = Path('screenshots')
    html_files = []

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--output-dir' and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1])
            i += 2
        elif arg == '--output':
            output_dir = Path(sys.argv[i + 1])
            i += 2
        else:
            # HTML file or pattern
            if '*' in arg:
                # Glob pattern
                html_files.extend([Path(f) for f in glob.glob(arg)])
            else:
                # Single file
                html_files.append(Path(arg))
            i += 1

    if not html_files:
        print(json.dumps({
            'error': f"No HTML files found"
        }))
        sys.exit(1)

    # Validate files exist
    html_files = [f for f in html_files if f.exists()]

    if not html_files:
        print(json.dumps({
            'error': f"HTML files not found: {html_pattern}"
        }))
        sys.exit(1)

    try:
        # Generate screenshots
        screenshots = screenshot_slides(html_files, output_dir)

        # Calculate total size
        total_size = sum(s['size_bytes'] for s in screenshots)

        # Output summary
        result = {
            "screenshots": screenshots,
            "total_slides": len(screenshots),
            "output_directory": str(output_dir),
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
