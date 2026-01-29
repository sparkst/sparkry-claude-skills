#!/usr/bin/env python3
"""
Convert ASCII to Visual

Transform ASCII art diagrams into professional visuals.

Usage:
    python convert-ascii-to-visual.py --ascii-input "ASCII content" --output diagram.png --title "Framework"

Output (JSON):
    {
      "success": true,
      "visual_path": "diagram.png",
      "detected_type": "flowchart",
      "nodes": 4,
      "connections": 3
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
import argparse


def parse_ascii_structure(ascii_content: str) -> Dict[str, Any]:
    """
    Parse ASCII diagram structure.

    Args:
        ascii_content: ASCII art string

    Returns:
        Dict with detected elements (boxes, arrows, text)
    """
    lines = ascii_content.split('\n')

    boxes = []
    arrows = []
    text_blocks = []

    # Detect boxes with box-drawing characters
    box_patterns = [
        r'┌([─]+)┐',  # Top border
        r'\+([─\-]+)\+',  # ASCII top border
    ]

    for i, line in enumerate(lines):
        # Detect box tops
        for pattern in box_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                width = len(match.group(1))
                # Look for box content and bottom
                content = []
                j = i + 1
                while j < len(lines):
                    if '│' in lines[j] or '|' in lines[j]:
                        # Extract text between borders
                        text_match = re.search(r'[│\|]\s*(.+?)\s*[│\|]', lines[j])
                        if text_match:
                            content.append(text_match.group(1).strip())
                        j += 1
                    elif '└' in lines[j] or '+' in lines[j]:
                        # Box bottom found
                        boxes.append({
                            "line": i,
                            "column": match.start(),
                            "width": width,
                            "content": content,
                            "height": j - i + 1
                        })
                        break
                    else:
                        break

        # Detect arrows
        arrow_symbols = ['→', '←', '↑', '↓', '▼', '▲', '►', '◄', '⇒', '⇐']
        for symbol in arrow_symbols:
            if symbol in line:
                arrows.append({
                    "line": i,
                    "symbol": symbol,
                    "direction": get_arrow_direction(symbol)
                })

    # Determine diagram type
    diagram_type = "flowchart"
    if len(boxes) >= 3 and len(arrows) >= 2:
        diagram_type = "flowchart"
    elif '├' in ascii_content or '└' in ascii_content:
        diagram_type = "tree"
    elif len(boxes) >= 3 and not arrows:
        diagram_type = "framework"

    return {
        "type": diagram_type,
        "boxes": boxes,
        "arrows": arrows,
        "box_count": len(boxes),
        "arrow_count": len(arrows)
    }


def get_arrow_direction(symbol: str) -> str:
    """Get arrow direction from symbol."""
    directions = {
        '→': 'right', '⇒': 'right', '►': 'right',
        '←': 'left', '⇐': 'left', '◄': 'left',
        '↑': 'up', '▲': 'up',
        '↓': 'down', '▼': 'down'
    }
    return directions.get(symbol, 'right')


def generate_html_for_diagram(
    ascii_content: str,
    structure: Dict[str, Any],
    title: str = "",
    style: str = "framework"
) -> str:
    """
    Generate HTML/CSS for diagram visualization.

    Args:
        ascii_content: Original ASCII content
        structure: Parsed structure from parse_ascii_structure
        title: Diagram title
        style: Visualization style

    Returns:
        HTML string with embedded CSS
    """
    # Sparkry brand colors
    colors = {
        "navy": "#171d28",
        "orange": "#ff6b35",
        "blue": "#0ea5e9",
        "white": "#ffffff",
        "gray": "#6b7280",
        "light_gray": "#f3f4f6"
    }

    # Generate simplified HTML representation
    # For MVP, we'll render a styled version of the ASCII with better typography
    # Future: More sophisticated HTML generation based on structure

    boxes = structure.get("boxes", [])
    diagram_type = structure.get("type", "framework")

    # If we have parsed boxes, generate structured HTML
    if boxes:
        box_html = ""
        for i, box in enumerate(boxes):
            content_lines = "<br>".join(box["content"]) if box["content"] else "Node"
            box_html += f"""
            <div class="diagram-box">
                <div class="box-content">{content_lines}</div>
            </div>
            """
            if i < len(boxes) - 1:
                box_html += '<div class="arrow">↓</div>'

        diagram_html = f'<div class="diagram-flow">{box_html}</div>'
    else:
        # Fallback: Render ASCII as pre-formatted text with better styling
        escaped_ascii = ascii_content.replace('<', '&lt;').replace('>', '&gt;')
        diagram_html = f'<pre class="ascii-diagram">{escaped_ascii}</pre>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            width: 1200px;
            height: 800px;
            background: {colors["white"]};
            padding: 60px;
            font-family: 'Inter', sans-serif;
            color: {colors["navy"]};
        }}
        .diagram-container {{
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
        }}
        .title {{
            font-family: 'Poppins', sans-serif;
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 40px;
            color: {colors["navy"]};
            text-align: center;
        }}
        .content {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .diagram-flow {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 30px;
        }}
        .diagram-box {{
            background: {colors["light_gray"]};
            border: 3px solid {colors["blue"]};
            border-radius: 12px;
            padding: 30px 40px;
            min-width: 400px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .box-content {{
            font-family: 'Inter', sans-serif;
            font-size: 24px;
            font-weight: 500;
            line-height: 1.6;
            text-align: center;
            color: {colors["navy"]};
        }}
        .arrow {{
            font-size: 48px;
            color: {colors["orange"]};
            font-weight: bold;
        }}
        .ascii-diagram {{
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 20px;
            line-height: 1.4;
            color: {colors["navy"]};
            background: {colors["light_gray"]};
            padding: 40px;
            border-radius: 8px;
            border: 2px solid {colors["blue"]};
            white-space: pre;
            overflow: auto;
        }}
        .brand {{
            position: absolute;
            bottom: 30px;
            right: 40px;
            font-family: 'Poppins', sans-serif;
            font-size: 18px;
            font-weight: 600;
            color: {colors["orange"]};
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="diagram-container">
        {f'<div class="title">{title}</div>' if title else ''}
        <div class="content">
            {diagram_html}
        </div>
    </div>
    <div class="brand">Sparkry.AI</div>
</body>
</html>"""

    return html


def convert_ascii_to_visual(
    ascii_input: str,
    output_path: str,
    style: str = "framework",
    title: str = ""
) -> Dict[str, Any]:
    """
    Convert ASCII art to professional visual.

    Args:
        ascii_input: ASCII art content
        output_path: Output PNG path
        style: Diagram style (framework, flowchart, tree)
        title: Optional title above diagram

    Returns:
        Dict with success status and output info
    """
    import time
    start_time = time.time()

    try:
        # Parse ASCII structure
        structure = parse_ascii_structure(ascii_input)

        # Generate HTML
        html = generate_html_for_diagram(ascii_input, structure, title, style)

        # Write HTML to temp file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        temp_html = output_file.parent / "_temp_diagram.html"

        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html)

        # Import render function
        tools_dir = Path(__file__).parent
        sys.path.insert(0, str(tools_dir))

        try:
            from render_html_to_image import render_html_to_image as render_fn
        except ImportError:
            # Fallback: call as subprocess
            import subprocess
            render_cmd = [
                sys.executable,
                str(tools_dir / "render-html-to-image.py"),
                "--html-file", str(temp_html),
                "--output", str(output_path),
                "--width", "1200",
                "--height", "800"
            ]
            result = subprocess.run(render_cmd, capture_output=True, text=True)
            temp_html.unlink()

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Render failed: {result.stderr}"
                }

            render_time_ms = int((time.time() - start_time) * 1000)

            return {
                "success": True,
                "visual_path": str(output_path),
                "detected_type": structure["type"],
                "nodes": structure["box_count"],
                "connections": structure["arrow_count"],
                "render_time_ms": render_time_ms,
                "style": style
            }

        # Render HTML to PNG
        render_result = render_fn(
            html_file=str(temp_html),
            output_path=str(output_path),
            width=1200,
            height=800
        )

        # Clean up temp HTML
        temp_html.unlink()

        if not render_result.get("success"):
            return render_result

        render_time_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "visual_path": str(output_path),
            "detected_type": structure["type"],
            "nodes": structure["box_count"],
            "connections": structure["arrow_count"],
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
        description='Convert ASCII art to professional diagram'
    )
    parser.add_argument('--ascii-input', required=True, help='ASCII art content')
    parser.add_argument('--output', required=True, help='Output PNG path')
    parser.add_argument('--style', choices=['framework', 'flowchart', 'tree'],
                       default='framework', help='Diagram style')
    parser.add_argument('--title', default='', help='Optional title above diagram')

    args = parser.parse_args()

    # Convert ASCII to visual
    result = convert_ascii_to_visual(
        ascii_input=args.ascii_input,
        output_path=args.output,
        style=args.style,
        title=args.title
    )

    # Output result
    print(json.dumps(result, indent=2))

    # Exit with error code if failed
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
