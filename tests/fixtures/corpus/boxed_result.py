"""
Boxed Result
"""

from manim import Create, SurroundingRectangle, Text, Write

from open_manim_slides import Slide
from open_manim_slides.theme import (
    COLOR_ACCENT,
    COLOR_ACCENT_2,
    FONT_SIZE_BODY,
    SPACING_SM,
)


class BoxedResult(Slide):
    """CLEAN: a backdrop that *frames* text is not a backdrop colliding with it.

    `SurroundingRectangle` is drawn close on purpose. A bounding-box rule
    reports it; the ink rule skips it because the box contains the text.
    The second segment grows the box, which must stay a framing relation.
    """

    def construct(self) -> None:
        self.segment_answer()
        self.next_slide()
        self.segment_emphasise()
        self.next_slide()

    def segment_answer(self) -> None:
        result = self.track(Text("42", font_size=FONT_SIZE_BODY), id="result")
        box = self.track(
            SurroundingRectangle(result, buff=SPACING_SM, color=COLOR_ACCENT),
            id="result-box",
            decorative=True,
        )
        self.result, self.box = result, box
        self.play(Write(result), Create(box))
        self.assert_no_overlap_among_tracked()

    def segment_emphasise(self) -> None:
        self.play(
            self.box.animate.scale(1.2),
            self.result.animate.set_color(COLOR_ACCENT_2),
        )
        self.assert_no_overlap_among_tracked()
