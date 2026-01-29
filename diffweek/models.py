"""Data models for DiffWeek."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class TimeWindow:
    """Time range for filtering git history."""

    since: str  # anything git understands: ISO-8601, "2026-01-01 00:00:00 -0800", etc.
    until: str

    @property
    def since_datetime(self) -> Optional[datetime]:
        """Parse since as datetime if possible."""
        try:
            return datetime.fromisoformat(self.since.replace("Z", "+00:00"))
        except ValueError:
            return None

    @property
    def until_datetime(self) -> Optional[datetime]:
        """Parse until as datetime if possible."""
        try:
            return datetime.fromisoformat(self.until.replace("Z", "+00:00"))
        except ValueError:
            return None


@dataclass
class Contributor:
    """A contributor identified by username and associated emails."""

    username: str
    emails: List[str] = field(default_factory=list)


@dataclass
class PullRequest:
    """Pull request metadata from GitHub."""

    number: int
    title: str
    state: str  # "merged", "open", "closed"
    url: str
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    merged_at: Optional[str] = None


@dataclass
class CommitSummary:
    """Aggregated commit data for display."""

    sha: str
    date: str
    message: str
    files_changed: int
    additions: int
    deletions: int


@dataclass
class ReportData:
    """All data needed to generate a report."""

    contributor: str
    repository: str
    period_start: str
    period_end: str
    total_commits: int = 0
    total_prs_merged: int = 0
    total_files_changed: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    pull_requests: List[PullRequest] = field(default_factory=list)
    commits: List[CommitSummary] = field(default_factory=list)
