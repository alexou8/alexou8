"""Regression tests for the failure that broke the daily refresh.

An expired ACCESS_TOKEN made Actions fall back to the repository-scoped
GITHUB_TOKEN, and GitHub answered the repository query with a full `data`
block plus one FORBIDDEN error per inaccessible `stargazerCount`.  The old
generator raised on any GraphQL error and the workflow went red every day.
"""

import json

import pytest

from profilecard.github import GitHubClient


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession:
    """Serves canned responses and records what was asked for."""

    def __init__(self, post=None, get=None):
        self.headers = {}
        self._post = post or (lambda: FakeResponse(200, {"data": {}}))
        self._get = get or (lambda path: FakeResponse(404))
        self.get_paths = []

    def post(self, url, **kwargs):
        return self._post()

    def get(self, url, **kwargs):
        path = url.replace("https://api.github.com", "")
        self.get_paths.append(path)
        return self._get(path)


def _client(session):
    client = GitHubClient("token", "alexou8")
    client.session = session
    return client


FORBIDDEN_REPOS = {
    "data": {
        "user": {
            "repositories": {
                "totalCount": 2,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "nameWithOwner": "alexou8/one",
                        "pushedAt": "2026-07-01T00:00:00Z",
                        "isPrivate": False,
                        "stargazerCount": None,
                        "forkCount": None,
                        "languages": None,
                    },
                    {
                        "nameWithOwner": "alexou8/two",
                        "pushedAt": "2026-07-02T00:00:00Z",
                        "isPrivate": False,
                        "stargazerCount": None,
                        "forkCount": None,
                        "languages": None,
                    },
                ],
            }
        }
    },
    "errors": [
        {
            "type": "FORBIDDEN",
            "path": ["user", "repositories", "nodes", 0, "stargazerCount"],
            "message": "Resource not accessible by integration",
        }
    ],
}


def test_partial_forbidden_response_keeps_its_data():
    session = FakeSession(post=lambda: FakeResponse(200, FORBIDDEN_REPOS))
    client = _client(session)

    data, errors = client.graphql("query {}", {})

    assert data is not None, "partial data must survive a FORBIDDEN error"
    assert client.saw_forbidden is True
    assert errors and "FORBIDDEN" in errors[0]


def test_repository_fetch_falls_back_to_rest_for_star_counts():
    def get(path):
        if path == "/users/alexou8/repos":
            return FakeResponse(
                200,
                [
                    {"full_name": "alexou8/one", "stargazers_count": 3, "forks_count": 1},
                    {"full_name": "alexou8/two", "stargazers_count": 4, "forks_count": 0},
                ],
            )
        if path.endswith("/languages"):
            return FakeResponse(200, {"Python": 120})
        return FakeResponse(404)

    client = _client(
        FakeSession(post=lambda: FakeResponse(200, FORBIDDEN_REPOS), get=get)
    )
    repos, warnings = client.fetch_repositories()

    assert [r["stars"] for r in repos] == [3, 4]
    assert all(r["languages"] == {"Python": 120} for r in repos)
    assert any("REST" in w for w in warnings)


def test_unauthorized_token_yields_no_data():
    client = _client(FakeSession(post=lambda: FakeResponse(401)))
    data, errors = client.graphql("query {}", {})

    assert data is None
    assert "401" in errors[0]


def test_forbidden_commit_search_is_reported_not_raised():
    client = _client(FakeSession(get=lambda path: FakeResponse(403)))
    total, warnings = client.fetch_commit_total()

    assert total is None
    assert warnings and "forbidden" in warnings[0]
    assert client.saw_forbidden is True


def test_loc_reuses_the_cache_until_a_repository_is_pushed_to(tmp_path, monkeypatch):
    from profilecard import github

    cache = tmp_path / "loc_cache.json"
    cache.write_text(
        json.dumps(
            {"alexou8/one": {"a": 500, "d": 20, "pushed_at": "2026-07-01T00:00:00Z"}}
        )
    )
    monkeypatch.setattr(github, "LOC_CACHE", cache)

    contributors = [
        {"author": {"login": "alexou8"}, "weeks": [{"a": 10, "d": 1}, {"a": 5, "d": 0}]},
        {"author": {"login": "someone-else"}, "weeks": [{"a": 999, "d": 999}]},
    ]
    session = FakeSession(get=lambda path: FakeResponse(200, contributors))
    client = _client(session)

    repos = [
        # Unchanged since the cached reading: must not be refetched.
        {"slug": "alexou8/one", "pushed_at": "2026-07-01T00:00:00Z"},
        # Never seen before: must be fetched, and only this user counted.
        {"slug": "alexou8/two", "pushed_at": "2026-07-02T00:00:00Z"},
    ]
    added, deleted, warnings = client.fetch_loc(repos)

    assert session.get_paths == ["/repos/alexou8/two/stats/contributors"]
    assert added == 500 + 15
    assert deleted == 20 + 1
    assert warnings == []


def test_loc_refetches_when_a_repository_moved(tmp_path, monkeypatch):
    from profilecard import github

    cache = tmp_path / "loc_cache.json"
    cache.write_text(
        json.dumps(
            {"alexou8/one": {"a": 500, "d": 20, "pushed_at": "2026-07-01T00:00:00Z"}}
        )
    )
    monkeypatch.setattr(github, "LOC_CACHE", cache)

    contributors = [{"author": {"login": "alexou8"}, "weeks": [{"a": 900, "d": 30}]}]
    session = FakeSession(get=lambda path: FakeResponse(200, contributors))
    client = _client(session)

    added, deleted, _ = client.fetch_loc(
        [{"slug": "alexou8/one", "pushed_at": "2026-07-20T00:00:00Z"}]
    )

    assert session.get_paths == ["/repos/alexou8/one/stats/contributors"]
    assert (added, deleted) == (900, 30)


def test_loc_keeps_repositories_the_token_could_not_list(tmp_path, monkeypatch):
    """A token that sees fewer repos must not shrink the line count."""
    from profilecard import github

    cache = tmp_path / "loc_cache.json"
    cache.write_text(
        json.dumps(
            {
                "alexou8/public": {"a": 100, "d": 5, "pushed_at": "x"},
                "alexou8/private": {"a": 900, "d": 40, "pushed_at": "y"},
            }
        )
    )
    monkeypatch.setattr(github, "LOC_CACHE", cache)

    client = _client(FakeSession())
    # Only the public repository is visible this run.
    added, deleted, _ = client.fetch_loc([{"slug": "alexou8/public", "pushed_at": "x"}])

    assert (added, deleted) == (1000, 45)
    assert "alexou8/private" in json.loads(cache.read_text())


def test_loc_keeps_the_stale_reading_when_a_repository_fails(tmp_path, monkeypatch):
    from profilecard import github

    cache = tmp_path / "loc_cache.json"
    cache.write_text(
        json.dumps({"alexou8/one": {"a": 500, "d": 20, "pushed_at": "old"}})
    )
    monkeypatch.setattr(github, "LOC_CACHE", cache)

    client = _client(FakeSession(get=lambda path: FakeResponse(403)))
    added, deleted, warnings = client.fetch_loc(
        [{"slug": "alexou8/one", "pushed_at": "new"}]
    )

    assert (added, deleted) == (500, 20)
    assert warnings and "1 repository" in warnings[0]


def test_commit_activity_builds_a_gap_free_daily_series():
    """The activity strip must work on a token with no calendar access."""
    commits = [
        {"commit": {"author": {"date": "2026-07-20T10:00:00Z"}}},
        {"commit": {"author": {"date": "2026-07-20T18:00:00Z"}}},
        {"commit": {"author": {"date": "2026-07-23T09:00:00Z"}}},
    ]

    def get(path):
        if path == "/repos/alexou8/one/commits":
            return FakeResponse(200, commits)
        return FakeResponse(200, [])

    client = _client(FakeSession(get=get))
    series, total, warnings = client.fetch_commit_activity(
        [{"slug": "alexou8/one"}, {"slug": "alexou8/two"}]
    )

    assert total == 3
    assert warnings == []
    counts = dict(series)
    assert counts["2026-07-20"] == 2
    assert counts["2026-07-23"] == 1
    # Quiet days are present as zeroes, not missing.
    assert counts["2026-07-21"] == 0
    dates = [day for day, _ in series]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)


def test_commit_activity_skips_empty_repositories():
    client = _client(FakeSession(get=lambda path: FakeResponse(409)))
    series, total, warnings = client.fetch_commit_activity([{"slug": "alexou8/new"}])

    assert series == [] and total is None
    assert warnings == []  # an empty repo is not a failure


def test_commit_activity_reports_unreadable_repositories():
    client = _client(FakeSession(get=lambda path: FakeResponse(403)))
    _, _, warnings = client.fetch_commit_activity([{"slug": "alexou8/one"}])
    assert warnings and "unreadable" in warnings[0]


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"data": {"viewer": {"login": "alexou8"}, "user": {"repositories": {"nodes": [{"stargazerCount": 3}]}}}}, True),
        ({"data": {"viewer": None, "user": {"repositories": {"nodes": [{"stargazerCount": None}]}}}}, False),
    ],
)
def test_probe_reports_star_visibility(payload, expected):
    client = _client(FakeSession(post=lambda: FakeResponse(200, payload)))
    assert client.probe()["can_read_stars"] is expected
