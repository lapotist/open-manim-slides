from pathlib import Path

import pytest
from manim import (
    LEFT,
    PI,
    RIGHT,
    UP,
    Circle,
    Dot,
    FadeIn,
    FadeOut,
    FadeTransform,
    LaggedStart,
    Indicate,
    MathTex,
    Rotate,
    Square,
    Text,
    Transform,
    TransformMatchingTex,
    VGroup,
    ValueTracker,
    always_redraw,
)

from open_manim_slides import Slide, assert_within_safe_frame
from open_manim_slides.validate import (
    Failure,
    ValidateError,
    format_failures,
    load_scene_class,
    main,
    validate_scene,
)


class _CleanDeck(Slide):
    def construct(self) -> None:
        self.segment_one()
        self.next_slide()

    def segment_one(self) -> None:
        box = self.track(Square(side_length=1), id="box")
        assert_within_safe_frame(box)
        self.assert_no_overlap_among_tracked()


class _AnimatedDeck(Slide):
    """Passes only if `play()` actually applied each animation's end state."""

    def construct(self) -> None:
        self.segment_move()
        self.next_slide()

    def segment_move(self) -> None:
        box = self.track(Square(side_length=1).shift(LEFT * 3), id="box")
        self.play(box.animate.shift(RIGHT * 6))
        if round(float(box.get_center()[0]), 3) != 3.0:
            raise AssertionError(f"end state not applied: x={box.get_center()[0]}")


class _UpdaterDeck(Slide):
    """Passes only if scene updaters ran, so always_redraw geometry is current."""

    def construct(self) -> None:
        self.segment_sweep()
        self.next_slide()

    def segment_sweep(self) -> None:
        tracker = ValueTracker(0.0)
        dot = always_redraw(lambda: Dot(RIGHT * tracker.get_value()))
        self.add(dot)
        self.play(tracker.animate.set_value(2.0))
        dot.clear_updaters()
        if round(float(dot.get_center()[0]), 3) != 2.0:
            raise AssertionError(f"updater never ticked: x={dot.get_center()[0]}")


class _TwoIndependentFailuresDeck(Slide):
    def construct(self) -> None:
        self.segment_overflow()
        self.next_slide()
        self.segment_duplicate()
        self.next_slide()

    def segment_overflow(self) -> None:
        box = Square(side_length=2).shift(RIGHT * 6.4)
        assert_within_safe_frame(box)

    def segment_duplicate(self) -> None:
        self.track(Circle(radius=0.2), id="dup")
        self.track(Circle(radius=0.2), id="dup")


class _CascadeDeck(Slide):
    def construct(self) -> None:
        self.segment_fails()
        self.next_slide()
        self.segment_reads_missing_attr()
        self.next_slide()

    def segment_fails(self) -> None:
        raise ValueError("primary failure")

    def segment_reads_missing_attr(self) -> None:
        self.figure.shift(RIGHT)  # never set, because segment_fails raised


def test_clean_deck_reports_no_failures():
    assert validate_scene(_CleanDeck) == []


def test_play_applies_each_animation_end_state():
    """The whole harness rests on this: geometry after `play()` must match
    what a real render would produce, or later segments compute nonsense."""
    assert validate_scene(_AnimatedDeck) == []


def test_scene_updaters_run_so_always_redraw_geometry_is_current():
    """always_redraw mobjects only regenerate when the scene ticks; a later
    segment reading their geometry would otherwise see a stale pose."""
    assert validate_scene(_UpdaterDeck) == []


def test_every_failing_segment_is_reported_in_one_pass():
    """The point of the tool: N independent mistakes cost one run, not N
    render cycles."""
    failures = validate_scene(_TwoIndependentFailuresDeck)

    assert [failure.index for failure in failures] == [0, 1]
    assert "safe frame" in failures[0].message
    assert "already used in this segment" in failures[1].message
    assert not any(failure.cascaded for failure in failures)


def test_missing_attribute_after_a_failure_is_marked_as_a_cascade():
    failures = validate_scene(_CascadeDeck)

    assert len(failures) == 2
    assert not failures[0].cascaded
    assert failures[1].cascaded


def test_repeated_geometry_is_marked_as_a_cascade_despite_different_wording():
    """`assert_no_overlap` names whichever of the pair it reaches first, so
    one unresolved collision reads as both "A overlaps B" and "B overlaps
    A". Matching on the coordinates sees through that."""
    first = ValueError("Circle overlaps Square: x=[-1.00,1.00] vs [-0.75,0.75]")
    second = ValueError("Square overlaps Circle: x=[-0.75,0.75] vs [-1.00,1.00]")

    from open_manim_slides.validate import _failure_signature

    assert _failure_signature(first, str(first)) == _failure_signature(second, str(second))


class _TextMorphDeck(Slide):
    """One illegible swap plus every shape that must NOT be flagged."""

    def construct(self) -> None:
        self.segment_bad_heading_swap()
        self.next_slide()
        self.segment_fade_transform_is_fine()
        self.next_slide()
        self.segment_matching_tex_is_fine()
        self.next_slide()
        self.segment_shape_morph_is_fine()
        self.next_slide()
        self.segment_tiny_number_is_fine()
        self.next_slide()
        self.segment_bad_morph_nested_in_a_group()
        self.next_slide()

    def segment_bad_heading_swap(self) -> None:
        head = Text("Choose Two of Five")
        self.add(head)
        self.play(Transform(head, Text("First, Then Second")))

    def segment_fade_transform_is_fine(self) -> None:
        head = Text("Choose Two of Five")
        self.add(head)
        self.play(FadeTransform(head, Text("First, Then Second")))

    def segment_matching_tex_is_fine(self) -> None:
        eq = MathTex("a^2", "+", "b^2")
        self.add(eq)
        self.play(TransformMatchingTex(eq, MathTex("a^2", "+", "25")))

    def segment_shape_morph_is_fine(self) -> None:
        square = Square()
        self.add(square)
        self.play(Transform(square, Circle()))

    def segment_tiny_number_is_fine(self) -> None:
        number = MathTex("1")
        self.add(number)
        self.play(Transform(number, MathTex("2")))

    def segment_bad_morph_nested_in_a_group(self) -> None:
        head = Text("Rolling Two Dice")
        self.add(head)
        self.play(LaggedStart(Transform(head, Text("Counting Outcomes"))))


def test_illegible_text_morphs_are_reported():
    """`Transform` interpolates glyph outlines, so swapping one sentence for
    another spends most of the play unreadable. A final-frame review cannot
    see it -- the final frame is the one moment nothing is moving -- which
    is why it has to be a mechanical check."""
    failures = validate_scene(_TextMorphDeck)

    assert [failure.index for failure in failures] == [0, 5]
    assert all(failure.error_type == "IllegibleTextMorph" for failure in failures)
    assert "Choose Two of Five" in failures[0].message
    assert "FadeTransform" in failures[0].message


def test_a_morph_nested_in_an_animation_group_is_still_found():
    """Wrapping the same bug in LaggedStart/AnimationGroup must not hide it."""
    failures = validate_scene(_TextMorphDeck)

    assert any(failure.segment == "segment_bad_morph_nested_in_a_group" for failure in failures)


def test_legible_text_swaps_are_not_flagged():
    """FadeTransform cross-dissolves, TransformMatchingTex glides shared
    terms, shape-to-shape interpolation is the whole point, and a couple of
    glyphs still read as "this becomes that". False positives here would
    train the author to ignore the check."""
    flagged = {failure.segment for failure in validate_scene(_TextMorphDeck)}

    assert "segment_fade_transform_is_fine" not in flagged
    assert "segment_matching_tex_is_fine" not in flagged
    assert "segment_shape_morph_is_fine" not in flagged
    assert "segment_tiny_number_is_fine" not in flagged


def test_glyph_count_not_source_length_decides_smallness():
    """`tex_string` is LaTeX source: `\\tfrac12` is eight characters but one
    small fraction on screen. Thresholding on source length would flag a
    perfectly readable morph."""
    from open_manim_slides.validate import _glyph_count

    assert _glyph_count(MathTex(r"\tfrac12")) <= 3


class _ConflictDeck(Slide):
    def construct(self) -> None:
        self.segment_fades_a_group_while_morphing_its_child()
        self.next_slide()
        self.segment_two_animations_on_separate_mobjects()
        self.next_slide()

    def segment_fades_a_group_while_morphing_its_child(self) -> None:
        keep, other = Square(), Square().shift(RIGHT * 3)
        group = VGroup(keep, other)
        self.add(group)
        self.play(FadeOut(group), Transform(keep, Circle()))

    def segment_two_animations_on_separate_mobjects(self) -> None:
        square, circle = Square(), Circle().shift(RIGHT * 3)
        self.add(square, circle)
        self.play(FadeOut(circle), Transform(square, Circle()))


def test_two_animations_driving_one_mobject_are_reported():
    """Manim can deadlock the encoder on this -- no traceback, no partial
    output, just a hung render. It cost a full render cycle to find by hand,
    and the harness cannot reproduce it (it applies animations one at a
    time), so it has to be detected structurally."""
    failures = validate_scene(_ConflictDeck)

    assert [failure.index for failure in failures] == [0]
    assert failures[0].error_type == "ConflictingAnimations"
    assert "FadeOut" in failures[0].message and "Transform" in failures[0].message


def test_animations_on_unrelated_mobjects_are_not_flagged():
    """Most plays animate several mobjects at once; flagging those would
    make the check useless."""
    flagged = {f.segment for f in validate_scene(_ConflictDeck)}

    assert "segment_two_animations_on_separate_mobjects" not in flagged


def test_conflict_detection_uses_family_membership_not_identity():
    """The arguments look distinct -- the clash is only visible because the
    group's family contains the child."""
    from open_manim_slides.validate import _conflicting_pairs

    child = Square()
    group = VGroup(child, Square().shift(RIGHT * 2))

    assert _conflicting_pairs([FadeOut(group), Transform(child, Circle())])
    assert not _conflicting_pairs([FadeOut(Circle()), Transform(child, Circle())])


def test_format_failures_announces_a_clean_deck():
    assert "layout OK" in format_failures([], "MyDeck")


def test_format_failures_explains_cascades_only_when_present():
    plain = [Failure(index=0, segment="segment_a", error_type="ValueError", message="boom")]
    assert "fix the first failure first" not in format_failures(plain, "D")

    with_cascade = [*plain, Failure(1, "segment_b", "AttributeError", "x", cascaded=True)]
    assert "fix the first failure first" in format_failures(with_cascade, "D")


def test_load_scene_class_rejects_a_missing_file(tmp_path: Path):
    with pytest.raises(ValidateError, match="No such deck file"):
        load_scene_class(tmp_path / "nope.py")


def test_load_scene_class_requires_a_slide_subclass(tmp_path: Path):
    path = tmp_path / "empty_deck.py"
    path.write_text("x = 1\n")

    with pytest.raises(ValidateError, match="No Slide subclass"):
        load_scene_class(path)


def test_load_scene_class_names_candidates_when_several_exist(tmp_path: Path):
    path = tmp_path / "two_decks.py"
    path.write_text(
        "from open_manim_slides import Slide\n"
        "class DeckA(Slide):\n    pass\n"
        "class DeckB(Slide):\n    pass\n"
    )

    with pytest.raises(ValidateError, match="DeckA"):
        load_scene_class(path)
    assert load_scene_class(path, "DeckB").__name__ == "DeckB"


def test_main_rejects_wrong_arg_count(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


class _TextOnDecorativeDeck(Slide):
    """Passes every other check: nothing overlaps, nothing leaves the frame."""

    def construct(self) -> None:
        self.segment_one()
        self.next_slide()

    def segment_one(self) -> None:
        from manim import LEFT, Line

        self.track(Line(LEFT * 3, RIGHT * 3), id="axis", decorative=True)
        self.track(Text("a caption", font_size=24), id="caption")
        self.assert_no_overlap_among_tracked()


class _EntrancesOnlyDeck(Slide):
    def construct(self) -> None:
        self.segment_open()
        self.next_slide()
        self.segment_more()
        self.next_slide()

    def segment_open(self) -> None:
        self.box = Square(side_length=1)
        self.play(FadeIn(self.box))

    def segment_more(self) -> None:
        self.play(FadeIn(Circle(radius=0.3).shift(RIGHT * 3)))


class _EmphasisOnlyDeck(_EntrancesOnlyDeck):
    def segment_more(self) -> None:
        self.play(Indicate(self.box))


class _ChangeDeck(_EntrancesOnlyDeck):
    def segment_more(self) -> None:
        self.play(self.box.animate.shift(RIGHT * 2))


class _AddedByTransformDeck(Slide):
    """The second segment can only see a change if the first segment's
    `Transform` put its mobject on screen, the way a real render does."""

    def construct(self) -> None:
        self.segment_stamp()
        self.next_slide()
        self.segment_move()
        self.next_slide()

    def segment_stamp(self) -> None:
        self.copy = Square(side_length=1)
        self.play(Transform(self.copy, Square(side_length=1).shift(RIGHT)))

    def segment_move(self) -> None:
        self.play(self.copy.animate.shift(LEFT))


class _UnperformedActionDeck(Slide):
    def construct(self) -> None:
        self.segment_open()
        self.next_slide()
        self.segment_promise()
        self.next_slide()

    def segment_open(self) -> None:
        self.caption = Text("start", font_size=24)
        self.shape = Square(side_length=1).shift(RIGHT * 3)
        self.play(FadeIn(self.caption), FadeIn(self.shape))

    def segment_promise(self) -> None:
        # The caption is replaced rather than morphed, because a `Transform`
        # between two strings leaves `original_text` reading the *old* one --
        # and is separately reported as an illegible morph anyway.
        self.remove(self.caption)
        self.caption = Text("the square rotates", font_size=24)
        self.add(self.caption)
        self.play(self.caption.animate.shift(UP * 0.5))


class _PerformedActionDeck(_UnperformedActionDeck):
    def segment_promise(self) -> None:
        self.remove(self.caption)
        self.caption = Text("the square rotates", font_size=24)
        self.add(self.caption)
        self.play(Rotate(self.shape, PI / 2))


def _types(failures: list[Failure]) -> list[str]:
    return [failure.error_type for failure in failures]


def test_text_on_a_decorative_element_is_reported():
    failures = validate_scene(_TextOnDecorativeDeck)

    assert _types(failures) == ["TextOnDecorative"]
    assert "caption" in failures[0].message and "axis" in failures[0].message


def test_a_segment_of_pure_entrances_is_reported():
    """R2, made countable. Nothing changes -- things only appear."""
    failures = validate_scene(_EntrancesOnlyDeck)

    assert _types(failures) == ["NoChangeAnimation"]
    assert failures[0].index == 1


def test_emphasis_does_not_satisfy_the_change_rule():
    """`Indicate` is a `Transform` subclass, so this only passes if the
    emphasis animations are excluded by class rather than by base class."""
    assert _types(validate_scene(_EmphasisOnlyDeck)) == ["NoChangeAnimation"]


def test_a_real_change_satisfies_the_rule():
    assert validate_scene(_ChangeDeck) == []


def test_the_opening_segment_is_exempt_from_the_change_rule():
    """A deck opens on a cleared frame; there is nothing there to change."""
    failures = validate_scene(_EntrancesOnlyDeck)

    assert all(failure.index != 0 for failure in failures)


def test_middle_school_demands_two_changes_per_segment():
    assert validate_scene(_ChangeDeck, audience="middle-school")[0].error_type == "NoChangeAnimation"
    assert validate_scene(_ChangeDeck, audience="high-school") == []


def test_a_transform_puts_its_mobject_on_screen_like_a_real_render():
    """`Scene.compile_animation_data` adds any animated mobject that isn't
    in the scene yet. Without that, the harness's scene graph drifts from
    the render's and every later on-screen test reads the wrong scene."""
    assert validate_scene(_AddedByTransformDeck) == []


def test_an_action_verb_with_nothing_but_text_animated_is_reported():
    failures = validate_scene(_UnperformedActionDeck)

    assert "UnperformedAction" in _types(failures)
    assert "rotates" in failures[-1].message


def test_an_action_verb_performed_by_a_figure_is_not_reported():
    assert validate_scene(_PerformedActionDeck) == []
