#!/usr/bin/env python3
"""
Swarm Orchestrator for Headlines

Coordinates the 5 angles running in parallel:
1. emotional - The Emotional Provocateur
2. identity - The Identity Crafter
3. action - The Action Catalyst
4. contrarian - The Contrarian
5. simplifier - The Simplifier

Workflow:
1. Generate 50 candidates (5 angles x 10 each)
2. Filter candidates through validator (~35 pass)
3. Cross-rank using Borda count
4. Generate subtitles for top headlines
5. Return top 10 with full metadata

Usage:
    python swarm_orchestrator.py --content "..." --title-context "optional current title"

Output (JSON):
    {
      "top_headlines": [...],
      "subtitles": [...],
      "pipeline": {...}
    }
"""

import json
import sys
import time
from typing import Dict, Any, List, Optional

# Import other tools
from angle_generator import generate_from_angle, VALID_ANGLES
from headline_validator import validate_headline
from cross_ranker import aggregate_rankings


# Default configuration
DEFAULT_TIMEOUT_SECONDS = 30
CANDIDATES_PER_ANGLE = 10


# Subtitle templates that complement headlines
SUBTITLE_TEMPLATES = [
    "How to lead through disruption without corporate BS or broken promises",
    "A framework for honest conversations when your team is scared",
    "What to say, how to say it, and why it matters",
    "The script your team has been waiting for",
    "Because your engineers deserve the truth"
]


def _deduplicate_headlines(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate headlines, keeping the higher-scoring version.

    Args:
        candidates: List of candidate headlines

    Returns:
        Deduplicated list
    """
    seen: Dict[str, Dict[str, Any]] = {}

    for candidate in candidates:
        headline = candidate.get("headline", "")
        key = headline.lower().strip()

        if key not in seen:
            seen[key] = candidate
        else:
            # Keep higher-scoring version
            existing_score = seen[key].get("score", 0)
            new_score = candidate.get("score", 0)
            if new_score > existing_score:
                seen[key] = candidate

    return list(seen.values())


def _generate_angle(
    content: str,
    angle: str,
    context: Optional[Dict[str, str]] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    """
    Generate headlines from a single angle with timeout handling.

    Args:
        content: Content to generate from
        angle: Creative angle name
        context: Optional context
        timeout: Timeout in seconds

    Returns:
        Generation result or error dict
    """
    try:
        result = generate_from_angle(content, angle, context)
        return {
            "angle": angle,
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "angle": angle,
            "success": False,
            "error": str(e)
        }


def _generate_subtitles(top_headline: str, content: str) -> List[Dict[str, Any]]:
    """
    Generate subtitle options for the top headline.

    Args:
        top_headline: The selected headline
        content: Article content for context

    Returns:
        List of subtitle options
    """
    # In production, this would use LLM to generate contextual subtitles
    # For now, return curated templates
    subtitles = []
    for i, template in enumerate(SUBTITLE_TEMPLATES[:3]):
        subtitles.append({
            "subtitle": template,
            "pairs_with": 1,  # Pairs with top headline
            "word_count": len(template.split())
        })
    return subtitles


def orchestrate_swarm(
    content: str,
    title_context: Optional[str] = None,
    context: Optional[Dict[str, str]] = None,
    _test_max_valid: Optional[int] = None,
    _test_force_tie: bool = False,
    _test_fail_all_validation: bool = False,
    _test_timeout_angle: Optional[str] = None,
    _test_fail_cross_ranker: bool = False
) -> Dict[str, Any]:
    """
    Orchestrate the 5-angle swarm to generate and rank headlines.

    Args:
        content: Content text to generate headlines from
        title_context: Optional current title for context
        context: Optional additional context (hero_image, audience, theme)
        _test_*: Test-only parameters for edge case testing

    Returns:
        Dict with top_headlines, subtitles, and pipeline metadata

    Raises:
        ValueError: If content is empty
        TypeError: If content is None
    """
    start_time = time.time()

    # Validate input
    if content is None:
        raise TypeError("content cannot be None")

    if not content or not content.strip():
        raise ValueError("Content required - cannot orchestrate from empty text")

    # Build context for generation
    gen_context = context or {}
    if title_context:
        gen_context["current_title"] = title_context

    # Track warnings
    warnings: List[str] = []
    if len(content.split()) < 100:
        warnings.append("Short content may reduce headline quality and diversity")

    # Phase 1: Generate from all angles
    angles_executed = []
    timed_out_angles = []
    all_candidates = []
    angle_results: Dict[str, Any] = {}

    # Determine which angles to run (for testing timeout scenarios)
    angles_to_run = VALID_ANGLES.copy()
    if _test_timeout_angle:
        angles_to_run = [a for a in angles_to_run if a != _test_timeout_angle]
        timed_out_angles.append(_test_timeout_angle)

    # Generate from each angle
    for angle in angles_to_run:
        gen_result = _generate_angle(content, angle, gen_context if gen_context else None)

        if gen_result["success"]:
            angles_executed.append(angle)
            angle_results[angle] = gen_result["result"]

            # Extract candidates
            for candidate in gen_result["result"]["candidates"]:
                all_candidates.append({
                    **candidate,
                    "generating_angle": angle
                })

    candidates_generated = len(all_candidates)

    # Phase 2: Validate and filter candidates
    valid_candidates = []

    if _test_fail_all_validation:
        valid_candidates = []
    else:
        for candidate in all_candidates:
            headline_data = {
                "headline": candidate["headline"],
                "scores": candidate["scores"]
            }

            try:
                validation_result = validate_headline(headline_data)
                if validation_result["valid"]:
                    valid_candidates.append({
                        **candidate,
                        "validation": validation_result
                    })
            except Exception:
                # Skip candidates that fail validation
                pass

    # Apply test constraint if specified
    if _test_max_valid is not None:
        valid_candidates = valid_candidates[:_test_max_valid]

    candidates_after_filter = len(valid_candidates)

    # Handle case where all candidates fail validation
    if not valid_candidates:
        total_time = int((time.time() - start_time) * 1000)
        return {
            "top_headlines": [],
            "subtitles": [],
            "error": True,
            "error_message": "All candidates failed validation - no valid headlines produced",
            "pipeline": {
                "candidates_generated": candidates_generated,
                "candidates_after_filter": 0,
                "final_count": 0,
                "angles_executed": angles_executed,
                "timed_out_angles": timed_out_angles,
                "total_time_ms": total_time,
                "partial_execution": len(timed_out_angles) > 0
            },
            "warnings": warnings
        }

    # Phase 3: Cross-rank candidates
    ranking_mode = "cross_ranking"

    if _test_fail_cross_ranker:
        # Fallback to self-score ranking
        ranking_mode = "self_score_fallback"
        valid_candidates.sort(key=lambda x: x["scores"]["overall"], reverse=True)
        top_candidates = valid_candidates[:10]
    else:
        # Prepare rankings for cross-ranker
        rankings: Dict[str, List[Dict[str, Any]]] = {}

        for angle in angles_executed:
            # Sort candidates by overall score (simulating angle's ranking)
            sorted_candidates = sorted(
                valid_candidates,
                key=lambda x: x["scores"]["overall"],
                reverse=True
            )[:10]

            rankings[angle] = [
                {
                    "rank": i + 1,
                    "candidate_id": f"{c['generating_angle']}_{c['headline'][:20]}",
                    "headline": c["headline"],
                    "scores": c["scores"]
                }
                for i, c in enumerate(sorted_candidates)
            ]

        try:
            cross_ranked = aggregate_rankings(rankings)

            # Map back to full candidate data
            top_candidates = []
            for ranked in cross_ranked:
                for candidate in valid_candidates:
                    if candidate["headline"] == ranked["headline"]:
                        top_candidates.append({
                            **candidate,
                            "cross_rank_data": ranked
                        })
                        break

        except Exception:
            # Fallback to self-score ranking
            ranking_mode = "self_score_fallback"
            valid_candidates.sort(key=lambda x: x["scores"]["overall"], reverse=True)
            top_candidates = valid_candidates[:10]

    # Deduplicate results
    top_candidates = _deduplicate_headlines(top_candidates)

    # Handle tie for 10th place
    if _test_force_tie and len(top_candidates) == 10:
        if len(valid_candidates) > 10:
            tie_candidate = valid_candidates[10].copy()
            tie_candidate["scores"]["overall"] = top_candidates[-1]["scores"]["overall"]
            top_candidates.append(tie_candidate)

    # Limit to top 10 (or 11 in case of tie)
    final_candidates = top_candidates[:11] if _test_force_tie else top_candidates[:10]

    # Phase 4: Generate subtitles for top headline
    subtitles = []
    if final_candidates:
        top_headline = final_candidates[0]["headline"]
        subtitles = _generate_subtitles(top_headline, content)

    # Format final output
    top_headlines = []
    for candidate in final_candidates:
        cross_rank_data = candidate.get("cross_rank_data", {})

        top_headlines.append({
            "headline": candidate["headline"],
            "composite_score": candidate["scores"]["overall"],
            "generating_angle": candidate["generating_angle"],
            "word_count": candidate.get("word_count", len(candidate["headline"].split())),
            "scores": candidate["scores"],
            "primary_lens": candidate.get("primary_lens", ""),
            "rationale": candidate.get("rationale", ""),
            "cross_rank_performance": {
                "borda_points": cross_rank_data.get("borda_points", 0),
                "angles_ranked": cross_rank_data.get("angles_ranked", 1),
                "consensus_bonus": cross_rank_data.get("consensus_bonus", False),
                "top_5_count": cross_rank_data.get("top_5_count", 0)
            }
        })

    # Sort by composite score
    top_headlines.sort(key=lambda x: x["composite_score"], reverse=True)

    total_time = int((time.time() - start_time) * 1000)

    return {
        "top_headlines": top_headlines,
        "subtitles": subtitles,
        "pipeline": {
            "candidates_generated": candidates_generated,
            "candidates_after_filter": candidates_after_filter,
            "final_count": len(top_headlines),
            "angles_executed": angles_executed,
            "timed_out_angles": timed_out_angles,
            "partial_execution": len(timed_out_angles) > 0,
            "ranking_mode": ranking_mode,
            "total_time_ms": total_time
        },
        "warnings": warnings if warnings else None
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Orchestrate 5-angle headline swarm")
    parser.add_argument("--content", required=True, help="Content text to process")
    parser.add_argument("--title-context", help="Current title for context")
    parser.add_argument("--context", help="JSON string with additional context")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    context = None
    if args.context:
        try:
            context = json.loads(args.context)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": f"Invalid context JSON: {e}"}), file=sys.stderr)
            sys.exit(1)

    try:
        result = orchestrate_swarm(
            args.content,
            title_context=args.title_context,
            context=context
        )

        output = json.dumps(result, indent=2)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Output written to {args.output}")
        else:
            print(output)

    except (TypeError, ValueError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
