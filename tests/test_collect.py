from profilecard import config
from profilecard.collect import streaks, top_languages, weekly_totals


def _days(counts):
    return [(f"2026-01-{i + 1:02d}", count) for i, count in enumerate(counts)]


def test_top_languages_aggregates_across_repos():
    repos = [
        {"languages": {"Python": 100, "HTML": 10}},
        {"languages": {"Python": 50, "TypeScript": 200}},
    ]
    assert top_languages(repos) == [
        ["TypeScript", 200],
        ["Python", 150],
        ["HTML", 10],
    ]


def test_top_languages_honours_the_denylist():
    repos = [{"languages": {"Python": 10, "Jupyter Notebook": 9_000_000}}]
    assert top_languages(repos) == [["Python", 10]]


def test_top_languages_collapses_the_tail_into_other():
    repos = [{"languages": {f"Lang{i}": 100 - i for i in range(10)}}]
    segments = top_languages(repos)

    assert len(segments) == config.LANGUAGE_SLOTS + 1
    assert segments[-1][0] == "Other"
    # Nothing may be lost in the collapse.
    assert sum(size for _, size in segments) == sum(100 - i for i in range(10))


def test_top_languages_without_data():
    assert top_languages([{"languages": {}}]) == []


def test_weekly_totals_buckets_from_the_most_recent_day():
    days = _days([1] * 21)
    assert weekly_totals(days, weeks=2) == [7, 7]


def test_weekly_totals_drops_a_partial_leading_week():
    # 9 days -> one whole week, with the two oldest days trimmed.
    days = _days([1] * 9)
    assert weekly_totals(days) == [7]


def test_current_streak_ignores_a_still_running_today():
    # Three active days, then a zero for today.
    current, longest = streaks(_days([0, 5, 5, 5, 0]))
    assert current == 3
    assert longest == 3


def test_current_streak_breaks_on_an_older_zero():
    current, _ = streaks(_days([5, 5, 0, 5]))
    assert current == 1


def test_longest_streak_spans_the_whole_history():
    _, longest = streaks(_days([1, 1, 1, 1, 0, 1, 1]))
    assert longest == 4


def test_streaks_without_data():
    assert streaks([]) == (None, None)
