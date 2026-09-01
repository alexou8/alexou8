"""Human-editable content for the profile card.

Everything in this module is static copy: the numbers on the card come from
the GitHub API, but the identity, links and declared stack live here.  Edit
this file to change what the card says; no other module needs to know.
"""

import datetime

# GitHub login. Overridden at runtime by the USER_NAME environment variable.
LOGIN = "alexou8"

# ── Identity ──────────────────────────────────────────────────────────────
NAME = "Alex Ou"
ROLE = "Full-stack software engineer · backend services, data pipelines, applied ML"

# When the "Dev age" counter starts: the first term of the CS degree.
DEV_SINCE = datetime.date(2021, 9, 1)

# ── Profile rows ──────────────────────────────────────────────────────────
# (label, value).  The literal "{dev_age}" is substituted at render time.
#
# Deliberately short.  The rows that used to be here — editor, languages
# spoken — are the ones every profile card carries and none of them tell a
# reader anything about the work.
WHOAMI = [
    ("School", "Wilfrid Laurier University"),
    ("Program", "Computer Science (BCS)"),
    ("Based in", "Toronto, ON"),
    ("Writing code", "{dev_age}"),
]

# ── Declared stack ────────────────────────────────────────────────────────
# Rendered as chips whenever the API could not supply measured language
# bytes, so the section never collapses into an empty strip.
STACK_FALLBACK = [
    "Python",
    "TypeScript",
    "JavaScript",
    "Java",
    "C",
    "SQL",
]

# Frameworks and tools, always shown as a second chip row.
TOOLBELT = ["FastAPI", "React", "PostgreSQL", "TensorFlow", "Docker"]

# Languages to leave out of the measured language bar.  Generated or
# vendored files otherwise drown out the languages actually written.
LANGUAGE_DENYLIST = {
    "Jupyter Notebook",
    "Roff",
    "TeX",
    "Makefile",
    "Batchfile",
    "Dockerfile",
}

# Number of language segments to draw before collapsing into "Other".
LANGUAGE_SLOTS = 6

# ── Contact ───────────────────────────────────────────────────────────────
# The card is an image, so none of this is clickable; the README carries the
# real links under it.  These are here because a reader who screenshots the
# card, or meets it outside GitHub, still needs to know where to go.
CONTACT = [
    ("Portfolio", "alexou.ca"),
    ("GitHub", "github.com/alexou8"),
    ("LinkedIn", "linkedin.com/in/alexou8"),
]

# ── Output ────────────────────────────────────────────────────────────────
OUTPUTS = {
    "dark": "dark_mode.svg",
    "light": "light_mode.svg",
}

CARD_WIDTH = 920


def dev_age(as_of: datetime.date | None = None) -> str:
    """Return the dev-age string, e.g. '4 years, 10 months, 21 days'.

    Measured against *as_of* — the moment the stats were collected — rather
    than "now", so rendering stays a pure function of the stats and the
    committed SVGs can be checked for drift on any later day.
    """
    from dateutil import relativedelta

    today = as_of or datetime.date.today()
    diff = relativedelta.relativedelta(today, DEV_SINCE)
    parts = [
        f"{diff.years} year{'s' if diff.years != 1 else ''}",
        f"{diff.months} month{'s' if diff.months != 1 else ''}",
        f"{diff.days} day{'s' if diff.days != 1 else ''}",
    ]
    # A cake only on the exact anniversary.
    suffix = " 🎂" if diff.months == 0 and diff.days == 0 else ""
    return ", ".join(parts) + suffix
