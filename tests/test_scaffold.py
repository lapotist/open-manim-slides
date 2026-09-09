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

    assert source.count("delete these notes") == 2
    assert "must CHANGE" in source
    # Checklist sits above the baked-in overlap check, inside the segment body.
    segment_body = source.split("def segment_intro(self) -> None:")[1].split("def segment_")[0]
    assert segment_body.index("delete these notes") < segment_body.index(
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


# --- Authoring context -------------------------------------------------
#
# These cover what the scaffolder emits *beyond* function stubs. The
# motivation is measured, not stylistic: across six real builds the two
# failure classes that drove the most check-fix round trips were state
# handoff (AttributeError on a name an earlier segment never set) and
# per-segment invented coordinates (safe-frame / overlap). Both are decided
# before any check can run, so both are answered in the emitted file.

from open_manim_slides.scaffold import (  # noqa: E402
    AUDIENCE_BUDGETS,
    MAX_CLEARED_STARTS,
    Segment,
    check_plan,
)


def _planned_deck():
    return [
        Segment("open", shows="A roof over an area", produces=["axes", "roof"]),
        Segment("spike", shows="The spike runs away", carries=["axes"], produces=["spike"]),
        Segment("close", shows="The band collapses", carries=["axes", "spike"]),
    ]


def test_planned_segments_declare_their_handoff_names():
    source = render_deck_source("Planned", _planned_deck())

    assert "axes: Mobject" in source
    assert "roof: Mobject" in source
    assert "spike: Mobject" in source


def test_declared_state_is_annotation_only_so_a_missed_handoff_still_raises():
    """Annotations document the name without creating the attribute.

    Assigning defaults here would turn a forgotten handoff into a silent
    `None` flowing into the next segment -- strictly worse than the
    `AttributeError` it replaces. The name being written down is the whole
    benefit; the failure must stay loud.
    """
    source = render_deck_source("Planned", _planned_deck())

    assert "axes: Mobject" in source
    assert "axes = None" not in source
    assert "axes: Mobject =" not in source


def test_segment_stub_names_what_it_carries_and_hands_off():
    source = render_deck_source("Planned", _planned_deck())
    body = source.split("def segment_spike(self) -> None:")[1].split("def segment_")[0]

    assert "carried in:  self.axes" in body
    assert "hand off:    self.spike" in body


def test_cleared_start_is_labelled_as_one_of_the_two_allowed():
    source = render_deck_source("Planned", _planned_deck())
    body = source.split("def segment_open(self) -> None:")[1].split("def segment_")[0]

    assert "cleared frame" in body
    assert "at most 2" in body


def test_composition_block_slots_sit_inside_the_safe_frame():
    source = render_deck_source("Planned", _planned_deck())
    namespace: dict = {}
    for line in source.splitlines():
        if line and not line.startswith((" ", "#", '"', "f", "c")) and "=" in line:
            try:
                exec(line, {}, namespace)  # noqa: S102 - reading our own emitted constants
            except Exception:
                pass

    assert abs(namespace["COL_LEFT_X"]) + namespace["COL_W"] / 2 <= namespace["SAFE_X"] + 1e-9
    assert abs(namespace["COL_RIGHT_X"]) + namespace["COL_W"] / 2 <= namespace["SAFE_X"] + 1e-9
    assert max(abs(y) for y in namespace["ROW_Y"]) < namespace["SAFE_Y"]
    assert namespace["HEAD_Y"] < namespace["SAFE_Y"]


def test_composition_can_be_omitted():
    source = render_deck_source("Planned", _planned_deck(), composition="none")

    assert "COL_LEFT_X" not in source


def test_segment_stub_carries_the_audience_budget():
    source = render_deck_source("Planned", _planned_deck(), audience="middle-school")
    budget = AUDIENCE_BUDGETS["middle-school"]

    assert source.count(f"<= {budget['plays']} self.play() calls") == 3
    assert f"<= {budget['words']} words on screen" in source


def test_plan_rejects_a_handoff_no_earlier_segment_produces():
    """The AttributeError class, caught before any code is written."""
    with pytest.raises(ValueError, match="no earlier segment produces"):
        check_plan([Segment("a", produces=["axes"]), Segment("b", carries=["roof_fig"])])


def test_plan_error_names_what_was_available_instead():
    with pytest.raises(ValueError, match="Available at that point: axes"):
        check_plan([Segment("a", produces=["axes"]), Segment("b", carries=["typo"])])


def test_plan_rejects_more_than_two_cleared_starts():
    plan = [Segment("a", produces=["f"]), Segment("b"), Segment("c"), Segment("d", carries=["f"])]
    with pytest.raises(ValueError, match=f"R1 allows {MAX_CLEARED_STARTS}"):
        check_plan(plan)


def test_plan_allows_exactly_two_cleared_starts():
    plan = [Segment("a", produces=["f"]), Segment("b"), Segment("c", carries=["f"])]

    assert check_plan(plan) == []


def test_plan_notes_segment_count_against_the_audience_without_raising():
    notes = check_plan(_planned_deck(), audience="high-school")

    assert any("3 segments" in note and "7-9" in note for note in notes)


def test_unplanned_string_segments_still_work():
    """Backwards compatibility: a bare name list is still a valid plan."""
    source = render_deck_source("Simple", ["intro", "summary"])

    assert "def segment_intro(self) -> None:" in source
    assert "Mobject" not in source


def test_segments_accept_dicts_from_the_plan_table():
    source = render_deck_source(
        "From Table",
        [
            {"name": "open", "shows": "the setup", "produces": ["fig"]},
            {"name": "close", "shows": "the payoff", "carries": ["fig"]},
        ],
    )

    assert '"""the setup"""' in source
    assert "carried in:  self.fig" in source


# --- Imports -----------------------------------------------------------
#
# The file used to arrive with two imports for a workflow whose own
# examples use `np.array`, `heading()`, `Text` and a colour token in the
# first ten lines -- so the first thing every build did was add an import
# and re-run. These pin that the emitted file can be authored against the
# skill's documented vocabulary without editing the import block.


def test_emitted_file_imports_what_the_workflow_tells_the_author_to_use():
    source = render_deck_source("Imports", ["intro"])

    assert "import numpy as np" in source
    assert "from manim import *" in source
    for name in ("heading", "title_slide", "COLOR_ACCENT", "FONT_SIZE_HEADING", "SPACING_MD"):
        assert name in source, name


def test_two_column_is_not_offered_alongside_a_composition_block():
    """Two layout systems in one file and no way to choose between them.

    `two_column` centres its halves on their own content width, so the
    column centres move segment to segment -- which is the placement
    `COL_LEFT_X`/`COL_RIGHT_X` exist to replace.
    """
    with_composition = render_deck_source("Imports", ["intro"])
    without = render_deck_source("Imports", ["intro"], composition="none")

    assert "two_column" not in with_composition
    assert "COL_LEFT_X" in with_composition
    assert "two_column" in without


def test_emitted_file_is_importable_and_authorable_as_written(tmp_path: Path):
    """A syntax or name error in the scaffold costs every build a round
    trip, so the emitted file is executed here rather than string-matched."""
    import importlib.util
    import sys

    path = new_deck(
        "Runnable Deck",
        [Segment("open", shows="a square", produces=["fig"])],
        out_dir=tmp_path,
        audience="high-school",
    )
    spec = importlib.util.spec_from_file_location("runnable_deck", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        # Every name the segment stub's own checklist points the author at
        # resolves in the emitted module's namespace.
        for name in ("np", "Text", "VGroup", "Transform", "heading", "COLOR_ACCENT", "COL_LEFT_X"):
            assert hasattr(module, name), name
        assert module.RunnableDeck.__name__ == "RunnableDeck"
    finally:
        sys.modules.pop("runnable_deck", None)


def test_composition_slot_comments_line_up():
    """A negative value is one character wider than its positive twin, and
    used to push `COL_LEFT_X`'s comment out of line with every other row."""
    source = render_deck_source("Aligned", ["intro"])
    columns = {
        line.index("#")
        for line in source.splitlines()
        if line.startswith(("SAFE_", "HEAD_Y", "COL_", "ROW_Y")) and "#" in line
    }

    assert len(columns) == 1


# --- Modes and imports -------------------------------------------------
#
# Two axes the project owner pins once, in `open-manim-slides.json`, rather
# than the agent re-deciding per build. The line they draw is the point:
# a mode changes what is *written into the file*, never what `validate`
# enforces. Pre-commitment gates are house style and relax; the checks that
# catch defects do not.

from open_manim_slides.scaffold import (  # noqa: E402
    MODE_DEFAULTS,
    SETTINGS_FILE,
    project_settings,
    resolve_options,
)


def test_simple_mode_is_the_default_and_keeps_the_rails():
    source = render_deck_source("Demo", _planned_deck())

    assert "COL_LEFT_X" in source
    assert "from manim import *" in source
    assert "delete these notes" in source


def test_advanced_mode_hands_the_composition_back_to_the_author():
    source = render_deck_source("Demo", _planned_deck(), mode="advanced")

    assert "COL_LEFT_X" not in source
    assert "from manim import *" not in source
    assert "two_column" in source  # the content-width template is right again
    assert "You own the composition" in source


def test_advanced_mode_still_scaffolds_the_overlap_check():
    """Relaxing house style must not relax a check that catches defects."""
    source = render_deck_source("Demo", _planned_deck(), mode="advanced")

    assert source.count("self.assert_no_overlap_among_tracked()") == 3
    assert "allow=" in source  # and names the sanctioned way to overlap on purpose


def test_advanced_mode_lifts_the_cleared_start_ceiling_but_not_the_handoff_check():
    """How many segments open on a cleared frame is a pacing judgement; a
    carried name nothing produces is a defect in any style."""
    too_many = [Segment("a", produces=["f"]), Segment("b"), Segment("c"), Segment("d", carries=["f"])]

    assert check_plan(too_many, max_cleared_starts=None) == []
    with pytest.raises(ValueError, match="R1 allows"):
        check_plan(too_many)
    with pytest.raises(ValueError, match="no earlier segment produces"):
        check_plan([Segment("a", produces=["f"]), Segment("b", carries=["nope"])], max_cleared_starts=None)


def test_curated_imports_name_the_house_vocabulary():
    source = render_deck_source("Demo", ["intro"], imports="curated")

    assert "from manim import (" in source
    assert "    Transform," in source
    assert "from manim import *" not in source
    assert "heading," in source  # theme tokens still arrive


def test_minimal_imports_restore_the_bare_file():
    """Kept as an explicit choice, so nobody falls back into it by accident."""
    source = render_deck_source("Demo", _planned_deck(), imports="minimal")

    assert "from manim import Mobject" in source
    assert "numpy" not in source
    assert "COLOR_ACCENT" not in source


def test_an_explicit_import_list_is_used_verbatim():
    source = render_deck_source("Demo", ["intro"], imports=["Square", "Create"])

    assert "    Square,\n" in source and "    Create,\n" in source
    assert "    Brace," not in source


def test_an_empty_import_list_is_rejected():
    with pytest.raises(ValueError, match="empty list"):
        render_deck_source("Demo", ["intro"], imports=[])


def test_unknown_mode_is_rejected_by_name():
    with pytest.raises(ValueError, match="Unknown mode"):
        render_deck_source("Demo", ["intro"], mode="expert")


def test_a_project_setting_decides_when_the_caller_does_not(tmp_path: Path):
    """The whole point of the file: the project pins the choice once, so no
    build has to re-decide it."""
    (tmp_path / SETTINGS_FILE).write_text('{"mode": "advanced"}', encoding="utf-8")

    assert project_settings(tmp_path) == {"mode": "advanced"}
    assert resolve_options(root=tmp_path)["composition"] == "none"
    # An explicit argument still wins over the file.
    assert resolve_options(mode="simple", root=tmp_path)["composition"] == "two-column"


def test_a_missing_or_unreadable_settings_file_falls_back_to_simple(tmp_path: Path):
    assert project_settings(tmp_path) == {}
    (tmp_path / SETTINGS_FILE).write_text("{not json", encoding="utf-8")

    assert project_settings(tmp_path) == {}
    assert resolve_options(root=tmp_path)["mode"] == "simple"


def test_every_mode_declares_a_full_set_of_defaults():
    keys = {"composition", "imports", "brief_stub", "max_cleared_starts"}

    assert all(set(defaults) == keys for defaults in MODE_DEFAULTS.values())
