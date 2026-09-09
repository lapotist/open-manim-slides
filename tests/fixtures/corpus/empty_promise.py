"""
Empty Promise
"""

from manim import DOWN, RIGHT, UP, FadeIn, Square, Text

from open_manim_slides import Slide


class EmptyPromise(Slide):
    """FAILS: UnperformedAction (R4).

    The caption says the square rotates. The caption moves; the square
    does not.

    The size is load-bearing: R4 scans prose as R7 defines it, so this must
    stay at caption size. Raise it to heading size and it becomes a title,
    which `heading_names_the_subject.py` pins as correct.
    """

    def construct(self) -> None:
        self.segment_open()
        self.next_slide()
        self.segment_promise()
        self.next_slide()

    def segment_open(self) -> None:
        self.shape = self.track(Square(side_length=1).shift(RIGHT * 3), id="shape")
        self.caption = self.track(Text("a square", font_size=24).shift(DOWN * 2), id="caption")
        self.play(FadeIn(self.shape), FadeIn(self.caption))
        self.assert_no_overlap_among_tracked()

    def segment_promise(self) -> None:
        self.remove(self.caption)
        self.caption = self.track(
            Text("the square rotates", font_size=24).shift(DOWN * 2), id="caption"
        )
        self.add(self.caption)
        self.play(self.caption.animate.shift(UP * 0.4))
        self.assert_no_overlap_among_tracked()
