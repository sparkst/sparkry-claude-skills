#!/usr/bin/env python3
"""
Persona Schema Generator - Generate persona schemas from requirements

Generates YAML persona schemas with layers, traits, vocabulary, and validation criteria.

Usage:
    python persona-schema-gen.py --input requirements.md --output persona.yaml

Output (YAML file + JSON summary):
    {
      "persona_name": "strategic_advisor",
      "layers": [
        {
          "layer": "base_voice",
          "traits": ["direct", "systems_thinking", "proof_of_work"],
          "vocabulary": ["scale", "leverage", "iterate"],
          "sentence_structure": "active_voice_present_tense"
        },
        {
          "layer": "content_type",
          "type": "strategic",
          "tone": "analytical",
          "structure": "thesis_evidence_conclusion"
        },
        {
          "layer": "platform",
          "platform": "linkedin",
          "constraints": {
            "hook_words": 25,
            "max_length": 2000,
            "formality": "professional_conversational"
          }
        }
      ],
      "fallback_strategy": "default_to_base_voice",
      "validation_criteria": [
        "No corporate jargon",
        "Active voice >80%",
        "Concrete examples required"
      ]
    }
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List


def extract_persona_name(requirements: str) -> str:
    """
    Extract persona name from requirements.

    Returns:
        Persona name string
    """
    # Stub implementation - in production, this would:
    # 1. Parse requirements for persona name
    # 2. Default to descriptive name if not found

    return "strategic_advisor"


def extract_layers(requirements: str) -> List[Dict[str, Any]]:
    """
    Extract persona layers from requirements.

    Returns:
        List of layer dicts
    """
    # Stub implementation - in production, this would:
    # 1. Parse requirements for layer specifications
    # 2. Extract traits, vocabulary, structure per layer

    return [
        {
            "layer": "base_voice",
            "traits": ["direct", "systems_thinking", "proof_of_work"],
            "vocabulary": ["scale", "leverage", "iterate"],
            "sentence_structure": "active_voice_present_tense"
        },
        {
            "layer": "content_type",
            "type": "strategic",
            "tone": "analytical",
            "structure": "thesis_evidence_conclusion"
        },
        {
            "layer": "platform",
            "platform": "linkedin",
            "constraints": {
                "hook_words": 25,
                "max_length": 2000,
                "formality": "professional_conversational"
            }
        }
    ]


def extract_fallback_strategy(requirements: str) -> str:
    """
    Extract fallback strategy from requirements.

    Returns:
        Fallback strategy string
    """
    # Stub implementation - in production, this would:
    # 1. Parse requirements for fallback strategy
    # 2. Default to base_voice if not specified

    return "default_to_base_voice"


def extract_validation_criteria(requirements: str) -> List[str]:
    """
    Extract validation criteria from requirements.

    Returns:
        List of validation criteria strings
    """
    # Stub implementation - in production, this would:
    # 1. Parse requirements for validation rules
    # 2. Generate criteria from persona traits

    return [
        "No corporate jargon",
        "Active voice >80%",
        "Concrete examples required"
    ]


def generate_yaml(schema: Dict[str, Any]) -> str:
    """
    Generate YAML from schema dict.

    Returns:
        YAML string
    """
    # Stub implementation - in production, this would:
    # 1. Convert schema dict to YAML format
    # 2. Preserve structure and indentation

    yaml_output = f"""---
name: {schema['persona_name']}
description: Auto-generated persona schema
version: 1.0.0
fallback_strategy: {schema['fallback_strategy']}

layers:
"""

    for layer in schema['layers']:
        yaml_output += f"  - layer: {layer['layer']}\n"
        for key, value in layer.items():
            if key != 'layer':
                if isinstance(value, list):
                    yaml_output += f"    {key}:\n"
                    for item in value:
                        yaml_output += f"      - {item}\n"
                elif isinstance(value, dict):
                    yaml_output += f"    {key}:\n"
                    for k, v in value.items():
                        yaml_output += f"      {k}: {v}\n"
                else:
                    yaml_output += f"    {key}: {value}\n"

    yaml_output += "\nvalidation_criteria:\n"
    for criterion in schema['validation_criteria']:
        yaml_output += f"  - {criterion}\n"

    return yaml_output


def main():
    parser = argparse.ArgumentParser(description="Generate persona schemas from requirements")
    parser.add_argument("--input", required=True, help="Path to requirements file")
    parser.add_argument("--output", required=True, help="Path to output YAML file")

    args = parser.parse_args()

    try:
        input_path = Path(args.input)

        # Read requirements
        requirements = ""
        if input_path.exists():
            with open(input_path, 'r', encoding='utf-8') as f:
                requirements = f.read()

        # Extract persona components
        persona_name = extract_persona_name(requirements)
        layers = extract_layers(requirements)
        fallback_strategy = extract_fallback_strategy(requirements)
        validation_criteria = extract_validation_criteria(requirements)

        # Build schema
        schema = {
            "persona_name": persona_name,
            "layers": layers,
            "fallback_strategy": fallback_strategy,
            "validation_criteria": validation_criteria
        }

        # Generate YAML
        yaml_content = generate_yaml(schema)

        # Write YAML file
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        # Print JSON summary to stdout
        result = {
            **schema,
            "output_file": str(output_path),
            "status": "success"
        }

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
