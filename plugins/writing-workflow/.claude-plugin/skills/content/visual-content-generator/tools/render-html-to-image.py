#!/usr/bin/env python3
"""
Render HTML to Image

Core rendering engine that converts HTML templates to PNG images using Playwright.

Usage:
    python render-html-to-image.py --html-file template.html --output image.png --width 1200 --height 630

Output (JSON):
    {
      "success": true,
      "output_path": "image.png",
      "render_time_ms": 342,
      "size": {"width": 1200, "height": 630}
    }
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional
import argparse


def render_html_to_image(
    html_file: str,
    output_path: str,
    width: int = 1200,
    height: int = 630,
    scale: float = 2.0,
    variables: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Render HTML file to PNG image using Playwright.

    Args:
        html_file: Path to HTML template file
        output_path: Output PNG file path
        width: Viewport width in pixels
        height: Viewport height in pixels
        scale: DPI scale factor (2.0 = retina)
        variables: Template variables for substitution

    Returns:
        Dict with success status, output path, render time, and size
    """
    start_time = time.time()

    # Validate inputs
    html_path = Path(html_file).resolve()
    if not html_path.exists():
        return {
            "success": False,
            "error": f"HTML file not found: {html_file}"
        }

    output_file = Path(output_path).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load HTML content
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Apply template variable substitution if provided
    if variables:
        for key, value in variables.items():
            html_content = html_content.replace(f'{{{{ {key} }}}}', value)

    # Write processed HTML to temp file
    temp_html = output_file.parent / f"_temp_{output_file.stem}.html"
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    try:
        # Import Playwright (lazy import to avoid import errors)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "success": False,
                "error": "Playwright not installed. Run: pip install playwright && playwright install chromium"
            }

        # Render HTML to PNG
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={'width': width, 'height': height},
                device_scale_factor=scale
            )

            # Load HTML file
            page.goto(f'file://{temp_html}')

            # Wait for fonts and assets to load
            page.wait_for_timeout(1000)  # 1 second

            # Take screenshot
            page.screenshot(path=str(output_file), full_page=False)

            browser.close()

        # Clean up temp file
        temp_html.unlink()

        render_time_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "output_path": str(output_file),
            "render_time_ms": render_time_ms,
            "size": {
                "width": width,
                "height": height
            },
            "scale": scale
        }

    except Exception as e:
        # Clean up temp file on error
        if temp_html.exists():
            temp_html.unlink()

        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description='Render HTML template to PNG image using Playwright'
    )
    parser.add_argument('--html-file', required=True, help='Path to HTML template file')
    parser.add_argument('--output', required=True, help='Output PNG file path')
    parser.add_argument('--width', type=int, default=1200, help='Viewport width (default: 1200)')
    parser.add_argument('--height', type=int, default=630, help='Viewport height (default: 630)')
    parser.add_argument('--scale', type=float, default=2.0, help='DPI scale factor (default: 2.0)')
    parser.add_argument('--variables', type=str, help='Template variables as JSON string')

    args = parser.parse_args()

    # Parse variables if provided
    variables = None
    if args.variables:
        try:
            variables = json.loads(args.variables)
        except json.JSONDecodeError as e:
            print(json.dumps({
                "success": False,
                "error": f"Invalid JSON for variables: {e}"
            }), file=sys.stderr)
            sys.exit(1)

    # Render HTML to image
    result = render_html_to_image(
        html_file=args.html_file,
        output_path=args.output,
        width=args.width,
        height=args.height,
        scale=args.scale,
        variables=variables
    )

    # Output result
    print(json.dumps(result, indent=2))

    # Exit with error code if failed
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
