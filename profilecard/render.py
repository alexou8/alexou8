"""Draw a ProfileStats as an SVG terminal card.

The previous generator kept two hand-written SVG files in the repository and
rewrote text nodes inside them, padding every value with a literal run of "."
characters whose length came from a table of hand-tuned column widths.  Any
value a character longer than expected pushed a row out of alignment, and the
widths only held for one specific font.

This renderer draws the card instead.  Values are positioned with
`text-anchor="end"`, leaders are dotted *lines* rather than dot characters,
and the vertical layout is a flow: each section reports the height it used
and sections that have no data simply do not appear.  Nothing depends on
counting characters, so nothing drifts.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from . import config
from .model import ProfileStats, parse_stamp
from .theme import Theme

# The portfolio sets its micro-labels and technical copy in Geist Mono and
# everything editorial in Crimson Pro.  Neither can be *loaded* here: an SVG
# rendered as an <img> through GitHub's image proxy has no network and no
# @font-face, so a web font would silently fall back to whatever the viewer's
# browser picks.  So the card names the families anyway — they resolve for
# anyone who has them installed — and puts a deliberate stack behind each,
# chosen so the register survives the fallback: a grotesque-adjacent mono for
# the data, an old-style serif for the two lines of display type.
MONO = (
    "'Geist Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
    "'Liberation Mono', 'Courier New', monospace"
)

SERIF = (
    "'Crimson Pro', 'Iowan Old Style', 'Palatino Linotype', Palatino, "
    "Georgia, 'Times New Roman', serif"
)

WIDTH = config.CARD_WIDTH
PAD = 32
CHROME_H = 44
CONTENT_W = WIDTH - PAD * 2
COL_GAP = 40
COL_W = (CONTENT_W - COL_GAP) // 2
COL_X = (PAD, PAD + COL_W + COL_GAP)

# One radius for every rectangle, matching the site's `--edge: 2px`.  The
# card used to be a 16px-rounded macOS terminal window; the portfolio has no
# rounded anything.
EDGE = 2

ROW_SIZE = 13.5
ROW_STEP = 25
LABEL_SIZE = 11.5
LABEL_TRACK = 1.7

# Monospace advance width as a fraction of the font size.  Real fonts land
# between 0.55 and 0.61 em; the high end is used so estimates never run short
# and overlap the text they are meant to sit beside.
ADVANCE = 0.615


def measure(text: str, size: float, tracking: float = 0.0) -> float:
    """Estimate the rendered width of monospace *text*."""
    return len(text) * (size * ADVANCE + tracking)


def _fmt(value, dash: str = "—") -> str:
    if value is None:
        return dash
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _compact(value) -> str:
    """1234567 → '1.23M', 65373 → '65.4K'."""
    if value is None:
        return "—"
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{value / 1_000_000:.2f}".rstrip("0").rstrip(".") + "M"
    if magnitude >= 1_000:
        return f"{value / 1_000:.1f}".rstrip("0").rstrip(".") + "K"
    return str(value)


class Canvas:
    """Collects SVG fragments and tracks the vertical cursor."""

    def __init__(self, theme: Theme):
        self.theme = theme
        self.parts: list = []
        self.y = CHROME_H + 30

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    # ── primitives ───────────────────────────────────────────────────────

    def text(
        self,
        x: float,
        y: float,
        content: str,
        *,
        size: float = ROW_SIZE,
        fill: str | None = None,
        weight: str | None = None,
        anchor: str | None = None,
        tracking: float | None = None,
        opacity: float | None = None,
        family: str | None = None,
        raw: bool = False,
    ) -> None:
        attrs = [f'x="{_n(x)}"', f'y="{_n(y)}"', f'font-size="{_n(size)}"']
        if family:
            attrs.append(f'font-family="{family}"')
        attrs.append(f'fill="{fill or self.theme.text}"')
        if weight:
            attrs.append(f'font-weight="{weight}"')
        if anchor:
            attrs.append(f'text-anchor="{anchor}"')
        if tracking:
            attrs.append(f'letter-spacing="{_n(tracking)}"')
        if opacity is not None:
            attrs.append(f'opacity="{_n(opacity)}"')
        body = content if raw else escape(content)
        self.add(f"<text {' '.join(attrs)}>{body}</text>")

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str = "none",
        rx: float = 0,
        stroke: str | None = None,
        opacity: float | None = None,
    ) -> None:
        attrs = [
            f'x="{_n(x)}"',
            f'y="{_n(y)}"',
            f'width="{_n(w)}"',
            f'height="{_n(h)}"',
            f'fill="{fill}"',
        ]
        if rx:
            attrs.append(f'rx="{_n(rx)}"')
        if stroke:
            attrs.append(f'stroke="{stroke}"')
        if opacity is not None:
            attrs.append(f'opacity="{_n(opacity)}"')
        self.add(f"<rect {' '.join(attrs)}/>")

    def line(
        self,
        x1: float,
        y: float,
        x2: float,
        *,
        stroke: str | None = None,
        dash: str | None = None,
        opacity: float = 1.0,
        width: float = 1,
    ) -> None:
        if x2 <= x1:
            return
        attrs = [
            f'x1="{_n(x1)}"',
            f'y1="{_n(y)}"',
            f'x2="{_n(x2)}"',
            f'y2="{_n(y)}"',
            f'stroke="{stroke or self.theme.border}"',
            f'stroke-width="{_n(width)}"',
            f'opacity="{_n(opacity)}"',
        ]
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
            attrs.append('stroke-linecap="round"')
        self.add(f"<line {' '.join(attrs)}/>")

    # ── composites ───────────────────────────────────────────────────────

    def section_label(self, x: float, y: float, label: str, width: float) -> None:
        """A small uppercase caption with a rule running to the column edge."""
        self.text(
            x,
            y,
            label.upper(),
            size=LABEL_SIZE,
            fill=self.theme.accent,
            weight="700",
            tracking=LABEL_TRACK,
        )
        start = x + measure(label, LABEL_SIZE, LABEL_TRACK) + 12
        self.line(start, y - 4, x + width, opacity=0.85)

    def kv_row(
        self,
        x: float,
        y: float,
        width: float,
        key: str,
        value: str,
        *,
        value_markup: str | None = None,
        value_plain: str | None = None,
    ) -> None:
        """A label, a dotted leader, and a right-aligned value."""
        self.text(x, y, key, fill=self.theme.key)
        if value_markup:
            self.text(
                x + width, y, value_markup, anchor="end", fill=self.theme.value, raw=True
            )
        else:
            self.text(x + width, y, value, anchor="end", fill=self.theme.value)

        key_end = x + measure(key, ROW_SIZE) + 9
        value_start = x + width - measure(value_plain or value, ROW_SIZE) - 9
        self.line(
            key_end,
            y - 4,
            value_start,
            stroke=self.theme.muted,
            dash="1 5",
            opacity=0.6,
            width=1.4,
        )

    def chips(self, x: float, y: float, width: float, labels: list, *, size=12) -> float:
        """Lay out pill-shaped chips, wrapping at *width*.  Returns height used."""
        cursor_x, cursor_y = x, y
        height = 24
        gap = 8
        for label in labels:
            chip_w = measure(label, size) + 26
            if cursor_x > x and cursor_x + chip_w > x + width:
                cursor_x = x
                cursor_y += height + gap
            self.rect(
                cursor_x,
                cursor_y,
                chip_w,
                height,
                fill=self.theme.panel,
                rx=EDGE,
                stroke=self.theme.border,
            )
            self.text(
                cursor_x + chip_w / 2,
                cursor_y + height / 2 + 4.2,
                label,
                size=size,
                fill=self.theme.text,
                anchor="middle",
            )
            cursor_x += chip_w + gap
        return cursor_y + height - y


def _swatch(theme: Theme, index: int) -> str:
    """The language bar's colour for the *index*-th largest language."""
    return theme.spectrum[min(index, len(theme.spectrum) - 1)]


def _n(value) -> str:
    """Format a number for an SVG attribute without trailing zeros."""
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return text or "0"
    return str(value)


# ── sections ─────────────────────────────────────────────────────────────


def _draw_chrome(canvas: Canvas, height: float) -> None:
    """The plate the card is drawn on.

    The portfolio does not have windows, cards or panes; it has plates —
    dark steel laid over a live scene, squared off at 2px, edged in a cyan
    hairline, with light landing on the top edge and falling away at the
    bottom.  This draws that, in place of the traffic-light title bar the
    card used to wear, which belonged to a different profile entirely.
    """
    theme = canvas.theme
    canvas.rect(0, 0, WIDTH, height, fill=theme.bg, rx=EDGE)

    # The header strip, and the sheen under the lit edge: a short vertical
    # wash as if the surface is catching the column rather than emitting.
    canvas.add(
        f'<linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{theme.lit}" stop-opacity="0.22"/>'
        f'<stop offset="100%" stop-color="{theme.lit}" stop-opacity="0"/>'
        f"</linearGradient>"
    )
    canvas.rect(0, 0, WIDTH, CHROME_H, fill=theme.chrome, rx=EDGE)
    canvas.rect(0, 0, WIDTH, 96, fill="url(#sheen)")
    canvas.line(0, CHROME_H, WIDTH, stroke=theme.border)

    # The eyebrow, in the label register: what the card is on the left, where
    # the rest of it lives on the right.
    canvas.text(
        PAD,
        CHROME_H / 2 + 4.5,
        "GITHUB · SIGNAL",
        size=11,
        fill=theme.accent,
        weight="500",
        tracking=2.2,
    )
    canvas.text(
        WIDTH - PAD,
        CHROME_H / 2 + 4.5,
        "ALEXOU.CA",
        size=11,
        fill=theme.muted,
        anchor="end",
        tracking=2.2,
    )

    # The bevel: 1px lit along the top edge, 1px of shade at the foot.  Two
    # lines are the whole difference between a flat rectangle and a plate
    # with thickness.
    canvas.line(0, 0.5, WIDTH, stroke=theme.lit, opacity=0.5)
    canvas.line(0, height - 0.5, WIDTH, stroke="#000000", opacity=0.35)

    canvas.rect(
        0.5,
        0.5,
        WIDTH - 1,
        height - 1,
        rx=EDGE,
        stroke=theme.border,
        fill="none",
    )


def _draw_identity(canvas: Canvas) -> None:
    """The name, and the two lines under it.

    The name is set in the display serif rather than the mono the rest of
    the card is drawn in.  That is the whole hierarchy: one editorial voice
    at the top, and everything below it in the technical register.  The
    monogram tile that used to sit beside it was a rounded gradient chip —
    an app icon — and it is a squared plate now, edged rather than filled,
    because the site fills nothing.
    """
    theme = canvas.theme
    top = canvas.y
    tile = 68

    canvas.rect(PAD, top, tile, tile, fill=theme.panel, rx=EDGE, stroke=theme.border)
    canvas.line(PAD, top + 0.5, PAD + tile, stroke=theme.lit, opacity=0.55)
    canvas.text(
        PAD + tile / 2,
        top + tile / 2 + 10,
        config.MONOGRAM,
        size=27,
        fill=theme.accent,
        weight="700",
        anchor="middle",
        tracking=2.5,
        family=SERIF,
    )

    text_x = PAD + tile + 24
    canvas.text(
        text_x,
        top + 30,
        config.NAME,
        size=34,
        weight="700",
        fill=theme.value,
        tracking=1.5,
        family=SERIF,
    )
    canvas.text(text_x, top + 51, config.ROLE, size=13, fill=theme.text, family=SERIF)
    canvas.text(
        text_x,
        top + 70,
        config.TAGLINE.upper(),
        size=10.5,
        fill=theme.accent,
        tracking=2.0,
    )

    canvas.y = top + tile + 36


def _draw_columns(canvas: Canvas, stats: ProfileStats) -> None:
    theme = canvas.theme
    top = canvas.y
    dev_age = config.dev_age(parse_stamp(stats.generated_at))

    canvas.section_label(COL_X[0], top, "whoami", COL_W)
    canvas.section_label(COL_X[1], top, "github", COL_W)

    y = top + 26
    for index, (key, value) in enumerate(config.WHOAMI):
        canvas.kv_row(
            COL_X[0],
            y + index * ROW_STEP,
            COL_W,
            key,
            value.format(dev_age=dev_age),
        )

    rows = [
        ("Repos", _fmt(stats.repos)),
        ("Stars", _fmt(stats.stars)),
        ("Commits", _fmt(stats.commits)),
        ("Followers", _fmt(stats.followers)),
        ("Contributed", _fmt(stats.contributed)),
    ]
    for index, (key, value) in enumerate(rows):
        canvas.kv_row(COL_X[1], y + index * ROW_STEP, COL_W, key, value)

    # Lines of code carries a coloured +/- breakdown, so the value is built
    # from tspans and measured from its plain-text equivalent.
    loc_y = y + len(rows) * ROW_STEP
    net = _fmt(stats.loc_net)
    added = _compact(stats.loc_added)
    deleted = _compact(stats.loc_deleted)
    plain = f"{net}  +{added} / -{deleted}"
    markup = (
        f'<tspan fill="{theme.value}">{escape(net)}</tspan>'
        f'<tspan fill="{theme.muted}">  </tspan>'
        f'<tspan fill="{theme.add}">+{escape(added)}</tspan>'
        f'<tspan fill="{theme.muted}"> / </tspan>'
        f'<tspan fill="{theme.delete}">-{escape(deleted)}</tspan>'
    )
    canvas.kv_row(
        COL_X[1],
        loc_y,
        COL_W,
        "Lines of code",
        plain,
        value_markup=markup,
        value_plain=plain,
    )

    used = max(len(config.WHOAMI), len(rows) + 1)
    canvas.y = y + used * ROW_STEP + 16


def _draw_stack(canvas: Canvas, stats: ProfileStats) -> None:
    theme = canvas.theme
    top = canvas.y
    measured = bool(stats.languages)
    label = "stack · measured across repositories" if measured else "stack"
    canvas.section_label(PAD, top, label, CONTENT_W)
    y = top + 20

    if measured:
        total = sum(size for _, size in stats.languages) or 1
        bar_h = 13
        canvas.add(
            f'<clipPath id="lang-clip">'
            f'<rect x="{_n(PAD)}" y="{_n(y)}" width="{_n(CONTENT_W)}" '
            f'height="{_n(bar_h)}" rx="{_n(EDGE)}"/></clipPath>'
        )
        canvas.add('<g clip-path="url(#lang-clip)">')
        cursor = float(PAD)
        for index, (name, size) in enumerate(stats.languages):
            # Give the final segment the remaining pixels so rounding never
            # leaves a sliver of background showing at the right edge.
            is_last = index == len(stats.languages) - 1
            seg_w = (PAD + CONTENT_W) - cursor if is_last else CONTENT_W * size / total
            canvas.rect(cursor, y, seg_w, bar_h, fill=_swatch(theme, index))
            cursor += seg_w
        canvas.add("</g>")

        y += bar_h + 24
        # A fixed four-column grid keeps the legend aligned regardless of
        # which monospace font the viewer's browser resolves.
        cell = CONTENT_W / 4
        for index, (name, size) in enumerate(stats.languages):
            col = index % 4
            row = index // 4
            cx = PAD + col * cell
            cy = y + row * 22
            canvas.add(
                f'<circle cx="{_n(cx + 5)}" cy="{_n(cy - 4)}" r="5" '
                f'fill="{_swatch(theme, index)}"/>'
            )
            percent = size / total * 100
            canvas.text(cx + 17, cy, name, size=12.5, fill=theme.text)
            canvas.text(
                cx + 17 + measure(name, 12.5) + 8,
                cy,
                f"{percent:.1f}%",
                size=12.5,
                fill=theme.muted,
            )
        rows = (len(stats.languages) + 3) // 4
        y += rows * 22 - 8
    else:
        y += canvas.chips(PAD, y - 14, CONTENT_W, config.STACK_FALLBACK) - 6

    y += canvas.chips(PAD, y, CONTENT_W, config.TOOLBELT) + 8
    canvas.y = y + 22


def _draw_activity(canvas: Canvas, stats: ProfileStats) -> None:
    if not stats.weeks:
        return
    theme = canvas.theme
    top = canvas.y
    weeks = stats.weeks
    counting = "commits" if stats.activity_source == "commits" else "activity"
    canvas.section_label(PAD, top, f"{counting} · last {len(weeks)} weeks", CONTENT_W)

    y = top + 16
    height = 46
    gap = 4
    bar_w = (CONTENT_W - gap * (len(weeks) - 1)) / len(weeks)
    peak = max(weeks) or 1
    baseline = y + height

    for index, count in enumerate(weeks):
        x = PAD + index * (bar_w + gap)
        if count <= 0:
            canvas.rect(x, baseline - 3, bar_w, 3, fill=theme.border, rx=EDGE, opacity=0.8)
            continue
        level = min(3, int(count / peak * 4))
        bar_h = max(5.0, height * count / peak)
        canvas.rect(
            x, baseline - bar_h, bar_w, bar_h, fill=theme.ramp[level], rx=EDGE
        )

    y = baseline + 22
    caption = []
    if stats.contributions_total is not None:
        window = (
            f"commits across {len(weeks)} weeks"
            if stats.activity_source == "commits"
            else "contributions in the last year"
        )
        caption.append(f"{stats.contributions_total:,} {window}")
    if stats.current_streak is not None:
        streak = f"{stats.current_streak} day streak"
        if stats.longest_streak:
            streak += f" (best {stats.longest_streak})"
        caption.append(streak)
    if caption:
        canvas.text(PAD, y, "  ·  ".join(caption), size=12.5, fill=theme.muted)
        y += 8

    canvas.y = y + 22


def _draw_contact(canvas: Canvas) -> None:
    theme = canvas.theme
    top = canvas.y
    canvas.section_label(PAD, top, "contact", CONTENT_W)
    y = top + 26
    cell = CONTENT_W / len(config.CONTACT)
    for index, (label, value) in enumerate(config.CONTACT):
        x = PAD + index * cell
        canvas.text(x, y, label.upper(), size=10.5, fill=theme.muted, tracking=2.0)
        canvas.text(x, y + 21, value, size=13.5, fill=theme.key)
    canvas.y = y + 48


def _draw_footer(canvas: Canvas, stats: ProfileStats) -> None:
    theme = canvas.theme
    y = canvas.y
    canvas.line(PAD, y - 14, WIDTH - PAD, stroke=theme.border, opacity=0.8)

    left = f"updated {stats.generated_at}" if stats.generated_at else "updated on push"
    canvas.text(PAD, y + 8, left, size=11.5, fill=theme.muted)

    right = "refreshed daily by GitHub Actions"
    if stats.stale:
        right = f"{len(stats.stale)} figure(s) served from cache · {right}"
    canvas.text(WIDTH - PAD, y + 8, right, size=11.5, fill=theme.muted, anchor="end")
    canvas.y = y + 26


# ── entry point ──────────────────────────────────────────────────────────


def render(stats: ProfileStats, theme: Theme) -> str:
    """Render the whole card and return the SVG document as a string."""
    canvas = Canvas(theme)

    _draw_identity(canvas)
    _draw_columns(canvas, stats)
    _draw_stack(canvas, stats)
    _draw_activity(canvas, stats)
    _draw_contact(canvas)
    _draw_footer(canvas, stats)

    height = canvas.y

    chrome = Canvas(theme)
    _draw_chrome(chrome, height)

    body = "\n".join(chrome.parts + canvas.parts)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" '
        f'height="{_n(height)}" viewBox="0 0 {WIDTH} {_n(height)}" '
        f'font-family="{MONO}" role="img" '
        f'aria-label="{escape(config.NAME)} — GitHub profile summary">\n'
        f"{body}\n"
        "</svg>\n"
    )
