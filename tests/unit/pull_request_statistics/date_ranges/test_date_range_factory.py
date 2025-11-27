from datetime import UTC, date, datetime

import pytest

from pull_request_statistics.date_ranges import (
    DateRange,
    DateRangeFactory,
    HalfName,
    MonthName,
    QuarterName,
)


def test_date_range_rejects_inverted_bounds() -> None:
    with pytest.raises(ValueError, match="end_date must not be earlier than start_date"):
        DateRange(start_date=date(2024, 1, 2), end_date=date(2024, 1, 1))


def test_quarter_range_for_current_quarter_is_partial() -> None:
    factory = DateRangeFactory(default_today=date(2024, 5, 10))
    assert factory.for_quarter(QuarterName.Q2) == DateRange(
        start_date=date(2024, 4, 1),
        end_date=date(2024, 5, 10),
    )


def test_quarter_range_for_previous_quarter_in_same_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 5, 10))
    assert factory.for_quarter(QuarterName.Q1) == DateRange(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
    )


def test_quarter_range_rolls_back_to_previous_year_when_future_quarter_requested() -> None:
    factory = DateRangeFactory(default_today=date(2024, 2, 5))
    assert factory.for_quarter(QuarterName.Q3) == DateRange(
        start_date=date(2023, 7, 1),
        end_date=date(2023, 9, 30),
    )


def test_quarter_range_for_specific_year_is_full_quarter() -> None:
    factory = DateRangeFactory(default_today=date(2024, 8, 23))
    assert factory.for_quarter_in_year(QuarterName.Q4, 2022) == DateRange(
        start_date=date(2022, 10, 1),
        end_date=date(2022, 12, 31),
    )


@pytest.mark.parametrize(
    ("quarter", "year", "today", "message"),
    [
        (QuarterName.Q1, 2025, date(2024, 8, 23), "year must not be in the future."),
        (QuarterName.Q4, 2024, date(2024, 5, 10), "quarter must not be in the future."),
    ],
)
def test_quarter_range_future_inputs_rejected(quarter: QuarterName, year: int, today: date, message: str) -> None:
    factory = DateRangeFactory(default_today=today)
    with pytest.raises(ValueError, match=message):
        factory.for_quarter_in_year(quarter, year)


def test_year_range_for_current_year_is_partial() -> None:
    factory = DateRangeFactory(default_today=date(2024, 8, 15))
    assert factory.for_year(2024) == DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 8, 15))


def test_year_range_for_previous_year_is_full() -> None:
    factory = DateRangeFactory(default_today=date(2024, 8, 15))
    assert factory.for_year(2023) == DateRange(start_date=date(2023, 1, 1), end_date=date(2023, 12, 31))


def test_year_range_rejects_year_zero() -> None:
    factory = DateRangeFactory(default_today=date(2024, 8, 15))
    with pytest.raises(ValueError, match="year must be 1 or later"):
        factory.for_year(0)


def test_year_range_rejects_future_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 8, 15))
    with pytest.raises(ValueError, match="year must not be in the future"):
        factory.for_year(2025)


def test_month_range_for_current_month_is_partial() -> None:
    factory = DateRangeFactory(default_today=date(2024, 5, 10))
    assert factory.for_month(MonthName.MAY) == DateRange(
        start_date=date(2024, 5, 1),
        end_date=date(2024, 5, 10),
    )


def test_month_range_for_previous_month_same_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 5, 10))
    assert factory.for_month(MonthName.MARCH) == DateRange(
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 31),
    )


def test_month_range_for_future_month_rolls_back_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 3, 12))
    assert factory.for_month(MonthName.NOVEMBER) == DateRange(
        start_date=date(2023, 11, 1),
        end_date=date(2023, 11, 30),
    )


def test_month_range_for_specific_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 3, 12))
    assert factory.for_month_in_year(MonthName.FEBRUARY, 2020) == DateRange(
        start_date=date(2020, 2, 1),
        end_date=date(2020, 2, 29),
    )


@pytest.mark.parametrize(
    ("month", "year", "today", "message"),
    [
        (MonthName.JANUARY, 2025, date(2024, 3, 12), "year must not be in the future."),
        (MonthName.NOVEMBER, 2024, date(2024, 3, 12), "month must not be in the future."),
    ],
)
def test_month_range_for_future_inputs_rejected(month: MonthName, year: int, today: date, message: str) -> None:
    factory = DateRangeFactory(default_today=today)
    with pytest.raises(ValueError, match=message):
        factory.for_month_in_year(month, year)


def test_half_range_for_current_half_is_partial() -> None:
    factory = DateRangeFactory(default_today=date(2024, 8, 15))
    assert factory.for_half(HalfName.H2) == DateRange(
        start_date=date(2024, 7, 1),
        end_date=date(2024, 8, 15),
    )


def test_half_range_for_previous_half_same_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 8, 15))
    assert factory.for_half(HalfName.H1) == DateRange(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 6, 30),
    )


def test_half_range_for_future_half_rolls_back_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 3, 18))
    assert factory.for_half(HalfName.H2) == DateRange(
        start_date=date(2023, 7, 1),
        end_date=date(2023, 12, 31),
    )


def test_half_range_for_specific_year() -> None:
    factory = DateRangeFactory(default_today=date(2024, 3, 18))
    assert factory.for_half_in_year(HalfName.H1, 2019) == DateRange(
        start_date=date(2019, 1, 1),
        end_date=date(2019, 6, 30),
    )


@pytest.mark.parametrize(
    ("half", "year", "today", "message"),
    [
        (HalfName.H2, 2025, date(2024, 3, 18), "year must not be in the future."),
        (HalfName.H2, 2024, date(2024, 3, 18), "half must not be in the future."),
    ],
)
def test_half_range_for_future_inputs_rejected(half: HalfName, year: int, today: date, message: str) -> None:
    factory = DateRangeFactory(default_today=today)
    with pytest.raises(ValueError, match=message):
        factory.for_half_in_year(half, year)


def test_single_date_range_matches_same_day() -> None:
    factory = DateRangeFactory(default_today=date(2024, 3, 18))
    assert factory.for_date(date(2024, 3, 5)) == DateRange(
        start_date=date(2024, 3, 5),
        end_date=date(2024, 3, 5),
    )


def test_single_date_range_rejects_future_date() -> None:
    factory = DateRangeFactory(default_today=date(2024, 3, 18))
    with pytest.raises(ValueError, match="date must not be in the future"):
        factory.for_date(date(2024, 3, 19))


def test_resolve_today_uses_override_and_system_clock() -> None:
    factory = DateRangeFactory()
    override = date(2023, 1, 1)
    assert factory._resolve_today(override) == override
    today = factory._resolve_today(None)
    assert isinstance(today, date)
    assert (datetime.now(tz=UTC).date() - today).days == 0
