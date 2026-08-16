"""Per-segment review-frame extractor for rendered decks.

The create-deck skill's self-review step needs to *look* at what a render
produced, cheaply, without scrubbing video: for each segment, a still of
its final frame (what the audience sits on while the presenter talks) and
a small contact sheet of six evenly spaced frames (the motion arc a final
frame can't show).

The final frame is read from the forward video with `-sseof` (seek from
end). Frame 0 of the pre-rendered `<hash>_reversed.mp4` looks like a
free final frame but is not one: manim-slides splits videos longer than
`max_duration_before_split_reverse` (default 4 s) into chunks before
reversing, and the result's first frame is a mid-segment state at a chunk
boundary -- observed empirically on an 8.15 s segment whose "reversed
frame 0" showed the ~4 s mark, while short segments mask the bug.

Segment order comes from `slides/<Scene>.json`'s `slides` array, which is
appended in presentation order; the sha256-derived filenames sort
meaninglessly, so globbing the files directory would silently misnumber
segments. Output indices match the manifest's 0-based `segment` indices
(caveat: a deck using `skip_animations` drops those segments from the
slides JSON, desyncing the two -- no deck here does).

Usage: `python -m open_manim_slides.frames <SceneName>` from the repo
root. Writes to `media/review/<SceneName>/` (media/ is gitignored) and
prints the ordered list of images written.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SLIDES_DIR = Path("slides")
REVIEW_DIR = Path("media") / "review"
SHEET_TILES = 6  # 3x2 grid

_FINAL_FRAME_WIDTH = 960
_SHEET_TILE_SIZE = "640:360"


class FramesError(RuntimeError):
    """A frames-extraction failure with a user-facing message."""


def segment_videos(config_path: Path) -> list[tuple[Path, Path]]:
    """Read `slides/<Scene>.json` and return [(forward, reversed), ...] in segment order.

    Paths in the JSON are written relative to the directory manim ran in
    (e.g. `slides/files/<Scene>/<hash>.mp4`); manim-slides itself
    re-anchors them against the config's parent-of-parent on load, so the
    same resolution is used here.
    """
    data = json.loads(config_path.read_text())
    base = config_path.parent.parent
    pairs = []
    for slide in data["slides"]:
        forward = Path(slide["file"])
        rev = Path(slide["rev_file"])
        pairs.append(
            (
                forward if forward.is_absolute() else base / forward,
                rev if rev.is_absolute() else base / rev,
            )
        )
    return pairs


def _frame_count(video: Path) -> int:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_frames",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(result.stdout.strip())


def sheet_select_step(frame_count: int, tiles: int = SHEET_TILES) -> int:
    """Frame stride that spreads `tiles` samples across `frame_count` frames."""
    return max(1, frame_count // tiles)


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-v", "error", "-y", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise FramesError(f"ffmpeg failed: {result.stderr.strip()}")


def extract_review_frames(
    scene: str, slides_dir: Path = SLIDES_DIR, review_dir: Path = REVIEW_DIR
) -> list[Path]:
    """Write final-frame + contact-sheet PNGs per segment; return them in order."""
    config_path = slides_dir / f"{scene}.json"
    if not config_path.is_file():
        available = sorted(path.stem for path in slides_dir.glob("*.json"))
        hint = f" Rendered scenes: {', '.join(available)}." if available else ""
        raise FramesError(f"No slide config at {config_path} -- render the deck first.{hint}")

    out_dir = review_dir / scene
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for index, (forward, _rev) in enumerate(segment_videos(config_path)):
        final_png = out_dir / f"seg-{index:02d}-final.png"
        sheet_png = out_dir / f"seg-{index:02d}-sheet.png"

        # Final frame: seek to just before the forward video's end. See the
        # module docstring for why the reversed video's frame 0 is NOT a
        # trustworthy substitute despite looking like one.
        _run_ffmpeg(
            [
                "-sseof",
                "-0.1",
                "-i",
                str(forward),
                "-frames:v",
                "1",
                "-vf",
                f"scale={_FINAL_FRAME_WIDTH}:-1",
                str(final_png),
            ]
        )

        step = sheet_select_step(_frame_count(forward))
        _run_ffmpeg(
            [
                "-i",
                str(forward),
                "-vf",
                f"select='not(mod(n,{step}))',scale={_SHEET_TILE_SIZE},tile=3x2",
                "-frames:v",
                "1",
                str(sheet_png),
            ]
        )
        written.extend([final_png, sheet_png])
    return written


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: python -m open_manim_slides.frames <SceneName>", file=sys.stderr)
        return 2
    try:
        written = extract_review_frames(args[0])
    except FramesError as error:
        print(str(error), file=sys.stderr)
        return 1
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
