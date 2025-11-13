"""
Custom exceptions for the GitHub client package.

Each error intentionally inherits from ``RuntimeError`` so callers can decide
whether to catch specific client failures or allow them to bubble up to a
global handler.
"""


class GitHubClientError(RuntimeError):
    """
    Provide a consistent error for unexpected GitHub responses.

    The error wraps issues such as malformed JSON, missing ``data`` fields, or
    GraphQL error payloads, giving callers one exception type to catch for all
    client-side validation concerns.
    """
