# How the profile card is generated

`README.md` displays two SVGs — `dark_mode.svg` and `light_mode.svg` — that a
scheduled workflow regenerates every day at 04:00 UTC. Both files are
generated output: edit `profilecard/config.py` and re-run the generator
instead of editing the SVGs by hand.

```
generate_svg.py        CLI entry point
profilecard/
  config.py            identity, links, declared stack   ← edit this
  theme.py             the dark and light palettes
  langcolors.py        language swatch colours
  model.py             ProfileStats + the last-known-good cache
  github.py            API access that degrades instead of raising
  collect.py           API responses → ProfileStats
  render.py            ProfileStats → SVG
cache/
  stats.json           last known good numbers
  loc_cache.json       per-repository line counts
```

## Running it locally

```bash
pip install -r requirements.txt
export ACCESS_TOKEN=ghp_...        # a personal access token
python generate_svg.py             # fetch and regenerate

python generate_svg.py --offline   # re-render from cache, no network
python generate_svg.py --check     # verify the committed SVGs are current
python generate_svg.py --strict    # exit non-zero if anything degraded
```

`--offline` is the fast loop when changing layout or copy: it renders from
`cache/stats.json` without touching the API.

## The ACCESS_TOKEN secret

Set a **fine-grained personal access token** as the repository secret
`ACCESS_TOKEN`, with read access to:

- *Repository permissions* → **Metadata: read** (stars, forks, pushes)
- *Repository permissions* → **Contents: read** (line-count statistics)
- *Account permissions* → **Followers: read**

Without it the workflow falls back to the built-in `GITHUB_TOKEN`. That token
is scoped to this repository alone, so GitHub answers with

```
FORBIDDEN … Resource not accessible by integration
```

for star counts, language bytes and the commit search on every *other*
repository. When that happens the run does **not** fail: the affected figures
come from `cache/stats.json`, the card still regenerates, and the run is
annotated with a warning naming the cause. The card itself also says so, in
its footer — `N figure(s) served from cache`.

Most of the card survives that fallback on its own, because the public REST
endpoints stay readable:

| Section | With a PAT | With only `GITHUB_TOKEN` |
| --- | --- | --- |
| Stars, forks, repos | GraphQL | REST `/users/:login/repos` |
| Language bar | GraphQL language bytes | REST `/repos/:slug/languages` |
| Activity strip | contribution calendar, labelled `activity` | commit history, labelled `commits` |
| Commits | all-time commit search | default branches of listed repos |
| Private repositories | included | not visible |

The activity strip changes meaning between those two rows, so it changes its
label with it: the calendar counts pull requests, issues and work in other
people's repositories, while the commit fallback counts only commits on the
default branches of the repositories listed. The card never presents one as
the other.

That fallback is the safety net, not the plan. Fine-grained tokens expire, so
when the card stops moving, check the workflow annotations first: an expired
`ACCESS_TOKEN` is the most likely reason.

## Changing what the card says

Everything human-written lives in `profilecard/config.py`: name, monogram,
tagline, the `whoami` rows, the declared stack chips, the contact list, and
`DEV_SINCE` for the dev-age counter. The layout is a vertical flow — sections
report the height they use, so adding or removing a row reflows the card and
resizes the SVG automatically.

Sections with no data disappear rather than rendering empty: the activity
sparkline only appears once the contribution calendar is readable, and the
measured language bar falls back to `STACK_FALLBACK` chips when language bytes
are unavailable.

After changing the config, regenerate and commit the SVGs — CI runs
`--check` and fails if they drift from `cache/stats.json`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The suite covers the cache-merge rules, language aggregation, streak
arithmetic, SVG well-formedness, and the partial-`FORBIDDEN` GraphQL response
that broke the daily refresh in July 2026.
