"""Dead-space detector for rendered decks.

Answers the review question `frames.py` can only pose: *is a region of the
frame empty, and does it stay empty?* A slide with one quiet corner is
fine -- a deck whose right third is never used by any segment is a layout
that was never designed, and that is the failure this measures.

Three deliberate design choices, each because the obvious alternative is
wrong:

- **Pixels, not bounding boxes.** The manifest already records a bbox per
  tracked element, which would be cheaper to read -- but a bbox
  *overstates* coverage. A triangle's bbox claims its two empty corners; a
  diagonal line's bbox claims a whole rectangle. Measuring dead space from
  bboxes would therefore under-report exactly the emptiness worth finding.
  The rendered PNG is ground truth about what the audience sees.
- **Across segments, not per frame.** Empty space that later fills up was
  reserved, not wasted. A cell only counts as dead when *no* segment ever
  puts content in it, so deliberately-staged layouts don't get flagged.
- **Inside the safe frame only.** The 0.5-unit margin
  (`layout.DEFAULT_MARGIN`) is supposed to be empty; including it would
  report a dead border on every well-built deck.

Occupancy is coarse by construction: a 16x9 grid over the safe area, one
cell roughly a word wide. A cell counts as occupied on very little ink
(`MIN_CELL_FILL`), which biases the tool toward *under*-reporting dead
space -- a region this calls dead is one nothing reached at all.

Reads the `seg-NN-final.png` stills `frames.py` writes, so run that first.

Known limits, so the numbers aren't over-read:

- **It samples each segment's final frame only.** Space a mobject sweeps
  through mid-animation but doesn't end in reads as unused. A
  `ValueTracker` segment is the clearest case: only the end pose counts.
- **Fill % is cell reach, not ink density.** A cell counts as occupied on
  a trace of content, so 50% fill means half the cells hold *something*,
  nowhere near half the pixels painted.
- **It measures reach, not composition.** Scattered specks score like a
  designed layout, and deliberate negative space around a focal point
  scores like waste. Use it to find space nothing claims, not to grade
  taste.
- **Background is the frame's modal color**, so a full-bleed fill larger
  than the background would invert the content test.

Usage: `python -m open_manim_slides.blankspace <SceneName>` from the repo
root.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from open_manim_slides.frames import REVIEW_DIR, SLIDES_DIR

GRID_COLS = 16
GRID_ROWS = 9

# A pixel counts as content when any channel differs from the background
# by more than this (0-255). Low on purpose: faint fills (the decks use
# fill_opacity as low as 0.12) are real content, and the PNGs are lossless
# so there is no compression noise to reject.
CONTENT_DELTA = 10

# Fraction of a cell's pixels that must be content for the cell to count as
# occupied. ~0.5% is a few dozen pixels -- roughly a thin stroke clipping a
# corner. Small so that "dead" means genuinely untouched.
MIN_CELL_FILL = 0.005

# Report a never-used region only once it is worth restructuring for.
MIN_REPORTABLE_DEAD_FRACTION = 0.08

# Below this, a segment's final frame is mostly background.
SPARSE_SEGMENT_FILL = 0.15


class BlankSpaceError(RuntimeError):
    """A dead-space analysis failure with a user-facing message."""


@dataclass(frozen=True)
class Rect:
    """A cell-space rectangle, inclusive on both ends."""

    row0: int
    col0: int
    row1: int
    col1: int

    @property
    def cells(self) -> int:
        return (self.row1 - self.row0 + 1) * (self.col1 - self.col0 + 1)

    def fraction_of(self, rows: int, cols: int) -> float:
        return self.cells / (rows * cols)

    def describe(self, rows: int, cols: int) -> str:
        """Name the region the way a person would point at it."""
        mid_col = (self.col0 + self.col1) / 2
        mid_row = (self.row0 + self.row1) / 2
        spans_width = self.col1 - self.col0 + 1 >= cols * 0.8
        spans_height = self.row1 - self.row0 + 1 >= rows * 0.8

        horizontal = "left" if mid_col < cols / 3 else "right" if mid_col > 2 * cols / 3 else "center"
        vertical = "top" if mid_row < rows / 3 else "bottom" if mid_row > 2 * rows / 3 else "middle"

        if spans_width and spans_height:
            return "the whole frame"
        if spans_height:
            return f"the {horizontal} side, full height"
        if spans_width:
            return f"the {vertical} band, full width"
        return f"{vertical}-{horizontal}"


@dataclass(frozen=True)
class SegmentOccupancy:
    index: int
    grid: np.ndarray  # bool[rows, cols], True = has content

    @property
    def fill(self) -> float:
        return float(self.grid.mean())


@dataclass(frozen=True)
class Report:
    scene: str
    segments: list[SegmentOccupancy]
    ever_used: np.ndarray  # bool[rows, cols]
    # True when the deck was re-rendered after these stills were extracted,
    # i.e. the numbers describe a version of the deck that no longer
    # exists. Silent staleness is the likeliest way to trust a wrong
    # measurement, since the edit-render-measure loop invites exactly it.
    stale: bool = False

    @property
    def dead_fraction(self) -> float:
        return float((~self.ever_used).mean())

    @property
    def largest_dead(self) -> Rect | None:
        return largest_empty_rect(self.ever_used)

    @property
    def sparse_segments(self) -> list[SegmentOccupancy]:
        return [seg for seg in self.segments if seg.fill < SPARSE_SEGMENT_FILL]


def background_color(pixels: np.ndarray) -> np.ndarray:
    """The frame's background, taken as its most common color.

    Not hardcoded to black: `theme.COLOR_BACKGROUND` is a token a deck can
    change, and slide-like content is overwhelmingly background by area, so
    the mode is both robust and cheap.
    """
    flat = pixels.reshape(-1, pixels.shape[-1])
    # Pack each RGB triple into one integer so `unique` counts whole colors
    # rather than per-channel values.
    packed = (flat[:, 0].astype(np.int64) << 16) | (flat[:, 1].astype(np.int64) << 8) | flat[:, 2].astype(np.int64)
    values, counts = np.unique(packed, return_counts=True)
    winner = int(values[counts.argmax()])
    return np.array([(winner >> 16) & 255, (winner >> 8) & 255, winner & 255], dtype=np.int64)


def occupancy_grid(
    pixels: np.ndarray,
    *,
    rows: int = GRID_ROWS,
    cols: int = GRID_COLS,
    margin_x: float = 0.0,
    margin_y: float = 0.0,
    content_delta: int = CONTENT_DELTA,
    min_cell_fill: float = MIN_CELL_FILL,
) -> np.ndarray:
    """Reduce an RGB frame to a bool grid of which cells hold content.

    `margin_x`/`margin_y` crop that fraction off each side before gridding,
    so the safe frame's deliberately-empty border doesn't register as dead
    space. They are separate because the safe margin is a fixed number of
    Manim units on a frame that is not square: 0.5 of 14.22 across but 0.5
    of 8 down, so one shared value leaves a quarter of the top and bottom
    rows measuring known-empty margin and reports it as dead.
    """
    if pixels.ndim != 3 or pixels.shape[-1] < 3:
        raise BlankSpaceError(f"Expected an RGB image array, got shape {pixels.shape}.")
    pixels = pixels[:, :, :3].astype(np.int64)

    height, width = pixels.shape[:2]
    top, left = int(round(height * margin_y)), int(round(width * margin_x))
    cropped = pixels[top : height - top, left : width - left]

    content = np.abs(cropped - background_color(pixels)).max(axis=-1) > content_delta

    # Integer-split the crop into cells; np.array_split handles the
    # remainder when the pixel dimensions don't divide evenly.
    grid = np.zeros((rows, cols), dtype=bool)
    for r, row_block in enumerate(np.array_split(content, rows, axis=0)):
        for c, cell in enumerate(np.array_split(row_block, cols, axis=1)):
            grid[r, c] = cell.size > 0 and cell.mean() >= min_cell_fill
    return grid


def largest_empty_rect(occupied: np.ndarray) -> Rect | None:
    """Largest axis-aligned rectangle containing no occupied cell.

    Standard maximal-rectangle-in-a-histogram sweep: per row, `heights[c]`
    is the run of empty cells ending at that row, and each row's histogram
    is scanned with a monotonic stack. O(rows * cols).
    """
    rows, cols = occupied.shape
    heights = [0] * cols
    best_area = 0
    best: Rect | None = None

    for r in range(rows):
        for c in range(cols):
            heights[c] = 0 if occupied[r, c] else heights[c] + 1

        stack: list[tuple[int, int]] = []  # (start column, height)
        for c, height in enumerate([*heights, 0]):  # trailing 0 flushes the stack
            start = c
            while stack and stack[-1][1] >= height:
                s_col, s_height = stack.pop()
                area = s_height * (c - s_col)
                if area > best_area:
                    best_area = area
                    best = Rect(row0=r - s_height + 1, col0=s_col, row1=r, col1=c - 1)
                start = s_col
            stack.append((start, height))

    return best


def _read_png(path: Path) -> np.ndarray:
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - Pillow ships with manim
        raise BlankSpaceError("Pillow is required to analyze frames.") from error
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"))


def frames_are_stale(scene: str, frames: list[Path], slides_dir: Path = SLIDES_DIR) -> bool:
    """True if the deck was re-rendered after these stills were extracted.

    `slides/<Scene>.json` is rewritten by every render, so it is a reliable
    clock for "when did this deck last change". Without this, editing a
    deck and re-running the analyzer without re-extracting silently reports
    the previous layout's numbers.
    """
    config_path = slides_dir / f"{scene}.json"
    if not config_path.is_file() or not frames:
        return False
    return config_path.stat().st_mtime > max(path.stat().st_mtime for path in frames)


def analyze(
    scene: str,
    *,
    review_dir: Path = REVIEW_DIR,
    slides_dir: Path = SLIDES_DIR,
    rows: int = GRID_ROWS,
    cols: int = GRID_COLS,
) -> Report:
    """Build a dead-space report from a scene's extracted final frames."""
    from open_manim_slides.layout import DEFAULT_MARGIN

    scene_dir = review_dir / scene
    frames = sorted(scene_dir.glob("seg-*-final.png"))
    if not frames:
        raise BlankSpaceError(
            f"No final-frame PNGs in {scene_dir} -- run "
            f"`python -m open_manim_slides.frames {scene}` first."
        )

    # Per-axis, because the safe margin is a fixed unit count on a
    # non-square frame (0.5 of 14.22 across, 0.5 of 8 down).
    from manim import config

    margin_x = DEFAULT_MARGIN / config.frame_width
    margin_y = DEFAULT_MARGIN / config.frame_height

    segments = [
        SegmentOccupancy(
            index=index,
            grid=occupancy_grid(_read_png(path), rows=rows, cols=cols, margin_x=margin_x, margin_y=margin_y),
        )
        for index, path in enumerate(frames)
    ]
    ever_used = np.zeros((rows, cols), dtype=bool)
    for segment in segments:
        ever_used |= segment.grid
    return Report(
        scene=scene,
        segments=segments,
        ever_used=ever_used,
        stale=frames_are_stale(scene, frames, slides_dir),
    )


def _render_grid(grid: np.ndarray, occupied_char: str = "#", empty_char: str = ".") -> str:
    return "\n".join("  " + "".join(occupied_char if cell else empty_char for cell in row) for row in grid)


def format_report(report: Report) -> str:
    """Human-readable summary: per-segment fill, then deck-level dead space."""
    rows, cols = report.ever_used.shape
    lines = [f"{report.scene}: {len(report.segments)} segments, {rows}x{cols} grid inside the safe frame", ""]
    if report.stale:
        lines.append(
            f"STALE: the deck was re-rendered after these stills were extracted. "
            f"Run `python -m open_manim_slides.frames {report.scene}` again -- "
            f"the numbers below describe the previous layout."
        )
        lines.append("")

    lines.append("per-segment fill (final frame):")
    for segment in report.segments:
        flag = "  <- sparse" if segment.fill < SPARSE_SEGMENT_FILL else ""
        lines.append(f"  seg-{segment.index:02d}  {segment.fill:5.1%}{flag}")
        empty = largest_empty_rect(segment.grid)
        if empty is not None and empty.fraction_of(rows, cols) >= MIN_REPORTABLE_DEAD_FRACTION:
            lines.append(
                f"            largest empty block: {empty.fraction_of(rows, cols):.0%} of frame "
                f"({empty.describe(rows, cols)})"
            )
    lines.append("")

    lines.append(f"never used by ANY segment: {report.dead_fraction:.0%} of the safe frame")
    dead = report.largest_dead
    if dead is not None and dead.fraction_of(rows, cols) >= MIN_REPORTABLE_DEAD_FRACTION:
        lines.append(
            f"  largest dead region: {dead.fraction_of(rows, cols):.0%} of frame -- {dead.describe(rows, cols)} "
            f"(rows {dead.row0}-{dead.row1}, cols {dead.col0}-{dead.col1})"
        )
        lines.append("  This space is never reached by any segment: it was not reserved, it was left over.")
    else:
        lines.append("  No single dead region large enough to restructure for.")
    lines.append("")
    lines.append("union of all segments ('#' used at some point, '.' never used):")
    lines.append(_render_grid(report.ever_used))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m open_manim_slides.blankspace <SceneName>", file=sys.stderr)
        return 2
    try:
        report = analyze(args[0])
    except BlankSpaceError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
