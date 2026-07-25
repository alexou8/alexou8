"""Turn raw GitHub API responses into a single ProfileStats object."""

from __future__ import annotations

from . import config
from .github import GitHubClient, TokenUnusable
from .model import ProfileStats, utc_stamp

__all__ = ["collect", "TokenUnusable", "streaks", "weekly_totals", "top_languages"]


def collect(client: GitHubClient) -> ProfileStats:
    """Fetch everything the card shows.  Never raises for a missing metric."""
    stats = ProfileStats(generated_at=utc_stamp())

    repos, warnings = client.fetch_repositories()
    for message in warnings:
        stats.warn(message)

    if repos:
        stats.repos = len(repos)
        star_counts = [r["stars"] for r in repos if r["stars"] is not None]
        fork_counts = [r["forks"] for r in repos if r["forks"] is not None]
        if star_counts:
            stats.stars = sum(star_counts)
        if fork_counts:
            stats.forks = sum(fork_counts)
        stats.languages = top_languages(repos)
    else:
        stats.warn("no repositories returned")

    stats.followers, messages = client.fetch_followers()
    for message in messages:
        stats.warn(message)

    stats.contributed, messages = client.fetch_contributed()
    for message in messages:
        stats.warn(message)

    stats.commits, messages = client.fetch_commit_total()
    for message in messages:
        stats.warn(message)

    days, total, messages = client.fetch_contribution_calendar()
    for message in messages:
        stats.warn(message)
    if days:
        stats.activity_source = "contributions"
        stats.weeks = weekly_totals(days)
        # GitHub's `total` covers the trailing year; the strip draws a
        # shorter window, so summing the drawn weeks keeps the two in step.
        stats.activity_total = sum(stats.weeks)
        stats.current_streak, stats.longest_streak = streaks(days)
    elif repos:
        # No calendar access.  Fall back to commit history, which any token
        # can read for public repositories, so the strip still shows real
        # activity instead of vanishing.
        days, commit_total, messages = client.fetch_commit_activity(repos)
        for message in messages:
            stats.warn(message)
        if days:
            stats.activity_source = "commits"
            stats.weeks = weekly_totals(days)
            stats.activity_total = sum(stats.weeks)
            stats.current_streak, stats.longest_streak = streaks(days)
        if stats.commits is None and commit_total:
            stats.commits = commit_total
            stats.warn(
                "commit total counts only the default branches of the "
                "repositories listed above, not every contribution"
            )

    if repos:
        added, deleted, messages = client.fetch_loc(repos)
        for message in messages:
            stats.warn(message)
        stats.loc_added, stats.loc_deleted = added, deleted

    if client.saw_forbidden:
        stats.warn(
            "the token was refused on at least one resource — if this is the "
            "default GITHUB_TOKEN, set a personal access token as the "
            "ACCESS_TOKEN secret"
        )

    return stats


def top_languages(repos: list) -> list:
    """Aggregate language bytes across repos into the card's segment list."""
    totals: dict = {}
    for repo in repos:
        for name, size in (repo.get("languages") or {}).items():
            if name in config.LANGUAGE_DENYLIST:
                continue
            totals[name] = totals.get(name, 0) + int(size)

    if not totals:
        return []

    # Ties sort by name so the SVG is byte-stable between runs.
    ordered = sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))
    head = ordered[: config.LANGUAGE_SLOTS]
    tail = ordered[config.LANGUAGE_SLOTS :]
    segments = [[name, size] for name, size in head]
    if tail:
        segments.append(["Other", sum(size for _, size in tail)])
    return segments


def weekly_totals(days: list, weeks: int = 30) -> list:
    """Collapse (date, count) pairs into the trailing *weeks* week totals."""
    counts = [count for _, count in days]
    # Trim from the front so the buckets align to the most recent day.
    usable = len(counts) - (len(counts) % 7)
    counts = counts[len(counts) - usable :] if usable else []
    buckets = [sum(counts[i : i + 7]) for i in range(0, len(counts), 7)]
    return buckets[-weeks:]


def streaks(days: list) -> tuple:
    """Return (current_streak, longest_streak) in days.

    A zero on the most recent day does not break the current streak: that
    day is still in progress, which is how GitHub's own counter behaves.
    """
    counts = [count for _, count in days]
    if not counts:
        return None, None

    longest = run = 0
    for count in counts:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)

    tail = counts[:-1] if counts and counts[-1] == 0 else counts
    current = 0
    for count in reversed(tail):
        if count <= 0:
            break
        current += 1
    return current, longest
