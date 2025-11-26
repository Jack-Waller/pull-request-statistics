"""
Custom errors for the pull request statistics package.

These errors signal structural problems with data returned from upstream
services (such as unexpected GraphQL shapes) so callers can distinguish between
transport errors and format errors.
"""


class PullRequestDataError(RuntimeError):
    """Raised when pull request data does not match expected format."""
