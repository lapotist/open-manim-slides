"""Minimal layout/safety primitives.

Deliberately narrow scope for this pass: a margin-safety check and an
inter-element overlap check. Typography scale, color/theme tokens, and
reusable slide templates are a separate, later design pass -- not built
here.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MARGIN: float = 0.5  # Manim units, applied on all four sides.


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


def _direction(x: float, y: float) -> Any:
    import numpy as np

    return np.array([x, y, 0.0])
