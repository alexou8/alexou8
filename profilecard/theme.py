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
    # Four-step ramp for the contribution sparkline, low → high.
    #
    # GitHub's own contribution greens, and the language bar keeps GitHub's
    # linguist swatches, which is the one place the card does not take the
    # site's palette.  Both are read rather than looked at: a visitor already
    # knows what Python blue and a dark-green week mean, and recolouring them
    # to match the plate would cost that recognition for a hue.  The rest of
    # the card carries the brand; these two carry their meaning.
    ramp: tuple
    # The swatch for a week with nothing in it.  It is GitHub's own empty
    # cell rather than the plate's border, which read as a blue gap in a
    # green strip.
    ramp_empty: str

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
    ramp=("#0e4429", "#006d32", "#26a641", "#39d353"),
    ramp_empty="#151b23",
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
    ramp=("#9be9a8", "#40c463", "#30a14e", "#216e39"),
    ramp_empty="#ebedf0",
)

THEMES = {"dark": DARK, "light": LIGHT}
