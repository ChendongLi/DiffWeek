"""Command-line interface for DiffWeek."""

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer

from .filters import aggregate_commits, filter_by_contributor, filter_large_diffs
from .git_extract import extract_git_changes, resolve_repo_path
from .github_client import get_merged_prs, get_user_emails
from .models import ReportData, TimeWindow
from .report import generate_markdown_report

app = typer.Typer(
    name="diffweek",
    help="Generate weekly engineering summaries with git stats and PR metadata.",
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context) -> None:
    """DiffWeek CLI - Generate weekly engineering summaries."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


def parse_relative_time(since: str) -> datetime:
    """
    Parse relative time string like '7d', '2w', '1m' into a datetime.

    Args:
        since: Relative time string (e.g., '7d' for 7 days, '2w' for 2 weeks, '1m' for 1 month)

    Returns:
        datetime object representing the start of the time window
    """
    match = re.match(r"^(\d+)([dwm])$", since.lower())
    if not match:
        raise typer.BadParameter(
            f"Invalid relative time format: {since}. Use formats like '7d', '2w', '1m'"
        )

    amount = int(match.group(1))
    unit = match.group(2)

    now = datetime.now(timezone.utc)

    if unit == "d":
        delta = timedelta(days=amount)
    elif unit == "w":
        delta = timedelta(weeks=amount)
    elif unit == "m":
        delta = timedelta(days=amount * 30)  # Approximate month
    else:
        raise typer.BadParameter(f"Unknown time unit: {unit}")

    return now - delta


def parse_repo_identifier(repo: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Parse repository identifier to determine if it's local or remote.

    Args:
        repo: Either a local path or 'owner/repo' format

    Returns:
        Tuple of (resolved_path, owner, repo_name)
        For local repos, owner and repo_name are None
    """
    # Check if it looks like owner/repo
    if re.match(r"^[\w.-]+/[\w.-]+$", repo):
        parts = repo.split("/")
        return resolve_repo_path(repo), parts[0], parts[1]
    else:
        # Local path
        return resolve_repo_path(repo), None, None


@app.command("report")
def report_cmd(
    repo: str = typer.Option(
        ...,
        "--repo",
        "-r",
        help="GitHub repo (owner/repo) or local path",
    ),
    contributor: str = typer.Option(
        ...,
        "--contributor",
        "-c",
        help="GitHub username of the contributor",
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        "-s",
        help="Relative time period (e.g., 7d, 2w, 1m)",
    ),
    start: Optional[str] = typer.Option(
        None,
        "--start",
        help="Start date (ISO format: YYYY-MM-DD)",
    ),
    end: Optional[str] = typer.Option(
        None,
        "--end",
        help="End date (ISO format: YYYY-MM-DD)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stdout)",
    ),
) -> None:
    """Generate a weekly engineering summary report."""

    # Validate time options
    if since and (start or end):
        raise typer.BadParameter(
            "Cannot use --since together with --start/--end. Choose one method."
        )

    if not since and not (start and end):
        # Default to 7 days
        since = "7d"

    # Calculate time window
    if since:
        start_dt = parse_relative_time(since)
        end_dt = datetime.now(timezone.utc)
    else:
        try:
            start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
            end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise typer.BadParameter(f"Invalid date format: {e}")

    # Format dates for display and git
    period_start = start_dt.strftime("%Y-%m-%d")
    period_end = end_dt.strftime("%Y-%m-%d")
    window = TimeWindow(
        since=start_dt.isoformat(),
        until=end_dt.isoformat(),
    )

    # Resolve repository
    typer.echo(f"Resolving repository: {repo}")
    repo_path, owner, repo_name = parse_repo_identifier(repo)

    # Determine display name for repository
    if owner and repo_name:
        repo_display = f"{owner}/{repo_name}"
    else:
        resolved_path = Path(repo_path).resolve()
        repo_display = resolved_path.name or str(resolved_path)

    # Get contributor emails
    typer.echo(f"Resolving contributor emails for: {contributor}")
    emails = get_user_emails(contributor)
    typer.echo(f"  Found emails: {', '.join(emails)}")

    # Extract git changes
    typer.echo("Extracting git history...")
    commits_df, files_df = extract_git_changes(repo_path, window)
    typer.echo(f"  Total commits in window: {len(commits_df)}")

    # Filter by contributor
    filtered_commits, filtered_files = filter_by_contributor(commits_df, files_df, emails)
    typer.echo(f"  Commits by contributor: {len(filtered_commits)}")

    # Mark large diffs
    filtered_files = filter_large_diffs(filtered_files)

    # Aggregate commits
    commit_summaries = aggregate_commits(filtered_commits, filtered_files)

    # Fetch PRs from GitHub (if remote repo)
    pull_requests = []
    if owner and repo_name:
        typer.echo("Fetching merged PRs from GitHub...")
        pull_requests = get_merged_prs(owner, repo_name, contributor, window)
        typer.echo(f"  Found {len(pull_requests)} merged PRs")

    # Calculate totals
    total_files = filtered_files["path"].nunique() if not filtered_files.empty else 0
    total_additions = int(filtered_files["additions"].fillna(0).sum()) if not filtered_files.empty else 0
    total_deletions = int(filtered_files["deletions"].fillna(0).sum()) if not filtered_files.empty else 0

    # Build report data
    report_data = ReportData(
        contributor=contributor,
        repository=repo_display,
        period_start=period_start,
        period_end=period_end,
        total_commits=len(filtered_commits),
        total_prs_merged=len(pull_requests),
        total_files_changed=total_files,
        total_additions=total_additions,
        total_deletions=total_deletions,
        pull_requests=pull_requests,
        commits=commit_summaries,
    )

    # Generate report
    typer.echo("Generating report...")
    markdown = generate_markdown_report(report_data)

    # Output
    if output:
        output.write_text(markdown)
        typer.echo(f"Report written to: {output}")
    else:
        typer.echo("")
        typer.echo(markdown)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
