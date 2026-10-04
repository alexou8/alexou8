"""The colour palette for the generated card.

The values are the portfolio's Ghoul world, lifted from the
`html[data-theme='ghoul']` block of `app/globals.css` in
alexou8/alex-ou-portfolio: a white spider-lily field, paper and bone in place
of steel, ink in place of pale cyan, and one accent, which is blood.

There is one theme, not a dark and a light one.  The Ghoul world is light
only on the site, and the banner above the card in the README is a white
field, so the card is drawn on the same paper in either GitHub colour scheme
and the two read as one plate.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str  # the plate
    panel: str  # inset panels (chips)
    border: str
    lit: str  # the plate's top bevel — light lands here
    text: str  # primary body text
    muted: str  # captions, leaders, footers
    key: str  # row labels
    value: str  # row values
    accent: str  # blood
    accent_deep: str  # oxblood
    add: str  # LOC additions
    delete: str  # LOC deletions
    # Four-step ramp for the activity strip, low → high.  The site has one
    # accent and the strip takes it: the field goes red as it is walked
    # through, and so does a busy week.
    ramp: tuple
    # The swatch for a week with nothing in it.
    ramp_empty: str


# Contrast on the plate (#f8f6f2): value 18.2, text 15.8, muted 7.1,
# accent 7.3 — every ratio clears AA for body text.
GHOUL = Theme(
    name="ghoul",
    bg="#f8f6f2",
    panel="#f2efea",
    border="#cfcbc6",
    lit="#ffffff",
    text="#1d1b20",
    muted="#55525a",
    key="#5a0a10",
    value="#0c0b0e",
    accent="#a3121c",
    accent_deep="#5a0a10",
    add="#1f6b3a",
    delete="#a3121c",
    ramp=("#f1c9cc", "#d8737b", "#c23a44", "#a3121c"),
    ramp_empty="#e4e0da",
)

THEMES = {"ghoul": GHOUL}
