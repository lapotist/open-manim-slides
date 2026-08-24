"""Workaround for a merged-but-unreleased upstream manim-slides bug (PR #664).

`RevealJS`/`HtmlZip`'s HTML config options that are backed by a
`(Str, StrEnum)` type -- `transition`, `controls_layout`, `slide_number`,
`keyboard_condition`, `navigation_mode`, `auto_play_media`,
`background_size`, and 10 others -- lose their quoting during pydantic
validation. `Str.__get_pydantic_core_schema__` returns a bare
`core_schema.str_schema()`, so validating any value against one of these
fields collapses it to a plain `str`, discarding the `Str` subclass whose
`__str__` is what adds the quotes. This isn't limited to the CLI's
`-c key=value` string parsing -- verified directly in this environment that
even constructing `RevealJS(transition=Transition.fade)` with an
already-built enum member reproduces the bug, since pydantic-core's plain
`str_schema()` validator coerces any `str` subclass instance back down to a
bare `str` on the way in.

Concretely, `manim-slides convert Scene out.html -c transition=fade` emits
`transition: fade,` into the page's inline JS instead of
`transition: 'fade',`. `fade` is read as an undefined variable reference,
throwing at slide-init time and aborting the whole init script -- the
exported presentation is a blank page, with no error surfaced anywhere.

Fix (matches the upstream PR): validate as a plain string, then reconstruct
the proper type from it via
`core_schema.no_info_after_validator_function(cls, core_schema.str_schema())`.
The catch is that pydantic bakes a model's core schema in at class-creation
time -- `RevealJS`/`HtmlZip` are built once, at `manim_slides.convert`
import time, so patching `Str.__get_pydantic_core_schema__` after the fact
has no effect on its own. `model_rebuild(force=True)` regenerates the
schema from the (now patched) field-level hooks; doing both, in that order,
is what actually fixes it (verified empirically against the installed
manim-slides 5.6.0).

PR #664 merged upstream 2026-08-20. Not yet in a release as of this
writing -- PyPI's latest is manim-slides 5.6.0 (2026-04-15, predates the
merge). Remove this module once this project's manim-slides floor moves
past whichever release first includes the fix.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _patch_str_quoting() -> None:
    from manim_slides.convert import HtmlZip, RevealJS, Str
    from pydantic_core import core_schema

    def _fixed_schema(cls: type[Str], source_type: Any, handler: Any) -> Any:
        return core_schema.no_info_after_validator_function(cls, core_schema.str_schema())

    Str.__get_pydantic_core_schema__ = classmethod(_fixed_schema)
    RevealJS.model_rebuild(force=True)
    HtmlZip.model_rebuild(force=True)


_patch_str_quoting()


# Injected into the exported HTML (see convert_to_html's instant_navigation
# parameter). Every claim below was read off the real sources, not assumed.
#
# reveal.js 6.0.1 (js/controllers/slidecontent.js, `startEmbeddedMedia`)
# restarts a background video from `currentTime = 0` every time its slide
# becomes current, in *either* direction, because manim-slides' HTML export
# drops the pre-rendered reversed videos its native Qt presenter uses for
# backward navigation (convert.py: `copy_to(..., include_reversed=False)`)
# and the Reveal template only ever references the forward file.
#
# That one behavior produces two symptoms that look unrelated and are not:
#
#   * Backward: the segment replays its entire construction animation
#     instead of showing the finished state the viewer just watched.
#   * Forward: re-entering a segment whose video was left parked at its end
#     shows that end frame -- the spoiler, the whole point of the build-up --
#     until the seek back to 0 is decoded and painted.
#
# The second symptom is what an earlier, narrower version of this script
# (which seeked the *entering* video to its end on backward navigation)
# traded the first one for: parking videos at their end is exactly what
# makes the next forward entry flash. Both are the same underlying cost --
# seeking a video that is already on screen does not repaint it until the
# new frame is decoded, and until then the compositor keeps showing the old
# one. Measured in headless Firefox 153 that stale frame stands for 37 ms;
# on a GPU-composited desktop Firefox a screen recording showed ~400 ms.
#
# So this script never seeks a visible video. Instead each video is parked,
# while it is off screen, at the pose it will next be entered with:
#
#   * a slide left going forward is next seen going *backward*, so it is
#     parked at its final frame;
#   * a slide left going backward is next seen going *forward*, so it is
#     parked at 0.
#
# Entering a slide then requires no seek at all, in either direction, and
# the frame already on screen is the right one.
#
# Two details are load-bearing. `slidechanged` fires *before* Reveal's own
# `startEmbeddedContent`/`backgrounds.update()` in the same synchronous
# `slide()` call, which is the window this script uses to stop the reset
# from happening at all: `startEmbeddedMedia` resets only a video that
# reads as `paused || ended`, so shadowing those two properties with own
# accessors for the rest of that call makes it skip the video entirely,
# then they are deleted and the real prototype getters are back.
#
# Shadowing is used rather than the more obvious trick of calling `play()`
# first (a playing video is also left alone) because a segment that ran to
# completion *is* `ended`, and `play()` on an ended element seeks back to
# the start per the HTML spec -- which is the flash this removes. That
# version was written, measured, and rejected: it left two of three
# backward entries painting frame 0. For the same reason videos are parked
# at `duration - EPSILON`, and parking always seeks an `ended` video even
# when it already sits at the right position.
_INSTANT_NAVIGATION_SCRIPT = """\
    <script>
      // open-manim-slides: navigation shows each segment's correct frame
      // immediately, in both directions, by never seeking a visible video.
      (() => {
        // Small enough to stay inside the final frame at any realistic
        // frame rate (a frame is 16.7 ms at 60 fps, 66 ms at manim's -ql
        // 15 fps), but enough that the element is not `ended`.
        const EPSILON = 0.01;

        const videoOf = (slide) => {
          const content = slide && slide.slideBackgroundContentElement;
          return (content && content.querySelector('video')) || null;
        };
        const endPose = (video) => Math.max(0, video.duration - EPSILON);
        const park = (video, time) => {
          if (!video || !isFinite(video.duration)) return;
          video.pause();
          // `ended` is re-seeked away from even when the position already
          // looks right: it is the state that makes a later play() jump
          // back to the start.
          if (video.ended || Math.abs(video.currentTime - time) > 0.001) {
            video.currentTime = time;
          }
        };
        // Make Reveal's `paused || ended` test read false for the rest of
        // this synchronous slide() call, so it leaves the video alone.
        const shieldFromReset = (video) => {
          const alwaysFalse = { configurable: true, get: () => false };
          Object.defineProperty(video, 'paused', alwaysFalse);
          Object.defineProperty(video, 'ended', alwaysFalse);
          setTimeout(() => {
            delete video.paused;
            delete video.ended;
          }, 0);
        };

        let previous = null;

        Reveal.on('ready', (event) => {
          previous = { h: event.indexh, v: event.indexv || 0 };
        });

        Reveal.on('slidechanged', (event) => {
          const current = { h: event.indexh, v: event.indexv || 0 };
          const backward = previous !== null &&
            (current.h < previous.h ||
             (current.h === previous.h && current.v < previous.v));
          previous = current;

          const entering = videoOf(event.currentSlide);
          if (backward && entering && isFinite(entering.duration)) {
            // Reveal is about to reset this video, later in this same
            // synchronous slide() call; stop it from seeing a resettable
            // video. The seek is a safety net for a slide reached without
            // having been parked (a jump, or a first-ever visit) -- in the
            // ordinary case the pose is already right and nothing seeks,
            // which is the whole point.
            if (entering.ended ||
                Math.abs(entering.currentTime - endPose(entering)) > 0.25) {
              entering.currentTime = endPose(entering);
            }
            shieldFromReset(entering);
          }

          // Park the slide just left for its next entry, now that it is
          // hidden and a seek costs nothing visible.
          const leaving = videoOf(event.previousSlide);
          if (leaving) {
            setTimeout(() => park(leaving, backward ? 0 : endPose(leaving)), 0);
          }
        });

        // The export template binds SPACE to play/pause. Re-register it
        // (a later addKeyBinding for the same keyCode replaces the earlier
        // one) so that a deliberate replay still works: videos now rest one
        // EPSILON short of `ended`, where a bare play() would only finish
        // that sliver instead of restarting from the beginning.
        Reveal.addKeyBinding(
          { keyCode: 32, key: 'SPACE', description: 'Play / pause video' },
          () => {
            const video = videoOf(Reveal.getCurrentSlide());
            if (!video) { Reveal.next(); return; }
            if (!video.paused) { video.pause(); return; }
            if (video.currentTime >= endPose(video) - EPSILON) {
              video.currentTime = 0;
            }
            video.play();
          }
        );
      })();
    </script>
"""


def convert_to_html(
    scenes: list[str],
    dest: Path,
    folder: Path = Path("./slides"),
    *,
    zip: bool = False,
    instant_navigation: bool = True,
    **config_options: Any,
) -> Path:
    """Convert rendered scenes to a Reveal.js HTML deck (or a `.zip` of one).

    Drop-in replacement for
    `manim-slides convert <scenes> <dest> [-c key=value ...]` when `dest` is
    `.html`/`.zip` -- use this instead of the CLI for any deck that sets
    `transition`, `controls_layout`, `slide_number`, or any of the other
    enum-typed config options described in the module docstring above; the
    CLI form is silently broken for those. Values for those options should
    be passed as plain strings (e.g. `transition="fade"`), same as `-c`
    would take -- this function's import-time patch is what makes that
    string get validated correctly instead of the CLI's broken path.

    `instant_navigation` (default on, `.html` output only) injects the
    script documented above `_INSTANT_NAVIGATION_SCRIPT`: moving between
    segments shows the right frame immediately in both directions, instead
    of replaying a finished segment on the way back or flashing a segment's
    end state on the way in. Verify it against a real browser with
    `python -m open_manim_slides.playback <exported.html>`.
    """
    from manim_slides.convert import HtmlZip, RevealJS
    from manim_slides.present import get_scenes_presentation_config

    presentation_configs = get_scenes_presentation_config(scenes, Path(folder))
    cls = HtmlZip if zip else RevealJS
    converter = cls(presentation_configs=presentation_configs, **config_options)
    converter.convert_to(dest)

    if instant_navigation and not zip:
        html = dest.read_text()
        dest.write_text(html.replace("</body>", _INSTANT_NAVIGATION_SCRIPT + "</body>"))

    return dest
