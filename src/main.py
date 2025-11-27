"""
Command-line entry point for pull request statistics.

Environment variables:
    GITHUB_ACCESS_TOKEN: Required. Token with permission to run search queries.
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime

from github_client.client import GitHubClient
from pull_request_statistics.date_ranges import HalfName, MonthName, QuarterName
from pull_request_statistics.pull_request_service import PullRequestStatisticsService
from require_env import require_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gather pull request statistics for authored and reviewed PRs.")
    parser.add_argument("--author", required=True, help="GitHub login of the author to analyse.")
    parser.add_argument("--organisation", required=True, help="GitHub organisation to search within.")
    parser.add_argument("--reviewer", help="GitHub login of the reviewer. Defaults to the author.")
    parser.add_argument("--merged-only", action="store_true", help="Limit authored results to merged pull requests.")
    parser.add_argument(
        "--exclude-self-reviews",
        action="store_true",
        help="Exclude reviews on self-authored pull requests when counting reviewed PRs.",
    )
    parser.add_argument("--quarter", help="Quarter to search (e.g. Q1).")
    parser.add_argument("--half", help="Half-year to search (e.g. H1).")
    parser.add_argument("--month", help="Month name or number (e.g. March or 3).")
    parser.add_argument("--year", type=int, help="Year to search.")
    parser.add_argument("--date", dest="on_date", help="Specific date (YYYY-MM-DD) to search.")
    parser.add_argument("--page-size", type=int, default=50, help="Page size for GitHub search pagination.")
    parser.add_argument(
        "--counts-only",
        action="store_true",
        help="Only fetch counts; skip fetching full pull request lists for authored and reviewed queries.",
    )
    return parser.parse_args()


def default_periods(args: argparse.Namespace) -> None:
    """Populate default period values when none were provided."""
    if any((args.quarter, args.half, args.month, args.year, args.on_date)):
        return
    today = datetime.now(UTC).date()
    current_quarter = QuarterName(((today.month - 1) // 3) + 1)
    args.quarter = current_quarter.name


def parse_period_inputs(args: argparse.Namespace) -> dict:
    """Normalise CLI period inputs into service arguments."""
    default_periods(args)
    quarter = QuarterName.from_string(args.quarter) if args.quarter else None
    half = HalfName.from_string(args.half) if args.half else None
    month = MonthName.from_string(args.month) if args.month else None
    on_date = date.fromisoformat(args.on_date) if args.on_date else None
    return {
        "quarter": quarter,
        "half": half,
        "month": month,
        "year": args.year,
        "on_date": on_date,
    }


def main() -> None:
    args = parse_args()
    periods = parse_period_inputs(args)

    access_token = require_env("GITHUB_ACCESS_TOKEN")
    client = GitHubClient(access_token=access_token)
    service = PullRequestStatisticsService(client, page_size=args.page_size)

    authored = []
    if not args.counts_only:
        authored = list(
            service.iter_pull_requests_by_author_in_date_range(
                author=args.author,
                organisation=args.organisation,
                merged_only=args.merged_only,
                **periods,
            )
        )
    authored_range, authored_count = service.count_pull_requests_by_author_in_date_range(
        author=args.author,
        organisation=args.organisation,
        merged_only=args.merged_only,
        **periods,
    )

    reviewer = args.reviewer or args.author
    reviewed = []
    if not args.counts_only:
        reviewed = list(
            service.iter_pull_requests_reviewed_by_user_in_date_range(
                reviewer=reviewer,
                organisation=args.organisation,
                exclude_self_authored=args.exclude_self_reviews,
                **periods,
            )
        )
    reviewed_range, reviewed_count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer=reviewer,
        organisation=args.organisation,
        exclude_self_authored=args.exclude_self_reviews,
        **periods,
    )

    print(
        (
            f"Authored PRs for {args.author} in {args.organisation}: {authored_count} "
            f"from {authored_range.start_date.isoformat()} to {authored_range.end_date.isoformat()} "
            f"(retrieved {len(authored)}).{' Merged only.' if args.merged_only else ''}"
        ),
        flush=True,
    )
    if not args.counts_only:
        for pr in authored:
            print(f"- {pr.repository} #{pr.number}: {pr.title} ({pr.url})", flush=True)

    print(
        (
            f"Reviewed PRs by {reviewer} in {args.organisation}: {reviewed_count} "
            f"from {reviewed_range.start_date.isoformat()} to {reviewed_range.end_date.isoformat()} "
            f"(retrieved {len(reviewed)}).{' Excluding self-authored.' if args.exclude_self_reviews else ''}"
        ),
        flush=True,
    )
    if not args.counts_only:
        for pr in reviewed:
            print(f"- REVIEWED {pr.repository} #{pr.number}: {pr.title} ({pr.url})", flush=True)


if __name__ == "__main__":
    main()
