"""The validation corpus: every gated check must fire, and must not misfire.

Each fixture in `fixtures/corpus/` is a real deck file loaded through
`validate.load_scene_class`, so this exercises the same path a user's
`python -m open_manim_slides.validate decks/<slug>.py` takes.

Two halves, two different jobs:

* **The failing half** pins that each check *can* fire, with the exact
  finding it is supposed to produce. A check that cannot fail is not a
  check — the standard the browser test was held to, applied to the
  headless ones.
* **The clean half** is the expensive half. It is the false-positive guard:
  run any *proposed* new check against it before shipping, because a rule
  that reports correct work does not merely annoy, it teaches the author to
  ignore every report. It is deliberately varied in composition so that
  passing it does not mean matching one house style.

See `fixtures/corpus/README.md`. These files are test data, never examples.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from open_manim_slides.validate import load_scene_class, validate_scene

CORPUS = Path(__file__).parent / "fixtures" / "corpus"

#: fixture -> the error types it must produce, exactly. `[]` means clean.
EXPECTED: dict[str, list[str]] = {
    # --- the check fires --------------------------------------------------
    "off_frame.py": ["ValueError"],
    "overlapping.py": ["ValueError"],
    "duplicate_id.py": ["ValueError"],
    "glyph_soup.py": ["IllegibleTextMorph"],
    "conflicting_play.py": ["ConflictingAnimations"],
    "caption_on_axis.py": ["TextOnDecorative"],
    "static_slideshow.py": ["NoChangeAnimation"],
    "empty_promise.py": ["UnperformedAction"],
    "lost_handoff.py": ["ValueError", "AttributeError"],
    # --- the check stays quiet --------------------------------------------
    "driven_diagram.py": [],
    "dissection.py": [],
    "centred_summary.py": [],
    "boxed_result.py": [],
    "heading_names_the_subject.py": [],
    "equation_steps.py": [],
}

#: Fixtures that compile a `MathTex`. `doctor` calls latex optional, so they
#: skip without it rather than failing, like the browser test without Firefox.
NEEDS_LATEX = {"equation_steps.py"}

CLEAN = sorted(name for name, expected in EXPECTED.items() if not expected)
BROKEN = sorted(name for name, expected in EXPECTED.items() if expected)


def _findings(name: str) -> list[str]:
    if name in NEEDS_LATEX and shutil.which("latex") is None:
        pytest.skip("needs a LaTeX install to compile MathTex")
    return [f.error_type for f in validate_scene(load_scene_class(CORPUS / name))]


def test_every_fixture_on_disk_is_registered():
    """An unregistered fixture is measured by nothing, which is worse than
    not existing: it looks like coverage."""
    on_disk = {path.name for path in CORPUS.glob("*.py")}

    assert on_disk == set(EXPECTED)


@pytest.mark.parametrize("name", BROKEN)
def test_a_broken_fixture_produces_exactly_its_finding(name: str):
    """A check that cannot fail is not a check.

    Exact, not "at least": a check that fires *and* drags two unrelated
    findings along with it is not reporting the thing under test.
    """
    assert _findings(name) == EXPECTED[name]


@pytest.mark.parametrize("name", CLEAN)
def test_a_clean_fixture_reports_nothing(name: str):
    """The false-positive guard.

    Each of these is correct work built out of a construct the framework
    documents and recommends. Anything reported here is the check being
    wrong, not the deck.
    """
    assert _findings(name) == []


def test_the_clean_half_covers_more_than_one_composition():
    """Passing this corpus must not mean matching one house style.

    A clean half that was five variations on the two-column layout would
    quietly turn the false-positive guard into a conformance test.
    """
    assert len(CLEAN) >= 4
    sources = [(CORPUS / name).read_text(encoding="utf-8") for name in CLEAN]

    assert any("Axes" in source for source in sources)
    assert any("Polygon" in source for source in sources)
    assert any("SurroundingRectangle" in source for source in sources)
    assert any("heading(" not in source for source in sources)
