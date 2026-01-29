#!/usr/bin/env python3
"""
Slide HTML Generator

Generate styled HTML/CSS for each slide with proper design, contrast, and brand compliance.
Uses web fonts, Iconify web icons, and modern CSS for professional results.

Usage:
    python slide-html-generator.py slides.json --output-dir html/ --background bg.png

Output:
    HTML files (slide-1.html, slide-2.html, ...) with embedded CSS
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional


# Brand color system
BRAND_COLORS = {
    "primary": "#ff6b35",
    "navy": "#171d28",
    "electric_blue": "#0ea5e9",
    "electric_cyan": "#00d9ff",
    "text_primary": "#0f172a",
    "text_muted": "#64748b",
    "white": "#ffffff",
    "muted_bg": "#f1f5f9"
}


def get_text_color_for_background(bg_hex: str) -> str:
    """
    Get optimal text color using color-contrast-validator.py

    Args:
        bg_hex: Background color hex

    Returns:
        Text color hex (#ffffff or #000000)
    """
    try:
        result = subprocess.run(
            ['python3', 'color-contrast-validator.py', '--background', bg_hex],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('recommended_hex', '#ffffff')
        else:
            # Fallback: white for dark colors, black for light
            return '#ffffff' if bg_hex.lower() in ['#171d28', '#0f172a'] else '#000000'

    except Exception:
        # Fallback
        return '#ffffff'


def generate_hook_slide(slide: Dict[str, Any], background: Optional[str], output_path: Path) -> None:
    """Generate HTML for hook slide (opening slide)."""

    title = slide.get('title', '')
    subtitle = slide.get('content', '')
    icon = slide.get('icon', '').replace('lucide:', '')

    # Determine background style
    if background and Path(background).exists():
        bg_style = f"background: url('{background}') center/cover;"
        text_color = get_text_color_for_background(BRAND_COLORS['navy'])
    else:
        bg_style = f"background: linear-gradient(135deg, {BRAND_COLORS['navy']} 0%, {BRAND_COLORS['electric_blue']} 100%);"
        text_color = BRAND_COLORS['white']

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, height=1080">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@700;800&family=Inter:wght@400;500&display=swap" rel="stylesheet">
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    body {{
      width: 1080px;
      height: 1080px;
      {bg_style}
      font-family: 'Inter', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      color: {text_color};
      position: relative;
    }}
    .slide-content {{
      padding: 80px;
      max-width: 900px;
      text-align: center;
      z-index: 10;
    }}
    .icon {{
      font-size: 100px;
      margin-bottom: 40px;
      color: {BRAND_COLORS['primary']};
    }}
    h1 {{
      font-family: 'Poppins', sans-serif;
      font-size: 72px;
      font-weight: 800;
      line-height: 1.1;
      margin-bottom: 30px;
    }}
    .subtitle {{
      font-size: 40px;
      font-weight: 400;
      line-height: 1.4;
      opacity: 0.9;
    }}
    .logo-zone {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      width: 200px;
      height: 130px;
      /* Logo placeholder */
    }}
  </style>
  <script src="https://code.iconify.design/iconify-icon/3.0.0/iconify-icon.min.js"></script>
</head>
<body>
  <div class="slide-content">
    {f'<iconify-icon icon="lucide:{icon}" class="icon"></iconify-icon>' if icon else ''}
    <h1>{title}</h1>
    {f'<div class="subtitle">{subtitle}</div>' if subtitle else ''}
  </div>
  <div class="logo-zone"></div>
</body>
</html>"""

    output_path.write_text(html, encoding='utf-8')


def generate_framework_slide(slide: Dict[str, Any], background: Optional[str], output_path: Path) -> None:
    """Generate HTML for framework slide (core content with bullets)."""

    title = slide.get('title', '')
    content = slide.get('content', [])
    icon = slide.get('icon', '').replace('lucide:', '')

    if isinstance(content, str):
        content = [content]

    # Determine background and text colors
    if background and Path(background).exists():
        bg_style = f"background: url('{background}') center/cover;"
        text_color = get_text_color_for_background(BRAND_COLORS['navy'])
    else:
        bg_style = f"background: {BRAND_COLORS['white']};"
        text_color = BRAND_COLORS['text_primary']

    # Generate bullet HTML
    bullets_html = '\n'.join([
        f'<li><span class="bullet-title">{line}</span></li>'
        for line in content[:5]  # Max 5 bullets
    ])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, height=1080">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    body {{
      width: 1080px;
      height: 1080px;
      {bg_style}
      font-family: 'Inter', sans-serif;
      color: {text_color};
      padding: 80px;
      position: relative;
    }}
    .header {{
      display: flex;
      align-items: center;
      margin-bottom: 60px;
    }}
    .icon {{
      font-size: 80px;
      margin-right: 30px;
      color: {BRAND_COLORS['primary']};
    }}
    h1 {{
      font-family: 'Poppins', sans-serif;
      font-size: 56px;
      font-weight: 700;
      line-height: 1.2;
    }}
    ul {{
      list-style: none;
      margin-top: 40px;
    }}
    li {{
      margin-bottom: 40px;
      padding-left: 40px;
      position: relative;
    }}
    li::before {{
      content: '';
      position: absolute;
      left: 0;
      top: 12px;
      width: 12px;
      height: 12px;
      background: {BRAND_COLORS['electric_blue']};
      border-radius: 50%;
    }}
    .bullet-title {{
      font-size: 36px;
      font-weight: 500;
      line-height: 1.4;
    }}
    .logo-zone {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      width: 200px;
      height: 130px;
    }}
  </style>
  <script src="https://code.iconify.design/iconify-icon/3.0.0/iconify-icon.min.js"></script>
</head>
<body>
  <div class="header">
    {f'<iconify-icon icon="lucide:{icon}" class="icon"></iconify-icon>' if icon else ''}
    <h1>{title}</h1>
  </div>
  <ul>
    {bullets_html}
  </ul>
  <div class="logo-zone"></div>
</body>
</html>"""

    output_path.write_text(html, encoding='utf-8')


def generate_example_slide(slide: Dict[str, Any], background: Optional[str], output_path: Path) -> None:
    """Generate HTML for example slide (real-world story)."""

    title = slide.get('title', 'REAL EXAMPLE')
    content = slide.get('content', '')
    icon = slide.get('icon', '').replace('lucide:', '')

    bg_style = f"background: {BRAND_COLORS['muted_bg']};"
    text_color = BRAND_COLORS['text_primary']

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, height=1080">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    body {{
      width: 1080px;
      height: 1080px;
      {bg_style}
      font-family: 'Inter', sans-serif;
      color: {text_color};
      padding: 80px;
      position: relative;
    }}
    .label {{
      font-family: 'Poppins', sans-serif;
      font-size: 16px;
      font-weight: 600;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: {BRAND_COLORS['primary']};
      margin-bottom: 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    .icon {{
      font-size: 60px;
      color: {BRAND_COLORS['electric_blue']};
    }}
    .content {{
      font-size: 38px;
      line-height: 1.5;
      font-weight: 400;
    }}
    .logo-zone {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      width: 200px;
      height: 130px;
    }}
  </style>
  <script src="https://code.iconify.design/iconify-icon/3.0.0/iconify-icon.min.js"></script>
</head>
<body>
  <div class="label">
    <span>{title}</span>
    {f'<iconify-icon icon="lucide:{icon}" class="icon"></iconify-icon>' if icon else ''}
  </div>
  <div class="content">{content}</div>
  <div class="logo-zone"></div>
</body>
</html>"""

    output_path.write_text(html, encoding='utf-8')


def generate_diagnostic_slide(slide: Dict[str, Any], background: Optional[str], output_path: Path) -> None:
    """Generate HTML for diagnostic slide (key question/test)."""

    content = slide.get('content', '')

    bg_style = f"background: {BRAND_COLORS['navy']};"
    text_color = BRAND_COLORS['white']

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, height=1080">
  <title>Diagnostic</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&display=swap" rel="stylesheet">
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    body {{
      width: 1080px;
      height: 1080px;
      {bg_style}
      font-family: 'Poppins', sans-serif;
      color: {text_color};
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 100px;
      position: relative;
    }}
    .content {{
      font-size: 48px;
      font-weight: 600;
      line-height: 1.4;
      text-align: center;
    }}
    .logo-zone {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      width: 200px;
      height: 130px;
    }}
  </style>
</head>
<body>
  <div class="content">{content}</div>
  <div class="logo-zone"></div>
</body>
</html>"""

    output_path.write_text(html, encoding='utf-8')


def generate_cta_slide(slide: Dict[str, Any], background: Optional[str], output_path: Path) -> None:
    """Generate HTML for CTA slide (call-to-action)."""

    title = slide.get('title', '')
    content = slide.get('content', '')
    icon = slide.get('icon', '').replace('lucide:', '')

    bg_style = f"background: linear-gradient(135deg, {BRAND_COLORS['navy']} 0%, {BRAND_COLORS['electric_blue']} 100%);"
    text_color = BRAND_COLORS['white']

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=1080, height=1080">
  <title>Call to Action</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@500&display=swap" rel="stylesheet">
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}
    body {{
      width: 1080px;
      height: 1080px;
      {bg_style}
      font-family: 'Poppins', sans-serif;
      color: {text_color};
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 80px;
      position: relative;
    }}
    .slide-content {{
      text-align: center;
    }}
    .icon {{
      font-size: 80px;
      margin-bottom: 40px;
      color: {BRAND_COLORS['primary']};
    }}
    h1 {{
      font-size: 52px;
      font-weight: 600;
      line-height: 1.3;
      margin-bottom: 40px;
    }}
    .cta {{
      font-family: 'Inter', sans-serif;
      font-size: 40px;
      font-weight: 500;
      color: {BRAND_COLORS['primary']};
    }}
    .logo-zone {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      width: 200px;
      height: 130px;
    }}
  </style>
  <script src="https://code.iconify.design/iconify-icon/3.0.0/iconify-icon.min.js"></script>
</head>
<body>
  <div class="slide-content">
    {f'<iconify-icon icon="lucide:{icon}" class="icon"></iconify-icon>' if icon else ''}
    <h1>{title}</h1>
    <div class="cta">{content}</div>
  </div>
  <div class="logo-zone"></div>
</body>
</html>"""

    output_path.write_text(html, encoding='utf-8')


def generate_slides(slides_data: Dict[str, Any], output_dir: Path, background: Optional[str]) -> List[Path]:
    """
    Generate HTML files for all slides.

    Args:
        slides_data: Slides JSON data
        output_dir: Output directory for HTML files
        background: Optional background image path

    Returns:
        List of generated HTML file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    slides = slides_data.get('slides', [])
    generated_files = []

    for i, slide in enumerate(slides, start=1):
        slide_type = slide.get('type', 'hook')
        output_path = output_dir / f"slide-{i}.html"

        if slide_type == 'hook':
            generate_hook_slide(slide, background, output_path)
        elif slide_type == 'framework':
            generate_framework_slide(slide, background, output_path)
        elif slide_type == 'example':
            generate_example_slide(slide, background, output_path)
        elif slide_type == 'diagnostic':
            generate_diagnostic_slide(slide, background, output_path)
        elif slide_type == 'cta':
            generate_cta_slide(slide, background, output_path)
        else:
            # Default to framework layout
            generate_framework_slide(slide, background, output_path)

        generated_files.append(output_path)

    return generated_files


def main():
    if len(sys.argv) < 2:
        print("Usage: python slide-html-generator.py <slides.json> [--output-dir html/] [--background bg.png]", file=sys.stderr)
        sys.exit(1)

    slides_file = sys.argv[1]

    # Parse arguments
    output_dir = Path('html')
    background = None

    for i, arg in enumerate(sys.argv):
        if arg == '--output-dir' and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1])
        elif arg == '--background' and i + 1 < len(sys.argv):
            background = sys.argv[i + 1]

    # Validate slides file exists
    if not Path(slides_file).exists():
        print(json.dumps({
            'error': f"Slides file not found: {slides_file}"
        }))
        sys.exit(1)

    try:
        # Read slides data
        with open(slides_file, 'r', encoding='utf-8') as f:
            slides_data = json.load(f)

        # Generate HTML files
        generated_files = generate_slides(slides_data, output_dir, background)

        # Output summary
        result = {
            "generated_files": [str(f) for f in generated_files],
            "total_slides": len(generated_files),
            "output_directory": str(output_dir),
            "background_image": background if background else "None (gradient backgrounds)"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
