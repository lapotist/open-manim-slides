"""
Conflicting Play
"""

from manim import RIGHT, Circle, FadeOut, Square, Transform, VGroup

from open_manim_slides import Slide


class ConflictingPlay(Slide):
    """FAILS: ConflictingAnimations.

    `FadeOut(group)` and `Transform(child)` in one play own the same
    mobject. Manim can deadlock on this with no traceback, so the harness
    cannot reproduce it and the check has to be structural.
    """

    def construct(self) -> None:
        self.segment_open()
        self.next_slide()
        self.segment_clash()
        self.next_slide()

    def segment_open(self) -> None:
        self.keeper = Square(side_length=1)
        self.figure = VGroup(self.keeper, Square(side_length=1).shift(RIGHT * 3))
        self.add(self.figure)

    def segment_clash(self) -> None:
        self.play(FadeOut(self.figure), Transform(self.keeper, Circle(radius=0.5)))
        self.assert_no_overlap_among_tracked()
