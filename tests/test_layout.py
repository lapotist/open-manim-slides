import pytest
from manim import DOWN, RIGHT, Circle, Text

from open_manim_slides.layout import assert_no_overlap, assert_reasonably_centered, assert_within_safe_frame


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
