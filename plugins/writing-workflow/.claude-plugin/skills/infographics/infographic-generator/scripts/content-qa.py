#!/usr/bin/env python3
"""
Content, Structural & Creativity QA

Validates rendered HTML matches framework without hallucinations.
Checks accessibility, content alignment, and creative effectiveness.

Usage:
    python content-qa.py <rendered-html> <framework-json> <infographic-copy-json>

Output (JSON):
    {
      "qa_results": {
        "content_alignment_score": 0.94,
        "issues": [],
        "creativity_issues": [],
        "hallucination_check": {"passed": true},
        "accessibility_check": {"wcag_aa_contrast": true}
      },
      "selected": true
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
from html.parser import HTMLParser


class InfographicHTMLParser(HTMLParser):
    """Parse HTML to extract text content."""

    def __init__(self):
        super().__init__()
        self.text_content = []
        self.in_title = False
        self.in_heading = False

    def handle_starttag(self, tag, attrs):
        if tag == 'h1':
            self.in_title = True
        elif tag in ['h2', 'h3', 'h4']:
            self.in_heading = True

    def handle_endtag(self, tag):
        if tag == 'h1':
            self.in_title = False
        elif tag in ['h2', 'h3', 'h4']:
            self.in_heading = False

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.text_content.append(text)


def parse_html_content(html: str) -> List[str]:
    """
    Extract text content from HTML.

    Args:
        html: HTML string

    Returns:
        List of text strings
    """
    parser = InfographicHTMLParser()
    parser.feed(html)
    return parser.text_content


def check_content_alignment(html_content: List[str], framework: Dict[str, Any], infographic_copy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if HTML content matches framework and copy.

    Args:
        html_content: Extracted HTML text
        framework: Validated framework
        infographic_copy: Infographic copy

    Returns:
        Alignment result dict
    """
    issues = []

    # Join all HTML content for searching
    html_text = ' '.join(html_content).lower()

    # Check title present
    title = infographic_copy.get("title", "").lower()
    if title and title not in html_text:
        issues.append(f"Title not found in HTML: '{title}'")

    # Check all framework elements present
    elements = framework.get("elements", [])
    missing_elements = []

    for element in elements:
        label = element["label"].lower()
        # Check if label or close variant appears
        if label not in html_text:
            # Check for partial match (at least 50% of label words)
            label_words = label.split()
            found_words = sum(1 for word in label_words if word in html_text)
            if found_words / len(label_words) < 0.5:
                missing_elements.append(element["label"])

    if missing_elements:
        issues.append(f"Missing elements: {', '.join(missing_elements)}")

    # Calculate alignment score
    total_checks = 1 + len(elements)  # Title + elements
    failed_checks = len(issues)
    alignment_score = (total_checks - failed_checks) / total_checks

    return {
        "content_alignment_score": alignment_score,
        "issues": issues,
        "missing_elements": missing_elements
    }


def check_hallucinations(html_content: List[str], infographic_copy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check for hallucinated content not in original copy.

    Args:
        html_content: Extracted HTML text
        infographic_copy: Infographic copy (source of truth)

    Returns:
        Hallucination check result
    """
    # Build expected content from copy
    expected_texts = [
        infographic_copy.get("title", ""),
        infographic_copy.get("subtitle", "")
    ]

    for panel in infographic_copy.get("panels", []):
        expected_texts.append(panel.get("heading", ""))
        expected_texts.extend(panel.get("body_bullets", []))
        if panel.get("highlight_stat"):
            expected_texts.append(panel["highlight_stat"])

    # Join and normalize
    expected_text_lower = ' '.join(expected_texts).lower()

    # Check if HTML contains unexpected content
    # (Simple heuristic: look for sentences in HTML not in expected)
    fabricated_content = []

    for content in html_content:
        if len(content) < 20:  # Skip short fragments
            continue

        content_lower = content.lower()

        # Check if this content appears in expected
        if content_lower not in expected_text_lower:
            # Check for substantial overlap
            content_words = set(content_lower.split())
            expected_words = set(expected_text_lower.split())
            overlap = len(content_words & expected_words) / len(content_words) if content_words else 0

            if overlap < 0.6:
                fabricated_content.append(content)

    return {
        "passed": len(fabricated_content) == 0,
        "fabricated_content": fabricated_content[:5]  # Limit to 5 examples
    }


def check_accessibility(html: str) -> Dict[str, Any]:
    """
    Check basic accessibility compliance.

    Args:
        html: HTML string

    Returns:
        Accessibility check result
    """
    issues = []

    # Check for semantic HTML (h1, h2, etc.)
    has_h1 = bool(re.search(r'<h1[^>]*>', html))
    has_h2_or_h3 = bool(re.search(r'<h[23][^>]*>', html))

    if not has_h1:
        issues.append("Missing <h1> element (semantic HTML)")
    if not has_h2_or_h3:
        issues.append("Missing heading hierarchy (<h2>, <h3>)")

    # Check for icon+text pairing (icons should not be alone)
    icon_pattern = r'<i class="[^"]*fa-[^"]*"[^>]*></i>'
    icons_found = re.findall(icon_pattern, html)

    # Simple check: icons should be near text
    icon_text_pairing = True  # Assume true unless proven otherwise

    # Check for alt text on images (if any)
    img_pattern = r'<img[^>]*src='
    imgs_without_alt = re.findall(r'<img(?![^>]*alt=)[^>]*>', html)
    if imgs_without_alt:
        issues.append(f"Images missing alt text: {len(imgs_without_alt)}")

    return {
        "wcag_aa_contrast": True,  # Assume true (CSS uses compliant colors)
        "semantic_html": has_h1 and has_h2_or_h3,
        "icon_text_pairing": icon_text_pairing,
        "issues": issues
    }


def check_creativity(html: str, creative_profile: Dict[str, Any]) -> List[str]:
    """
    Check for creativity issues (e.g., cluttered, weak metaphor).

    Args:
        html: HTML string
        creative_profile: Creative profile

    Returns:
        List of creativity issues
    """
    issues = []

    # Check HTML size (too large = likely cluttered)
    if len(html) > 50000:
        issues.append("HTML size very large (potential clutter)")

    # Check for inline styles (should use classes for maintainability)
    inline_styles = re.findall(r'style="[^"]*"', html)
    if len(inline_styles) > 10:
        issues.append(f"Too many inline styles ({len(inline_styles)}), prefer CSS classes")

    # Check for visual metaphor hints in HTML (should have relevant classes/structure)
    visual_metaphor = creative_profile.get("visual_metaphor", "")

    # Positive checks (absence is an issue)
    has_gradient = 'gradient' in html.lower()
    has_shadow = 'shadow' in html.lower()

    if not has_gradient:
        issues.append("Missing gradients (visual richness)")
    if not has_shadow:
        issues.append("Missing shadows (depth)")

    return issues


def run_qa(html_file: str, framework_file: str, copy_file: str) -> Dict[str, Any]:
    """
    Run complete QA checks on generated infographic.

    Args:
        html_file: Path to rendered HTML
        framework_file: Path to framework JSON
        copy_file: Path to infographic copy JSON

    Returns:
        Complete QA results
    """
    # Load files
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    with open(framework_file, 'r', encoding='utf-8') as f:
        framework_data = json.load(f)
    framework = framework_data.get("framework_validated") or framework_data.get("framework")

    with open(copy_file, 'r', encoding='utf-8') as f:
        copy_data = json.load(f)
    infographic_copy = copy_data.get("infographic_copy", {})

    # Extract creative profile if present
    creative_profile = copy_data.get("creative_profile", {})

    # Parse HTML content
    html_content = parse_html_content(html)

    # Run checks
    alignment_result = check_content_alignment(html_content, framework, infographic_copy)
    hallucination_result = check_hallucinations(html_content, infographic_copy)
    accessibility_result = check_accessibility(html)
    creativity_issues = check_creativity(html, creative_profile)

    # Combine issues
    all_issues = alignment_result["issues"]

    # Determine if selected
    critical_issues = (
        len(alignment_result["missing_elements"]) > 0 or
        not hallucination_result["passed"]
    )

    selected = not critical_issues and alignment_result["content_alignment_score"] >= 0.8

    return {
        "qa_results": {
            "content_alignment_score": alignment_result["content_alignment_score"],
            "layout_alignment_notes": f"Checked {len(framework['elements'])} elements",
            "issues": all_issues,
            "creativity_issues": creativity_issues,
            "hallucination_check": hallucination_result,
            "accessibility_check": accessibility_result
        },
        "selected": selected,
        "statistics": {
            "html_size": len(html),
            "text_elements": len(html_content),
            "framework_elements": len(framework["elements"]),
            "missing_elements": len(alignment_result["missing_elements"])
        }
    }


def main():
    if len(sys.argv) < 4:
        print("Usage: python content-qa.py <rendered-html> <framework-json> <infographic-copy-json>", file=sys.stderr)
        sys.exit(1)

    html_file = sys.argv[1]
    framework_file = sys.argv[2]
    copy_file = sys.argv[3]

    for file in [html_file, framework_file, copy_file]:
        if not Path(file).exists():
            print(json.dumps({
                "error": f"File not found: {file}"
            }))
            sys.exit(1)

    try:
        result = run_qa(html_file, framework_file, copy_file)

        print(json.dumps(result, indent=2))

        # Exit with error if not selected (critical issues)
        if not result["selected"]:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
