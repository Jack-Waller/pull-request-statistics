import re

import pytest

from github_client.pull_request_statistics.date_ranges.enums.quarter import QuarterName


class TestQuarterNameFromString:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("Q1", QuarterName.Q1),
            ("q1", QuarterName.Q1),
            ("q2", QuarterName.Q2),
            ("Q3", QuarterName.Q3),
            ("q4", QuarterName.Q4),
            ("1", QuarterName.Q1),
            ("4", QuarterName.Q4),
            (QuarterName.Q3, QuarterName.Q3),
        ],
    )
    def test_accepts_prefixed_and_numeric_inputs(self, value: str | int | QuarterName, expected: QuarterName) -> None:
        assert QuarterName.from_string(value) is expected

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
            QuarterName.from_string(value)
        assert str(exc.value) == message

    def test_accepts_uppercase_enum_name(self) -> None:
        assert QuarterName.from_string("Q2") is QuarterName.Q2
