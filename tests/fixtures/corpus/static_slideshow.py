"""
Static Slideshow
"""

from manim import RIGHT, UP, Circle, FadeIn, Square

from open_manim_slides import Slide


class StaticSlideshow(Slide):
    """FAILS: NoChangeAnimation (R2).

    Everything only ever appears. Nothing the previous segment left is
    touched, which is the slideshow failure the workflow exists to stop.
    """

    def construct(self) -> None:
        self.segment_open()
        self.next_slide()
        self.segment_more()
        self.next_slide()

    def segment_open(self) -> None:
        self.box = self.track(Square(side_length=1), id="box")
        self.play(FadeIn(self.box))
        self.assert_no_overlap_among_tracked()

    def segment_more(self) -> None:
        disc = self.track(Circle(radius=0.4).shift(RIGHT * 3 + UP * 2), id="disc")
        self.play(FadeIn(disc))
        self.assert_no_overlap_among_tracked()
