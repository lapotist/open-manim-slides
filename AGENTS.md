# AGENTS.md

Canonical, agent-agnostic instructions for working in this repo. Claude
Code reads this file via a `CLAUDE.md` symlink; other agents read it
directly. Skills live under `.agents/skills/<name>/SKILL.md`, with
`.claude/skills/<name>` as a symlinked projection for Claude Code's
discovery mechanism — that pattern is adopted directly from
[open-slide](https://github.com/1weiho/open-slide), not designed fresh.

## What this project is

An open-source framework for building [Manim Slides](https://github.com/jeertmans/manim-slides)
presentations, inspired by [open-slide](https://open-slide.dev/) — a
controlled, skill-driven workflow for generating and iterating on slide
decks with an AI coding agent. See `HANDOFF.md` for the design background
and full session-by-session history (decisions made, why, what's left).

## Workflow

- **Read `HANDOFF.md` before doing anything else, if the session is new, or after /clear** It's the current
  status doc, not just an initial design record.
  **Exception — a test run of a skill.** When the user invokes a skill and
  calls it a test run, they are simulating a real invocation, and a real
  user has installed this package to build something: they have no
  `HANDOFF.md`, no `decks/`, no dev history. Loading any of it measures a
  context that no real run would ever have. Read only what the skill
  itself directs you to.
- **Framework work can proceed autonomously; deck *content* can't** —
  fixing or authoring anything under `decks/`, curating examples, or
  designing the review site is reserved for explicit user direction. See
  `HANDOFF.md`'s standing scope boundary note.
- **After real work, update `HANDOFF.md`'s session history** with what
  changed and *why* — the reasoning is the point, not a diff. Update this
  file's Architecture section too if files or public APIs changed.
- **Compact either file when it's grown unwieldy** from session-by-session
  accumulation (repeated verification narration, fragmented sections from
  incremental edits). Cut prose, not substance — keep every decision, root
  cause, and non-obvious reasoning; merge fragments into one coherent
  entry instead of truncating history.
- **Don't commit without being asked.** Work has accumulated uncommitted
  across multiple sessions on purpose — see `HANDOFF.md`'s next-steps list.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires system `cairo` and `pango` development headers for the `manim`
dependency `manimpango` to build (see `README.md`).

## Architecture

- `src/open_manim_slides/base.py` — `Slide`, the framework's base class
  (subclasses `manim_slides.Slide`):
  - Fixes the segment-transition flash (`wait_time_between_slides`
    defaults to `0` upstream) by setting it through the real property,
    not a shadowing class attribute.
  - `track(mobj, id="...")` tags an element with a stable id, written to
    an ID-addressable manifest (`<DeckClass>.manifest.json`) at the end of
    rendering — the foundation for the not-yet-built review site. An id
    gets an `appearances` entry for every segment its mobject is actually
    still on screen for, not just the segment `track()` was called in.
    Duplicate `id` within one segment raises; reuse across segments is
    expected.
  - `assert_no_overlap_among_tracked()` — pairwise overlap check across
    every currently-active, non-decorative tracked element. Scaffolded
    decks call this automatically at the end of every segment.
  - `track(mobj, id="...", decorative=True)` opts an element out of that
    check while still recording it in the manifest — for backdrop/
    indicator geometry (axes, guide circles, a `SurroundingRectangle`)
    where an axis-aligned bbox is structurally a bad proxy (any point on a
    circle is always within that circle's own bbox on both axes, so
    checking a circle against anything on/near it false-positives at
    every angle).
  - `assert_reasonably_centered_among_tracked()` — see `layout.py` below;
    unlike the overlap check, does **not** exclude `decorative` ids.
  - `find_text_over_decorative()` — the pair no other check's scope spans
    (sessions eight and fourteen): tracked text landing on a `decorative`
    element's strokes, which the overlap check cannot see because it drops
    decorative ids from *both* sides. Reports rather than raises, and
    `validate.py` is what calls it; text is found by descending into
    tracked groups, since a caption is as often a group's child as a
    tracked mobject in its own right.
- `src/open_manim_slides/layout.py` — safety primitives, one slice below
  the design-system layer in `theme.py`:
  - `assert_within_safe_frame(mobj)` / `assert_no_overlap(*mobjects)` —
    margin- and collision-safety, raise at construction time.
  - `find_text_over_ink(texts, backdrops, clearance=0.08)` — the geometry
    under `find_text_over_decorative`: does a backdrop's *stroke* run
    through a text's box? Three decisions are load-bearing, each measured
    over 77 segments of 11 decks. It walks the polyline through each
    leaf's Bezier control points, because a bounding box reports every
    legitimate adjacency (25 findings, nearly all benign) while the
    control points *alone* miss an axis line running through a caption —
    it has four of them, all at its ends. Only text is tested, because
    non-text over a backdrop is routinely correct (a plotted curve crosses
    its own axis by construction). And a backdrop whose bbox contains the
    text is framing it, not colliding with it. The 0.08 clearance sits
    mid-plateau: the finding set is identical from 0.0 to 0.08, and the
    first false positive arrives at 0.12.
  - `assert_reasonably_centered(*mobjects, tolerance=0.2)` — checks the
    *combined* bounding box sits near the frame's true center, catching a
    composition that's in-frame and non-overlapping but never recentered
    as a group (e.g. a title left at its default position with more
    content stacked below it, which only ever grows one direction). Not
    wired into scaffolded segments automatically — call it deliberately
    on slides where centering is the point (a title, a summary, a boxed
    result), not diagram-heavy layouts that naturally sit off-center.
- `src/open_manim_slides/theme.py` — the design system: a typography scale
  (`FONT_SIZE_TITLE`/`HEADING`/`BODY`/`CAPTION`), a spacing scale
  (`SPACING_XS`/`SM`/`MD`/`LG`/`XL`, anchored to manim's own `next_to`/
  `arrange`/`to_edge` defaults), a color palette on manim's own color
  constants (`COLOR_TEXT`/`MUTED`/`ACCENT`/`ACCENT_2`/`BACKGROUND` —
  `ACCENT_2` exists so a segment comparing two things can color-code
  both), and four templates: `title_slide()`, `heading()` (36pt
  per-segment heading pinned near the top with slack past the safe
  margin — the `title_slide(...).to_edge(UP)` idiom it replaces put a
  48pt heading exactly on the margin), `two_column()`,
  `diagram_with_caption()`. Deeper palette work (contrast-checked custom
  hues) is a future slice.
- `src/open_manim_slides/convert.py` — the project's HTML export path,
  `convert_to_html(...)`, a drop-in replacement for the CLI conversion
  with two fixes:
  - Workaround for a merged-but-unreleased upstream manim-slides bug
    ([PR #664](https://github.com/jeertmans/manim-slides/pull/664),
    merged 2026-08-20): enum-typed Reveal.js config options lose their
    quoting during pydantic validation, producing invalid JS. Remove once
    this project's manim-slides floor moves past whichever release first
    ships the fix — not yet out as of 5.6.0 (2026-04-15, predates the
    merge).
  - `instant_navigation` (default on): reveal.js restarts a background
    video from 0 whenever its slide becomes current, in *either*
    direction, because the HTML export drops the pre-rendered reversed
    videos its native presenter uses. Two symptoms, one cause: backward
    navigation replays the whole segment animation, and forward
    re-entry into a segment left parked at its end flashes that ending —
    the spoiler — until the seek back to 0 repaints. **The invariant the
    injected script keeps: never seek a video that is on screen.** Each
    one is parked, while hidden, at the pose it will next be entered with
    (left going forward → parked at its end; left going backward → parked
    at 0), so entering needs no seek in either direction. See the long
    comment above `_INSTANT_NAVIGATION_SCRIPT` — it records which
    alternatives were measured and rejected, because the obvious
    simplifications of this script are the two bugs.
    Verify with `playback.py` below; do not "clean it up" without
    re-running that.
- `src/open_manim_slides/scaffold.py` — deterministic deck-file generator,
  not agent-authored. Takes the `create-deck` plan table directly
  (`Segment(name, shows, carries, produces)`, or plain names for the
  legacy form) plus an optional `audience` ("middle-school"/"high-school",
  emitted as a module-level `AUDIENCE` constant — deliberately *below* the
  docstring, because the webrunner's title regex captures everything
  between the docstring quotes). It emits the file's structure *and its
  authoring context*, which is the load-bearing part:
  - a **composition block** (`SAFE_X`, `COL_LEFT_X`, `COL_RIGHT_X`,
    `COL_W`, `ROW_Y`, `HEAD_Y`) derived from the real frame, with the
    column half-width **floored** rather than rounded so a slot's outer
    edge cannot land outside the bound it came from — placing against
    these names cannot fail the safe-frame check;
  - a **declaration of every cross-segment attribute** as a bare
    annotation. Annotations create no attribute, so a forgotten handoff
    still raises `AttributeError` — the benefit is that the name is
    written down once where both the producing and consuming segment can
    see it, instead of being re-invented at both ends. Assigning defaults
    here would trade a loud failure for a silent `None`;
  - per segment, what it **carries in**, what it must **hand off**, and
    the audience's play/word budget, so R5's ceiling is at the point of
    writing rather than in a table read thirty turns earlier;
  - `check_plan()`, which runs at scaffold time and **rejects the plan**
    if a segment carries a name no earlier segment produces (the
    `AttributeError`-cascade class, killed before any code exists) or if
    more than `MAX_CLEARED_STARTS` segments begin from a cleared frame
    (R1). Segment count against the audience is returned as an advisory
    note, not raised — a deliberate outline may differ.

  The motivation is measured, from six real build transcripts: `validate`
  made each check ~4.5× cheaper without reducing how *often* the agent
  checked (one build: 15 `validate` runs across 54 edits, in
  `AUTHOR AUTHOR VALIDATE` cycles; an earlier one: 23 renders). Round-trip
  *count* is what a build spends. The two classes driving those cycles —
  state handoff and invented coordinates — are both decided before any
  check can run, so they are answered in the file the agent starts from.
- `src/open_manim_slides/frames.py` — per-segment review-frame extractor
  (`python -m open_manim_slides.frames <SceneName>`): reads
  `slides/<Scene>.json` in array order (the hash filenames sort
  meaninglessly) and writes, per segment, a final-frame PNG plus a
  6-tile contact sheet to `media/review/<Scene>/` via ffmpeg. The final
  frame is seeked from the *forward* video with `-sseof`; frame 0 of the
  pre-rendered `_reversed.mp4` looks equivalent but is a mid-segment
  state for videos longer than manim-slides'
  `max_duration_before_split_reverse` (4 s) — see the module docstring.
  Powers the `create-deck` skill's look-at-the-frames review step.
- `src/open_manim_slides/progress.py` — phase timer and time budget for a
  deck build (`python -m open_manim_slides.progress start|phase|report
  <Deck> [budget]`, state in `media/progress/<Deck>.json`). Wall clock
  between phase calls includes the agent's own thinking, so this measures
  what render timings never could: drafting and code writing are most of
  a run's cost and were previously invisible. With a budget it judges
  drift at each boundary and says what to cut, scoped to the phase being
  entered. Two decisions worth keeping: drift is judged at the moment a
  phase *starts*, not live, because time spent inside a phase is that
  phase's own allocation and comparing live elapsed against
  expected-at-entry flags every run as behind the moment it starts work
  (budget *exhaustion* is still judged live); and the status line is only
  computed here, never displayed — a command's stdout goes to the agent,
  not reliably to the user's terminal, so `SKILL.md` requires the agent to
  relay the line in its own visible reply.
- `src/open_manim_slides/validate.py` — headless layout validation
  (`python -m open_manim_slides.validate decks/<slug>.py [ClassName]`):
  runs `construct()` and every check (safe frame, overlap, centering,
  duplicate ids) without rendering a frame — ~2 s versus ~9 s for a `-ql`
  render, and it reports **every** failing segment where a render aborts
  at the first. Two substitutions make it work: `play()` applies each
  animation's end state instantly (begin → interpolate(1) → finish →
  clean up) then ticks scene updaters once, because `always_redraw`
  mobjects only regenerate on a tick and a later segment reading their
  geometry would see a stale pose; and `next_slide()` only snapshots the
  segment, skipping manim-slides' file bookkeeping (which needs rendered
  video), while keeping the segment-index advance that makes duplicate-id
  detection work. Each `segment_*` method is wrapped so a failure is
  recorded and the run continues. It also reports `IllegibleTextMorph` —
  a plain `Transform` between two different multi-glyph strings, which
  interpolates glyph *outlines* and so spends most of the play as
  unreadable shapes. That one is uniquely invisible to the frame review
  (the final frame is the one moment nothing is moving), which is exactly
  why it belongs in a mechanical gate. Smallness is judged by counting
  drawable glyphs, not string length, because `tex_string` is LaTeX
  source — `\tfrac12` is eight characters but one small fraction.
  `FadeTransform`, `TransformMatchingTex`, `.animate`, and shape-to-shape
  transforms are deliberately not flagged.
  It reports `TextOnDecorative` from `base.py`'s finder above, and two
  content rules that were previously self-graded prose: `NoChangeAnimation`
  (R2 — at least one animation per segment altering something already on
  screen, two for middle school, reading the deck's `AUDIENCE` constant,
  which nothing had ever read; segment 0 is exempt, since a cleared frame
  has nothing to change) and `UnperformedAction` (R4 — on-screen prose
  promising an action while nothing but text is animated). Both are floors,
  not the rules: whether the change *carries the idea* is not countable.
  The emphasis animations must be excluded **by class before descending**,
  because `Indicate` is a `Transform` subclass and `Circumscribe`/`Flash`
  are `AnimationGroup`s — otherwise a pulse would satisfy R2, which is
  exactly what R2 says doesn't count.
  `_instant_play` mirrors `Scene.compile_animation_data`'s
  `add_mobjects_from_animations`: anything animated that is not already in
  the scene gets added. Without it the harness's scene graph drifts from a
  real render's — a `Transform`ed mobject is on screen in the render and
  absent here — and any check reading `scene.mobjects` silently reads the
  wrong scene. It also reports
  `ConflictingAnimations` — two animations in one `play()` whose mobject
  *families* intersect, the classic case being `FadeOut(group)` alongside
  `Transform(child_of_group, ...)`. Manim 0.20 can deadlock its encoder on
  that: the render hangs at 0% CPU with no traceback and no further
  partial movie files, so it reads as a slow render rather than a bug.
  The harness cannot reproduce the hang (it applies animations one at a
  time), which is exactly why the check is structural rather than
  behavioural. Failures downstream of another are
  flagged, matched on the *coordinates* in the message rather than its
  wording, since `assert_no_overlap` names whichever of a pair it reaches
  first. Manim's own `--dry_run` is not a substitute: it crashes under
  manim-slides (`scene_file_writer` IndexError on the first `play()`).
- `src/open_manim_slides/blankspace.py` — dead-space detector
  (`python -m open_manim_slides.blankspace <SceneName>`): reduces the
  `seg-NN-final.png` stills `frames.py` writes to a 16x9 occupancy grid
  over the safe frame, reports per-segment fill % and — the point — any
  region **no segment ever uses**, with an ASCII map. Three choices are
  load-bearing: it measures *pixels*, not the manifest's bboxes (a bbox
  overstates coverage — a triangle's bbox claims its empty corners — so
  bbox-based emptiness would under-report exactly what's worth finding);
  it aggregates *across* segments (space that fills up later was
  reserved, not wasted, and only a never-reached cell is dead); and it
  crops the safe margin (which is supposed to be empty). Thresholds bias
  toward under-reporting, so a region it calls dead is genuinely
  untouched. Answers the `create-deck` review's Q2 mechanically instead
  of by eye.
- `src/open_manim_slides/playback.py` — navigation check for an exported
  deck, driven through real headless Firefox
  (`python -m open_manim_slides.playback <exported.html>`; stdlib-only —
  it speaks WebDriver BiDi over a ~90-line WebSocket client, so there is
  no new dependency and no Node). It walks the deck with the arrow keys
  and reports any navigation where the viewer would see the wrong frame.
  Why it exists: this class of bug is invisible to every other check here
  — the deck renders correctly and every frame is right; what is wrong is
  *which already-decoded frame the compositor is still showing* when a
  slide becomes current. `currentTime` cannot see it (it updates
  synchronously while the old frame is still presented — that gap is the
  flash), so the check reads `requestVideoFrameCallback`'s `mediaTime`,
  i.e. the frames actually presented. It asserts the *pose* (0 going
  forward, final frame going backward) and never the timing: the
  magnitude is environment-specific (a stale frame standing 37 ms under
  headless software compositing stood ~400 ms on a GPU-composited
  desktop) while the wrong-pose condition is not. Runs on `pytest`
  (~11 s, skipped without Firefox) and never during a deck build — it
  checks the finished artifact, it is not a step in producing one.
- `src/open_manim_slides/cli.py` — the `open-manim-slides` console script
  (`init`, `doctor`, `version`), which is what makes a *fresh install*
  usable. The skill files are the workflow, so the wheel force-includes
  `.agents/skills` as `open_manim_slides/_skills` and `init` copies them
  back out into a project (plus a minimal `AGENTS.md`, its `CLAUDE.md`
  symlink, a `.claude/skills` projection, and `decks/`). That generated
  `AGENTS.md` is deliberately short: this repo's own is 278 lines of
  internals that the harness auto-loads through `CLAUDE.md` before any
  skill runs, which is exactly the context a real user does not have —
  reproducing it in generated projects would rebuild the leak that the
  skill's test-run rule exists to avoid, and cannot itself prevent.
  `doctor` reports python/ffmpeg/manim/manim-slides/manimpango plus
  optional latex/dvisvgm/firefox, and notes when the installed manim
  differs from `VERIFIED_MANIM`, the release the motion recipes were
  checked against. **`__init__.py` re-exports lazily (PEP 562) for this
  module's sake**: `doctor` has to run on a machine where manim failed to
  build (the likeliest first-install state, since manimpango compiles
  against system cairo/pango), and eager re-exports made the diagnostic
  crash with the very `ModuleNotFoundError` it exists to report.
- `npm/` — the `npx open-manim-slides@latest new <dir>` bootstrapper: a
  zero-dependency Node script that creates the project directory, builds a
  venv, installs the Python distribution into it, and runs
  `open-manim-slides init`. Node is the delivery mechanism, not a
  dependency of the framework — `npx <pkg>@latest` is the widely-available
  command that fetches a current version every time with nothing installed
  globally to go stale, which is what a clean measurement of the authoring
  workflow needs. `--from pypi` pins the Python distribution to the npm
  package's own version so the two releases cannot drift; the default
  (`git`) needs no registry publish. Not published to either registry yet
  — that is the user's call.
- `src/open_manim_slides/webrunner/` — optional local web UI
  (`pip install -e ".[web]"`, then `./run-webrunner.sh`): lists decks
  under `decks/`, renders one on click with a live progress bar (parsed
  from manim's real tqdm output, not simulated), and presents the result
  in-browser. Not imported by the core package. `render.py` shells out to
  `manim render` as a subprocess per render; `app.py` is the FastAPI route
  layer, streaming progress over Server-Sent Events; the finished deck is
  exported via `convert.convert_to_html` and served directly.

## Authoring convention

**One file per deck.** Each `self.next_slide()` segment is its own
top-level method (`segment_<name>`), called in sequence from `construct()`.
Chosen over open-slide's one-file-per-slide convention because a Manim
scene's segments routinely share state (a persisting title, a diagram
built up across segments) in a way independent React components don't —
see `HANDOFF.md` decision 2. Use `create-deck` to generate a new deck
rather than hand-writing this structure. `decks/` is gitignored — dev-only
content, not curated public examples yet (see `HANDOFF.md`).

## Skills

- `create-deck` (`.agents/skills/create-deck/SKILL.md`) — plans a deck
  against seven countable content rules (carry-forward, change-not-appear,
  anchored figures, perform-what-you-write, play budget, semantic color,
  prose cap) and an audience setting, scaffolds via `scaffold.py`, fills
  in segments, then runs a closed-question visual review over
  `frames.py` output. References in
  `.agents/skills/create-deck/references/`: `exemplar.md` (one rendered
  segment at target quality, annotated by *move*), `motion-recipes.md`
  (verified animation snippets, gotcha-first), `framework-rules.md`
  (tracking/check mechanics, narrowed `decorative=True` criteria).
  Calling a run a "test run" suppresses reading other `decks/` files as
  reference, so the run measures the skill's own written guidance.

## Testing

```bash
pytest
```

Includes one end-to-end browser test (`tests/test_playback.py`, ~11 s)
that walks a real exported deck in headless Firefox and fails if any
navigation shows the viewer the wrong frame. It skips when Firefox is
absent rather than failing, so **a green suite on a machine without
Firefox has not checked navigation** — run it somewhere that has one
before trusting a change to `convert.py`'s injected script.
