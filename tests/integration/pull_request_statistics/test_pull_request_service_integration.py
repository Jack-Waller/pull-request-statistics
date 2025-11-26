"""Integration-style tests for pull request statistics with HTTP mocked via requests_mock."""

from datetime import date

import pytest

from github_client.client import GITHUB_GRAPHQL_ENDPOINT, GitHubClient
from pull_request_statistics.pull_request_service import PullRequestStatisticsService


@pytest.fixture
def service() -> PullRequestStatisticsService:
    """Provide a service instance with a dummy GitHub client."""
    return PullRequestStatisticsService(GitHubClient(access_token="x" * 8), page_size=2)


def test_authored_pull_requests_iter_and_count(requests_mock, service):
    """Iterating and counting authored pull requests should drive the expected GraphQL calls."""
    list_response = {
        "search": {
            "issueCount": 2,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 1,
                    "title": "First change",
                    "url": "https://github.com/skyscanner/example/pull/1",
                    "createdAt": "2024-12-01T12:00:00Z",
                    "author": {"login": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                }
            ],
        }
    }
    count_response = {"search": {"issueCount": 2}}
    requests_mock.post(
        GITHUB_GRAPHQL_ENDPOINT,
        response_list=[
            {"json": {"data": list_response}, "status_code": 200},
            {"json": {"data": count_response}, "status_code": 200},
        ],
    )

    authored = list(
        service.iter_pull_requests_by_author_in_date_range(
            author="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 2),
            merged_only=False,
        )
    )
    total = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 2),
        merged_only=False,
    )

    assert len(authored) == 1
    assert authored[0].number == 1
    assert total == 2
    # First request should be the list query.
    assert "author:octocat org:skyscanner" in requests_mock.request_history[0].json()["variables"]["query"]
    # Second request should be the count query.
    assert "author:octocat org:skyscanner" in requests_mock.request_history[1].json()["variables"]["query"]


def test_reviewed_pull_requests_iter_and_count(requests_mock, service):
    """Review queries should filter by reviewer and count via dedicated review query."""
    count_response = {
        "search": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "author": {"login": "other-user"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T10:00:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    list_response = {
        "search": {
            "issueCount": 1,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 7,
                    "title": "Reviewed change",
                    "url": "https://github.com/skyscanner/example/pull/7",
                    "createdAt": "2024-12-02T09:00:00Z",
                    "author": {"login": "other-user"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T10:00:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    requests_mock.post(
        GITHUB_GRAPHQL_ENDPOINT,
        response_list=[
            {"json": {"data": count_response}, "status_code": 200},
            {"json": {"data": list_response}, "status_code": 200},
        ],
    )

    count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 3),
        exclude_self_authored=True,
    )
    reviewed = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 3),
            exclude_self_authored=True,
        )
    )

    assert count == 1
    assert len(reviewed) == 1
    assert reviewed[0].number == 7
    # First request should be the review count query.
    assert "reviewed-by:octocat" in requests_mock.request_history[0].json()["variables"]["query"]
    # Second request should be the review list query.
    assert "reviewed-by:octocat" in requests_mock.request_history[1].json()["variables"]["query"]
