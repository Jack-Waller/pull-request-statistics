"""
Helpers for retrieving pull request information from GitHub.

The package offers a small service that composes GraphQL search queries using
the shared ``GitHubClient`` and converts responses into simple Python objects.
It supports date range filtering, optional merged-only filtering, and safe
pagination across all results returned by GitHub's search API.
"""

from .models import MemberStatistics, PullRequestSummary
from .pull_request_statistics_service import (
    PullRequestStatisticsService,
)

__all__ = [
    "PullRequestStatisticsService",
    "PullRequestSummary",
    "MemberStatistics",
]
