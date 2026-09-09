"""
Lost Handoff
"""

from manim import RIGHT

from open_manim_slides import Slide


class LostHandoff(Slide):
    """FAILS: a real failure, then a cascade.

    The first segment raises before setting `self.figure`, so the second
    reports an `AttributeError` several lines from the actual mistake.
    That cascade shape is the single most common failure in past builds.
    """

    def construct(self) -> None:
        self.segment_builds()
        self.next_slide()
        self.segment_reads()
        self.next_slide()

    def segment_builds(self) -> None:
        raise ValueError("the real mistake lives here")

    def segment_reads(self) -> None:
        self.figure.shift(RIGHT)
