from pathlib import Path

import numpy as np
import pytest

from open_manim_slides.blankspace import (
    BlankSpaceError,
    Rect,
    Report,
    SegmentOccupancy,
    analyze,
    background_color,
    format_report,
    frames_are_stale,
    largest_empty_rect,
    main,
    occupancy_grid,
)


def _frame(width: int = 320, height: int = 180, color: int = 0) -> np.ndarray:
    return np.full((height, width, 3), color, dtype=np.uint8)


def test_background_color_uses_the_mode_not_a_hardcoded_black():
    """`theme.COLOR_BACKGROUND` is a token a deck can change, so the
    background is whatever dominates the frame by area."""
    pixels = _frame(color=30)
    pixels[0:10, 0:10] = 255

    assert background_color(pixels).tolist() == [30, 30, 30]


def test_occupancy_grid_marks_only_cells_holding_content():
    pixels = _frame()
    # Fill the top-left eighth of the frame -- one grid cell's worth.
    pixels[0:20, 0:20] = 255

    grid = occupancy_grid(pixels, rows=9, cols=16)

    assert grid[0, 0]
    assert not grid[8, 15]


def test_occupancy_grid_counts_faint_fills_as_content():
    """Decks use fill_opacity as low as 0.12; that is real content, not noise."""
    pixels = _frame()
    pixels[0:20, 0:20] = 31  # ~0.12 opacity white on black

    assert occupancy_grid(pixels, rows=9, cols=16)[0, 0]


def test_occupancy_grid_ignores_a_speck_below_the_fill_threshold():
    pixels = _frame(width=640, height=360)  # 40x40 cells, so MIN_CELL_FILL is 8 px
    pixels[0:2, 0:2] = 255  # 4 px -- under the threshold

    assert not occupancy_grid(pixels, rows=9, cols=16)[0, 0]


def test_occupancy_grid_margin_crops_the_deliberately_empty_border():
    """The safe margin is supposed to be empty; counting it would report a
    dead border on every correctly-built deck."""
    pixels = _frame()
    pixels[0:6, :] = 255  # content only in the top border strip

    assert occupancy_grid(pixels, rows=9, cols=16)[0, 0]
    assert not occupancy_grid(pixels, rows=9, cols=16, margin_y=0.1).any()


def test_occupancy_grid_margins_are_independent_per_axis():
    """The safe margin is a fixed unit count on a 14.22x8 frame, so its
    fraction differs per axis; one shared value would leave a quarter of
    the top and bottom rows measuring known-empty margin."""
    pixels = _frame(width=320, height=180)
    pixels[:, 0:20] = 255  # content only in the left border strip

    assert occupancy_grid(pixels, rows=9, cols=16, margin_y=0.2)[:, 0].any()
    assert not occupancy_grid(pixels, rows=9, cols=16, margin_x=0.1).any()


def test_largest_empty_rect_finds_the_biggest_block():
    occupied = np.ones((4, 4), dtype=bool)
    occupied[1:3, 1:4] = False  # a 2x3 hole

    rect = largest_empty_rect(occupied)

    assert rect == Rect(row0=1, col0=1, row1=2, col1=3)
    assert rect.cells == 6


def test_largest_empty_rect_returns_none_when_everything_is_occupied():
    assert largest_empty_rect(np.ones((3, 3), dtype=bool)) is None


def test_largest_empty_rect_spans_full_frame_when_nothing_is_occupied():
    rect = largest_empty_rect(np.zeros((3, 5), dtype=bool))

    assert rect is not None
    assert rect.cells == 15


def test_space_used_by_only_one_segment_is_not_dead():
    """The core distinction: empty-then-filled space was reserved, not
    wasted. Only a cell no segment ever reaches counts as dead."""
    used_late = np.zeros((2, 2), dtype=bool)
    used_late[0, 0] = True
    never_used = np.zeros((2, 2), dtype=bool)

    report = Report(
        scene="D",
        segments=[
            SegmentOccupancy(index=0, grid=never_used),
            SegmentOccupancy(index=1, grid=used_late),
        ],
        ever_used=never_used | used_late,
    )

    assert report.ever_used[0, 0]
    assert report.dead_fraction == 0.75


def test_rect_describe_names_a_full_height_side():
    assert Rect(row0=0, col0=12, row1=8, col1=15).describe(rows=9, cols=16) == "the right side, full height"


def test_rect_describe_names_a_full_width_band():
    assert Rect(row0=7, col0=0, row1=8, col1=15).describe(rows=9, cols=16) == "the bottom band, full width"


def test_analyze_without_extracted_frames_points_at_the_frames_command(tmp_path: Path):
    with pytest.raises(BlankSpaceError, match="open_manim_slides.frames"):
        analyze("NeverExtracted", review_dir=tmp_path)


def test_format_report_calls_out_dead_space_as_left_over(tmp_path: Path):
    grid = np.zeros((9, 16), dtype=bool)
    grid[0:9, 0:8] = True  # only the left half ever used
    report = Report(scene="D", segments=[SegmentOccupancy(index=0, grid=grid)], ever_used=grid)

    text = format_report(report)

    assert "the right side, full height" in text
    assert "left over" in text


def test_frames_are_stale_when_the_deck_was_rendered_after_extraction(tmp_path: Path):
    """Silent staleness is the likeliest way to trust a wrong measurement:
    the edit-render-measure loop invites re-running the analyzer without
    re-extracting."""
    slides_dir = tmp_path / "slides"
    slides_dir.mkdir()
    frame = tmp_path / "seg-00-final.png"
    frame.write_bytes(b"")
    config = slides_dir / "D.json"
    config.write_text("{}")
    import os

    os.utime(frame, (1000, 1000))
    os.utime(config, (2000, 2000))

    assert frames_are_stale("D", [frame], slides_dir=slides_dir)

    os.utime(config, (500, 500))
    assert not frames_are_stale("D", [frame], slides_dir=slides_dir)


def test_format_report_leads_with_a_stale_warning(tmp_path: Path):
    grid = np.ones((9, 16), dtype=bool)
    report = Report(
        scene="D", segments=[SegmentOccupancy(index=0, grid=grid)], ever_used=grid, stale=True
    )

    assert "STALE" in format_report(report)


def test_main_rejects_wrong_arg_count(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
