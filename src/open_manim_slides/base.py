"""Base Slide class: segment-boundary manifest capture + transition-flash fix.

NOTE: manim-slides isn't installed in this environment yet (blocked on a
system dependency), so the exact `Slide.next_slide()` signature and the
`wait_time_between_slides` attribute name below are written from
documentation knowledge, not verified against an importable package. Recheck
both against the installed `manim_slides` source once available.
"""

from __future__ import annotations

import inspect
import json
import logging
import pathlib
from typing import Any

from manim import config
from manim_slides import Slide as _BaseSlide

logger = logging.getLogger(__name__)

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent


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


class Slide(_BaseSlide):
    """Framework base class: fixes the segment-transition flash and records
    an ID-addressable manifest of tracked elements for the (not-yet-built)
    review site.
    """

    # manim-slides defaults this to 0, which cuts each clip one frame short
    # of settling and causes a visible flash on every segment transition.
    wait_time_between_slides: float = 0.15

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._manifest: dict[str, dict[str, Any]] = {}
        self._segment_index: int = 0
        self._segment_tracked_ids: set[str] = set()
        self._pending_snapshot: dict[str, Any] = {}

    def track(self, mobj: Any, id: str) -> Any:  # noqa: A002 - matches the design's `id=` kwarg
        """Tag `mobj` with a stable, human-meaningful id for the manifest.

        Raises if `id` was already used earlier in the *same* segment (almost
        certainly a copy-paste mistake). Reusing an id in a *later* segment is
        expected -- it means "this element persists or reappears" -- and is
        allowed.
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
                "source": _caller_location(),
                "appearances": [],
            }
        self._pending_snapshot[id] = mobj
        return mobj

    def next_slide(self, *args: Any, **kwargs: Any) -> None:
        # Order is load-bearing: snapshot before advancing, since advancing
        # is what triggers manim-slides' own transition/wait effects, which
        # can move or hide tracked elements before they've been recorded.
        self._snapshot_segment()
        super().next_slide(*args, **kwargs)

    def _snapshot_segment(self) -> None:
        for id, mobj in self._pending_snapshot.items():
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
        self._pending_snapshot.clear()

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
