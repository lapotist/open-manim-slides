import pytest
from manim import RIGHT, Circle, Text

from open_manim_slides.layout import assert_no_overlap, assert_within_safe_frame


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
