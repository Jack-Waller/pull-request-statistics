"""
Command-line entry point for pull request statistics.

Environment variables:
    GITHUB_ACCESS_TOKEN: Required. Token with permission to run search queries.
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime

from github_client.client import GitHubClient
from github_client.pull_request_statistics import PullRequestStatisticsService
from github_client.pull_request_statistics.date_ranges import HalfName, MonthName, QuarterName
from github_client.team_members import TeamMembersService
from require_env import require_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gather pull request statistics for authored and reviewed PRs.")
    subject_group = parser.add_mutually_exclusive_group(required=True)
    subject_group.add_argument("--author", help="GitHub login of the author to analyse.")
    subject_group.add_argument("--team", help="Team slug within the organisation to list members for.")
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
    parser.add_argument("--week", action="store_true", help="Use the most recent seven days ending today.")
    parser.add_argument("--year", type=int, help="Year to search.")
    parser.add_argument("--date", dest="on_date", help="Specific date (YYYY-MM-DD) to search.")
    parser.add_argument("--page-size", type=int, default=50, help="Page size for GitHub search pagination.")
    parser.add_argument(
        "--counts-only",
        action="store_true",
        help="Only fetch counts; skip fetching full pull request lists for authored and reviewed queries.",
    )
    args = parser.parse_args()
    if args.team and args.reviewer:
        parser.error("--team cannot be combined with --reviewer; team statistics include review counts per member.")
    return args


def default_periods(args: argparse.Namespace) -> None:
    """Populate default period values when none were provided."""
    if any((args.quarter, args.half, args.month, args.year, args.on_date, args.week)):
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
        "week": args.week,
    }


def gather_authored_statistics(
    args: argparse.Namespace,
    *,
    periods: dict,
    service: PullRequestStatisticsService,
) -> tuple[list, tuple[object, int]]:
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
    return authored, (authored_range, authored_count)


def gather_reviewed_statistics(
    args: argparse.Namespace,
    reviewer: str,
    *,
    periods: dict,
    service: PullRequestStatisticsService,
) -> tuple[list, tuple[object, int]]:
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
    return reviewed, (reviewed_range, reviewed_count)


def print_authored_results(
    args: argparse.Namespace,
    authored: list,
    authored_range: object,
    authored_count: int,
) -> None:
    merged_suffix = " Merged only." if args.merged_only else ""
    print(
        (
            f"Authored PRs for {args.author} in {args.organisation}: {authored_count} "
            f"from {authored_range.start_date.isoformat()} to {authored_range.end_date.isoformat()} "
            f"(retrieved {len(authored)}).{merged_suffix}"
        ),
        flush=True,
    )
    if args.counts_only:
        return
    for pr in authored:
        print(f"- {pr.repository} #{pr.number}: {pr.title} {pr.url}", flush=True)


def print_reviewed_results(
    args: argparse.Namespace,
    reviewer: str,
    reviewed: list,
    reviewed_range: object,
    reviewed_count: int,
) -> None:
    suffix = " Excluding self-authored." if args.exclude_self_reviews else ""
    print(
        (
            f"Reviewed PRs by {reviewer} in {args.organisation}: {reviewed_count} "
            f"from {reviewed_range.start_date.isoformat()} to {reviewed_range.end_date.isoformat()} "
            f"(retrieved {len(reviewed)}).{suffix}"
        ),
        flush=True,
    )
    if args.counts_only:
        return
    for pr in reviewed:
        print(f"- REVIEWED {pr.repository} #{pr.number}: {pr.title} {pr.url}", flush=True)


def print_team_statistics(
    args: argparse.Namespace,
    *,
    periods: dict,
    service: PullRequestStatisticsService,
    team_service: TeamMembersService,
) -> None:
    team_members = team_service.list_team_members(args.organisation, args.team)
    rows: list[tuple[str, str, int, int]] = []
    date_range = None

    for member in team_members:
        authored_range, authored_count = service.count_pull_requests_by_author_in_date_range(
            author=member.login,
            organisation=args.organisation,
            merged_only=args.merged_only,
            **periods,
        )
        _, reviewed_count = service.count_pull_requests_reviewed_by_user_in_date_range(
            reviewer=member.login,
            organisation=args.organisation,
            exclude_self_authored=args.exclude_self_reviews,
            **periods,
        )
        if date_range is None:
            date_range = authored_range
        member_display = f"{member.login} ({member.name})" if member.name else member.login
        rows.append((member.login, member_display, authored_count, reviewed_count))

    if date_range:
        start = date_range.start_date.isoformat()
        end = date_range.end_date.isoformat()
        period_text = f" from {start} to {end}"
    else:
        period_text = ""
    print(
        f"Pull request counts for team {args.team} in {args.organisation}{period_text}:",
        flush=True,
    )
    if not rows:
        print("- No team members found.", flush=True)
        return

    total_authored = sum(authored for _, _, authored, _ in rows)
    total_reviewed = sum(reviewed for _, _, _, reviewed in rows)

    name_width = max(len("Member"), *(len(name) for _, name, _, _ in rows))
    include_review_share = args.exclude_self_reviews
    if include_review_share:
        header = f"{'Member':<{name_width}} {'Authored':>10} {'Auth %':>7} {'Reviewed':>10} {'Non-self %':>11}"
    else:
        header = f"{'Member':<{name_width}} {'Authored':>10} {'Auth %':>7} {'Reviewed':>10}"
    print(header, flush=True)
    print("-" * len(header), flush=True)
    for _, name, authored_count, reviewed_count in rows:
        authored_share = f"{(authored_count / total_authored) * 100:.1f}%" if total_authored else "n/a"
        if include_review_share:
            other_members_authored = total_authored - authored_count
            reviewable_prs_count = max(other_members_authored, 0)
            reviewed_share = f"{(reviewed_count / reviewable_prs_count) * 100:.1f}%" if reviewable_prs_count else "n/a"
            print(
                f"{name:<{name_width}} {authored_count:>10} {authored_share:>7} "
                f"{reviewed_count:>10} {reviewed_share:>11}",
                flush=True,
            )
        else:
            print(
                f"{name:<{name_width}} {authored_count:>10} {authored_share:>7} {reviewed_count:>10}",
                flush=True,
            )

    print("-" * len(header), flush=True)
    if include_review_share:
        print(
            f"{'Team total':<{name_width}} {total_authored:>10} {'100%':>7} {total_reviewed:>10} {'n/a':>11}",
            flush=True,
        )
    else:
        print(
            f"{'Team total':<{name_width}} {total_authored:>10} {'100%':>7} {total_reviewed:>10}",
            flush=True,
        )


def main() -> None:
    args = parse_args()
    if args.team:
        args.counts_only = True
    periods = parse_period_inputs(args)

    access_token = require_env("GITHUB_ACCESS_TOKEN")
    client = GitHubClient(access_token=access_token)
    service = PullRequestStatisticsService(client, page_size=args.page_size)
    team_service = TeamMembersService(client, page_size=args.page_size)

    if args.team:
        print_team_statistics(args, periods=periods, service=service, team_service=team_service)
        return

    reviewer = args.reviewer or args.author
    authored, (authored_range, authored_count) = gather_authored_statistics(args, periods=periods, service=service)
    reviewed, (reviewed_range, reviewed_count) = gather_reviewed_statistics(
        args,
        reviewer,
        periods=periods,
        service=service,
    )
    print_authored_results(args, authored, authored_range, authored_count)
    print_reviewed_results(args, reviewer, reviewed, reviewed_range, reviewed_count)


if __name__ == "__main__":
    main()
