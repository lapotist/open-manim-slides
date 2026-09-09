"""
Heading Names The Subject
"""

from manim import Create, DOWN, Square, Write

from open_manim_slides import Slide
from open_manim_slides.theme import COLOR_ACCENT, heading


class HeadingNamesTheSubject(Slide):
    """CLEAN: a heading may name what the deck shows.

    "A Moving Point" is a title, not a claim about this instant. R4 used to
    report it, because an opening segment only introduces things and
    introductions are not changes, which is exactly the condition R4 fires
    on -- so every deck named after what it demonstrates was flagged on its
    first slide. R7 already draws the line this pins: headings, labels and
    equations are not prose. `empty_promise.py` is the other side of it,
    where the same words at caption size are still reported.
    """

    def construct(self) -> None:
        self.segment_open()
        self.next_slide()

    def segment_open(self) -> None:
        head = heading(self, "A Moving Point")
        figure = self.track(
            Square(side_length=2, color=COLOR_ACCENT).shift(DOWN * 0.5), id="figure"
        )
        self.play(Write(head), Create(figure))
        self.assert_no_overlap_among_tracked()
