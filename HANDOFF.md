# open-manim-slides — New Repo Handoff

Status: planning handoff for a brand-new session, written 2026-08-09.
Nothing in this directory is initialized yet (no git repo, no code) — this
file is the entire contents so far. `open-manim-slides` is a provisional
name; rename freely, nothing depends on it yet.

## The Ask

The user wants an **open-source framework for building Manim Slides
presentations**, distinct from their existing private lesson-content repo
at `/home/lapotist/Documents/manim`. Explicit requirements from the
conversation that produced this handoff:

- Its own workspace/repo (confirmed: new standalone repo, not a split of
  the existing one).
- A **more controlled environment** for generating lessons/decks than "hope
  the agent reads a long prose instructions file correctly."
- **Skills for generation and editing** — Claude Code Skills (packaged
  slash-command workflows) as the primary interface for authoring and
  iterating on decks, not just documentation.
- A **more interactive experience** than the current render-and-inspect
  loop.
- Explicit inspiration: **open-slide** (https://open-slide.dev/,
  https://github.com/1weiho/open-slide) — "a slide framework built for
  agents," but for React. The user wants the Manim equivalent of that
  experience.

Do not assume the user wants a 1:1 port of open-slide's mechanics — the
project's own "no DSL, arbitrary code" philosophy doesn't map cleanly onto
a rendered-video medium (see "Where the analogy breaks," below). Treat
open-slide as a reference for *shape*, not a spec to copy blindly.

## Why This Came Up: Context From the Source Repo

`/home/lapotist/Documents/manim` is a private repo producing Traditional
Chinese-language math lesson videos with Manim Community + Manim Slides.
During one session there, real, systemic problems surfaced when an agent
generated lesson content with only a large prose `AGENTS.md` (527 lines) to
go on:

1. **Slide-to-slide flash on every transition.** Root-caused to
   `manim-slides` defaulting `wait_time_between_slides` to `0` (cuts each
   clip one frame short of settling) plus a Reveal.js `transition`/
   `background_transition` config never being set. Fixed locally in the
   source repo's shared base class. While investigating the export
   pipeline, an **upstream manim-slides bug** was found, root-caused,
   fixed, tested (regression test added, proven to fail without the fix
   and pass with it), and PR'd: **https://github.com/jeertmans/manim-slides/pull/664**
   (open, unmerged as of this handoff — check its status before assuming
   the fix is available in a released `manim-slides` version).

2. **Bad spacing, alignment, and overlap across many already-rendered
   lessons.** Root-caused to a **helper-library gap, not per-lesson
   sloppiness**: the shared design-system layer (`carlo_manim`/`math_manim`
   — `layout.py`, `attention.py`) offered exactly one hardcoded two-column
   layout preset and an opacity-only "dim context" helper (explicitly *not*
   sufficient for overlap, per the source repo's own `AGENTS.md`). 45 of 48
   sampled lesson scenes bypassed the shared facade entirely and hand-rolled
   ~1,580 raw `.move_to()`/`.shift()` coordinate calls. A fix was designed,
   implemented, and unit-tested in that session:
   - `src/carlo_manim/layout.py`: `FRAME_MARGIN`, `safe_frame()`,
     `assert_within_safe_frame()`, `stack_column()` — margin-checked
     placement that raises at construction time instead of silently
     overlapping/clipping.
   - `src/carlo_manim/attention.py`: `settle_region(old, new, run_time)` —
     fades old content out before new content in, as one call, instead of
     leaving "remove old before placing new" to per-scene discipline.

   These two files in the source repo are a concrete, tested starting point
   for this new framework's design-system layer — read them directly
   rather than re-deriving from this description.

3. **The core lesson learned**: when problems are systemic (a missing
   library primitive, a wrong pipeline default) rather than random
   per-lesson mistakes, neither "manually review everything" nor
   "regenerate everything and hope" is right. Fix the root cause first
   (cheap, deterministic), *then* decide regenerate-vs-hand-fix per item.
   This is the actual motivation for wanting a more controlled framework:
   the current repo has good rules written down, but no scaffold and no
   enforcement, so agents (and humans) drift from them silently.

## What open-slide Actually Does (researched via WebSearch + WebFetch,
2026-08-09 — re-verify against the live site/repo before designing, this
project was ~2 months old at research time and likely still moving fast)

- **Philosophy**: "Slides as code. Crafted by agents." No DSL — every slide
  is an arbitrary React component rendered into a fixed 1920×1080 canvas.
  The framework's stated rationale: agents are better at generating and
  refactoring real code than navigating a constrained slide-builder UI or
  proprietary format.
- **Scaffold**: `npx @open-slide/cli init my-deck` creates a workspace;
  Vite/React/tsconfig internals stay hidden inside a `core` package. Slides
  live at `slides/<name>/index.tsx`, each with an optional `assets/`
  subfolder.
- **Author**: the agent generates new slide pages from natural-language
  prompts via a slash command, e.g. `/create-slide for Q2 roadmap`.
- **Iterate — two complementary modes**:
  - *Visual editor*: toggle inspect mode, click a canvas element, edit
    text/font/color/image directly. Edits buffer in memory, then commit as
    **one HMR write** on save.
  - *Comment-driven*: leave `@slide-comment` markers directly in the
    source `.tsx` file, then run `/apply-comments` — the agent rewrites
    only the flagged sections and clears the markers.
- **Assets**: in-editor logo search via svgl (1500+ logos), drag/rename/
  replace without leaving the tool.
- **Agent-agnostic by design**: explicitly supports Claude Code, Codex,
  Cursor, Gemini CLI, OpenCode, Windsurf, Zed — "anything that edits React
  works." This is achieved by keeping the agent-facing surface as plain
  files (slash-command definitions, source comments), not a
  Claude-Code-specific integration.
- **Version control**: every slide is a real file, so git/PR review works
  for free — comments-in-source double as a collaborative revision
  mechanism.

Sources: https://open-slide.dev/, https://github.com/1weiho/open-slide

## Where the Analogy Maps Cleanly

- **"Arbitrary code, no DSL"** — Manim scenes are *already* arbitrary
  Python (each lesson is a `Scene`/`Slide` subclass). This part of
  open-slide's philosophy is free; Manim never had a DSL problem to begin
  with. The actual gap in the source repo wasn't "too constrained," it was
  "too under-supported" (see helper-library gap above).
- **Fixed canvas** — Manim already renders into a fixed frame
  (`config.frame_width` / `config.frame_height`). Direct parallel to
  open-slide's 1920×1080 canvas.
- **`/create-slide`-style generation command** — directly buildable as a
  Claude Code Skill/slash command, e.g. `/new-lesson`, that scaffolds a new
  deck's files with the required structure pre-filled (this was recommended,
  but not built, in the source-repo session — see "Immediate Next Steps").
- **File-based, git/PR-reviewable** — already true for Manim scene code;
  nothing new needed here.
- **`@slide-comment` + `/apply-comments`** — the source repo already has
  adjacent infrastructure worth mining before building this from scratch:
  a QA review site (`scripts/build_site.py`, `scripts/public_site_assets/`,
  `scripts/qa_slides.py`) with a per-segment review-status schema
  (`qa/review-status.json`) that round-trips reviewer notes. It's not
  currently wired to an agent-apply step, but it's much closer to
  open-slide's comment-loop than starting fresh.

## Where the Analogy Breaks — Open Design Problems for This Session

- **No web canvas ⇒ no HMR.** open-slide's core interactivity (click an
  element, see it change instantly) depends on a live DOM. Manim produces
  rendered video. There is no drop-in equivalent. This is the single
  biggest open design question. Candidates worth evaluating, roughly
  cheapest-to-build first:
  1. Fast low-quality/low-resolution segment re-renders as the "preview"
     loop (Manim already supports `--quality l`; the source repo's
     `pixi run lessons render <id> --quality l` is evidence this is fast
     enough to iterate with).
  2. Lean on the existing segment-based review site as the "visual" side
     of iteration (watch, don't drag) — comment-driven editing rather than
     direct manipulation, which is a legitimate and simpler alternative to
     open-slide's click-to-edit inspector, not just a fallback.
  3. Something closer to Manim's own interactive/Jupyter preview for a
     tighter loop during authoring, before a full segment render.
- **Video segments, not a single continuous DOM.** open-slide's
  "slide = one file" maps to Manim Slides' "segment = one
  `self.next_slide()` boundary," but a single Manim *scene* file already
  contains many segments (unlike open-slide, where one file is one slide).
  Decide up front whether this framework's unit of authoring is "one file
  per deck" (current source-repo convention) or "one file per slide"
  (open-slide's convention, arguably better for agent-sized diffs and
  parallel editing) — this is a real architecture decision, not a detail.
- **Agent-agnostic vs. Claude-Code-specific.** The user asked specifically
  for "skills," which is Claude Code's term for its packaged slash-command
  mechanism. open-slide achieves multi-agent support by keeping its
  agent-facing surface as plain markdown/files rather than a
  platform-specific integration. Decide deliberately whether this
  framework commits to Claude Code Skills as a first-class citizen (fine —
  the user is a Claude Code user and asked for skills explicitly) while
  still keeping the underlying commands plain-file-based enough that
  other agents *could* drive them later, rather than accidentally building
  something Claude-Code-only by default.

## Concrete Extraction Candidates From the Source Repo

Bring over and generalize (strip Traditional-Chinese-specific and
exam-content-specific assumptions):

- `src/carlo_manim/layout.py`, `src/carlo_manim/attention.py` (and their
  `math_manim` facades) — the fixed margin/overlap primitives described
  above. Concrete, tested code, not a proposal.
- `src/carlo_manim/base.py` (`CarloSlide`/`MathSlide`) — the
  `wait_time_between_slides` fix and the general "stable base class" shape.
- The QA/review-site machinery (`scripts/build_site.py`,
  `scripts/public_site_assets/`, `scripts/qa_slides.py`,
  `qa/review-status.json` schema) — closest existing thing to open-slide's
  "iterate" loop; needs a feedback-to-agent connection, not a rewrite.
- The production-state lifecycle concept (`discovered → planned →
  storyboarded → math_verified → draft_rendered → visual_verified →
  published`) — a reasonable general content pipeline if renamed away from
  math-specific terms (e.g. `math_verified` → `content_verified`).

Leave behind (repo-specific, don't generalize):

- Traditional Chinese language requirements, presenter-script conventions
  tied to that.
- Source-provenance/licensing rules specific to clearing exam-content
  rights (`docs/provenance/`, `NOTICE.md` split, `catalog/` schema).
- Anything keyed to "problem/exam/collection" as the unit of content — the
  new framework's unit should be domain-neutral ("deck," "slide").

Does not exist yet, needs building:

- The scaffold/generation Skill (open-slide's `init` + `create-slide`
  equivalent).
- An `/apply-comments`-equivalent Skill wired to the review-site's stored
  notes.
- The fast-preview iteration loop (see "Where the analogy breaks").
- Neutral example content (not Chinese math problems) for a public,
  general-audience framework.

## Immediate Next Steps

1. Initialize the actual repo here (git init, license — the source repo
   uses MIT for code / CC BY 4.0 for content, a reasonable default to
   reuse), decide the final project name.
2. Re-fetch https://open-slide.dev/ and read
   https://github.com/1weiho/open-slide's actual source (not just the
   marketing site) for the CLI implementation and slash-command file
   format — this handoff is based on the public site's description, not
   the code.
3. Decide the authoring-unit question above (one file per deck vs. per
   slide) before writing any scaffold, since it shapes everything
   downstream.
4. Copy and generalize `carlo_manim`'s `layout.py`/`attention.py`/
   `base.py` from `/home/lapotist/Documents/manim/src/carlo_manim/` as the
   first real code in this repo, rather than redesigning from zero.
5. Check the status of https://github.com/jeertmans/manim-slides/pull/664
   before depending on the fix being in a released version — pin a
   workaround (like the source repo's own `build_lessons.py` transition-
   quoting workaround) if it's still unmerged.
6. Design one Skill end-to-end (recommend starting with the generation/
   scaffold one, since it has the clearest open-slide precedent) before
   building the harder iterate/apply-comments loop.
