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
decks with an AI coding agent. See `HANDOFF.md` for the full design
background (why this project exists, what was tried before, open questions
worked through during initial planning).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires system `cairo` and `pango` development headers for the `manim`
dependency `manimpango` to build (see `README.md`).

## Architecture

- `src/open_manim_slides/base.py` — `Slide`, the framework's base class.
  Subclasses `manim_slides.Slide` and:
  - Fixes the default segment-transition flash (`wait_time_between_slides`
    defaults to `0` upstream, which cuts a clip short of settling).
  - Provides `track(mobj, id="...")` to tag an element with a stable,
    human-meaningful id. Writes an ID-addressable manifest
    (`<DeckClass>.manifest.json`, in the render's media directory) at the
    end of rendering — this is the foundation for a not-yet-built review
    site (see `HANDOFF.md`'s "no HMR equivalent" discussion).
  - Duplicate `id` within one segment raises at construction time; reusing
    an `id` across segments is expected (a persisting/reappearing element).
- `src/open_manim_slides/layout.py` — `assert_within_safe_frame(mobj)`, a
  margin-safety check that raises at construction time instead of letting
  an element silently overlap or clip. This is a deliberately minimal
  slice of a larger design-system layer (typography, color tokens, slide
  templates) that hasn't been built yet.
- `src/open_manim_slides/scaffold.py` — deterministic deck-file generator.
  Not agent-authored: given a title and segment list, produces the file's
  structure (imports, class, one function per segment) so it's consistent
  and testable. Content within each segment is filled in separately.

## Authoring convention

**One file per deck.** Each `self.next_slide()` segment is its own
top-level method (`segment_<name>`), called in sequence from `construct()`.
This was chosen over open-slide's one-file-per-slide convention because a
Manim scene's segments routinely share state (a persisting title, a diagram
built up incrementally across several segments) in a way independent React
components don't — see `HANDOFF.md` for the full reasoning. Use
`create-deck` (below) to generate a new deck rather than hand-writing this
structure.

## Skills

- `create-deck` (`.agents/skills/create-deck/SKILL.md`) — scaffolds a new
  deck via `scaffold.py`, then fills in each segment's content. Use this
  instead of hand-writing a deck file's structure.

## Testing

```bash
pytest
```
