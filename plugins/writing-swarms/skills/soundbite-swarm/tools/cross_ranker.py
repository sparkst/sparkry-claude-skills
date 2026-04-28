#!/usr/bin/env python3
"""
Cross-Ranker

Aggregates rankings from 5 angles using Borda count:
- 1st place = 10 points
- 2nd place = 9 points
- ... 10th place = 1 point
- Unranked = 0 points
- Bonus: +5 if in top-5 of 3+ angles

Usage:
    python cross_ranker.py --rankings '<json_rankings>'

Output (JSON):
    [
      {
        "candidate_id": "sb_001",
        "soundbite": "You Already Know",
        "borda_points": 55,
        "consensus_bonus": true,
        "angles_ranked": 5,
        "top_5_count": 5
      }
    ]
"""

import json
import sys
from typing import Dict, Any, List, Optional
from collections import defaultdict


class DuplicateError(Exception):
    """Raised when duplicate candidates found in same angle's ranking."""
    pass


class RangeError(Exception):
    """Raised when rank is outside valid range (1-10)."""
    pass


def calculate_borda_points(rank: Optional[int]) -> int:
    """
    Calculate Borda count points for a given rank.

    Args:
        rank: Rank position (1-10) or None for unranked

    Returns:
        Points (10 for rank 1, 1 for rank 10, 0 for unranked)
    """
    if rank is None:
        return 0

    if not isinstance(rank, int):
        return 0

    if rank < 1 or rank > 10:
        return 0

    return 11 - rank


def calculate_consensus_bonus(candidate_id: str, top_5_counts: Dict[str, int]) -> int:
    """
    Calculate consensus bonus for a candidate.

    +5 points if candidate appears in top-5 of 3+ angles.

    Args:
        candidate_id: The candidate identifier
        top_5_counts: Dict mapping candidate_id to count of top-5 appearances

    Returns:
        Bonus points (5 or 0)
    """
    count = top_5_counts.get(candidate_id, 0)
    return 5 if count >= 3 else 0


def _validate_rankings(rankings: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Validate rankings structure.

    Raises:
        DuplicateError: If duplicate candidates in same angle
        RangeError: If invalid rank numbers
        KeyError: If required fields missing
    """
    for angle, ranking_list in rankings.items():
        seen_candidates = set()

        for entry in ranking_list:
            # Check required fields
            if "candidate_id" not in entry:
                raise KeyError("Missing required field: candidate_id")

            if "rank" not in entry:
                raise KeyError("Missing required field: rank")

            candidate_id = entry["candidate_id"]
            rank = entry["rank"]

            # Check for duplicates
            if candidate_id in seen_candidates:
                raise DuplicateError(f"Duplicate candidate '{candidate_id}' in {angle} rankings")
            seen_candidates.add(candidate_id)

            # Validate rank range
            if not isinstance(rank, int) or rank < 1 or rank > 10:
                raise RangeError(f"rank must be between 1 and 10, got {rank}")


def aggregate_rankings(rankings: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Aggregate rankings from multiple angles using Borda count.

    Args:
        rankings: Dict mapping angle name to list of ranked candidates

    Returns:
        List of candidates sorted by aggregated score

    Raises:
        DuplicateError: If duplicate candidates in same angle
        RangeError: If invalid rank numbers
        KeyError: If required fields missing
    """
    # Validate input
    _validate_rankings(rankings)

    # Collect all candidates and their metadata
    candidates: Dict[str, Dict[str, Any]] = {}
    borda_scores: Dict[str, int] = defaultdict(int)
    top_5_counts: Dict[str, int] = defaultdict(int)
    angles_ranked: Dict[str, int] = defaultdict(int)

    # Track scores for tiebreaking
    candidate_scores: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"authenticity": 0, "brevity": 0, "emotional_resonance": 0}
    )

    # Process each angle's rankings
    for angle, ranking_list in rankings.items():
        if not ranking_list:
            continue

        for entry in ranking_list:
            candidate_id = entry["candidate_id"]
            rank = entry["rank"]
            soundbite = entry.get("soundbite", "")
            scores = entry.get("scores", {})

            # Store candidate metadata
            if candidate_id not in candidates:
                candidates[candidate_id] = {
                    "candidate_id": candidate_id,
                    "soundbite": soundbite,
                    "original_angle": angle
                }

            # Calculate Borda points
            points = calculate_borda_points(rank)
            borda_scores[candidate_id] += points

            # Track top-5 appearances
            if rank <= 5:
                top_5_counts[candidate_id] += 1

            # Track how many angles ranked this candidate
            angles_ranked[candidate_id] += 1

            # Store scores for tiebreaking
            if scores:
                for key in ["authenticity", "brevity", "emotional_resonance"]:
                    if key in scores:
                        # Take max score across angles
                        candidate_scores[candidate_id][key] = max(
                            candidate_scores[candidate_id][key],
                            scores[key]
                        )

    # Calculate final scores with consensus bonus
    results = []
    for candidate_id, metadata in candidates.items():
        base_points = borda_scores[candidate_id]
        bonus = calculate_consensus_bonus(candidate_id, top_5_counts)
        total_points = base_points + bonus

        results.append({
            "candidate_id": candidate_id,
            "soundbite": metadata["soundbite"],
            "original_angle": metadata["original_angle"],
            "borda_points": total_points,
            "base_points": base_points,
            "consensus_bonus": bonus > 0,
            "angles_ranked": angles_ranked[candidate_id],
            "top_5_count": top_5_counts[candidate_id],
            "tiebreaker_scores": candidate_scores[candidate_id]
        })

    # Sort by Borda points (descending), then tiebreakers
    results.sort(
        key=lambda x: (
            x["borda_points"],
            x["tiebreaker_scores"]["authenticity"],
            x["tiebreaker_scores"]["brevity"],
            x["angles_ranked"],
            x["tiebreaker_scores"]["emotional_resonance"]
        ),
        reverse=True
    )

    return results[:10]


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate rankings using Borda count")
    parser.add_argument("--rankings", required=True, help="JSON string with rankings by angle")

    args = parser.parse_args()

    try:
        rankings = json.loads(args.rankings)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}), file=sys.stderr)
        sys.exit(1)

    try:
        results = aggregate_rankings(rankings)
        print(json.dumps(results, indent=2))

    except (DuplicateError, RangeError, KeyError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
