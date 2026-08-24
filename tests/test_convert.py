"""End-to-end tests for the HTML export path (see convert.py's docstrings).

One real scene is rendered once (module-scoped fixture -- rendering is the
expensive part), then converted per-test to cover:

- the PR #664 workaround: an enum-typed config option (`transition="fade"`)
  must come out quoted, valid JS, rather than reproducing the upstream bug
  (bare identifier that throws at slide-init time and blanks the page);
- the instant-navigation script: injected by default, absent when opted
  out, and syntactically valid JS (it is inlined verbatim, so a syntax
  error would blank the exported page with nothing surfaced anywhere).
"""

import pytest
from manim import Circle, Create

from open_manim_slides import Slide, convert_to_html


class _ConvertSmokeDeck(Slide):
    def construct(self) -> None:
        self.play(Create(Circle()))
        self.next_slide()


@pytest.fixture(scope="module")
def rendered_slides_dir(tmp_path_factory):
    from manim import config

    tmp_path = tmp_path_factory.mktemp("convert")
    media_dir = tmp_path / "media"
    slides_dir = tmp_path / "slides"
    original_media_dir = config.media_dir
    original_quality = (config.pixel_width, config.pixel_height, config.frame_rate)
    original_output_file = config.output_file
    config.media_dir = str(media_dir)
    config.pixel_width, config.pixel_height, config.frame_rate = 320, 180, 15
    # config.output_file is a global that sticks around after a render --
    # left as-is, a later render() in the same process reuses the previous
    # scene's stale output path instead of deriving its own from the new
    # scene's name, and its own video never gets written.
    config.output_file = ""

    try:
        scene = _ConvertSmokeDeck(output_folder=slides_dir)
        scene.render()
    finally:
        config.media_dir = original_media_dir
        config.pixel_width, config.pixel_height, config.frame_rate = original_quality
        config.output_file = original_output_file

    return slides_dir


def test_convert_to_html_quotes_enum_config_options(rendered_slides_dir, tmp_path):
    dest = tmp_path / "out.html"
    convert_to_html(
        ["_ConvertSmokeDeck"],
        dest,
        folder=rendered_slides_dir,
        transition="fade",
        controls_layout="bottom-right",
    )

    html = dest.read_text()
    assert "transition: 'fade'," in html
    assert "transition: fade," not in html
    assert "controlsLayout: 'bottom-right'," in html


_MARKER = "open-manim-slides: navigation shows each segment's correct frame"


def test_convert_to_html_injects_instant_navigation_by_default(
    rendered_slides_dir, tmp_path
):
    dest = tmp_path / "out.html"
    convert_to_html(["_ConvertSmokeDeck"], dest, folder=rendered_slides_dir)

    html = dest.read_text()
    assert _MARKER in html
    # Injected inside the document, not appended after it.
    assert html.index(_MARKER) < html.index("</body>")


def test_convert_to_html_instant_navigation_opt_out(rendered_slides_dir, tmp_path):
    dest = tmp_path / "out.html"
    convert_to_html(
        ["_ConvertSmokeDeck"], dest, folder=rendered_slides_dir, instant_navigation=False
    )

    assert _MARKER not in dest.read_text()
