#!/usr/bin/env python3
"""
Tool Stub Generator - Generate Python tool stubs with boilerplate

Generate tool stubs with standard structure, error handling, and optional tests.

Usage:
    python tool-stub-generator.py --name "tool-name" --skill-dir "skills/my-skill"

Output:
    Creates Python tool stub in scripts/ directory
"""

import json
import sys
import argparse
from pathlib import Path


TOOL_TEMPLATE = '''#!/usr/bin/env python3
"""
{name_title} - {description}

{long_description}

Usage:
    python {filename} <{input_name}> [options]

Output ({output_format}):
    {{
      "result": "...",
      "metadata": {{}}
    }}
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any


def process(input_file: Path) -> Dict[str, Any]:
    """
    Process input and generate result.

    Args:
        input_file: Path to input file

    Returns:
        Processing result
    """
    # TODO: Implement processing logic
    result = {{
        "status": "success",
        "message": "Processing complete",
        "data": {{}}
    }}

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python {filename} <{input_name}>", file=sys.stderr)
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(json.dumps({{
            "error": f"File not found: {{input_file}}"
        }}))
        sys.exit(1)

    try:
        result = process(input_file)
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({{
            "error": str(e)
        }}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''


def generate_tool_stub(
    name: str,
    description: str,
    skill_dir: Path,
    input_name: str = "input",
    output_format: str = "JSON",
    generate_test: bool = False
) -> dict:
    """
    Generate a tool stub with standard structure.

    Args:
        name: Tool name (e.g., "coverage-analyzer")
        description: Brief description
        skill_dir: Skill directory path
        input_name: Input parameter name
        output_format: Output format (JSON, HTML, etc.)
        generate_test: Whether to generate test file

    Returns:
        Generation result
    """
    # Convert name to filename
    filename = f"{name}.py"
    name_title = name.replace('-', ' ').replace('_', ' ').title()

    # Create scripts directory
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Output path
    output_path = scripts_dir / filename

    # Long description (can be expanded)
    long_description = f"Processes {input_name} and generates {output_format.lower()} output."

    # Render template
    content = TOOL_TEMPLATE.format(
        name_title=name_title,
        description=description,
        long_description=long_description,
        filename=filename,
        input_name=input_name,
        output_format=output_format
    )

    # Write tool stub
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Make executable
    output_path.chmod(0o755)

    files_created = [str(output_path)]

    # Generate test if requested
    if generate_test:
        test_file = generate_test_file(name, skill_dir)
        files_created.append(str(test_file))

    return {
        "tool_created": {
            "name": name,
            "file": str(output_path),
            "test_file": files_created[1] if generate_test else None
        },
        "next_steps": [
            f"Implement logic in {output_path}",
            f"Run tests: python {files_created[1]}" if generate_test else "Create tests"
        ]
    }


def generate_test_file(tool_name: str, skill_dir: Path) -> Path:
    """Generate test file for tool."""
    test_template = f'''#!/usr/bin/env python3
"""
Tests for {tool_name}.py
"""

import unittest
import json
import tempfile
from pathlib import Path
import sys

# Import tool
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from {tool_name.replace('-', '_')} import process


class Test{tool_name.replace('-', '').replace('_', '').title()}(unittest.TestCase):
    """Test cases for {tool_name}."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        # Create temp input file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump({{"test": "data"}}, f)
            temp_file = Path(f.name)

        try:
            result = process(temp_file)
            self.assertIsNotNone(result)
            self.assertEqual(result.get('status'), 'success')
        finally:
            temp_file.unlink()

    def test_error_handling(self):
        """Test error handling with invalid input."""
        # Test with non-existent file should be handled in main()
        pass


if __name__ == '__main__':
    unittest.main()
'''

    tests_dir = skill_dir / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    test_file = tests_dir / f"test_{tool_name.replace('-', '_')}.py"

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_template)

    test_file.chmod(0o755)

    return test_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate Python tool stub"
    )

    parser.add_argument("--name", required=True, help="Tool name (e.g., coverage-analyzer)")
    parser.add_argument("--description", default="Process data", help="Brief description")
    parser.add_argument("--skill-dir", required=True, help="Skill directory path")
    parser.add_argument("--input", default="input", help="Input parameter name")
    parser.add_argument("--output-format", default="JSON", help="Output format")
    parser.add_argument("--generate-test", action="store_true", help="Generate test file")

    args = parser.parse_args()

    try:
        result = generate_tool_stub(
            name=args.name,
            description=args.description,
            skill_dir=Path(args.skill_dir),
            input_name=args.input,
            output_format=args.output_format,
            generate_test=args.generate_test
        )

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(json.dumps({
            "error": str(e)
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
