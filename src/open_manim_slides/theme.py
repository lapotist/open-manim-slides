"""Design-system slice: typography scale, spacing scale, color tokens,
and reusable slide templates.

Same framing as layout.py: a handful of named font sizes and spacing
values, a small semantic color palette built on manim's own validated
color constants (rather than inventing untested hex values), and reusable
templates (`title_slide`, `two_column`, `diagram_with_caption`) factored
out of layout patterns decks otherwise duplicate ad hoc. Deeper palette
work (e.g. contrast-checked custom hues) is a future slice, not this pass.
"""

from __future__ import annotations

from typing import Any

from manim import BLACK, BLUE_D, GRAY_B, WHITE, YELLOW_D

# Typography scale ---------------------------------------------------------
# Named font sizes (manim `Text`/`Tex` `font_size` units). Prefer these
# over ad hoc numbers so decks stay visually consistent with each other --
# the two dev-test decks each picked their own sizes (28, 36, 24) for
# what's structurally the same three roles this scale now names.
FONT_SIZE_TITLE: int = 48
FONT_SIZE_HEADING: int = 36
FONT_SIZE_BODY: int = 28
FONT_SIZE_CAPTION: int = 24

# Spacing scale ---------------------------------------------------------
# Named `buff=` values (Manim units) for `next_to`/`arrange`/`to_edge`.
# Anchored to manim's own defaults rather than invented numbers, so the
# scale doesn't fight the library's built-in spacing: SPACING_SM matches
# `DEFAULT_MOBJECT_TO_MOBJECT_BUFFER` (manim's own `next_to`/`arrange`
# default), and SPACING_MD matches both `DEFAULT_MOBJECT_TO_EDGE_BUFFER`
# and `layout.DEFAULT_MARGIN`.
SPACING_XS: float = 0.15
SPACING_SM: float = 0.25
SPACING_MD: float = 0.5
SPACING_LG: float = 1.0
SPACING_XL: float = 1.5

# Color tokens ---------------------------------------------------------
# Semantic names over manim's own color constants (not new hex values --
# nothing here has been contrast-checked, and manim's named colors are
# already tuned to render correctly), so a deck's intent ("this is the
# accent color") survives a future palette change without touching every
# call site.
COLOR_TEXT = WHITE
COLOR_MUTED = GRAY_B
COLOR_ACCENT = BLUE_D
# Second accent, for segments that compare two things (two squares, two
# sides of an equation): each gets its own color and keeps it. YELLOW_D
# reads cleanly against both BLUE_D and WHITE on the black background.
COLOR_ACCENT_2 = YELLOW_D
COLOR_BACKGROUND = BLACK


def title_slide(slide: Any, text: str, id: str = "title", **kwargs: Any) -> Any:  # noqa: A002 - matches track()'s `id=` kwarg
    """Create, size, track, and safe-frame-check a deck/segment title.

    Factors out the pattern duplicated identically across both dev-test
    decks: `Text(...)` at title size, `slide.track(..., id=...)`, then
    `assert_within_safe_frame(...)`. Callers still animate it in
    themselves (`slide.play(Write(title))`) and handle any deck-specific
    state assignment (e.g. `self.title = title`) -- this only removes the
    boilerplate that was identical everywhere, not the parts that vary.
    """
    from manim import Text

    from open_manim_slides.layout import assert_within_safe_frame

    kwargs.setdefault("font_size", FONT_SIZE_TITLE)
    title = slide.track(Text(text, **kwargs), id=id)
    assert_within_safe_frame(title)
    return title


def heading(slide: Any, text: str, id: str = "heading", **kwargs: Any) -> Any:  # noqa: A002 - matches track()'s `id=` kwarg
    """Create, place, track, and safe-frame-check a per-segment heading.

    The pattern both dev decks actually needed but had no template for:
    they reached for `title_slide(...)` (48pt) and then `.to_edge(UP)`
    with the default 0.5 buff -- which is exactly `layout.DEFAULT_MARGIN`,
    so every segment opened with an oversized heading sitting precisely on
    the safe-frame boundary with zero slack. This is the right-sized
    version: heading scale (36pt), pinned near the top edge with
    `SPACING_XS` of slack past the safe margin (`to_edge`'s buff is
    measured from the frame edge, so margin + slack). Callers still
    animate it in themselves.
    """
    from manim import UP, Text

    from open_manim_slides.layout import DEFAULT_MARGIN, assert_within_safe_frame

    kwargs.setdefault("font_size", FONT_SIZE_HEADING)
    mobj = slide.track(Text(text, **kwargs), id=id)
    mobj.to_edge(UP, buff=DEFAULT_MARGIN + SPACING_XS)
    assert_within_safe_frame(mobj)
    return mobj


def two_column(left: Any, right: Any, *, buff: float = SPACING_LG) -> Any:
    """Arrange two mobjects side by side as a safe-frame-checked pair.

    Factors out the "split the body into two halves" layout (e.g. a
    diagram next to bullet text): arranges `left`/`right` horizontally
    with `buff` between them -- `VGroup.arrange` centers the resulting
    group on the frame by default, so callers don't need to re-center it
    -- then safe-frame-checks the pair together, since either half alone
    can be in-frame while the combined width isn't.

    Does not create, track, or animate `left`/`right` -- callers still own
    that for each half individually, since the two halves are almost
    always different kinds of content (a diagram vs. text) needing
    different ids and entrance animations. Returns the `VGroup` so a
    caller can animate or reposition both halves together if needed.
    """
    from manim import RIGHT, VGroup

    from open_manim_slides.layout import assert_within_safe_frame

    group = VGroup(left, right).arrange(RIGHT, buff=buff)
    assert_within_safe_frame(group)
    return group


def diagram_with_caption(
    slide: Any,
    diagram: Any,
    text: str,
    id: str = "caption",  # noqa: A002 - matches track()'s `id=` kwarg
    *,
    buff: float = SPACING_SM,
    **kwargs: Any,
) -> Any:
    """Create, position, track, and safe-frame-check a caption under `diagram`.

    Factors out the "diagram with an explanatory line of text underneath"
    pattern: builds a `Text` at caption size, places it `buff` below
    `diagram` via `next_to`, tracks it, then safe-frame-checks the
    diagram+caption *pair* together -- not just the caption alone, since a
    caption can sit fine on its own while pushing the combined group past
    the frame edge.

    Does not create or track `diagram` itself -- callers own that, since
    diagrams vary too much (a `Circle`, a `VGroup` of shapes, ...) for one
    signature to cover. Still call `self.play(...)` yourself for both the
    diagram and the returned caption; this only removes the boilerplate
    that's identical regardless of what the diagram is.
    """
    from manim import DOWN, Text, VGroup

    from open_manim_slides.layout import assert_within_safe_frame

    kwargs.setdefault("font_size", FONT_SIZE_CAPTION)
    caption = slide.track(Text(text, **kwargs).next_to(diagram, DOWN, buff=buff), id=id)
    assert_within_safe_frame(VGroup(diagram, caption))
    return caption
