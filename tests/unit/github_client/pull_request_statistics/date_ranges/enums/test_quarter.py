import re

import pytest

from github_client.pull_request_statistics.date_ranges.enums.quarter import Quarter


class TestQuarterNameFromString:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Q1", Quarter.Q1),
            ("q1", Quarter.Q1),
            ("q2", Quarter.Q2),
            ("Q3", Quarter.Q3),
            ("q4", Quarter.Q4),
            ("1", Quarter.Q1),
            ("4", Quarter.Q4),
            (Quarter.Q3, Quarter.Q3),
        ],
    )
    def test_accepts_prefixed_and_numeric_inputs(self, value: str | int | Quarter, expected: Quarter) -> None:
        assert Quarter.from_string(value) is expected

    @pytest.mark.parametrize(
        ("value", "message"),
        [
            ("", "Quarter value cannot be empty."),
            ("Q5", "Unrecognised quarter value: 'Q5'"),
            ("5", "Unrecognised quarter value: '5'"),
            ("quarter", "Unrecognised quarter value: 'quarter'"),
        ],
    )
    def test_rejects_invalid_values(self, value: str, message: str) -> None:
        with pytest.raises(ValueError, match=re.escape(message)) as exc:
            Quarter.from_string(value)
        assert str(exc.value) == message

    def test_accepts_uppercase_enum_name(self) -> None:
        assert Quarter.from_string("Q2") is Quarter.Q2
