"""Integration tests for pull request statistics built on mocked GitHub responses."""

from github_client import GitHubClient, MemberStatistics, Month, PullRequestStatisticsService

GRAPHQL_URL = "https://api.github.com/graphql"


def _build_service() -> PullRequestStatisticsService:
    return PullRequestStatisticsService(
        GitHubClient(access_token="token"),  # noqa: S106 - placeholder token for mocked requests
        organisation="skyscanner",
        page_size=2,
    )


def test_count_pull_requests_for_single_user(requests_mock) -> None:
    service = _build_service()
    requests_mock.post(GRAPHQL_URL, json={"data": {"search": {"issueCount": 4}}})

    _, total = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        month=Month.JANUARY,
        year=2024,
    )

    assert total == 4
    query_text = requests_mock.last_request.json()["variables"]["query"]
    assert query_text.startswith("author:octocat org:skyscanner is:pr created:")
    assert "is:merged" not in query_text


def test_fetch_opened_and_reviewed_pull_requests_for_user(requests_mock) -> None:
    service = _build_service()
    requests_mock.post(
        GRAPHQL_URL,
        response_list=[
            {"json": {"data": {"search": {"issueCount": 2}}}, "status_code": 200},
            {
                "json": {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "author": {"login": "teammate"},
                                    "reviews": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "createdAt": "2024-01-15T10:00:00Z",
                                                    "author": {"login": "octocat"},
                                                }
                                            }
                                        ]
                                    },
                                }
                            ],
                        }
                    }
                },
                "status_code": 200,
            },
        ],
    )

    _, statistics = service.count_member_statistics(
        members=["octocat"],
        month=Month.JANUARY,
        year=2024,
    )

    assert statistics == [
        # 2 opened, 1 reviewed inside the window
        MemberStatistics(login="octocat", authored_count=2, reviewed_count=1)
    ]
    assert "author:octocat" in requests_mock.request_history[0].json()["variables"]["query"]
    assert "reviewed-by:octocat" in requests_mock.request_history[1].json()["variables"]["query"]


def test_fetch_statistics_for_multiple_users(requests_mock) -> None:
    service = _build_service()
    requests_mock.post(
        GRAPHQL_URL,
        response_list=[
            {"json": {"data": {"search": {"issueCount": 2}}}, "status_code": 200},  # alice authored
            {
                "json": {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [],
                        }
                    }
                },
                "status_code": 200,
            },  # alice reviewed
            {"json": {"data": {"search": {"issueCount": 1}}}, "status_code": 200},  # bob authored
            {
                "json": {
                    "data": {
                        "search": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "author": {"login": "carol"},
                                    "reviews": {
                                        "edges": [
                                            {
                                                "node": {
                                                    "createdAt": "2024-01-05T09:00:00Z",
                                                    "author": {"login": "bob"},
                                                }
                                            }
                                        ]
                                    },
                                }
                            ],
                        }
                    }
                },
                "status_code": 200,
            },  # bob reviewed
        ],
    )

    _, statistics = service.count_member_statistics(
        members=["alice", "bob", "alice"],
        month=Month.JANUARY,
        year=2024,
    )

    assert [entry.login for entry in statistics] == ["alice", "bob"]
    assert statistics[0].authored_count == 2
    assert statistics[0].reviewed_count == 0
    assert statistics[1].authored_count == 1
    assert statistics[1].reviewed_count == 1
    assert len(requests_mock.request_history) == 4
