#!/usr/bin/env python3
"""
Generate Hero Image

Create branded hero image from article title and subtitle.

Usage:
    python generate-hero-image.py --file content.md --output hero.png

Output (JSON):
    {
      "success": true,
      "visual_path": "hero.png",
      "title": "Article Title",
      "subtitle": "Key insight",
      "size": {"width": 1200, "height": 630}
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional
import argparse


def extract_article_metadata(content: str) -> Dict[str, str]:
    """
    Extract title and subtitle from markdown content.

    Args:
        content: Markdown article content

    Returns:
        Dict with title and subtitle
    """
    # Extract H1 title
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = h1_match.group(1).strip() if h1_match else "Untitled Article"

    # Extract first paragraph as subtitle
    lines = content.split('\n')
    subtitle = ""
    in_content = False
    for line in lines:
        line = line.strip()
        # Skip until after H1
        if line.startswith('# '):
            in_content = True
            continue
        # Skip metadata blocks and formatting
        if line.startswith('---') or line.startswith('**') or line.startswith('##'):
            continue
        # Collect first non-empty paragraph
        if in_content and line and not line.startswith('#'):
            subtitle = line
            break

    # Truncate subtitle if too long (for readability)
    if len(subtitle) > 150:
        subtitle = subtitle[:147] + "..."

    # Default subtitle if none found
    if not subtitle:
        subtitle = "Key insights and practical strategies"

    return {
        "title": title,
        "subtitle": subtitle
    }


def generate_html_for_hero(
    title: str,
    subtitle: str,
    style: str = "gradient",
    template_path: Optional[str] = None
) -> str:
    """
    Generate HTML for hero image.

    Args:
        title: Article title
        subtitle: Article subtitle/hook
        style: Visual style (bold, minimal, gradient)
        template_path: Optional custom template path

    Returns:
        HTML string with embedded CSS
    """
    # If template provided, load and substitute
    if template_path:
        path = Path(template_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                html = f.read()
                html = html.replace('{{ title }}', title)
                html = html.replace('{{ subtitle }}', subtitle)
                return html

    # Default: Generate inline HTML based on style
    if style == "bold":
        background = "background: #171d28;"  # Sparkry navy
    elif style == "minimal":
        background = "background: white;"
    else:  # gradient (default)
        background = "background: linear-gradient(135deg, #171d28 0%, #0ea5e9 100%);"

    # Text color (white for dark backgrounds, navy for light)
    text_color = "#ffffff" if style != "minimal" else "#171d28"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@700;800&family=Inter:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            width: 1200px;
            height: 630px;
            {background}
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: {text_color};
        }}
        .container {{
            max-width: 1000px;
            padding: 80px;
            text-align: left;
        }}
        .title {{
            font-family: 'Poppins', sans-serif;
            font-size: 64px;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 30px;
            letter-spacing: -0.02em;
        }}
        .subtitle {{
            font-family: 'Inter', sans-serif;
            font-size: 28px;
            font-weight: 400;
            line-height: 1.5;
            opacity: 0.95;
        }}
        .brand {{
            position: absolute;
            bottom: 30px;
            right: 40px;
            font-family: 'Poppins', sans-serif;
            font-size: 20px;
            font-weight: 600;
            color: #ff6b35;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="title">{title}</div>
        <div class="subtitle">{subtitle}</div>
    </div>
    <div class="brand">Sparkry.AI</div>
</body>
</html>"""

    return html


def generate_hero_image(
    file_path: str,
    output_path: Optional[str] = None,
    style: str = "gradient",
    width: int = 1200,
    height: int = 630,
    template_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate hero image from article.

    Args:
        file_path: Path to markdown article
        output_path: Output PNG path (auto-generated if None)
        style: Visual style (bold, minimal, gradient)
        width: Image width
        height: Image height
        template_path: Optional custom template path

    Returns:
        Dict with success status and output info
    """
    import time
    start_time = time.time()

    # Read article
    path = Path(file_path)
    if not path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}"
        }

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract metadata
        metadata = extract_article_metadata(content)
        title = metadata["title"]
        subtitle = metadata["subtitle"]

        # Auto-generate output path if not provided
        if not output_path:
            # Extract week and day from filename (e.g., W02-THU-article.md)
            filename = path.stem
            week_match = re.search(r'W(\d+)', filename)
            if week_match:
                week_num = week_match.group(1)
                output_dir = path.parent.parent / f"visuals/week-{week_num}"
            else:
                output_dir = path.parent / "visuals"

            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"{filename}-hero.png")

        # Generate HTML
        html = generate_html_for_hero(title, subtitle, style, template_path)

        # Write HTML to temp file
        temp_html = Path(output_path).parent / "_temp_hero.html"
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html)

        # Import render function from render-html-to-image.py
        # Get the tools directory
        tools_dir = Path(__file__).parent
        sys.path.insert(0, str(tools_dir))

        try:
            from render_html_to_image import render_html_to_image as render_fn
        except ImportError:
            # Fallback: call render-html-to-image.py as subprocess
            import subprocess
            render_cmd = [
                sys.executable,
                str(tools_dir / "render-html-to-image.py"),
                "--html-file", str(temp_html),
                "--output", output_path,
                "--width", str(width),
                "--height", str(height)
            ]
            result = subprocess.run(render_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                temp_html.unlink()
                return {
                    "success": False,
                    "error": f"Render failed: {result.stderr}"
                }
            render_result = json.loads(result.stdout)
            temp_html.unlink()

            render_time_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "visual_path": output_path,
                "title": title,
                "subtitle": subtitle,
                "size": {
                    "width": width,
                    "height": height
                },
                "render_time_ms": render_time_ms,
                "style": style
            }

        # Render HTML to PNG
        render_result = render_fn(
            html_file=str(temp_html),
            output_path=output_path,
            width=width,
            height=height
        )

        # Clean up temp HTML
        temp_html.unlink()

        if not render_result.get("success"):
            return render_result

        render_time_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "visual_path": output_path,
            "title": title,
            "subtitle": subtitle,
            "size": {
                "width": width,
                "height": height
            },
            "render_time_ms": render_time_ms,
            "style": style
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description='Generate hero image from article'
    )
    parser.add_argument('--file', required=True, help='Path to markdown article')
    parser.add_argument('--output', help='Output PNG path (auto-generated if not provided)')
    parser.add_argument('--style', choices=['bold', 'minimal', 'gradient'],
                       default='gradient', help='Visual style')
    parser.add_argument('--width', type=int, default=1200, help='Image width')
    parser.add_argument('--height', type=int, default=630, help='Image height')
    parser.add_argument('--template', help='Custom HTML template path')

    args = parser.parse_args()

    # Generate hero image
    result = generate_hero_image(
        file_path=args.file,
        output_path=args.output,
        style=args.style,
        width=args.width,
        height=args.height,
        template_path=args.template
    )

    # Output result
    print(json.dumps(result, indent=2))

    # Exit with error code if failed
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
