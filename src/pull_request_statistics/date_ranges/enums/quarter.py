"""Quarter enumeration with flexible string parsing."""

from __future__ import annotations

from enum import IntEnum


class QuarterName(IntEnum):
    """Quarters of a calendar year."""

    Q1 = 1
    Q2 = 2
    Q3 = 3
    Q4 = 4

    @classmethod
    def from_string(cls, value: str | int | QuarterName) -> QuarterName:
        """
        Parse a quarter from a numeric or ``Qx`` representation.

        Accepts values like ``"Q1"``, ``"q3"``, ``1``, or the enum itself. Case
        and optional leading ``Q`` are ignored when matching.

        Raises:
            ValueError: if the supplied value cannot be matched to a quarter.
        """
        if isinstance(value, cls):
            return value

        text = str(value).strip()
        if not text:
            raise ValueError("Quarter value cannot be empty.")

        normalised = text.upper()
        for quarter in cls:
            if normalised == quarter.name:
                return quarter

        if normalised.startswith("Q"):
            normalised = normalised[1:]

        if normalised.isdigit():
            try:
                return cls(int(normalised))
            except ValueError as error:
                raise ValueError(f"Unrecognised quarter value: {value!r}") from error

        raise ValueError(f"Unrecognised quarter value: {value!r}")
