"""
Helpers for retrieving pull request information from GitHub.

The package offers a small service that composes GraphQL search queries using
the shared ``GitHubClient`` and converts responses into simple Python objects.
It supports date range filtering, optional merged-only filtering, and safe
pagination across all results returned by GitHub's search API.
"""

from github_client.pull_request_statistics.models import MemberStatistics, PullRequestSummary
from github_client.pull_request_statistics.pull_request_statistics_service import (
    COUNT_QUERY,
    LIST_QUERY,
    REVIEW_COUNT_QUERY,
    REVIEW_LIST_QUERY,
    PullRequestStatisticsService,
)

__all__ = [
    "PullRequestStatisticsService",
    "PullRequestSummary",
    "MemberStatistics",
    "COUNT_QUERY",
    "LIST_QUERY",
    "REVIEW_COUNT_QUERY",
    "REVIEW_LIST_QUERY",
]
