#!/usr/bin/env python3
"""
Decision Tracker for Learning Weights System

Logs build-vs-buy decisions and analyzes patterns to suggest weight adjustments.

Usage:
    # Log a decision
    python decision_tracker.py log \
        --decision-id "dec_001" \
        --choice "buy" \
        --matrix-file "buy_build.json"

    # Analyze patterns and suggest weight adjustments
    python decision_tracker.py analyze \
        --decision-log "decisions/decision_log.csv"

Output:
    - Logs decisions to CSV
    - Suggests weight adjustments based on historical patterns
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


class DecisionTracker:
    """Tracks build-vs-buy decisions and learns from patterns."""

    def __init__(self, log_file: str = "decisions/decision_log.csv"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True, parents=True)

        # Initialize CSV if it doesn't exist
        if not self.log_file.exists():
            self._initialize_log()

    def _initialize_log(self):
        """Create CSV with headers."""
        with open(self.log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                "decision_id",
                "date",
                "topic",
                "matrix_recommendation",
                "actual_choice",
                "override",
                "build_score",
                "buy_score",
                "strategic_fit_weight",
                "tco_weight",
                "time_to_market_weight",
                "risk_weight",
                "control_weight",
                "learning_weight",
                "ecosystem_weight",
                "override_rationale",
            ])

    def log_decision(
        self,
        decision_id: str,
        matrix_file: Path,
        actual_choice: str,
        override_rationale: str = "",
    ):
        """Log a decision to the CSV."""

        # Load matrix file
        with open(matrix_file) as f:
            matrix = json.load(f)

        # Extract data
        date = datetime.now().isoformat()
        topic = matrix.get("decision", "unknown")
        matrix_recommendation = matrix.get("recommendation", "unknown")
        override = actual_choice.upper() != matrix_recommendation.upper()

        weighted_scores = matrix.get("weighted_scores", {})
        build_score = weighted_scores.get("build_total", 0)
        buy_score = weighted_scores.get("buy_total", 0)

        weights = matrix.get("weights", {})

        # Append to log
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                decision_id,
                date,
                topic,
                matrix_recommendation,
                actual_choice.upper(),
                override,
                build_score,
                buy_score,
                weights.get("strategic_fit", 0),
                weights.get("tco_3yr", 0),
                weights.get("time_to_market", 0),
                weights.get("risk", 0),
                weights.get("control", 0),
                weights.get("learning", 0),
                weights.get("ecosystem", 0),
                override_rationale,
            ])

        print(f"✅ Decision {decision_id} logged to {self.log_file}")

    def analyze_patterns(self) -> Dict:
        """Analyze logged decisions and suggest weight adjustments."""

        decisions = self._load_decisions()

        if len(decisions) < 5:
            return {
                "message": f"Need at least 5 decisions to analyze patterns (currently: {len(decisions)})",
                "suggested_weights": None,
            }

        # Analyze override patterns
        override_analysis = self._analyze_overrides(decisions)

        # Suggest weight adjustments
        suggested_weights = self._suggest_weights(decisions, override_analysis)

        return {
            "total_decisions": len(decisions),
            "override_rate": override_analysis["override_rate"],
            "override_patterns": override_analysis["patterns"],
            "suggested_weights": suggested_weights,
            "rationale": self._explain_suggestions(override_analysis),
        }

    def _load_decisions(self) -> List[Dict]:
        """Load decisions from CSV."""
        decisions = []
        with open(self.log_file, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert string booleans and floats
                row['override'] = row['override'] == 'True'
                for key in ['build_score', 'buy_score', 'strategic_fit_weight',
                           'tco_weight', 'time_to_market_weight', 'risk_weight',
                           'control_weight', 'learning_weight', 'ecosystem_weight']:
                    row[key] = float(row[key])
                decisions.append(row)
        return decisions

    def _analyze_overrides(self, decisions: List[Dict]) -> Dict:
        """Analyze when and why user overrode matrix recommendation."""

        total = len(decisions)
        overrides = [d for d in decisions if d['override']]
        override_rate = len(overrides) / total if total > 0 else 0

        # Group overrides by dimension emphasis
        patterns = defaultdict(list)

        for decision in overrides:
            # Find which dimension had highest weight
            dimension_weights = {
                "strategic_fit": decision["strategic_fit_weight"],
                "tco": decision["tco_weight"],
                "time_to_market": decision["time_to_market_weight"],
                "risk": decision["risk_weight"],
                "control": decision["control_weight"],
                "learning": decision["learning_weight"],
                "ecosystem": decision["ecosystem_weight"],
            }

            max_dimension = max(dimension_weights, key=dimension_weights.get)
            patterns[max_dimension].append({
                "decision_id": decision["decision_id"],
                "topic": decision["topic"],
                "rationale": decision["override_rationale"],
            })

        return {
            "override_rate": override_rate,
            "patterns": dict(patterns),
        }

    def _suggest_weights(
        self,
        decisions: List[Dict],
        override_analysis: Dict
    ) -> Dict[str, float]:
        """Suggest adjusted weights based on historical patterns."""

        # Start with current average weights
        avg_weights = self._calculate_average_weights(decisions)

        # Adjust based on override patterns
        patterns = override_analysis["patterns"]

        # If user frequently overrides for a specific dimension,
        # increase that dimension's weight
        adjustments = {}
        total_overrides = sum(len(v) for v in patterns.values())

        if total_overrides > 0:
            for dimension, override_list in patterns.items():
                # Frequency of overrides for this dimension
                freq = len(override_list) / total_overrides

                # If >50% of overrides were for this dimension, boost its weight
                if freq > 0.5:
                    if dimension == "tco":
                        dimension = "tco_3yr"
                    adjustments[dimension] = min(avg_weights.get(dimension, 0.20) + 0.10, 0.40)

        # Merge adjustments with average weights
        suggested = {**avg_weights, **adjustments}

        # Normalize to sum to 1.0
        total = sum(suggested.values())
        suggested = {k: round(v / total, 2) for k, v in suggested.items()}

        return suggested

    def _calculate_average_weights(self, decisions: List[Dict]) -> Dict[str, float]:
        """Calculate average weights across all decisions."""

        totals = defaultdict(float)
        count = len(decisions)

        for decision in decisions:
            totals["strategic_fit"] += decision["strategic_fit_weight"]
            totals["tco_3yr"] += decision["tco_weight"]
            totals["time_to_market"] += decision["time_to_market_weight"]
            totals["risk"] += decision["risk_weight"]
            totals["control"] += decision["control_weight"]
            totals["learning"] += decision["learning_weight"]
            totals["ecosystem"] += decision["ecosystem_weight"]

        return {k: v / count for k, v in totals.items()}

    def _explain_suggestions(self, override_analysis: Dict) -> List[str]:
        """Explain why weights are being adjusted."""

        rationale = []
        patterns = override_analysis["patterns"]

        for dimension, override_list in patterns.items():
            if len(override_list) >= 2:
                rationale.append(
                    f"You overrode the matrix {len(override_list)} times "
                    f"when '{dimension}' was critical. Consider increasing its weight."
                )

        if override_analysis["override_rate"] < 0.2:
            rationale.append(
                "Your override rate is low (<20%), suggesting current weights "
                "align well with your decision-making."
            )
        elif override_analysis["override_rate"] > 0.5:
            rationale.append(
                f"Your override rate is high ({override_analysis['override_rate']:.0%}), "
                "suggesting weights may not reflect your priorities. Review patterns above."
            )

        return rationale


def main():
    parser = argparse.ArgumentParser(
        description="Track build-vs-buy decisions and learn from patterns"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Log command
    log_parser = subparsers.add_parser("log", help="Log a decision")
    log_parser.add_argument("--decision-id", required=True, help="Unique decision ID")
    log_parser.add_argument("--matrix-file", required=True, help="Path to buy_build.json")
    log_parser.add_argument("--choice", required=True, choices=["build", "buy"], help="Actual choice made")
    log_parser.add_argument("--rationale", default="", help="Override rationale (if applicable)")
    log_parser.add_argument("--log-file", default="decisions/decision_log.csv", help="Path to log file")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze patterns and suggest weights")
    analyze_parser.add_argument("--decision-log", default="decisions/decision_log.csv", help="Path to log file")
    analyze_parser.add_argument("--output", default=None, help="Output JSON file (default: stdout)")

    args = parser.parse_args()

    if args.command == "log":
        tracker = DecisionTracker(log_file=args.log_file)
        tracker.log_decision(
            decision_id=args.decision_id,
            matrix_file=Path(args.matrix_file),
            actual_choice=args.choice,
            override_rationale=args.rationale,
        )

    elif args.command == "analyze":
        tracker = DecisionTracker(log_file=args.decision_log)
        result = tracker.analyze_patterns()

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Analysis saved to {args.output}")
        else:
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
