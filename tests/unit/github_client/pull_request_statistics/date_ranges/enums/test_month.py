import re

import pytest

from github_client.pull_request_statistics.date_ranges import Month


class TestMonthNameFromString:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("January", Month.JANUARY),
            ("jAnUaRy", Month.JANUARY),
            ("JAN", Month.JANUARY),
            ("jan", Month.JANUARY),
            ("3", Month.MARCH),
            ("12", Month.DECEMBER),
            ("Dec", Month.DECEMBER),
            ("dEcEmBeR", Month.DECEMBER),
            (Month.AUGUST, Month.AUGUST),
        ],
    )
    def test_accepts_varied_case_and_numeric_inputs(self, value: str | int | Month, expected: Month) -> None:
        assert Month.from_string(value) is expected

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
            Month.from_string(value)
        assert str(exc.value) == message
