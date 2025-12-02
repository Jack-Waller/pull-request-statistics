"""
Fetch members of a GitHub team using the GraphQL API.

This module isolates the query shape and pagination logic required to retrieve
team members. Callers receive simple value objects representing each member and
do not need to manage cursors or unpack GraphQL responses.
"""

from __future__ import annotations

from collections.abc import Iterator

from github_client.client import GitHubClient
from github_client.errors import MalformedResponseError
from github_client.team_members.team_member import TeamMember

TEAM_MEMBERS_QUERY = """
query($organisation: String!, $team: String!, $pageSize: Int!, $after: String) {
  organization(login: $organisation) {
    team(slug: $team) {
      members(first: $pageSize, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          login
          name
        }
      }
    }
  }
}
"""


def _build_member(node: dict) -> TeamMember:
    """
    Convert a raw GraphQL node into a ``GitHubTeamMember`` instance.

    Args:
        node: Member node returned by the GitHub API.

    Returns:
        ``GitHubTeamMember`` populated from the provided node.

    Raises:
        MalformedResponseError: When the required ``login`` field is missing.
    """
    login = node.get("login")
    if not login:
        raise MalformedResponseError("GitHub response missing login for a team member")
    return TeamMember(login=login, name=node.get("name"))


def _extract_members_page(
    data: dict,
    organisation: str,
    team_slug: str,
) -> tuple[list[dict], bool, str | None]:
    """
    Extract member nodes and pagination data from a GraphQL response.

    Args:
        data: The parsed response returned by the GitHub client.
        organisation: Organisation login, for error messages.
        team_slug: Team slug, for error messages.

    Returns:
        Tuple containing the member nodes, the ``hasNextPage`` flag, and
        the next cursor when more data remains.

    Raises:
        MalformedResponseError: When any expected field is absent.
    """
    organisation_data = data.get("organization")
    if organisation_data is None:
        raise MalformedResponseError("GitHub response missing organisation data when listing team members")

    team_data = organisation_data.get("team")
    if team_data is None:
        raise MalformedResponseError(f"Team '{team_slug}' was not found in organisation '{organisation}'")

    members = team_data.get("members")
    if members is None:
        raise MalformedResponseError("GitHub response missing members data when listing team members")

    nodes = members.get("nodes")
    if nodes is None:
        raise MalformedResponseError("GitHub response missing member entries when listing team members")

    page_info = members.get("pageInfo")
    if page_info is None:
        raise MalformedResponseError("GitHub response missing pagination info when listing team members")

    has_next_page = page_info.get("hasNextPage")
    if has_next_page is None:
        raise MalformedResponseError("GitHub response missing next page indicator when listing team members")

    cursor = page_info.get("endCursor")
    if has_next_page and cursor is None:
        raise MalformedResponseError("GitHub response missing cursor for additional pages of team members")

    return nodes, bool(has_next_page), cursor


class TeamMembersService:
    """
    Provide helpers for listing team members from GitHub.

    The service exposes both iterator and list-based methods. It handles
    pagination internally, performing successive GraphQL calls until all
    members have been retrieved. Errors raised include descriptive context to
    make troubleshooting API issues straightforward.
    """

    def __init__(self, client: GitHubClient, organisation: str, *, page_size: int = 100) -> None:
        """
        Create a service that queries the GitHub GraphQL API.

        Args:
            client: Authenticated GitHub client instance.
            organisation: GitHub organisation login to search within.
            page_size: Number of member nodes to fetch per GraphQL request.
        """
        self._client = client
        self._organisation = organisation
        self._page_size = page_size

    def list_team_members(self, team_slug: str) -> list[TeamMember]:
        """
        Return all members of a GitHub team.

        Args:
            team_slug: The slug of the team to fetch members for.

        Returns:
            A list of ``GitHubTeamMember`` entries.

        Raises:
            MalformedResponseError: When the GraphQL response is missing expected
                fields or the organisation or team cannot be found.
        """
        return list(self.iter_team_members(team_slug=team_slug))

    def iter_team_members(self, team_slug: str) -> Iterator[TeamMember]:
        """
        Yield members of a team, handling pagination internally.

        Yields:
            ``GitHubTeamMember`` objects for each member returned by GitHub.

        Raises:
            MalformedResponseError: When required fields are missing from responses.
        """
        cursor: str | None = None

        while True:
            data = self._client.query_graphql(
                TEAM_MEMBERS_QUERY,
                variables={
                    "organisation": self._organisation,
                    "team": team_slug,
                    "pageSize": self._page_size,
                    "after": cursor,
                },
            )

            nodes, has_next_page, cursor = _extract_members_page(data, self._organisation, team_slug)
            for node in nodes:
                yield _build_member(node)

            if not has_next_page:
                break
