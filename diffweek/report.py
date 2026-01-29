"""Markdown report generation."""

from .models import ReportData


def generate_markdown_report(data: ReportData) -> str:
    """
    Generate a markdown report from the report data.

    Args:
        data: ReportData object containing all report information

    Returns:
        Formatted markdown string
    """
    lines = []

    # Header
    lines.append("# Weekly Engineering Summary")
    lines.append(f"**Contributor:** @{data.contributor}")
    lines.append(f"**Repository:** {data.repository}")
    lines.append(f"**Period:** {data.period_start} to {data.period_end}")
    lines.append("")

    # Overview section
    lines.append("## Overview")
    lines.append(f"- **Commits:** {data.total_commits:,}")
    lines.append(f"- **PRs Merged:** {data.total_prs_merged:,}")
    lines.append(f"- **Files Changed:** {data.total_files_changed:,}")
    lines.append(f"- **Lines Added:** {data.total_additions:,}")
    lines.append(f"- **Lines Removed:** {data.total_deletions:,}")
    lines.append("")

    # Pull Requests section
    lines.append("## Pull Requests")
    if data.pull_requests:
        lines.append("| PR | Title | State | Files | +/- |")
        lines.append("|----|-------|-------|-------|-----|")
        for pr in data.pull_requests:
            # Escape pipe characters in title
            title = pr.title.replace("|", "\\|")[:50]
            if len(pr.title) > 50:
                title += "..."
            diff_str = f"+{pr.additions}/-{pr.deletions}"
            lines.append(
                f"| [#{pr.number}]({pr.url}) | {title} | {pr.state} | {pr.files_changed} | {diff_str} |"
            )
    else:
        lines.append("*No pull requests merged in this period.*")
    lines.append("")

    # Commits section
    lines.append("## Commits")
    if data.commits:
        lines.append("| Date | Message | Files | +/- |")
        lines.append("|------|---------|-------|-----|")
        for commit in data.commits:
            # Escape pipe characters in message
            message = commit.message.replace("|", "\\|")[:60]
            if len(commit.message) > 60:
                message += "..."
            diff_str = f"+{commit.additions}/-{commit.deletions}"
            lines.append(
                f"| {commit.date} | {message} | {commit.files_changed} | {diff_str} |"
            )
    else:
        lines.append("*No commits in this period.*")
    lines.append("")

    return "\n".join(lines)
