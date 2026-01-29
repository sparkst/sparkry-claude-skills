#!/usr/bin/env python3
"""
Color Contrast Validator

Calculate optimal text color based on background luminance using WCAG algorithms.
Prevents black-on-black or white-on-white text issues.

Usage:
    python color-contrast-validator.py --background "#171d28"

Output (JSON):
    {
      "background_rgb": [23, 29, 40],
      "background_luminance": 0.012,
      "recommended_text_color": "white",
      "contrast_ratio": 15.8,
      "wcag_aa": true,
      "wcag_aaa": true
    }
"""

import json
import sys
import re
from typing import Tuple, Dict, Any


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string (#RRGGBB or RRGGBB)

    Returns:
        RGB tuple (r, g, b)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_luminance(rgb: Tuple[int, int, int]) -> float:
    """
    Calculate relative luminance using WCAG formula.

    Args:
        rgb: RGB tuple (r, g, b)

    Returns:
        Relative luminance (0.0 - 1.0)
    """
    r, g, b = rgb

    # Convert to 0.0-1.0 range
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0

    # Apply gamma correction
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4

    # Calculate luminance
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def get_contrast_ratio(lum1: float, lum2: float) -> float:
    """
    Calculate contrast ratio between two luminance values.

    Args:
        lum1: First luminance value
        lum2: Second luminance value

    Returns:
        Contrast ratio (1.0 - 21.0)
    """
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def choose_text_color(background_rgb: Tuple[int, int, int]) -> Dict[str, Any]:
    """
    Choose optimal text color (white or black) based on background.

    Args:
        background_rgb: Background color RGB tuple

    Returns:
        Dict with recommended color and contrast details
    """
    bg_lum = get_luminance(background_rgb)
    white_lum = 1.0  # Pure white
    black_lum = 0.0  # Pure black

    white_contrast = get_contrast_ratio(white_lum, bg_lum)
    black_contrast = get_contrast_ratio(black_lum, bg_lum)

    # Choose color with better contrast
    if white_contrast > black_contrast:
        recommended_color = "white"
        recommended_hex = "#ffffff"
        contrast_ratio = white_contrast
    else:
        recommended_color = "black"
        recommended_hex = "#000000"
        contrast_ratio = black_contrast

    # WCAG compliance levels
    wcag_aa = contrast_ratio >= 4.5  # Normal text AA
    wcag_aaa = contrast_ratio >= 7.0  # Normal text AAA

    return {
        "background_rgb": list(background_rgb),
        "background_luminance": round(bg_lum, 3),
        "recommended_text_color": recommended_color,
        "recommended_hex": recommended_hex,
        "contrast_ratio": round(contrast_ratio, 1),
        "wcag_aa": wcag_aa,
        "wcag_aaa": wcag_aaa,
        "white_contrast": round(white_contrast, 1),
        "black_contrast": round(black_contrast, 1)
    }


def validate_custom_colors(background_hex: str, text_hex: str) -> Dict[str, Any]:
    """
    Validate contrast ratio between custom background and text colors.

    Args:
        background_hex: Background color hex
        text_hex: Text color hex

    Returns:
        Dict with validation results
    """
    bg_rgb = hex_to_rgb(background_hex)
    text_rgb = hex_to_rgb(text_hex)

    bg_lum = get_luminance(bg_rgb)
    text_lum = get_luminance(text_rgb)

    contrast_ratio = get_contrast_ratio(bg_lum, text_lum)

    wcag_aa = contrast_ratio >= 4.5
    wcag_aaa = contrast_ratio >= 7.0

    return {
        "background_hex": background_hex,
        "text_hex": text_hex,
        "contrast_ratio": round(contrast_ratio, 1),
        "wcag_aa": wcag_aa,
        "wcag_aaa": wcag_aaa,
        "valid": wcag_aa,
        "recommendation": "Use white text" if bg_lum < 0.5 else "Use black text" if not wcag_aa else "Current colors pass WCAG AA"
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python color-contrast-validator.py --background <hex> [--text <hex>]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  python color-contrast-validator.py --background \"#171d28\"", file=sys.stderr)
        print("  python color-contrast-validator.py --background \"#171d28\" --text \"#ffffff\"", file=sys.stderr)
        sys.exit(1)

    # Parse arguments
    background_hex = None
    text_hex = None

    for i, arg in enumerate(sys.argv):
        if arg == '--background' and i + 1 < len(sys.argv):
            background_hex = sys.argv[i + 1]
        elif arg == '--text' and i + 1 < len(sys.argv):
            text_hex = sys.argv[i + 1]

    if not background_hex:
        print(json.dumps({
            "error": "Background color required (--background <hex>)"
        }))
        sys.exit(1)

    try:
        if text_hex:
            # Validate custom color combination
            result = validate_custom_colors(background_hex, text_hex)
        else:
            # Recommend optimal text color
            background_rgb = hex_to_rgb(background_hex)
            result = choose_text_color(background_rgb)

        print(json.dumps(result, indent=2))

        # Exit with error code if contrast insufficient
        if not result.get('wcag_aa', result.get('valid', False)):
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
