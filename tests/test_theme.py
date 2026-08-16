import pytest
from manim import Circle

from open_manim_slides import Slide
from open_manim_slides.theme import (
    COLOR_ACCENT,
    COLOR_ACCENT_2,
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


class _DummySlide(Slide):
    def construct(self) -> None:
        pass


def test_typography_scale_is_ordered_title_down_to_caption():
    assert FONT_SIZE_TITLE > FONT_SIZE_HEADING > FONT_SIZE_BODY > FONT_SIZE_CAPTION


def test_spacing_scale_is_ordered_xs_up_to_xl():
    assert SPACING_XS < SPACING_SM < SPACING_MD < SPACING_LG < SPACING_XL


def test_title_slide_tracks_and_returns_a_sized_text_mobject():
    slide = _DummySlide()

    title = title_slide(slide, "Hello")

    assert title.text == "Hello"
    assert title.font_size == FONT_SIZE_TITLE
    assert slide._tracked_mobjects["title"] is title
    assert "title" in slide._active_ids


def test_title_slide_accepts_a_custom_id_and_font_size_override():
    slide = _DummySlide()

    heading = title_slide(slide, "Section", id="section-heading", font_size=FONT_SIZE_HEADING)

    assert heading.font_size == FONT_SIZE_HEADING
    assert slide._tracked_mobjects["section-heading"] is heading


def test_accent_colors_are_distinct_from_each_other_and_from_text():
    assert len({str(COLOR_ACCENT), str(COLOR_ACCENT_2), str(COLOR_TEXT)}) == 3


def test_heading_tracks_a_heading_sized_text_pinned_near_the_top():
    from manim import config

    slide = _DummySlide()

    mobj = heading(slide, "A Section")

    assert mobj.original_text == "A Section"
    assert mobj.font_size == pytest.approx(FONT_SIZE_HEADING)
    assert slide._tracked_mobjects["heading"] is mobj
    assert "heading" in slide._active_ids
    # Sits in the top band of the frame, but strictly inside the safe
    # margin -- the old title_slide(...).to_edge(UP) idiom landed exactly
    # on the boundary with zero slack.
    top = config.frame_height / 2
    assert mobj.get_top()[1] < top - 0.5
    assert mobj.get_top()[1] > top - 1.5


def test_heading_accepts_a_custom_id():
    slide = _DummySlide()

    mobj = heading(slide, "Other", id="other-heading")

    assert slide._tracked_mobjects["other-heading"] is mobj


def test_two_column_arranges_left_and_right_without_overlap():
    left = Circle(radius=1)
    right = Circle(radius=1)

    group = two_column(left, right)

    assert list(group) == [left, right]
    assert left.get_right()[0] <= right.get_left()[0]


def test_diagram_with_caption_tracks_and_positions_below_the_diagram():
    slide = _DummySlide()
    diagram = Circle(radius=0.5)

    caption = diagram_with_caption(slide, diagram, "A circle", id="circle-caption")

    assert caption.original_text == "A circle"
    assert caption.font_size == pytest.approx(FONT_SIZE_CAPTION)
    assert caption.get_top()[1] <= diagram.get_bottom()[1]
    assert slide._tracked_mobjects["circle-caption"] is caption
    assert "circle-caption" in slide._active_ids
