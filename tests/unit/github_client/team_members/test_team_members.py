"""Unit tests for the GitHub team member helpers."""

from uuid import uuid4

import pytest

from github_client.client import GitHubClient
from github_client.errors import MalformedResponseError
from github_client.team_members import TeamMembersService

GRAPHQL_ENDPOINT = "https://api.github.com/graphql"


@pytest.fixture
def team_service() -> TeamMembersService:
    """Provide a team member service backed by a dummy GitHub client."""
    client = GitHubClient(access_token=uuid4().hex)
    return TeamMembersService(client, organisation="skyscanner", page_size=2)


def test_list_team_members_returns_members(requests_mock, team_service: TeamMembersService) -> None:
    """Team members should be returned with both login and name data."""
    requests_mock.post(
        GRAPHQL_ENDPOINT,
        json={
            "data": {
                "organization": {
                    "team": {
                        "members": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {"login": "alice", "name": "Alice Example"},
                                {"login": "bob", "name": None},
                            ],
                        }
                    }
                }
            }
        },
    )

    members = team_service.list_team_members("mighty-llamas")

    assert [member.login for member in members] == ["alice", "bob"]
    assert members[0].name == "Alice Example"
    assert members[1].name is None
    last_request = requests_mock.last_request
    assert last_request is not None
    assert last_request.json()["variables"] == {
        "organisation": "skyscanner",
        "team": "mighty-llamas",
        "pageSize": 2,
        "after": None,
    }


def test_list_team_members_paginates(requests_mock, team_service: TeamMembersService) -> None:
    """The service should continue fetching pages until ``hasNextPage`` is false."""
    requests_mock.post(
        GRAPHQL_ENDPOINT,
        [
            {
                "json": {
                    "data": {
                        "organization": {
                            "team": {
                                "members": {
                                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                                    "nodes": [{"login": "alice", "name": None}],
                                }
                            }
                        }
                    }
                }
            },
            {
                "json": {
                    "data": {
                        "organization": {
                            "team": {
                                "members": {
                                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                                    "nodes": [{"login": "bob", "name": "Bob Example"}],
                                }
                            }
                        }
                    }
                }
            },
        ],
    )

    members = team_service.list_team_members("mighty-llamas")

    assert [member.login for member in members] == ["alice", "bob"]
    assert requests_mock.call_count == 2
    assert requests_mock.request_history[0].json()["variables"]["after"] is None
    assert requests_mock.request_history[1].json()["variables"]["after"] == "cursor-1"


def test_list_team_members_raises_when_team_missing(requests_mock, team_service: TeamMembersService) -> None:
    """A missing team should raise an error rather than returning an empty list."""
    requests_mock.post(
        GRAPHQL_ENDPOINT,
        json={"data": {"organization": {"team": None}}},
    )

    with pytest.raises(MalformedResponseError):
        team_service.list_team_members("unknown-team")


def test_iter_team_members_requires_login(requests_mock, team_service: TeamMembersService) -> None:
    """Each member entry must include a login value."""
    requests_mock.post(
        GRAPHQL_ENDPOINT,
        json={
            "data": {
                "organization": {
                    "team": {
                        "members": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [{"name": "Nameless"}],
                        }
                    }
                }
            }
        },
    )

    with pytest.raises(MalformedResponseError):
        list(team_service.iter_team_members("mighty-llamas"))


@pytest.mark.parametrize(
    ("response_json", "message"),
    [
        ({"data": {}}, "organisation data"),
        ({"data": {"organization": {}}}, "not found"),
        ({"data": {"organization": {"team": None}}}, "not found"),
        ({"data": {"organization": {"team": {"members": None}}}}, "members data"),
        (
            {"data": {"organization": {"team": {"members": {"pageInfo": {"hasNextPage": False}, "nodes": None}}}}},
            "member entries",
        ),
        ({"data": {"organization": {"team": {"members": {"pageInfo": None, "nodes": []}}}}}, "pagination info"),
        (
            {"data": {"organization": {"team": {"members": {"pageInfo": {"hasNextPage": None}, "nodes": []}}}}},
            "next page indicator",
        ),
        (
            {"data": {"organization": {"team": {"members": {"pageInfo": {"endCursor": None}, "nodes": []}}}}},
            "next page indicator",
        ),
    ],
)
def test_iter_team_members_raises_on_malformed_structures(
    requests_mock, team_service: TeamMembersService, response_json: dict, message: str
) -> None:
    """Malformed GraphQL structures should raise MalformedResponseError."""
    requests_mock.post(GRAPHQL_ENDPOINT, json=response_json)

    with pytest.raises(MalformedResponseError, match=message):
        list(team_service.iter_team_members("mighty-llamas"))


def test_iter_team_members_requires_cursor_when_more_pages_exist(
    requests_mock, team_service: TeamMembersService
) -> None:
    """When hasNextPage is true, a cursor must be provided."""
    requests_mock.post(
        GRAPHQL_ENDPOINT,
        json={
            "data": {
                "organization": {
                    "team": {
                        "members": {
                            "pageInfo": {"hasNextPage": True, "endCursor": None},
                            "nodes": [],
                        }
                    }
                }
            }
        },
    )

    with pytest.raises(MalformedResponseError, match="cursor"):
        list(team_service.iter_team_members("mighty-llamas"))
