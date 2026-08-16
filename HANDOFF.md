# open-manim-slides — Handoff

Status: updated after the sixth implementation session, 2026-08-14.
The repo is real: git initialized, MIT-licensed, pushed to
**https://github.com/lapotist/open-manim-slides** (public). Read this file
before doing further work here — it's the authoritative summary of what's
decided, what's built, and what's next. See `AGENTS.md` for the current
file-by-file architecture; this file is the *why* behind it and the
running history, kept intentionally compact — full investigation detail
for any item below lives in this repo's session transcripts if it's ever
needed again, not duplicated here.

**Standing scope boundary** (set explicitly by the user, still in force):
framework/tooling work can proceed autonomously; deck *content* — fixing
`layers_of_the_earth.py`, growing/curating example decks, the review
site's design — is reserved for the user to guide directly, unless they
explicitly ask for it (as they did for both example decks and the
webrunner below).

## What this project is

An open-source framework for building **Manim Slides** presentations,
inspired by [open-slide](https://open-slide.dev/) (https://github.com/1weiho/open-slide)
— "a slide framework built for agents," but for Manim instead of React. The
goal is a controlled, skill-driven workflow for generating and iterating on
slide decks, with real enforcement (things that fail loudly at construction
time) instead of a long prose instructions file an agent might silently
drift from.

It is being extracted and generalized from a private repo at
`/home/lapotist/Documents/manim` (Traditional Chinese math lesson videos).
That repo is the origin of the problems this framework addresses, but **no
code from it has been ported** — see decision 1 below.

## Decisions made (first session)

1. **No porting from the source repo — design fresh instead.** The old
   repo's `carlo_manim` (`layout.py`/`attention.py`/`base.py`) and its QA
   review site are both "not well made" per the user, and shouldn't be
   used as reference, not just left unported.
2. **Authoring unit: one file per deck, segments as top-level functions.**
   open-slide's one-file-per-slide convention doesn't transfer — a Manim
   scene's segments routinely share state across `self.next_slide()`
   boundaries (a persisting title, a diagram built up over several
   segments) in a way independent React components don't. A harder
   alternative (true file-per-slide with a `track()`-based state-handoff
   registry) is a documented future path, not a current bet.
3. **Skills are canonical plain files, Claude Code gets a symlinked
   projection.** Adopted directly from open-slide's real implementation:
   `SKILL.md` files live under agent-agnostic `.agents/skills/<name>/`,
   plus a canonical `AGENTS.md`; `.claude/skills/<name>` and `CLAUDE.md`
   are symlinks into the canonical files.
4. **Site rebuild direction** (the "no web canvas ⇒ no HMR" question).
   Manim CE is raster-only and manim-slides' own FAQ confirms slides are
   static pre-rendered video, so: build an ID+source-location **manifest**
   first, drive an **outline/tree list UI** before a pixel-accurate video
   overlay; audience is primarily **public viewers**, not an internal QA
   tool; editing is a click → a structured, ID + file:line-scoped
   comment/edit-request (not live hot-editing), consumed later by an
   apply-comments Skill — chosen over open-slide's inline JSX-comment
   markers because Manim's construction calls aren't co-located with their
   on-screen appearance the way JSX is.
5. **Manifest schema + `track()` design**: element-centric JSON (one entry
   per id, list of appearances), duplicate id within one *segment* raises,
   reuse across segments is expected, bbox captured at end-of-segment
   (piggybacking on the `next_slide()` override already needed for the
   transition fix), snapshot step failure-isolated so a bad element can't
   break a render.
6. **Python/tooling**: `mise` (`python = "latest"`), standard
   `pyproject.toml`, not the source repo's `pixi.toml`.

## Session history

**First session (2026-08-09)** — Repo scaffolded (MIT, `pyproject.toml`,
pushed to GitHub). Built `base.py` (`Slide`, `track()`, transition-flash
fix), `layout.py` (`assert_within_safe_frame` only), `scaffold.py`,
`create-deck` skill, 17 tests. Testing `layers_of_the_earth.py` (four
labels on concentric circles) found two real gaps even with the safe-frame
check in place: (a) labels overlapped each other into a garbled mess —
`assert_within_safe_frame` only guards the frame *edge*, not other
elements; (b) the manifest only recorded the segment `track()` was called
in, not every segment an element actually stayed visible for. Both
motivated the second session's fixes.

**Second session (2026-08-10)** — Fixed both gaps from session one:
- `wait_time_between_slides` was being set via a shadowing class
  attribute (written before `manim-slides` was installed to verify
  against); it's actually a clamped `@property`, so the shadow silently
  defeated the setter for anyone writing to it in `construct()`. Fixed by
  setting it through the real property.
- Manifest appearance gap fixed by overriding `Scene.remove()` (which
  `FadeOut` routes through) to deactivate a tracked id only once its
  mobject actually leaves the scene, so every segment it's still visible
  in gets an appearance entry.
- Built `assert_no_overlap()` and — critically — baked
  `self.assert_no_overlap_among_tracked()` into every segment
  `scaffold.py` generates, so the check is structural, not a convention an
  agent could skip.
- Built the `manim-slides` PR #664 workaround (`convert.py`): a
  `(Str, StrEnum)` field's `__get_pydantic_core_schema__` collapses to a
  bare string during pydantic validation, dropping the quoting that keeps
  exported Reveal.js config valid JS. Fix needs both the schema patch
  *and* `model_rebuild(force=True)` — patching alone doesn't touch an
  already-built schema.
- First `theme.py` slice: typography scale, color tokens, `title_slide()`.
- Test count 17 → 28.

**Third session (2026-08-10)** — Long session, several threads:
- *Design system finished*: spacing scale (anchored to manim's own
  `next_to`/`arrange`/`to_edge` buffer defaults, not invented numbers),
  `two_column()`, `diagram_with_caption()`. 28 → 31 tests.
- *Two decks built via `create-deck`* at the user's explicit request —
  `decks/euler_s_formula.py` and `decks/the_pythagorean_theorem.py`
  (both `MathTex`-based, `Transform`-driven step derivations). Found
  `dvisvgm` was missing (required by `MathTex`/`Tex` specifically, not
  manim generally) — user installed it manually, agent has no sudo.
  Building Euler's formula's complex-plane diagram surfaced a real,
  structural gap in `assert_no_overlap_among_tracked()`: it compares
  axis-aligned bounding boxes, and any point on a circle of radius `R`
  centered at `C` is always within `[C-R, C+R]` on *both* axes — so a
  circle checked against anything on/radiating from its center
  (a radius line, an angle-arc indicator) false-positives at every angle,
  and a diagonal line's bbox is a large rectangle that swallows anything
  positioned near it. Evaluated 8 fixes (per-pair exemptions, exact
  per-shape geometry, pixel-mask rasterization, convex-hull+SAT, a
  `fill_opacity` heuristic, a circle-specific special case, a role flag)
  and built the smallest one matching the project's "explicit, no magic"
  taste: **`track(mobj, id=..., decorative=True)`** — still gets a full
  manifest entry, just excluded from the pairwise overlap check.
  Convex-hull+SAT would also fix the diagonal-line case for genuinely
  independent content, not just backdrop; deferred as a documented
  medium-term follow-up (next-steps item 9). The Pythagorean deck
  rendered clean on the *first* full render by verifying the trickier
  manim APIs headlessly before rendering, unlike Euler's multi-round
  debugging. 31 → 35 tests.
- *Built `src/open_manim_slides/webrunner/`* (FastAPI + plain JS, stack
  and scope confirmed with the user first): deck discovery from source
  alone, subprocess-based `manim render` with a **real** progress bar
  (manim's tqdm output survives being piped to a non-tty subprocess —
  confirmed, not assumed), SSE streaming, HTML export via
  `convert_to_html` served for in-browser presenting. Not imported by the
  core package, so `fastapi`/`uvicorn` aren't forced on the base install.
  35 → 46 tests, plus a real end-to-end run (started the server, rendered
  real decks through it, confirmed the error path with a throwaway deck
  that deliberately raises).
- *Investigated a "flashing" report on `layers_of_the_earth`* — turned out
  to be the same known overlap bug (item 2 below), unflagged because that
  deck predates `assert_no_overlap_among_tracked()` and never calls it.
- *Built `assert_reasonably_centered(*mobjects, tolerance=0.2)`* after the
  user pointed at the Pythagorean deck's summary slide specifically:
  neither existing check catches a composition that's in-frame and
  non-overlapping but never centered as a *group* (a title left at its
  default position with content stacked below it via `next_to` only ever
  grows downward). Calibrated against real numbers before picking a
  threshold — the buggy slide sat at -30% vertical offset vs. a normal
  diagram segment's +11%. That same pass showed `the-algebra`/
  `eulers-identity` sit on the same spectrum (+55%/+27%), surfaced to the
  user rather than silently flagging already-shipped segments; the user
  chose to fix only the summary slide. Deliberately **not** baked into
  `scaffold.py` (opt-in, recommended in `create-deck/SKILL.md` for
  title/summary/result "punchline" slides specifically) and, unlike the
  overlap check, does **not** exclude `decorative` elements — a backdrop
  still occupies real space and should count toward centering. 46 → 54
  tests.

**Fourth session (2026-08-12)** — User reported four `webrunner` bugs;
fixed all four:
- **Presenter unresponsive unless fullscreened**: the iframe was never
  focused after `src` was set, so keyboard input went to the parent page.
  Fixed with `.contentWindow.focus()` on load, on click, and after
  `requestFullscreen()`.
- **Fullscreen-transition stall**: mitigated by giving the presenter a
  wider pre-fullscreen layout (`.presenting` CSS modifier), so the resize
  jump is smaller. Not fully verifiable without a real browser.
- **"12 of ~8" progress message**: the `self.play(` call-site count is a
  lower bound (a single call can log more than one `Animation N` entry)
  and the display never self-corrected once exceeded. Extracted
  `_progress_from_animation_line()` (now a small, tested pure function)
  that clamps the displayed total upward, verified live against a real
  render flipping from "26 of ~27" to "28 of ~28" mid-stream.
- **"One page" — browser back/forward not tracking the loaded deck**:
  added real `history.pushState`/`popstate` handling (`?present=<url>
  &title=<title>` for the presenter view, `/` for the list), including
  restoring state on a fresh load/reload.
- **Process-hygiene finding**: an end-to-end verification pass (checking
  `lsof -i :8000`, not just that `curl` succeeded) caught a **webrunner
  server from the third session still running two days later**, bound to
  port 8000 and serving pre-fix code — almost certainly what the user was
  actually testing against for several of these reports. Killed it;
  two more stale processes turned up and were killed during the same
  session's later verification passes. Lesson banked: check who actually
  holds the port before trusting that served code matches source.
- **Follow-up in the same session**: "sometimes laggy going back and
  forth" traced by reading reveal.js 6.0.1's actual source (`gh api`
  against the exact tag, not docs — which don't cover this) to
  `config.viewDistance` (default 3): a segment's background `<video>` is
  only created — source set, browser starts fetching/decoding — the first
  time that segment comes within view distance of the current one; for
  these typically 5-8 segment decks, later segments hadn't started
  loading at all until first navigated near. Fixed with
  `view_distance=50, mobile_view_distance=50` passed to `convert_to_html`
  in `webrunner/render.py`, verified in the generated config and via a
  real render.
- Test count: 54 → 57.

**Fifth session (2026-08-12)** — The fourth session's `view_distance` fix
didn't resolve the back-and-forth lag; the user's refined symptom ("stuck
on some middle state then jumps to the end of the animation; forward-only
is smooth") pointed elsewhere. Diagnosed from a **screen recording** the
user made (OBS installed for the purpose; its own QSV-encoder failure
diagnosed from the tmux pane en route — `MFX_ERR_UNSUPPORTED` on ICQ rate
control, worked around with FFmpeg VAAPI), frames extracted with ffmpeg
into timestamped contact sheets:
- **Root cause, two confirmed halves.** (a) manim-slides pre-renders a
  reversed video per segment (`SlideConfig.rev_file`) and its native Qt
  presenter uses it for backward navigation — but the HTML exporter
  explicitly drops it (`copy_to(..., include_reversed=False)`) and the
  Reveal template only references the forward file. (b) reveal.js 6.0.1's
  `startEmbeddedMedia` restarts a background video from `currentTime = 0`
  every time its slide becomes current, in either direction. Net: pressing
  "previous" replays the target segment's *entire construction animation*.
  The recording showed exactly that (already-seen titles re-writing
  stroke-by-stroke after back-nav), plus Firefox stalling frame
  presentation ~1–1.5 s mid-replay under rapid navigation before snapping
  forward — the literal "stuck then jumps" report. The dimmed/black
  in-between frames were the decks' own opening `FadeOut`s replaying, not
  Reveal transitions (generated config confirmed `transition: 'none'`).
- **Fix: `snap_back_navigation` in `convert_to_html` (default on).**
  Injects a script into the exported HTML that, on backward navigation,
  pauses the now-current video and seeks it to its final frame — matching
  the native presenter's semantics and PowerPoint-family behavior, and
  removing the replay churn that triggered the stall. Timing subtlety,
  read from reveal.js source: `slidechanged` fires *before*
  `backgrounds.update()` restarts the video in the same synchronous
  `slide()` call, so the snap runs on a 0 ms timer, with a one-shot `play`
  guard (dropped after 200 ms) for the case where Reveal defers the
  restart to `loadeddata` mid-seek. Deliberate replay via the template's
  SPACE binding still works — `play()` on an ended video restarts from 0.
- Verified end-to-end: all inline scripts in the generated HTML parse
  under node, the deck the user tested was regenerated in place, and the
  **live** webrunner (which was serving it) confirmed serving the patched
  page over HTTP — port-holder checked first, per the fourth session's
  lesson. Rapid *forward* re-navigation can still theoretically stall
  (browser decode churn is outside page JS control), but back-nav no
  longer plays anything at all.
- Test count: 57 → 59 (`test_convert.py` restructured around a
  module-scoped rendered fixture so the expensive render happens once).

**Sixth session (2026-08-13/14)** — Content-quality rewrite of
`create-deck`, prompted by the user's judgment that generated decks were
"technically correct but bland" and their question whether that was a
model problem or a prompt problem. Diagnosis (measured, not guessed):
both skill-generated decks contain **zero** `.animate` calls while the
two pre-skill hand-written decks contain one each — the old skill made
decks *less* animated than no skill at all. Causes: ~90% of the skill's
words were compliance mechanics with one clause about content; motion is
invisible to every existing check (they sample the segment's final
layout only); the workflow never looked at a rendered frame; and
`theme.py` had no `heading()`, so eight section headings shipped at 48pt
sitting exactly on the safe margin. Rebuilt around "will a mid-tier
model reliably do this unsupervised" — the user runs the validation
deck through Sonnet in a fresh session on purpose:
- **Skill rewritten** (SKILL.md ~1/3 compliance-free) around: seven
  countable rules (R1 carry-forward ≤2 cleared starts; R2 something
  already on screen must change — emphasis animations explicitly don't
  count; R3 anchored non-text mobject; R4 perform every written action
  verb; R5 play budget + heading-arrives-with-figure; R6 semantic color;
  R7 prose cap), a pre-commitment **plan table** (one row per segment
  with "carried in" and "change animation" cells that must be filled
  before code), an audience setting (middle-school/high-school as a
  behavior diff table, recorded by `scaffold.py` as an `AUDIENCE`
  constant — below the docstring because the webrunner title regex is
  DOTALL), and a closed-question visual review (six questions +
  mechanical fix-or-accept + "could be prettier is not a reason" +
  restructure escape hatch if >half the segments flag). Compliance prose
  moved to `references/framework-rules.md` on the split rule *compliance
  failures are loud, content failures are silent*; `decorative=True`
  criteria narrowed (the old guidance had decks marking their own
  subject decorative — the Pythagorean deck's `proof-square` comment
  even claimed a collision that geometrically can't happen); added the
  composite-figure one-id pattern as the checked alternative.
- **`references/exemplar.md`** — one completing-the-square segment at
  target quality, built as a real deck, rendered, critiqued by the new
  review loop (two composition fixes found), then transcribed with every
  line annotated by the *move* it performs, a same-move-three-subjects
  table, and an explicit anti-copy line. The "weak version" is a pointer
  at the real `segment_the_algebra`, not a fabricated strawman.
- **`references/motion-recipes.md`** — every snippet construct-verified
  headlessly *and* rendered in one throwaway deck first. Non-obvious
  gotchas banked: a `ValueTracker` stores its value in its coordinates
  (so safe-frame-checking one raises); `clear_updaters()` before fading
  any `always_redraw`/`TracedPath` mobject; `TransformMatchingTex`
  *replaces* its input (re-track); transient overlap is free because the
  checks only sample segment ends.
- **`frames.py` built** (per-segment final frame + 6-tile contact sheet
  via ffmpeg, `python -m open_manim_slides.frames <Scene>`). Planned
  mechanism — "frame 0 of the pre-rendered `_reversed.mp4` is the final
  frame free of charge" — was **disproved during verification**:
  manim-slides splits videos > 4 s (`max_duration_before_split_reverse`)
  into chunks before reversing, so rev-frame-0 of an 8.15 s segment
  showed the ~4 s mark. (A PSNR spot-check during planning had used a
  4.15 s segment, where the error is invisible.) Switched to `-sseof`
  on the forward video. Segment order must come from `slides/<Scene>.json`
  array order — hash filenames sort meaninglessly.
- **`theme.py`**: `heading()` (36pt, margin + `SPACING_XS` slack —
  `to_edge`'s buff measures from the frame edge, not the margin) and
  `COLOR_ACCENT_2 = YELLOW_D`. **`scaffold.py`**: `audience=` param +
  the checklist comment replacing the bare `# TODO` (the smoke test
  string-replaced that exact TODO line to inject content, so it silently
  became a no-op render — re-anchored the test on the assert line).
- **Dry run** (user-approved as the before/after): executed the new
  skill end-to-end on the Pythagorean topic →
  `decks/the_pythagorean_theorem_v2.py` (original untouched). First
  render tripped the overlap check legitimately (rearranged dissection
  halves share an identical bbox — flush diagonal tiling), fixed with
  the composite-id pattern; second issue was a stale-tracking bug
  (fading a *re-wrapped* `VGroup` of tracked children leaves the tracked
  wrapper active) — both banked into `framework-rules.md`. The review
  loop then caught four real issues (undersized triangle, a stamp
  triangle lingering into the summary slide, the derived equation
  duplicating the still-visible header formula). Scored against v1:
  change-animations 2 → 12 (≥1 in all 7 segments), cleared-frame starts
  5 → 0, `Write()`-on-shapes 4 → 0, max plays/segment 7 → 4,
  decorative-on-subject 3 → 0.
- Test count: 59 → 72 (theme heading/color, scaffold audience/checklist
  + webrunner-title regression guard, `test_frames.py`).
- **Next validation step, waiting on the user**: run the new skill in a
  fresh **Sonnet** session on topic "Slope: rise over run",
  middle-school audience, then bring the deck + `media/review/` frames
  back here for scoring. The exemplar is deliberately area-flavored
  while the test topic is slope, so squares/braces/area structure
  appearing in the slope deck = measured topic-lock.

**Seventh session (2026-08-16)** — User feedback on the v2 deck, and a
new direction:
- **Pacing rule learned and banked**: the v2 algebra segment chained two
  `TransformMatchingTex` steps in one segment, so the intermediate line
  (`(a+b)² = 2ab + c²`) was on screen for ~1 s — plays inside a segment
  auto-advance, only `next_slide()` boundaries wait for the presenter.
  User-directed fix (their suggestion): each derivation step is now its
  own segment (`segment_the_algebra` → `segment_simplify` →
  `segment_cancel`, deck is 9 segments). Encoded for future generations
  in three places: R5 in `SKILL.md` ("an equation the audience must
  read gets its own segment"), the audience table's derivations row,
  and a gotcha under motion-recipes recipe 5. The exemplar was checked
  and already complies (single TMT per segment).
- **Triangle sized up again** (user-directed): seg-01 display scale
  1.45 → 1.9, extracted into a `TRI_SCALE` module constant so the
  inverse shrink in `segment_three_squares` can't drift. Note the
  review loop *did* flag this once and the fix was still too timid —
  "caught but under-corrected" is a real reviewer failure mode.
- **New direction from the user (not yet built): narration alongside
  decks.** Their framing: pacing is best solved by generating speech
  with the deck, integrated into the play menu, script visible when not
  fullscreened. Verified the carrier already exists end-to-end upstream
  (manim-slides 5.6.0): `next_slide(notes="...")` → per-slide `notes`
  in `slides/<Scene>.json` → `<aside class="notes">` + `show_notes`
  flag in the RevealJS export. So the slice is: scaffold emits a
  narration placeholder per segment, create-deck writes the script, the
  webrunner reads `notes` from the slides JSON and renders a script
  pane beside the player when not fullscreen; TTS audio is a later
  layer on the same per-segment script (and would give principled
  auto-advance timings). Design proposed to the user, awaiting their
  direction before building.

## Immediate next steps (priority order)

1. ~~Build `assert_no_overlap`~~ — **DONE** (first/second session).
2. **Fix `layers_of_the_earth.py`'s placement.** Still open — deck
   content, deliberately left for the user. The overlap checker will
   catch it the moment this deck calls it.
3. ~~Wire `assert_no_overlap` into `create-deck`~~ — **DONE**, baked into
   `scaffold.py`'s stub, not just documented.
4. ~~Fix the manifest's appearance-tracking gap~~ — **DONE**.
5. ~~Finish the design system~~ — **DONE**. Migrating the two hand-written
   dev decks onto the theme tokens is left as content work.
6. ~~PR #664 workaround~~ — **DONE**.
7. **Site build-out** (decision 4) — `webrunner/` is a real but partial
   slice (render + present). Still unbuilt: the manifest-driven
   click-to-comment flow, the apply-comments Skill, the public/author
   permission split. Natural next step: surface `track()`'s manifest ids
   in the runner's UI.
8. **Grow example content** — four dev-only decks exist locally (water
   cycle, layers of the earth, Euler's formula, the Pythagorean theorem),
   none on `main` (`decks/` is gitignored). Promoting any to a curated
   public gallery is a bigger content decision left for the user.
9. **Convex-hull + SAT for `assert_no_overlap`** — `decorative=True` is
   the short-term fix for the AABB-vs-circle false positive; a hull-based
   check would also fix the diagonal-line-vs-nearby-content case for
   genuinely independent (non-decorative) content. Evaluated and
   deliberately deferred as medium-term, not an oversight.
10. ~~Commit the accumulated work~~ — **DONE** (seventh session, at the
    user's request): eight commits split by slice (base/layout, theme,
    convert, webrunner, scaffold, frames, skill rewrite, docs), 72 tests
    green on the committed state. Not pushed.
11. **Watch for the Reveal.js background-video flash recurring.**
    `background_transition` defaults to `'none'` (abrupt cut) in
    `webrunner/render.py`'s `convert_to_html` call; user reported it
    resolved on its own so nothing was changed. If it recurs, pass
    `background_transition="fade"` — mechanism is confirmed via the real
    generated HTML/config, not speculative.

## Reference

- Repo: https://github.com/lapotist/open-manim-slides
- Upstream manim-slides bug being tracked: https://github.com/jeertmans/manim-slides/pull/664
- open-slide (design reference for *shape*, not a spec to copy blindly):
  https://open-slide.dev/, https://github.com/1weiho/open-slide
