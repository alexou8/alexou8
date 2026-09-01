"""Colour palettes for the generated cards.

Both themes carry the same key names so the renderer never branches on which
theme it is drawing.

The values are the portfolio's own tokens, lifted from `app/globals.css` in
alexou8/alex-ou-portfolio: the void the scene sits in (#01040c), the plate the
copy sits on (#06132c at 93%, flattened to an opaque hex here because an SVG
served through GitHub's camo proxy has nothing behind it to be translucent
over), the cyan hairline the plates are edged in, and the aurora green that
is the site's only accent.

The site has no light mode — it is a night scene and that is the point — so
the light theme is not a second palette but the same *relationships* on
paper: the same cyan in the label register, the same green as the single
accent, both darkened until they hold contrast on white.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str  # page / card background
    chrome: str  # header strip
    panel: str  # inset panels (chips, sparkline trough)
    border: str
    lit: str  # the plate's top bevel — light lands here
    text: str  # primary body text
    muted: str  # captions, leaders, footers
    key: str  # row labels
    value: str  # row values
    accent: str  # aurora green
    accent_soft: str  # aurora green, low emphasis
    add: str  # LOC additions
    delete: str  # LOC deletions
    # Four-step ramp for the contribution sparkline, low → high.  It runs
    # deep blue → cyan → aurora, which is the column's own gradient.
    ramp: tuple
    # Segment colours for the language bar, most-written first.
    #
    # These used to be GitHub's own language swatches, which is the correct
    # default and the wrong one here: eight unrelated hues — Python blue,
    # HTML orange, JavaScript yellow — are the single loudest thing that can
    # be put on a page whose whole identity is one cyan and one green.  The
    # bar reads as proportion, and proportion does not need eight hues; it
    # needs an ordered ramp, which is also what makes the largest language
    # legible as the largest.
    spectrum: tuple

    @property
    def is_dark(self) -> bool:
        return self.name == "dark"


DARK = Theme(
    name="dark",
    bg="#020813",
    chrome="#06132c",
    panel="#0a1c3d",
    border="#1c3a63",
    lit="#2f5c8a",
    text="#c5dcf2",
    muted="#7c9ac0",
    key="#6fe6ff",
    value="#f4fcff",
    accent="#7cf3c4",
    accent_soft="#2c6f5f",
    add="#7cf3c4",
    delete="#ff8fa3",
    ramp=("#12294a", "#1d5675", "#3fb4b8", "#7cf3c4"),
    spectrum=(
        "#7cf3c4",
        "#6fe6ff",
        "#5aa8e0",
        "#4a7fc0",
        "#3d5f9c",
        "#31477a",
        "#27365c",
        "#1e2a45",
    ),
)

LIGHT = Theme(
    name="light",
    bg="#f7fafd",
    chrome="#ecf2f9",
    panel="#e6eef7",
    border="#c3d6e8",
    lit="#ffffff",
    text="#12345c",
    muted="#5d7896",
    key="#0e6f8c",
    value="#05102a",
    accent="#0e7f5f",
    accent_soft="#9fdcc6",
    add="#0e7f5f",
    delete="#b3243c",
    ramp=("#d6e6f2", "#8fc3d8", "#3f9f96", "#0e7f5f"),
    spectrum=(
        "#0e7f5f",
        "#1a7fa0",
        "#3f92c0",
        "#6aa8d0",
        "#8fbcdc",
        "#aecce6",
        "#c6dcee",
        "#dbe8f4",
    ),
)

THEMES = {"dark": DARK, "light": LIGHT}
