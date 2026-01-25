import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Optional

import pandas as pd


@dataclass(frozen=True)
class TimeWindow:
    since: str  # anything git understands: ISO-8601, "2026-01-01 00:00:00 -0800", etc.
    until: str


def _run_git(repo_path: str, args: List[str]) -> str:
    if not os.path.isdir(repo_path):
        raise FileNotFoundError(f"Repo path not found: {repo_path}")

    cmd = ["git", "-C", repo_path] + args
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{p.stderr.strip()}")
    return p.stdout


def extract_git_changes(repo_path: str, window: TimeWindow) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract commit-level and file-level change data for a given time window.
    Returns: (commits_df, files_df)
    """
    # Get commit list within window (reverse chronological not required, but stable ordering helps)
    # Using a unit separator to avoid parsing issues.
    fmt = "%H%x1f%an%x1f%ae%x1f%ad%x1f%s"
    log_out = _run_git(
        repo_path,
        ["log", f"--since={window.since}", f"--until={window.until}",
         f"--pretty=format:{fmt}", "--date=iso-strict"]
    ).strip()

    commits = []
    if log_out:
        for line in log_out.splitlines():
            parts = line.split("\x1f")
            if len(parts) != 5:
                continue
            commit_hash, author_name, author_email, author_date, subject = parts
            commits.append({
                "commit": commit_hash,
                "author_name": author_name,
                "author_email": author_email,
                "author_date": author_date,  # ISO-8601 string
                "subject": subject,
            })

    commits_df = pd.DataFrame(commits)
    if commits_df.empty:
        # No commits in range
        files_df = pd.DataFrame(columns=["commit", "path", "additions", "deletions", "is_binary"])
        return commits_df, files_df

    # For each commit, gather numstat (file-level additions/deletions)
    file_rows = []
    for commit_hash in commits_df["commit"].tolist():
        show_out = _run_git(repo_path, ["show", "--numstat", "--format=", commit_hash]).strip()
        if not show_out:
            continue

        for line in show_out.splitlines():
            # numstat format: "<add>\t<del>\t<path>"
            # For binary files: "-\t-\t<path>"
            cols = line.split("\t")
            if len(cols) < 3:
                continue
            add_s, del_s, path = cols[0], cols[1], "\t".join(cols[2:])

            is_binary = (add_s == "-" or del_s == "-")
            additions = None if is_binary else int(add_s)
            deletions = None if is_binary else int(del_s)

            file_rows.append({
                "commit": commit_hash,
                "path": path,
                "additions": additions,
                "deletions": deletions,
                "is_binary": is_binary,
            })

    files_df = pd.DataFrame(file_rows)

    # Optional convenience columns (helps later steps)
    if not files_df.empty:
        files_df["dir"] = files_df["path"].str.rsplit("/", n=1).str[0].fillna("")
        files_df["ext"] = files_df["path"].str.rsplit(".", n=1).str[-1].where(files_df["path"].str.contains(".", regex=False), "")

    # Commit date as datetime for filtering/aggregation later
    commits_df["author_datetime"] = pd.to_datetime(commits_df["author_date"], errors="coerce")

    return commits_df, files_df


if __name__ == "__main__":
    # Example:
    # python step1_extract.py /path/to/repo "2026-01-12T00:00:00-08:00" "2026-01-19T00:00:00-08:00"
    import sys
    from pathlib import Path

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
                # Optional: git fetch/pull to ensure up-to-date
                # We'll skip auto-pull for now or allow it to be just a cache.
                # But typically for analyzing recent history, we might want it updated.
                # Let's try to update it.
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
                subprocess.run(["gh", "repo", "clone", repo_arg, str(local_repo_path)], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback
                url = f"https://github.com/{repo_arg}.git"
                print(f"gh cli failed or not found, trying git clone {url}...")
                subprocess.run(["git", "clone", url, str(local_repo_path)], check=True)
            
            return str(local_repo_path)

        raise FileNotFoundError(f"Repo path not found locally and does not look like 'owner/repo': {repo_arg}")

    if len(sys.argv) != 4:
        print("Usage: python git_extract.py <repo_path_or_owner/repo> <since> <until>")
        print('Example: python git_extract.py . "2026-01-12T00:00:00-08:00" "2026-01-19T00:00:00-08:00"')
        raise SystemExit(2)

    repo = resolve_repo_path(sys.argv[1])
    since = sys.argv[2]
    until = sys.argv[3]

    commits_df, files_df = extract_git_changes(repo, TimeWindow(since=since, until=until))

    print("\n=== Commits ===")
    print(commits_df.head(20).to_string(index=False))

    print("\n=== File changes ===")
    print(files_df.head(50).to_string(index=False))

    print(f"\nTotal commits: {len(commits_df)}")
    print(f"Total file-change rows: {len(files_df)}")