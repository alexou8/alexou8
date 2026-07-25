#!/usr/bin/env python3
"""Regenerate the profile README cards.

    python generate_svg.py            # fetch from GitHub, then render
    python generate_svg.py --offline  # render from cache/stats.json only
    python generate_svg.py --check    # verify the committed SVGs are current
    python generate_svg.py --strict   # exit non-zero if any metric degraded

Environment:
    ACCESS_TOKEN / GITHUB_TOKEN   GitHub token used for the API calls
    USER_NAME                     GitHub login (defaults to config.LOGIN)

A run that cannot reach part of the API is *not* a failure.  Missing metrics
fall back to the previous run's cached values, the card still regenerates,
and the reason is reported as a workflow annotation.  Only a token that
cannot identify the user at all stops the run.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from profilecard import config, model, render
from profilecard.collect import TokenUnusable, collect
from profilecard.github import GitHubClient
from profilecard.theme import THEMES


def _annotate(level: str, message: str) -> None:
    """Emit a GitHub Actions annotation, or a plain line when run locally."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::{level}::{message}")
    else:
        print(f"[{level}] {message}")


def _summary(lines: list) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_cards(stats: model.ProfileStats) -> dict:
    """Render every theme.  Returns {path: svg_text}."""
    return {
        Path(filename): render.render(stats, THEMES[name])
        for name, filename in config.OUTPUTS.items()
    }


def _fetch(login: str) -> model.ProfileStats:
    token = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("No GitHub token found. Set ACCESS_TOKEN or GITHUB_TOKEN.")

    client = GitHubClient(token, login)
    capability = client.probe()
    if not capability["can_read_stars"]:
        _annotate(
            "warning",
            "This token cannot read repository star counts. That is the "
            "signature of the default GITHUB_TOKEN or an expired personal "
            "access token — add a fine-grained PAT as the ACCESS_TOKEN "
            "secret to restore full stats.",
        )

    stats = collect(client)
    return stats


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the API entirely and render from cache/stats.json",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="render and compare against the committed SVGs without writing",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero when any metric had to fall back to cache",
    )
    args = parser.parse_args(argv)

    login = os.environ.get("USER_NAME") or config.LOGIN
    config.LOGIN = login

    cached = model.load_cache()

    if args.offline or args.check:
        # Rendering is a pure function of the stats — including the dev-age
        # row, which counts from `generated_at` — so re-rendering the
        # committed cache must reproduce the committed SVGs byte for byte.
        stats = cached
    else:
        try:
            stats = _fetch(login)
        except TokenUnusable as exc:
            _annotate("error", f"GitHub token is unusable: {exc}")
            return 1
        model.merge_with_cache(stats, cached)

    cards = _write_cards(stats)

    if args.check:
        drift = [
            str(path)
            for path, svg in cards.items()
            if not path.exists() or path.read_text() != svg
        ]
        if drift:
            _annotate("error", f"SVGs are out of date: {', '.join(drift)}")
            return 1
        print("Cards match the committed SVGs.")
        return 0

    for path, svg in cards.items():
        path.write_text(svg)
        print(f"wrote {path} ({len(svg):,} bytes)")

    if not args.offline:
        model.save_cache(stats)

    # ── report ───────────────────────────────────────────────────────────
    for warning in stats.warnings:
        _annotate("warning", warning)
    if stats.stale:
        _annotate(
            "notice",
            "served from the previous run's cache: " + ", ".join(sorted(stats.stale)),
        )

    summary = [
        "### Profile card refresh",
        "",
        f"- User: `{login}`",
        f"- Generated: {stats.generated_at or 'n/a'}",
        f"- Repos: {stats.repos} · Stars: {stats.stars} · "
        f"Followers: {stats.followers} · Commits: {stats.commits}",
        f"- Lines of code: {stats.loc_net}",
        f"- Languages measured: {len(stats.languages)}",
    ]
    if stats.stale:
        summary += ["", f"⚠️ Cached values used for: {', '.join(sorted(stats.stale))}"]
    if stats.warnings:
        summary += ["", "**Warnings**"] + [f"- {w}" for w in stats.warnings]
    _summary(summary)

    if args.strict and stats.degraded:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
