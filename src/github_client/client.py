"""
Abstractions for interacting with GitHub's GraphQL API.

The module exposes ``GitHubClient``, a lightweight helper that handles
authentication headers, error translation, and request construction so the
rest of the application can focus on the GraphQL queries it issues.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

import requests

from github_client.errors import GitHubClientError, MalformedResponseError

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_GRAPHQL_PATH = "/graphql"
GITHUB_GRAPHQL_ENDPOINT = urljoin(GITHUB_API_BASE_URL, GITHUB_GRAPHQL_PATH)


class GitHubClient:
    """
    Provide authenticated helpers for talking to GitHub.

    The client currently focuses on the GraphQL endpoint, but the separation of
    the base URL and path constants makes adding REST endpoints in future
    straightforward.
    """

    def __init__(self, access_token: str) -> None:
        """
        Store the access token required for authenticating with GitHub.

        Args:
            access_token: Personal access token or installation token with the
                scopes required for the queries this application issues.
        """
        self._access_token = access_token

    def query_graphql(
        self,
        query: str,
        *,
        variables: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query against GitHub's GraphQL endpoint.

        Args:
            query: GraphQL operation string to execute.
            variables: Optional mapping of variable names to values to substitute
                into the query.
            timeout_seconds: Number of seconds to wait for GitHub to respond
                before the request is aborted.

        Returns:
            The ``data`` payload returned by GitHub.

        Raises:
            GitHubClientError: When the request cannot be issued.
            MalformedResponseError: When the response body does not match
                GitHub's documented structure.
        """
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            response = requests.post(
                GITHUB_GRAPHQL_ENDPOINT,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=timeout_seconds,
            )
            response.raise_for_status()
        except Exception as request_error:
            raise GitHubClientError("GitHub GraphQL request failed") from request_error

        try:
            response_json = response.json()
        except ValueError as decode_error:
            raise MalformedResponseError("GitHub GraphQL response was not valid JSON") from decode_error

        if "errors" in response_json:
            raise MalformedResponseError(f"GitHub GraphQL returned errors: {response_json['errors']}")

        if "data" not in response_json:
            raise MalformedResponseError("GitHub GraphQL response did not contain data")

        return response_json["data"]
