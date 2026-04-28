#!/usr/bin/env python3
"""
QIMAGE Orchestrator - Main entry point for image generation skill.

Handles all modes: generate, variations, learn, refine.
Outputs structured instructions for the Claude agent to follow,
including ready-to-paste Gemini prompts and file management commands.

Usage:
    python3 qimage.py --mode generate --concept "AI agents doing real work"
    python3 qimage.py --mode generate --concept "..." --variations 4
    python3 qimage.py --mode learn --images "img1.png,img2.png" --notes "2x engagement"
    python3 qimage.py --mode refine --concept "..." --refine "make it warmer"
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
REFERENCES_DIR = SKILL_DIR / "references"
LEARNINGS_DIR = SKILL_DIR / "learnings"
IMAGES_DIR = Path.cwd() / "images"

# ─────────────────────────────────────────────
# Style Guide
# ─────────────────────────────────────────────

def load_style_guide() -> str:
    """Load the current style guide."""
    path = REFERENCES_DIR / "style-guide.md"
    if path.exists():
        return path.read_text()
    return ""


def extract_style_preferences(style_guide: str) -> dict:
    """Extract key preferences from style guide into structured data."""
    prefs = {
        "core_aesthetic": "Real humans empowered by invisible AI",
        "human_subjects": {
            "demographics": "diverse",
            "clothing": "casual-authentic",
            "expressions": "relaxed confidence, determined focus, genuine emotion",
            "actions": "using phones, working, relaxing, tinkering"
        },
        "ai_elements": {
            "visualization": "holographic, translucent, glowing outlines",
            "relationship": "floating nearby, handling tasks, serving human",
            "colors": ["#0f3460", "#00d4ff", "#7b2ff7"]
        },
        "settings": {
            "preferred": ["beach/tropical", "home office", "outdoor cafe", "workshop"],
            "lighting": "golden hour, warm, soft, side-lit",
            "avoid": ["cold offices", "server rooms", "abstract tech", "dystopian"]
        },
        "colors": {
            "warmth": ["#ff6b35", "#ffa94d"],
            "ai_accent": ["#0f3460", "#00d4ff", "#7b2ff7"],
            "text": {"primary": "#ff6b35", "secondary": "#ffffff"},
            "avoid": ["cold grays", "neon greens", "harsh reds"]
        },
        "text_overlay": {
            "max_words": 7,
            "font_style": "bold condensed sans-serif, all caps",
            "placement": "top 1/3 or bottom 1/3",
            "color": "#ff6b35 primary, #ffffff secondary"
        },
        "composition": {
            "aspect_ratio": "16:9",
            "focal_point": "rule of thirds",
            "depth": "foreground (person), midground (AI), background (environment)"
        },
        "style_variants": {
            "primary": "Cinematic 3D (Pixar/DreamWorks-adjacent)",
            "secondary": "Photorealistic + AI overlay",
            "humor": "Comic panel (cartoon robots)"
        }
    }
    return prefs


# ─────────────────────────────────────────────
# Creative Angles for Variations
# ─────────────────────────────────────────────

CREATIVE_ANGLES = [
    {
        "name": "emotional_warmth",
        "description": "Focus on human emotion and connection",
        "modifiers": "warm lighting, genuine smile, intimate setting, personal moment",
        "scene_type": "Person in comfortable setting, AI as gentle presence"
    },
    {
        "name": "dramatic_contrast",
        "description": "Juxtapose chaos/calm or old/new",
        "modifiers": "split composition, dramatic lighting, strong shadows, visual tension",
        "scene_type": "Left side: problem/struggle. Right side: AI-assisted solution"
    },
    {
        "name": "aspirational_freedom",
        "description": "Freedom and possibility enabled by AI",
        "modifiers": "open sky, beach/nature, expansive view, golden hour, relaxed posture",
        "scene_type": "Person in paradise while AI handles the work"
    },
    {
        "name": "determined_builder",
        "description": "Human actively building with AI assistance",
        "modifiers": "workshop/garage, tools, focused expression, blue-collar setting",
        "scene_type": "Person creating/tinkering with AI augmenting their capability"
    },
    {
        "name": "discovery_wonder",
        "description": "First contact / breakthrough moment",
        "modifiers": "wide eyes, reaching hand, glowing interface, sense of awe",
        "scene_type": "Person encountering AI capability for first time"
    },
    {
        "name": "everyday_magic",
        "description": "AI seamlessly integrated into mundane life",
        "modifiers": "kitchen, commute, morning coffee, casual setting, subtle AI presence",
        "scene_type": "Ordinary scene with AI working invisibly in background"
    },
    {
        "name": "comic_narrative",
        "description": "Story told in panels with humor",
        "modifiers": "2-3 panel comic, cartoon style, speech bubbles, step labels",
        "scene_type": "Sequential panels telling a story with punchline"
    },
    {
        "name": "cinematic_epic",
        "description": "Movie-poster scale and drama",
        "modifiers": "low angle, dramatic sky, large-scale AI presence, epic proportions",
        "scene_type": "Person standing before massive AI presence, heroic framing"
    }
]


def select_angles(num_variations: int, concept: str) -> list:
    """Select the best creative angles for this concept."""
    # Always include emotional_warmth and aspirational_freedom (top performers)
    # Then fill with diverse options
    priority = ["emotional_warmth", "aspirational_freedom", "dramatic_contrast",
                "determined_builder", "discovery_wonder", "everyday_magic",
                "comic_narrative", "cinematic_epic"]

    selected = []
    for name in priority[:num_variations]:
        angle = next((a for a in CREATIVE_ANGLES if a["name"] == name), None)
        if angle:
            selected.append(angle)
    return selected


# ─────────────────────────────────────────────
# Prompt Builder
# ─────────────────────────────────────────────

def build_prompt(concept: str, prefs: dict, text_overlay: str = None,
                 aspect_ratio: str = "16:9", angle: dict = None) -> str:
    """Build an optimized Gemini image prompt using Nano Banana Pro techniques."""

    # Determine style based on angle
    if angle and angle["name"] == "comic_narrative":
        style_desc = "Clean cartoon illustration, distinct panels, simple expressive characters"
        setting = angle.get("scene_type", "Sequential comic panels")
    else:
        style_desc = "Cinematic 3D illustration in Pixar/DreamWorks style with rich textures and volumetric lighting"
        setting = angle.get("scene_type", "Real-world setting with AI presence") if angle else "Real-world setting with AI presence"

    # Build the prompt using Nano Banana Pro principles:
    # - Describe scenes, don't list keywords
    # - Use CAPS for critical instructions
    # - Specify hex colors
    # - Structure with markdown

    prompt_parts = []

    # Scene description (narrative style)
    prompt_parts.append(f"{style_desc} for a social media article about: {concept}.")
    prompt_parts.append("")

    if angle:
        prompt_parts.append(f"Creative direction: {angle['description']}.")
        prompt_parts.append(f"Scene concept: {setting}.")
        prompt_parts.append("")

    # Visual elements
    prompt_parts.append("Visual elements:")
    prompt_parts.append("- MUST include a realistic, diverse human subject with genuine facial expression and authentic body language")
    prompt_parts.append("- The person should be DOING something (working, relaxing, creating, thinking) — NOT just standing or posing")
    prompt_parts.append("- AI/technology appears as holographic, translucent, glowing elements — ethereal and magical, NOT industrial or threatening")
    prompt_parts.append("- AI element floats near or around the person, serving them — the human is ALWAYS the protagonist")

    if angle:
        prompt_parts.append(f"- Mood modifiers: {angle['modifiers']}")

    prompt_parts.append("")

    # Color and lighting
    prompt_parts.append("Color and lighting:")
    prompt_parts.append("- Warm color palette: sunset oranges, golden yellows, amber tones")
    prompt_parts.append("- AI elements use electric blue (#0f3460), cyan (#00d4ff), or soft purple (#7b2ff7)")
    prompt_parts.append("- Golden hour lighting — warm, soft, side-lit")
    prompt_parts.append("- NEVER use cold grays, harsh reds, or all-blue palettes")
    prompt_parts.append("")

    # Text overlay
    if text_overlay:
        prompt_parts.append("Text overlay:")
        prompt_parts.append(f'- Text MUST read EXACTLY: "{text_overlay}"')
        prompt_parts.append("- Bold condensed sans-serif font, ALL CAPS")
        prompt_parts.append(f"- Color: Sparkry orange (#ff6b35) or white (#ffffff)")
        prompt_parts.append("- Position: top third of image")
        prompt_parts.append("- Slight text shadow for readability")
        prompt_parts.append("")

    # Composition
    prompt_parts.append("Composition and technical specs:")
    prompt_parts.append(f"- Aspect ratio: {aspect_ratio}")
    prompt_parts.append("- Rule of thirds — human subject on one side, AI element on the other")
    prompt_parts.append("- Cinematic depth: foreground (person), midground (AI/tech), background (environment)")

    if not text_overlay:
        prompt_parts.append("- Leave negative space at top for potential text overlay later")

    prompt_parts.append("")

    # What to avoid
    prompt_parts.append("MUST NOT include:")
    prompt_parts.append("- Stock photo aesthetic or staged corporate poses")
    prompt_parts.append("- Uncanny valley faces (waxy skin, dead eyes, too-perfect features)")
    prompt_parts.append("- Dark, dystopian, or threatening AI imagery")
    prompt_parts.append("- Abstract technology backgrounds (circuit boards, code rain, binary)")
    prompt_parts.append("- More than 7 words of text overlay")

    return "\n".join(prompt_parts)


def build_refine_prompt(original_prompt: str, refinement: str) -> str:
    """Modify an existing prompt based on user feedback."""
    return f"""REVISED VERSION of previous image. Apply these changes:

{refinement}

Original prompt (modify based on feedback above):
{original_prompt}

Keep all technical specs and brand guidelines from original. Only change what the feedback requests."""


# ─────────────────────────────────────────────
# File Management
# ─────────────────────────────────────────────

def generate_filename(concept: str, variant: int = 0) -> str:
    """Generate a filename from concept and date."""
    today = date.today().isoformat()

    # Slugify the concept
    slug = concept.lower()
    # Remove common words
    for word in ["the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                 "to", "for", "of", "with", "about", "my", "your", "our"]:
        slug = slug.replace(f" {word} ", " ")

    # Clean up
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = "-".join(slug.split())[:50]  # Max 50 chars

    if variant > 0:
        return f"{today}-{slug}-v{variant}.png"
    return f"{today}-{slug}.png"


# ─────────────────────────────────────────────
# Image Analysis (Learn Mode)
# ─────────────────────────────────────────────

def analyze_images_prompt(image_paths: list, notes: str = "") -> str:
    """Generate analysis instructions for the Claude agent."""
    analysis = []
    analysis.append("## Image Analysis Instructions")
    analysis.append("")
    analysis.append("Analyze each image below for these attributes:")
    analysis.append("")
    analysis.append("1. **Color palette**: Dominant colors, accent colors, background")
    analysis.append("2. **Composition**: Layout, focal point, use of space")
    analysis.append("3. **Human subjects**: Demographics, clothing, expression, action")
    analysis.append("4. **AI/Tech elements**: How technology is visualized")
    analysis.append("5. **Setting**: Environment, lighting, time of day")
    analysis.append("6. **Text treatment**: Amount, font, placement, color")
    analysis.append("7. **Style**: 3D, photorealistic, illustrated, comic")
    analysis.append("8. **Mood/emotion**: What feeling does it evoke?")
    analysis.append("9. **Effectiveness**: What makes it work? What draws the eye?")
    analysis.append("")

    for i, path in enumerate(image_paths, 1):
        analysis.append(f"### Image {i}: `{path}`")
        analysis.append(f"Read this image file and analyze using the attributes above.")
        analysis.append("")

    if notes:
        analysis.append(f"### User notes: {notes}")
        analysis.append("")

    analysis.append("### After Analysis")
    analysis.append("")
    analysis.append("Update the style guide at:")
    analysis.append(f"`{REFERENCES_DIR / 'style-guide.md'}`")
    analysis.append("")
    analysis.append("Add new patterns, strengthen confirmed preferences, note contradictions.")

    return "\n".join(analysis)


# ─────────────────────────────────────────────
# Main Output Generator
# ─────────────────────────────────────────────

def generate_output(args) -> dict:
    """Generate the full output for the Claude agent."""
    style_guide = load_style_guide()
    prefs = extract_style_preferences(style_guide)

    output = {
        "mode": args.mode,
        "prompts": [],
        "files": [],
        "instructions": []
    }

    if args.mode == "learn":
        images = [p.strip() for p in args.images.split(",")]
        output["instructions"].append(analyze_images_prompt(images, args.notes or ""))
        return output

    concept = args.concept
    if not concept:
        output["instructions"].append("ERROR: --concept is required for generate/refine modes")
        return output

    num_variations = args.variations or 1

    if args.mode == "refine" and args.refine:
        # Build one refined prompt
        # Load last prompt from learnings if available
        last_prompt_file = LEARNINGS_DIR / "last-prompt.txt"
        original = last_prompt_file.read_text() if last_prompt_file.exists() else f"Image about: {concept}"
        prompt = build_refine_prompt(original, args.refine)
        filename = generate_filename(concept)
        output["prompts"].append({
            "id": 1,
            "angle": "refinement",
            "prompt": prompt,
            "filename": filename,
            "filepath": str(IMAGES_DIR / filename)
        })
    elif num_variations == 1:
        # Single generation - use the best default angle
        prompt = build_prompt(concept, prefs, args.text, args.aspect_ratio or "16:9")
        filename = generate_filename(concept)
        output["prompts"].append({
            "id": 1,
            "angle": "default (emotional_warmth + aspirational_freedom blend)",
            "prompt": prompt,
            "filename": filename,
            "filepath": str(IMAGES_DIR / filename)
        })
    else:
        # Multiple variations with different creative angles
        angles = select_angles(num_variations, concept)
        for i, angle in enumerate(angles, 1):
            prompt = build_prompt(concept, prefs, args.text, args.aspect_ratio or "16:9", angle)
            filename = generate_filename(concept, i)
            output["prompts"].append({
                "id": i,
                "angle": f"{angle['name']}: {angle['description']}",
                "prompt": prompt,
                "filename": filename,
                "filepath": str(IMAGES_DIR / filename)
            })

    # Save last prompt for potential refinement
    if output["prompts"]:
        LEARNINGS_DIR.mkdir(exist_ok=True)
        last_prompt_file = LEARNINGS_DIR / "last-prompt.txt"
        last_prompt_file.write_text(output["prompts"][0]["prompt"])

    return output


def format_output(output: dict) -> str:
    """Format output as human-readable instructions for the agent."""
    lines = []
    lines.append(f"# QIMAGE Output — Mode: {output['mode']}")
    lines.append("")

    if output.get("instructions"):
        for instruction in output["instructions"]:
            lines.append(instruction)
        return "\n".join(lines)

    lines.append(f"## {len(output['prompts'])} Prompt(s) to Generate")
    lines.append("")

    for p in output["prompts"]:
        lines.append(f"### Prompt {p['id']} — Angle: {p['angle']}")
        lines.append("")
        lines.append("**Copy-paste this prompt into Gemini:**")
        lines.append("")
        lines.append("```")
        lines.append(p["prompt"])
        lines.append("```")
        lines.append("")
        lines.append(f"**Save as:** `{p['filepath']}`")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## File Management")
    lines.append("")
    for p in output["prompts"]:
        lines.append(f"```bash")
        lines.append(f"mv ~/Downloads/<downloaded-image> \"{p['filepath']}\"")
        lines.append(f"```")
    lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QIMAGE Orchestrator")
    parser.add_argument("--mode", choices=["generate", "learn", "refine"],
                        default="generate", help="Operation mode")
    parser.add_argument("--concept", type=str, help="Image concept/description")
    parser.add_argument("--variations", type=int, help="Number of variations (default: 1)")
    parser.add_argument("--text", type=str, help="Text overlay (max 7 words)")
    parser.add_argument("--aspect-ratio", type=str, default="16:9",
                        help="Aspect ratio (default: 16:9)")
    parser.add_argument("--images", type=str, help="Comma-separated image paths (learn mode)")
    parser.add_argument("--notes", type=str, help="Notes about images (learn mode)")
    parser.add_argument("--refine", type=str, help="Refinement feedback (refine mode)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of markdown")

    args = parser.parse_args()

    output = generate_output(args)

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(format_output(output))


if __name__ == "__main__":
    main()
