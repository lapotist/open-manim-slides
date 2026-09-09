"""
Overlapping
"""

from manim import RIGHT, Circle, Square

from open_manim_slides import Slide


class Overlapping(Slide):
    """FAILS: overlap. Two tracked elements land on each other."""

    def construct(self) -> None:
        self.segment_collide()
        self.next_slide()

    def segment_collide(self) -> None:
        self.track(Square(side_length=2), id="box")
        self.track(Circle(radius=1).shift(RIGHT * 0.5), id="disc")
        self.assert_no_overlap_among_tracked()
