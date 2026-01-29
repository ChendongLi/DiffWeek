"""Filtering and aggregation utilities for commit data."""

from typing import List, Tuple

import pandas as pd

from .config import get_settings
from .models import CommitSummary


def filter_by_contributor(
    commits_df: pd.DataFrame, files_df: pd.DataFrame, contributor: str
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter commits and files to only those by the specified contributor.

    Args:
        commits_df: DataFrame with commit data (must have 'author_name' and 'author_email' columns)
        files_df: DataFrame with file change data (must have 'commit' column)
        contributor: GitHub username to match (matches in author_name or author_email)

    Returns:
        Tuple of (filtered_commits_df, filtered_files_df)
    """
    if commits_df.empty:
        return commits_df, files_df

    contributor_lower = contributor.lower()
    mask = (
        commits_df["author_name"].str.lower().str.contains(contributor_lower, na=False)
        | commits_df["author_email"].str.lower().str.contains(contributor_lower, na=False)
    )
    filtered_commits = commits_df[mask].copy()

    if filtered_commits.empty:
        return filtered_commits, pd.DataFrame(columns=files_df.columns)

    # Filter files to only those from filtered commits
    filtered_files = files_df[
        files_df["commit"].isin(filtered_commits["commit"])
    ].copy()

    return filtered_commits, filtered_files


def filter_large_diffs(files_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark files with large diffs as stats-only (set diff content to None).

    Files with more than max_diff_lines additions+deletions are marked
    with is_large_diff=True.

    Args:
        files_df: DataFrame with file change data

    Returns:
        DataFrame with 'is_large_diff' column added
    """
    if files_df.empty:
        files_df = files_df.copy()
        files_df["is_large_diff"] = False
        return files_df

    settings = get_settings()
    max_lines = settings.max_diff_lines

    df = files_df.copy()

    # Calculate total lines changed per file
    additions = df["additions"].fillna(0)
    deletions = df["deletions"].fillna(0)
    total_lines = additions + deletions

    df["is_large_diff"] = total_lines > max_lines

    return df


def aggregate_commits(
    commits_df: pd.DataFrame, files_df: pd.DataFrame
) -> List[CommitSummary]:
    """
    Aggregate commit and file data into CommitSummary objects.

    Args:
        commits_df: DataFrame with commit data
        files_df: DataFrame with file change data

    Returns:
        List of CommitSummary objects sorted by date (newest first)
    """
    if commits_df.empty:
        return []

    summaries = []

    # Group files by commit to get per-commit stats
    if not files_df.empty:
        file_stats = (
            files_df.groupby("commit")
            .agg(
                files_changed=("path", "count"),
                additions=("additions", lambda x: x.fillna(0).sum()),
                deletions=("deletions", lambda x: x.fillna(0).sum()),
            )
            .reset_index()
        )
        file_stats_dict = file_stats.set_index("commit").to_dict("index")
    else:
        file_stats_dict = {}

    for _, row in commits_df.iterrows():
        commit_hash = row["commit"]
        stats = file_stats_dict.get(commit_hash, {})

        # Format date as YYYY-MM-DD
        date_str = row["author_date"][:10] if row["author_date"] else ""

        summary = CommitSummary(
            sha=commit_hash[:7],  # Short SHA
            date=date_str,
            message=row["subject"][:80],  # Truncate long messages
            files_changed=int(stats.get("files_changed", 0)),
            additions=int(stats.get("additions", 0)),
            deletions=int(stats.get("deletions", 0)),
        )
        summaries.append(summary)

    # Sort by date descending (newest first)
    summaries.sort(key=lambda s: s.date, reverse=True)

    return summaries
