"""Base Slide class: segment-boundary manifest capture + transition-flash fix.

Verified against installed `manim_slides` 5.6.0. Notably,
`wait_time_between_slides` is a `@property` (getter/setter, clamped to
`>= 0`) backed by a private `_wait_time_between_slides`, not a plain
attribute -- `Slide.__init__` below sets it *through* the property rather
than shadowing it with a class attribute. A shadowing class attribute would
silently defeat the property's setter for anyone who later does
`self.wait_time_between_slides = ...` inside their own `construct()`, which
is exactly the pattern manim-slides' own docs demonstrate.
"""

from __future__ import annotations

import inspect
import json
import logging
import pathlib
from typing import Any

from manim import config
from manim_slides import Slide as _BaseSlide

from open_manim_slides.layout import (
    DEFAULT_INK_CLEARANCE,
    assert_no_overlap,
    assert_reasonably_centered,
    find_text_over_ink,
    text_content,
)

logger = logging.getLogger(__name__)

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent

# manim-slides defaults this to 0, which cuts each clip one frame short of
# settling and causes a visible flash on every segment transition.
DEFAULT_WAIT_TIME_BETWEEN_SLIDES: float = 0.15


def _caller_location() -> dict[str, Any] | None:
    """Find the first stack frame outside this package -- the user's call site."""
    for frame_info in inspect.stack()[1:]:
        path = pathlib.Path(frame_info.filename).resolve()
        try:
            path.relative_to(_PACKAGE_DIR)
        except ValueError:
            return {"file": str(path), "line": frame_info.lineno}
    return None


def _normalized_bbox(mobj: Any) -> list[float] | None:
    """Bounding box in 0-1, top-left-origin fractions of the render frame."""
    from manim import DR, UL

    frame_width = config.frame_width
    frame_height = config.frame_height
    top_left = mobj.get_corner(UL)
    bottom_right = mobj.get_corner(DR)
    x_min = (top_left[0] + frame_width / 2) / frame_width
    y_min = (frame_height / 2 - top_left[1]) / frame_height
    x_max = (bottom_right[0] + frame_width / 2) / frame_width
    y_max = (frame_height / 2 - bottom_right[1]) / frame_height
    return [x_min, y_min, x_max, y_max]


def _removal_covers(removed: Any, tracked: Any) -> bool:
    """Would removing `removed` (as passed to `Scene.remove`) take `tracked` off screen?

    `removed` may itself be a transient group (e.g. `FadeOut(a, b)` wraps
    `a`/`b` in a `Group` before handing it to `Scene.remove`), so checking
    family membership rather than identity is what makes this correct for
    the common multi-mobject fade-out case.
    """
    try:
        return tracked is removed or tracked in removed.get_family()
    except Exception:
        return tracked is removed


def _text_parts(mobj: Any) -> Any:
    """Every text mobject at or under `mobj`, without descending into glyphs."""
    if text_content(mobj) is not None:
        yield mobj
        return
    for child in getattr(mobj, "submobjects", ()):
        yield from _text_parts(child)


class Slide(_BaseSlide):
    """Framework base class: fixes the segment-transition flash and records
    an ID-addressable manifest of tracked elements for the (not-yet-built)
    review site.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.wait_time_between_slides = DEFAULT_WAIT_TIME_BETWEEN_SLIDES
        self._manifest: dict[str, dict[str, Any]] = {}
        self._segment_index: int = 0
        self._segment_tracked_ids: set[str] = set()
        self._tracked_mobjects: dict[str, Any] = {}
        self._active_ids: set[str] = set()

    def track(self, mobj: Any, id: str, *, decorative: bool = False) -> Any:  # noqa: A002 - matches the design's `id=` kwarg
        """Tag `mobj` with a stable, human-meaningful id for the manifest.

        Raises if `id` was already used earlier in the *same* segment (almost
        certainly a copy-paste mistake). Reusing an id in a *later* segment is
        expected -- it means "this element persists or reappears" -- and is
        allowed.

        `decorative=True` marks structural/backdrop content (a coordinate
        axis, a guide circle, an angle-arc indicator) that's still worth
        recording in the manifest but shouldn't participate in
        `assert_no_overlap_among_tracked()`'s pairwise check. This exists
        because a bounding-box overlap test is a poor proxy for curved or
        diagonal shapes -- a point or line anywhere on/inside a circle
        centered at C with radius R always has coordinates within
        `[C-R, C+R]` on both axes, i.e. within the circle's own bounding
        box, so tracking a circle alongside anything radiating from its
        center false-positives at every angle. Prefer this over leaving an
        element untracked entirely: it keeps the element addressable for
        the future review site while still opting it out of the check.
        """
        if id in self._segment_tracked_ids:
            raise ValueError(
                f"track(id={id!r}) was already used in this segment. "
                "Reusing an id within the same segment is almost always a "
                "mistake; reuse across different segments is fine."
            )
        self._segment_tracked_ids.add(id)

        if id not in self._manifest:
            self._manifest[id] = {
                "id": id,
                "label": id,
                "decorative": decorative,
                "source": _caller_location(),
                "appearances": [],
            }
        self._tracked_mobjects[id] = mobj
        self._active_ids.add(id)
        return mobj

    def remove(self, *mobjects: Any) -> None:
        """Deactivate tracked ids whose mobject is taken off screen.

        Manim mobjects persist once added until explicitly removed --
        directly, or via a `remover`-flagged animation like `FadeOut`, which
        routes through this same `Scene.remove` at the end of the animation
        (see `Animation.clean_up_from_scene`). Overriding it here is what
        lets `_snapshot_segment` know an id has actually left the scene,
        instead of only ever recording an appearance for the single segment
        `track()` happened to be called in.
        """
        super().remove(*mobjects)
        for id in list(self._active_ids):
            tracked = self._tracked_mobjects.get(id)
            if any(_removal_covers(removed, tracked) for removed in mobjects):
                self._active_ids.discard(id)

    def assert_no_overlap_among_tracked(self) -> None:
        """Check every currently-active, non-decorative tracked element pairwise for overlap.

        Convenience wrapper around `layout.assert_no_overlap` that gathers
        every id still active (tracked and not yet removed) instead of
        requiring an explicit list. Call at the end of a segment, once all
        of that segment's elements have been placed.

        Ids tracked with `track(..., decorative=True)` are excluded from
        both sides of the comparison -- see `track()`'s docstring for why.
        """
        checked_ids = (id for id in self._active_ids if not self._manifest[id]["decorative"])
        assert_no_overlap(*(self._tracked_mobjects[id] for id in checked_ids))

    def find_text_over_decorative(
        self, clearance: float = DEFAULT_INK_CLEARANCE
    ) -> list[tuple[str, str]]:
        """Tracked text sitting on a tracked `decorative` element's strokes.

        Returns `(text_id, decorative_id)` pairs; reports rather than raises,
        because the caller (`validate.py`) lists every finding in one pass.

        This is the one recurrence that no other check's scope spans:
        `assert_no_overlap_among_tracked` drops `decorative` ids from *both*
        sides, and `assert_within_safe_frame` only ever sees one element, so
        a caption crossing an axis's tick numbers (session fourteen) or a
        heading grazing a decorative square (session eight) passes
        everything and is still wrong on screen.

        Text is found by descending into tracked groups, since a caption is
        as often a group's child as a tracked mobject in its own right.
        """
        texts: list[tuple[str, Any]] = []
        decoratives: list[tuple[str, Any]] = []
        for id in self._active_ids:
            mobj = self._tracked_mobjects[id]
            if self._manifest[id]["decorative"]:
                decoratives.append((id, mobj))
            else:
                texts.extend((id, part) for part in _text_parts(mobj))

        findings: list[tuple[str, str]] = []
        for text_id, text in texts:
            for decorative_id, decorative in decoratives:
                if find_text_over_ink([text], [decorative], clearance=clearance):
                    findings.append((text_id, decorative_id))
        # One pair per id pair: a group with three labels on one axis is one
        # placement mistake, not three.
        return sorted(set(findings))

    def assert_reasonably_centered_among_tracked(self, tolerance: float | None = None) -> None:
        """Check every currently-active tracked element, combined, for off-center composition.

        Convenience wrapper around `layout.assert_reasonably_centered` that
        gathers every id still active instead of requiring an explicit
        list. Unlike `assert_no_overlap_among_tracked`, `decorative` ids are
        *not* excluded here -- a decorative backdrop (a diagram, a guide
        circle) still occupies real visual space and should count toward
        whether the overall composition reads as centered.

        Not called automatically by scaffolded segments -- call it
        yourself for slides where centering matters (a title, a summary, a
        boxed final result), not diagram-heavy segments that naturally sit
        somewhat off from dead-center.
        """
        mobjects = (self._tracked_mobjects[id] for id in self._active_ids)
        if tolerance is None:
            assert_reasonably_centered(*mobjects)
        else:
            assert_reasonably_centered(*mobjects, tolerance=tolerance)

    def next_slide(self, *args: Any, **kwargs: Any) -> None:
        # Order is load-bearing: snapshot before advancing, since advancing
        # is what triggers manim-slides' own transition/wait effects, which
        # can move or hide tracked elements before they've been recorded.
        self._snapshot_segment()
        super().next_slide(*args, **kwargs)

    def _snapshot_segment(self) -> None:
        for id in self._active_ids:
            mobj = self._tracked_mobjects[id]
            try:
                bbox = _normalized_bbox(mobj)
            except Exception:
                logger.warning("Failed to compute bbox for track(id=%r); skipping.", id, exc_info=True)
                bbox = None
            # start_time/end_time are deliberately omitted here -- they only
            # exist after manim-slides renders and writes its own per-segment
            # timing JSON. Backfilling them is a post-render merge step, not
            # yet built (out of scope for this pass).
            self._manifest[id]["appearances"].append({"segment": self._segment_index, "bbox": bbox})

        self._segment_index += 1
        self._segment_tracked_ids.clear()

    def render(self, *args: Any, **kwargs: Any) -> Any:
        result = super().render(*args, **kwargs)
        self._write_manifest()
        return result

    def _write_manifest(self) -> None:
        if not self._manifest:
            return
        out_path = pathlib.Path(config.media_dir) / f"{type(self).__name__}.manifest.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "deck": type(self).__name__,
            "frame_width": config.frame_width,
            "frame_height": config.frame_height,
            "elements": list(self._manifest.values()),
        }
        out_path.write_text(json.dumps(payload, indent=2))
