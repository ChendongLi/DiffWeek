"""GitHub API client for fetching PR and user data."""

from datetime import datetime
from typing import List, Optional

import httpx

from .config import get_settings
from .models import PullRequest, TimeWindow


def _get_headers() -> dict:
    """Get HTTP headers for GitHub API requests."""
    settings = get_settings()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_personal_access_token:
        headers["Authorization"] = f"Bearer {settings.github_personal_access_token}"
    return headers


def get_user_emails(username: str) -> List[str]:
    """
    Get email addresses associated with a GitHub username.

    Uses the events API to find emails from public commit events.
    Falls back to username-based email patterns if no emails found.
    """
    emails = set()

    # Try to get emails from user's public events (commits)
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"https://api.github.com/users/{username}/events/public",
                headers=_get_headers(),
                params={"per_page": 100},
            )
            response.raise_for_status()
            events = response.json()

            for event in events:
                if event.get("type") == "PushEvent":
                    payload = event.get("payload", {})
                    for commit in payload.get("commits", []):
                        author = commit.get("author", {})
                        email = author.get("email")
                        if email and not email.endswith("@users.noreply.github.com"):
                            emails.add(email)
    except httpx.HTTPError:
        pass

    # Add the GitHub noreply email pattern
    emails.add(f"{username}@users.noreply.github.com")

    # Try to get user profile email
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"https://api.github.com/users/{username}",
                headers=_get_headers(),
            )
            response.raise_for_status()
            user_data = response.json()
            if user_data.get("email"):
                emails.add(user_data["email"])
    except httpx.HTTPError:
        pass

    return list(emails)


def get_merged_prs(
    owner: str, repo: str, author: str, window: TimeWindow
) -> List[PullRequest]:
    """
    Fetch merged pull requests for a given author within a time window.

    Uses REST API /repos/{owner}/{repo}/pulls instead of Search API
    to avoid 422 errors with organization repositories.
    """
    pull_requests = []

    since_dt = window.since_datetime
    until_dt = window.until_datetime

    try:
        with httpx.Client(timeout=30.0) as client:
            page = 1
            while True:
                # List closed PRs (merged PRs are a subset of closed)
                response = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls",
                    headers=_get_headers(),
                    params={
                        "state": "closed",
                        "sort": "updated",
                        "direction": "desc",
                        "per_page": 100,
                        "page": page,
                    },
                )
                response.raise_for_status()
                prs = response.json()

                if not prs:
                    break

                for pr_data in prs:
                    # Filter: must be merged
                    if not pr_data.get("merged_at"):
                        continue

                    # Filter: by author (case-insensitive)
                    if pr_data["user"]["login"].lower() != author.lower():
                        continue

                    # Filter: within time window
                    merged_at = datetime.fromisoformat(
                        pr_data["merged_at"].replace("Z", "+00:00")
                    )
                    if since_dt and merged_at < since_dt:
                        continue
                    if until_dt and merged_at > until_dt:
                        continue

                    # Fetch detailed PR info (for files_changed, additions, deletions)
                    pr_detail_response = client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_data['number']}",
                        headers=_get_headers(),
                    )
                    pr_detail_response.raise_for_status()
                    pr_detail = pr_detail_response.json()

                    pr = PullRequest(
                        number=pr_data["number"],
                        title=pr_data["title"],
                        state="merged",
                        url=pr_data["html_url"],
                        files_changed=pr_detail.get("changed_files", 0),
                        additions=pr_detail.get("additions", 0),
                        deletions=pr_detail.get("deletions", 0),
                        merged_at=pr_data["merged_at"],
                    )
                    pull_requests.append(pr)

                page += 1

                # Early exit: stop if oldest PR in page is before our time window
                if prs and since_dt:
                    oldest_updated = prs[-1].get("updated_at", "")
                    if oldest_updated:
                        oldest_dt = datetime.fromisoformat(
                            oldest_updated.replace("Z", "+00:00")
                        )
                        if oldest_dt < since_dt:
                            break

    except httpx.HTTPError as e:
        print(f"Warning: Failed to fetch PRs from GitHub: {e}")

    return pull_requests
