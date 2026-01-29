#!/usr/bin/env python3
"""
Framework Validator

Validates extracted framework against article text to prevent hallucinations.
Ensures all framework elements are backed by article content.

Usage:
    python framework-validator.py <framework-json> <article-file>

Output (JSON):
    {
      "framework_validated": {...},
      "confidence_score": 0.87,
      "issues": [
        {
          "element_id": "step_3",
          "issue": "Summary introduces claim not in article",
          "severity": "high|medium|low"
        }
      ],
      "validation_passed": true
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
from difflib import SequenceMatcher


def similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings (0-1)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def validate_element_label(element: Dict[str, Any], article_text: str) -> Dict[str, Any]:
    """
    Validate that element label appears or is paraphrased in article.

    Returns:
        {
          "valid": bool,
          "issue": str or None,
          "confidence": float,
          "supporting_text": str or None
        }
    """
    label = element["label"]
    label_lower = label.lower()

    # Check exact match
    if label_lower in article_text.lower():
        # Find surrounding context
        pos = article_text.lower().find(label_lower)
        context_start = max(0, pos - 50)
        context_end = min(len(article_text), pos + len(label) + 50)
        supporting_text = article_text[context_start:context_end].strip()

        return {
            "valid": True,
            "issue": None,
            "confidence": 1.0,
            "supporting_text": supporting_text
        }

    # Check paraphrase (similarity > 0.7)
    # Split article into sentences
    sentences = re.split(r'[.!?]+', article_text)
    best_match_ratio = 0.0
    best_match_text = None

    for sentence in sentences:
        if len(sentence.strip()) < 10:
            continue
        ratio = similarity_ratio(label, sentence)
        if ratio > best_match_ratio:
            best_match_ratio = ratio
            best_match_text = sentence.strip()

    if best_match_ratio >= 0.7:
        return {
            "valid": True,
            "issue": None,
            "confidence": best_match_ratio,
            "supporting_text": best_match_text
        }

    # Label not found or too dissimilar
    return {
        "valid": False,
        "issue": f"Label '{label}' not found in article (best match: {best_match_ratio:.2f})",
        "confidence": best_match_ratio,
        "supporting_text": best_match_text
    }


def validate_element_summary(element: Dict[str, Any], article_text: str) -> Dict[str, Any]:
    """
    Validate that summary doesn't introduce undocumented claims.

    Returns:
        {
          "valid": bool,
          "issue": str or None,
          "confidence": float
        }
    """
    summary = element["summary"]

    # Extract key claims from summary (noun phrases, verbs)
    # Simple heuristic: split into chunks
    summary_chunks = [chunk.strip() for chunk in re.split(r'[,;]+', summary) if len(chunk.strip()) > 10]

    if not summary_chunks:
        return {
            "valid": True,
            "issue": None,
            "confidence": 0.5  # Empty summary is technically valid but low confidence
        }

    # Check if summary chunks appear in article
    found_chunks = 0
    for chunk in summary_chunks:
        chunk_lower = chunk.lower()
        # Check direct match or high similarity
        if chunk_lower in article_text.lower():
            found_chunks += 1
            continue

        # Check similarity to article sentences
        sentences = re.split(r'[.!?]+', article_text)
        for sentence in sentences:
            if similarity_ratio(chunk, sentence) >= 0.65:
                found_chunks += 1
                break

    coverage = found_chunks / len(summary_chunks)

    if coverage < 0.5:
        return {
            "valid": False,
            "issue": f"Summary contains claims not found in article (coverage: {coverage:.0%})",
            "confidence": coverage
        }

    return {
        "valid": True,
        "issue": None,
        "confidence": coverage
    }


def validate_element_order(elements: List[Dict[str, Any]], article_text: str) -> Dict[str, Any]:
    """
    Validate that element order matches article introduction order.

    Returns:
        {
          "valid": bool,
          "issue": str or None,
          "suggested_order": List[str] or None
        }
    """
    # Find positions of labels in article
    label_positions = []
    for element in elements:
        label = element["label"]
        pos = article_text.lower().find(label.lower())
        if pos != -1:
            label_positions.append((element["id"], pos))

    if len(label_positions) < 2:
        # Not enough elements found to validate order
        return {
            "valid": True,
            "issue": None,
            "suggested_order": None
        }

    # Check if positions are in order
    sorted_positions = sorted(label_positions, key=lambda x: x[1])
    actual_order = [el["id"] for el in elements if any(el["id"] == lp[0] for lp in label_positions)]
    expected_order = [lp[0] for lp in sorted_positions]

    if actual_order != expected_order:
        return {
            "valid": False,
            "issue": f"Element order doesn't match article (expected: {expected_order})",
            "suggested_order": expected_order
        }

    return {
        "valid": True,
        "issue": None,
        "suggested_order": None
    }


def validate_framework(framework: Dict[str, Any], article_text: str) -> Dict[str, Any]:
    """
    Main validation function.

    Args:
        framework: Extracted framework dict
        article_text: Original article text

    Returns:
        Validation result with validated framework, confidence, issues
    """
    issues = []
    element_confidences = []
    validated_elements = []

    # Validate each element
    for element in framework["elements"]:
        # Validate label
        label_result = validate_element_label(element, article_text)
        if not label_result["valid"]:
            issues.append({
                "element_id": element["id"],
                "issue": label_result["issue"],
                "severity": "high"
            })

        # Validate summary
        summary_result = validate_element_summary(element, article_text)
        if not summary_result["valid"]:
            issues.append({
                "element_id": element["id"],
                "issue": summary_result["issue"],
                "severity": "medium"
            })

        # Store confidence
        avg_confidence = (label_result["confidence"] + summary_result["confidence"]) / 2
        element_confidences.append(avg_confidence)

        # Build validated element (add validation metadata)
        validated_element = element.copy()
        validated_element["validation"] = {
            "label_confidence": label_result["confidence"],
            "summary_confidence": summary_result["confidence"],
            "supporting_text": label_result.get("supporting_text")
        }
        validated_elements.append(validated_element)

    # Validate element order
    order_result = validate_element_order(framework["elements"], article_text)
    if not order_result["valid"]:
        issues.append({
            "element_id": "all",
            "issue": order_result["issue"],
            "severity": "medium"
        })

    # Calculate overall confidence
    overall_confidence = sum(element_confidences) / len(element_confidences) if element_confidences else 0.0

    # Check for high-severity issues
    high_severity_issues = [i for i in issues if i["severity"] == "high"]
    validation_passed = len(high_severity_issues) == 0 and overall_confidence >= 0.7

    # Build validated framework
    framework_validated = framework.copy()
    framework_validated["elements"] = validated_elements

    return {
        "framework_validated": framework_validated,
        "confidence_score": overall_confidence,
        "issues": issues,
        "validation_passed": validation_passed,
        "statistics": {
            "total_elements": len(framework["elements"]),
            "validated_elements": len([e for e in element_confidences if e >= 0.7]),
            "high_severity_issues": len(high_severity_issues),
            "medium_severity_issues": len([i for i in issues if i["severity"] == "medium"]),
            "low_severity_issues": len([i for i in issues if i["severity"] == "low"])
        }
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python framework-validator.py <framework-json> <article-file>", file=sys.stderr)
        sys.exit(1)

    framework_file = sys.argv[1]
    article_file = sys.argv[2]

    if not Path(framework_file).exists():
        print(json.dumps({
            "error": f"Framework file not found: {framework_file}"
        }))
        sys.exit(1)

    if not Path(article_file).exists():
        print(json.dumps({
            "error": f"Article file not found: {article_file}"
        }))
        sys.exit(1)

    try:
        # Load framework
        with open(framework_file, 'r', encoding='utf-8') as f:
            framework_data = json.load(f)

        if "framework" not in framework_data:
            print(json.dumps({
                "error": "Invalid framework JSON: missing 'framework' key"
            }))
            sys.exit(1)

        framework = framework_data["framework"]

        # Load article
        with open(article_file, 'r', encoding='utf-8') as f:
            article_text = f.read()

        # Validate
        result = validate_framework(framework, article_text)

        print(json.dumps(result, indent=2))

        # Exit with error code if validation failed
        if not result["validation_passed"]:
            sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
