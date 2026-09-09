"""
Dissection
"""

from manim import Create, DOWN, Indicate, Polygon, VGroup, Write

from open_manim_slides import Slide
from open_manim_slides.theme import COLOR_ACCENT, COLOR_ACCENT_2, SPACING_SM, heading


class Dissection(Slide):
    """CLEAN: a composite figure under one id, plus emphasis beside a change.

    Two halves tile flush against each other by construction, which is a
    bounding-box collision and a correct drawing. The documented answer is
    one `VGroup` under one id, not `decorative=True`. The second segment
    pairs an `Indicate` on one half with a real move of the other, in a
    single play -- so this fails if emphasis exclusion ever starts
    swallowing the change standing next to it.
    """

    def construct(self) -> None:
        self.segment_split()
        self.next_slide()
        self.segment_open_it()
        self.next_slide()

    def segment_split(self) -> None:
        corners = [(-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5)]
        lower = Polygon(
            [*corners[0], 0], [*corners[1], 0], [*corners[2], 0], color=COLOR_ACCENT
        )
        upper = Polygon(
            [*corners[0], 0], [*corners[2], 0], [*corners[3], 0], color=COLOR_ACCENT_2
        )
        self.figure = self.track(VGroup(lower, upper), id="square")
        self.halves = (lower, upper)
        head = heading(self, "One Cut")
        self.play(Write(head), Create(self.figure))
        self.assert_no_overlap_among_tracked()

    def segment_open_it(self) -> None:
        lower, upper = self.halves
        self.play(Indicate(lower), upper.animate.shift(DOWN * SPACING_SM))
        self.assert_no_overlap_among_tracked()
