"""Workaround for an unmerged upstream manim-slides bug (PR #664).

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

Remove this module once
https://github.com/jeertmans/manim-slides/pull/664 merges and this
project's manim-slides floor moves past that release.
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


# Injected into the exported HTML (see convert_to_html's snap_back_navigation
# parameter). Both halves of the problem it fixes were confirmed against real
# sources/behavior, not assumed:
#
# - manim-slides pre-renders a reversed video per segment (config.py's
#   SlideConfig.rev_file) and its native Qt presenter uses it for backward
#   navigation, but the HTML exporter explicitly excludes it
#   (convert.py: `copy_to(..., include_reversed=False)`), and the Reveal.js
#   template only ever references the forward file.
# - reveal.js (6.0.1, js/controllers/slidecontent.js `startEmbeddedMedia`)
#   restarts a background video from `currentTime = 0` every time its slide
#   becomes current again, in either direction.
#
# Net effect: pressing "previous" replays the target segment's entire
# construction animation instead of showing its finished state -- and a
# screen-recording diagnosis (2026-08-12) showed Firefox additionally
# stalling frame presentation for ~1-1.5s mid-replay under rapid
# back-and-forth navigation, which reads as "stuck on a middle state, then
# jumps to the end". Snapping backward navigation to the video's last frame
# matches the native presenter's semantics and removes the replay churn that
# triggers the stall. A deliberate replay (the template's SPACE binding)
# still works: play() on an ended video restarts it from the beginning.
_SNAP_BACK_NAVIGATION_SCRIPT = """\
    <script>
      // open-manim-slides: snap backward navigation to the segment's final
      // frame instead of replaying its whole construction animation.
      (() => {
        let last = null;
        Reveal.on('ready', (event) => {
          last = { h: event.indexh, v: event.indexv || 0 };
        });
        Reveal.on('slidechanged', (event) => {
          const cur = { h: event.indexh, v: event.indexv || 0 };
          const backward = last !== null &&
            (cur.h < last.h || (cur.h === last.h && cur.v < last.v));
          last = cur;
          if (!backward) return;
          const content = event.currentSlide.slideBackgroundContentElement;
          const video = content && content.querySelector('video');
          if (!video) return;
          // Reveal restarts this video (currentTime = 0, play()) *after*
          // 'slidechanged', later in the same synchronous slide() call --
          // snap on a 0ms timer so it runs after that, and guard against
          // the restart being deferred to 'loadeddata' (which happens when
          // the element is still mid-seek and readyState has dropped).
          setTimeout(() => {
            const snap = () => {
              video.pause();
              if (video.duration) video.currentTime = video.duration;
            };
            snap();
            video.addEventListener('play', snap, { once: true });
            // Let a deliberate replay (SPACE) win again shortly after.
            setTimeout(() => video.removeEventListener('play', snap), 200);
          }, 0);
        });
      })();
    </script>
"""


def convert_to_html(
    scenes: list[str],
    dest: Path,
    folder: Path = Path("./slides"),
    *,
    zip: bool = False,
    snap_back_navigation: bool = True,
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

    `snap_back_navigation` (default on, `.html` output only) injects the
    script documented above `_SNAP_BACK_NAVIGATION_SCRIPT`: backward
    navigation shows the previous segment's finished state immediately
    instead of replaying its whole construction animation.
    """
    from manim_slides.convert import HtmlZip, RevealJS
    from manim_slides.present import get_scenes_presentation_config

    presentation_configs = get_scenes_presentation_config(scenes, Path(folder))
    cls = HtmlZip if zip else RevealJS
    converter = cls(presentation_configs=presentation_configs, **config_options)
    converter.convert_to(dest)

    if snap_back_navigation and not zip:
        html = dest.read_text()
        dest.write_text(html.replace("</body>", _SNAP_BACK_NAVIGATION_SCRIPT + "</body>"))

    return dest
