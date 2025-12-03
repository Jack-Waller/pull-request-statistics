"""Month enumeration with tolerant parsing helpers."""

from __future__ import annotations

from enum import IntEnum


class Month(IntEnum):
    """Months of the calendar year."""

    JANUARY = 1
    FEBRUARY = 2
    MARCH = 3
    APRIL = 4
    MAY = 5
    JUNE = 6
    JULY = 7
    AUGUST = 8
    SEPTEMBER = 9
    OCTOBER = 10
    NOVEMBER = 11
    DECEMBER = 12

    @classmethod
    def from_string(cls, value: str | int | Month) -> Month:
        """
        Parse a month from a numeric or textual representation.

        Accepts numeric strings (``"3"``), integers (``3``), full month names
        (``"January"``) or case-insensitive three-letter abbreviations
        (``"jan"``). Existing enum members are returned unchanged.

        Raises:
            ValueError: if the supplied value cannot be matched to a month.
        """
        if isinstance(value, cls):
            return value

        text = str(value).strip()
        if not text:
            raise ValueError("Month value cannot be empty.")

        if text.isdigit():
            try:
                return cls(int(text))
            except ValueError as error:
                raise ValueError(f"Unrecognised month value: {value!r}") from error

        normalised = text.upper()
        for month in cls:
            if normalised in {month.name, month.name[:3]}:
                return month

        raise ValueError(f"Unrecognised month value: {value!r}")
