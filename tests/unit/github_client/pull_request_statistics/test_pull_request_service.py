"""Unit tests for pull request statistics queries."""

from datetime import UTC, date, datetime

import pytest

from github_client.errors import MalformedResponseError
from github_client.pull_request_statistics import COUNT_QUERY, REVIEW_COUNT_QUERY
from github_client.pull_request_statistics.date_ranges import DateRange, HalfName, MonthName, QuarterName
from github_client.pull_request_statistics.models import MemberStatistics, PullRequestSummary


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

    date_range, result = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        month=MonthName.DECEMBER,
        year=2024,
    )

    assert date_range == DateRange(start_date=date(2024, 12, 1), end_date=date(2024, 12, 31))
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
                    "author": {"username": "octocat"},
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
            month=MonthName.DECEMBER,
            year=2024,
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
                    "author": {"username": "octocat"},
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
                    "author": {"username": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                },
                {
                    "number": 3,
                    "title": "Third",
                    "url": "https://github.com/skyscanner/example/pull/3",
                    "createdAt": "2024-12-01T11:00:00Z",
                    "author": {"username": "octocat"},
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
            month=MonthName.DECEMBER,
            year=2024,
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
                    "author": {"username": "another"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-01T12:30:00Z",
                                    "author": {"username": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    service, calls = service_with_mocked_client(responses=[response])

    date_range, result = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        month=MonthName.DECEMBER,
        year=2024,
    )

    assert date_range == DateRange(start_date=date(2024, 12, 1), end_date=date(2024, 12, 31))
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
                    "author": {"username": "octocat"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"username": "octocat"},
                                }
                            }
                        ]
                    },
                },
            ],
        }
    }
    service, _ = service_with_mocked_client(responses=[response])

    _, count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        month=MonthName.DECEMBER,
        year=2024,
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
                    "author": {"username": "other"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"username": "octocat"},
                                }
                            }
                        ]
                    },
                }
            ],
        }
    }
    service, calls = service_with_mocked_client(responses=[first_page, second_page], page_size=1)

    _, count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        month=MonthName.DECEMBER,
        year=2024,
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
                    "author": {"username": "other-user"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-01T12:30:00Z",
                                    "author": {"username": "octocat"},
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
            month=MonthName.DECEMBER,
            year=2024,
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
                    "author": {"username": "another"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"username": "octocat"},
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
            month=MonthName.DECEMBER,
            year=2024,
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
                    "author": {"username": "octocat"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {
                                "node": {
                                    "createdAt": "2024-12-01T12:30:00Z",
                                    "author": {"username": "octocat"},
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
            month=MonthName.DECEMBER,
            year=2024,
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
                    "author": {"username": "other"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {"edges": [{"node": {"createdAt": "invalid", "author": {"username": "octocat"}}}]},
                }
            ],
        }
    }
    service, _ = service_with_mocked_client(responses=[response])

    summaries = list(
        service.iter_pull_requests_reviewed_by_user_in_date_range(
            reviewer="octocat",
            organisation="skyscanner",
            month=MonthName.DECEMBER,
            year=2024,
        )
    )

    assert summaries == []


def test_count_member_statistics_returns_counts(service_with_mocked_client):
    """Member statistics should include authored and reviewed counts for each unique member."""
    responses = [
        {"search": {"issueCount": 2}},  # alice authored
        {
            "search": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "author": {"username": "someone"},
                        "reviews": {
                            "edges": [
                                {
                                    "node": {
                                        "createdAt": "2024-12-02T12:30:00Z",
                                        "author": {"username": "alice"},
                                    }
                                }
                            ]
                        },
                    }
                ],
            }
        },
        {"search": {"issueCount": 1}},  # bob authored
        {
            "search": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "author": {"username": "another"},
                        "reviews": {
                            "edges": [
                                {
                                    "node": {
                                        "createdAt": "2024-12-03T12:30:00Z",
                                        "author": {"username": "bob"},
                                    }
                                }
                            ]
                        },
                    }
                ],
            }
        },
    ]
    service, calls = service_with_mocked_client(responses=responses, today=date(2024, 12, 31))

    date_range, statistics = service.count_member_statistics(
        members=["alice", "bob", "alice"],
        organisation="skyscanner",
        month=MonthName.DECEMBER,
        year=2024,
    )

    assert date_range == DateRange(start_date=date(2024, 12, 1), end_date=date(2024, 12, 31))
    assert statistics == [
        MemberStatistics(username="alice", authored_count=2, reviewed_count=1),
        MemberStatistics(username="bob", authored_count=1, reviewed_count=1),
    ]
    assert calls[0]["query"].strip() == COUNT_QUERY.strip()
    assert calls[1]["query"].strip() == REVIEW_COUNT_QUERY.strip()
    assert calls[2]["query"].strip() == COUNT_QUERY.strip()
    assert calls[3]["query"].strip() == REVIEW_COUNT_QUERY.strip()


def test_count_member_statistics_skips_empty_members(service_with_mocked_client):
    """Empty member list should return no statistics."""
    service, _ = service_with_mocked_client(responses=[])

    date_range, statistics = service.count_member_statistics(members=[], organisation="skyscanner", year=2024)

    assert date_range is None
    assert statistics == []


def test_count_reviewed_respects_exclude_self_authored(service_with_mocked_client):
    """Reviewed counting should skip self-authored pull requests when requested."""
    responses = [
        {
            "search": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "author": {"username": "alice"},
                        "reviews": {
                            "edges": [
                                {
                                    "node": {
                                        "createdAt": "2024-12-02T12:30:00Z",
                                        "author": {"username": "alice"},
                                    }
                                }
                            ]
                        },
                    }
                ],
            }
        }
    ]
    service, _ = service_with_mocked_client(responses=responses, today=date(2024, 12, 31))

    _, count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="alice",
        organisation="skyscanner",
        month=MonthName.DECEMBER,
        year=2024,
        exclude_self_authored=True,
    )

    assert count == 0


def test_extract_helpers_raise_when_missing_data(service_with_mocked_client):
    """Helper extractors should raise PullRequestDataError when fields are missing."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(MalformedResponseError, match="search data"):
        service._extract_search({})
    with pytest.raises(MalformedResponseError, match="issueCount"):
        service._extract_issue_count({})
    with pytest.raises(MalformedResponseError, match="pageInfo"):
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
                    "author": {"username": "another"},
                    "repository": {"nameWithOwner": "skyscanner/example"},
                    "reviews": {
                        "edges": [
                            {"node": None},
                            {"node": {"createdAt": "2024-12-01T12:00:00Z", "author": {"username": "someone-else"}}},
                            {"node": {"author": {"username": "octocat"}}},
                            {
                                "node": {
                                    "createdAt": "2024-12-02T12:30:00Z",
                                    "author": {"username": "octocat"},
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
            month=MonthName.DECEMBER,
            year=2024,
        )
    )

    assert len(summaries) == 1
    # Count method uses the same review filtering logic; ensure it also matches.
    service, _ = service_with_mocked_client(responses=[response])
    _, count = service.count_pull_requests_reviewed_by_user_in_date_range(
        reviewer="octocat",
        organisation="skyscanner",
        month=MonthName.DECEMBER,
        year=2024,
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


def test_period_selection_requires_at_least_one_value(service_with_mocked_client):
    """At least one period input must be provided."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(ValueError, match="At least one of year, quarter, month, half, week or date is required"):
        service.count_pull_requests_by_author_in_date_range(author="octocat", organisation="skyscanner")


def test_period_selection_rejects_multiple_periods(service_with_mocked_client):
    """Only one of month, quarter, or half can be supplied."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(ValueError, match="Specify only one of month, quarter or half"):
        service.count_pull_requests_by_author_in_date_range(
            author="octocat",
            organisation="skyscanner",
            month=MonthName.JANUARY,
            quarter=QuarterName.Q1,
            year=2024,
        )


def test_half_with_year_is_supported(service_with_mocked_client):
    """Half-year and year combination should produce a valid query."""
    service, calls = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}])

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        half=HalfName.H1,
        year=2023,
    )

    assert date_range == DateRange(start_date=date(2023, 1, 1), end_date=date(2023, 6, 30))
    assert "created:2023-01-01T00:00:00Z..2023-06-30T23:59:59Z" in calls[0]["variables"]["query"]


def test_single_date_creates_same_day_range(service_with_mocked_client):
    """Providing a specific date should create a single-day range."""
    service, calls = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}])

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        on_date=date(2024, 12, 5),
    )

    assert date_range.start_date == date(2024, 12, 5)
    assert date_range.end_date == date(2024, 12, 5)
    assert "created:2024-12-05T00:00:00Z..2024-12-05T23:59:59Z" in calls[0]["variables"]["query"]


def test_date_cannot_be_combined_with_other_periods(service_with_mocked_client):
    """Date input must not be combined with additional periods."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(ValueError, match="date cannot be combined with year, quarter, month, half, or week"):
        service.count_pull_requests_by_author_in_date_range(
            author="octocat",
            organisation="skyscanner",
            on_date=date(2024, 12, 5),
            year=2024,
        )


def test_count_supports_half_without_year(service_with_mocked_client):
    """Half without year uses the most recent half for default today."""
    service, _ = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}], today=date(2024, 12, 31))

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        half=HalfName.H2,
    )

    assert date_range == DateRange(start_date=date(2024, 7, 1), end_date=date(2024, 12, 31))


def test_count_supports_quarter_without_year(service_with_mocked_client):
    """Quarter without year uses the most recent quarter for default today."""
    service, _ = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}], today=date(2024, 12, 31))

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        quarter=QuarterName.Q4,
    )

    assert date_range == DateRange(start_date=date(2024, 10, 1), end_date=date(2024, 12, 31))


def test_count_supports_month_without_year(service_with_mocked_client):
    """Month without year uses the most recent occurrence for default today."""
    service, _ = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}], today=date(2024, 12, 31))

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        month=MonthName.DECEMBER,
    )

    assert date_range == DateRange(start_date=date(2024, 12, 1), end_date=date(2024, 12, 31))


def test_count_supports_quarter_with_year(service_with_mocked_client):
    """Quarter with year should return full quarter for that year."""
    service, _ = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}], today=date(2024, 12, 31))

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        quarter=QuarterName.Q2,
        year=2023,
    )

    assert date_range == DateRange(start_date=date(2023, 4, 1), end_date=date(2023, 6, 30))


def test_count_supports_year_only(service_with_mocked_client):
    """Year-only selection should build a range for that calendar year."""
    service, _ = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}], today=date(2024, 12, 31))

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        year=2022,
    )

    assert date_range == DateRange(start_date=date(2022, 1, 1), end_date=date(2022, 12, 31))


def test_count_supports_week_without_other_periods(service_with_mocked_client):
    """Week flag should use the most recent seven-day window."""
    service, calls = service_with_mocked_client(responses=[{"search": {"issueCount": 1}}], today=date(2024, 12, 31))

    date_range, _ = service.count_pull_requests_by_author_in_date_range(
        author="octocat",
        organisation="skyscanner",
        week=True,
    )

    assert date_range == DateRange(start_date=date(2024, 12, 25), end_date=date(2024, 12, 31))
    assert "created:2024-12-25T00:00:00Z..2024-12-31T23:59:59Z" in calls[0]["variables"]["query"]


def test_week_cannot_be_combined_with_other_periods(service_with_mocked_client):
    """Week input must not be combined with additional period selectors."""
    service, _ = service_with_mocked_client(responses=[])

    with pytest.raises(ValueError, match="week cannot be combined with year, quarter, month, half, or date"):
        service.count_pull_requests_by_author_in_date_range(
            author="octocat",
            organisation="skyscanner",
            week=True,
            year=2024,
        )
