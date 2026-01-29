#!/usr/bin/env python3
"""
Pattern Selector

Maps validated framework to infographic pattern (timeline/process/hierarchy/pillars/cycle).
Determines panel structure based on framework type and target channel.

Usage:
    python pattern-selector.py <framework-json> --channel linkedin_carousel

Output (JSON):
    {
      "pattern": "vertical_process",
      "rationale": "Sequential steps best shown as vertical flow",
      "structure": {
        "panels": [{id, role, framework_element_ids, approx_content_density}]
      },
      "title_options": ["Option 1", "Option 2"],
      "cta_options": ["Read the full article"]
    }
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


PATTERN_MAPPINGS = {
    "steps": ["vertical_process", "timeline", "stacked_steps"],
    "pillars": ["pillars", "columns", "foundation_blocks"],
    "layers": ["stacked_layers", "pyramid", "elevation_chart"],
    "principles": ["pillars", "dashboard", "grid_layout"],
    "stages": ["timeline", "horizontal_process", "cycle"],
    "loops": ["cycle", "circular_flow", "orbit_model"]
}

CHANNEL_CONSTRAINTS = {
    "linkedin_carousel": {
        "aspect_ratio": "1:1",
        "max_panels": 10,
        "density_preference": "medium"
    },
    "pinterest_tall": {
        "aspect_ratio": "2:3",
        "max_panels": 15,
        "density_preference": "high"
    },
    "blog_hero": {
        "aspect_ratio": "16:9",
        "max_panels": 8,
        "density_preference": "low"
    },
    "generic_vertical": {
        "aspect_ratio": "9:16",
        "max_panels": 12,
        "density_preference": "medium"
    }
}


def select_pattern(framework_type: str, element_count: int, channel: str) -> Dict[str, Any]:
    """
    Select best infographic pattern for framework type and channel.

    Args:
        framework_type: Type of framework (steps, pillars, etc.)
        element_count: Number of framework elements
        channel: Target channel

    Returns:
        Dict with pattern, rationale
    """
    # Get possible patterns for framework type
    possible_patterns = PATTERN_MAPPINGS.get(framework_type, ["dashboard"])

    # Get channel constraints
    constraints = CHANNEL_CONSTRAINTS.get(channel, CHANNEL_CONSTRAINTS["generic_vertical"])

    # Select pattern based on element count and channel
    if element_count <= 4:
        # Fewer elements: can use spacious layouts
        if "pillars" in possible_patterns:
            pattern = "pillars"
            rationale = f"{element_count} {framework_type} work well as side-by-side pillars"
        elif "dashboard" in possible_patterns:
            pattern = "dashboard"
            rationale = f"{element_count} {framework_type} fit in grid layout"
        else:
            pattern = possible_patterns[0]
            rationale = f"Standard {pattern} layout for {element_count} {framework_type}"

    elif element_count <= 7:
        # Medium count: vertical flow works well
        if "vertical_process" in possible_patterns:
            pattern = "vertical_process"
            rationale = f"{element_count} {framework_type} flow vertically with good spacing"
        elif "stacked_layers" in possible_patterns:
            pattern = "stacked_layers"
            rationale = f"{element_count} {framework_type} stack vertically showing hierarchy"
        else:
            pattern = possible_patterns[0]
            rationale = f"Standard {pattern} layout for {element_count} {framework_type}"

    else:
        # Many elements: compact layouts
        if "timeline" in possible_patterns:
            pattern = "timeline"
            rationale = f"{element_count} {framework_type} work as compact timeline"
        elif "cycle" in possible_patterns and element_count <= 10:
            pattern = "cycle"
            rationale = f"{element_count} {framework_type} fit in circular layout"
        else:
            pattern = possible_patterns[0]
            rationale = f"Efficient {pattern} layout for {element_count} {framework_type}"

    # Adjust for channel constraints
    if constraints["max_panels"] < element_count + 2:  # +2 for hero and summary
        rationale += f". Optimized for {channel} panel limits."

    return {
        "pattern": pattern,
        "rationale": rationale
    }


def generate_panel_structure(framework: Dict[str, Any], pattern: str, channel: str) -> List[Dict[str, Any]]:
    """
    Generate panel structure based on pattern and framework.

    Args:
        framework: Validated framework
        pattern: Selected pattern
        channel: Target channel

    Returns:
        List of panel dicts
    """
    panels = []
    elements = framework["elements"]
    element_count = len(elements)

    # Hero panel (always first)
    panels.append({
        "id": "hero",
        "role": "hero",
        "framework_element_ids": [],
        "approx_content_density": "low"
    })

    # Element panels (pattern-specific layout)
    if pattern in ["pillars", "columns", "foundation_blocks"]:
        # One panel per element (side-by-side if space allows)
        for element in elements:
            panels.append({
                "id": element["id"],
                "role": "pillar",
                "framework_element_ids": [element["id"]],
                "approx_content_density": "medium"
            })

    elif pattern in ["vertical_process", "stacked_steps", "stacked_layers"]:
        # One panel per element (vertical stack)
        for element in elements:
            panels.append({
                "id": element["id"],
                "role": "step",
                "framework_element_ids": [element["id"]],
                "approx_content_density": "medium"
            })

    elif pattern == "timeline":
        # Compact: 2 elements per panel if many elements
        if element_count > 6:
            for i in range(0, element_count, 2):
                batch = elements[i:i+2]
                panels.append({
                    "id": f"timeline_panel_{i//2 + 1}",
                    "role": "timeline_segment",
                    "framework_element_ids": [el["id"] for el in batch],
                    "approx_content_density": "high"
                })
        else:
            for element in elements:
                panels.append({
                    "id": element["id"],
                    "role": "timeline_item",
                    "framework_element_ids": [element["id"]],
                    "approx_content_density": "medium"
                })

    elif pattern in ["cycle", "circular_flow", "orbit_model"]:
        # Overview panel + cycle visualization
        panels.append({
            "id": "cycle_overview",
            "role": "overview",
            "framework_element_ids": [el["id"] for el in elements],
            "approx_content_density": "high"
        })

    elif pattern == "dashboard":
        # Grid layout: 2-3 elements per panel
        batch_size = 2 if element_count <= 6 else 3
        for i in range(0, element_count, batch_size):
            batch = elements[i:i+batch_size]
            panels.append({
                "id": f"dashboard_panel_{i//batch_size + 1}",
                "role": "grid_section",
                "framework_element_ids": [el["id"] for el in batch],
                "approx_content_density": "high"
            })

    else:
        # Default: one panel per element
        for element in elements:
            panels.append({
                "id": element["id"],
                "role": "element",
                "framework_element_ids": [element["id"]],
                "approx_content_density": "medium"
            })

    # Summary/CTA panel (always last)
    panels.append({
        "id": "summary",
        "role": "summary",
        "framework_element_ids": [],
        "approx_content_density": "low"
    })

    return panels


def generate_title_options(framework: Dict[str, Any]) -> List[str]:
    """
    Generate 2-3 title options for infographic.

    Args:
        framework: Validated framework

    Returns:
        List of title strings
    """
    name = framework["name"]
    ftype = framework["type"]
    count = len(framework["elements"])

    options = [
        name,  # Use explicit name
        f"Your {ftype.capitalize()} Stack: {count} {ftype.capitalize()}",
        f"{count} {ftype.capitalize()} to Transform Your [Topic]"
    ]

    return options[:3]


def generate_cta_options(framework: Dict[str, Any]) -> List[str]:
    """
    Generate CTA options for infographic.

    Args:
        framework: Validated framework

    Returns:
        List of CTA strings
    """
    return [
        "Read the full article →",
        "Learn more at [URL]",
        "Apply this framework today"
    ]


def select_infographic_strategy(framework: Dict[str, Any], channel: str) -> Dict[str, Any]:
    """
    Main strategy selection function.

    Args:
        framework: Validated framework
        channel: Target channel

    Returns:
        Complete infographic strategy
    """
    framework_type = framework["type"]
    element_count = len(framework["elements"])

    # Select pattern
    pattern_result = select_pattern(framework_type, element_count, channel)

    # Generate panel structure
    panels = generate_panel_structure(framework, pattern_result["pattern"], channel)

    # Generate title options
    title_options = generate_title_options(framework)

    # Generate CTA options
    cta_options = generate_cta_options(framework)

    return {
        "pattern": pattern_result["pattern"],
        "rationale": pattern_result["rationale"],
        "structure": {
            "panels": panels
        },
        "title_options": title_options,
        "subtitle_options": [
            framework.get("supporting_context", ""),
            f"A practical guide to {framework_type}"
        ],
        "cta_options": cta_options
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python pattern-selector.py <framework-json> [--channel CHANNEL]", file=sys.stderr)
        sys.exit(1)

    framework_file = sys.argv[1]
    channel = "generic_vertical"

    # Parse channel argument
    if len(sys.argv) > 2 and sys.argv[2] == '--channel':
        channel = sys.argv[3] if len(sys.argv) > 3 else channel

    if not Path(framework_file).exists():
        print(json.dumps({
            "error": f"Framework file not found: {framework_file}"
        }))
        sys.exit(1)

    try:
        # Load framework
        with open(framework_file, 'r', encoding='utf-8') as f:
            framework_data = json.load(f)

        if "framework_validated" in framework_data:
            framework = framework_data["framework_validated"]
        elif "framework" in framework_data:
            framework = framework_data["framework"]
        else:
            print(json.dumps({
                "error": "Invalid framework JSON: missing 'framework' or 'framework_validated' key"
            }))
            sys.exit(1)

        # Select strategy
        result = select_infographic_strategy(framework, channel)

        # Validate: all framework elements mapped to panels
        all_element_ids = {el["id"] for el in framework["elements"]}
        mapped_element_ids = set()
        for panel in result["structure"]["panels"]:
            mapped_element_ids.update(panel["framework_element_ids"])

        if not all_element_ids.issubset(mapped_element_ids):
            unmapped = all_element_ids - mapped_element_ids
            print(json.dumps({
                "error": f"Some framework elements not mapped to panels: {unmapped}"
            }))
            sys.exit(1)

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
