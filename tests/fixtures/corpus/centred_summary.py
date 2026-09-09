"""
Centred Summary
"""

from manim import Circle, Create, VGroup, Write, Text

from open_manim_slides import Slide
from open_manim_slides.theme import COLOR_ACCENT, FONT_SIZE_BODY


class CentredSummary(Slide):
    """CLEAN: a single central figure, with the opt-in centering check.

    Not every deck is two columns. This is the shape `composition="none"`
    exists for, and the one place
    `assert_reasonably_centered_among_tracked()` is meant to be called --
    no heading pulling the combined box upward.
    """

    def construct(self) -> None:
        self.segment_result()
        self.next_slide()
        self.segment_grow()
        self.next_slide()

    def segment_result(self) -> None:
        disc = Circle(radius=1.2, color=COLOR_ACCENT)
        label = Text("one whole", font_size=FONT_SIZE_BODY)
        VGroup(disc, label).arrange_in_grid(rows=2, buff=0.4).move_to([0, 0, 0])
        self.disc = self.track(disc, id="disc")
        self.label = self.track(label, id="label")
        self.play(Create(disc), Write(label))
        self.assert_no_overlap_among_tracked()
        self.assert_reasonably_centered_among_tracked()

    def segment_grow(self) -> None:
        self.play(self.disc.animate.scale(1.15))
        self.assert_no_overlap_among_tracked()
