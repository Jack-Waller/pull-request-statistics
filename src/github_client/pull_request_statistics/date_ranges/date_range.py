"""Immutable inclusive date range value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DateRange:
    """
    Inclusive date interval represented by start and end dates.

    The bounds are inclusive, ensuring predictable comparisons when passing date
    ranges to queries and filters. Instances are immutable to support safe
    sharing between services.
    """

    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        """Validate that the end date is not earlier than the start date."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date.")
