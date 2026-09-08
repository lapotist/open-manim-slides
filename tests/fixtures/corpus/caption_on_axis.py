"""
Caption On Axis
"""

from manim import LEFT, RIGHT, Line, Text

from open_manim_slides import Slide


class CaptionOnAxis(Slide):
    """FAILS: TextOnDecorative.

    The pair no other check spans: the overlap check drops decorative ids
    from both sides, and the caption is safely inside the frame. It is
    still sitting on the axis stroke.
    """

    def construct(self) -> None:
        self.segment_label()
        self.next_slide()

    def segment_label(self) -> None:
        self.track(Line(LEFT * 3, RIGHT * 3), id="axis", decorative=True)
        self.track(Text("one metre", font_size=24), id="caption")
        self.assert_no_overlap_among_tracked()
