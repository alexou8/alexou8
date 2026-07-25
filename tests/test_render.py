import xml.etree.ElementTree as ET

from profilecard.model import ProfileStats
from profilecard.render import render
from profilecard.theme import DARK, LIGHT, THEMES

FULL = ProfileStats(
    followers=2,
    repos=12,
    stars=4,
    contributed=2,
    commits=238,
    loc_added=65_373,
    loc_deleted=4_950,
    languages=[["Python", 600], ["TypeScript", 400]],
    weeks=[1, 0, 9, 4, 12],
    activity_total=1204,
    current_streak=12,
    longest_streak=31,
    generated_at="2026-07-25 06:12 UTC",
)


def _parse(svg):
    return ET.fromstring(svg.split("?>", 1)[1])


def test_both_themes_produce_wellformed_svg():
    for theme in THEMES.values():
        root = _parse(render(FULL, theme))
        assert root.tag.endswith("svg")
        assert float(root.get("height")) > 0


def test_render_is_deterministic():
    assert render(FULL, DARK) == render(FULL, DARK)


def test_themes_differ():
    assert render(FULL, DARK) != render(FULL, LIGHT)


def test_stats_reach_the_card():
    svg = render(FULL, DARK)
    assert ">238<" in svg  # commits
    assert ">60,423<" in svg  # net lines of code
    assert "1,204 contributions" in svg
    assert "12 day streak (best 31)" in svg


def test_missing_metrics_render_as_a_dash_not_a_zero():
    svg = render(ProfileStats(generated_at="2026-07-25 06:12 UTC"), DARK)
    assert ">—<" in svg
    assert ">0<" not in svg


def test_empty_stats_still_render():
    root = _parse(render(ProfileStats(), DARK))
    assert float(root.get("height")) > 0


def test_activity_section_is_dropped_without_data():
    assert "ACTIVITY" in render(FULL, DARK)
    assert "ACTIVITY" not in render(ProfileStats(repos=1), DARK)


def test_measured_languages_replace_the_declared_stack():
    with_languages = render(FULL, DARK)
    assert "MEASURED ACROSS REPOSITORIES" in with_languages
    assert "60.0%" in with_languages

    without = render(ProfileStats(repos=1), DARK)
    assert "MEASURED ACROSS REPOSITORIES" not in without
    assert "Python" in without  # declared stack chips


def test_language_bar_segments_fill_the_full_width():
    root = _parse(render(FULL, DARK))
    ns = "{http://www.w3.org/2000/svg}"
    clip = root.find(f".//{ns}clipPath/{ns}rect")
    bar_left = float(clip.get("x"))
    bar_right = bar_left + float(clip.get("width"))

    segments = [
        r
        for group in root.findall(f".//{ns}g")
        for r in group.findall(f"{ns}rect")
    ]
    assert segments, "expected the stacked language bar"
    edge = max(float(r.get("x")) + float(r.get("width")) for r in segments)
    assert abs(edge - bar_right) < 0.01


def test_dev_age_counts_from_the_collection_date():
    # Stats collected in 2026 must not silently re-age when re-rendered later.
    svg = render(FULL, DARK)
    assert "4 years, 10 months, 24 days" in svg


def test_stale_metrics_are_disclosed_on_the_card():
    stats = ProfileStats(repos=12, generated_at="2026-07-25 06:12 UTC")
    stats.stale.extend(["stars", "commits"])
    assert "2 figure(s) served from cache" in render(stats, DARK)


def test_text_is_xml_escaped():
    stats = ProfileStats(generated_at="a & b <c>")
    svg = render(stats, DARK)
    assert "a &amp; b &lt;c&gt;" in svg
    _parse(svg)


def test_activity_strip_is_labelled_for_what_it_counts():
    calendar = ProfileStats(
        weeks=[1, 2, 3],
        activity_total=600,
        activity_source="contributions",
        generated_at="2026-07-25 06:12 UTC",
    )
    assert "ACTIVITY · LAST 3 WEEKS" in render(calendar, DARK)
    assert "600 contributions in the last 3 weeks" in render(calendar, DARK)

    from dataclasses import replace

    commits = replace(calendar, activity_source="commits", activity_total=412)
    assert "COMMITS · LAST 3 WEEKS" in render(commits, DARK)
    assert "412 commits in the last 3 weeks" in render(commits, DARK)


def test_activity_caption_matches_the_window_it_draws():
    """The caption must never describe a longer window than the chart.

    GitHub reports contributions over a trailing year while the strip draws
    a shorter window, and quoting the year total under a 30-week chart put
    two different periods side by side as if they were one figure.
    """
    weeks = [827, 808, 771, 14, 0, 35, 42]
    stats = ProfileStats(
        weeks=weeks,
        activity_total=sum(weeks),
        activity_source="contributions",
        generated_at="2026-07-25 06:12 UTC",
    )
    svg = render(stats, DARK)
    assert f"{sum(weeks):,} contributions in the last {len(weeks)} weeks" in svg
