"""Tests for environment variable helper."""

import pytest

from require_env import require_env


def test_require_env_returns_value_when_present(monkeypatch):
    """Should return the variable when it exists."""
    monkeypatch.setenv("EXAMPLE_VAR", "value")

    assert require_env("EXAMPLE_VAR") == "value"


def test_require_env_optional_returns_none(monkeypatch):
    """Optional variables should return None when absent."""
    monkeypatch.delenv("OPTIONAL_VAR", raising=False)

    assert require_env("OPTIONAL_VAR", require=False) is None


def test_require_env_raises_when_required(monkeypatch):
    """Missing required variables should raise OSError."""
    monkeypatch.delenv("MISSING_VAR", raising=False)

    with pytest.raises(OSError, match="required but not set"):
        require_env("MISSING_VAR")
