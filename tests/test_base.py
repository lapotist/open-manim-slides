import json

import pytest
from manim import Circle

from open_manim_slides import Slide


class _DummySlide(Slide):
    def construct(self) -> None:
        pass


def test_wait_time_between_slides_defaults_through_the_real_property():
    slide = _DummySlide()

    assert slide.wait_time_between_slides == 0.15
    # If the default were set by shadowing manim-slides' property with a
    # plain class attribute, the property's own clamping setter would never
    # run -- confirm it does.
    slide.wait_time_between_slides = -1.0
    assert slide.wait_time_between_slides == 0.0


def test_track_returns_the_mobject_unchanged():
    slide = _DummySlide()
    circle = Circle()

    result = slide.track(circle, id="c1")

    assert result is circle


def test_track_duplicate_id_within_same_segment_raises():
    slide = _DummySlide()
    slide.track(Circle(), id="dup")

    with pytest.raises(ValueError, match="dup"):
        slide.track(Circle(), id="dup")


def test_track_same_id_reused_across_segments_is_allowed():
    slide = _DummySlide()
    slide.track(Circle(), id="title")
    slide.next_slide()

    # Same id again, in a new segment -- must not raise.
    slide.track(Circle(), id="title")

    assert len(slide._manifest["title"]["appearances"]) == 1  # recorded once so far (segment 0)


def test_next_slide_records_one_appearance_per_segment():
    slide = _DummySlide()
    slide.track(Circle(), id="title")
    slide.next_slide()
    slide.track(Circle(), id="title")
    slide.next_slide()

    appearances = slide._manifest["title"]["appearances"]
    assert [a["segment"] for a in appearances] == [0, 1]


def test_snapshot_failure_is_isolated_per_element():
    slide = _DummySlide()
    slide.track(object(), id="broken")  # has no get_corner() -> bbox computation fails
    slide.track(Circle(), id="ok")

    slide.next_slide()  # must not raise despite the broken element

    broken_appearance = slide._manifest["broken"]["appearances"][0]
    ok_appearance = slide._manifest["ok"]["appearances"][0]
    assert broken_appearance["bbox"] is None
    assert ok_appearance["bbox"] is not None


def test_persisting_element_gets_an_appearance_every_segment_without_retracking():
    """Regression test for the appearance-tracking gap in HANDOFF.md.

    A tracked element stays visually on screen once added, so it must keep
    accumulating appearances every segment it survives into -- not just the
    single segment `track()` happened to be called in.
    """
    slide = _DummySlide()
    slide.track(Circle(), id="title")
    slide.next_slide()  # segment 0 snapshot
    slide.next_slide()  # segment 1 snapshot -- title was never re-tracked
    slide.next_slide()  # segment 2 snapshot

    appearances = slide._manifest["title"]["appearances"]
    assert [a["segment"] for a in appearances] == [0, 1, 2]


def test_remove_stops_further_appearances_for_that_id():
    slide = _DummySlide()
    circle = slide.track(Circle(), id="title")
    slide.next_slide()  # segment 0: still active

    slide.remove(circle)
    slide.next_slide()  # segment 1: should be skipped, id is no longer active
    slide.next_slide()  # segment 2: still skipped

    appearances = slide._manifest["title"]["appearances"]
    assert [a["segment"] for a in appearances] == [0]


def test_remove_via_group_deactivates_member_ids():
    """FadeOut(a, b) wraps its targets in a transient Group before calling
    Scene.remove -- the removal check must see through that grouping."""
    from manim import Group

    slide = _DummySlide()
    a = slide.track(Circle(), id="a")
    b = slide.track(Circle(), id="b")
    slide.next_slide()

    slide.remove(Group(a, b))
    slide.next_slide()

    assert [x["segment"] for x in slide._manifest["a"]["appearances"]] == [0]
    assert [x["segment"] for x in slide._manifest["b"]["appearances"]] == [0]


def test_assert_no_overlap_among_tracked_catches_active_collisions():
    from manim import RIGHT

    slide = _DummySlide()
    slide.track(Circle(radius=1), id="a")
    slide.track(Circle(radius=1).shift(RIGHT * 0.5), id="b")

    with pytest.raises(ValueError, match="overlaps"):
        slide.assert_no_overlap_among_tracked()


def test_assert_no_overlap_among_tracked_ignores_removed_elements():
    from manim import RIGHT

    slide = _DummySlide()
    a = slide.track(Circle(radius=1), id="a")
    slide.track(Circle(radius=1).shift(RIGHT * 0.5), id="b")
    slide.remove(a)

    slide.assert_no_overlap_among_tracked()  # only "b" remains active -- must not raise


def test_track_decorative_defaults_to_false():
    slide = _DummySlide()
    slide.track(Circle(), id="c1")

    assert slide._manifest["c1"]["decorative"] is False


def test_track_decorative_true_is_recorded_in_manifest():
    slide = _DummySlide()
    slide.track(Circle(), id="backdrop", decorative=True)

    assert slide._manifest["backdrop"]["decorative"] is True


def test_assert_no_overlap_among_tracked_ignores_decorative_elements():
    from manim import RIGHT

    slide = _DummySlide()
    # A point sitting on a circle's own boundary always falls within that
    # circle's bounding box -- the exact false-positive pattern
    # `decorative=True` exists to opt out of.
    slide.track(Circle(radius=2), id="guide-circle", decorative=True)
    slide.track(Circle(radius=0.1).shift(RIGHT * 2), id="point-on-circle")

    slide.assert_no_overlap_among_tracked()  # must not raise


def test_assert_no_overlap_among_tracked_still_catches_content_collisions_alongside_decorative():
    from manim import RIGHT

    slide = _DummySlide()
    slide.track(Circle(radius=2), id="guide-circle", decorative=True)
    slide.track(Circle(radius=1), id="a")
    slide.track(Circle(radius=1).shift(RIGHT * 0.5), id="b")

    with pytest.raises(ValueError, match="overlaps"):
        slide.assert_no_overlap_among_tracked()


def test_assert_reasonably_centered_among_tracked_accepts_a_centered_composition():
    slide = _DummySlide()
    slide.track(Circle(radius=1), id="c1")

    slide.assert_reasonably_centered_among_tracked()  # must not raise


def test_assert_reasonably_centered_among_tracked_rejects_a_lopsided_composition():
    from manim import DOWN

    slide = _DummySlide()
    slide.track(Circle(radius=0.3), id="title")
    slide.track(Circle(radius=0.3).shift(DOWN * 2.5), id="result")

    with pytest.raises(ValueError, match="off-center"):
        slide.assert_reasonably_centered_among_tracked()


def test_assert_reasonably_centered_among_tracked_counts_decorative_elements():
    # Unlike assert_no_overlap_among_tracked, decorative elements still
    # occupy real visual space and should count toward whether the overall
    # composition reads as centered.
    from manim import DOWN

    slide = _DummySlide()
    slide.track(Circle(radius=0.3), id="title", decorative=True)
    slide.track(Circle(radius=0.3).shift(DOWN * 2.5), id="result", decorative=True)

    with pytest.raises(ValueError, match="off-center"):
        slide.assert_reasonably_centered_among_tracked()


def test_assert_reasonably_centered_among_tracked_accepts_a_custom_tolerance():
    from manim import DOWN

    slide = _DummySlide()
    slide.track(Circle(radius=0.3).shift(DOWN * 1.0), id="c1")

    slide.assert_reasonably_centered_among_tracked(tolerance=0.9)  # must not raise


def test_write_manifest_produces_expected_shape(tmp_path):
    from manim import config

    slide = _DummySlide()
    slide.track(Circle(), id="c1")
    slide.next_slide()

    original_media_dir = config.media_dir
    config.media_dir = str(tmp_path)
    try:
        slide._write_manifest()
    finally:
        config.media_dir = original_media_dir

    out_file = tmp_path / f"{type(slide).__name__}.manifest.json"
    payload = json.loads(out_file.read_text())

    assert payload["deck"] == "_DummySlide"
    assert payload["elements"][0]["id"] == "c1"
    assert payload["elements"][0]["appearances"][0]["segment"] == 0


def _tracking_slide():
    slide = _DummySlide()
    return slide


def test_find_text_over_decorative_reports_text_sitting_on_a_backdrop():
    """The gap no other check spans: `assert_no_overlap_among_tracked`
    drops decorative ids from both sides, so this pair is invisible to it."""
    from manim import LEFT, RIGHT, Line, Text

    slide = _tracking_slide()
    slide.track(Line(LEFT * 3, RIGHT * 3), id="axis", decorative=True)
    slide.track(Text("a caption", font_size=24), id="caption")

    assert slide.find_text_over_decorative() == [("caption", "axis")]
    # ...while the check that is supposed to cover collisions says nothing:
    slide.assert_no_overlap_among_tracked()


def test_find_text_over_decorative_ignores_text_placed_clear():
    from manim import DOWN, LEFT, RIGHT, Line, Text

    slide = _tracking_slide()
    slide.track(Line(LEFT * 3, RIGHT * 3), id="axis", decorative=True)
    slide.track(Text("a caption", font_size=24).shift(DOWN * 2), id="caption")

    assert slide.find_text_over_decorative() == []


def test_find_text_over_decorative_descends_into_tracked_groups():
    """A caption is as often a group's child as a tracked mobject itself --
    this found a real collision in an existing deck that every other check
    passed."""
    from manim import LEFT, RIGHT, Dot, Line, Text, VGroup

    slide = _tracking_slide()
    slide.track(Line(LEFT * 3, RIGHT * 3), id="meter", decorative=True)
    slide.track(VGroup(Dot(), Text("label", font_size=24)), id="marks")

    assert slide.find_text_over_decorative() == [("marks", "meter")]


def test_find_text_over_decorative_ignores_a_decorative_frame_around_the_text():
    from manim import SurroundingRectangle, Text

    slide = _tracking_slide()
    result = slide.track(Text("42", font_size=24), id="result")
    slide.track(SurroundingRectangle(result, buff=0.15), id="result-box", decorative=True)

    assert slide.find_text_over_decorative() == []


def test_find_text_over_decorative_ignores_pairs_the_overlap_check_already_covers():
    """Two non-decorative elements are `assert_no_overlap`'s job; reporting
    them here would double up on every finding it already raises."""
    from manim import LEFT, RIGHT, Line, Text

    slide = _tracking_slide()
    slide.track(Line(LEFT * 3, RIGHT * 3), id="axis")
    slide.track(Text("a caption", font_size=24), id="caption")

    assert slide.find_text_over_decorative() == []
    with pytest.raises(ValueError, match="overlaps"):
        slide.assert_no_overlap_among_tracked()
