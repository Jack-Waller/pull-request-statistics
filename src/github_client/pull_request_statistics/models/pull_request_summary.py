"""
Lightweight representation of a pull request returned from GitHub.

The summary object converts GraphQL nodes into a convenient Python dataclass
with strongly typed fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from github_client.errors import MalformedResponseError


@dataclass(frozen=True)
class PullRequestSummary:
    """
    Lightweight representation of a pull request returned from GitHub.

    Attributes:
        number: Pull request number within the repository.
        title: Pull request title.
        url: Link to the pull request on GitHub.
        repository: Repository in ``owner/name`` format.
        author: Author username extracted from the GraphQL node, or ``"unknown"`` when absent.
        created_at: Datetime when the pull request was created (timezone aware).
    """

    number: int
    title: str
    url: str
    repository: str
    author: str
    created_at: datetime

    @staticmethod
    def from_graphql(node: dict) -> PullRequestSummary:
        """
        Build a summary object from a GraphQL node.

        Raises:
            MalformedResponseError: when expected fields are missing from the GraphQL response.
            ValueError: when the creation timestamp cannot be parsed.

        Args:
            node: GraphQL node returned by the search query representing a pull request.

        Returns:
            Parsed ``PullRequestSummary`` populated from the node fields.
        """
        created_at_raw = node.get("createdAt")
        if created_at_raw is None:
            raise MalformedResponseError("Pull request node missing createdAt")
        try:
            created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        except ValueError as parse_error:
            raise ValueError(f"Could not parse creation time '{created_at_raw}'") from parse_error

        author = node.get("author", {}) or {}
        repository = node.get("repository") or {}
        name_with_owner = repository.get("nameWithOwner")
        if name_with_owner is None:
            raise MalformedResponseError("Pull request node missing repository.nameWithOwner")
        number = node.get("number")
        title = node.get("title")
        url = node.get("url")
        if number is None or title is None or url is None:
            raise MalformedResponseError("Pull request node missing required fields")
        return PullRequestSummary(
            number=number,
            title=title,
            url=url,
            repository=name_with_owner,
            author=author.get("username", "unknown"),
            created_at=created_at,
        )
