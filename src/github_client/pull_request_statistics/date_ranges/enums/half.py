"""Half-year enumeration with tolerant parsing."""

from __future__ import annotations

from enum import IntEnum


class Half(IntEnum):
    """Halves of a calendar year."""

    H1 = 1
    H2 = 2

    @classmethod
    def from_string(cls, value: str | int | Half) -> Half:
        """
        Parse a half-year value from numeric or ``Hx`` representations.

        Accepts values such as ``"H1"``, ``"h2"``, ``1``, or an existing enum
        member. Case and an optional leading ``H`` are ignored when matching.

        Raises:
            ValueError: if the supplied value cannot be matched to a half-year.
        """
        if isinstance(value, cls):
            return value

        text = str(value).strip()
        if not text:
            raise ValueError("Half value cannot be empty.")

        normalised = text.upper()
        for half in cls:
            if normalised == half.name:
                return half

        if normalised.startswith("H"):
            normalised = normalised[1:]

        if normalised.isdigit():
            try:
                return cls(int(normalised))
            except ValueError as error:
                raise ValueError(f"Unrecognised half value: {value!r}") from error

        raise ValueError(f"Unrecognised half value: {value!r}")
