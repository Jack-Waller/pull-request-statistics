"""Unit tests for the GitHub client helpers."""

from uuid import uuid4

import pytest

from github_client.client import (
    GITHUB_GRAPHQL_ENDPOINT,
    GitHubClient,
)
from github_client.errors import GitHubClientError


@pytest.fixture
def github_client() -> GitHubClient:
    """Provide a GitHub client with a dummy token for tests."""
    return GitHubClient(access_token=uuid4().hex)


def test_query_graphql_returns_data(requests_mock, github_client):
    """Successful responses should return the data payload."""
    expected_data = {"viewer": {"login": "octocat"}}
    requests_mock.post(
        GITHUB_GRAPHQL_ENDPOINT,
        json={"data": expected_data},
        status_code=200,
    )

    result = github_client.query_graphql("query { viewer { login } }")

    assert result == expected_data
    last_request = requests_mock.last_request
    assert last_request is not None
    assert last_request.json() == {"query": "query { viewer { login } }"}


def test_query_graphql_sends_variables(requests_mock, github_client):
    """Variables should be forwarded verbatim to the API call."""
    requests_mock.post(
        GITHUB_GRAPHQL_ENDPOINT,
        json={"data": {"node": {"id": "123"}}},
    )
    variables = {"nodeId": "123"}

    github_client.query_graphql("query($nodeId: ID!) { node(id: $nodeId) { id }}", variables=variables)

    last_request = requests_mock.last_request
    assert last_request is not None
    assert last_request.json()["variables"] == variables


def test_query_graphql_raises_on_http_error(requests_mock, github_client):
    """HTTP failures should be wrapped in the custom client error."""
    requests_mock.post(GITHUB_GRAPHQL_ENDPOINT, status_code=401, json={"message": "nope"}, reason="Unauthorized")

    with pytest.raises(GitHubClientError) as error_info:
        github_client.query_graphql("query { viewer { login } }")

    assert "request failed" in str(error_info.value)


def test_query_graphql_raises_on_invalid_json(requests_mock, github_client):
    """Non JSON responses should be rejected with a descriptive error."""
    requests_mock.post(GITHUB_GRAPHQL_ENDPOINT, text="not json", status_code=200)

    with pytest.raises(GitHubClientError):
        github_client.query_graphql("query { viewer { login } }")


def test_query_graphql_raises_on_graphql_errors(requests_mock, github_client):
    """GraphQL error payloads should raise the client exception."""
    requests_mock.post(
        GITHUB_GRAPHQL_ENDPOINT,
        json={"errors": [{"message": "Something went wrong"}]},
        status_code=200,
    )

    with pytest.raises(GitHubClientError):
        github_client.query_graphql("query { viewer { login } }")


def test_query_graphql_requires_data_field(requests_mock, github_client):
    """The response must contain a ``data`` field for the caller."""
    requests_mock.post(GITHUB_GRAPHQL_ENDPOINT, json={"something": "else"}, status_code=200)

    with pytest.raises(GitHubClientError):
        github_client.query_graphql("query { viewer { login } }")


def test_query_graphql_wraps_transport_errors(requests_mock):
    """Unexpected transport issues should become ``GitHubClientError``."""
    client = GitHubClient(access_token=uuid4().hex)
    requests_mock.post(GITHUB_GRAPHQL_ENDPOINT, exc=RuntimeError("boom"))

    with pytest.raises(GitHubClientError):
        client.query_graphql("query { viewer { login } }")
