"""
Entry point for running pull request statistics tooling from the command line.

Environment variables:
    GITHUB_ACCESS_TOKEN: Required. Token with permission to run search queries.
    GITHUB_AUTHOR: Optional. GitHub login to filter by. Defaults to ``Jack-Waller``.
    GITHUB_ORGANISATION: Optional. Organisation name. Defaults to ``Skyscanner``.
    GITHUB_PULL_REQUEST_DATE: Optional. Single date to use for both start and end.
    GITHUB_PULL_REQUEST_START_DATE: Optional. ISO date for the start of the range.
    GITHUB_PULL_REQUEST_END_DATE: Optional. ISO date for the end of the range.
    GITHUB_PULL_REQUEST_MERGED_ONLY: Optional. Set to ``true`` to include only merged PRs.
    GITHUB_PULL_REQUEST_REVIEW_EXCLUDE_SELF: Optional. Set to ``true`` to exclude reviews on self-authored PRs.
    GITHUB_PULL_REQUEST_REVIEW_EXCLUDE_SELF: Optional. Set to ``true`` to exclude reviews on self-authored PRs.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from github_client.client import GitHubClient
from pull_request_statistics.pull_request_service import PullRequestStatisticsService
from require_env import require_env


def main() -> None:
    """
    Execute the console entry point.

    The script demonstrates listing and counting pull requests for a given
    author within an organisation across a date range. Authentication requires a
    ``GITHUB_ACCESS_TOKEN`` environment variable with permission to run the
    search queries. When no date inputs are supplied, the default range covers
    the current calendar quarter. Set ``GITHUB_PULL_REQUEST_MERGED_ONLY`` to
    ``true`` to restrict results to merged pull requests.
    """
    access_token = require_env("GITHUB_ACCESS_TOKEN")
    author = require_env("GITHUB_AUTHOR", require=False) or "Jack-Waller"
    organisation = require_env("GITHUB_ORGANISATION", require=False) or "Skyscanner"
    today = datetime.now(UTC).date()
    quarter_index = (today.month - 1) // 3
    start_month = quarter_index * 3 + 1
    start_of_quarter = today.replace(month=start_month, day=1)
    next_quarter_month = start_month + 3
    next_quarter_year = today.year + 1 if next_quarter_month > 12 else today.year
    next_quarter_month = ((next_quarter_month - 1) % 12) + 1
    start_of_next_quarter = start_of_quarter.replace(year=next_quarter_year, month=next_quarter_month, day=1)
    end_of_quarter = start_of_next_quarter - timedelta(days=1)
    default_start_date = start_of_quarter.isoformat()
    default_end_date = end_of_quarter.isoformat()
    single_date = require_env("GITHUB_PULL_REQUEST_DATE", require=False)
    start_date_raw = require_env("GITHUB_PULL_REQUEST_START_DATE", require=False) or single_date or default_start_date
    end_date_raw = require_env("GITHUB_PULL_REQUEST_END_DATE", require=False) or single_date or default_end_date
    start_date = date.fromisoformat(start_date_raw)
    end_date = date.fromisoformat(end_date_raw)
    merged_only = (require_env("GITHUB_PULL_REQUEST_MERGED_ONLY", require=False) or "true").lower() == "true"
    exclude_self_reviews = (
        require_env("GITHUB_PULL_REQUEST_REVIEW_EXCLUDE_SELF", require=False) or "true"
    ).lower() == "true"

    client = GitHubClient(access_token=access_token)
    service = PullRequestStatisticsService(client)

    pull_requests = list(
        service.iter_pull_requests_by_author_in_date_range(
            author=author,
            organisation=organisation,
            start_date=start_date,
            end_date=end_date,
            merged_only=merged_only,
        )
    )
    count = service.count_pull_requests_by_author_in_date_range(
        author=author,
        organisation=organisation,
        start_date=start_date,
        end_date=end_date,
        merged_only=merged_only,
    )

    computed_count = len(pull_requests)
    print(
        (
            "Found "
            f"{count} pull request(s) opened by {author} in {organisation} "
            f"from {start_date.isoformat()} to {end_date.isoformat()}."
            f" Retrieved {computed_count} items from pagination."
        ),
        flush=True,
    )
    if computed_count != count:
        print(f"Warning: count {count} did not match retrieved items {computed_count}.", flush=True)
    for pull_request in pull_requests:
        print(
            f"- {pull_request.repository} #{pull_request.number}: {pull_request.title} ({pull_request.url})",
            flush=True,
        )

    reviewed_pull_requests = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer=author,
            organisation=organisation,
            start_date=start_date,
            end_date=end_date,
            exclude_self_authored=exclude_self_reviews,
        )
    )
    reviewed_count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer=author,
        organisation=organisation,
        start_date=start_date,
        end_date=end_date,
        exclude_self_authored=exclude_self_reviews,
    )
    computed_reviewed_count = len(reviewed_pull_requests)
    print(
        (
            "Found "
            f"{reviewed_count} pull request(s) reviewed by {author} in {organisation} "
            f"from {start_date.isoformat()} to {end_date.isoformat()}."
            f" Retrieved {computed_reviewed_count} items from pagination."
            f"{' Excluding self-authored pull requests.' if exclude_self_reviews else ''}"
        ),
        flush=True,
    )
    if computed_reviewed_count != reviewed_count:
        print(
            f"Warning: review count {reviewed_count} did not match retrieved items {computed_reviewed_count}.",
            flush=True,
        )
    for pull_request in reviewed_pull_requests:
        print(
            f"- REVIEWED {pull_request.repository} #{pull_request.number}: {pull_request.title} ({pull_request.url})",
            flush=True,
        )


if __name__ == "__main__":
    main()
