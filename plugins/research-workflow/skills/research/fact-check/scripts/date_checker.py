#!/usr/bin/env python3
"""
Date Alignment Checker for Claim Validation

Validates that source publication dates align with claim timeframes.

Usage:
    python date_checker.py \
        --claim-date "2025" \
        --source-date "2025-06-15" \
        --tolerance-years 1

Output:
    JSON with alignment status: ok, stale, future, or unknown
"""

import argparse
import json
import re
from datetime import datetime
from typing import Optional, Dict


class DateChecker:
    """Checks temporal alignment between claims and sources."""

    def __init__(self, tolerance_years: int = 1):
        """
        Args:
            tolerance_years: Acceptable gap between claim and source date
        """
        self.tolerance_years = tolerance_years

    def extract_year(self, date_string: str) -> Optional[int]:
        """
        Extract year from various date formats.
        
        Supports:
        - ISO 8601: 2025-06-15, 2025-06-15T10:30:00Z
        - Year only: 2025
        - US format: 06/15/2025
        - Written: June 15, 2025
        """
        if not date_string:
            return None

        # Try ISO 8601 format (2025-06-15)
        iso_match = re.search(r'(\d{4})-\d{2}-\d{2}', date_string)
        if iso_match:
            return int(iso_match.group(1))

        # Try year only (2025)
        year_match = re.search(r'\b(20\d{2})\b', date_string)
        if year_match:
            return int(year_match.group(1))

        # Try US format (06/15/2025 or 6/15/25)
        us_match = re.search(r'\d{1,2}/\d{1,2}/(\d{2,4})', date_string)
        if us_match:
            year = int(us_match.group(1))
            if year < 100:  # 2-digit year
                year += 2000
            return year

        # Try written format (June 15, 2025)
        written_match = re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(\d{4})\b', date_string, re.IGNORECASE)
        if written_match:
            return int(written_match.group(2))

        return None

    def check_alignment(
        self,
        claim_date: str,
        source_date: str
    ) -> Dict:
        """
        Check if source date aligns with claim timeframe.
        
        Returns:
            {
                "status": "ok" | "stale" | "future" | "unknown",
                "claim_year": int | None,
                "source_year": int | None,
                "gap_years": int | None,
                "rationale": str
            }
        """
        claim_year = self.extract_year(claim_date)
        source_year = self.extract_year(source_date)

        # Unknown dates
        if claim_year is None and source_year is None:
            return {
                "status": "unknown",
                "claim_year": None,
                "source_year": None,
                "gap_years": None,
                "rationale": "Both claim and source dates could not be parsed"
            }

        if claim_year is None:
            return {
                "status": "unknown",
                "claim_year": None,
                "source_year": source_year,
                "gap_years": None,
                "rationale": "Claim date could not be parsed"
            }

        if source_year is None:
            return {
                "status": "unknown",
                "claim_year": claim_year,
                "source_year": None,
                "gap_years": None,
                "rationale": "Source date could not be parsed"
            }

        # Calculate gap
        gap = claim_year - source_year

        # Check alignment
        if abs(gap) <= self.tolerance_years:
            return {
                "status": "ok",
                "claim_year": claim_year,
                "source_year": source_year,
                "gap_years": gap,
                "rationale": f"Source date within {self.tolerance_years} year(s) of claim"
            }

        if gap > self.tolerance_years:
            return {
                "status": "stale",
                "claim_year": claim_year,
                "source_year": source_year,
                "gap_years": gap,
                "rationale": f"Source predates claim by {gap} year(s) (tolerance: {self.tolerance_years})"
            }

        # gap < -tolerance_years
        return {
            "status": "future",
            "claim_year": claim_year,
            "source_year": source_year,
            "gap_years": gap,
            "rationale": f"Source postdates claim by {abs(gap)} year(s)"
        }


def main():
    parser = argparse.ArgumentParser(
        description="Check temporal alignment between claim and source dates"
    )
    parser.add_argument(
        "--claim-date",
        required=True,
        help="Claim date or timeframe (e.g., '2025', '2025 market')"
    )
    parser.add_argument(
        "--source-date",
        required=True,
        help="Source publication date (e.g., '2025-06-15', 'June 15, 2025')"
    )
    parser.add_argument(
        "--tolerance-years",
        type=int,
        default=1,
        help="Acceptable gap in years (default: 1)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file (default: stdout)"
    )

    args = parser.parse_args()

    checker = DateChecker(tolerance_years=args.tolerance_years)
    result = checker.check_alignment(args.claim_date, args.source_date)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Date alignment check saved to {args.output}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
