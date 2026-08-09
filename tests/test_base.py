import json

import pytest
from manim import Circle

from open_manim_slides import Slide


class _DummySlide(Slide):
    def construct(self) -> None:
        pass


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
