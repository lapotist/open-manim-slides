"""Tests for the web runner's deck discovery, progress parsing, and route
wiring. Deliberately does not trigger a real `manim render` subprocess --
that path is exercised manually / would belong in a slower, separate
end-to-end test, same reasoning as `test_render_smoke.py` being the one
real-render test in the suite.
"""

from pathlib import Path

from open_manim_slides.webrunner.render import _ANIMATION_PROGRESS_RE, _progress_from_animation_line, list_decks


def _write_deck(tmp_path: Path, filename: str, title: str, class_name: str) -> Path:
    path = tmp_path / filename
    path.write_text(
        f'"""\n{title}\n"""\n\n'
        "from open_manim_slides import Slide\n\n\n"
        f"class {class_name}(Slide):\n"
        "    def construct(self) -> None:\n"
        "        pass\n"
    )
    return path


def test_list_decks_finds_title_and_class_name(tmp_path):
    _write_deck(tmp_path, "the_water_cycle.py", "The Water Cycle", "TheWaterCycle")

    decks = list_decks(tmp_path)

    assert len(decks) == 1
    assert decks[0].id == "the_water_cycle"
    assert decks[0].file == "the_water_cycle.py"
    assert decks[0].class_name == "TheWaterCycle"
    assert decks[0].title == "The Water Cycle"


def test_list_decks_falls_back_to_filename_without_a_docstring(tmp_path):
    path = tmp_path / "untitled.py"
    path.write_text("from open_manim_slides import Slide\n\n\nclass Untitled(Slide):\n    pass\n")

    decks = list_decks(tmp_path)

    assert decks[0].title == "untitled"


def test_list_decks_skips_files_with_no_slide_subclass(tmp_path):
    (tmp_path / "helpers.py").write_text("def helper():\n    pass\n")

    assert list_decks(tmp_path) == []


def test_list_decks_returns_empty_for_missing_directory(tmp_path):
    assert list_decks(tmp_path / "does_not_exist") == []


def test_list_decks_is_sorted_and_handles_multiple_files(tmp_path):
    _write_deck(tmp_path, "b_deck.py", "B Deck", "BDeck")
    _write_deck(tmp_path, "a_deck.py", "A Deck", "ADeck")

    decks = list_decks(tmp_path)

    assert [d.id for d in decks] == ["a_deck", "b_deck"]


def test_animation_progress_regex_parses_manims_tqdm_line():
    line = "Animation 13: Write(MathTex('a')), etc.:  83%|████████▎ | 50/60 [00:00<00:00, 145.00it/s]\n"

    match = _ANIMATION_PROGRESS_RE.search(line)

    assert match is not None
    assert match.group(1) == "13"
    assert match.group(2) == "83"


def test_animation_progress_regex_does_not_match_unrelated_lines():
    assert _ANIMATION_PROGRESS_RE.search("Rendered TheWaterCycle") is None


def test_progress_from_animation_line_within_the_original_estimate():
    total, progress, message = _progress_from_animation_line(index=2, within=50, total_estimate=8)

    assert total == 8
    assert message == "Rendering animation 3 of ~8"
    assert 0 < progress < 99


def test_progress_from_animation_line_self_corrects_when_estimate_is_exceeded():
    # The estimate (counting `self.play(` call sites) is a lower bound in
    # practice -- a single call can log as more than one "Animation N"
    # entry. Once the real count exceeds it, the displayed total must grow
    # to match rather than showing a nonsensical "animation 12 of ~8".
    total, progress, message = _progress_from_animation_line(index=11, within=50, total_estimate=8)

    assert total == 12
    assert message == "Rendering animation 12 of ~12"
    assert progress <= 99


def test_progress_from_animation_line_caps_progress_at_99():
    _, progress, _ = _progress_from_animation_line(index=7, within=99, total_estimate=8)

    assert progress == 99


def test_api_lists_decks(tmp_path, monkeypatch):
    decks_dir = tmp_path / "decks"
    decks_dir.mkdir()
    _write_deck(decks_dir, "solo.py", "Solo Deck", "SoloDeck")
    monkeypatch.chdir(tmp_path)

    from fastapi.testclient import TestClient

    from open_manim_slides.webrunner.app import app

    client = TestClient(app)
    response = client.get("/api/decks")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "solo", "file": "solo.py", "class_name": "SoloDeck", "title": "Solo Deck"}
    ]


def test_api_render_unknown_deck_returns_404(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    from fastapi.testclient import TestClient

    from open_manim_slides.webrunner.app import app

    client = TestClient(app)
    response = client.post("/api/render/does-not-exist")

    assert response.status_code == 404


def test_api_events_for_unknown_job_returns_404():
    from fastapi.testclient import TestClient

    from open_manim_slides.webrunner.app import app

    client = TestClient(app)
    response = client.get("/api/render/does-not-exist/events")

    assert response.status_code == 404


def test_index_serves_the_frontend_page():
    from fastapi.testclient import TestClient

    from open_manim_slides.webrunner.app import app

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "Runner" in response.text
