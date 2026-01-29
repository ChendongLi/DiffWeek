"""Git repository data extraction utilities."""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from .models import TimeWindow


def _run_git(repo_path: str, args: List[str]) -> str:
    """Run a git command in the specified repository."""
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(f"Repo path not found: {repo_path}")

    cmd = ["git", "-C", repo_path] + args
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def resolve_repo_path(repo_arg: str) -> str:
    """
    Resolves the repository path.
    If it's a local directory, returns it.
    If it looks like 'owner/repo', clones it to a cache directory and returns the cache path.
    """
    if os.path.isdir(repo_arg):
        return repo_arg

    # Check if it looks like owner/repo
    if re.match(r"^[\w.-]+/[\w.-]+$", repo_arg):
        # Define cache directory
        cache_dir = Path.home() / ".cache" / "diffweek" / "repos"
        repo_name = repo_arg.replace("/", "_")
        local_repo_path = cache_dir / repo_name

        if local_repo_path.exists():
            print(f"Using cached repo: {local_repo_path}")
            # Try to update it
            try:
                _run_git(str(local_repo_path), ["fetch", "--all"])
            except Exception as e:
                print(f"Warning: Failed to fetch updates for cached repo: {e}")
            return str(local_repo_path)

        # Clone it
        print(f"Cloning remote repo {repo_arg} to {local_repo_path}...")
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Try gh cli first, then fallback to git clone https
        try:
            subprocess.run(
                ["gh", "repo", "clone", repo_arg, str(local_repo_path)], check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback
            url = f"https://github.com/{repo_arg}.git"
            print(f"gh cli failed or not found, trying git clone {url}...")
            subprocess.run(["git", "clone", url, str(local_repo_path)], check=True)

        # Fetch all remote branches so git log --all can find them
        print("Fetching all remote branches...")
        _run_git(str(local_repo_path), ["fetch", "--all"])

        return str(local_repo_path)

    raise FileNotFoundError(
        f"Repo path not found locally and does not look like 'owner/repo': {repo_arg}"
    )


def extract_git_changes(
    repo_path: str, window: TimeWindow
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract commit-level and file-level change data for a given time window.
    Returns: (commits_df, files_df)

    Uses a single git log --numstat command to get both commit metadata and
    file stats in one pass, avoiding the N+1 query pattern.
    """
    # Get commits with numstat in a single command
    # Format: commit info line, then numstat lines, separated by blank lines
    fmt = "%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
    log_out = _run_git(
        repo_path,
        [
            "log",
            "--all",
            f"--since={window.since}",
            f"--until={window.until}",
            f"--pretty=format:{fmt}",
            "--date=iso-strict",
            "--numstat",
        ],
    ).strip()

    commits = []
    file_rows = []
    current_commit = None

    if log_out:
        for line in log_out.splitlines():
            if not line:
                continue

            # Check if this is a commit line (contains our delimiter)
            if "\x1f" in line:
                parts = line.split("\x1f")
                if len(parts) == 5:
                    commit_hash, author_name, author_email, author_date, subject = parts
                    current_commit = commit_hash
                    commits.append(
                        {
                            "commit": commit_hash,
                            "author_name": author_name,
                            "author_email": author_email,
                            "author_date": author_date,
                            "subject": subject,
                        }
                    )
            elif current_commit:
                # This is a numstat line for the current commit
                # numstat format: "<add>\t<del>\t<path>"
                # For binary files: "-\t-\t<path>"
                cols = line.split("\t")
                if len(cols) >= 3:
                    add_s, del_s, path = cols[0], cols[1], "\t".join(cols[2:])
                    is_binary = add_s == "-" or del_s == "-"
                    file_rows.append(
                        {
                            "commit": current_commit,
                            "path": path,
                            "additions": None if is_binary else int(add_s),
                            "deletions": None if is_binary else int(del_s),
                            "is_binary": is_binary,
                        }
                    )

    commits_df = pd.DataFrame(commits)
    if commits_df.empty:
        # No commits in range
        files_df = pd.DataFrame(
            columns=["commit", "path", "additions", "deletions", "is_binary"]
        )
        return commits_df, files_df

    files_df = pd.DataFrame(file_rows)

    # Optional convenience columns
    if not files_df.empty:
        files_df["dir"] = files_df["path"].str.rsplit("/", n=1).str[0].fillna("")
        files_df["ext"] = files_df["path"].str.rsplit(".", n=1).str[-1].where(
            files_df["path"].str.contains(".", regex=False), ""
        )

    # Commit date as datetime for filtering/aggregation later
    commits_df["author_datetime"] = pd.to_datetime(
        commits_df["author_date"], utc=True, errors="coerce"
    )

    return commits_df, files_df
