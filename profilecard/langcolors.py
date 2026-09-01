"""Language swatch colours, matching GitHub's linguist palette.

Only the languages likely to show up on this profile are listed; anything
else gets a stable colour derived from its name so the bar never renders a
grey blob for an unrecognised language.
"""

import hashlib

COLORS = {
    "Python": "#3572A5",
    "TypeScript": "#3178c6",
    "JavaScript": "#f1e05a",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "SCSS": "#c6538c",
    "Shell": "#89e051",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Dart": "#00B4AB",
    "R": "#198CE7",
    "SQL": "#e38c00",
    "PLpgSQL": "#336790",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Jupyter Notebook": "#DA5B0B",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "Assembly": "#6E4C13",
    "MATLAB": "#e16737",
}

# Colour used for the aggregated "Other" segment.
OTHER = "#8b949e"


def color_for(language: str) -> str:
    """Return a hex colour for *language*, deriving one if it is unknown."""
    if language in COLORS:
        return COLORS[language]
    if language == "Other":
        return OTHER
    # Deterministic pastel so repeated runs produce identical SVGs.
    digest = hashlib.sha1(language.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    return _hsl_to_hex(hue, 0.55, 0.55)


def _hsl_to_hex(h: float, s: float, ll: float) -> str:
    def channel(n: float) -> int:
        k = (n + h * 12) % 12
        a = s * min(ll, 1 - ll)
        value = ll - a * max(-1, min(k - 3, 9 - k, 1))
        return round(value * 255)

    return "#{:02x}{:02x}{:02x}".format(channel(0), channel(8), channel(4))
