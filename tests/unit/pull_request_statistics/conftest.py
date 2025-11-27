"""Shared fixtures for pull_request_statistics tests."""

from datetime import date

import pytest

from github_client.client import GitHubClient
from pull_request_statistics.date_ranges import DateRangeFactory
from pull_request_statistics.pull_request_service import PullRequestStatisticsService


@pytest.fixture
def service_with_mocked_client(monkeypatch):
    """Provide a factory that returns a service and call log with a mocked GitHub client."""

    def _factory(responses: list[dict], page_size: int = 50, today: date | None = date(2024, 12, 31)):
        client = GitHubClient(access_token="token-" + "x" * 8)
        call_log: list[dict] = []
        date_range_factory = DateRangeFactory(default_today=today)

        def fake_query_graphql(query: str, *, variables: dict | None = None, timeout_seconds: float = 30.0) -> dict:
            call_log.append({"query": query, "variables": variables, "timeout_seconds": timeout_seconds})
            if not responses:
                raise AssertionError("No stubbed responses left for query.")
            return responses.pop(0)

        monkeypatch.setattr(client, "query_graphql", fake_query_graphql)
        service = PullRequestStatisticsService(client, page_size=page_size, date_range_factory=date_range_factory)
        return service, call_log

    return _factory
