#!/usr/bin/env python3
"""
3-Year Total Cost of Ownership (TCO) Calculator for Build vs Buy Decisions

Usage:
    python tco_3y_calc.py --build-sp 13 --eng-rate 150 --buy-monthly 99

Output:
    JSON with build vs buy TCO breakdown over 3 years
"""

import argparse
import json
from dataclasses import dataclass, asdict
from typing import Dict


@dataclass
class BuildCosts:
    """Costs associated with building in-house."""
    initial_dev_usd: float
    year1_maintenance_usd: float
    year2_maintenance_usd: float
    year3_maintenance_usd: float
    infrastructure_year1_usd: float
    infrastructure_year2_usd: float
    infrastructure_year3_usd: float
    opportunity_cost_usd: float

    @property
    def total_3yr_usd(self) -> float:
        return (
            self.initial_dev_usd
            + self.year1_maintenance_usd
            + self.year2_maintenance_usd
            + self.year3_maintenance_usd
            + self.infrastructure_year1_usd
            + self.infrastructure_year2_usd
            + self.infrastructure_year3_usd
            + self.opportunity_cost_usd
        )


@dataclass
class BuyCosts:
    """Costs associated with buying/subscribing to third-party solution."""
    integration_usd: float
    year1_subscription_usd: float
    year2_subscription_usd: float
    year3_subscription_usd: float
    training_usd: float

    @property
    def total_3yr_usd(self) -> float:
        return (
            self.integration_usd
            + self.year1_subscription_usd
            + self.year2_subscription_usd
            + self.year3_subscription_usd
            + self.training_usd
        )


class TCOCalculator:
    """Calculates 3-year TCO for build vs buy decisions."""

    # Constants
    HOURS_PER_STORY_POINT = 8  # Baseline: 1 SP = 1 day = 8 hours
    MAINTENANCE_BURDEN = 0.25  # Annual maintenance = 25% of initial build
    INFRASTRUCTURE_GROWTH_RATE = 1.15  # Infrastructure costs grow 15% YoY
    SUBSCRIPTION_GROWTH_RATE = 1.10  # Assume vendor raises prices 10% YoY
    OPPORTUNITY_COST_MULTIPLIER = 2.0  # Opportunity cost = 2x initial dev cost

    def __init__(
        self,
        build_story_points: float,
        engineering_rate_usd_per_hour: float,
        buy_monthly_subscription_usd: float,
        buy_integration_sp: float = 0.5,  # Default: integration takes 0.5 SP
        infrastructure_monthly_usd: float = 0,  # Default: no extra infra cost
        training_hours: float = 0,  # Default: no training cost
    ):
        self.build_sp = build_story_points
        self.eng_rate = engineering_rate_usd_per_hour
        self.buy_monthly = buy_monthly_subscription_usd
        self.buy_integration_sp = buy_integration_sp
        self.infra_monthly = infrastructure_monthly_usd
        self.training_hours = training_hours

    def calculate_build_costs(self) -> BuildCosts:
        """Calculate all build-related costs over 3 years."""

        # Initial development
        initial_dev_hours = self.build_sp * self.HOURS_PER_STORY_POINT
        initial_dev_usd = initial_dev_hours * self.eng_rate

        # Annual maintenance (25% of initial build effort)
        maintenance_hours_per_year = initial_dev_hours * self.MAINTENANCE_BURDEN
        year1_maintenance = maintenance_hours_per_year * self.eng_rate
        year2_maintenance = maintenance_hours_per_year * self.eng_rate
        year3_maintenance = maintenance_hours_per_year * self.eng_rate

        # Infrastructure costs (grow 15% YoY)
        infra_year1 = self.infra_monthly * 12
        infra_year2 = infra_year1 * self.INFRASTRUCTURE_GROWTH_RATE
        infra_year3 = infra_year2 * self.INFRASTRUCTURE_GROWTH_RATE

        # Opportunity cost (what else could you build?)
        # Baseline: 2x initial dev cost (you could build 2 other features)
        opportunity_cost = initial_dev_usd * self.OPPORTUNITY_COST_MULTIPLIER

        return BuildCosts(
            initial_dev_usd=initial_dev_usd,
            year1_maintenance_usd=year1_maintenance,
            year2_maintenance_usd=year2_maintenance,
            year3_maintenance_usd=year3_maintenance,
            infrastructure_year1_usd=infra_year1,
            infrastructure_year2_usd=infra_year2,
            infrastructure_year3_usd=infra_year3,
            opportunity_cost_usd=opportunity_cost,
        )

    def calculate_buy_costs(self) -> BuyCosts:
        """Calculate all buy-related costs over 3 years."""

        # Integration cost (one-time)
        integration_hours = self.buy_integration_sp * self.HOURS_PER_STORY_POINT
        integration_usd = integration_hours * self.eng_rate

        # Annual subscription (assume 10% price increase YoY)
        year1_subscription = self.buy_monthly * 12
        year2_subscription = year1_subscription * self.SUBSCRIPTION_GROWTH_RATE
        year3_subscription = year2_subscription * self.SUBSCRIPTION_GROWTH_RATE

        # Training cost (one-time)
        training_usd = self.training_hours * self.eng_rate

        return BuyCosts(
            integration_usd=integration_usd,
            year1_subscription_usd=year1_subscription,
            year2_subscription_usd=year2_subscription,
            year3_subscription_usd=year3_subscription,
            training_usd=training_usd,
        )

    def calculate(self) -> Dict:
        """Calculate full TCO comparison."""
        build = self.calculate_build_costs()
        buy = self.calculate_buy_costs()

        savings_buy = build.total_3yr_usd - buy.total_3yr_usd
        roi_buy = build.total_3yr_usd / buy.total_3yr_usd if buy.total_3yr_usd > 0 else 0

        return {
            "inputs": {
                "build_story_points": self.build_sp,
                "engineering_rate_usd_per_hour": self.eng_rate,
                "buy_monthly_subscription_usd": self.buy_monthly,
                "buy_integration_sp": self.buy_integration_sp,
                "infrastructure_monthly_usd": self.infra_monthly,
                "training_hours": self.training_hours,
            },
            "assumptions": {
                "hours_per_story_point": self.HOURS_PER_STORY_POINT,
                "maintenance_burden_percent": self.MAINTENANCE_BURDEN * 100,
                "infrastructure_growth_rate_percent": (self.INFRASTRUCTURE_GROWTH_RATE - 1) * 100,
                "subscription_growth_rate_percent": (self.SUBSCRIPTION_GROWTH_RATE - 1) * 100,
                "opportunity_cost_multiplier": self.OPPORTUNITY_COST_MULTIPLIER,
            },
            "build": asdict(build),
            "buy": asdict(buy),
            "comparison": {
                "build_total_3yr_usd": build.total_3yr_usd,
                "buy_total_3yr_usd": buy.total_3yr_usd,
                "savings_buy_usd": savings_buy,
                "roi_buy": round(roi_buy, 2),
                "recommendation": "BUY" if savings_buy > 0 else "BUILD",
            }
        }


def main():
    parser = argparse.ArgumentParser(
        description="Calculate 3-year TCO for build vs buy decisions"
    )
    parser.add_argument(
        "--build-sp",
        type=float,
        required=True,
        help="Story points to build the solution in-house"
    )
    parser.add_argument(
        "--eng-rate",
        type=float,
        required=True,
        help="Engineering rate in USD per hour (e.g., 150)"
    )
    parser.add_argument(
        "--buy-monthly",
        type=float,
        required=True,
        help="Monthly subscription cost in USD (e.g., 99)"
    )
    parser.add_argument(
        "--buy-integration-sp",
        type=float,
        default=0.5,
        help="Story points to integrate third-party solution (default: 0.5)"
    )
    parser.add_argument(
        "--infra-monthly",
        type=float,
        default=0,
        help="Monthly infrastructure cost for build option in USD (default: 0)"
    )
    parser.add_argument(
        "--training-hours",
        type=float,
        default=0,
        help="Training hours for buy option (default: 0)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: stdout)"
    )

    args = parser.parse_args()

    calculator = TCOCalculator(
        build_story_points=args.build_sp,
        engineering_rate_usd_per_hour=args.eng_rate,
        buy_monthly_subscription_usd=args.buy_monthly,
        buy_integration_sp=args.buy_integration_sp,
        infrastructure_monthly_usd=args.infra_monthly,
        training_hours=args.training_hours,
    )

    result = calculator.calculate()

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"TCO calculation saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
