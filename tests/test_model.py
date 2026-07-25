import json

from profilecard.model import (
    ProfileStats,
    load_cache,
    merge_with_cache,
    parse_stamp,
    save_cache,
)


def test_merge_fills_only_missing_fields():
    fresh = ProfileStats(repos=14, stars=None, languages=[])
    cached = ProfileStats(repos=12, stars=7, languages=[["Python", 100]])

    merged = merge_with_cache(fresh, cached)

    assert merged.repos == 14, "a fetched value must win over the cache"
    assert merged.stars == 7
    assert merged.languages == [["Python", 100]]
    assert set(merged.stale) == {"stars", "languages"}


def test_merge_leaves_zero_alone():
    # Zero stars is a real answer, not a missing one.
    merged = merge_with_cache(ProfileStats(stars=0), ProfileStats(stars=9))
    assert merged.stars == 0
    assert merged.stale == []


def test_merge_without_cache_records_nothing():
    merged = merge_with_cache(ProfileStats(repos=None), ProfileStats())
    assert merged.repos is None
    assert merged.stale == []


def test_cache_round_trip_drops_diagnostics(tmp_path):
    path = tmp_path / "stats.json"
    stats = ProfileStats(repos=12, generated_at="2026-07-25 06:12 UTC")
    stats.warn("something went wrong")
    stats.stale.append("stars")

    save_cache(stats, path)
    written = json.loads(path.read_text())

    assert "warnings" not in written and "stale" not in written
    assert load_cache(path).repos == 12


def test_load_cache_survives_corruption(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text("{ not json")
    assert load_cache(path) == ProfileStats()


def test_loc_net_needs_both_halves():
    assert ProfileStats(loc_added=100, loc_deleted=40).loc_net == 60
    assert ProfileStats(loc_added=100).loc_net is None


def test_parse_stamp():
    assert str(parse_stamp("2026-07-25 06:12 UTC")) == "2026-07-25"
    assert parse_stamp("") is None
