"""
Duplicate Id
"""

from manim import RIGHT, Circle

from open_manim_slides import Slide


class DuplicateId(Slide):
    """FAILS: duplicate id. The same id is tracked twice in one segment."""

    def construct(self) -> None:
        self.segment_copy_paste()
        self.next_slide()

    def segment_copy_paste(self) -> None:
        self.track(Circle(radius=0.4), id="mark")
        self.track(Circle(radius=0.4).shift(RIGHT * 2), id="mark")
        self.assert_no_overlap_among_tracked()
