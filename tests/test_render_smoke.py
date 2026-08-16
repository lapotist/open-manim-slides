"""End-to-end smoke test: scaffold a deck, render it, confirm a video exists.

This is the one test in the suite that invokes manim's real rendering
pipeline, so it's slower than the rest -- kept to a two-segment deck with
trivial content to keep it reasonably fast.
"""

import importlib.util
import sys

from open_manim_slides.scaffold import new_deck


def test_scaffold_then_render_produces_a_video(tmp_path):
    from manim import config

    deck_path = new_deck("Smoke Test Deck", ["first", "second"], out_dir=tmp_path)
    # The scaffolder leaves a checklist comment above the baked-in overlap
    # check; give each segment trivial content above that check, same as
    # real authoring would, so the scene has something to render and the
    # scaffolded self.assert_no_overlap_among_tracked() call actually runs.
    # Anchored on the assert line rather than the checklist's wording so
    # this test doesn't silently inject nothing when the checklist changes.
    assert_line = "        self.assert_no_overlap_among_tracked()\n"
    source = deck_path.read_text().replace(
        assert_line,
        "        self.wait(0.2)\n" + assert_line,
    )
    deck_path.write_text(source)

    media_dir = tmp_path / "media"
    original_media_dir = config.media_dir
    original_quality = (config.pixel_width, config.pixel_height, config.frame_rate)
    original_output_file = config.output_file
    config.media_dir = str(media_dir)
    config.pixel_width, config.pixel_height, config.frame_rate = 320, 180, 15
    # config.output_file is a global that sticks around after a render --
    # left as-is, a later render() in the same process reuses the previous
    # scene's stale output path instead of deriving its own from the new
    # scene's name, and its own video never gets written.
    config.output_file = ""

    try:
        spec = importlib.util.spec_from_file_location("smoke_test_deck", deck_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        scene = module.SmokeTestDeck()
        scene.render()
    finally:
        config.media_dir = original_media_dir
        config.pixel_width, config.pixel_height, config.frame_rate = original_quality
        config.output_file = original_output_file
        sys.modules.pop("smoke_test_deck", None)

    videos = list(media_dir.rglob("SmokeTestDeck.mp4"))
    assert videos, "expected a rendered SmokeTestDeck.mp4 under the media dir"
    assert videos[0].stat().st_size > 0

    manifests = list(media_dir.rglob("*.manifest.json"))
    # No self.track() calls in this trivial deck, so no manifest is written --
    # just confirm rendering didn't produce one spuriously.
    assert manifests == []
