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
- `src/open_manim_slides/layout.py` — safety primitives, one slice below
  the design-system layer in `theme.py`:
  - `assert_within_safe_frame(mobj)` / `assert_no_overlap(*mobjects)` —
    margin- and collision-safety, raise at construction time.
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
  - Workaround for an unmerged upstream manim-slides bug
    ([PR #664](https://github.com/jeertmans/manim-slides/pull/664)):
    enum-typed Reveal.js config options lose their quoting during pydantic
    validation, producing invalid JS. Remove once the upstream PR merges.
  - `snap_back_navigation` (default on): the upstream HTML export drops
    the pre-rendered reversed videos its native presenter uses, and
    reveal.js restarts a background video from 0 whenever its slide
    becomes current — so backward navigation replays the whole segment
    animation. The injected script snaps backward navigation to the
    segment's final frame instead. See the long comment above
    `_SNAP_BACK_NAVIGATION_SCRIPT` for the full mechanism.
- `src/open_manim_slides/scaffold.py` — deterministic deck-file generator,
  not agent-authored: given a title, segment list, and optional
  `audience` ("middle-school"/"high-school", emitted as a module-level
  `AUDIENCE` constant — deliberately *below* the docstring, because the
  webrunner's title regex captures everything between the docstring
  quotes), produces the file's structure (imports, class, one function
  per segment, each pre-wired to call
  `self.assert_no_overlap_among_tracked()` beneath a content-rules
  checklist comment the author deletes as they fill the segment in).
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

## Testing

```bash
pytest
```
