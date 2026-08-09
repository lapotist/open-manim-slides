# open-manim-slides — Handoff

Status: updated after the first implementation session, 2026-08-09.
Supersedes the original pre-initialization handoff (also written
2026-08-09, same day — this project moved from "no code" to "committed,
pushed, and stress-tested" in one session). The repo is now real: git
initialized, MIT-licensed, pushed to **https://github.com/lapotist/open-manim-slides**
(public). Read this file before doing further work here — it's the
authoritative summary of what's decided, what's built, and what's next.

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
code from it has been ported** — see "Decisions made," below.

## Decisions made this session

These were open questions in the original handoff; all are now resolved.

1. **No porting from the source repo — design fresh instead.** The user's
   explicit call: `carlo_manim` (`layout.py`/`attention.py`/`base.py`) and
   the old QA review site are both "not well made," and should not be used
   as reference or inspiration, not just left unported. The framework's
   design-system layer and its review/editing site are both original design
   work addressing the same problem spaces, not extractions.
2. **Authoring unit: one file per deck, segments as top-level functions.**
   open-slide's one-file-per-slide convention doesn't transfer cleanly — a
   Manim scene's segments routinely share state across `self.next_slide()`
   boundaries (a persisting title, a diagram built up over several
   segments) in a way independent React components don't. Chosen: one file
   per deck, each segment as its own method (`segment_<name>`), called in
   sequence from `construct()`. A harder alternative (true file-per-slide,
   with a `track()`-based state-handoff registry) is a documented future
   path if this convention proves limiting, not a current bet.
3. **Skills are canonical plain files, Claude Code gets a symlinked
   projection.** Adopted directly from open-slide's real (verified)
   implementation rather than designed from scratch: `SKILL.md` files live
   under agent-agnostic `.agents/skills/<name>/`, plus a canonical
   `AGENTS.md`. `.claude/skills/<name>` and `CLAUDE.md` are symlinks into
   the canonical files, purely for Claude Code's discovery mechanism.
4. **open-slide's real source was re-verified** (not just its marketing
   site, which the original handoff was based on). Most claims held up.
   New/corrected details worth knowing: `/create-slide` is a multi-step
   wizard, not single-shot; comment markers are literal JSX comments the
   inspector UI writes at the clicked element's location (works because
   JSX *is* the visual structure — doesn't transfer to Manim, see decision
   6 below); there's a `/current-slide` skill that publishes the inspector's
   current selection to a file the agent reads; assets have a two-tier
   (per-slide + global) model.
5. **Site rebuild direction chosen** (the "no web canvas ⇒ no HMR"
   question). Manim CE is confirmed raster-only (no scene-level SVG/DOM
   export); manim-slides' own FAQ confirms slides are static pre-rendered
   video. Chosen approach:
   - Priority: build an ID+source-location **manifest** first, drive an
     **outline/tree list UI** (click a named element in a list) before a
     pixel-accurate video overlay (deferred, likely 2D-only when built —
     3D-camera scenes make screen-space bbox projection unreliable).
   - Audience: primarily **public viewers** — a real polished
     presentation-viewing experience, not a bare internal QA tool.
   - Editing mechanism: a click creates a **structured, ID + file:line-
     scoped comment/edit-request** (not live hot-editing), consumed later
     by an apply-comments Skill. Chosen over copying open-slide's inline
     JSX-comment-marker approach because Manim's construction calls aren't
     co-located with their on-screen appearance the way JSX is.
6. **Manifest schema + `track()` design finalized** (see "What's built,"
   below, for the actual implementation). Key calls: element-centric JSON
   (one entry per id, list of appearances), duplicate id within one
   *segment* raises, reuse across segments is expected, bbox captured at
   end-of-segment (not at `track()` call time) piggybacking on the same
   `next_slide()` override already needed for the transition fix, with the
   snapshot step failure-isolated so a bad element can't break a render.
7. **`manim-slides` PR #664 re-checked**: still open, unmerged as of this
   session. Only the Python-side `wait_time_between_slides` fix has been
   built (a class attribute override in `base.py`); the CLI-level
   Reveal.js `transition`/`background_transition` config-quoting bug PR
   #664 addresses has **no workaround built yet** — still open work, see
   below.
8. **Python/tooling**: managed via `mise` (`mise.toml`, `python = "latest"`,
   currently resolves to 3.14.7), matching the user's existing toolchain
   conventions rather than pinning a specific version file-by-file. Package
   uses standard `pyproject.toml`, not the source repo's `pixi.toml`.

## What's built and verified this session

- Repo: `git init`, MIT `LICENSE`, `pyproject.toml`, `mise.toml`, `README.md`,
  `.gitignore`. Pushed to GitHub (public).
- `AGENTS.md` (canonical) / `CLAUDE.md` (symlink) — rewritten from the
  stale pre-init version per decision 3, above.
- `src/open_manim_slides/base.py` — the `Slide` base class:
  `wait_time_between_slides` fix, `track(mobj, id=...)` with same-segment
  duplicate validation and cross-segment reuse, failure-isolated manifest
  snapshot on `next_slide()`, JSON manifest writer on `render()`.
  Import-verified and behavior-tested against the real installed
  `manim`/`manim-slides` (not just written from documentation knowledge).
- `src/open_manim_slides/layout.py` — **one** primitive:
  `assert_within_safe_frame(mobj)`, a margin-vs-frame-edge check. This is a
  deliberately minimal first slice of the full design system (typography,
  color tokens, slide templates, and — as of this session's testing,
  urgently — inter-element overlap checking — are all still unbuilt; see
  "Immediate next steps").
- `src/open_manim_slides/scaffold.py` — deterministic deck generator
  (`new_deck(title, segments, out_dir)`), tested directly.
- `.agents/skills/create-deck/SKILL.md` (+ `.claude/skills/create-deck`
  symlink) — wizard that scaffolds via `scaffold.py`, then fills in each
  segment's content, following the `track()`/`assert_within_safe_frame()`
  conventions.
- `tests/` — 17 passing tests (`test_base.py`, `test_layout.py`,
  `test_scaffold.py`, and `test_render_smoke.py` — a real end-to-end
  render, not mocked).
- Two example decks used for dev testing: `the_water_cycle.py` (clean,
  hand-authored carefully) and `layers_of_the_earth.py` (deliberately naive
  placement, used as a stress test — see next section). **`decks/` is
  gitignored and not tracked on `main`** — these are dev-only scratch decks
  for exercising the framework, not curated examples. Real example content
  gets added once the framework is further along (see "Immediate next
  steps").

## Key discovery: generation-quality testing found a real gap

After the scaffold/base-class/Skill were built and verified to *render
without errors*, a separate question was tested: does it generate *good*
slides? Method (worth reusing going forward): render a deck, check the
written manifest for bounding-box overlaps between tracked elements, and
pull actual frames (`ffmpeg` + visual inspection) to confirm.

Result on `layers_of_the_earth.py` (four labels placed via
`next_to(circle, RIGHT)` on concentric circles): **all four labels overlap
each other**, rendering as an unreadable garbled mess. Confirmed both by a
bbox-overlap script and by looking directly at an extracted frame. This is
the exact failure mode the project exists to prevent (see the source
repo's `carlo_manim` incident, decision 1 above) — and it happened even
with `assert_within_safe_frame` in place, because that check only guards
against the *frame edge*, not against other elements.

A second, subtler gap surfaced during this test: the manifest's
`appearances` list only records the segment where `track()` was called,
not every segment an element remains visually present in — but Manim
elements persist on screen once added unless explicitly removed. A naive
per-segment overlap check therefore misses real co-presence; the correct
check compares all labels pairwise regardless of segment. This also
matters for the future site's "highlight during active segments" UI (an
element should show as active in every segment it's actually still visible
in, not just the one it was first tracked in).

## Immediate next steps (priority order)

1. ~~Build `assert_no_overlap(*mobjects)`~~ — **DONE.** Added to
   `layout.py` alongside `assert_within_safe_frame`, same fail-fast
   philosophy (raise at construction time). Confirmed it catches the real
   `layers_of_the_earth.py` bug directly (crust-label vs. mantle-label),
   without needing a render — 5 tests added in `test_layout.py`, 17/17
   passing overall. **Not yet done**: going back and fixing
   `layers_of_the_earth.py`'s actual placement, and wiring
   `assert_no_overlap` into `create-deck`'s `SKILL.md` instructions so
   future generation actually calls it.
2. **Fix the manifest's appearance-tracking gap** — track "still visible"
   across segments, not just "first tracked in." Needed for the overlap
   checker to be usable *automatically* (right now it must be called
   manually with an explicit list of co-visible elements) and for the
   future site.
3. **Continue the full design system** beyond the two safety primitives:
   typography scale, color/theme tokens, reusable slide templates —
   deferred scope from decision 1/6, not yet started.
4. **Pin a `manim-slides` PR #664 workaround** — still open upstream, no
   local workaround built yet (only the unrelated Python-side
   `wait_time_between_slides` fix is done).
5. **Site build-out** (decision 5) — manifest schema and `track()` exist
   and are tested; the site itself (tech stack, actual UI, apply-comments
   Skill, public/author permission split) is still entirely undesigned.
6. **Grow example content** — two dev-only decks exist locally now (water
   cycle, layers of the earth); a public framework will eventually want a
   curated, gitignore-cleared example gallery. Not until the framework is
   further along (see decision on `decks/` being dev-only, above).

## Reference

- Repo: https://github.com/lapotist/open-manim-slides
- Upstream manim-slides bug being tracked: https://github.com/jeertmans/manim-slides/pull/664
- open-slide (design reference for *shape*, not a spec to copy blindly):
  https://open-slide.dev/, https://github.com/1weiho/open-slide
