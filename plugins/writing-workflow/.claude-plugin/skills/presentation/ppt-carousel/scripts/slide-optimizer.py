#!/usr/bin/env python3
"""
Slide Optimizer

Parse LinkedIn post markdown and optimize content for PowerPoint carousel slides.
Extracts structure, chunks content, suggests icons, and recommends layouts.

Usage:
    python slide-optimizer.py content.md --target-slides 8 --icon-style lucide

Output (JSON):
    {
      "slides": [...],
      "metadata": {...}
    }
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


# Icon mappings for keyword detection
ICON_MAPPINGS = {
    r'\b(team|people|split|organization|group)\b': 'lucide:users-2',
    r'\b(problem|warning|mistake|alert|issue)\b': 'lucide:alert-triangle',
    r'\b(layer|level|architecture|framework|structure)\b': 'lucide:layers',
    r'\b(example|case|story|real)\b': 'lucide:sparkles',
    r'\b(quality|shield|protect|security|safe)\b': 'lucide:shield-check',
    r'\b(handoff|transfer|protocol|exchange|flow)\b': 'lucide:arrow-right-left',
    r'\b(speed|fast|diagnostic|performance|quick)\b': 'lucide:zap',
    r'\b(calendar|book|schedule|meeting|time)\b': 'lucide:calendar-check',
    r'\b(decision|choose|rights|permission)\b': 'lucide:check-circle',
    r'\b(contract|agreement|rules|policy)\b': 'lucide:file-text',
    r'\b(question|ask|diagnostic|test)\b': 'lucide:help-circle',
    r'\b(comment|feedback|discussion|engage)\b': 'lucide:message-circle',
    r'\b(link|connection|reference|resource)\b': 'lucide:link',
}


def parse_markdown(content: str) -> Dict[str, Any]:
    """
    Parse markdown content to extract structure.

    Args:
        content: Raw markdown text

    Returns:
        Dict with parsed structure (sections, bullets, examples)
    """
    lines = content.strip().split('\n')

    structure = {
        'hook': [],
        'frameworks': [],
        'examples': [],
        'diagnostic': [],
        'cta': [],
        'metadata': {}
    }

    current_section = None
    buffer = []

    for line in lines:
        line = line.strip()

        # Skip metadata header
        if line.startswith('**') and line.endswith('**'):
            if ':' in line:
                key, value = line.strip('*').split(':', 1)
                structure['metadata'][key.strip().lower()] = value.strip()
                continue

        # Skip separators
        if line == '---':
            continue

        # Empty line - flush buffer if needed
        if not line:
            if buffer:
                if current_section:
                    structure[current_section].append('\n'.join(buffer))
                buffer = []
            continue

        # Detect section by content patterns

        # Hook detection (first paragraph, attention-grabbing)
        if not structure['hook'] and len(line) > 30 and '?' not in line and not line.startswith('**'):
            current_section = 'hook'
            buffer.append(line)
            continue

        # Framework detection (numbered lists, "Layer X:")
        if re.match(r'^\*\*Layer \d+:', line) or re.match(r'^\d+\.', line):
            if buffer and current_section:
                structure[current_section].append('\n'.join(buffer))
            current_section = 'frameworks'
            buffer = [line]
            continue

        # Example detection ("Example:", "Real example:", case studies)
        if re.search(r'\b(example|case)\b', line.lower()) and ':' in line:
            if buffer and current_section:
                structure[current_section].append('\n'.join(buffer))
            current_section = 'examples'
            buffer = [line]
            continue

        # Diagnostic detection (questions, "If X, then Y")
        if '?' in line or re.search(r'\bIf .+ (would|will)', line):
            if buffer and current_section:
                structure[current_section].append('\n'.join(buffer))
            current_section = 'diagnostic'
            buffer = [line]
            continue

        # CTA detection ("Your turn:", "Book a", "Drop it in")
        if re.search(r'\b(your turn|book a|drop it|link in comments|free.*session)\b', line.lower()):
            if buffer and current_section:
                structure[current_section].append('\n'.join(buffer))
            current_section = 'cta'
            buffer = [line]
            continue

        # Add to current buffer
        buffer.append(line)

    # Flush remaining buffer
    if buffer and current_section:
        structure[current_section].append('\n'.join(buffer))

    return structure


def suggest_icon(text: str, icon_style: str = 'lucide') -> str:
    """
    Suggest icon based on text content using keyword mappings.

    Args:
        text: Slide text content
        icon_style: Icon library (lucide, mdi, phosphor)

    Returns:
        Icon identifier (e.g., "lucide:users-2")
    """
    text_lower = text.lower()

    # Check keyword mappings
    for pattern, icon in ICON_MAPPINGS.items():
        if re.search(pattern, text_lower):
            # Convert to requested style if different
            if not icon.startswith(icon_style):
                icon_name = icon.split(':')[1]
                return f"{icon_style}:{icon_name}"
            return icon

    # Default icon if no match
    return f"{icon_style}:circle"


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def count_lines(text: str, max_chars_per_line: int = 60) -> int:
    """Estimate line count based on character length."""
    return (len(text) // max_chars_per_line) + 1


def chunk_content(text: str, max_lines: int = 5, max_words: int = 30, max_chars_per_line: int = 60) -> List[str]:
    """
    Chunk long content into slide-appropriate pieces.
    Enforces: Max 30 words, max 5 lines per slide.

    Args:
        text: Content to chunk
        max_lines: Maximum lines per chunk (default: 5)
        max_words: Maximum words per chunk (default: 30)
        max_chars_per_line: Maximum characters per line (default: 60)

    Returns:
        List of content chunks
    """
    # Split by sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_word_count = 0
    current_line_count = 0

    for sentence in sentences:
        sentence_words = count_words(sentence)
        sentence_lines = count_lines(sentence, max_chars_per_line)

        # Check if adding this sentence would exceed limits
        if (current_word_count + sentence_words <= max_words and
            current_line_count + sentence_lines <= max_lines):
            current_chunk.append(sentence)
            current_word_count += sentence_words
            current_line_count += sentence_lines
        else:
            # Flush current chunk and start new one
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_word_count = sentence_words
            current_line_count = sentence_lines

    # Flush remaining chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks


def optimize_slides(structure: Dict[str, Any], target_slides: int = 8, icon_style: str = 'lucide') -> Dict[str, Any]:
    """
    Optimize parsed content into slide structure.

    Args:
        structure: Parsed markdown structure
        target_slides: Target number of slides (6-10)
        icon_style: Icon library preference

    Returns:
        Dict with optimized slides and metadata
    """
    slides = []

    # Slide 1: Hook (always first)
    if structure['hook']:
        hook_text = structure['hook'][0]
        # Split hook into title and subtitle if long
        hook_parts = hook_text.split('. ', 1)
        title = hook_parts[0].strip('. ')
        subtitle = hook_parts[1] if len(hook_parts) > 1 else ''

        # Truncate if exceeds limits
        title_words = count_words(title)
        subtitle_words = count_words(subtitle)
        total_words = title_words + subtitle_words

        if total_words > 30:
            # Truncate subtitle
            subtitle = ' '.join(subtitle.split()[:max(5, 30 - title_words)])

        slides.append({
            'type': 'hook',
            'title': title,
            'content': subtitle,
            'icon': suggest_icon(hook_text, icon_style),
            'layout': 'hook',
            'notes': 'Opening slide - grab attention',
            'word_count': count_words(f"{title} {subtitle}"),
            'line_count': count_lines(f"{title}\n{subtitle}")
        })

    # Slides 2-N: Frameworks (core content)
    for framework in structure['frameworks']:
        # Parse framework layers
        lines = framework.split('\n')
        title_line = lines[0]

        # Extract framework title
        if title_line.startswith('**Layer'):
            # Multi-layer framework
            title = "Permission Architecture"  # Default, should be extracted from context
            content = []
            for line in lines:
                if line.startswith('**Layer'):
                    layer_text = line.strip('*').strip()
                    content.append(layer_text)
        else:
            # Single framework item
            title = title_line.strip('*→ ').strip()
            content = [line.strip('→ ').strip() for line in lines[1:] if line.strip()]

        # Limit to 5 bullets, truncate each to reasonable length
        content = content[:5]
        content = [' '.join(line.split()[:15]) for line in content]  # Max ~15 words per bullet

        content_text = '\n'.join(content)
        slides.append({
            'type': 'framework',
            'title': title,
            'content': content,
            'icon': suggest_icon(title, icon_style),
            'layout': 'framework',
            'notes': 'Core framework',
            'word_count': count_words(f"{title} {content_text}"),
            'line_count': len(content) + 1  # Title + bullets
        })

    # Slides: Examples (real-world stories)
    for example in structure['examples']:
        # Split into title and content
        example_parts = example.split(':', 1)
        title = example_parts[0].strip() if len(example_parts) > 1 else "REAL EXAMPLE"
        content = example_parts[1].strip() if len(example_parts) > 1 else example

        # Chunk if too long (max 30 words, 5 lines)
        content_chunks = chunk_content(content, max_lines=5, max_words=30)

        for chunk in content_chunks:
            slides.append({
                'type': 'example',
                'title': title,
                'content': chunk,
                'icon': suggest_icon(chunk, icon_style),
                'layout': 'example',
                'notes': 'Real-world credibility',
                'word_count': count_words(chunk),
                'line_count': count_lines(chunk)
            })

    # Slide: Diagnostic (key question/test)
    if structure['diagnostic']:
        diagnostic_text = structure['diagnostic'][0]
        # Truncate if too long
        if count_words(diagnostic_text) > 30:
            diagnostic_text = ' '.join(diagnostic_text.split()[:30]) + '...'

        slides.append({
            'type': 'diagnostic',
            'title': '',
            'content': diagnostic_text,
            'icon': '',  # No icon for diagnostic
            'layout': 'diagnostic',
            'notes': 'Key question or test',
            'word_count': count_words(diagnostic_text),
            'line_count': count_lines(diagnostic_text)
        })

    # Final Slide: CTA (call-to-action)
    if structure['cta']:
        cta_text = structure['cta'][0]
        # Extract question and CTA action
        cta_parts = cta_text.split('?', 1)
        question = cta_parts[0].strip() + '?' if cta_parts else cta_text
        action = cta_parts[1].strip() if len(cta_parts) > 1 else 'Link in comments'

        # Truncate if needed
        if count_words(question) > 15:
            question = ' '.join(question.split()[:15]) + '?'
        if count_words(action) > 10:
            action = ' '.join(action.split()[:10])

        slides.append({
            'type': 'cta',
            'title': question,
            'content': action,
            'icon': suggest_icon(cta_text, icon_style),
            'layout': 'cta',
            'notes': 'Call-to-action',
            'word_count': count_words(f"{question} {action}"),
            'line_count': 2  # Question + action
        })

    # Adjust to target slide count
    if len(slides) > target_slides:
        # Remove example slides first if over target
        slides = [s for s in slides if s['type'] != 'example'][:target_slides]
    elif len(slides) < target_slides - 2:
        # Add more framework/example slides if under target
        # (Implementation would expand framework bullets into separate slides)
        pass

    return {
        'slides': slides,
        'metadata': {
            'total_slides': len(slides),
            'estimated_read_time': f"{len(slides) * 20}-{len(slides) * 30} seconds",
            'mobile_optimized': True,
            'icon_style': icon_style
        }
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python slide-optimizer.py <content.md> [--target-slides N] [--icon-style lucide]", file=sys.stderr)
        sys.exit(1)

    content_file = sys.argv[1]

    # Parse arguments
    target_slides = 8
    icon_style = 'lucide'

    for i, arg in enumerate(sys.argv):
        if arg == '--target-slides' and i + 1 < len(sys.argv):
            target_slides = int(sys.argv[i + 1])
        elif arg == '--icon-style' and i + 1 < len(sys.argv):
            icon_style = sys.argv[i + 1]

    # Validate file exists
    if not Path(content_file).exists():
        print(json.dumps({
            'error': f"File not found: {content_file}"
        }))
        sys.exit(1)

    try:
        # Read content
        with open(content_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse structure
        structure = parse_markdown(content)

        # Optimize slides
        result = optimize_slides(structure, target_slides, icon_style)

        # Output JSON
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            'error': str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
