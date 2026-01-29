#!/usr/bin/env python3
"""
Detect Visual Opportunities

Scan article for visualizable content (hero image, ASCII diagrams, frameworks).

Usage:
    python detect-visual-opportunities.py --file content.md

Output (JSON):
    {
      "success": true,
      "article": "content.md",
      "opportunities": [...],
      "total_opportunities": 3
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
import argparse


def detect_hero_opportunity(content: str, file_path: str) -> Dict[str, Any]:
    """
    Always suggest hero image from H1 + first paragraph.

    Args:
        content: Markdown content
        file_path: Article file path

    Returns:
        Hero opportunity dict
    """
    # Extract H1 title
    h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = h1_match.group(1).strip() if h1_match else "Untitled Article"

    # Extract first paragraph (after H1, before next heading)
    # Skip empty lines and metadata blocks
    lines = content.split('\n')
    subtitle = ""
    in_content = False
    for line in lines:
        line = line.strip()
        # Skip until after H1
        if line.startswith('# '):
            in_content = True
            continue
        # Skip metadata blocks
        if line.startswith('---') or line.startswith('**'):
            continue
        # Stop at next heading
        if in_content and line.startswith('#'):
            break
        # Collect first non-empty paragraph
        if in_content and line and not line.startswith('#'):
            subtitle = line
            break

    # Truncate subtitle if too long
    if len(subtitle) > 150:
        subtitle = subtitle[:147] + "..."

    return {
        "type": "hero",
        "suggested": True,
        "content": {
            "title": title,
            "subtitle": subtitle if subtitle else "Key insights from the article"
        }
    }


def detect_ascii_diagrams(content: str) -> List[Dict[str, Any]]:
    """
    Detect ASCII art diagrams with box-drawing characters.

    Args:
        content: Markdown content

    Returns:
        List of ASCII diagram opportunities
    """
    opportunities = []

    # Box-drawing character patterns
    box_chars = r'[┌┐└┘│─├┤┬┴┼╔╗╚╝║═╠╣╦╩╬]'
    ascii_borders = r'[\+\-\|]'
    arrows = r'[→←↑↓▼▲►◄⇒⇐↔]'

    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect code blocks with box-drawing characters
        if '```' in line:
            i += 1
            code_block = []
            start_line = i
            while i < len(lines) and '```' not in lines[i]:
                code_block.append(lines[i])
                i += 1

            code_content = '\n'.join(code_block)

            # Check if code block contains ASCII art
            if (re.search(box_chars, code_content) or
                (re.search(ascii_borders, code_content) and len(code_block) > 2) or
                re.search(arrows, code_content)):

                # Determine diagram type
                diagram_type = "flowchart"
                if '├' in code_content or '└' in code_content:
                    diagram_type = "tree"
                elif re.search(r'┌.*┐', code_content):
                    diagram_type = "framework"

                opportunities.append({
                    "type": "ascii_diagram",
                    "location": f"Line {start_line}-{i}",
                    "content": code_content.strip(),
                    "suggested_style": diagram_type,
                    "line_count": len(code_block)
                })

        # Detect indented ASCII art (not in code blocks)
        elif line.startswith('    ') or line.startswith('\t'):
            if re.search(box_chars, line) or re.search(arrows, line):
                ascii_block = [line]
                start_line = i + 1
                i += 1
                # Collect adjacent indented lines
                while i < len(lines) and (lines[i].startswith('    ') or lines[i].startswith('\t') or lines[i].strip() == ''):
                    if lines[i].strip():  # Skip empty lines
                        ascii_block.append(lines[i])
                    i += 1
                    if len(ascii_block) > 20:  # Limit block size
                        break

                if len(ascii_block) >= 3:  # Minimum 3 lines for diagram
                    ascii_content = '\n'.join(ascii_block)

                    # Determine type
                    diagram_type = "flowchart"
                    if '├' in ascii_content or '└' in ascii_content:
                        diagram_type = "tree"

                    opportunities.append({
                        "type": "ascii_diagram",
                        "location": f"Line {start_line}-{i}",
                        "content": ascii_content.strip(),
                        "suggested_style": diagram_type,
                        "line_count": len(ascii_block)
                    })
                continue

        i += 1

    return opportunities


def detect_framework_opportunities(content: str) -> List[Dict[str, Any]]:
    """
    Detect framework descriptions (numbered lists, process flows).

    Args:
        content: Markdown content

    Returns:
        List of framework opportunities
    """
    opportunities = []

    # Pattern: Section with "Framework", "Pillars", "Layers", "Steps" in heading
    framework_keywords = r'(framework|pillars|layers|steps|principles|components)'
    section_pattern = rf'##\s+.*{framework_keywords}.*\n\n((?:(?:\d+\.|[-*])\s+.+\n?)+)'

    for match in re.finditer(section_pattern, content, re.IGNORECASE | re.MULTILINE):
        section_title = re.search(r'##\s+(.+)', match.group(0))
        title = section_title.group(1).strip() if section_title else "Framework"

        # Extract list items
        list_content = match.group(2).strip()
        items = re.findall(r'(?:\d+\.|[-*])\s+(.+)', list_content)

        if len(items) >= 3:  # At least 3 items to be a framework
            # Find line number
            line_num = content[:match.start()].count('\n') + 1

            opportunities.append({
                "type": "framework",
                "location": f"Section: {title}",
                "content": list_content,
                "suggested_style": "framework",
                "item_count": len(items),
                "title": title,
                "line_number": line_num
            })

    return opportunities


def detect_visual_opportunities(file_path: str, suggest_only: bool = False) -> Dict[str, Any]:
    """
    Scan article for all visual opportunities.

    Args:
        file_path: Path to markdown article
        suggest_only: Only suggest, don't generate

    Returns:
        Dict with all detected opportunities
    """
    path = Path(file_path)
    if not path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}"
        }

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        opportunities = []

        # 1. Hero image (always)
        hero = detect_hero_opportunity(content, file_path)
        opportunities.append(hero)

        # 2. ASCII diagrams
        ascii_diagrams = detect_ascii_diagrams(content)
        opportunities.extend(ascii_diagrams)

        # 3. Framework descriptions
        frameworks = detect_framework_opportunities(content)
        opportunities.extend(frameworks)

        return {
            "success": True,
            "article": file_path,
            "opportunities": opportunities,
            "total_opportunities": len(opportunities),
            "breakdown": {
                "hero": 1,
                "ascii_diagrams": len(ascii_diagrams),
                "frameworks": len(frameworks)
            },
            "suggest_only": suggest_only
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description='Detect visual opportunities in markdown article'
    )
    parser.add_argument('--file', required=True, help='Path to markdown article')
    parser.add_argument('--suggest-only', action='store_true',
                       help='Only suggest opportunities, do not generate')

    args = parser.parse_args()

    # Detect opportunities
    result = detect_visual_opportunities(args.file, args.suggest_only)

    # Output result
    print(json.dumps(result, indent=2))

    # Exit with error code if failed
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
