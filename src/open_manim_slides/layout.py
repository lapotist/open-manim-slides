"""Minimal layout/safety primitives.

Deliberately narrow scope for this pass: one margin-safety check. Typography
scale, color/theme tokens, and reusable slide templates are a separate,
later design pass -- not built here.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MARGIN: float = 0.5  # Manim units, applied on all four sides.


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

    x_min, y_min, _ = mobj.get_corner(_direction(-1, -1))
    x_max, y_max, _ = mobj.get_corner(_direction(1, 1))

    if x_min < left or x_max > right or y_min < bottom or y_max > top:
        raise ValueError(
            f"{mobj} extends outside the safe frame (margin={margin}): "
            f"x=[{x_min:.2f}, {x_max:.2f}] must be within [{left:.2f}, {right:.2f}], "
            f"y=[{y_min:.2f}, {y_max:.2f}] must be within [{bottom:.2f}, {top:.2f}]."
        )
    return mobj


def _direction(x: float, y: float) -> Any:
    import numpy as np

    return np.array([x, y, 0.0])
