"""
Equation Steps
"""

from manim import Brace, Create, MathTex, Square, TransformMatchingTex, UP, Write

from open_manim_slides import Slide
from open_manim_slides.theme import COLOR_ACCENT, SPACING_XS


class EquationSteps(Slide):
    """CLEAN: `TransformMatchingTex` and a `Brace`, the two constructs most
    likely to be misread by a text-morph or overlap check.

    `TransformMatchingTex` is an `AnimationGroup` whose children *are*
    `Transform`s between glyph groups, so a morph check that recurses
    without care reports the framework's own recommended fix as the bug it
    replaces. Needs latex.
    """

    def construct(self) -> None:
        self.segment_setup()
        self.next_slide()
        self.segment_substitute()
        self.next_slide()

    def segment_setup(self) -> None:
        figure = self.track(Square(side_length=2).shift(UP * 1.2), id="figure")
        brace = self.track(Brace(figure, UP, buff=SPACING_XS), id="brace", decorative=True)
        eq = self.track(MathTex("a^2", "+", "b^2", font_size=44).shift(UP * -1.6), id="eq")
        eq[0].set_color(COLOR_ACCENT)
        self.eq = eq
        self.play(Create(figure), Create(brace), Write(eq))
        self.assert_no_overlap_among_tracked()

    def segment_substitute(self) -> None:
        after = MathTex("a^2", "+", "25", font_size=44).move_to(self.eq)
        after[0].set_color(COLOR_ACCENT)
        self.play(TransformMatchingTex(self.eq, after))
        self.eq = self.track(after, id="eq-after")
        self.assert_no_overlap_among_tracked()
