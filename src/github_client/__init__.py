"""
User friendly surface that exposes GitHub API helpers.

Applications should import :class:`github_client.client.GitHubClient` from this
module rather than reaching into submodules directly so future refactors can
avoid breaking call sites.
"""

from .client import GitHubClient
from .pull_request_statistics import (
    MemberStatistics,
    PullRequestStatisticsService,
    PullRequestSummary,
)
from .pull_request_statistics.date_ranges import Half, Month, Quarter
from .team_members import TeamMember, TeamMembersService

__all__ = [
    "GitHubClient",
    "TeamMember",
    "TeamMembersService",
    "PullRequestStatisticsService",
    "PullRequestSummary",
    "MemberStatistics",
    "Half",
    "Month",
    "Quarter",
]
