from pathlib import Path

import pytest

from open_manim_slides.scaffold import new_deck, render_deck_source


def test_render_deck_source_has_one_function_per_segment():
    source = render_deck_source("My Deck", ["intro", "the main idea", "summary"])

    assert "class MyDeck(Slide):" in source
    assert "def segment_intro(self) -> None:" in source
    assert "def segment_the_main_idea(self) -> None:" in source
    assert "def segment_summary(self) -> None:" in source
    assert source.count("def segment_") == 3


def test_render_deck_source_calls_segments_in_order_with_next_slide():
    source = render_deck_source("My Deck", ["first", "second"])

    construct_body = source.split("def construct(self) -> None:")[1].split("def segment_")[0]
    assert construct_body.index("self.segment_first()") < construct_body.index("self.segment_second()")
    assert construct_body.count("self.next_slide()") == 2


def test_render_deck_source_rejects_empty_segments():
    with pytest.raises(ValueError):
        render_deck_source("Empty Deck", [])


def test_render_deck_source_rejects_duplicate_segment_slugs():
    with pytest.raises(ValueError):
        render_deck_source("Dupe Deck", ["Intro!", "intro"])


def test_new_deck_writes_expected_file(tmp_path: Path):
    out_path = new_deck("Intro to Vectors", ["intro", "example"], out_dir=tmp_path)

    assert out_path == tmp_path / "intro_to_vectors.py"
    assert out_path.exists()
    assert "class IntroToVectors(Slide):" in out_path.read_text()
