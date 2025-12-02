from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemberStatistics:
    """Store authored and reviewed counts for a GitHub user."""

    username: str
    authored_count: int
    reviewed_count: int
