"""open-manim-slides: a scaffolded, checked workflow for Manim Slides decks.

Every public name below is resolved lazily (PEP 562). Importing this
package therefore does *not* import `manim`, which matters for exactly one
consumer: `open_manim_slides.cli`. Its `doctor` subcommand exists to report
that manim is missing or unbuildable -- the most likely state of a machine
that has just tried its first install, since `manimpango` compiles against
system cairo and pango headers -- and a diagnostic that cannot run without
the thing it diagnoses is no diagnostic at all. Eager re-exports here made
`open-manim-slides doctor` fail with a `ModuleNotFoundError` traceback
instead of a report.
"""

from typing import TYPE_CHECKING

#: public name -> submodule it lives in
_EXPORTS = {
    "Slide": "base",
    "convert_to_html": "convert",
    "assert_no_overlap": "layout",
    "assert_reasonably_centered": "layout",
    "assert_within_safe_frame": "layout",
    "COLOR_ACCENT": "theme",
    "COLOR_ACCENT_2": "theme",
    "COLOR_BACKGROUND": "theme",
    "COLOR_MUTED": "theme",
    "COLOR_TEXT": "theme",
    "FONT_SIZE_BODY": "theme",
    "FONT_SIZE_CAPTION": "theme",
    "FONT_SIZE_HEADING": "theme",
    "FONT_SIZE_TITLE": "theme",
    "SPACING_LG": "theme",
    "SPACING_MD": "theme",
    "SPACING_SM": "theme",
    "SPACING_XL": "theme",
    "SPACING_XS": "theme",
    "diagram_with_caption": "theme",
    "heading": "theme",
    "title_slide": "theme",
    "two_column": "theme",
}

__all__ = sorted(_EXPORTS)

if TYPE_CHECKING:  # keep type checkers and editors seeing the real symbols
    from open_manim_slides.base import Slide
    from open_manim_slides.convert import convert_to_html
    from open_manim_slides.layout import (
        assert_no_overlap,
        assert_reasonably_centered,
        assert_within_safe_frame,
    )
    from open_manim_slides.theme import (
        COLOR_ACCENT,
        COLOR_ACCENT_2,
        COLOR_BACKGROUND,
        COLOR_MUTED,
        COLOR_TEXT,
        FONT_SIZE_BODY,
        FONT_SIZE_CAPTION,
        FONT_SIZE_HEADING,
        FONT_SIZE_TITLE,
        SPACING_LG,
        SPACING_MD,
        SPACING_SM,
        SPACING_XL,
        SPACING_XS,
        diagram_with_caption,
        heading,
        title_slide,
        two_column,
    )


def __getattr__(name: str) -> object:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(f"{__name__}.{module_name}"), name)
    globals()[name] = value  # resolve once, then it is a plain global
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))
