"""
Glyph Soup
"""

from manim import Text, Transform

from open_manim_slides import Slide


class GlyphSoup(Slide):
    """FAILS: IllegibleTextMorph.

    Two headings with no letter correspondence, morphed outline-to-outline.
    The final frame is correct, which is why only a mechanical check sees it.
    """

    def construct(self) -> None:
        self.segment_open()
        self.next_slide()
        self.segment_swap()
        self.next_slide()

    def segment_open(self) -> None:
        self.head = self.track(Text("Counting Pairs", font_size=36), id="heading")
        self.add(self.head)

    def segment_swap(self) -> None:
        self.play(Transform(self.head, Text("Ordering Triples", font_size=36)))
        self.assert_no_overlap_among_tracked()
