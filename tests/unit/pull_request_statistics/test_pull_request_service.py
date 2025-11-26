"""Unit tests for pull request statistics queries."""

from datetime import UTC, date, datetime

import pytest

from pull_request_statistics.errors import PullRequestDataError
from pull_request_statistics.pull_request_service import REVIEW_COUNT_QUERY
from pull_request_statistics.pull_request_summary import PullRequestSummary


def test_build_search_query_uses_full_range_window(service_with_mocked_client):
    """The search query should constrain results to the requested date range."""
    service, _ = service_with_mocked_client(responses=[])
    search_query = service._build_search_query(
        author="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 3),
    )

    assert search_query == "author:octocat org:skyscanner is:pr created:2024-12-01T00:00:00Z..2024-12-03T23:59:59Z"


def test_build_search_query_can_include_merged_filter(service_with_mocked_client):
    """The search query should include merged filter when requested."""
    service, _ = service_with_mocked_client(responses=[])

    search_query = service._build_search_query(
        author="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 3),
        merged_only=True,
    )

    assert "is:merged" in search_query


def test_count_pull_requests_returns_issue_count(service_with_mocked_client):
    """The count method should return the issueCount from the GraphQL response."""
    service, calls = service_with_mocked_client(responses=[{"search": {"issueCount": 3}}])

    result = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 2),
    )

    assert result == 3
    assert calls[0]["variables"]["query"].startswith("author:octocat org:skyscanner")


def test_list_pull_requests_returns_parsed_summaries(service_with_mocked_client):
    """Pull requests should be converted into summary objects."""
    response = {
        "search": {
            "issueCount": 1,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 42,
                    "title": "Improve documentation",
                    "url": "https://github.com/skyscanner/example/pull/42",
                    "createdAt": "2024-12-01T10:00:00Z",
                    "author": {"login": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                }
            ],
        }
    }
    service, _ = service_with_mocked_client(responses=[response])

    summaries = list(
        service.iter_pull_requests_by_author_in_date_range(
            author="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 1),
        )
    )

    assert summaries == [
        PullRequestSummary(
            number=42,
            title="Improve documentation",
            url="https://github.com/skyscanner/example/pull/42",
            created_at=datetime(2024, 12, 1, 10, 0, tzinfo=UTC),
            author="octocat",
            repository="skyscanner/example",
        )
    ]


def test_list_pull_requests_paginates_until_complete(service_with_mocked_client):
    """Multiple pages should be fetched until hasNextPage is false."""
    first_page = {
        "search": {
            "issueCount": 3,
            "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR_1"},
            "nodes": [
                {
                    "number": 1,
                    "title": "First",
                    "url": "https://github.com/skyscanner/example/pull/1",
                    "createdAt": "2024-12-01T08:00:00Z",
                    "author": {"login": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                }
            ],
        }
    }
    second_page = {
        "search": {
            "issueCount": 3,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                None,
                {
                    "number": 2,
                    "title": "Second",
                    "url": "https://github.com/skyscanner/example/pull/2",
                    "createdAt": "2024-12-01T09:00:00Z",
                    "author": {"login": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                },
                {
                    "number": 3,
                    "title": "Third",
                    "url": "https://github.com/skyscanner/example/pull/3",
                    "createdAt": "2024-12-01T11:00:00Z",
                    "author": {"login": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                },
            ],
        }
    }
    service, calls = service_with_mocked_client(responses=[first_page, second_page], page_size=1)

    summaries = list(
        service.iter_pull_requests_by_author_in_date_range(
            author="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 1),
        )
    )

    assert len(summaries) == 3
    assert calls[0]["variables"]["after"] is None
    assert calls[1]["variables"]["after"] == "CURSOR_1"


def test_count_pull_requests_reviewed_by_user_in_date_range(service_with_mocked_client):
    """The count method should return the issueCount for reviewed queries."""
    response = {
        "search": {
            "issueCount": 2,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 10,
                    "title": "Reviewed",
                    "url": "https://github.com/skyscanner/example/pull/10",
                    "createdAt": "2024-12-01T12:00:00Z",
                    "author": {"login": "another"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-01T12:30:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    service, calls = service_with_mocked_client(responses=[response])

    result = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 2),
    )

    assert result == 1
    assert calls[0]["query"].strip() == REVIEW_COUNT_QUERY.strip()
    query = calls[0]["variables"]["query"]
    assert query.startswith("reviewed-by:octocat org:skyscanner is:pr updated:")


def test_count_pull_requests_reviewed_skips_none_and_self_authored(service_with_mocked_client):
    """Count should ignore None nodes and self-authored pull requests when requested."""
    response = {
        "search": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                None,
                {
                    "author": {"login": "octocat"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                },
            ],
        }
    }
    service, _ = service_with_mocked_client(responses=[response])

    count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 2),
        exclude_self_authored=True,
    )

    assert count == 0


def test_count_pull_requests_reviewed_handles_pagination(service_with_mocked_client):
    """Count pagination should advance cursors when next pages exist."""
    first_page = {
        "search": {
            "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR_REVIEW"},
            "nodes": [None],
        }
    }
    second_page = {
        "search": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "author": {"login": "other"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    service, calls = service_with_mocked_client(responses=[first_page, second_page], page_size=1)

    count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 2),
    )

    assert count == 1
    assert calls[0]["variables"]["after"] is None
    assert calls[1]["variables"]["after"] == "CURSOR_REVIEW"


def test_iter_pull_requests_reviewed_by_user_excludes_self_authored(service_with_mocked_client):
    """Exclude self-authored PRs when requested."""
    response = {
        "search": {
            "issueCount": 1,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 5,
                    "title": "Reviewed change",
                    "url": "https://github.com/skyscanner/example/pull/5",
                    "createdAt": "2024-12-01T12:00:00Z",
                    "author": {"login": "other-user"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-01T12:30:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    service, calls = service_with_mocked_client(responses=[response])

    summaries = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 2),
            exclude_self_authored=True,
        )
    )

    assert len(summaries) == 1
    assert "-author:octocat" in calls[0]["variables"]["query"]


def test_iter_pull_requests_reviewed_paginates_and_skips_none_nodes(service_with_mocked_client):
    """Pagination should advance cursors and ignore None nodes for reviewed queries."""
    first_page = {
        "search": {
            "issueCount": 2,
            "pageInfo": {"hasNextPage": True, "endCursor": "CURSOR_REVIEW"},
            "nodes": [None],
        }
    }
    second_page = {
        "search": {
            "issueCount": 2,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 6,
                    "title": "Reviewed later",
                    "url": "https://github.com/skyscanner/example/pull/6",
                    "createdAt": "2024-12-02T12:00:00Z",
                    "author": {"login": "another"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    service, calls = service_with_mocked_client(responses=[first_page, second_page], page_size=1)

    summaries = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 2),
        )
    )

    assert len(summaries) == 1
    assert calls[0]["variables"]["after"] is None
    assert calls[1]["variables"]["after"] == "CURSOR_REVIEW"


def test_review_search_rejects_inverted_dates(service_with_mocked_client):
    """Review search should validate date ordering."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(ValueError, match="end_date must not be earlier than start_date"):
        service._build_review_search_query(
            reviewer="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 2),
            end_date=date(2024, 12, 1),
            exclude_self_authored=False,
        )


def test_iter_pull_requests_reviewed_skips_self_authored_when_requested(service_with_mocked_client):
    """Self-authored pull requests should be skipped when exclude_self_authored is True."""
    response = {
        "search": {
            "issueCount": 1,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 7,
                    "title": "Self-authored PR",
                    "url": "https://github.com/skyscanner/example/pull/7",
                    "createdAt": "2024-12-01T12:00:00Z",
                    "author": {"login": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-01T12:30:00Z",
                                    "author": {"login": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    service, _ = service_with_mocked_client(responses=[response])

    summaries = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 2),
            exclude_self_authored=True,
        )
    )

    assert summaries == []


def test_iter_pull_requests_reviewed_ignores_invalid_review_timestamps(service_with_mocked_client):
    """Invalid review timestamps should be ignored, leading to no results."""
    response = {
        "search": {
            "issueCount": 1,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 8,
                    "title": "Bad review time",
                    "url": "https://github.com/skyscanner/example/pull/8",
                    "createdAt": "2024-12-01T12:00:00Z",
                    "author": {"login": "other"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {"edges": [{"node": {"createdAt": "invalid", "author": {"login": "octocat"}}}]},
                }
            ],
        }
    }
    service, _ = service_with_mocked_client(responses=[response])

    summaries = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 2),
        )
    )

    assert summaries == []


def test_extract_helpers_raise_when_missing_data(service_with_mocked_client):
    """Helper extractors should raise PullRequestDataError when fields are missing."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(PullRequestDataError, match="search data"):
        service._extract_search({})
    with pytest.raises(PullRequestDataError, match="issueCount"):
        service._extract_issue_count({})
    with pytest.raises(PullRequestDataError, match="pageInfo"):
        service._extract_page_info({})


def test_iter_pull_requests_reviewed_exercises_all_review_filters(service_with_mocked_client):
    """Review parsing should skip None nodes, author mismatches, and missing timestamps."""
    response = {
        "search": {
            "issueCount": 1,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [
                {
                    "number": 9,
                    "title": "Various reviews",
                    "url": "https://github.com/skyscanner/example/pull/9",
                    "createdAt": "2024-12-01T12:00:00Z",
                    "author": {"login": "another"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {"node": None},
                            {"node": {"createdAt": "2024-12-01T12:00:00Z", "author": {"login": "someone-else"}}},
                            {"node": {"author": {"login": "octocat"}}},
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"login": "octocat"},
                                }
                            },
                        ]
                    },
                }
            ],
        }
    }
    service, _ = service_with_mocked_client(responses=[response])

    summaries = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 2),
        )
    )

    assert len(summaries) == 1
    # Count method uses the same review filtering logic; ensure it also matches.
    service, _ = service_with_mocked_client(responses=[response])
    count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        start_date=date(2024, 12, 1),
        end_date=date(2024, 12, 2),
    )
    assert count == 1


def test_page_size_validation(service_with_mocked_client):
    """Invalid page sizes should be rejected clearly."""
    with pytest.raises(ValueError, match="page_size"):
        service_with_mocked_client(responses=[], page_size=0)


def test_end_date_not_before_start_date(service_with_mocked_client):
    """The search should reject inverted date ranges."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(ValueError, match="end_date must not be earlier than start_date"):
        service._build_search_query(
            author="octocat",
            organisation="skyscanner",
            start_date=date(2024, 12, 2),
            end_date=date(2024, 12, 1),
        )
