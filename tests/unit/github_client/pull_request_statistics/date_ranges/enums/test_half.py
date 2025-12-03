import re

import pytest

from github_client.pull_request_statistics.date_ranges.enums.half import Half


class TestHalfNameFromString:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("H1", Half.H1),
            ("h1", Half.H1),
            ("H2", Half.H2),
            ("h2", Half.H2),
            ("1", Half.H1),
            ("2", Half.H2),
            (Half.H2, Half.H2),
        ],
    )
    def test_accepts_prefixed_and_numeric_inputs(self, value: str | int | Half, expected: Half) -> None:
        assert Half.from_string(value) is expected

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
            Half.from_string(value)
        assert str(exc.value) == message

    def test_accepts_uppercase_enum_name(self) -> None:
        assert Half.from_string("H1") is Half.H1
