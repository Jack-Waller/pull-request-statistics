"""
Custom exceptions for the GitHub client package.

Each error intentionally inherits from ``RuntimeError`` so callers can decide
whether to catch specific client failures or allow them to bubble up to a
global handler.
"""

from github_client.errors.github_client_error import GitHubClientError
from github_client.errors.malformed_response_error import MalformedResponseError

__all__ = ["GitHubClientError", "MalformedResponseError"]
