"""
Query helpers for locating pull requests by author, organisation, and date range.

The service wraps GitHub's GraphQL search endpoint to provide two operations:
counting pull requests and listing their key details for a given author within
an organisation across a specified date range. Callers can further restrict the
results to merged pull requests only by enabling the ``merged_only`` flag. It
also supports searching for pull requests reviewed by a specific user within a
date range, optionally excluding pull requests authored by the reviewer.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, time

from github_client.client import GitHubClient
from github_client.errors import MalformedResponseError
from github_client.pull_request_statistics.date_ranges import (
    DateRange,
    DateRangeFactory,
    HalfName,
    MonthName,
    QuarterName,
)
from github_client.pull_request_statistics.models import MemberStatistics, PullRequestSummary

COUNT_QUERY = """
query ($query: String!) {
  search(query: $query, type: ISSUE, first: 1) {
    issueCount
  }
}
"""

LIST_QUERY = """
query ($query: String!, $pageSize: Int!, $after: String) {
  search(query: $query, type: ISSUE, first: $pageSize, after: $after) {
    issueCount
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        url
        createdAt
        author {
          login
        }
        repository {
          nameWithOwner
        }
      }
    }
  }
}
"""

REVIEW_COUNT_QUERY = """
query ($query: String!, $pageSize: Int!, $after: String) {
  search(query: $query, type: ISSUE, first: $pageSize, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        author { login }
        reviews(first: 100) {
          edges {
            node {
              createdAt
              author { login }
            }
          }
        }
      }
    }
  }
}
"""

REVIEW_LIST_QUERY = """
query ($query: String!, $pageSize: Int!, $after: String) {
  search(query: $query, type: ISSUE, first: $pageSize, after: $after) {
    issueCount
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on PullRequest {
        number
        title
        url
        createdAt
        author {
          login
        }
        repository {
          nameWithOwner
        }
        reviews(first: 100) {
          edges {
            node {
              createdAt
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}
"""


class PullRequestStatisticsService:
    """
    Provide pull request count and listing helpers for authored and reviewed pull requests.

    The service builds GitHub search queries and paginates through results,
    applying additional client-side filters where GitHub's ``issueCount`` lacks
    the necessary detail (for example, review timestamps). Use
    ``merged_only=True`` to focus on merged pull requests; otherwise, both open
    and closed pull requests are returned. Review helpers fetch review edges to
    enforce date windows and optional exclusion of self-authored pull requests.
    """

    def __init__(
        self,
        client: GitHubClient,
        organisation: str,
        page_size: int = 50,
        date_range_factory: DateRangeFactory | None = None,
    ) -> None:
        """
        Store the GitHub client used for issuing GraphQL queries.

        Args:
            client: Authenticated GitHub client.
            organisation: GitHub organisation name to search within.
            page_size: Number of nodes to request per page when listing pull requests.
            date_range_factory: Factory for constructing period-based date ranges. Defaults to ``DateRangeFactory()``.

        Raises:
            ValueError: when the requested page size is not between 1 and 100.
        """
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100 to satisfy GitHub search limits.")
        self._client = client
        self._organisation = organisation
        self._page_size = page_size
        self._date_range_factory = date_range_factory or DateRangeFactory()

    def count_pull_requests_by_author_in_date_range(
        self,
        *,
        author: str,
        year: int | None = None,
        quarter: QuarterName | str | int | None = None,
        month: MonthName | str | int | None = None,
        half: HalfName | str | int | None = None,
        on_date: date | None = None,
        week: bool = False,
        merged_only: bool = False,
    ) -> tuple[DateRange, int]:
        """
        Count pull requests raised by an author in an organisation within a date range.

        Args:
            author: GitHub user login.
            year: Calendar year to include (optional unless no other period supplied).
            quarter: Quarter to include. Cannot be combined with ``month`` or ``half``.
            month: Month to include. Cannot be combined with ``quarter`` or ``half``.
            half: Half-year to include. Cannot be combined with ``quarter`` or ``month``.
            on_date: Specific day to include; creates a single-day range and cannot be combined with other periods.
            week: When true, use the most recent week ending today. Cannot be combined with other periods.
            merged_only: When true, limit results to merged pull requests.

        Returns:
            Tuple of the resolved ``DateRange`` and the number of pull requests matching the supplied criteria.
        """
        date_range = self._resolve_date_range(
            half=half, month=month, quarter=quarter, year=year, on_date=on_date, week=week
        )
        total = self._count_authored_within_range(
            author=author,
            date_range=date_range,
            merged_only=merged_only,
        )
        return date_range, total

    def iter_pull_requests_by_author_in_date_range(
        self,
        *,
        author: str,
        year: int | None = None,
        quarter: QuarterName | str | int | None = None,
        month: MonthName | str | int | None = None,
        half: HalfName | str | int | None = None,
        on_date: date | None = None,
        week: bool = False,
        merged_only: bool = False,
    ) -> Iterator[PullRequestSummary]:
        """
        Yield pull requests raised by an author in an organisation within a date range.

        The method paginates through all search results and yields each pull
        request as it is found, ensuring no pull requests are missed when more
        than one page is returned.

        Args:
            author: GitHub user login.
            year: Calendar year to include (optional unless no other period supplied).
            quarter: Quarter to include. Cannot be combined with ``month`` or ``half``.
            month: Month to include. Cannot be combined with ``quarter`` or ``half``.
            half: Half-year to include. Cannot be combined with ``quarter`` or ``month``.
            on_date: Specific day to include; creates a single-day range and cannot be combined with other periods.
            week: When true, use the most recent week ending today. Cannot be combined with other periods.
            merged_only: When true, limit results to merged pull requests.

        Yields:
            ``PullRequestSummary`` objects describing each pull request.
        """
        date_range = self._resolve_date_range(
            half=half, month=month, quarter=quarter, year=year, on_date=on_date, week=week
        )
        search_query = self._build_search_query(
            author=author,
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            merged_only=merged_only,
        )
        cursor: str | None = None

        while True:
            response = self._client.query_graphql(
                LIST_QUERY,
                variables={
                    "query": search_query,
                    "pageSize": self._page_size,
                    "after": cursor,
                },
            )
            search = self._extract_search(response)
            nodes: Iterable[dict] = search.get("nodes") or []
            for node in nodes:
                if node is None:
                    continue
                yield PullRequestSummary.from_graphql(node)

            page_info = self._extract_page_info(search)
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info["endCursor"]

    def _build_search_query(
        self,
        *,
        author: str,
        start_date: date,
        end_date: date,
        merged_only: bool = False,
    ) -> str:
        """Compose a GitHub search query string for the requested filters."""
        start_datetime, end_datetime = self._normalise_date_range(start_date, end_date)

        start_text = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_text = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        created_range = f"{start_text}..{end_text}"
        merged_filter = " is:merged" if merged_only else ""
        return f"author:{author} org:{self._organisation} is:pr created:{created_range}{merged_filter}"

    def count_pull_requests_reviewed_by_user_in_date_range(
        self,
        *,
        reviewer: str,
        year: int | None = None,
        quarter: QuarterName | str | int | None = None,
        month: MonthName | str | int | None = None,
        half: HalfName | str | int | None = None,
        on_date: date | None = None,
        week: bool = False,
        exclude_self_authored: bool = False,
    ) -> tuple[DateRange, int]:
        """
        Count pull requests reviewed by a user in an organisation within a date range.

        Args:
            reviewer: GitHub user login of the reviewer.
            year: Calendar year to include (optional unless no other period supplied).
            quarter: Quarter to include. Cannot be combined with ``month`` or ``half``.
            month: Month to include. Cannot be combined with ``quarter`` or ``half``.
            half: Half-year to include. Cannot be combined with ``quarter`` or ``month``.
            on_date: Specific day to include; creates a single-day range and cannot be combined with other periods.
            week: When true, use the most recent week ending today. Cannot be combined with other periods.
            exclude_self_authored: When true, exclude pull requests authored by the reviewer.

        Returns:
            Tuple of the resolved ``DateRange`` and the number of pull requests matching the supplied criteria.

        Note:
            GitHub's search API does not expose review timestamps inside
            ``issueCount``. The method issues a dedicated review query and
            paginates review edges client-side to honour review date windows and
            optional self-author exclusion. This is necessary to avoid counting
            reviews that occurred outside the requested period.
        """
        date_range = self._resolve_date_range(
            half=half, month=month, quarter=quarter, year=year, on_date=on_date, week=week
        )
        total = self._count_reviewed_within_range(
            reviewer=reviewer,
            date_range=date_range,
            exclude_self_authored=exclude_self_authored,
        )
        return date_range, total

    def iter_pull_requests_reviewed_by_user_in_date_range(
        self,
        *,
        reviewer: str,
        year: int | None = None,
        quarter: QuarterName | str | int | None = None,
        month: MonthName | str | int | None = None,
        half: HalfName | str | int | None = None,
        on_date: date | None = None,
        week: bool = False,
        exclude_self_authored: bool = False,
    ) -> Iterator[PullRequestSummary]:
        """
        Yield pull requests reviewed by a user in an organisation within a date range.

        The method paginates through review edges and yields each pull request
        when at least one review by ``reviewer`` falls inside the requested
        date window. GitHub search does not surface review timestamps in
        ``issueCount``, so this iterator inspects review edges directly.

        Args:
            reviewer: GitHub user login of the reviewer.
            year: Calendar year to include (optional unless no other period supplied).
            quarter: Quarter to include. Cannot be combined with ``month`` or ``half``.
            month: Month to include. Cannot be combined with ``quarter`` or ``half``.
            half: Half-year to include. Cannot be combined with ``quarter`` or ``month``.
            on_date: Specific day to include; creates a single-day range and cannot be combined with other periods.
            week: When true, use the most recent week ending today. Cannot be combined with other periods.
            exclude_self_authored: When true, exclude pull requests authored by the reviewer.

        Yields:
            ``PullRequestSummary`` objects describing each pull request.
        """
        date_range = self._resolve_date_range(
            half=half, month=month, quarter=quarter, year=year, on_date=on_date, week=week
        )
        search_query = self._build_review_search_query(
            reviewer=reviewer,
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            exclude_self_authored=exclude_self_authored,
        )
        cursor: str | None = None

        start_datetime = datetime.combine(date_range.start_date, time.min, tzinfo=UTC)
        end_datetime = datetime.combine(date_range.end_date, time(hour=23, minute=59, second=59), tzinfo=UTC)

        while True:
            response = self._client.query_graphql(
                REVIEW_LIST_QUERY,
                variables={
                    "query": search_query,
                    "pageSize": self._page_size,
                    "after": cursor,
                },
            )
            search = response["search"]
            nodes: Iterable[dict] = search.get("nodes") or []
            for node in nodes:
                if node is None:
                    continue
                if exclude_self_authored and node.get("author", {}).get("login") == reviewer:
                    continue
                if not self._has_review_in_range(
                    reviews=node.get("reviews"),
                    reviewer=reviewer,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ):
                    continue
                yield PullRequestSummary.from_graphql(node)

            page_info = search["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

    def _build_review_search_query(
        self,
        *,
        reviewer: str,
        start_date: date,
        end_date: date,
        exclude_self_authored: bool = False,
    ) -> str:
        """Compose a GitHub search query for pull requests reviewed by a user."""
        start_datetime, end_datetime = self._normalise_date_range(start_date, end_date)

        start_text = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_text = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        updated_range = f"{start_text}..{end_text}"
        self_filter = f" -author:{reviewer}" if exclude_self_authored else ""
        return f"reviewed-by:{reviewer} org:{self._organisation} is:pr updated:{updated_range}{self_filter}"

    def count_member_statistics(
        self,
        *,
        members: Iterable[str],
        year: int | None = None,
        quarter: QuarterName | str | int | None = None,
        month: MonthName | str | int | None = None,
        half: HalfName | str | int | None = None,
        on_date: date | None = None,
        week: bool = False,
        merged_only: bool = False,
        exclude_self_authored: bool = False,
    ) -> tuple[DateRange | None, list[MemberStatistics]]:
        """Return authored and reviewed counts for each member in one call."""
        unique_members = [login for login in dict.fromkeys(members) if login]
        if not unique_members:
            return None, []

        date_range = self._resolve_date_range(
            half=half, month=month, quarter=quarter, year=year, on_date=on_date, week=week
        )
        statistics: list[MemberStatistics] = []

        for member in unique_members:
            authored_count = self._count_authored_within_range(
                author=member,
                date_range=date_range,
                merged_only=merged_only,
            )
            reviewed_count = self._count_reviewed_within_range(
                reviewer=member,
                date_range=date_range,
                exclude_self_authored=exclude_self_authored,
            )
            statistics.append(
                MemberStatistics(
                    login=member,
                    authored_count=authored_count,
                    reviewed_count=reviewed_count,
                )
            )

        return date_range, statistics

    def _count_authored_within_range(
        self,
        *,
        author: str,
        date_range: DateRange,
        merged_only: bool,
    ) -> int:
        search_query = self._build_search_query(
            author=author,
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            merged_only=merged_only,
        )
        response = self._client.query_graphql(COUNT_QUERY, variables={"query": search_query})
        search = self._extract_search(response)
        return self._extract_issue_count(search)

    def _count_reviewed_within_range(
        self,
        *,
        reviewer: str,
        date_range: DateRange,
        exclude_self_authored: bool,
    ) -> int:
        search_query = self._build_review_search_query(
            reviewer=reviewer,
            start_date=date_range.start_date,
            end_date=date_range.end_date,
            exclude_self_authored=exclude_self_authored,
        )
        cursor: str | None = None
        start_datetime, end_datetime = self._normalise_date_range(date_range.start_date, date_range.end_date)
        total = 0

        while True:
            response = self._client.query_graphql(
                REVIEW_COUNT_QUERY,
                variables={
                    "query": search_query,
                    "pageSize": self._page_size,
                    "after": cursor,
                },
            )
            search = self._extract_search(response)
            nodes: Iterable[dict] = search.get("nodes") or []
            for node in nodes:
                if node is None:
                    continue
                if exclude_self_authored and node.get("author", {}).get("login") == reviewer:
                    continue
                if self._has_review_in_range(
                    reviews=node.get("reviews"),
                    reviewer=reviewer,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                ):
                    total += 1

            page_info = self._extract_page_info(search)
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info["endCursor"]

        return total

    @staticmethod
    def _has_review_in_range(
        *,
        reviews: dict | None,
        reviewer: str,
        start_datetime: datetime,
        end_datetime: datetime,
    ) -> bool:
        """Return True when a review by ``reviewer`` exists in the given window."""
        edges = (reviews or {}).get("edges", [])
        for edge in edges:
            review_node = edge.get("node")
            if not review_node:
                continue
            if review_node.get("author", {}).get("login") != reviewer:
                continue
            created_at = review_node.get("createdAt")
            if not created_at:
                continue
            try:
                review_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                continue
            if start_datetime <= review_time <= end_datetime:
                return True
        return False

    @staticmethod
    def _normalise_date_range(start_date: date, end_date: date) -> tuple[datetime, datetime]:
        """Validate and convert date bounds into UTC datetime bounds."""
        if end_date < start_date:
            raise ValueError("end_date must not be earlier than start_date.")
        start_datetime = datetime.combine(start_date, time.min, tzinfo=UTC)
        end_datetime = datetime.combine(end_date, time(hour=23, minute=59, second=59), tzinfo=UTC)
        return start_datetime, end_datetime

    @staticmethod
    def _extract_search(response: dict) -> dict:
        """Safely extract the search block or raise a descriptive error."""
        search = response.get("search")
        if search is None:
            raise MalformedResponseError("GitHub response missing search data")
        return search

    @staticmethod
    def _extract_issue_count(search: dict) -> int:
        """Safely extract issueCount."""
        issue_count = search.get("issueCount")
        if issue_count is None:
            raise MalformedResponseError("GitHub response missing issueCount")
        return int(issue_count)

    @staticmethod
    def _extract_page_info(search: dict) -> dict:
        """Safely extract pageInfo."""
        page_info = search.get("pageInfo")
        if page_info is None:
            raise MalformedResponseError("GitHub response missing pageInfo")
        return page_info

    def _resolve_date_range(
        self,
        *,
        half: HalfName | str | int | None = None,
        month: MonthName | str | int | None = None,
        quarter: QuarterName | str | int | None = None,
        year: int | None = None,
        on_date: date | None = None,
        week: bool = False,
    ) -> DateRange:
        """Construct a date range from a combination of year and optional period."""
        half_value, month_value, quarter_value, week_flag = self._validate_period_inputs(
            half=half,
            month=month,
            quarter=quarter,
            year=year,
            on_date=on_date,
            week=week,
        )

        if week_flag:
            return self._date_range_factory.for_week()

        if on_date is not None:
            return self._date_range_factory.for_date(on_date)

        if year is None:
            if half_value is not None:
                return self._date_range_factory.for_half(half_value)
            if month_value is not None:
                return self._date_range_factory.for_month(month_value)
            if quarter_value is not None:
                return self._date_range_factory.for_quarter(quarter_value)
            # Only year provided falls through to for_year
            raise ValueError("year is required when no month, quarter or half is provided.")  # pragma: no cover

        if half_value is not None:
            return self._date_range_factory.for_half_in_year(half_value, year)
        if month_value is not None:
            return self._date_range_factory.for_month_in_year(month_value, year)
        if quarter_value is not None:
            return self._date_range_factory.for_quarter_in_year(quarter_value, year)
        return self._date_range_factory.for_year(year)

    @staticmethod
    def _validate_period_inputs(
        *,
        half: HalfName | str | int | None,
        month: MonthName | str | int | None,
        quarter: QuarterName | str | int | None,
        year: int | None,
        on_date: date | None,
        week: bool,
    ) -> tuple[HalfName | None, MonthName | None, QuarterName | None, bool]:
        """Normalise and validate period selection inputs."""
        if all(period is None for period in (half, month, quarter, year, on_date)) and not week:
            raise ValueError("At least one of year, quarter, month, half, week or date is required.")

        if on_date is not None and (any(period is not None for period in (half, month, quarter, year)) or week):
            raise ValueError("date cannot be combined with year, quarter, month, half, or week.")

        if week and any(period is not None for period in (half, month, quarter, year, on_date)):
            raise ValueError("week cannot be combined with year, quarter, month, half, or date.")

        selected_periods = sum(period is not None for period in (half, month, quarter))
        if selected_periods > 1:
            raise ValueError("Specify only one of month, quarter or half.")

        half_value = HalfName.from_string(half) if half is not None else None
        month_value = MonthName.from_string(month) if month is not None else None
        quarter_value = QuarterName.from_string(quarter) if quarter is not None else None
        return half_value, month_value, quarter_value, week
