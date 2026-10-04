"""The red spider lily, as SVG markup.

The site's Ghoul world wears this mark where the Paths wear the Wings of
Freedom — see `app/components/shared/SpiderLily.tsx` and
`public/icon-ghoul.svg` in alexou8/alex-ou-portfolio — and this is the same
drawing, so the card and the site carry one insignia rather than two.

Six recurved petals in the accent, six stamens in the deeper accent, each
tipped with an anther, and a dark heart.  Drawn on a 32-unit square.
"""

SIZE = 32

_PETAL = "M16 15.2 C15.1 10.4 17.4 5.6 23.4 2.6 C20 6.2 18.6 10.2 17.1 15.2 Z"
_STAMEN = "M16 15.4 C15.6 10.2 12.6 6 7.8 3.4"


def markup(petal: str, stamen: str) -> str:
    """The lily in 32-unit glyph space, filled with the two given colours."""
    petals = "".join(
        f'<path transform="rotate({angle} 16 16)" d="{_PETAL}"/>'
        for angle in range(0, 360, 60)
    )
    stamens = "".join(
        f'<g transform="rotate({angle} 16 16)"><path d="{_STAMEN}"/>'
        f'<circle fill="{stamen}" stroke="none" cx="7.4" cy="3.2" r="1.3"/></g>'
        for angle in range(30, 360, 60)
    )
    return (
        f'<g fill="{petal}" stroke="{petal}" stroke-width="0.6" '
        f'stroke-linejoin="round">{petals}</g>'
        f'<g fill="none" stroke="{stamen}" stroke-width="0.9" '
        f'stroke-linecap="round">{stamens}</g>'
        f'<circle cx="16" cy="16" r="2" fill="{stamen}"/>'
    )
