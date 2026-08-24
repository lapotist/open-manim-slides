"""Headless layout validation — run every check without rendering video.

The framework's guarantees (`assert_within_safe_frame`,
`assert_no_overlap_among_tracked`, `assert_reasonably_centered_among_tracked`,
duplicate-id detection) all fire during `construct()`. But `construct()` is
normally only reached by rendering, so the cheapest way to learn that a
brace overhangs the frame has been to encode ~9 seconds of video and read
the traceback. Worse, a render aborts on the *first* failure, so N
independent placement mistakes cost N full render cycles — measured at 5
cycles and ~8 minutes on this repo's own trig deck, for five errors that
are all arithmetic.

This runs the same `construct()` with two substitutions:

- **`play()` applies each animation's end state instantly** — begin,
  interpolate to 1.0, finish, clean up — so mobject geometry after the
  call is what a real render would produce, without a single frame being
  drawn. Scene updaters are then run once, because `always_redraw`
  mobjects only regenerate when the scene ticks, and a later segment
  reading their geometry (`leg.get_start()`) would otherwise see a stale
  pose.
- **`next_slide()` only snapshots the segment**, skipping manim-slides'
  file bookkeeping, which needs rendered video that does not exist here.
  The snapshot is kept because it advances the segment index and clears
  the per-segment id set, which is what makes duplicate-id detection work.

Each `segment_*` method is wrapped so a failure is recorded and the run
continues to the next segment. That is the point: one pass reports every
broken segment. The caveat is real and reported — segments hand state to
each other through `self.<attr>`, so a failure can cascade into the
segments after it. Failures that look like cascades (a missing attribute
the failed segment was supposed to set) are marked as such.

Usage: `python -m open_manim_slides.validate decks/<slug>.py [ClassName]`
"""

from __future__ import annotations

import importlib.util
import re
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ValidateError(RuntimeError):
    """A validation-harness failure with a user-facing message."""


@dataclass(frozen=True)
class Failure:
    """One segment that raised during headless construction."""

    index: int
    segment: str
    error_type: str
    message: str
    cascaded: bool = False

    def format(self) -> str:
        mark = "  (likely a cascade of an earlier failure)" if self.cascaded else ""
        return f"seg-{self.index:02d} {self.segment}: {self.error_type}: {self.message}{mark}"


def _text_content(mobject: Any) -> str | None:
    """The string a text mobject renders, or None if it isn't one.

    `original_text` first: manim strips spaces out of `Text.text` for its
    glyph mapping, which would render the message as 'CountingThings'.
    """
    for attr in ("original_text", "text", "tex_string"):
        value = getattr(mobject, attr, None)
        if isinstance(value, str):
            return value
    return None


def _glyph_count(mobject: Any) -> int:
    """How many drawable shapes the morph actually has to interpolate.

    Counted, not measured off the string: `tex_string` is LaTeX *source*,
    so `\\tfrac12` is eight characters but renders as one small fraction.
    Thresholding on source length flags that as unreadable, which it
    plainly is not.
    """
    try:
        return len(mobject.family_members_with_points())
    except Exception:  # noqa: BLE001 - a mobject that can't be walked isn't text
        return 0


# A morph between a few glyphs ("1" -> "½", "2" -> "-2", "2<5" -> "-2<0")
# reads as "this becomes that" and is over in a moment. Past that there is
# no correspondence left to interpolate and the midpoint is mush. Biased
# toward under-reporting, like blankspace's thresholds: what this flags
# should be worth fixing every time.
_MORPH_GLYPH_ALLOWANCE = 3


def _text_morphs(animation: Any) -> list[tuple[str, str]]:
    """Every plain `Transform` between two different multi-character strings.

    `Transform` interpolates glyph *outlines*, so swapping a heading or a
    caption for different words spends most of the play unreadable
    (`Ch⊃∂s A T'w? 3f£!vG`). It is invisible to every other check here --
    and to a final-frame review, the one moment nothing is moving -- which
    is exactly why it belongs in a mechanical gate rather than a checklist.

    Deliberately *not* flagged: `FadeTransform` (cross-dissolves, both
    strings stay legible), `TransformMatchingTex` (an `AnimationGroup`, so
    it never matches the isinstance below), `.animate` chains (source and
    target render the same string), and shape-to-shape transforms such as
    `NumberLine` -> `NumberLine`, where interpolation is the whole point.
    """
    from manim import FadeTransform, Transform

    nested = getattr(animation, "animations", None)
    if nested:
        return [morph for child in nested for morph in _text_morphs(child)]

    if not isinstance(animation, Transform) or isinstance(animation, FadeTransform):
        return []
    target_mobject = getattr(animation, "target_mobject", None)
    source = _text_content(animation.mobject)
    target = _text_content(target_mobject)
    if source is None or target is None or source == target:
        return []
    if max(_glyph_count(animation.mobject), _glyph_count(target_mobject)) <= _MORPH_GLYPH_ALLOWANCE:
        return []
    return [(source, target)]


def _conflicting_pairs(animations: list[Any]) -> list[tuple[str, str]]:
    """Animations in one `play()` that target the same mobject.

    Two animations mutating one mobject in a single play is not a race the
    renderer resolves -- in manim 0.20 it can deadlock the encoder outright,
    with no traceback and no partial output. The usual shape is fading a
    group while transforming one of its own children:

        self.play(FadeOut(figure), Transform(figure_child, target))

    Family membership is what catches it: `figure`'s family contains
    `figure_child`, so the two animations overlap even though the arguments
    look distinct. Compared only across the *top-level* arguments, because
    an `AnimationGroup`/`LaggedStart` legitimately drives many mobjects.
    """
    families: list[tuple[Any, set[int]]] = []
    for animation in animations:
        try:
            family = {id(part) for part in animation.mobject.get_family()}
        except Exception:  # noqa: BLE001 - an animation without a mobject can't clash
            family = set()
        families.append((animation, family))

    clashes: list[tuple[str, str]] = []
    for index, (first, first_family) in enumerate(families):
        for second, second_family in families[index + 1 :]:
            if first_family & second_family:
                clashes.append((type(first).__name__, type(second).__name__))
    return clashes


def _instant_play(scene: Any, on_text_morph: Any = None, on_conflict: Any = None) -> Any:
    """A `play()` that jumps straight to each animation's final state."""
    from manim.animation.animation import prepare_animation

    def play(*args: Any, **kwargs: Any) -> None:  # noqa: ARG001 - run_time etc. are irrelevant at t=1
        prepared = [prepare_animation(arg) for arg in args]
        if on_conflict is not None:
            for first, second in _conflicting_pairs(prepared):
                on_conflict(first, second)
        for animation in prepared:
            if on_text_morph is not None:
                for source, target in _text_morphs(animation):
                    on_text_morph(source, target)
            animation._setup_scene(scene)
            animation.begin()
            animation.interpolate(1.0)
            animation.finish()
            animation.clean_up_from_scene(scene)
        # always_redraw / TracedPath mobjects only regenerate when the
        # scene ticks. Without this, a later segment reading their geometry
        # sees the pose from before this play.
        scene.update_mobjects(0)

    return play


def _failure_signature(error: BaseException, message: str) -> tuple[str, Any]:
    """Identify the *situation* a failure describes, not its wording.

    Keyed on the error type plus the set of coordinates in the message,
    because the same geometric problem can be phrased differently in
    different segments -- `assert_no_overlap` reports whichever of the
    pair it reaches first, so one unresolved collision surfaces as both
    "A overlaps B" and "B overlaps A". Comparing numbers sees through that.
    """
    numbers = frozenset(re.findall(r"-?\d+\.\d+", message))
    return (type(error).__name__, numbers or message)


def _looks_like_cascade(error: BaseException, signature: tuple[str, Any], seen: set[tuple[str, Any]]) -> bool:
    """True when this failure is most likely downstream of an earlier one.

    Two signatures, both common:
    - `AttributeError` — a segment that failed never set the `self.<attr>`
      the next one reads.
    - a situation already reported — an element left in a bad position
      keeps failing the same check in *every* later segment, since the
      framework considers it on screen until something removes it. Without
      this, one unresolved overlap buries the real errors under N repeats.
    """
    return isinstance(error, AttributeError) or signature in seen


def validate_scene(scene_class: type) -> list[Failure]:
    """Run `scene_class.construct()` headlessly; return every segment failure."""
    scene = scene_class()
    failures: list[Failure] = []
    morphs: list[Failure] = []
    current: dict[str, Any] = {"index": 0, "name": "construct"}
    seen: set[tuple[str, Any]] = set()

    def note_morph(source: str, target: str) -> None:
        morphs.append(
            Failure(
                index=current["index"],
                segment=current["name"],
                error_type="IllegibleTextMorph",
                message=(
                    f"Transform() morphs {source!r} into {target!r} -- glyph outlines "
                    "interpolate into unreadable shapes for most of the play. Use "
                    "FadeTransform and re-track the id (it replaces the mobject rather "
                    "than mutating it), or TransformMatchingTex for MathTex."
                ),
            )
        )

    def note_conflict(first: str, second: str) -> None:
        morphs.append(
            Failure(
                index=current["index"],
                segment=current["name"],
                error_type="ConflictingAnimations",
                message=(
                    f"{first} and {second} in one play() drive the same mobject "
                    "(one's family contains the other's). Manim can deadlock on "
                    "this with no traceback. Split them across two plays, or take "
                    "the shared mobject out of the group first."
                ),
            )
        )

    scene.play = _instant_play(scene, note_morph, note_conflict)
    # Snapshot only: advancing the segment index and clearing the
    # per-segment id set is what keeps duplicate-id detection honest.
    scene.next_slide = lambda *a, **k: scene._snapshot_segment()  # noqa: ARG005

    def wrap(name: str, method: Any) -> Any:
        def wrapped(*args: Any, **kwargs: Any) -> None:
            index = current["index"]
            current["name"] = name
            try:
                method(*args, **kwargs)
            except Exception as error:  # noqa: BLE001 - reporting, not handling
                message = str(error).strip().replace("\n", " ")
                signature = _failure_signature(error, message)
                failures.append(
                    Failure(
                        index=index,
                        segment=name,
                        error_type=type(error).__name__,
                        message=message,
                        cascaded=bool(failures) and _looks_like_cascade(error, signature, seen),
                    )
                )
                seen.add(signature)
            finally:
                # After, not before: morphs recorded *during* the segment
                # must carry that segment's own index.
                current["index"] = index + 1

        return wrapped

    for name in dir(scene_class):
        if name.startswith("segment_"):
            setattr(scene, name, wrap(name, getattr(scene, name)))

    try:
        scene.construct()
    except Exception as error:  # noqa: BLE001 - construct() itself broke, not a segment
        failures.append(
            Failure(
                index=current["index"],
                segment="construct",
                error_type=type(error).__name__,
                message=f"{error}\n{traceback.format_exc(limit=3)}".strip().replace("\n", " "),
            )
        )
    # Sorted by segment so the report reads in playback order; morphs are
    # never cascades -- each one is independently wrong.
    return sorted(failures + morphs, key=lambda failure: failure.index)


def quiet_manim_logging() -> None:
    """Silence manim's per-asset chatter.

    Importing a deck compiles its `MathTex`, and manim logs a paragraph per
    TeX file. That noise would swamp the failure list this tool exists to
    print -- and, when an agent reads the output, it costs far more than
    the signal it buries.
    """
    import logging

    logging.getLogger("manim").setLevel(logging.ERROR)


def load_scene_class(path: Path, class_name: str | None = None) -> type:
    """Import a deck file and return its Slide subclass."""
    from open_manim_slides.base import Slide

    if not path.is_file():
        raise ValidateError(f"No such deck file: {path}")

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValidateError(f"Could not import {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)

    candidates = [
        value
        for value in vars(module).values()
        if isinstance(value, type) and issubclass(value, Slide) and value is not Slide
    ]
    if class_name is not None:
        for candidate in candidates:
            if candidate.__name__ == class_name:
                return candidate
        found = ", ".join(c.__name__ for c in candidates) or "none"
        raise ValidateError(f"No Slide subclass named {class_name!r} in {path} (found: {found}).")
    if not candidates:
        raise ValidateError(f"No Slide subclass found in {path}.")
    if len(candidates) > 1:
        names = ", ".join(c.__name__ for c in candidates)
        raise ValidateError(f"Several Slide subclasses in {path} ({names}) -- name one explicitly.")
    return candidates[0]


def format_failures(failures: list[Failure], scene_name: str) -> str:
    if not failures:
        return f"{scene_name}: layout OK -- all segments constructed, every check passed."
    lines = [f"{scene_name}: {len(failures)} segment(s) failed", ""]
    lines.extend("  " + failure.format() for failure in failures)
    if any(failure.cascaded for failure in failures):
        lines.append("")
        lines.append("  Segments hand state to each other, so fix the first failure first;")
        lines.append("  the marked ones may disappear with it.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not 1 <= len(args) <= 2:
        print("usage: python -m open_manim_slides.validate <deck.py> [ClassName]", file=sys.stderr)
        return 2
    quiet_manim_logging()
    try:
        scene_class = load_scene_class(Path(args[0]), args[1] if len(args) == 2 else None)
        failures = validate_scene(scene_class)
    except ValidateError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(format_failures(failures, scene_class.__name__))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
