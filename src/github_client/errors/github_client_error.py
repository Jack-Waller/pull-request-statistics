"""
Base exception for GitHub client failures.

Use this for transport or authentication errors when issuing requests to
GitHub. Response-shape issues are represented by more specific errors.
"""

from __future__ import annotations


class GitHubClientError(RuntimeError):
    """
    Provide a consistent error for unexpected GitHub request failures.

    The error wraps issues such as HTTP failures or network problems, giving
    callers one exception type to catch for client-side transport concerns.
    """


__all__ = ["GitHubClientError"]
