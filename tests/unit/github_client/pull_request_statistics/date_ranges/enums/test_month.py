import re

import pytest

from github_client.pull_request_statistics.date_ranges import MonthName


class TestMonthNameFromString:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("January", MonthName.JANUARY),
            ("jAnUaRy", MonthName.JANUARY),
            ("JAN", MonthName.JANUARY),
            ("jan", MonthName.JANUARY),
            ("3", MonthName.MARCH),
            ("12", MonthName.DECEMBER),
            ("Dec", MonthName.DECEMBER),
            ("dEcEmBeR", MonthName.DECEMBER),
            (MonthName.AUGUST, MonthName.AUGUST),
        ],
    )
    def test_accepts_varied_case_and_numeric_inputs(self, value: str | int | MonthName, expected: MonthName) -> None:
        assert MonthName.from_string(value) is expected

    @pytest.mark.parametrize(
        ("value", "message"),
        [
            ("", "Month value cannot be empty."),
            ("Spr", "Unrecognised month value: 'Spr'"),
            ("month", "Unrecognised month value: 'month'"),
            ("0", "Unrecognised month value: '0'"),
        ],
    )
    def test_rejects_invalid_values(self, value: str, message: str) -> None:
        with pytest.raises(ValueError, match=re.escape(message)) as exc:
            MonthName.from_string(value)
        assert str(exc.value) == message
