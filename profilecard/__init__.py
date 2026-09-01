"""Generator for the alexou8 GitHub profile README cards.

The package is split so that fetching and drawing never depend on each other:

  config      – everything a human would want to edit (identity, links, stack)
  theme       – the dark/light colour palettes
  emblem      – the Wings of Freedom, traced from the site's own art
  model       – the ProfileStats dataclass plus cache load/merge/save
  github      – API client that degrades instead of raising
  render      – turns a ProfileStats into an SVG string

Rendering is pure: given the same ProfileStats it always produces the same
bytes, which is what makes `--check` and the unit tests possible.
"""

__all__ = ["config", "theme", "emblem", "model", "github", "render"]
