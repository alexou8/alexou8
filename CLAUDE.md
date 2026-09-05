# CLAUDE.md

Instructions for Claude Code working in `alexou8/alexou8`.

## What this repo is

Two things live here:

1. **The GitHub profile card generator** — a Python package that renders
   `dark_mode.svg` / `light_mode.svg`, which `README.md` displays. See
   @docs/generator.md for the module map and local run instructions.
2. **The portfolio redesign workspace** — the ground-up rebuild of
   <https://alexou.ca>, driven by the skills in `.claude/skills/`.

Ask which of the two a request targets when it is ambiguous. A change to the
card is not a change to the site.

## Commands

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                          # test suite (CI runs this)
python generate_svg.py             # fetch from GitHub and re-render the cards
python generate_svg.py --offline   # re-render from cache/stats.json, no network
python generate_svg.py --check     # verify the committed SVGs match the cache
```

Run `pytest -q` and `python generate_svg.py --check` before committing any
change under `profilecard/` or `generate_svg.py` — CI runs both and `--check`
fails whenever config changed without a regenerate.

## Generator conventions

- `dark_mode.svg`, `light_mode.svg`, and `cache/*.json` are **generated
  output**. Never hand-edit them; edit `profilecard/config.py` and re-run.
- Rendering is deterministic: the same `cache/stats.json` must reproduce
  byte-identical SVGs. Keep it that way — no timestamps, no dict ordering
  that depends on the API response, no randomness.
- A partial GitHub API failure is not an error. Missing metrics fall back to
  the cached value and are reported as workflow annotations. Only a token
  that cannot identify the user aborts a run.
- The refresh workflow commits with `[skip ci]`. Do not add commits on top of
  the bot's card commits by hand.
- Python 3.12, `from __future__ import annotations` at the top of modules,
  type hints on public functions.

## Portfolio redesign

Skills are installed project-level in `.claude/skills/` and tracked in
`skills-lock.json`. Use them rather than working from memory:

| Area | Skill |
| --- | --- |
| Visual design, layout, taste | `web-design-guidelines`, `designing-beautiful-websites` |
| Responsive behavior | `responsive-design` |
| Motion and page transitions | `vercel-react-view-transitions` |
| React/Next.js architecture | `vercel-react-best-practices`, `vercel-composition-patterns`, `nextjs-app-router-patterns` |
| Performance | `performance`, `core-web-vitals` |
| Accessibility | `accessibility` |
| Search visibility | `seo` |
| Pre-ship review | `web-quality-audit`, `best-practices` |
| Deploy | `deploy-to-vercel` |
| Finding more skills | `find-skills` |

Rules for the rebuild:

- Design first, then build. Read `web-design-guidelines` before writing the
  first component — do not ship a default-looking template.
- Every page must pass `accessibility` (WCAG 2.2 AA: keyboard reachable,
  visible focus, real landmarks, alt text) and respect
  `prefers-reduced-motion`.
- Site content mirrors `profilecard/config.py` — name, links, and declared
  stack come from there. Update that file rather than duplicating the values.
- Run `web-quality-audit` before any deploy.

## Pull requests

- Branch off `main`; never commit to `main` directly.
- Conventional commit subjects (`feat:`, `fix:`, `chore:`, `docs:`).
- Keep generator changes and site changes in separate PRs.
