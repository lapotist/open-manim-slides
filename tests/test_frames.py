import json
from pathlib import Path

import pytest

from open_manim_slides.frames import (
    FramesError,
    extract_review_frames,
    main,
    segment_videos,
    sheet_select_step,
)


def _write_config(tmp_path: Path, scene: str, files: list[tuple[str, str]]) -> Path:
    """Write a minimal slides/<scene>.json with the given (file, rev_file) pairs."""
    slides_dir = tmp_path / "slides"
    slides_dir.mkdir(exist_ok=True)
    config_path = slides_dir / f"{scene}.json"
    config_path.write_text(
        json.dumps({"slides": [{"file": fwd, "rev_file": rev} for fwd, rev in files]})
    )
    return config_path


def test_segment_videos_preserves_json_array_order(tmp_path: Path):
    """Order must come from the JSON array, never from filenames -- the
    sha256-derived names sort meaninglessly, so a glob would silently
    misnumber segments."""
    config_path = _write_config(
        tmp_path,
        "MyDeck",
        [
            ("slides/files/MyDeck/zzz.mp4", "slides/files/MyDeck/zzz_reversed.mp4"),
            ("slides/files/MyDeck/aaa.mp4", "slides/files/MyDeck/aaa_reversed.mp4"),
        ],
    )

    pairs = segment_videos(config_path)

    assert [pair[0].name for pair in pairs] == ["zzz.mp4", "aaa.mp4"]
    assert [pair[1].name for pair in pairs] == ["zzz_reversed.mp4", "aaa_reversed.mp4"]


def test_segment_videos_resolves_paths_against_config_grandparent(tmp_path: Path):
    """`file` entries are written relative to the directory manim ran in
    (`slides/files/...`), so they anchor at the parent-of-`slides/`,
    matching manim-slides' own `PresentationConfig.from_file`."""
    config_path = _write_config(
        tmp_path, "MyDeck", [("slides/files/MyDeck/a.mp4", "slides/files/MyDeck/a_reversed.mp4")]
    )

    pairs = segment_videos(config_path)

    assert pairs[0][0] == tmp_path / "slides" / "files" / "MyDeck" / "a.mp4"


def test_sheet_select_step_spreads_six_tiles_across_the_video():
    assert sheet_select_step(300) == 50
    assert sheet_select_step(6) == 1
    # Never zero, even for videos shorter than the tile count.
    assert sheet_select_step(3) == 1


def test_extract_review_frames_missing_config_names_available_scenes(tmp_path: Path):
    _write_config(tmp_path, "RenderedDeck", [])

    with pytest.raises(FramesError, match="RenderedDeck"):
        extract_review_frames("NeverRendered", slides_dir=tmp_path / "slides")


def test_main_rejects_wrong_arg_count(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err


# --- Frame count -------------------------------------------------------
#
# `nb_frames` is a container-level field: mp4 carries it, matroska reports
# `N/A`, and a truncated file gives nothing. The old code called `int()` on
# whatever came back, so a container without the field raised a bare
# `ValueError` that never named the video.


def test_frame_count_uses_the_container_header_when_it_has_one(monkeypatch):
    import open_manim_slides.frames as frames

    calls = []

    def fake(video, entries, *extra):
        calls.append(entries)
        return "47"

    monkeypatch.setattr(frames, "_ffprobe", fake)

    assert frames._frame_count(Path("a.mp4")) == 47
    # The counting pass costs a full demux, so it must not run when the
    # cheap field already answered.
    assert calls == ["stream=nb_frames"]


def test_frame_count_falls_back_to_counting_packets(monkeypatch):
    """Matroska and any stream-copied container report `N/A` here."""
    import open_manim_slides.frames as frames

    monkeypatch.setattr(
        frames,
        "_ffprobe",
        lambda video, entries, *extra: "N/A" if entries == "stream=nb_frames" else "47",
    )

    assert frames._frame_count(Path("a.mkv")) == 47


def test_frame_count_reports_the_video_when_neither_answer_works(monkeypatch):
    """An empty or truncated segment is a real thing to hit after an
    interrupted render, and the message has to say which file."""
    import open_manim_slides.frames as frames

    monkeypatch.setattr(frames, "_ffprobe", lambda video, entries, *extra: "")

    with pytest.raises(FramesError, match="broken.mp4"):
        frames._frame_count(Path("broken.mp4"))


def test_a_missing_ffprobe_is_reported_as_a_frames_error(monkeypatch):
    import subprocess

    import open_manim_slides.frames as frames

    def missing(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "ffprobe")

    monkeypatch.setattr(subprocess, "run", missing)

    with pytest.raises(FramesError, match="ffprobe is not on PATH"):
        frames._ffprobe(Path("a.mp4"), "stream=nb_frames")
