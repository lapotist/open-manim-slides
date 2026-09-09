"""
Driven Diagram
"""

from manim import Axes, Create, Dot, FadeIn, ValueTracker, always_redraw

from open_manim_slides import Slide
from open_manim_slides.theme import COLOR_ACCENT_2, heading


class DrivenDiagram(Slide):
    """CLEAN: `motion-recipes.md` recipe 2, exactly as written.

    The tracker keeps its value in its own coordinates and is never added
    to the scene, so R2's on-screen test cannot see it. This fixture is
    what stops that from being read as a segment where nothing changed.
    """

    def construct(self) -> None:
        self.segment_axes()
        self.next_slide()
        self.segment_sweep()
        self.next_slide()

    def segment_axes(self) -> None:
        head = heading(self, "A Point on Axes")
        axes = self.track(
            Axes(x_range=[0, 5, 1], y_range=[0, 4, 1], x_length=6, y_length=3.0),
            id="axes",
            decorative=True,
        )
        self.tracker = ValueTracker(0.5)
        dot = always_redraw(
            lambda: Dot(axes.c2p(self.tracker.get_value(), 2), color=COLOR_ACCENT_2)
        )
        self.dot = self.track(dot, id="runner")
        self.play(Create(head), Create(axes))
        self.play(FadeIn(self.dot))
        self.assert_no_overlap_among_tracked()

    def segment_sweep(self) -> None:
        self.play(self.tracker.animate.set_value(4.5))
        self.dot.clear_updaters()
        self.assert_no_overlap_among_tracked()
