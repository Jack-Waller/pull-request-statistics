"""
Command-line entry point for pull request statistics.

Environment variables:
    GITHUB_ACCESS_TOKEN: Required. Token with permission to run search queries.
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime

from github_client import (
    DateRange,
    GitHubClient,
    Half,
    MemberStatistics,
    Month,
    PullRequestStatisticsService,
    Quarter,
    TeamMember,
    TeamMembersService,
)
from require_env import require_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gather pull request statistics for authored and reviewed PRs.")
    parser.add_argument(
        "--user",
        action="append",
        help="GitHub login of the user to analyse for authored and reviewed PRs. Repeat to include multiple users.",
    )
    parser.add_argument("--team", help="Team slug within the organisation to list members for.")
    parser.add_argument("--organisation", required=True, help="GitHub organisation to search within.")
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
    if not args.user and not args.team:
        parser.error("Provide at least one --user or a --team to analyse.")
    return args


def default_periods(args: argparse.Namespace) -> None:
    """Populate default period values when none were provided."""
    if any((args.quarter, args.half, args.month, args.year, args.on_date, args.week)):
        return
    today = datetime.now(UTC).date()
    current_quarter = Quarter(((today.month - 1) // 3) + 1)
    args.quarter = current_quarter.name


def parse_period_inputs(args: argparse.Namespace) -> dict:
    """Normalise CLI period inputs into service arguments."""
    default_periods(args)
    quarter = Quarter.from_string(args.quarter) if args.quarter else None
    half = Half.from_string(args.half) if args.half else None
    month = Month.from_string(args.month) if args.month else None
    on_date = date.fromisoformat(args.on_date) if args.on_date else None
    return {
        "quarter": quarter,
        "half": half,
        "month": month,
        "year": args.year,
        "on_date": on_date,
        "week": args.week,
    }


def _merge_members(*member_lists: list[TeamMember]) -> list[TeamMember]:
    merged: dict[str, TeamMember] = {}
    for members in member_lists:
        for member in members:
            key = member.login.lower()
            existing = merged.get(key)
            if existing is None or (not existing.name and member.name):
                merged[key] = member
    return list(merged.values())


def resolve_members(
    args: argparse.Namespace,
    *,
    team_service: TeamMembersService,
) -> list[TeamMember]:
    explicit_members = [TeamMember(login=login, name=None) for login in (args.user or [])]
    team_members: list[TeamMember] = []
    if args.team:
        team_members = team_service.list_team_members(args.team)
    return _merge_members(explicit_members, team_members)


def gather_authored_statistics(
    *,
    user_login: str,
    args: argparse.Namespace,
    periods: dict,
    service: PullRequestStatisticsService,
) -> tuple[list, tuple[DateRange, int]]:
    authored = []
    if not args.counts_only:
        authored = list(
            service.iter_pull_requests_by_author_in_date_range(
                author=user_login,
                merged_only=args.merged_only,
                **periods,
            )
        )
    authored_range, authored_count = service.count_pull_requests_by_author_in_date_range(
        author=user_login,
        merged_only=args.merged_only,
        **periods,
    )
    return authored, (authored_range, authored_count)


def gather_reviewed_statistics(
    *,
    reviewer: str,
    args: argparse.Namespace,
    periods: dict,
    service: PullRequestStatisticsService,
) -> tuple[list, tuple[DateRange, int]]:
    reviewed = []
    if not args.counts_only:
        reviewed = list(
            service.iter_pull_requests_reviewed_by_user_in_date_range(
                reviewer=reviewer,
                exclude_self_authored=args.exclude_self_reviews,
                **periods,
            )
        )
    reviewed_range, reviewed_count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer=reviewer,
        exclude_self_authored=args.exclude_self_reviews,
        **periods,
    )
    return reviewed, (reviewed_range, reviewed_count)


def print_authored_results(
    args: argparse.Namespace,
    user_login: str,
    authored: list,
    authored_range: DateRange,
    authored_count: int,
) -> None:
    merged_suffix = " Merged only." if args.merged_only else ""
    print(
        (
            f"Authored PRs for {user_login} in {args.organisation}: {authored_count} "
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
    reviewed_range: DateRange,
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


def print_member_statistics(
    args: argparse.Namespace,
    *,
    members: list[TeamMember],
    label: str,
    date_range: DateRange | None,
    statistics: list[MemberStatistics],
) -> None:
    member_lookup = {member.login.lower(): member for member in members}
    rows: list[tuple[str, str, int, int]] = []

    for stat in statistics:
        member = member_lookup.get(stat.login.lower())
        display_name = f"{stat.login} ({member.name})" if member and member.name else stat.login
        rows.append((stat.login, display_name, stat.authored_count, stat.reviewed_count))

    if date_range:
        start = date_range.start_date.isoformat()
        end = date_range.end_date.isoformat()
        period_text = f" from {start} to {end}"
    else:
        period_text = ""
    print(f"Pull request counts for {label} in {args.organisation}{period_text}:", flush=True)
    if not rows:
        print("- No members found.", flush=True)
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
            row_text = (
                f"{name:<{name_width}} {authored_count:>10} {authored_share:>7} "
                f"{reviewed_count:>10} {reviewed_share:>11}"
            )
            print(row_text, flush=True)
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
    periods = parse_period_inputs(args)

    access_token = require_env("GITHUB_ACCESS_TOKEN")
    client = GitHubClient(access_token=access_token)
    service = PullRequestStatisticsService(client, organisation=args.organisation, page_size=args.page_size)
    team_service = TeamMembersService(client, organisation=args.organisation, page_size=args.page_size)

    members = resolve_members(args, team_service=team_service)
    if not members:
        print("No members to analyse.", flush=True)
        return

    multiple_members = len(members) > 1
    if args.team or multiple_members:
        args.counts_only = True
        if args.team and args.user:
            label = f"team {args.team} and specified users"
        elif args.team:
            label = f"team {args.team}"
        else:
            label = "specified users"
        date_range, statistics = service.count_member_statistics(
            members=[member.login for member in members],
            merged_only=args.merged_only,
            exclude_self_authored=args.exclude_self_reviews,
            **periods,
        )
        print_member_statistics(
            args,
            members=members,
            label=label,
            date_range=date_range,
            statistics=statistics,
        )
        return

    single_member = members[0]
    user_login = single_member.login
    reviewer = user_login
    authored, (authored_range, authored_count) = gather_authored_statistics(
        user_login=user_login,
        args=args,
        periods=periods,
        service=service,
    )
    reviewed, (reviewed_range, reviewed_count) = gather_reviewed_statistics(
        reviewer=reviewer,
        args=args,
        periods=periods,
        service=service,
    )
    print_authored_results(args, user_login, authored, authored_range, authored_count)
    print_reviewed_results(args, reviewer, reviewed, reviewed_range, reviewed_count)


if __name__ == "__main__":
    main()
