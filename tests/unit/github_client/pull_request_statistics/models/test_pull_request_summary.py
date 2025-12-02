"""Unit tests for pull request summary parsing."""

from datetime import UTC, datetime

import pytest

from github_client.errors import MalformedResponseError
from github_client.pull_request_statistics.models import PullRequestSummary


def test_from_graphql_parses_complete_node():
    """A complete node should parse into a populated summary."""
    node = {
        "number": 10,
        "title": "Add feature",
        "url": "https://github.com/skyscanner/example/pull/10",
        "createdAt": "2024-01-02T03:04:05Z",
        "author": {"login": "octocat"},
        "repository": {"nameWithOwner": "skyscanner/example"},
    }

    summary = PullRequestSummary.from_graphql(node)

    assert summary.author == "octocat"
    assert summary.created_at == datetime(2024, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_from_graphql_defaults_author_when_missing():
    """Missing author information should default to 'unknown'."""
    node = {
        "number": 11,
        "title": "Anonymous fix",
        "url": "https://github.com/skyscanner/example/pull/11",
        "createdAt": "2024-01-02T03:04:05Z",
        "author": None,
        "repository": {"nameWithOwner": "skyscanner/example"},
    }

    summary = PullRequestSummary.from_graphql(node)

    assert summary.author == "unknown"


def test_from_graphql_raises_on_invalid_timestamp():
    """Invalid timestamps should raise a descriptive error."""
    node = {
        "number": 12,
        "title": "Bad time",
        "url": "https://github.com/skyscanner/example/pull/12",
        "createdAt": "not-a-time",
        "author": {"login": "octocat"},
        "repository": {"nameWithOwner": "skyscanner/example"},
    }

    with pytest.raises(ValueError, match="Could not parse creation time"):
        PullRequestSummary.from_graphql(node)


def test_from_graphql_raises_on_missing_created_at():
    """Missing createdAt should raise the data error."""
    node = {
        "number": 13,
        "title": "No time",
        "url": "https://github.com/skyscanner/example/pull/13",
        "repository": {"nameWithOwner": "skyscanner/example"},
    }

    with pytest.raises(MalformedResponseError, match="createdAt"):
        PullRequestSummary.from_graphql(node)


def test_from_graphql_raises_on_missing_repository_name():
    """Missing repository name should raise the data error."""
    node = {
        "number": 14,
        "title": "No repo",
        "url": "https://github.com/skyscanner/example/pull/14",
        "createdAt": "2024-01-02T03:04:05Z",
        "repository": {},
    }

    with pytest.raises(MalformedResponseError, match="repository"):
        PullRequestSummary.from_graphql(node)


def test_from_graphql_raises_on_missing_required_fields():
    """Missing number/title/url should raise the data error."""
    node = {
        "createdAt": "2024-01-02T03:04:05Z",
        "repository": {"nameWithOwner": "skyscanner/example"},
    }

    with pytest.raises(MalformedResponseError, match="required fields"):
        PullRequestSummary.from_graphql(node)
