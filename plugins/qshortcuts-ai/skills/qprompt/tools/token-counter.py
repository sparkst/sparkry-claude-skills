#!/usr/bin/env python3
"""
Token Counter - Count tokens in text using Claude tokenizer

Counts tokens, words, and characters in text for optimization analysis.

Usage:
    python token-counter.py --text "Your prompt text here"
    python token-counter.py --file prompt.txt

Output (JSON):
    {
      "text_preview": "Your prompt text here...",
      "token_count": 1542,
      "character_count": 7891,
      "word_count": 1205,
      "tokens_per_word": 1.28,
      "breakdown": {
        "instructions": 842,
        "examples": 450,
        "constraints": 250
      }
    }
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any


def count_tokens(text: str) -> int:
    """
    Count tokens in text.

    Stub implementation - uses word-based estimate.
    In production, would use actual Claude tokenizer.

    Returns:
        Token count (estimated)
    """
    # Rough estimate: ~1.3 tokens per word for English text
    words = len(text.split())
    return int(words * 1.3)


def analyze_breakdown(text: str) -> Dict[str, int]:
    """
    Analyze token breakdown by section.

    Stub implementation - uses simple heuristics.

    Returns:
        Dict with token counts per section
    """
    # Stub implementation - in production, would:
    # 1. Identify sections (instructions, examples, constraints)
    # 2. Count tokens per section

    total_tokens = count_tokens(text)

    # Simple heuristic breakdown
    return {
        "instructions": int(total_tokens * 0.55),
        "examples": int(total_tokens * 0.30),
        "constraints": int(total_tokens * 0.15)
    }


def main():
    parser = argparse.ArgumentParser(description="Count tokens in text")
    parser.add_argument("--text", help="Text to count (inline)")
    parser.add_argument("--file", help="File path to count")

    args = parser.parse_args()

    try:
        # Get text from file or inline
        if args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                print(json.dumps({"error": f"File not found: {args.file}"}), file=sys.stderr)
                sys.exit(1)
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif args.text:
            text = args.text
        else:
            print(json.dumps({"error": "Must provide --text or --file"}), file=sys.stderr)
            sys.exit(1)

        # Count tokens
        token_count = count_tokens(text)

        # Count characters and words
        character_count = len(text)
        word_count = len(text.split())

        # Calculate tokens per word
        tokens_per_word = round(token_count / word_count, 2) if word_count > 0 else 0

        # Analyze breakdown
        breakdown = analyze_breakdown(text)

        # Generate preview (first 100 chars)
        text_preview = text[:100] + "..." if len(text) > 100 else text

        # Build result
        result = {
            "text_preview": text_preview,
            "token_count": token_count,
            "character_count": character_count,
            "word_count": word_count,
            "tokens_per_word": tokens_per_word,
            "breakdown": breakdown
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
