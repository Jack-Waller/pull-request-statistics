"""Factory for constructing inclusive date ranges across calendar periods."""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta

from github_client.pull_request_statistics.date_ranges.date_range import DateRange
from github_client.pull_request_statistics.date_ranges.enums.half import Half
from github_client.pull_request_statistics.date_ranges.enums.month import Month
from github_client.pull_request_statistics.date_ranges.enums.quarter import Quarter


class DateRangeFactory:
    """
    Construct inclusive date ranges for common calendar periods.

    The factory handles current in-progress periods by ending at ``today`` and
    rolls back to the most recent historical occurrence when a future period is
    requested. A fixed ``default_today`` can be supplied for deterministic unit
    testing.
    """

    def __init__(self, default_today: date | None = None) -> None:
        """
        Create a factory with an optional fixed ``today`` value for deterministic behaviour.

        Args:
            default_today: Date to treat as today when no explicit date is provided.
        """
        self._default_today = default_today

    def for_quarter(self, quarter: Quarter, *, today: date | None = None) -> DateRange:
        """
        Return the most recent completed occurrence of ``quarter`` or the in-progress range.

        When the requested quarter matches the current quarter, the end date is today.
        Otherwise, the range covers the most recent historical quarter.

        Args:
            quarter: Quarter to build a range for.
            today: Override for the current date when computing in-progress ranges.

        Returns:
            Inclusive date range for the requested quarter.
        """
        current = self._resolve_today(today)
        current_quarter = self._quarter_for_date(current)
        target_year = self._resolve_relative_year(quarter.value, current_quarter.value, current.year)

        start = self._quarter_start_date(quarter, target_year)
        end = (
            current
            if quarter == current_quarter and target_year == current.year
            else self._quarter_end_date(quarter, target_year)
        )
        return DateRange(start, end)

    def for_quarter_in_year(self, quarter: Quarter, year: int) -> DateRange:
        """
        Return the full date range for ``quarter`` within ``year``.

        Args:
            quarter: Quarter to build a range for.
            year: Calendar year to apply.

        Returns:
            Inclusive date range spanning the entire quarter.
        """
        self._validate_year(year)
        today = self._resolve_today(None)
        self._ensure_year_not_future(year, today)
        self._ensure_quarter_not_future(quarter, year, today)
        start = self._quarter_start_date(quarter, year)
        end = self._quarter_end_date(quarter, year)
        return DateRange(start, end)

    def for_year(self, year: int, *, today: date | None = None) -> DateRange:
        """
        Return the full year or the elapsed portion of the current year.

        If ``year`` matches the current year, the end date is today.

        Args:
            year: Calendar year to build a range for.
            today: Override for the current date when computing in-progress ranges.

        Returns:
            Inclusive date range spanning the requested year or elapsed portion.
        """
        self._validate_year(year)
        current = self._resolve_today(today)
        self._ensure_year_not_future(year, current)
        start = date(year, 1, 1)
        end = current if year == current.year else date(year, 12, 31)
        return DateRange(start, end)

    def for_month(self, month: Month, *, today: date | None = None) -> DateRange:
        """
        Return the most recent completed occurrence of ``month`` or the in-progress range.

        When the requested month matches the current month, the end date is today.
        Otherwise, the range covers the most recent historical month.

        Args:
            month: Month to build a range for.
            today: Override for the current date when computing in-progress ranges.

        Returns:
            Inclusive date range for the requested month.
        """
        current = self._resolve_today(today)
        current_month = Month(current.month)
        target_year = self._resolve_relative_year(month.value, current_month.value, current.year)

        start = date(target_year, month.value, 1)
        end = (
            current
            if target_year == current.year and month == current_month
            else self._end_of_month(target_year, month)
        )
        return DateRange(start, end)

    def for_month_in_year(self, month: Month, year: int) -> DateRange:
        """
        Return the full date range for ``month`` within ``year``.

        Args:
            month: Month to build a range for.
            year: Calendar year to apply.

        Returns:
            Inclusive date range spanning the entire month.
        """
        self._validate_year(year)
        today = self._resolve_today(None)
        self._ensure_year_not_future(year, today)
        self._ensure_month_not_future(month, year, today)
        start = date(year, month.value, 1)
        end = self._end_of_month(year, month)
        return DateRange(start, end)

    def for_half(self, half: Half, *, today: date | None = None) -> DateRange:
        """
        Return the most recent completed occurrence of ``half`` or the in-progress range.

        When the requested half matches the current half, the end date is today.
        Otherwise, the range covers the most recent historical half.

        Args:
            half: Half-year segment to build a range for.
            today: Override for the current date when computing in-progress ranges.

        Returns:
            Inclusive date range for the requested half-year segment.
        """
        current = self._resolve_today(today)
        current_half = self._half_for_date(current)
        target_year = self._resolve_relative_year(half.value, current_half.value, current.year)

        start = self._half_start_date(half, target_year)
        end = (
            current if half == current_half and target_year == current.year else self._half_end_date(half, target_year)
        )
        return DateRange(start, end)

    def for_half_in_year(self, half: Half, year: int) -> DateRange:
        """
        Return the full date range for ``half`` within ``year``.

        Args:
            half: Half-year segment to build a range for.
            year: Calendar year to apply.

        Returns:
            Inclusive date range spanning the requested half-year.
        """
        self._validate_year(year)
        today = self._resolve_today(None)
        self._ensure_year_not_future(year, today)
        self._ensure_half_not_future(half, year, today)
        start = self._half_start_date(half, year)
        end = self._half_end_date(half, year)
        return DateRange(start, end)

    def for_date(self, value: date) -> DateRange:
        """
        Return an inclusive range representing a single calendar day.

        Args:
            value: Day to represent.

            Returns:
            A ``DateRange`` where ``start_date`` and ``end_date`` match ``value``.
        """
        if value > self._resolve_today(None):
            raise ValueError("date must not be in the future.")
        return DateRange(value, value)

    def for_week(self, *, today: date | None = None) -> DateRange:
        """
        Return the most recent seven-day window ending on ``today``.

        The range always spans seven inclusive days. When ``today`` is omitted,
        the factory uses its configured default or the system date.

        Args:
            today: Override for the current date when computing the week window.

        Returns:
            Inclusive date range covering the last seven days including ``today``.
        """
        end_date = self._resolve_today(today)
        start_date = end_date - timedelta(days=6)
        return DateRange(start_date, end_date)

    def _resolve_today(self, override: date | None) -> date:
        """Resolve the effective current date using method override, default override, or system clock."""
        if override is not None:
            return override
        if self._default_today is not None:
            return self._default_today
        return datetime.now(tz=UTC).date()

    @staticmethod
    def _resolve_relative_year(target_period: int, current_period: int, current_year: int) -> int:
        """Determine the year to use for a period relative to the current date."""
        return current_year - 1 if target_period > current_period else current_year

    @staticmethod
    def _quarter_start_date(quarter: Quarter, year: int) -> date:
        """Return the first day of the quarter."""
        start_month = (quarter.value - 1) * 3 + 1
        return date(year, start_month, 1)

    def _quarter_end_date(self, quarter: Quarter, year: int) -> date:
        """Return the final day of the quarter."""
        start = self._quarter_start_date(quarter, year)
        end_month = start.month + 2
        return self._end_of_month(year, Month(end_month))

    @staticmethod
    def _half_start_date(half: Half, year: int) -> date:
        """Return the first day of the half-year period."""
        start_month = 1 if half == Half.H1 else 7
        return date(year, start_month, 1)

    def _half_end_date(self, half: Half, year: int) -> date:
        """Return the final day of the half-year period."""
        start = self._half_start_date(half, year)
        end_month = start.month + 5
        return self._end_of_month(year, Month(end_month))

    @staticmethod
    def _end_of_month(year: int, month: Month) -> date:
        """Return the final day of the given month."""
        return date(year, month.value, calendar.monthrange(year, month.value)[1])

    @staticmethod
    def _quarter_for_date(value: date) -> Quarter:
        """Return the calendar quarter that contains ``value``."""
        return Quarter(((value.month - 1) // 3) + 1)

    @staticmethod
    def _half_for_date(value: date) -> Half:
        """Return the half-year segment that contains ``value``."""
        return Half(1 if value.month <= 6 else 2)

    @staticmethod
    def _validate_year(year: int) -> None:
        """Validate year inputs to avoid nonsensical values such as zero or negatives."""
        if year < 1:
            raise ValueError("year must be 1 or later.")

    @staticmethod
    def _ensure_year_not_future(year: int, reference_date: date) -> None:
        """Prevent creation of date ranges wholly in the future."""
        if year > reference_date.year:
            raise ValueError("year must not be in the future.")

    @staticmethod
    def _ensure_quarter_not_future(quarter: Quarter, year: int, reference_date: date) -> None:
        """Prevent creation of quarters beyond the current quarter in the current year."""
        if year == reference_date.year and quarter.value > DateRangeFactory._quarter_for_date(reference_date).value:
            raise ValueError("quarter must not be in the future.")

    @staticmethod
    def _ensure_month_not_future(month: Month, year: int, reference_date: date) -> None:
        """Prevent creation of months beyond the current month in the current year."""
        if year == reference_date.year and month.value > reference_date.month:
            raise ValueError("month must not be in the future.")

    @staticmethod
    def _ensure_half_not_future(half: Half, year: int, reference_date: date) -> None:
        """Prevent creation of halves beyond the current half in the current year."""
        if year == reference_date.year and half.value > DateRangeFactory._half_for_date(reference_date).value:
            raise ValueError("half must not be in the future.")
