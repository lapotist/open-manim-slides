"""
The Water Cycle
"""

from manim import BLUE, DOWN, UP, Arrow, Circle, FadeIn, FadeOut, Text, Write

from open_manim_slides import Slide, assert_within_safe_frame


class TheWaterCycle(Slide):
    def construct(self) -> None:
        self.segment_intro()
        self.next_slide()
        self.segment_evaporation()
        self.next_slide()
        self.segment_condensation()
        self.next_slide()
        self.segment_precipitation()
        self.next_slide()
        self.segment_summary()
        self.next_slide()

    def segment_intro(self) -> None:
        """intro"""
        title = self.track(Text("The Water Cycle"), id="title")
        assert_within_safe_frame(title)
        self.play(Write(title))
        self.title = title

    def segment_evaporation(self) -> None:
        """evaporation"""
        label = self.track(Text("Evaporation", font_size=36).to_edge(DOWN), id="evaporation-label")
        assert_within_safe_frame(label)
        arrow = self.track(Arrow(start=DOWN * 2, end=UP * 2), id="evaporation-arrow")
        self.play(self.title.animate.to_edge(UP))
        self.play(FadeIn(arrow), Write(label))
        self.evaporation_arrow = arrow
        self.evaporation_label = label

    def segment_condensation(self) -> None:
        """condensation"""
        cloud = self.track(Circle(radius=0.8, color=BLUE, fill_opacity=0.5).to_edge(UP), id="cloud")
        assert_within_safe_frame(cloud)
        label = self.track(Text("Condensation", font_size=36).next_to(cloud, DOWN), id="condensation-label")
        self.play(FadeOut(self.evaporation_arrow, self.evaporation_label))
        self.play(FadeIn(cloud), Write(label))
        self.cloud = cloud
        self.condensation_label = label

    def segment_precipitation(self) -> None:
        """precipitation"""
        arrow = self.track(Arrow(start=UP * 1.5, end=DOWN * 2), id="precipitation-arrow")
        label = self.track(Text("Precipitation", font_size=36).to_edge(DOWN), id="precipitation-label")
        self.play(FadeOut(self.condensation_label))
        self.play(FadeIn(arrow), Write(label))
        self.precip_arrow = arrow
        self.precip_label = label

    def segment_summary(self) -> None:
        """summary"""
        summary = self.track(
            Text("Evaporation -> Condensation -> Precipitation", font_size=28),
            id="summary-text",
        )
        assert_within_safe_frame(summary)
        self.play(
            FadeOut(self.cloud, self.precip_arrow, self.precip_label, self.title),
            FadeIn(summary),
        )
