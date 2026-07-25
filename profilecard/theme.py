"""Colour palettes for the generated cards.

Both themes carry the same key names so the renderer never branches on which
theme it is drawing.  The accent green is taken from the portfolio banner in
assets/ so the profile and the site read as one brand.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str  # page / card background
    chrome: str  # title bar
    panel: str  # inset panels (chips, sparkline trough)
    border: str
    text: str  # primary body text
    muted: str  # captions, leaders, footers
    key: str  # row labels
    value: str  # row values
    accent: str  # brand green
    accent_soft: str  # brand green, low emphasis
    add: str  # LOC additions
    delete: str  # LOC deletions
    # Four-step ramp for the contribution sparkline, low → high.
    ramp: tuple

    @property
    def is_dark(self) -> bool:
        return self.name == "dark"


DARK = Theme(
    name="dark",
    bg="#0d1117",
    chrome="#161b22",
    panel="#161b22",
    border="#30363d",
    text="#c9d1d9",
    muted="#6e7681",
    key="#ffa657",
    value="#79c0ff",
    accent="#2ea884",
    accent_soft="#1c6b52",
    add="#3fb950",
    delete="#f85149",
    ramp=("#1b3a2c", "#1f6f4a", "#2ea884", "#56d4a4"),
)

LIGHT = Theme(
    name="light",
    bg="#ffffff",
    chrome="#f6f8fa",
    panel="#f6f8fa",
    border="#d0d7de",
    text="#1f2328",
    muted="#7d8590",
    key="#953800",
    value="#0a3069",
    accent="#169b66",
    accent_soft="#a9dcc6",
    add="#1a7f37",
    delete="#cf222e",
    ramp=("#d8f0e4", "#8fd6b8", "#3caa82", "#169b66"),
)

THEMES = {"dark": DARK, "light": LIGHT}
