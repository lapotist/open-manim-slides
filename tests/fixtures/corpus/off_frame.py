"""
Off Frame
"""

from manim import RIGHT, Square

from open_manim_slides import Slide, assert_within_safe_frame


class OffFrame(Slide):
    """FAILS: safe frame. The square hangs off the right edge."""

    def construct(self) -> None:
        self.segment_overhang()
        self.next_slide()

    def segment_overhang(self) -> None:
        box = self.track(Square(side_length=2).shift(RIGHT * 6.4), id="box")
        assert_within_safe_frame(box)
        self.assert_no_overlap_among_tracked()
