"""Tests for the exported deck's navigation behaviour (see playback.py).

Split deliberately. The analysis is pure, so the cases that matter --
does the check actually *fail* when the viewer would see the wrong frame
-- are unit tests over synthetic recordings, and cost nothing. A check
that cannot fail is not a check, and proving that shouldn't require a
browser.

The one end-to-end test renders a real three-segment deck, exports it,
and walks it in headless Firefox. It is the only place the whole chain is
exercised against a real compositor, and it is skipped when Firefox isn't
installed rather than failing.
"""

import shutil

import pytest
from manim import Circle, Create, Square, Transform

from open_manim_slides import Slide, convert_to_html
from open_manim_slides.playback import _analyse, check


def _recording(*poses: tuple[int, float | None]) -> dict:
    """Build a recording where slide `h` had `mediaTime` on screen at entry.

    Each entry is (slide index, mediaTime last presented for that slide's
    video before the navigation, or None for "never painted").
    """
    navigations = []
    paints = []
    for step, (index, on_screen) in enumerate(poses):
        at = 1000.0 * (step + 1)
        navigations.append({"t": at, "h": index})
        if on_screen is not None:
            paints.append({"index": index, "t": at - 10.0, "mediaTime": on_screen})
    return {"durations": [5.0] * 6, "paints": paints, "navigations": navigations}


def test_first_visit_to_a_segment_is_always_fine():
    # Nothing has been painted for it, so nothing stale can be showing.
    (nav,) = _analyse(_recording((1, None)))
    assert nav.direction == "forward"
    assert nav.ok


def test_forward_re_entry_showing_the_segments_end_is_flagged():
    # The exact user-visible bug: -> into a segment whose video was left
    # parked at its end shows that ending -- the spoiler -- until it
    # repaints.
    navs = _analyse(_recording((1, None), (2, None), (1, 4.98), (2, 4.98)))
    flash = navs[-1]
    assert flash.direction == "forward"
    assert not flash.ok


def test_backward_entry_showing_a_mid_animation_frame_is_flagged():
    # <- into a segment should show its finished state; a frame from the
    # middle of its build means the animation is replaying.
    navs = _analyse(_recording((1, None), (2, None), (1, 2.42)))
    back = navs[-1]
    assert back.direction == "backward"
    assert back.expected_pose == pytest.approx(5.0)
    assert not back.ok


def test_correct_poses_pass():
    # -> onto a segment parked at 0, <- onto one parked at its end.
    navs = _analyse(_recording((1, None), (2, 0.0), (1, 4.98)))
    assert all(nav.ok for nav in navs)


def test_re_entry_flashing_content_the_viewer_already_saw_is_tolerated():
    # A hidden video's composited frame can lag its currentTime, so a
    # quick re-entry may show, for one frame, the frame the viewer left
    # on. That is a hiccup on already-seen content, not the spoiler this
    # check exists to catch -- see _MINIMUM_TOLERANCE.
    navs = _analyse(_recording((1, None), (2, None), (1, None), (2, 0.55)))
    assert navs[-1].direction == "forward"
    assert navs[-1].ok


def test_tolerance_scales_with_segment_length():
    # 1.2s into a 5s segment is a quarter of the way in and tolerated;
    # the same 1.2s into a 2s segment is past the middle and is not.
    walk = ((1, None), (2, None), (1, None), (2, 1.2))
    assert _analyse(_recording(*walk))[-1].ok
    short = _recording(*walk)
    short["durations"] = [2.0] * 6
    assert not _analyse(short)[-1].ok


def test_repaint_is_reported_but_never_decisive():
    # Timing magnitude is environment-specific (software vs GPU
    # compositing), so it is informational only -- a navigation with the
    # right frame already on screen and no repaint at all is the ideal
    # case, not a missing-data case.
    (nav,) = _analyse(_recording((1, 0.0)))
    assert nav.repaint_ms is None
    assert nav.ok


def test_paints_after_the_next_navigation_are_not_counted_as_this_ones_repaint():
    # Leaving a slide parks its video off screen, which paints. That paint
    # belongs to no navigation -- counting it would report a repaint that
    # the viewer never saw.
    recording = _recording((1, None), (2, None))
    recording["paints"].append({"index": 1, "t": 2500.0, "mediaTime": 0.0})
    first = _analyse(recording)[0]
    assert first.to_index == 1
    assert first.repaint_ms is None


class _PlaybackDeck(Slide):
    """Three segments, each ending on a distinct still frame."""

    def construct(self) -> None:
        circle = Circle()
        self.play(Create(circle))
        self.next_slide()
        square = Square()
        self.play(Transform(circle, square))
        self.next_slide()
        self.play(square.animate.shift([1.0, 0.0, 0.0]))
        self.next_slide()


@pytest.mark.skipif(shutil.which("firefox") is None, reason="needs Firefox to drive a real page")
def test_exported_deck_never_shows_the_wrong_frame(tmp_path):
    from manim import config

    slides_dir = tmp_path / "slides"
    saved = (
        config.media_dir,
        config.pixel_width,
        config.pixel_height,
        config.frame_rate,
        config.output_file,
    )
    config.media_dir = str(tmp_path / "media")
    config.pixel_width, config.pixel_height, config.frame_rate = 320, 180, 15
    # See test_convert.py: output_file is global and sticks around.
    config.output_file = ""
    try:
        _PlaybackDeck(output_folder=slides_dir).render()
    finally:
        (
            config.media_dir,
            config.pixel_width,
            config.pixel_height,
            config.frame_rate,
            config.output_file,
        ) = saved

    dest = tmp_path / "deck.html"
    convert_to_html(["_PlaybackDeck"], dest, folder=slides_dir, view_distance=50)

    # forward through all three, back out, then forward again -- the last
    # step is the re-entry that used to flash the segment's ending.
    navigations = check(
        dest.resolve().as_uri(),
        steps=["forward", "forward", "backward", "backward", "forward"],
        settle=1.5,
    )

    assert navigations, "no navigation was recorded"
    wrong = [nav.describe() for nav in navigations if not nav.ok]
    assert not wrong, "wrong frame on screen:\n" + "\n".join(wrong)
