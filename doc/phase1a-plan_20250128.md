# DiffWeek Phase 1A Implementation Plan

**Status:** Completed (2026-01-28)

## Overview

Implement CLI tool to generate weekly engineering summaries with git stats + PR metadata (no LLM yet).

**CLI usage:**
```bash
diffweek report --repo owner/repo --contributor username --since 7d
diffweek report --repo ./local-repo --contributor user --start 2026-01-20 --end 2026-01-27
```

---

## File Structure

```
DiffWeek/
├── diffweek/                  # Package
│   ├── __init__.py
│   ├── cli.py                 # Typer CLI
│   ├── git_extract.py         # Git data extraction (moved from root)
│   ├── github_client.py       # GitHub API client
│   ├── models.py              # Data models
│   ├── filters.py             # Commit filtering
│   ├── report.py              # Markdown generator
│   └── config.py              # Settings
├── main.py                    # Entry point
├── pyproject.toml             # Dependencies + entry point
└── .env                       # Environment variables
```

---

## Implementation Steps

### Step 1: Project restructure - DONE
- Created `diffweek/` package directory
- Moved `git_extract.py` to `diffweek/git_extract.py`
- Created `diffweek/__init__.py` with version info
- Promoted `resolve_repo_path()` to module level
- Removed old `git_extract.py` from root

### Step 2: Add dependencies - DONE
Updated `pyproject.toml`:
```toml
typer = "^0.15.0"  # Changed from ^0.9.0 due to click compatibility
httpx = "^0.27.0"
python-dotenv = "^1.0.0"
pydantic-settings = "^2.0.0"
```
- Changed `package-mode = false` to `packages = [{include = "diffweek"}]`
- Ran `poetry lock && poetry install`

**Note:** Originally planned typer 0.9.0 but upgraded to 0.15.0 to fix click compatibility issue.

### Step 3: Create models (`diffweek/models.py`) - DONE
- `TimeWindow` - datetime-based time range with `since_datetime`/`until_datetime` properties
- `Contributor` - username + emails list
- `PullRequest` - PR metadata from GitHub (number, title, state, url, files_changed, additions, deletions, merged_at)
- `CommitSummary` - aggregated commit data (sha, date, message, files_changed, additions, deletions)
- `ReportData` - all data for report generation

### Step 4: Create config (`diffweek/config.py`) - DONE
- `Settings` class using pydantic-settings with `BaseSettings`
- Loads `GITHUB_PERSONAL_ACCESS_TOKEN` from .env
- `max_diff_lines = 500` setting
- `get_settings()` function with LRU cache

### Step 5: Create GitHub client (`diffweek/github_client.py`) - DONE
- `get_user_emails(username)` - resolves username to email(s) via:
  - Public events API for commit emails
  - GitHub noreply email pattern
  - User profile email
- `get_merged_prs(owner, repo, author, window)` - fetches merged PRs via GitHub search API

### Step 6: Create filters (`diffweek/filters.py`) - DONE
- `filter_by_contributor()` - filters commits/files by email(s), case-insensitive
- `filter_large_diffs()` - marks files > 500 lines with `is_large_diff=True`
- `aggregate_commits()` - converts DataFrames to CommitSummary list, sorted by date

### Step 7: Create report generator (`diffweek/report.py`) - DONE
- `generate_markdown_report(data: ReportData) -> str`
- Sections: Header, Overview, Pull Requests table, Commits table
- Handles empty states with appropriate messages
- Escapes pipe characters in PR titles and commit messages
- Truncates long titles (50 chars) and messages (60 chars)

### Step 8: Create CLI (`diffweek/cli.py`) - DONE
- `report` subcommand with options:
  - `--repo` / `-r` - GitHub repo (owner/repo) or local path (required)
  - `--contributor` / `-c` - GitHub username (required)
  - `--since` / `-s` - relative time (7d, 2w, 1m)
  - `--start` / `--end` - explicit ISO dates
  - `--output` / `-o` - file path (optional, default stdout)
- Added `@app.callback()` to enable subcommand structure
- Progress output via `typer.echo()`
- Defaults to 7 days if no time options provided

### Step 9: Update entry points - DONE
- Updated `main.py` to import from `diffweek.cli`
- Added `diffweek = "diffweek.cli:main"` to pyproject.toml scripts

---

## Changes from Original Plan

| Item | Planned | Actual |
|------|---------|--------|
| Typer version | ^0.9.0 | ^0.15.0 (click compatibility) |
| pyproject.toml | package-mode = false | packages = [{include = "diffweek"}] |
| pandas datetime | - | Added `utc=True` to fix FutureWarning |

---

## Output Format (Phase 1A)

```markdown
# Weekly Engineering Summary
**Contributor:** @username
**Repository:** owner/repo
**Period:** 2026-01-20 to 2026-01-27

## Overview
- **Commits:** 15
- **PRs Merged:** 3
- **Files Changed:** 42
- **Lines Added:** 1,234
- **Lines Removed:** 567

## Pull Requests
| PR | Title | State | Files | +/- |
|----|-------|-------|-------|-----|
| [#123](url) | Fix auth bug | merged | 5 | +120/-45 |

## Commits
| Date | Message | Files | +/- |
|------|---------|-------|-----|
| 2026-01-25 | feat: implement login | 3 | +89/-12 |
```

---

## Verification - COMPLETED

1. `poetry install` - Dependencies installed successfully
2. `diffweek --help` - Shows CLI help with `report` subcommand
3. `diffweek report --help` - Shows all options
4. Tested with local repository (`.`)
5. Tested with remote repository (`anthropics/anthropic-sdk-python`)
6. Tested with explicit dates (`--start 2026-01-20 --end 2026-01-27`)
7. Tested with relative time (`--since 30d`)
8. Tested output file (`--output /tmp/report.md`)

**Results:**
- Repository cloning/caching works correctly
- Contributor emails resolved via GitHub API
- Commits filtered by contributor emails
- PRs fetched from GitHub search API
- Markdown report generated with accurate stats
