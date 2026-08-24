# open-manim-slides — Handoff

Status: updated after the thirteenth implementation session, 2026-08-22.
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
labels on concentric circles) found two gaps the safe-frame check alone
couldn't catch: labels overlapped each other into a garbled mess
(safe-frame only guards the frame *edge*, not other elements), and the
manifest recorded only the segment `track()` was called in, not every
segment the element actually stayed visible for. Both fixed in session two.

**Second session (2026-08-10)** — Fixed both session-one gaps:
- `wait_time_between_slides` was set via a shadowing class attribute
  (written before `manim-slides` was installed, to verify against)
  instead of the real clamped `@property`, so the shadow silently
  defeated the setter. Fixed by writing through the real property.
- Manifest gap fixed by overriding `Scene.remove()` (which `FadeOut`
  routes through) to deactivate a tracked id only once its mobject
  actually leaves, so every segment it's visible in gets an appearance
  entry.
- Built `assert_no_overlap()`, baked into every scaffolded segment via
  `self.assert_no_overlap_among_tracked()` so the check is structural,
  not a convention an agent could skip.
- Built the manim-slides PR #664 workaround (`convert.py`): a
  `(Str, StrEnum)` field's `__get_pydantic_core_schema__` collapses to a
  bare string during pydantic validation, dropping the quoting that keeps
  exported Reveal.js config valid JS. Needs both the schema patch *and*
  `model_rebuild(force=True)` — patching alone doesn't touch an
  already-built schema.
- First `theme.py` slice: typography scale, color tokens, `title_slide()`.
- 17 → 28 tests.

**Third session (2026-08-10)** — Long session, several threads:
- Design system finished: spacing scale (anchored to manim's own
  `next_to`/`arrange`/`to_edge` buffer defaults, not invented numbers),
  `two_column()`, `diagram_with_caption()`. 28 → 31 tests.
- Two decks built via `create-deck` at the user's request —
  `euler_s_formula.py` and `the_pythagorean_theorem.py` (`MathTex`-based,
  `Transform`-driven derivations; needed `dvisvgm`, which the user
  installed manually). Euler's complex-plane diagram surfaced a
  structural gap in `assert_no_overlap_among_tracked()`: it compares
  axis-aligned bboxes, and any point on a circle of radius `R` centered
  at `C` is always within `[C-R, C+R]` on *both* axes, so a circle
  checked against anything on/radiating from its center false-positives
  at every angle (a diagonal line's bbox similarly swallows anything
  positioned near it). Evaluated 8 fixes (per-pair exemptions, exact
  per-shape geometry, pixel-mask rasterization, convex-hull+SAT, a
  `fill_opacity` heuristic, a circle special case, a role flag) and
  built the smallest one matching the project's "explicit, no magic"
  taste: **`track(mobj, id=..., decorative=True)`** — still gets a full
  manifest entry, just excluded from the pairwise check. Convex-hull+SAT
  would also fix the diagonal-line case for genuinely independent
  content; deferred as a documented follow-up (next-steps item 9). The
  Pythagorean deck rendered clean on the first full render by verifying
  tricky APIs headlessly first, unlike Euler's multi-round debugging.
  31 → 35 tests.
- Built `src/open_manim_slides/webrunner/` (FastAPI + plain JS, stack
  confirmed with the user first): deck discovery from source, subprocess
  `manim render` with a **real** progress bar (manim's tqdm output
  survives being piped to a non-tty subprocess — confirmed, not assumed),
  SSE streaming, HTML export via `convert_to_html` served for in-browser
  presenting. Not imported by the core package, so `fastapi`/`uvicorn`
  aren't forced on the base install. 35 → 46 tests, plus a real
  end-to-end run.
- A "flashing" report on `layers_of_the_earth` turned out to be the same
  overlap bug above, unflagged because that deck predates
  `assert_no_overlap_among_tracked()`.
- Built `assert_reasonably_centered(*mobjects, tolerance=0.2)` after the
  user flagged the Pythagorean deck's summary slide: neither existing
  check catches a composition that's in-frame and non-overlapping but
  never centered as a *group* (a title left at its default position with
  content stacked below via `next_to` only ever grows one direction).
  Calibrated against real numbers first — the buggy slide sat at -30%
  vertical offset vs. a normal diagram segment's +11%; the same pass
  showed two shipped segments on the same spectrum (+55%/+27%), surfaced
  to the user, who chose to fix only the summary slide. Opt-in
  (recommended for title/summary/"punchline" slides), and unlike the
  overlap check does **not** exclude `decorative` elements — a backdrop
  still occupies real space. 46 → 54 tests.

**Fourth session (2026-08-12)** — User reported four `webrunner` bugs;
fixed all four:
- **Presenter unresponsive unless fullscreened**: the iframe was never
  focused after `src` was set, so keyboard input went to the parent page.
  Fixed with `.contentWindow.focus()` on load, on click, and after
  `requestFullscreen()`.
- **Fullscreen-transition stall**: mitigated with a wider pre-fullscreen
  layout (`.presenting` CSS modifier) so the resize jump is smaller. Not
  fully verifiable without a real browser.
- **"12 of ~8" progress message**: the `self.play(` call-site count is a
  lower bound (one call can log more than one `Animation N` entry) and
  the display never self-corrected once exceeded. Extracted
  `_progress_from_animation_line()` (small, tested, pure) that clamps the
  displayed total upward — verified live against a render flipping
  "26 of ~27" to "28 of ~28" mid-stream.
- **"One page" — browser back/forward not tracking the loaded deck**:
  added real `history.pushState`/`popstate` handling (`?present=<url>
  &title=<title>` for the presenter, `/` for the list), including
  restoring state on reload.
- **Process-hygiene finding**: checking `lsof -i :8000` (not just that
  `curl` succeeded) caught a **webrunner server from session three still
  running two days later**, serving pre-fix code — almost certainly what
  the user was actually testing several of these reports against. Killed
  it plus two more stale processes found during later verification.
  Lesson banked: check who actually holds the port before trusting served
  code matches source.
- **Follow-up, same session**: "sometimes laggy going back and forth"
  traced by reading reveal.js 6.0.1's actual source (`gh api` against the
  exact tag, not docs) to `config.viewDistance` (default 3): a segment's
  background `<video>` is only created the first time it comes within
  view distance of the current one, so in a typical 5-8 segment deck
  later segments hadn't started loading at all until first navigated
  near. Fixed with `view_distance=50, mobile_view_distance=50` in
  `webrunner/render.py`.
- Test count: 54 → 57.

**Fifth session (2026-08-12)** — The fourth session's `view_distance` fix
didn't resolve the lag; the user's refined symptom ("stuck on some middle
state then jumps to the end; forward-only is smooth") pointed elsewhere.
Diagnosed from a **screen recording** (OBS; its own QSV-encoder failure
diagnosed en route — `MFX_ERR_UNSUPPORTED` on ICQ rate control, worked
around with FFmpeg VAAPI), frames extracted into timestamped contact
sheets:
- **Root cause, two confirmed halves.** (a) manim-slides pre-renders a
  reversed video per segment (`SlideConfig.rev_file`) and its native Qt
  presenter uses it for backward navigation, but the HTML exporter drops
  it (`copy_to(..., include_reversed=False)`) and the Reveal template
  only references the forward file. (b) reveal.js 6.0.1's
  `startEmbeddedMedia` restarts a background video from `currentTime = 0`
  every time its slide becomes current, in either direction. Net:
  "previous" replayed the target segment's *entire construction
  animation* — the recording showed exactly that (already-seen titles
  re-writing stroke-by-stroke), plus Firefox stalling frame presentation
  ~1-1.5s mid-replay under rapid navigation — the "stuck then jumps"
  report. Dimmed/black in-between frames were the decks' own opening
  `FadeOut`s replaying, not Reveal transitions (config confirmed
  `transition: 'none'`).
- **Fix: `snap_back_navigation` in `convert_to_html` (default on).** A
  script that, on backward navigation, pauses the now-current video and
  seeks it to its final frame — matching the native presenter and
  removing the replay churn. Timing subtlety from reveal.js source:
  `slidechanged` fires *before* `backgrounds.update()` restarts the video
  in the same synchronous `slide()` call, so the snap runs on a 0ms timer
  with a one-shot `play` guard (dropped after 200ms) for when Reveal
  defers the restart to `loadeddata`. SPACE-triggered replay still worked
  (`play()` on an ended video restarts from 0).
- Verified end-to-end (inline scripts parse under node; the live
  webrunner confirmed serving the patched page — port-holder checked
  first, per session four's lesson).
- **Superseded in session thirteen**: this exact fix is what caused that
  session's forward-flash symptom — see below.
- Test count: 57 → 59.

**Sixth session (2026-08-13/14)** — Content-quality rewrite of
`create-deck`, prompted by the user's judgment that generated decks were
"technically correct but bland" and whether that was a model problem or a
prompt problem. Diagnosis (measured, not guessed): both skill-generated
decks contained **zero** `.animate` calls while the two hand-written
pre-skill decks had one each — the skill made decks *less* animated than
no skill at all. Causes: ~90% of the skill's words were compliance
mechanics with one clause about content; motion was invisible to every
check (they sample only the segment's final layout); the workflow never
looked at a rendered frame; `theme.py` had no `heading()`, so eight
section headings shipped at 48pt sitting exactly on the safe margin.
Rebuilt around "will a mid-tier model reliably do this unsupervised" (the
user validates with a fresh Sonnet session on purpose):
- **Skill rewritten** (~1/3 compliance-free) around seven countable rules
  (R1 carry-forward ≤2 cleared starts; R2 something on screen must
  change, emphasis doesn't count; R3 anchored non-text mobject; R4
  perform every written verb; R5 play budget + heading-arrives-with-figure;
  R6 semantic color; R7 prose cap), a pre-commitment plan table
  (carried-in / change-animation per segment, filled before code), an
  audience setting (middle-school/high-school, recorded by `scaffold.py`
  as an `AUDIENCE` constant below the docstring because the webrunner
  title regex is DOTALL), and a closed-question visual review (six
  questions + mechanical fix-or-accept + "could be prettier is not a
  reason" + restructure escape hatch if >half the segments flag).
  Compliance prose moved to `references/framework-rules.md`;
  `decorative=True` criteria narrowed (old guidance had decks marking
  their own subject decorative); composite-figure one-id pattern added
  as the checked alternative.
- **`references/exemplar.md`** — one completing-the-square segment at
  target quality, built as a real deck, rendered, critiqued by the new
  review loop, then annotated per line by the *move* it performs, with a
  same-move-three-subjects table and an explicit anti-copy line.
- **`references/motion-recipes.md`** — every snippet construct-verified
  headlessly and rendered once. Gotchas banked: a `ValueTracker` stores
  its value in its coordinates (so safe-frame-checking one raises);
  `clear_updaters()` before fading any `always_redraw`/`TracedPath`
  mobject; `TransformMatchingTex` *replaces* its input (re-track);
  transient overlap is free (checks only sample segment ends).
- **`frames.py` built** (per-segment final frame + 6-tile contact sheet
  via ffmpeg). Planned mechanism — "frame 0 of the pre-rendered
  `_reversed.mp4` is the final frame free of charge" — was **disproved
  during verification**: manim-slides splits videos > 4s
  (`max_duration_before_split_reverse`) before reversing, so rev-frame-0
  of an 8.15s segment showed the ~4s mark. Switched to `-sseof` on the
  forward video. Segment order must come from `slides/<Scene>.json`
  array order, not hash filenames.
- **`theme.py`**: `heading()` (36pt, margin + `SPACING_XS` slack —
  `to_edge`'s buff measures from the frame edge, not the margin) and
  `COLOR_ACCENT_2 = YELLOW_D`. **`scaffold.py`**: `audience=` param + a
  checklist comment replacing the bare `# TODO` (the smoke test
  string-replaced that exact TODO line, so it silently became a no-op
  render — re-anchored on the assert line instead).
- **Dry run** (user-approved): new skill run end-to-end on the
  Pythagorean topic → `the_pythagorean_theorem_v2.py`. First render
  legitimately tripped the overlap check (rearranged dissection halves
  share an identical bbox), fixed with the composite-id pattern; second
  was a stale-tracking bug (fading a re-wrapped `VGroup` of tracked
  children leaves the tracked wrapper active) — both banked into
  `framework-rules.md`. Review then caught four real issues (undersized
  triangle, a stamp triangle lingering into the summary, a duplicated
  equation). Scored against v1: change-animations 2→12, cleared-frame
  starts 5→0, `Write()`-on-shapes 4→0, max plays/segment 7→4,
  decorative-on-subject 3→0.
- Test count: 59 → 72.
- Next validation step proposed at the time: run the new skill in a
  fresh Sonnet session on "Slope: rise over run" (middle-school) to
  measure topic-lock against the area-flavored exemplar. Superseded by
  real usage in session eight (a different topic, at the user's
  direction) and the workflow rebuild in session ten — never run as
  originally planned.

**Seventh session (2026-08-16)** — User feedback on the v2 deck, and a
new direction:
- **Pacing rule learned and banked**: the v2 algebra segment chained two
  `TransformMatchingTex` steps in one segment, so the intermediate line
  was on screen for ~1s — plays inside a segment auto-advance, only
  `next_slide()` boundaries wait for the presenter. Fixed (user's
  suggestion) by giving each derivation step its own segment (deck grew
  to 9 segments). Encoded for future generations: R5 in `SKILL.md` ("an
  equation the audience must read gets its own segment"), the audience
  table's derivations row, and a motion-recipes gotcha. The exemplar
  already complied.
- **Triangle sized up again** (user-directed): display scale 1.45→1.9,
  extracted into a `TRI_SCALE` constant so the inverse shrink elsewhere
  can't drift. The review loop *did* flag this once and the fix was
  still too timid — "caught but under-corrected" is a real reviewer
  failure mode.
- **New direction proposed by the user (not yet built): narration
  alongside decks.** Generate speech with the deck, integrated into the
  play menu, script visible when not fullscreened. Verified the carrier
  already exists upstream (manim-slides 5.6.0): `next_slide(notes="...")`
  → per-slide `notes` in the slides JSON → `<aside class="notes">` +
  `show_notes` in the RevealJS export. Slice: scaffold emits a narration
  placeholder, create-deck writes the script, webrunner renders a script
  pane beside the player when not fullscreen; TTS is a later layer on the
  same script (and would give principled auto-advance timings). Awaiting
  direction.

**Eighth session (2026-08-16, same day)** — Ran `create-deck` end-to-end
on "introducing sin, cos, and tan" (high-school, user-directed) as real
usage, not a validation dry run: `sine_cosine_and_tangent.py`, 8 segments
(labelled triangle → three ratios built on a concrete 3-4-5 triangle →
`tan = sin/cos` as its own segment → a `ValueTracker` angle sweep →
squares deriving `sin²θ+cos²θ=1` → recap). All four review rounds
surfaced issues invisible to the `assert_*` checks:
- **`Angle(Line(vertex,p1), Line(vertex,p2))` swept the reflex angle**
  (~323° instead of ~37°) — a huge loop dominating the opening segment,
  invisible to every check because it was one `decorative` composite
  with nothing to collide with; only visible in a rendered PNG. Fixed by
  building an `Arc` from computed ray angles instead of trusting
  `Angle`'s quadrant-picking (motion-recipes gotcha 10).
- **The angle-sweep segment's own geometry was underscaled** and its
  final angle (75°) too extreme, so the resulting leg-length ratio
  carried into segment 7's squares and shrank `cos²θ` to barely legible.
  Fixed by enlarging/recentering (`SWEEP_H`/`SWEEP_C` constants) and
  capping the sweep at 60°.
- **A `decorative` composite (hypotenuse square) nearly touched the next
  heading** — invisible to the overlap check by construction (decorative
  excluded from both sides) and to the safe-frame check (only ever
  called on the squares as a group, not against the heading). Caught by
  hand-tracing corner position against a known vertical band, not from
  the image alone — the general shape of the gap visual review exists
  for: two elements can each pass every automated check and still
  visually collide where no single check's scope spans both.
- Also routine: an outward brace docked flush to the frame edge blew
  past the safe margin (fixed with a larger dock buffer, not a smaller
  brace).
Final full-quality render clean; deck left uncommitted (gitignored, per
the standing scope boundary).

**Ninth session (2026-08-16, same day)** — User feedback on the trig
run, then a tooling slice:
- **Two workflow rules banked.** (a) On a "test run", don't read other
  `decks/` files as reference — it measures whether the skill's own
  written guidance suffices; recorded in `SKILL.md` itself, not only
  memory. (b) Long render→error→edit loops need brief checkpoint
  narration — several silent stretches read as "taking too long."
- **`blankspace.py` built** (user's ask: detect space genuinely left
  over, not reserved for later content — a temporal distinction, so it
  aggregates *across* segments; a cell is dead only if **no** segment
  ever fills it). Measures pixels from `frames.py` stills, not manifest
  bboxes (a bbox overstates coverage — a triangle's bbox claims its
  empty corners); crops the safe margin (which is supposed to be empty).
  Thresholds bias toward under-reporting. Reports per-segment fill %,
  largest empty block, the deck-level never-used region, and an ASCII
  map. Validated on the live deck: flagged exactly what the user
  described by eye (segments 1-4 each ~22-33% empty on the right, 14% of
  the frame never reached) — the class of defect every `assert_*` check
  is structurally blind to.
- **Wired into review Q2** (fill % from `blankspace` replacing eyeballed
  judgment) with mechanical triggers (<20%/segment fix, ≥15% dead region
  ⇒ restructure). Test count: 72 → 86.
- Deck-content fixes (user-directed, uncommitted): θ label repositioned
  onto the true bisector, triangle enlarged to unscaled 4-3-5, equations
  40→52pt.
- **Full restructure driven by `blankspace`'s numbers** (user:
  "restructure it"): the deck had no composition, just per-segment
  placement. Replaced with one two-column composition held for the whole
  deck (figure left, accumulating equation stack right, growing downward
  from a fixed top) so later segments have reserved space instead of
  leftover space. Dead space 32%→22%, largest dead region below the
  reporting threshold, per-segment fill 23.6-44.4%→29.2-54.2%.
- **Self-review of `blankspace`** (user asked what it costs): 268ms for
  an 8-segment deck, no optimization warranted. Two real defects found
  and fixed: the safe-margin crop used one fraction for both axes though
  the margin is a fixed unit count on a 14.22×8 frame (now per-axis);
  nothing detected stale stills, so editing without re-extracting
  silently reported the old layout (now compared against the slides
  JSON's mtime). Remaining limits (final-frame-only sampling, fill as
  reach not ink density, no designed-vs-wasted distinction) documented,
  not fixed.
- Gotcha re-confirmed: squares built via `.move_to(computed_center)`
  against triangle legs tripped the overlap check on rounding — fixed by
  building as `Polygon`s from the triangle's own corner points so
  touching edges share identical floats (same lesson as the Pythagorean
  deck's `_corner_points()`).

**Tenth session (2026-08-16, same day)** — Workflow rebuild, after
measuring why the session's own `create-deck` run took 30+ minutes.
- **The measurement**: machine time for the whole run was **2.4 min**
  (8×`-ql` render at 9.2s, 1 full render at 47s, 3×`frames.py` at 5s).
  ~28 min was ~46 sequential model round-trips — the renderer was never
  the bottleneck, round-trip *count* was, and the largest block was 12
  trips (~8 min) finding five layout errors one render at a time, since
  a render aborts at the first failure. (A prior version of this
  analysis blamed context growth; corrected — this session runs a
  1-hour prompt cache, so a stable prefix is cheap and 408 lines of this
  file cost ~6.4k tokens once, not per turn.)
- **`validate.py` built** — runs `construct()` and every check with no
  rendering, ~2s, reports *all* failing segments in one pass (verified:
  a deliberately broken 4-error deck reports 4 in 1.18s). Two
  subtleties: scene updaters must be ticked after applying animations or
  `always_redraw` geometry is stale for the next segment; cascade
  detection must match on the *coordinates* in a failure message, not
  its text, since `assert_no_overlap` names whichever of a pair it
  reaches first.
- **`create-deck` restructured around it**: new step 5 validates before
  any render ("fix everything, re-run until clean, only then render").
  Step 2 gained a "commit to one composition" section (two-column
  default, real frame dimensions, size-to-fill instruction, module
  constants for column centers) — encoding what this session arrived at
  after four rounds on the trig deck. Review commands now one quiet
  block, images read in one batch, fixes batched.
- Test count: 89 → 101.
- **`progress.py` built** (user asked for a progress/time-budget
  indicator). Marks phase boundaries, renders a one-line bar, and given
  a budget judges drift and says what to cut; budget also scales the
  plan up front. Two decisions: drift judged at *phase entry* not live
  (time inside a phase is that phase's allocation — judging live flagged
  every run as behind immediately, a real bug caught by testing all
  three states); the status line is computed but never counted as
  displayed, since a command's stdout reaches the agent, not reliably
  the user's terminal — the skill requires the agent to relay it.
  Test count: 101 → 125.

**Eleventh session (2026-08-20)** — A `create-deck` run reproduced a
defect the instructions already warned about: a plain `Transform`
between two different headings, interpolating glyph *outlines* and
spending most of the play as unreadable shapes. The user fixed the deck
and moved the rule into a gate: `IllegibleTextMorph` in `validate.py`, a
`FadeTransform` section in `motion-recipes.md`, review question Q7.
**Confirms the session's recurring lesson from the other direction:
written guidance didn't bind, the same rule as a mechanical check does.**
Also uniquely invisible to the review — the final frame is the one
moment nothing is moving.
- Verified against a deck holding one bad swap plus every shape that
  must *not* fire (`FadeTransform`, `TransformMatchingTex`, shape→shape,
  a two-glyph number, a bad morph nested in `LaggedStart`). All correct.
- Shipped with zero tests — the same failure mode it exists to prevent —
  so six were added, including the glyph-count-not-string-length rule
  (`\tfrac12` is eight source characters but one small fraction). Test
  count: 125 → 129.
- Stale docs corrected: `SKILL.md` still advertised "all four checks";
  `AGENTS.md` didn't mention the morph check.

**Twelfth session (2026-08-20)** — Built `decks/absolute_value.py`
(9 segments, high-school), which surfaced one genuinely new framework
bug.
- **Two animations driving one mobject in a single `play()` can deadlock
  manim's encoder.** Here `FadeOut(self.figure)` alongside
  `Transform(self.line, axes.x_axis)`, where `line` was a child of
  `figure`. The render hung at animation 29/30 — **0% CPU, futex wait,
  17 threads, no traceback, no further partial movie files** — reading
  as a slow render, not a failure (~13 of the run's 30 minutes).
  Diagnosed by checking the partial-movie count had stopped advancing,
  not by trusting the absence of output (`tail` buffers).
- **Fixed structurally**: `validate.py` now reports
  `ConflictingAnimations`, comparing mobject *families* across one
  `play()`'s top-level arguments. The harness **cannot reproduce the
  hang** (applies animations sequentially), so the check is structural
  by necessity — same reasoning as `IllegibleTextMorph`. Also banked as
  motion-recipes gotcha 11. Test count: 129 → 132.
- **The review loop worked as designed.** One round flagged exactly
  three segments on mechanical triggers, all fixed in one batch. Every
  segment ended ≥20% fill (21.5-41.7%), largest dead region 12%→8%.
- **A measurement that corrected an intuition**: raising a figure to
  "use the middle" *lowered* fill (18.1%→16.0%) — fill counts occupied
  cells, so concentrating content reduces it; spreading is what helps.
  Reverting position while keeping enlarged type gave 21.5%. Worth
  remembering before "centering" a sparse slide.
- Timing (`progress report`): 30m total, of which the deadlock was
  13m14s.

**Thirteenth session (2026-08-22)** — User screen-recording of the
`absolute_value` deck: "two problems, end state flashes after right key,
lag when going back and forth, both issues meant to be accounted for in
previous sessions." Both were real, both traced to the *fifth* session's
own fix, and the deck itself was never touched — the user's explicit
requirement was that this be handled for every future generation, with
no reference decks and under time pressure ("don't fix the slide").

- **The fifth session's fix caused the first symptom.** Snapping
  backward navigation to a segment's final frame parks that video at its
  end; reveal.js restarts a video from `currentTime = 0` whenever its
  slide becomes current, so the *next forward entry* into that segment
  has to seek from the end back to 0, and the compositor keeps
  presenting the old frame until the new one decodes. The viewer sees
  the segment's ending — the spoiler — before it builds. Backward replay
  had been traded for a forward flash; both are the same cost, seeking a
  video that is already on screen.
- **`currentTime` cannot see this, which is why it survived two
  sessions.** It updates synchronously while the previous frame is still
  presented, so a video reads `currentTime == 0` while the end frame is
  on screen. Instrumenting `requestVideoFrameCallback` (the `mediaTime`
  of frames actually *presented*) showed it immediately: the stale end
  frame stood 37ms in headless Firefox on forward re-entry, consistent
  with the ~400ms measured off the user's own recording on a
  GPU-composited desktop.
- **Fix: the invariant is "never seek a video that is on screen"**
  (`instant_navigation`, renamed from `snap_back_navigation` — the old
  name describes only half of what the script now does, and
  misremembering its scope is part of how this recurred). Every video is
  parked, while hidden, at the pose it will next be entered with: left
  going forward → parked at its final frame; left going backward →
  parked at 0. Entering then needs no seek in either direction.
- **Two rejected alternatives, both measured, both recorded in the
  source comment** so they aren't re-tried as "simplifications" later.
  Calling `play()` on the entering video to pre-empt Reveal (which only
  resets a video that is `paused || ended`) fails: a segment that ran to
  completion *is* `ended`, and `play()` on an ended element seeks back
  to the start per spec — two of three backward entries still painted
  frame 0. What works is shadowing `paused`/`ended` with own accessors
  for the remainder of Reveal's synchronous `slide()` call, then
  deleting them. Relatedly, videos park at `duration - EPSILON`, never
  at `duration`, for the same `ended` reason.
- **A residual, deliberately tolerated, found by an adversarial
  rapid-navigation test.** Re-entering a segment quickly can flash, for
  ~10-15ms, the frame the viewer was *already looking at* when they
  left — a hidden video's composited surface can lag its `currentTime`,
  and no page JS can force a present while nothing is showing it. That's
  a hiccup on already-seen content, categorically different from showing
  unseen content (above all an ending). `playback.py`'s pose tolerance
  scales with segment length (`max(0.5s, 25% of duration)`) rather than
  being silently widened to pass — proven the check still discriminates:
  0 of 20 wrong on the fixed export under rapid navigation (0.4s settle)
  vs. 6 of 20 on the old one.
- **New `playback.py`** — the durable half of the answer: drives real
  headless Firefox over WebDriver BiDi (stdlib only — a ~90-line
  WebSocket client, no new dependency, no Node), walks the deck with the
  arrow keys, and reports any navigation where the wrong frame is on
  screen. Asserts the *pose*, never the timing, since the magnitude is
  environment-specific while the wrong-pose condition is not.
- **Why this shape, given the constraint.** The fix lives in the export
  path, so every future deck gets it with zero agent effort — nothing to
  remember, nothing to cut under a tight budget, no reference deck
  needed. The check is out-of-band: `pytest` (~11s, skipped without
  Firefox) against the finished artifact, never a step in producing
  one — `create-deck` needed no new step and got none.
- Test count: 132 → 141. The end-to-end browser test was itself verified
  to fail when the fix is disabled — a check that cannot fail is not a
  check.

## Immediate next steps (priority order)

1. ~~Build `assert_no_overlap`~~ — **DONE** (session two).
2. ~~Wire `assert_no_overlap` into `create-deck`~~ — **DONE**, baked
   into `scaffold.py`'s stub.
3. ~~Fix the manifest's appearance-tracking gap~~ — **DONE** (session
   two).
4. ~~Finish the design system~~ — **DONE**. Migrating the two
   hand-written dev decks onto theme tokens is left as content work.
5. ~~PR #664 workaround~~ — **DONE** (session two).
6. **Site build-out** (decision 4) — `webrunner/` is a real but partial
   slice (render + present). Still unbuilt: the manifest-driven
   click-to-comment flow, the apply-comments Skill, the public/author
   permission split. Natural next step: surface `track()`'s manifest ids
   in the runner's UI.
7. **Grow example content** — nine dev-only decks exist locally now
   (water cycle, layers of the earth, Euler's formula, two versions of
   the Pythagorean theorem, sin/cos/tan, absolute value, probability
   combinations, what is a number), none on `main` (`decks/` is
   gitignored). Promoting any to a curated public gallery is a bigger
   content decision left for the user.
8. **Convex-hull + SAT for `assert_no_overlap`** — `decorative=True` is
   the short-term fix for the AABB-vs-circle false positive; a
   hull-based check would also fix the diagonal-line-vs-nearby-content
   case for genuinely independent (non-decorative) content. Evaluated
   and deliberately deferred as medium-term, not an oversight.
9. ~~Watch for the Reveal.js background-video flash recurring.~~ —
   **DONE** (session thirteen). It recurred, and it was not
   `background_transition` — it was the fifth session's own snap fix
   parking videos at their end, so the next forward entry flashed that
   ending. Fixed via the never-seek-a-visible-video invariant in
   `convert.py`, guarded by `playback.py` in `pytest`. If something in
   this area is ever suspected again, run
   `python -m open_manim_slides.playback <exported.html>` first — it
   answers the question mechanically instead of by eye.
10. **Deck series — shared context across related decks** (user's idea,
    not yet built). Every `create-deck` run is currently independent, so
    a second deck on the same topic re-decides everything the first one
    already settled: which color means which quantity, how the
    recurring figure is oriented, which symbols the audience has already
    met. The framing that makes this concrete: **R1 (carry something
    forward) lifted from the segment level to the deck level** — deck
    N+1 should open by *changing* deck N's closing figure, exactly as
    segment 4 opens by changing segment 3's.
    Sketch: a series file (`decks/<series>/series.json`) that
    `create-deck` reads before planning and appends to after building,
    carrying (a) audience, (b) color→meaning bindings, (c) figures
    established and their orientation, (d) symbols already introduced —
    so the high-school "≤8 new symbols" budget becomes cumulative across
    the series, (e) what each prior deck covered. Open questions: how a
    series is declared (directory vs explicit arg), and whether the
    carried closing figure is re-derived from source or from manifest
    bboxes. This pulls the opposite direction from the test-run rule
    above (load *less* context vs. *more*) — and that is correct: a test
    run simulates a real user's empty environment, while a series
    deliberately carries real, author-owned state forward.

## Reference

- Repo: https://github.com/lapotist/open-manim-slides
- Upstream manim-slides bug being tracked: https://github.com/jeertmans/manim-slides/pull/664
  (merged 2026-08-20, not yet released — still on 5.6.0 from 2026-04-15;
  the workaround in `convert.py` stays until the floor moves past
  whichever release ships it)
- open-slide (design reference for *shape*, not a spec to copy blindly):
  https://open-slide.dev/, https://github.com/1weiho/open-slide
