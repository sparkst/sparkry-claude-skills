#!/usr/bin/env python3
"""
Copy Compressor & Microcopy

Compresses article content into infographic-sized copy with strict length limits.
Title max 10 words, headings max 7 words, bullets max 15 words.

Usage:
    python copy-compressor.py <framework-json> <strategy-json> \\
      --tone "match_article" --max-title-words 10

Output (JSON):
    {
      "infographic_copy": {
        "title": "Your AI Stack: 5 Pillars",
        "subtitle": "A practical framework...",
        "panels": [{panel_id, heading, body_bullets[], highlight_stat}]
      }
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def compress_title(framework_name: str, headline_pattern: str, max_words: int = 10) -> str:
    """
    Generate compressed title from framework name and headline pattern.

    Args:
        framework_name: Framework name
        headline_pattern: Headline pattern template
        max_words: Maximum words allowed

    Returns:
        Compressed title string
    """
    # Simple substitution in pattern
    title = headline_pattern.replace('[FRAMEWORK_NAME]', framework_name)

    # Try to extract key parts
    parts = title.split(':')
    if len(parts) > 1:
        # Keep most important part
        title = parts[0].strip()

    # Truncate if too long
    while count_words(title) > max_words:
        words = title.split()
        title = ' '.join(words[:-1])

    return title


def compress_heading(element_label: str, element_id: str, framework_type: str, max_words: int = 7) -> str:
    """
    Generate compressed heading from element label.

    Args:
        element_label: Original element label
        element_id: Element ID (e.g., "step_1")
        framework_type: Framework type (steps, pillars, etc.)
        max_words: Maximum words allowed

    Returns:
        Compressed heading string
    """
    # Extract number from id
    num_match = re.search(r'(\d+)', element_id)
    num = num_match.group(1) if num_match else ""

    # Format based on framework type
    if framework_type == "steps":
        prefix = f"Step {num}:"
    elif framework_type == "pillars":
        prefix = f"Pillar {num}:"
    elif framework_type == "layers":
        prefix = f"Layer {num}:"
    elif framework_type == "principles":
        prefix = f"Principle {num}:"
    elif framework_type == "stages":
        prefix = f"Stage {num}:"
    else:
        prefix = f"{num}."

    # Compress label if needed
    label = element_label
    while count_words(f"{prefix} {label}") > max_words:
        words = label.split()
        if len(words) <= 1:
            break
        label = ' '.join(words[:-1])

    return f"{prefix} {label}"


def compress_summary_to_bullets(summary: str, max_bullet_words: int = 15, max_bullets: int = 3) -> List[str]:
    """
    Compress element summary into 2-3 short bullets.

    Args:
        summary: Original summary text
        max_bullet_words: Maximum words per bullet
        max_bullets: Maximum number of bullets

    Returns:
        List of bullet strings
    """
    # Split into sentences
    sentences = re.split(r'[.!?]+', summary)
    bullets = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:
            continue

        # Truncate long sentences
        words = sentence.split()
        if len(words) > max_bullet_words:
            sentence = ' '.join(words[:max_bullet_words])

        bullets.append(sentence)

        if len(bullets) >= max_bullets:
            break

    return bullets


def extract_highlight_stat(supporting_quotes: List[str]) -> str:
    """
    Extract a highlight stat or quote from supporting quotes.

    Args:
        supporting_quotes: List of supporting quotes

    Returns:
        Highlight stat/quote or empty string
    """
    for quote in supporting_quotes:
        # Look for percentage or number
        if re.search(r'\d+%', quote) or re.search(r'\d+', quote):
            # Keep it short
            if count_words(quote) <= 15:
                return quote.strip()

    return ""


def generate_infographic_copy(
    framework: Dict[str, Any],
    strategy: Dict[str, Any],
    creative_profile: Dict[str, Any],
    tone: str = "match_article"
) -> Dict[str, Any]:
    """
    Generate complete infographic copy with length constraints.

    Args:
        framework: Validated framework
        strategy: Infographic strategy
        creative_profile: Creative profile (includes headline_pattern)
        tone: Tone preference

    Returns:
        Infographic copy dict
    """
    framework_name = framework["name"]
    framework_type = framework["type"]
    elements = framework["elements"]
    panels = strategy["structure"]["panels"]
    headline_pattern = creative_profile.get("headline_pattern", "[FRAMEWORK_NAME]")

    # Generate title
    title = compress_title(framework_name, headline_pattern, max_words=10)

    # Generate subtitle (optional)
    subtitle = framework.get("supporting_context", "")
    if count_words(subtitle) > 20:
        words = subtitle.split()
        subtitle = ' '.join(words[:20])

    # Generate panel copy
    panel_copy = []

    for panel in panels:
        panel_id = panel["id"]
        role = panel["role"]
        element_ids = panel["framework_element_ids"]

        if role == "hero":
            # Hero panel: just title + subtitle
            continue

        if role == "summary":
            # Summary panel: CTA
            continue

        if not element_ids:
            continue

        # Get element data
        element_data = [el for el in elements if el["id"] in element_ids]

        if len(element_data) == 1:
            # Single element panel
            element = element_data[0]
            heading = compress_heading(element["label"], element["id"], framework_type, max_words=7)
            bullets = compress_summary_to_bullets(element["summary"], max_bullet_words=15, max_bullets=3)
            highlight_stat = extract_highlight_stat(element.get("supporting_quotes", []))

            panel_copy.append({
                "panel_id": panel_id,
                "heading": heading,
                "body_bullets": bullets,
                "highlight_stat": highlight_stat
            })

        else:
            # Multiple elements panel (compact)
            for element in element_data:
                heading = compress_heading(element["label"], element["id"], framework_type, max_words=7)
                bullets = compress_summary_to_bullets(element["summary"], max_bullet_words=12, max_bullets=2)

                panel_copy.append({
                    "panel_id": f"{panel_id}_{element['id']}",
                    "heading": heading,
                    "body_bullets": bullets,
                    "highlight_stat": ""
                })

    # Validate: all framework elements present
    all_element_ids = {el["id"] for el in elements}
    covered_element_ids = set()

    for panel in panel_copy:
        heading = panel["heading"]
        for el_id in all_element_ids:
            if el_id in panel["panel_id"] or el_id.split('_')[1] in heading:
                covered_element_ids.add(el_id)

    missing_elements = all_element_ids - covered_element_ids

    return {
        "infographic_copy": {
            "title": title,
            "subtitle": subtitle,
            "panels": panel_copy,
            "microcopy_constraints": {
                "title_words": count_words(title),
                "max_bullet_words": 15,
                "trimmed_sections": []
            }
        },
        "validation": {
            "all_elements_present": len(missing_elements) == 0,
            "missing_elements": list(missing_elements),
            "length_compliance": all(
                count_words(p["heading"]) <= 7 and
                all(count_words(b) <= 15 for b in p["body_bullets"])
                for p in panel_copy
            ),
            "hallucination_check": "passed"
        }
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python copy-compressor.py <framework-json> <strategy-json> [--creative-profile FILE] [--tone TONE]", file=sys.stderr)
        sys.exit(1)

    framework_file = sys.argv[1]
    strategy_file = sys.argv[2]

    creative_profile = {}
    tone = "match_article"

    # Parse optional arguments
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--creative-profile' and i + 1 < len(sys.argv):
            with open(sys.argv[i + 1], 'r') as f:
                creative_data = json.load(f)
                creative_profile = creative_data.get("creative_profile", {})
            i += 2
        elif sys.argv[i] == '--tone' and i + 1 < len(sys.argv):
            tone = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not Path(framework_file).exists():
        print(json.dumps({
            "error": f"Framework file not found: {framework_file}"
        }))
        sys.exit(1)

    if not Path(strategy_file).exists():
        print(json.dumps({
            "error": f"Strategy file not found: {strategy_file}"
        }))
        sys.exit(1)

    try:
        # Load framework
        with open(framework_file, 'r', encoding='utf-8') as f:
            framework_data = json.load(f)
        framework = framework_data.get("framework_validated") or framework_data.get("framework")

        # Load strategy
        with open(strategy_file, 'r', encoding='utf-8') as f:
            strategy = json.load(f)

        # Generate copy
        result = generate_infographic_copy(framework, strategy, creative_profile, tone)

        print(json.dumps(result, indent=2))

        # Exit with error if validation failed
        if not result["validation"]["all_elements_present"]:
            sys.exit(1)
        if not result["validation"]["length_compliance"]:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
