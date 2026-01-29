#!/usr/bin/env python3
"""
Icon Fetcher

Download and cache icons from Lucide/Iconify libraries.
Converts SVG to PNG with specified color and size.

Usage:
    python icon-fetcher.py lucide:users-2 --color ff6b35 --size 100

Output (JSON):
    {
      "icon": "lucide:users-2",
      "path": "cache/icons/lucide-users-2-ff6b35-100.png",
      "cached": true,
      "size": 100,
      "color": "#ff6b35"
    }
"""

import json
import sys
import hashlib
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from io import BytesIO

try:
    from PIL import Image, ImageDraw
except ImportError:
    print(json.dumps({
        'error': 'Pillow library not installed. Run: pip install Pillow'
    }), file=sys.stderr)
    sys.exit(1)


# Icon API endpoints
ICONIFY_API = 'https://api.iconify.design'

# Cache directory (relative to script)
SCRIPT_DIR = Path(__file__).parent.parent
CACHE_DIR = SCRIPT_DIR / 'cache' / 'icons'


def parse_icon_identifier(icon: str) -> Dict[str, str]:
    """
    Parse icon identifier into library and name.

    Args:
        icon: Icon identifier (e.g., "lucide:users-2")

    Returns:
        Dict with 'library' and 'name'
    """
    if ':' not in icon:
        return {'library': 'lucide', 'name': icon}

    parts = icon.split(':', 1)
    return {'library': parts[0], 'name': parts[1]}


def generate_cache_key(icon: str, color: str, size: int) -> str:
    """
    Generate cache key for icon.

    Args:
        icon: Icon identifier
        color: Hex color (without #)
        size: Icon size in pixels

    Returns:
        Cache key string
    """
    parsed = parse_icon_identifier(icon)
    return f"{parsed['library']}-{parsed['name']}-{color}-{size}.png"


def get_cached_icon(cache_key: str) -> Optional[Path]:
    """
    Retrieve icon from cache if exists.

    Args:
        cache_key: Cache key

    Returns:
        Path to cached icon or None
    """
    cache_path = CACHE_DIR / cache_key

    if cache_path.exists():
        return cache_path

    return None


def download_svg(icon: str) -> Optional[str]:
    """
    Download SVG from Iconify API.

    Args:
        icon: Icon identifier

    Returns:
        SVG content as string or None
    """
    parsed = parse_icon_identifier(icon)
    library = parsed['library']
    name = parsed['name']

    url = f"{ICONIFY_API}/{library}/{name}.svg"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(json.dumps({
            'error': f"Failed to download icon: {e}"
        }), file=sys.stderr)
        return None


def svg_to_png(svg_content: str, color: str, size: int) -> Optional[bytes]:
    """
    Convert SVG to PNG with specified color and size.

    Args:
        svg_content: SVG XML content
        color: Hex color (without #)
        size: Output size in pixels

    Returns:
        PNG bytes or None
    """
    try:
        # Use cairosvg if available for better SVG rendering
        try:
            import cairosvg

            # Replace color in SVG
            svg_content = svg_content.replace('currentColor', f'#{color}')

            png_bytes = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=size,
                output_height=size
            )

            return png_bytes

        except ImportError:
            # Fallback: Create simple colored square (placeholder)
            # For production, cairosvg should be installed
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Parse hex color
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)

            # Draw simple circle as placeholder
            margin = int(size * 0.2)
            draw.ellipse(
                [margin, margin, size - margin, size - margin],
                fill=(r, g, b, 255)
            )

            # Save to bytes
            output = BytesIO()
            img.save(output, format='PNG')
            return output.getvalue()

    except Exception as e:
        print(json.dumps({
            'error': f"Failed to convert SVG to PNG: {e}"
        }), file=sys.stderr)
        return None


def cache_icon(icon_data: bytes, cache_key: str) -> Path:
    """
    Save icon to cache.

    Args:
        icon_data: PNG bytes
        cache_key: Cache key

    Returns:
        Path to cached icon
    """
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_path = CACHE_DIR / cache_key

    with open(cache_path, 'wb') as f:
        f.write(icon_data)

    return cache_path


def fetch_icon(icon: str, color: str = 'ff6b35', size: int = 100) -> Dict[str, Any]:
    """
    Fetch icon from cache or download.

    Args:
        icon: Icon identifier
        color: Hex color (without #)
        size: Icon size in pixels

    Returns:
        Dict with icon path, cached status, etc.
    """
    # Generate cache key
    cache_key = generate_cache_key(icon, color, size)

    # Check cache
    cached_path = get_cached_icon(cache_key)

    if cached_path:
        return {
            'icon': icon,
            'path': str(cached_path),
            'cached': True,
            'size': size,
            'color': f'#{color}'
        }

    # Download SVG
    svg_content = download_svg(icon)

    if not svg_content:
        return {
            'error': f"Failed to download icon: {icon}"
        }

    # Convert to PNG
    png_bytes = svg_to_png(svg_content, color, size)

    if not png_bytes:
        return {
            'error': f"Failed to convert icon to PNG: {icon}"
        }

    # Cache icon
    cache_path = cache_icon(png_bytes, cache_key)

    return {
        'icon': icon,
        'path': str(cache_path),
        'cached': False,
        'size': size,
        'color': f'#{color}'
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python icon-fetcher.py <icon> [--color HEX] [--size N]", file=sys.stderr)
        print("Example: python icon-fetcher.py lucide:users-2 --color ff6b35 --size 100", file=sys.stderr)
        sys.exit(1)

    icon = sys.argv[1]

    # Parse arguments
    color = 'ff6b35'  # Default: Sparkry orange
    size = 100

    for i, arg in enumerate(sys.argv):
        if arg == '--color' and i + 1 < len(sys.argv):
            color = sys.argv[i + 1].lstrip('#')
        elif arg == '--size' and i + 1 < len(sys.argv):
            size = int(sys.argv[i + 1])

    try:
        # Fetch icon
        result = fetch_icon(icon, color, size)

        # Output JSON
        print(json.dumps(result, indent=2))

        # Exit with error code if failed
        if 'error' in result:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
