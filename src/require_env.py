"""Helpers for reading required environment variables."""

from os import getenv


def require_env(var_name: str, require: bool = True) -> str | None:
    """
    Return an environment variable or raise when it must be present.

    Args:
        var_name: Name of the variable to read.
        require: When True (the default) an ``OSError`` is raised if the variable
            is unset. When False, missing values return ``None``.

    Returns:
        The environment variable value or ``None`` when the variable is unset
        and not required.

    Raises:
        OSError: When the variable is required but missing.
    """
    value = getenv(var_name)
    if value is None and require:
        raise OSError(f"Environment variable '{var_name}' is required but not set.")
    return value
