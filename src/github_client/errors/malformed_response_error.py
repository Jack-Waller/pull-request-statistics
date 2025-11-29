"""
Raised when GitHub responses are missing expected fields or structure.

Use this to signal callers that a request succeeded but the returned data could
not be parsed because required keys were absent or in an unexpected shape.
"""

from __future__ import annotations

from github_client.errors.github_client_error import GitHubClientError


class MalformedResponseError(GitHubClientError):
    """Represent malformed or incomplete GitHub responses."""


__all__ = ["MalformedResponseError"]
