#!/usr/bin/env python3
"""
Framework Extractor

Detects and extracts structured frameworks (3-10 elements: steps, pillars, layers, stages)
from article text using pattern matching and semantic analysis.

Usage:
    python framework-extractor.py <article-file> [--framework-hint "5 pillars"]

Output (JSON):
    {
      "framework": {
        "name": "The 5 Pillars of AI Transformation",
        "explicit_name_in_text": true,
        "type": "pillars|steps|layers|stages|principles|loops",
        "elements": [{id, label, summary, supporting_quotes}],
        "supporting_context": "This framework guides..."
      },
      "confidence": 0.92,
      "candidates": [{alternative frameworks if multiple found}]
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple


FRAMEWORK_PATTERNS = {
    "steps": [
        r'(?i)(\d+)\s+steps?',
        r'(?i)step\s+(\d+)',
        r'(?i)phase\s+(\d+)',
        r'(?i)stage\s+(\d+)'
    ],
    "pillars": [
        r'(?i)(\d+)\s+pillars?',
        r'(?i)pillar\s+(\d+)',
        r'(?i)(\d+)\s+foundations?'
    ],
    "layers": [
        r'(?i)(\d+)\s+layers?',
        r'(?i)layer\s+(\d+)',
        r'(?i)(\d+)\s+levels?',
        r'(?i)level\s+(\d+)'
    ],
    "principles": [
        r'(?i)(\d+)\s+principles?',
        r'(?i)principle\s+(\d+)',
        r'(?i)(\d+)\s+tenets?'
    ],
    "stages": [
        r'(?i)(\d+)\s+stages?',
        r'(?i)stage\s+(\d+)'
    ],
    "loops": [
        r'(?i)(\d+)\s+loops?',
        r'(?i)loop\s+(\d+)',
        r'(?i)cycle\s+(\d+)'
    ],
    "questions": [
        r'(?i)(\d+)\s+questions?',
        r'(?i)question\s+(\d+)',
        r'(?i)(\d+)-question'
    ]
}


def detect_framework_type_and_count(text: str, hint: str = None) -> List[Tuple[str, int, float]]:
    """
    Detect framework type(s) and element count from article text.

    Args:
        text: Article text to analyze
        hint: Optional user hint (e.g., "5 pillars")

    Returns:
        List of (type, count, confidence) tuples sorted by confidence
    """
    candidates = []

    # If hint provided, prioritize matching patterns
    if hint:
        hint_lower = hint.lower()
        for ftype, patterns in FRAMEWORK_PATTERNS.items():
            if ftype in hint_lower:
                # Extract number from hint
                numbers = re.findall(r'\d+', hint)
                if numbers:
                    count = int(numbers[0])
                    if 3 <= count <= 10:
                        candidates.append((ftype, count, 0.95))

    # Pattern-based detection
    for ftype, patterns in FRAMEWORK_PATTERNS.items():
        counts = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    count = int(match) if match.isdigit() else int(re.search(r'\d+', match).group())
                    if 3 <= count <= 10:
                        counts.append(count)
                except (ValueError, AttributeError):
                    continue

        if counts:
            # Most common count for this type
            most_common = max(set(counts), key=counts.count)
            frequency = counts.count(most_common)
            confidence = min(0.9, 0.5 + (frequency * 0.1))
            candidates.append((ftype, most_common, confidence))

    # Sort by confidence (descending)
    candidates.sort(key=lambda x: x[2], reverse=True)

    return candidates


def extract_framework_elements(text: str, ftype: str, count: int) -> List[Dict[str, Any]]:
    """
    Extract individual framework elements from text.

    Args:
        text: Article text
        ftype: Framework type (steps, pillars, etc.)
        count: Expected number of elements

    Returns:
        List of element dicts with id, label, summary, supporting_quotes
    """
    elements = []

    # Build regex for detecting elements
    if ftype == "steps":
        element_pattern = r'(?i)step\s+(\d+)[\s:—-]+([^\n.]+)'
    elif ftype == "pillars":
        element_pattern = r'(?i)pillar\s+(\d+)[\s:—-]+([^\n.]+)'
    elif ftype == "layers":
        element_pattern = r'(?i)layer\s+(\d+)[\s:—-]+([^\n.]+)'
    elif ftype == "principles":
        element_pattern = r'(?i)principle\s+(\d+)[\s:—-]+([^\n.]+)'
    elif ftype == "stages":
        element_pattern = r'(?i)stage\s+(\d+)[\s:—-]+([^\n.]+)'
    elif ftype == "loops":
        element_pattern = r'(?i)loop\s+(\d+)[\s:—-]+([^\n.]+)'
    elif ftype == "questions":
        element_pattern = r'(?i)question\s+(\d+)[\s:—-]+([^\n?"]+)'
    else:
        # Generic numbered list
        element_pattern = r'(?:^|\n)(\d+)[\.\)]\s+([^\n]+)'

    matches = re.findall(element_pattern, text, re.MULTILINE)

    for num, label in matches:
        element_num = int(num)
        if element_num > count:
            continue

        # Extract supporting context (next 2-3 sentences after label)
        label_pos = text.find(label)
        if label_pos != -1:
            context_start = label_pos + len(label)
            context_text = text[context_start:context_start + 500]
            sentences = re.split(r'[.!?]+', context_text)
            summary = '. '.join(sentences[:2]).strip()
            supporting_quotes = [s.strip() for s in sentences[1:3] if len(s.strip()) > 20]
        else:
            summary = ""
            supporting_quotes = []

        elements.append({
            "id": f"{ftype}_{element_num}",
            "label": label.strip(),
            "summary": summary or f"Element {element_num} of the {ftype} framework",
            "supporting_quotes": supporting_quotes[:2]
        })

    # Fill missing elements if detected count doesn't match expected
    if len(elements) < count:
        for i in range(len(elements) + 1, count + 1):
            elements.append({
                "id": f"{ftype}_{i}",
                "label": f"{ftype.capitalize()} {i}",
                "summary": f"Element {i} (details not extracted)",
                "supporting_quotes": []
            })

    # Sort by id to ensure order
    elements.sort(key=lambda x: int(x['id'].split('_')[1]))

    return elements[:count]


def extract_framework_name(text: str, ftype: str, count: int) -> Tuple[str, bool]:
    """
    Extract explicit framework name from text if present.

    Returns:
        (name, explicit_in_text)
    """
    # Look for title-like patterns
    title_patterns = [
        rf'(?i)(?:the\s+)?(\d+\s+{ftype}[^\n.]+)',
        rf'(?i)([^\n]+:\s+\d+\s+{ftype})',
        rf'(?i)([^\n]+{ftype}[^\n]+)'
    ]

    for pattern in title_patterns:
        match = re.search(pattern, text[:1000])  # Check first 1000 chars
        if match:
            name = match.group(1).strip()
            # Clean up name
            name = re.sub(r'\s+', ' ', name)
            return (name, True)

    # Generate generic name
    return (f"The {count} {ftype.capitalize()}", False)


def extract_supporting_context(text: str) -> str:
    """
    Extract 1-2 sentence overview of what the framework accomplishes.
    """
    # Look for intro paragraph (first 500 chars)
    intro = text[:500]
    sentences = re.split(r'[.!?]+', intro)

    # Find sentence mentioning framework or purpose
    for sentence in sentences:
        if any(word in sentence.lower() for word in ['framework', 'help', 'guide', 'enable', 'transform']):
            return sentence.strip()

    # Fallback: return first 2 sentences
    return '. '.join([s.strip() for s in sentences[:2] if s.strip()])


def extract_framework(text: str, framework_hint: str = None) -> Dict[str, Any]:
    """
    Main extraction function.

    Args:
        text: Article text
        framework_hint: Optional user hint

    Returns:
        Dict with framework data + confidence
    """
    # Detect framework type and count
    candidates = detect_framework_type_and_count(text, framework_hint)

    if not candidates:
        return {
            "error": "No framework detected (3-10 elements) in article",
            "confidence": 0.0
        }

    # Use highest confidence candidate
    ftype, count, confidence = candidates[0]

    # Extract elements
    elements = extract_framework_elements(text, ftype, count)

    # Extract name
    name, explicit = extract_framework_name(text, ftype, count)

    # Extract context
    context = extract_supporting_context(text)

    return {
        "framework": {
            "name": name,
            "explicit_name_in_text": explicit,
            "type": ftype,
            "elements": elements,
            "supporting_context": context
        },
        "confidence": confidence,
        "candidates": [
            {"type": t, "count": c, "confidence": conf}
            for t, c, conf in candidates[1:3]  # Include top 2 alternatives
        ]
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python framework-extractor.py <article-file> [--framework-hint 'hint']", file=sys.stderr)
        sys.exit(1)

    article_file = sys.argv[1]
    framework_hint = None

    # Parse optional hint
    if len(sys.argv) > 2 and sys.argv[2] == '--framework-hint':
        framework_hint = sys.argv[3] if len(sys.argv) > 3 else None

    if not Path(article_file).exists():
        print(json.dumps({
            "error": f"File not found: {article_file}"
        }))
        sys.exit(1)

    try:
        with open(article_file, 'r', encoding='utf-8') as f:
            text = f.read()

        if len(text) < 500:
            print(json.dumps({
                "error": "Article too short (< 500 chars) for framework extraction"
            }))
            sys.exit(1)

        result = extract_framework(text, framework_hint)

        print(json.dumps(result, indent=2))

        # Exit with error code if no framework found
        if "error" in result:
            sys.exit(1)

        # Exit with error code if confidence too low
        if result["confidence"] < 0.6:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
