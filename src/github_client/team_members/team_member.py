"""
Lightweight representations of GitHub team members.

The classes in this module describe the shape of data returned when fetching
team membership via the GitHub GraphQL API. They are intentionally small so
that other services can reuse them without bringing in additional behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TeamMember:
    """
    Represent a single team member returned by GitHub.

    Attributes:
        login: The GitHub login for the team member.
        name: The member's display name when available; ``None`` when omitted.
    """

    login: str
    name: str | None = None


__all__ = ["TeamMember"]
