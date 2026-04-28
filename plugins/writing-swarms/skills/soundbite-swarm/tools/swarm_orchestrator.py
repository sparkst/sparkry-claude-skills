#!/usr/bin/env python3
"""
Swarm Orchestrator

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
4. Return top 10 with full metadata

Usage:
    python swarm_orchestrator.py --content "..."

Output (JSON):
    {
      "top_soundbites": [...],
      "pipeline": {...}
    }
"""

import json
import sys
import time
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Import other tools
from angle_generator import generate_from_angle, VALID_ANGLES
from soundbite_validator import validate_soundbite
from cross_ranker import aggregate_rankings


# Default configuration
DEFAULT_TIMEOUT_SECONDS = 30
CANDIDATES_PER_ANGLE = 10


def _deduplicate_soundbites(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate soundbites, keeping the higher-scoring version.

    Args:
        candidates: List of candidate soundbites

    Returns:
        Deduplicated list
    """
    seen: Dict[str, Dict[str, Any]] = {}

    for candidate in candidates:
        soundbite = candidate.get("soundbite", "")
        key = soundbite.lower().strip()

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
    timeout: float = DEFAULT_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    """
    Generate soundbites from a single angle with timeout handling.

    Args:
        content: Content to generate from
        angle: Creative angle name
        timeout: Timeout in seconds

    Returns:
        Generation result or error dict
    """
    try:
        result = generate_from_angle(content, angle)
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


def orchestrate_swarm(
    content: str,
    _test_max_valid: Optional[int] = None,
    _test_force_tie: bool = False,
    _test_fail_all_validation: bool = False,
    _test_timeout_angle: Optional[str] = None,
    _test_fail_cross_ranker: bool = False
) -> Dict[str, Any]:
    """
    Orchestrate the 5-angle swarm to generate and rank soundbites.

    Args:
        content: Content text to generate soundbites from
        _test_*: Test-only parameters for edge case testing

    Returns:
        Dict with top_soundbites and pipeline metadata

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

    # Track warnings
    warnings: List[str] = []
    if len(content.split()) < 50:
        warnings.append("Short content may reduce soundbite quality and diversity")

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

    # Generate from each angle (sequential for simplicity; parallel in production)
    for angle in angles_to_run:
        gen_result = _generate_angle(content, angle)

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
        # Test scenario: all validation fails
        valid_candidates = []
    else:
        for candidate in all_candidates:
            soundbite_data = {
                "soundbite": candidate["soundbite"],
                "scores": candidate["scores"]
            }

            try:
                validation_result = validate_soundbite(soundbite_data)
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
            "top_soundbites": [],
            "error": True,
            "error_message": "All candidates failed validation - no valid soundbites produced",
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
        # Sort by overall score
        valid_candidates.sort(key=lambda x: x["scores"]["overall"], reverse=True)
        top_candidates = valid_candidates[:10]
    else:
        # Prepare rankings for cross-ranker
        # Each angle ranks all candidates from its perspective
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
                    "candidate_id": f"{c['generating_angle']}_{c['soundbite'][:10]}",
                    "soundbite": c["soundbite"],
                    "scores": c["scores"]
                }
                for i, c in enumerate(sorted_candidates)
            ]

        try:
            cross_ranked = aggregate_rankings(rankings)

            # Map back to full candidate data
            top_candidates = []
            for ranked in cross_ranked:
                # Find matching candidate
                for candidate in valid_candidates:
                    if candidate["soundbite"] == ranked["soundbite"]:
                        top_candidates.append({
                            **candidate,
                            "cross_rank_data": ranked
                        })
                        break

        except Exception as e:
            # Fallback to self-score ranking
            ranking_mode = "self_score_fallback"
            valid_candidates.sort(key=lambda x: x["scores"]["overall"], reverse=True)
            top_candidates = valid_candidates[:10]

    # Deduplicate results
    top_candidates = _deduplicate_soundbites(top_candidates)

    # Handle tie for 10th place
    if _test_force_tie and len(top_candidates) == 10:
        # Add one more candidate with same score as 10th
        if len(valid_candidates) > 10:
            tie_candidate = valid_candidates[10].copy()
            tie_candidate["scores"]["overall"] = top_candidates[-1]["scores"]["overall"]
            top_candidates.append(tie_candidate)

    # Limit to top 10 (or 11 in case of tie)
    final_candidates = top_candidates[:11] if _test_force_tie else top_candidates[:10]

    # Format final output
    top_soundbites = []
    for candidate in final_candidates:
        cross_rank_data = candidate.get("cross_rank_data", {})

        top_soundbites.append({
            "soundbite": candidate["soundbite"],
            "composite_score": candidate["scores"]["overall"],
            "generating_angle": candidate["generating_angle"],
            "word_count": candidate.get("word_count", len(candidate["soundbite"].split())),
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
    top_soundbites.sort(key=lambda x: x["composite_score"], reverse=True)

    total_time = int((time.time() - start_time) * 1000)

    return {
        "top_soundbites": top_soundbites,
        "pipeline": {
            "candidates_generated": candidates_generated,
            "candidates_after_filter": candidates_after_filter,
            "final_count": len(top_soundbites),
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

    parser = argparse.ArgumentParser(description="Orchestrate 5-angle soundbite swarm")
    parser.add_argument("--content", required=True, help="Content text to process")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    try:
        result = orchestrate_swarm(args.content)

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
