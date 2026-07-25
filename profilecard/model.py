"""The stats data model and its last-known-good cache.

The card is regenerated every day by a scheduled workflow.  Any single run
may lose access to part of the GitHub API — a token expires, a scope is
dropped, an endpoint rate limits — and when that happens writing a zero into
the README would be worse than showing yesterday's number.  So every metric
is optional, and `merge_with_cache` fills the gaps from the previous run
while recording what it had to fall back on.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

CACHE_DIR = Path("cache")
STATS_CACHE = CACHE_DIR / "stats.json"

# Metrics that carry over from the previous run when a fetch comes back empty.
CARRYOVER = (
    "followers",
    "repos",
    "stars",
    "forks",
    "contributed",
    "commits",
    "loc_added",
    "loc_deleted",
    "languages",
    "weeks",
    "contributions_total",
    "current_streak",
    "longest_streak",
    "activity_source",
)


@dataclass
class ProfileStats:
    """Every number the card can display.  ``None``/empty means 'not fetched'."""

    followers: int | None = None
    repos: int | None = None
    stars: int | None = None
    forks: int | None = None
    contributed: int | None = None
    commits: int | None = None

    loc_added: int | None = None
    loc_deleted: int | None = None

    # [[language, bytes], ...] sorted descending; a list of pairs rather than
    # a dict so the JSON round-trip preserves ordering explicitly.
    languages: list = field(default_factory=list)

    # Weekly contribution counts, oldest first.
    weeks: list = field(default_factory=list)
    contributions_total: int | None = None
    current_streak: int | None = None
    longest_streak: int | None = None
    # "contributions" (the full calendar) or "commits" (repository history),
    # so the card can label the activity strip for what it actually counts.
    activity_source: str = ""

    generated_at: str = ""

    # Names of metrics served from cache this run, plus human-readable
    # explanations of what went wrong.  Neither is persisted.
    stale: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def loc_net(self) -> int | None:
        if self.loc_added is None or self.loc_deleted is None:
            return None
        return self.loc_added - self.loc_deleted

    @property
    def degraded(self) -> bool:
        return bool(self.stale or self.warnings)

    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def to_json(self) -> dict:
        data = asdict(self)
        # Transient diagnostics never belong in the committed cache.
        data.pop("stale", None)
        data.pop("warnings", None)
        return data


def _is_empty(value) -> bool:
    return value is None or (isinstance(value, (list, str)) and not value)


def load_cache(path: Path = STATS_CACHE) -> ProfileStats:
    """Read the previous run's stats, returning empty stats if unavailable."""
    if not path.exists():
        return ProfileStats()
    try:
        raw = json.loads(path.read_text())
    except (ValueError, OSError):
        return ProfileStats()
    known = {f.name for f in fields(ProfileStats)}
    return ProfileStats(**{k: v for k, v in raw.items() if k in known})


def merge_with_cache(fresh: ProfileStats, cached: ProfileStats) -> ProfileStats:
    """Fill gaps in *fresh* from *cached*, recording which fields went stale.

    Returns *fresh* mutated in place so callers can keep their reference.
    """
    for name in CARRYOVER:
        if not _is_empty(getattr(fresh, name)):
            continue
        previous = getattr(cached, name)
        if _is_empty(previous):
            continue
        setattr(fresh, name, previous)
        fresh.stale.append(name)
    return fresh


def save_cache(stats: ProfileStats, path: Path = STATS_CACHE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats.to_json(), indent=2, sort_keys=True) + "\n")


def utc_stamp(now: datetime.datetime | None = None) -> str:
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M UTC")


def parse_stamp(stamp: str) -> datetime.date | None:
    """Read back the date part of a `utc_stamp` string."""
    try:
        return datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M UTC").date()
    except (TypeError, ValueError):
        return None
