"""Generate terminal-style SVG profile cards for the alexou8 GitHub README.

Fetches live statistics from the GitHub GraphQL API and updates the dynamic
element IDs in dark_mode.svg and light_mode.svg.  Both files must already
exist in the repository root; this script updates them in place and writes
them back to disk.  Run via the GitHub Actions workflow on a schedule so the
README always shows current numbers.

Required environment variables:
  ACCESS_TOKEN   – GitHub personal access token (repo + read:user scopes)
  USER_NAME      – GitHub username (defaults to repository owner)
"""

import datetime
import os
import sys
import time
from pathlib import Path

import requests
from dateutil import relativedelta
from lxml import etree

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

GITHUB_GRAPHQL = "https://api.github.com/graphql"
CACHE_DIR = Path("cache")
SVG_FILES = ("dark_mode.svg", "light_mode.svg")

# Date used to calculate the "Dev Age" field shown on the card.
# Represents when Alex began studying Computer Science at Wilfrid Laurier.
DEV_SINCE = datetime.datetime(2021, 9, 1)

# Column widths used to build the dot-padding for each dynamic stat field.
# The formula is: dots = max(0, WIDTH - len(value)) dots characters surrounded
# by a leading and trailing space.  WIDTH is chosen so that prefix + dots +
# value always sums to the target line width (60 characters from x=390).
#
# Prefix lengths (". KEY:" or ". KEY.SUBKEY:"):
#   Dev Age:          10  →  WIDTH = 60 - 10 - 2 = 48
#   Repos:             8  →  WIDTH =  6  (independent column alignment)
#   Stars:            (right column, independent)  →  WIDTH = 14
#   Commits:          10  →  WIDTH = 22
#   Followers:        (right column)  →  WIDTH = 10
#   GitHub LOC:       12  →  WIDTH = 25
AGE_DATA_WIDTH = 48
COMMIT_DATA_WIDTH = 22
LOC_DATA_WIDTH = 25
FOLLOWER_DATA_WIDTH = 10
REPO_DATA_WIDTH = 6
STAR_DATA_WIDTH = 14

# Stats rows use a two-column layout.  The gap between the left and right
# halves is padded so both rows line up at the same column.
STATS_SECONDARY_COLUMN_WIDTH = 34
STATS_SECONDARY_SEPARATOR = " |  "

# Runtime state populated during configure_environment().
HEADERS: dict = {}
USER_NAME: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Environment helpers
# ──────────────────────────────────────────────────────────────────────────────


def configure_environment() -> None:
    """Read required environment variables and set module-level globals."""
    global HEADERS, USER_NAME
    token = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "No GitHub token found.  Set ACCESS_TOKEN or GITHUB_TOKEN."
        )
    USER_NAME = os.environ.get("USER_NAME") or os.environ.get(
        "GITHUB_REPOSITORY_OWNER", ""
    )
    if not USER_NAME:
        raise RuntimeError(
            "No GitHub username found.  Set USER_NAME."
        )
    HEADERS = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
    }


# ──────────────────────────────────────────────────────────────────────────────
# GitHub GraphQL helpers
# ──────────────────────────────────────────────────────────────────────────────


def graphql_request(operation: str, query: str, variables: dict) -> dict:
    """Send one GraphQL request and raise on any failure."""
    try:
        resp = requests.post(
            GITHUB_GRAPHQL,
            json={"query": query, "variables": variables},
            headers=HEADERS,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"{operation} request failed: {exc}") from exc

    if resp.status_code == 403:
        raise RuntimeError("GitHub returned 403 – rate limit or bad token.")
    if resp.status_code != 200:
        raise RuntimeError(
            f"{operation} failed with status {resp.status_code}: {resp.text}"
        )

    try:
        payload = resp.json()
    except ValueError as exc:
        raise RuntimeError(
            f"{operation} returned invalid JSON: {resp.text}"
        ) from exc

    if payload.get("errors"):
        raise RuntimeError(
            f"{operation} returned GraphQL errors: {payload['errors']}"
        )

    return payload["data"]


# ──────────────────────────────────────────────────────────────────────────────
# GitHub data fetchers
# ──────────────────────────────────────────────────────────────────────────────


def fetch_user_stats() -> dict:
    """Fetch followers, public repos, and stars in one paginated pass."""
    query = """
    query($login: String!, $cursor: String) {
        user(login: $login) {
            followers { totalCount }
            repositories(
                first: 100
                after: $cursor
                ownerAffiliations: [OWNER]
                isFork: false
            ) {
                totalCount
                pageInfo { endCursor hasNextPage }
                edges {
                    node { stargazers { totalCount } }
                }
            }
        }
    }"""

    followers = 0
    total_repos = 0
    total_stars = 0
    cursor = None
    first = True

    while True:
        data = graphql_request(
            "fetch_user_stats", query, {"login": USER_NAME, "cursor": cursor}
        )
        user = data["user"]

        if first:
            followers = user["followers"]["totalCount"]
            first = False

        repos = user["repositories"]
        total_repos = repos["totalCount"]
        for edge in repos["edges"]:
            total_stars += edge["node"]["stargazers"]["totalCount"]

        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    return {
        "followers": followers,
        "repos": total_repos,
        "stars": total_stars,
    }


def fetch_contributed_repos() -> int:
    """Count repos the user has contributed to (includes non-owned repos)."""
    query = """
    query($login: String!) {
        user(login: $login) {
            repositoriesContributedTo(
                first: 1
                contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]
            ) { totalCount }
        }
    }"""
    data = graphql_request("fetch_contributed_repos", query, {"login": USER_NAME})
    return data["user"]["repositoriesContributedTo"]["totalCount"]


def fetch_commit_count() -> int:
    """Approximate total commits via the GitHub search API."""
    try:
        resp = requests.get(
            "https://api.github.com/search/commits",
            headers={
                **HEADERS,
                "Accept": "application/vnd.github.cloak-preview+json",
            },
            params={"q": f"author:{USER_NAME}", "per_page": 1},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("total_count", 0)
    except requests.RequestException:
        pass
    return 0


def fetch_loc_stats() -> tuple:
    """
    Compute total lines of code added and deleted across all owned repos.

    Uses the REST contributor-statistics endpoint which returns weekly
    aggregates per contributor.  GitHub may respond with 202 (computing) the
    first time; this function retries up to three times with a short backoff.

    Returns (additions, deletions, net_loc) as integers.
    """
    cache_file = CACHE_DIR / "loc_cache.txt"
    CACHE_DIR.mkdir(exist_ok=True)

    # Load any previously cached repo slugs so we can skip re-fetching them.
    cached: dict = {}
    if cache_file.exists():
        for line in cache_file.read_text().splitlines():
            parts = line.split()
            if len(parts) == 3:
                slug, adds, dels = parts
                cached[slug] = (int(adds), int(dels))

    # Collect all owned repo slugs.
    repos_query = """
    query($login: String!, $cursor: String) {
        user(login: $login) {
            repositories(
                first: 100
                after: $cursor
                ownerAffiliations: [OWNER]
                isFork: false
            ) {
                pageInfo { endCursor hasNextPage }
                edges { node { nameWithOwner } }
            }
        }
    }"""
    slugs: list = []
    cursor = None
    while True:
        data = graphql_request("fetch_repos_for_loc", repos_query, {"login": USER_NAME, "cursor": cursor})
        repos = data["user"]["repositories"]
        for edge in repos["edges"]:
            slugs.append(edge["node"]["nameWithOwner"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    total_adds = 0
    total_dels = 0
    updated_cache: dict = {}

    for slug in slugs:
        if slug in cached:
            adds, dels = cached[slug]
            updated_cache[slug] = (adds, dels)
            total_adds += adds
            total_dels += dels
            continue

        url = f"https://api.github.com/repos/{slug}/stats/contributors"
        adds, dels = 0, 0
        for attempt in range(4):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
            except requests.RequestException:
                break
            if resp.status_code == 202:
                time.sleep(5)
                continue
            if resp.status_code != 200:
                break
            for contrib in resp.json():
                author = (contrib.get("author") or {}).get("login", "")
                if author.lower() != USER_NAME.lower():
                    continue
                for week in contrib.get("weeks", []):
                    adds += week.get("a", 0)
                    dels += week.get("d", 0)
            break

        updated_cache[slug] = (adds, dels)
        total_adds += adds
        total_dels += dels

    # Persist cache for next run.
    lines = [f"{slug} {a} {d}\n" for slug, (a, d) in updated_cache.items()]
    cache_file.write_text("".join(lines))

    return total_adds, total_dels, total_adds - total_dels


# ──────────────────────────────────────────────────────────────────────────────
# Dev-age calculator
# ──────────────────────────────────────────────────────────────────────────────


def format_dev_age() -> str:
    """Return a human-readable string like '4 years, 7 months, 6 days'."""
    today = datetime.date.today()
    diff = relativedelta.relativedelta(today, DEV_SINCE.date())
    parts = [
        f"{diff.years} year{'s' if diff.years != 1 else ''}",
        f"{diff.months} month{'s' if diff.months != 1 else ''}",
        f"{diff.days} day{'s' if diff.days != 1 else ''}",
    ]
    # Show birthday emoji only on the exact anniversary date.
    suffix = " 🎂" if diff.months == 0 and diff.days == 0 else ""
    return ", ".join(parts) + suffix


# ──────────────────────────────────────────────────────────────────────────────
# SVG update helpers
# ──────────────────────────────────────────────────────────────────────────────


def find_and_replace(root: etree._Element, element_id: str, text: str) -> None:
    """Find an SVG element by id and update its text content."""
    el = root.find(f".//*[@id='{element_id}']")
    if el is not None:
        el.text = text


def build_dot_string(value: str, width: int) -> str:
    """Build the dot-padding string that keeps labels and values aligned.

    Returns a string of the form ' ....... ' where the number of dots is
    ``max(0, width - len(value))``.  Edge cases for very short padding are
    handled to keep the output printable.
    """
    just_len = max(0, width - len(value))
    if just_len == 0:
        return ""
    if just_len == 1:
        return " "
    if just_len == 2:
        return ". "
    return " " + "." * just_len + " "


def format_number(value) -> str:
    """Format an integer with thousands separators."""
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def format_compact(value) -> str:
    """Shorten large numbers to compact form (e.g. 1,234,567 → 1.23M)."""
    if isinstance(value, str):
        normalised = value.replace(",", "").strip().upper()
        if normalised.endswith(("M", "K")):
            return value
        try:
            value = int(normalised)
        except ValueError:
            return value

    abs_val = abs(value)
    if abs_val >= 1_000_000:
        s = f"{value / 1_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{s}M"
    if abs_val >= 1_000:
        s = f"{value / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{s}K"
    return str(value)


def justify_format(
    root: etree._Element, element_id: str, value, width: int = 0
) -> None:
    """Update a stat element and regenerate its companion dot-padding field."""
    text = format_number(value)
    find_and_replace(root, element_id, text)
    dots = build_dot_string(text, width)
    find_and_replace(root, f"{element_id}_dots", dots)


def repo_stats_left_width(repo_data: str, contrib_data: str) -> int:
    """Character count of the left half of the Repos/Stars stats row."""
    repo_dots = build_dot_string(repo_data, REPO_DATA_WIDTH)
    return len(
        f". Repos:{repo_dots}{repo_data} {{Contributed: {contrib_data}}}"
    )


def commit_stats_left_width(commit_data: str) -> int:
    """Character count of the left half of the Commits/Followers stats row."""
    commit_dots = build_dot_string(commit_data, COMMIT_DATA_WIDTH)
    return len(f". Commits:{commit_dots}{commit_data}")


def secondary_stat_gap(left_width: int) -> str:
    """Build the separator that aligns the right stat column."""
    padding = " " * max(0, STATS_SECONDARY_COLUMN_WIDTH - left_width)
    return padding + STATS_SECONDARY_SEPARATOR


def svg_overwrite(
    filename: str,
    age_data: str,
    commit_data: int,
    star_data: int,
    repo_data: int,
    contrib_data: int,
    follower_data: int,
    loc_data: list,
) -> None:
    """Open one SVG file and replace all dynamic stat elements in place."""
    tree = etree.parse(filename)
    root = tree.getroot()

    justify_format(root, "age_data", age_data, AGE_DATA_WIDTH)
    justify_format(root, "commit_data", commit_data, COMMIT_DATA_WIDTH)
    justify_format(root, "star_data", star_data, STAR_DATA_WIDTH)
    justify_format(root, "repo_data", repo_data, REPO_DATA_WIDTH)
    justify_format(root, "contrib_data", contrib_data)
    justify_format(root, "follower_data", follower_data, FOLLOWER_DATA_WIDTH)
    justify_format(root, "loc_data", loc_data[2], LOC_DATA_WIDTH)
    find_and_replace(root, "loc_add", format_compact(loc_data[0]))
    find_and_replace(root, "loc_del", format_compact(loc_data[1]))
    find_and_replace(root, "loc_del_dots", "")

    repo_text = format_number(repo_data)
    contrib_text = format_number(contrib_data)
    commit_text = format_number(commit_data)

    find_and_replace(
        root,
        "repo_stats_gap",
        secondary_stat_gap(repo_stats_left_width(repo_text, contrib_text)),
    )
    find_and_replace(
        root,
        "commit_stats_gap",
        secondary_stat_gap(commit_stats_left_width(commit_text)),
    )

    tree.write(filename, encoding="utf-8", xml_declaration=True)


# ──────────────────────────────────────────────────────────────────────────────
# Timing helpers
# ──────────────────────────────────────────────────────────────────────────────


def timed(fn, *args):
    """Run *fn* and return (result, elapsed_seconds)."""
    start = time.perf_counter()
    result = fn(*args)
    return result, time.perf_counter() - start


def print_duration(label: str, seconds: float) -> None:
    metric = f"{seconds:.4f} s" if seconds >= 1 else f"{seconds * 1000:.2f} ms"
    print(f"   {label + ':':<22}{metric:>12}")


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    configure_environment()
    print(f"Generating SVGs for: {USER_NAME}")
    print("Calculation times:")

    age_data, age_t = timed(format_dev_age)
    print_duration("dev age", age_t)

    user_stats, user_t = timed(fetch_user_stats)
    print_duration("user stats", user_t)

    contrib_count, contrib_t = timed(fetch_contributed_repos)
    print_duration("contributed repos", contrib_t)

    commit_count, commit_t = timed(fetch_commit_count)
    print_duration("commit count", commit_t)

    loc_raw, loc_t = timed(fetch_loc_stats)
    print_duration("LOC stats", loc_t)

    # Format LOC values as comma-separated integers; keep a boolean cache flag
    # in the last slot to signal whether data came from cache (not used here
    # but kept for compatibility with the SVG writer signature).
    loc_data = [loc_raw[0], loc_raw[1], loc_raw[2]]

    for svg_file in SVG_FILES:
        svg_overwrite(
            svg_file,
            age_data=age_data,
            commit_data=commit_count,
            star_data=user_stats["stars"],
            repo_data=user_stats["repos"],
            contrib_data=contrib_count,
            follower_data=user_stats["followers"],
            loc_data=loc_data,
        )
        print(f"Updated {svg_file}")

    total = age_t + user_t + contrib_t + commit_t + loc_t
    print(f"{'Total time:':<23} {total:>11.4f} s")


if __name__ == "__main__":
    main()
