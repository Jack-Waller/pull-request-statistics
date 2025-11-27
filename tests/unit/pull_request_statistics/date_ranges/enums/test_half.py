import re

import pytest

from pull_request_statistics.date_ranges.enums.half import HalfName


class TestHalfNameFromString:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("H1", HalfName.H1),
            ("h1", HalfName.H1),
            ("H2", HalfName.H2),
            ("h2", HalfName.H2),
            ("1", HalfName.H1),
            ("2", HalfName.H2),
            (HalfName.H2, HalfName.H2),
        ],
    )
    def test_accepts_prefixed_and_numeric_inputs(self, value: str | int | HalfName, expected: HalfName) -> None:
        assert HalfName.from_string(value) is expected

    @pytest.mark.parametrize(
        ("value", "message"),
        [
            ("", "Half value cannot be empty."),
            ("H3", "Unrecognised half value: 'H3'"),
            ("0", "Unrecognised half value: '0'"),
            ("half", "Unrecognised half value: 'half'"),
        ],
    )
    def test_rejects_invalid_values(self, value: str, message: str) -> None:
        with pytest.raises(ValueError, match=re.escape(message)) as exc:
            HalfName.from_string(value)
        assert str(exc.value) == message

    def test_accepts_uppercase_enum_name(self) -> None:
        assert HalfName.from_string("H1") is HalfName.H1
