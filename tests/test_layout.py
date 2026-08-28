import pytest
from manim import DOWN, RIGHT, Circle, Text

from open_manim_slides.layout import (
    assert_no_overlap,
    assert_reasonably_centered,
    assert_within_safe_frame,
    find_text_over_ink,
)


def test_assert_within_safe_frame_accepts_a_centered_small_shape():
    circle = Circle(radius=0.5)
    assert assert_within_safe_frame(circle) is circle


def test_assert_within_safe_frame_rejects_an_oversized_shape():
    circle = Circle(radius=20)
    with pytest.raises(ValueError, match="extends outside the safe frame"):
        assert_within_safe_frame(circle)


def test_assert_no_overlap_accepts_disjoint_shapes():
    a = Circle(radius=0.3)
    b = Circle(radius=0.3).shift(RIGHT * 5)
    assert_no_overlap(a, b)  # must not raise


def test_assert_no_overlap_rejects_overlapping_shapes():
    a = Circle(radius=1)
    b = Circle(radius=1).shift(RIGHT * 0.5)
    with pytest.raises(ValueError, match="overlaps"):
        assert_no_overlap(a, b)


def test_assert_no_overlap_catches_concentric_labels_stacking_up():
    # Same shape as the layers_of_the_earth.py stress test: labels placed
    # next_to() concentric circles of adjacent radii land close enough in
    # both x and y to collide horizontally. (The two most extreme radii
    # are far enough apart not to collide -- it's adjacent layers that do.)
    crust = Circle(radius=3)
    mantle = Circle(radius=2.2)
    crust_label = Text("Crust", font_size=28).next_to(crust, RIGHT)
    mantle_label = Text("Mantle", font_size=28).next_to(mantle, RIGHT)

    with pytest.raises(ValueError, match="overlaps"):
        assert_no_overlap(crust_label, mantle_label)


def test_assert_reasonably_centered_accepts_a_centered_shape():
    circle = Circle(radius=1)
    assert_reasonably_centered(circle)  # must not raise


def test_assert_reasonably_centered_rejects_a_lopsided_composition():
    # Same shape as the_pythagorean_theorem.py's summary bug: a title left
    # at its default centered position with more content stacked below it
    # via next_to, pushing the combined group's center well below true
    # center and leaving the top conspicuously empty.
    title = Circle(radius=0.3)
    result = Circle(radius=0.3).next_to(title, DOWN, buff=1.0)
    caption = Circle(radius=0.2).next_to(result, DOWN, buff=1.0)

    with pytest.raises(ValueError, match="off-center"):
        assert_reasonably_centered(title, result, caption)


def test_assert_reasonably_centered_accepts_the_same_group_once_recentered():
    from manim import ORIGIN, VGroup

    title = Circle(radius=0.3)
    result = Circle(radius=0.3).next_to(title, DOWN, buff=1.0)
    caption = Circle(radius=0.2).next_to(result, DOWN, buff=1.0)
    VGroup(title, result, caption).move_to(ORIGIN)

    assert_reasonably_centered(title, result, caption)  # must not raise


def test_assert_reasonably_centered_respects_custom_tolerance():
    circle = Circle(radius=0.3).shift(DOWN * 1.0)
    assert_reasonably_centered(circle, tolerance=0.9)  # loose enough to pass

    with pytest.raises(ValueError, match="off-center"):
        assert_reasonably_centered(circle, tolerance=0.01)  # too strict to pass


def test_find_text_over_ink_flags_a_line_running_through_the_text():
    """The session-fourteen shape: an axis crossing a caption.

    A `Line` has four control points, all at its ends, so a check that
    only tested the *points* would miss this entirely -- the polyline
    through them is what catches it.
    """
    from manim import LEFT, Line

    caption = Text("a caption", font_size=24)
    axis = Line(LEFT * 3, RIGHT * 3)

    assert find_text_over_ink([caption], [axis]) == [(caption, axis)]


def test_find_text_over_ink_ignores_a_stroke_that_only_shares_a_bounding_box():
    """Why `decorative=True` exists, and why this check doesn't need it.

    A diagonal line's bounding box covers both corners it never passes
    through -- exactly the false positive that made `assert_no_overlap`
    unusable on curved and diagonal shapes.
    """
    from manim import Line

    diagonal = Line([-2, -2, 0], [2, 2, 0])
    label = Text("x", font_size=24).move_to([1.4, -1.4, 0])

    assert find_text_over_ink([label], [diagonal]) == []


def test_find_text_over_ink_skips_a_backdrop_that_frames_the_text():
    """A `SurroundingRectangle` is drawn close on purpose; that isn't a collision."""
    from manim import SurroundingRectangle

    result = Text("42", font_size=24)
    box = SurroundingRectangle(result, buff=0.15)

    assert find_text_over_ink([result], [box]) == []


def test_find_text_over_ink_respects_the_clearance():
    from manim import LEFT, Line

    caption = Text("a caption", font_size=24)
    top = caption.get_top()[1]
    grazing = Line(LEFT * 3 + [0, top + 0.04, 0], RIGHT * 3 + [0, top + 0.04, 0])
    clear = Line(LEFT * 3 + [0, top + 0.5, 0], RIGHT * 3 + [0, top + 0.5, 0])

    assert find_text_over_ink([caption], [grazing]) == [(caption, grazing)]
    assert find_text_over_ink([caption], [clear]) == []
    assert find_text_over_ink([caption], [grazing], clearance=0.0) == []
