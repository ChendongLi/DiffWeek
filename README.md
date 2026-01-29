# DiffWeek

Generate weekly engineering summaries from real code changes.

## Goal

DiffWeek is a CLI tool that analyzes git repositories and GitHub PRs to generate comprehensive weekly engineering summaries. It extracts commit statistics, pull request metadata, and code change metrics for individual contributors.

**Use cases:**
- Weekly status updates for engineering managers
- Performance reviews and contribution tracking
- Team retrospectives and sprint summaries
- Personal productivity tracking

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/DiffWeek.git
cd DiffWeek

# Install dependencies with Poetry
poetry install
```

## Configuration

Create a `.env` file with your GitHub token for API access:

```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_your_token_here
```

## Usage (Phase 1A)

Generate a weekly engineering summary report (will save to report folder by default)

```bash
# Using relative time (7 days, 2 weeks, 1 month)
diffweek report --repo owner/repo --contributor username --since 7d

# Using explicit date range
diffweek report --repo owner/repo --contributor username --start 2026-01-20 --end 2026-01-27

# Using a local repository
diffweek report --repo ./path/to/repo --contributor username --since 7d

# Output is saved to report/{contributor}_{date}.md by default
diffweek report --repo owner/repo --contributor username --since 7d

# Save output to a custom file
diffweek report --repo owner/repo --contributor username --since 7d --output custom-report.md
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--repo` | `-r` | GitHub repo (owner/repo) or local path (required) |
| `--contributor` | `-c` | GitHub username of the contributor (required) |
| `--since` | `-s` | Relative time period: `7d`, `2w`, `1m` |
| `--start` | | Start date (ISO format: YYYY-MM-DD) |
| `--end` | | End date (ISO format: YYYY-MM-DD) |
| `--output` | `-o` | Output file path (default: `report/{contributor}_{date}.md`) |

### Example Output

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

## Project Structure

```
DiffWeek/
├── diffweek/
│   ├── __init__.py        # Package init
│   ├── cli.py             # Typer CLI
│   ├── config.py          # Settings (pydantic-settings)
│   ├── filters.py         # Commit filtering and aggregation
│   ├── git_extract.py     # Git data extraction
│   ├── github_client.py   # GitHub API client
│   ├── models.py          # Data models
│   └── report.py          # Markdown report generator
├── report/                # Generated reports (default output)
├── main.py                # Entry point
├── pyproject.toml         # Dependencies and config
└── .env                   # Environment variables
```

## Roadmap

- **Phase 1A** (current): CLI with git stats + PR metadata
- **Phase 1B**: LLM-powered summary generation
- **Phase 2**: Web interface and scheduled reports
