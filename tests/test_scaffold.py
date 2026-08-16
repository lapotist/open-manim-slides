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


def test_render_deck_source_bakes_in_overlap_check_per_segment():
    """The overlap check must be scaffolded in, not left to prose instructions
    an agent might skip -- see HANDOFF.md's "helper exists but gets bypassed"
    failure mode."""
    source = render_deck_source("My Deck", ["intro", "summary"])

    assert source.count("self.assert_no_overlap_among_tracked()") == 2


def test_render_deck_source_rejects_empty_segments():
    with pytest.raises(ValueError):
        render_deck_source("Empty Deck", [])


def test_render_deck_source_rejects_duplicate_segment_slugs():
    with pytest.raises(ValueError):
        render_deck_source("Dupe Deck", ["Intro!", "intro"])


def test_render_deck_source_stub_carries_the_content_checklist():
    source = render_deck_source("My Deck", ["intro", "summary"])

    assert source.count("delete this checklist") == 2
    assert "must CHANGE" in source
    # Checklist sits above the baked-in overlap check, inside the segment body.
    segment_body = source.split("def segment_intro(self) -> None:")[1].split("def segment_")[0]
    assert segment_body.index("delete this checklist") < segment_body.index(
        "self.assert_no_overlap_among_tracked()"
    )


def test_render_deck_source_audience_becomes_a_module_constant():
    source = render_deck_source("My Deck", ["intro"], audience="middle-school")

    assert 'AUDIENCE = "middle-school"' in source
    # Below the docstring, not inside it -- the webrunner's title regex
    # captures everything between the docstring quotes.
    assert source.index('"""\n\n') < source.index("AUDIENCE")


def test_render_deck_source_omits_audience_constant_by_default():
    source = render_deck_source("My Deck", ["intro"])

    assert "AUDIENCE" not in source


def test_audience_constant_does_not_leak_into_webrunner_title(tmp_path: Path):
    """Regression guard for the coupling that kept audience out of the
    docstring: webrunner's `_TITLE_RE` is DOTALL and captures everything
    between the docstring quotes."""
    pytest.importorskip("fastapi")
    from open_manim_slides.webrunner.render import list_decks

    new_deck("Audience Deck", ["intro"], out_dir=tmp_path, audience="high-school")

    decks = list_decks(tmp_path)
    assert [deck.title for deck in decks] == ["Audience Deck"]


def test_new_deck_writes_expected_file(tmp_path: Path):
    out_path = new_deck("Intro to Vectors", ["intro", "example"], out_dir=tmp_path)

    assert out_path == tmp_path / "intro_to_vectors.py"
    assert out_path.exists()
    assert "class IntroToVectors(Slide):" in out_path.read_text()


def test_new_deck_records_audience(tmp_path: Path):
    out_path = new_deck("Intro to Vectors", ["intro"], out_dir=tmp_path, audience="middle-school")

    assert 'AUDIENCE = "middle-school"' in out_path.read_text()
