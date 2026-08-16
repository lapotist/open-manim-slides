"""Minimal layout/safety primitives.

Deliberately narrow scope for this pass: a margin-safety check, an
inter-element overlap check, and a composition-centering check.
Typography scale, color/theme tokens, and reusable slide templates are a
separate, later design pass -- not built here.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MARGIN: float = 0.5  # Manim units, applied on all four sides.
DEFAULT_CENTER_TOLERANCE: float = 0.2  # Fraction of half-frame width/height.


def _bbox(mobj: Any) -> tuple[float, float, float, float]:
    x_min, y_min, _ = mobj.get_corner(_direction(-1, -1))
    x_max, y_max, _ = mobj.get_corner(_direction(1, 1))
    return x_min, y_min, x_max, y_max


def assert_within_safe_frame(mobj: Any, margin: float = DEFAULT_MARGIN) -> Any:
    """Raise at construction time if `mobj` extends past the frame margins.

    Fails fast instead of silently overlapping/clipping -- catch a
    mis-placed element when it's written, not when someone notices a bad
    render later.
    """
    from manim import config

    half_width = config.frame_width / 2
    half_height = config.frame_height / 2
    left = -half_width + margin
    right = half_width - margin
    top = half_height - margin
    bottom = -half_height + margin

    x_min, y_min, x_max, y_max = _bbox(mobj)

    if x_min < left or x_max > right or y_min < bottom or y_max > top:
        raise ValueError(
            f"{mobj} extends outside the safe frame (margin={margin}): "
            f"x=[{x_min:.2f}, {x_max:.2f}] must be within [{left:.2f}, {right:.2f}], "
            f"y=[{y_min:.2f}, {y_max:.2f}] must be within [{bottom:.2f}, {top:.2f}]."
        )
    return mobj


def assert_no_overlap(*mobjects: Any) -> None:
    """Raise at construction time if any two of `mobjects` overlap.

    Same fail-fast philosophy as `assert_within_safe_frame`, but for
    collisions *between* elements rather than against the frame edge --
    the check that actually catches labels/shapes landing on top of each
    other (e.g. several `next_to(shared_center, RIGHT)` calls stacking up).
    Call it with every element that's simultaneously visible on screen,
    not just the newest one -- Manim elements persist once added, so a
    newly placed element can collide with anything still on screen from an
    earlier segment.
    """
    boxes = [(mobj, _bbox(mobj)) for mobj in mobjects]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            mobj_a, (ax0, ay0, ax1, ay1) = boxes[i]
            mobj_b, (bx0, by0, bx1, by1) = boxes[j]
            if ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0:
                raise ValueError(f"{mobj_a} overlaps {mobj_b}: x=[{ax0:.2f},{ax1:.2f}] vs [{bx0:.2f},{bx1:.2f}], y=[{ay0:.2f},{ay1:.2f}] vs [{by0:.2f},{by1:.2f}].")


def assert_reasonably_centered(*mobjects: Any, tolerance: float = DEFAULT_CENTER_TOLERANCE) -> None:
    """Raise if `mobjects`, combined, sit noticeably off-center in the frame.

    Neither `assert_within_safe_frame` nor `assert_no_overlap` catches a
    composition that's technically in-frame and non-overlapping but was
    never actually centered as a group -- e.g. a title left at its default
    position with more content stacked below it via `next_to`, which
    quietly pushes the combined bounding box's center well below the
    frame's true center and leaves the top conspicuously, asymmetrically
    empty. This computes the union bounding box of all `mobjects` and
    checks that its center is within `tolerance` (as a fraction of the
    frame's half-width/half-height) of the frame's own center.

    Deliberately *not* wired into every scaffolded segment the way
    `assert_no_overlap_among_tracked` is -- a diagram-plus-caption
    composition naturally sits somewhat off from dead-center and that's
    fine, so this is for the author to call where centering actually
    matters (a title, a summary, a boxed final result), not a blanket
    per-segment check. See `Slide.assert_reasonably_centered_among_tracked`
    for the tracked-element convenience wrapper.
    """
    from manim import config

    x_mins, y_mins, x_maxs, y_maxs = zip(*(_bbox(mobj) for mobj in mobjects), strict=True)
    x_min, y_min, x_max, y_max = min(x_mins), min(y_mins), max(x_maxs), max(y_maxs)
    center_x, center_y = (x_min + x_max) / 2, (y_min + y_max) / 2

    dx_frac = abs(center_x) / (config.frame_width / 2)
    dy_frac = abs(center_y) / (config.frame_height / 2)

    if dx_frac > tolerance or dy_frac > tolerance:
        raise ValueError(
            f"Combined bounding box of {mobjects!r} is off-center "
            f"(dx={dx_frac:.2f}, dy={dy_frac:.2f} as a fraction of half-frame, "
            f"tolerance={tolerance}): center=({center_x:.2f}, {center_y:.2f}). "
            "Recenter the group as a whole, e.g. `group.move_to(ORIGIN)`, "
            "rather than leaving it wherever its first element happened to land."
        )


def _direction(x: float, y: float) -> Any:
    import numpy as np

    return np.array([x, y, 0.0])
