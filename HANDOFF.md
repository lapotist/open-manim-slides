# open-manim-slides — Handoff

Status: updated after the nineteenth implementation session, 2026-09-22.
MIT, public at **https://github.com/lapotist/open-manim-slides**, `main`
pushed through session seventeen. Read this before doing further work —
it's the authoritative summary of what's decided, what's built, and what's
next. `AGENTS.md` holds the file-by-file architecture; this file is the
*why* behind it and the running history. Full investigation detail for any
item lives in the session transcripts, not duplicated here.

**Standing scope boundary** (set by the user, still in force):
framework/tooling work proceeds autonomously; deck *content* — fixing a
deck, growing or curating examples, the review site's design — is reserved
for the user's direct guidance unless they ask for it.

## What this project is

An open-source framework for building **Manim Slides** presentations,
inspired by [open-slide](https://open-slide.dev/) (https://github.com/1weiho/open-slide)
— "a slide framework built for agents," but for Manim instead of React: a
controlled, skill-driven workflow for generating and iterating on decks,
with real enforcement (things that fail loudly at construction time)
rather than a long prose file an agent silently drifts from. It is being
generalized from a private repo of Traditional Chinese math lesson videos
(`~/Documents/manim`) — the origin of the problems it addresses, but **no
code has been ported** (decision 1).

## Decisions made (first session)

1. **No porting from the source repo — design fresh.** That repo's
   `carlo_manim` layer and QA review site are "not well made" per the
   user, so they aren't reference material, not merely unported.
2. **Authoring unit: one file per deck, segments as top-level functions.**
   open-slide's file-per-slide convention doesn't transfer — Manim
   segments routinely share state across `next_slide()` boundaries (a
   persisting title, a diagram built up over several segments) in a way
   independent React components don't. True file-per-slide with a
   `track()`-based handoff registry is a documented future path, not a
   current bet.
3. **Skills are canonical plain files; Claude Code gets a symlinked
   projection.** Taken from open-slide's real implementation: `SKILL.md`
   under agent-agnostic `.agents/skills/<name>/` plus a canonical
   `AGENTS.md`, with `.claude/skills/<name>` and `CLAUDE.md` as symlinks.
4. **Site rebuild direction** (the "no web canvas ⇒ no HMR" question).
   Manim CE is raster-only and manim-slides' FAQ confirms slides are
   static pre-rendered video, so: build an ID + source-location
   **manifest** first, drive an **outline/tree UI** before any
   pixel-accurate video overlay; the audience is **public viewers**, not
   an internal QA tool; editing is a click → a structured, ID +
   `file:line`-scoped comment consumed later by an apply-comments skill.
   Chosen over open-slide's inline JSX-comment markers because Manim's
   construction calls aren't co-located with their on-screen appearance
   the way JSX is.
5. **Manifest schema + `track()`**: element-centric JSON (one entry per
   id, list of appearances); duplicate id within one *segment* raises,
   reuse across segments is expected; bbox captured at end-of-segment
   (piggybacking the `next_slide()` override the transition fix already
   needed); the snapshot step is failure-isolated so a bad element can't
   break a render.
6. **Python/tooling**: `mise` (`python = "latest"`) and a standard
   `pyproject.toml`, not the source repo's `pixi.toml`.

## Session history

**1 (2026-08-09)** — Repo scaffolded. Built `base.py` (`Slide`,
`track()`, transition-flash fix), `layout.py` (safe frame only),
`scaffold.py`, the `create-deck` skill; 17 tests. Testing
`layers_of_the_earth.py` (labels on concentric circles) exposed two gaps
the safe-frame check structurally cannot see: labels overlapping *each
other* (safe-frame guards only the frame edge), and the manifest
recording only the segment `track()` was called in rather than every
segment the element stayed visible for.

**2 (2026-08-10)** — Both gaps closed, plus two framework fixes.
- `wait_time_between_slides` had been set through a shadowing class
  attribute (written before `manim-slides` was installed to check
  against), silently defeating the real clamped `@property` setter for
  anyone assigning it later — the pattern manim-slides' own docs
  demonstrate. Fixed by writing through the property.
- Manifest gap fixed by overriding `Scene.remove()` — which `FadeOut`
  routes through — so a tracked id deactivates only once its mobject
  actually leaves.
- `assert_no_overlap()` built and baked into every scaffolded segment as
  `assert_no_overlap_among_tracked()`, making the check structural rather
  than a convention an agent could skip.
- manim-slides PR #664 workaround (`convert.py`): a `(Str, StrEnum)`
  field's `__get_pydantic_core_schema__` collapses to a bare string during
  pydantic validation, dropping the quoting that keeps exported Reveal.js
  config valid JS. Needs the schema patch **and** `model_rebuild(force=True)`
  — patching alone doesn't touch an already-built schema.
- First `theme.py` slice. → 28 tests.

**3 (2026-08-10)** — Design system, two decks, the `decorative` decision,
and the webrunner.
- Design system finished: spacing scale anchored to manim's own
  `next_to`/`arrange`/`to_edge` buffer defaults rather than invented
  numbers; `two_column()`, `diagram_with_caption()`.
- Two decks built via `create-deck` at the user's request
  (`euler_s_formula.py`, `the_pythagorean_theorem.py`). Euler's
  complex-plane diagram exposed a **structural** limit of the overlap
  check: it compares axis-aligned bboxes, and any point on a circle of
  radius `R` about `C` lies within `[C-R, C+R]` on *both* axes, so a
  circle checked against anything radiating from its center
  false-positives at every angle (a diagonal line's bbox swallows nearby
  content the same way). Eight fixes were evaluated — per-pair
  exemptions, exact per-shape geometry, pixel-mask rasterization,
  convex-hull + SAT, a `fill_opacity` heuristic, a circle special case, a
  role flag — and the smallest one matching the project's "explicit, no
  magic" taste was built: **`track(..., decorative=True)`**, still fully
  recorded in the manifest, just excluded from the pairwise check.
  Convex-hull + SAT would also fix the diagonal case for genuinely
  independent content; deferred (next step 5).
- The Pythagorean deck rendered clean on the *first* full render by
  verifying tricky APIs headlessly first — unlike Euler's multi-round
  debugging. That contrast is the seed of `validate.py` (session 10).
- `webrunner/` built (FastAPI + plain JS, stack confirmed with the user):
  deck discovery from source, subprocess `manim render` with a **real**
  progress bar (manim's tqdm output survives being piped to a non-tty
  subprocess — confirmed, not assumed), SSE streaming, HTML export served
  for in-browser presenting. Not imported by the core package, so
  `fastapi`/`uvicorn` aren't forced on the base install.
- A "flashing" report on `layers_of_the_earth` was the same overlap bug,
  unflagged only because that deck predates the check.
- `assert_reasonably_centered()` built after the user flagged the
  Pythagorean summary slide: no existing check catches a composition
  that's in-frame and non-overlapping but never centered *as a group* (a
  title left at its default position with content stacked below via
  `next_to` only ever grows one direction). Calibrated against real
  numbers — the bad slide sat at −30% vertical offset vs a normal
  diagram's +11%; the same pass found two shipped segments at +55%/+27%,
  surfaced to the user, who chose to fix only the summary. Opt-in, and
  unlike the overlap check it does **not** exclude `decorative` elements:
  a backdrop still occupies real space. → 54 tests.

**4 (2026-08-12)** — Four user-reported `webrunner` bugs, all fixed.
- **Presenter unresponsive unless fullscreened**: the iframe was never
  focused after `src` was set, so keys went to the parent page.
- **"12 of ~8" progress**: the `self.play(` call-site count is a lower
  bound (one call can log several `Animation N` lines) and never
  self-corrected. Extracted a small pure `_progress_from_animation_line()`
  that clamps the total upward; verified live flipping "26 of ~27" to
  "28 of ~28" mid-stream.
- **Browser back/forward not tracking the loaded deck**: real
  `pushState`/`popstate` handling, including restore on reload.
- **Fullscreen-transition stall**: mitigated with a wider pre-fullscreen
  layout so the resize jump is smaller; not fully verifiable headless.
- **Process hygiene, banked as a lesson**: checking `lsof -i :8000` (not
  just that `curl` succeeded) found a webrunner from session three *still
  running two days later*, serving pre-fix code — almost certainly what
  several of these reports were tested against. Check who holds the port
  before trusting that served code matches source.
- **Follow-up**: "laggy going back and forth" traced by reading reveal.js
  6.0.1's own source at the exact tag (not docs) to `config.viewDistance`
  (default 3) — a segment's background `<video>` is only created once it
  comes within view distance, so later segments hadn't begun loading.
  Fixed with `view_distance=50` in `webrunner/render.py`.

**5 (2026-08-12)** — The `view_distance` fix didn't resolve the lag; the
refined symptom ("stuck on a middle state then jumps to the end;
forward-only is smooth") pointed elsewhere. Diagnosed from a screen
recording, frames extracted into timestamped contact sheets. **Root
cause, two halves:** (a) manim-slides pre-renders a reversed video per
segment and its native Qt presenter uses it, but the HTML exporter drops
it (`include_reversed=False`) and the template only references the
forward file; (b) reveal.js restarts a background video from
`currentTime = 0` whenever its slide becomes current, in either
direction. Net: "previous" replayed the target segment's entire
construction. The fix (`snap_back_navigation`: on backward navigation,
pause and seek to the final frame) **is what caused session thirteen's
forward flash** — see there for the correct invariant. Both halves of the
root cause above still hold.

**6 (2026-08-13/14)** — Content-quality rewrite of `create-deck`,
prompted by the user's judgment that generated decks were "technically
correct but bland" and the question of whether that was a model problem
or a prompt problem. **Diagnosis, measured**: both skill-generated decks
contained **zero** `.animate` calls while the two hand-written pre-skill
decks had one each — the skill made decks *less* animated than no skill
at all. Causes: ~90% of the skill's words were compliance mechanics with
one clause about content; motion was invisible to every check (they
sample only a segment's final layout); the workflow never looked at a
rendered frame; `theme.py` had no `heading()`, so eight section headings
shipped at 48pt sitting exactly on the safe margin. Rebuilt around "will
a mid-tier model reliably do this unsupervised" (the user validates with
a fresh Sonnet session on purpose):
- **Skill rewritten** (~1/3 compliance-free) around seven countable rules
  — R1 carry-forward (≤2 cleared starts), R2 something on screen must
  change (emphasis doesn't count), R3 anchored non-text mobject, R4
  perform every written verb, R5 play budget + heading-arrives-with-figure,
  R6 semantic color, R7 prose cap — plus a pre-commitment plan table
  filled before any code, an audience setting (middle-school/high-school,
  recorded by `scaffold.py` as an `AUDIENCE` constant placed *below* the
  docstring because the webrunner's title regex is DOTALL), and a
  closed-question visual review with mechanical fix-or-accept triggers,
  "could be prettier is not a reason", and a restructure escape hatch
  when more than half the segments flag. Compliance prose moved to
  `references/framework-rules.md`; `decorative=True` criteria narrowed
  (the old guidance had decks marking their own subject decorative); the
  composite-figure one-id pattern added as the checked alternative.
- **`references/exemplar.md`** — one completing-the-square segment at
  target quality, built as a real deck, rendered, critiqued by the new
  review loop, then annotated per line by the *move* it performs, with a
  same-move-three-subjects table and an explicit anti-copy line.
- **`references/motion-recipes.md`** — every snippet construct-verified
  headlessly. Gotchas banked: a `ValueTracker` stores its value in its
  coordinates (safe-frame-checking one raises); `clear_updaters()` before
  fading any `always_redraw`/`TracedPath` mobject; `TransformMatchingTex`
  *replaces* its input (re-track it); transient overlap is free, since
  checks only sample segment ends.
- **`frames.py` built.** The planned mechanism — "frame 0 of the
  pre-rendered `_reversed.mp4` is the final frame for free" — was
  **disproved during verification**: manim-slides splits videos over 4s
  before reversing, so rev-frame-0 of an 8.15s segment is the ~4s mark.
  Switched to `-sseof` on the forward video. Segment order must come from
  `slides/<Scene>.json` array order, not the hash filenames.
- `theme.py` gained `heading()` (36pt, margin + `SPACING_XS` slack, since
  `to_edge`'s buff measures from the frame edge, not the margin) and
  `COLOR_ACCENT_2`. `scaffold.py` gained `audience=` and a checklist
  comment replacing the bare `# TODO` — the smoke test string-replaced
  that exact TODO line, so it had silently become a no-op render;
  re-anchored on the assert line.
- **Dry run** (user-approved) produced `the_pythagorean_theorem_v2.py`.
  Two framework findings banked into `framework-rules.md`: rearranged
  dissection halves share an identical bbox (fixed with the composite-id
  pattern), and fading a re-wrapped `VGroup` of tracked children leaves
  the tracked wrapper active. Scored against v1: change-animations 2→12,
  cleared-frame starts 5→0, `Write()`-on-shapes 4→0, max plays/segment
  7→4, decorative-on-subject 3→0. → 72 tests.

**7 (2026-08-16)** — User feedback on the v2 deck.
- **Pacing rule banked**: the algebra segment chained two
  `TransformMatchingTex` steps in one segment, so the intermediate line
  was on screen ~1s — plays inside a segment auto-advance, only
  `next_slide()` boundaries wait for the presenter. Fixed by giving each
  derivation step its own segment. Encoded into R5 ("an equation the
  audience must read gets its own segment"), the audience table, and a
  motion-recipes gotcha.
- **Triangle sized up again** (1.45→1.9, extracted as `TRI_SCALE` so the
  inverse shrink can't drift). The review loop *had* flagged this once
  and the fix was still too timid — "caught but under-corrected" is a
  real reviewer failure mode.
- **Narration proposed by the user, not built.** The carrier already
  exists upstream: `next_slide(notes=...)` → per-slide `notes` in the
  slides JSON → `<aside class="notes">` + `show_notes` in the RevealJS
  export. Slice: scaffold emits a placeholder, `create-deck` writes the
  script, webrunner shows a script pane when not fullscreen; TTS is a
  later layer on the same script and would give principled auto-advance
  timings. Awaiting direction.

**8 (2026-08-16)** — `create-deck` run end-to-end on sin/cos/tan
(high-school, 8 segments) as real usage. All four review rounds surfaced
issues invisible to the `assert_*` checks:
- **`Angle(Line(vertex,p1), Line(vertex,p2))` swept the reflex angle**
  (~323° instead of ~37°), dominating the opening segment — invisible to
  every check because it was one `decorative` composite with nothing to
  collide with. Fixed by building an `Arc` from computed ray angles
  rather than trusting `Angle`'s quadrant-picking (recipe 10).
- **The sweep segment's geometry was underscaled** and its final angle
  (75°) too extreme, so the leg-length ratio carried forward and shrank
  `cos²θ` to barely legible two segments later.
- **A `decorative` composite nearly touched the next heading** —
  invisible to the overlap check by construction (decorative excluded
  from both sides) and to safe-frame (only ever called on the squares as
  a group). **Two elements can each pass every automated check and still
  collide where no single check's scope spans both** — the gap finally
  closed in session seventeen.

**9 (2026-08-16)** — Feedback, then a tooling slice.
- **Two workflow rules banked.** (a) On a "test run", don't read other
  `decks/` files as reference — it measures whether the skill's own
  written guidance suffices; recorded in `SKILL.md` itself, not only in
  memory. (b) Long render→error→edit loops need brief checkpoint
  narration; silent stretches read as "taking too long".
- **`blankspace.py` built** (user's ask: find space genuinely left over,
  not space reserved for later content — a *temporal* distinction, so it
  aggregates across segments and calls a cell dead only if **no** segment
  ever fills it). Measures pixels from `frames.py` stills, not manifest
  bboxes, because a bbox overstates coverage — a triangle's bbox claims
  its empty corners, so bbox-based emptiness under-reports exactly what
  is worth finding. Crops the safe margin, which is supposed to be empty.
  Validated on the live deck: flagged precisely what the user had
  described by eye. Wired into review Q2 with mechanical triggers: fix a
  segment under 20% fill, restructure the deck on a dead region ≥ 15%.
- **Full restructure driven by its numbers** (user: "restructure it"):
  the deck had no composition, only per-segment placement. Replaced with
  one two-column composition held for the whole deck (figure left,
  equation stack accumulating downward from a fixed top on the right) so
  later segments have *reserved* space rather than leftover space. Dead
  space 32%→22%, per-segment fill 23.6-44.4%→29.2-54.2%.
- **Self-review of `blankspace`** (user asked what it costs): 268ms for 8
  segments, no optimization warranted. Two real defects found and fixed:
  the safe-margin crop used one fraction for both axes though the margin
  is a fixed unit count on a 14.22×8 frame; and nothing detected stale
  stills, so editing without re-extracting silently reported the old
  layout (now compared against the slides JSON's mtime).
- Gotcha re-confirmed: squares built via `.move_to(computed_center)`
  against triangle legs trip the overlap check on rounding — build them
  as `Polygon`s from the triangle's own corner points so touching edges
  share identical floats. → 86 tests.

**10 (2026-08-16)** — Workflow rebuild, after measuring why the session's
own `create-deck` run took 30+ minutes.
- **The measurement**: machine time for the whole run was **2.4 min**.
  ~28 min was ~46 sequential model round-trips — the renderer was never
  the bottleneck, round-trip *count* was, and the largest single block
  was 12 trips (~8 min) finding five layout errors one render at a time,
  since a render aborts at the first failure. (An earlier version of this
  analysis blamed context growth; corrected — a 1-hour prompt cache makes
  a stable prefix cheap, so this file costs its tokens once, not per turn.)
- **`validate.py` built** — runs `construct()` and every check with no
  rendering (~2s) and reports *all* failing segments in one pass. Two
  subtleties: scene updaters must be ticked after applying animations or
  `always_redraw` geometry is stale for the next segment; and cascade
  detection must match on the *coordinates* in a failure message rather
  than its wording, since `assert_no_overlap` names whichever of a pair
  it reaches first.
- **`create-deck` restructured around it**: validate before any render
  ("fix everything, re-run until clean, only then render"), plus a
  "commit to one composition" section (two-column default, real frame
  dimensions, module constants for column centers) encoding what session
  nine arrived at after four rounds.
- **`progress.py` built.** Two decisions: drift is judged at *phase
  entry*, not live — time spent inside a phase is that phase's own
  allocation, and comparing live elapsed against expected-at-entry flagged
  every run as behind the moment it started (a real bug caught by testing
  all three states); and the status line is computed but never counted as
  displayed, since a command's stdout reaches the agent, not reliably the
  user's terminal, so `SKILL.md` requires the agent to relay it. → 125 tests.

**11 (2026-08-20)** — A run reproduced a defect the instructions already
warned about: a plain `Transform` between two headings, interpolating
glyph *outlines* and spending most of the play unreadable. Moved into a
gate — `IllegibleTextMorph` in `validate.py`, a `FadeTransform` section
in `motion-recipes.md`, review question Q7. **Written guidance didn't
bind; the same rule as a mechanical check did** — and this one is
uniquely invisible to the frame review, since the final frame is the one
moment nothing is moving. Verified against a deck holding one bad swap
plus every shape that must *not* fire. Shipped with zero tests — the same
failure mode it exists to prevent — so six were added, including the
glyph-count-not-string-length rule (`\tfrac12` is eight source characters
but one small fraction). → 129 tests.

**12 (2026-08-20)** — Built `decks/absolute_value.py`, which surfaced a
new framework bug: **two animations driving one mobject in a single
`play()` can deadlock manim's encoder.** Here `FadeOut(figure)` alongside
`Transform(line, ...)` where `line` was a child of `figure`. The render
hung at 29/30 — 0% CPU, futex wait, no traceback, no further partial
movie files — reading as a slow render rather than a failure (~13 of the
run's 30 minutes). Diagnosed by noticing the partial-movie count had
stopped advancing, not by trusting absent output (`tail` buffers). Fixed
structurally as `ConflictingAnimations`, comparing mobject *families*
across one `play()`'s top-level arguments; the harness **cannot reproduce
the hang** (it applies animations sequentially), so the check is
structural by necessity — same reasoning as `IllegibleTextMorph`.
- **A measurement that corrected an intuition**: raising a figure to "use
  the middle" *lowered* fill (18.1%→16.0%) — fill counts occupied cells,
  so concentrating content reduces it and spreading is what helps. Worth
  remembering before "centering" a sparse slide. → 132 tests.

**13 (2026-08-22)** — User screen-recording of `absolute_value`: "end
state flashes after right key, lag going back and forth, both meant to be
accounted for already." Both real, both caused by the *fifth* session's
own fix, and the deck was never touched — the requirement was that this
be handled for every future generation.
- **Root cause.** Snapping backward navigation to a segment's final frame
  parks that video at its end; reveal.js restarts a video from
  `currentTime = 0` whenever its slide becomes current, so the next
  *forward* entry must seek from the end back to 0, and the compositor
  keeps presenting the old frame until the new one decodes. The viewer
  sees the segment's ending — the spoiler — before it builds. Backward
  replay had been traded for a forward flash: both are the same cost,
  seeking a video that is already on screen.
- **`currentTime` cannot see this, which is why it survived two
  sessions.** It updates synchronously while the previous frame is still
  presented. Instrumenting `requestVideoFrameCallback` — the `mediaTime`
  of frames actually *presented* — showed it at once: the stale end frame
  stood 37ms headless, consistent with ~400ms measured off the user's own
  GPU-composited recording.
- **Fix: the invariant is "never seek a video that is on screen"**
  (`instant_navigation`, renamed from `snap_back_navigation` — the old
  name describes half of what the script does, and misremembering its
  scope is part of how this recurred). Each video is parked, while
  hidden, at the pose it will next be entered with: left going forward →
  parked at its end; left going backward → parked at 0.
- **Two rejected alternatives, measured and recorded in the source
  comment** so they aren't re-tried as simplifications. Calling `play()`
  on the entering video to pre-empt Reveal (which only resets a video
  that is `paused || ended`) fails: a segment that ran to completion *is*
  `ended`, and `play()` on an ended element seeks to the start per spec.
  What works is shadowing `paused`/`ended` with own accessors for the
  remainder of Reveal's synchronous `slide()` call, then deleting them.
  For the same reason videos park at `duration - EPSILON`, never at
  `duration`.
- **A residual, deliberately tolerated**, found by adversarial rapid
  navigation: re-entering quickly can flash, for ~10-15ms, the frame the
  viewer was *already looking at* — a hidden video's composited surface
  can lag its `currentTime`, and no page JS can force a present while
  nothing shows it. A hiccup on already-seen content is categorically
  different from showing unseen content. `playback.py`'s tolerance scales
  with segment length rather than being widened to pass, and the check
  still discriminates: 0/20 wrong on the fixed export vs 6/20 on the old.
- **`playback.py`** — drives real headless Firefox over WebDriver BiDi
  (stdlib only: a ~90-line WebSocket client, no new dependency, no Node),
  walks the deck with arrow keys, asserts the *pose* and never the
  timing, since magnitude is environment-specific while the wrong-pose
  condition is not.
- **Why this shape**: the fix lives in the export path, so every future
  deck gets it with zero agent effort — nothing to remember, nothing to
  cut under a tight budget. The check is out-of-band (`pytest`, ~11s,
  skipped without Firefox) against the finished artifact, never a step in
  producing one, so `create-deck` needed no new step. → 141 tests, and the
  browser test was itself verified to fail with the fix disabled — a
  check that cannot fail is not a check.
- **If anything in this area is ever suspected again**, run `python -m
  open_manim_slides.playback <exported.html>` first: it answers the
  question mechanically instead of by eye, which is what let two sessions
  chase the wrong half of it.

**14 (2026-08-27)** — `create-deck` run on the dominated convergence
theorem (high-school, 9 segments, user-directed). Framework unchanged;
recorded for what it measured.
- **`validate.py` paid for itself as designed**: first pass reported 7
  failing segments (2 real, 5 correctly marked cascades) in ~2s, and
  fixing the two cleared four of the five. **Zero renders were spent
  finding layout errors**, against session ten's 12 round-trips.
- **A recurring blind spot recurred in a new costume**: the caption ran
  through the x-axis tick numbers in four segments. Both parties pass
  every check — the axes are correctly `decorative`, the caption is
  safe-framed — and no single check's scope spans the pair (session
  eight's shape exactly). The visual review caught it immediately, which
  is the argument for keeping the review even when `validate` is clean.
- **Stale tracking, third variant**: `VGroup.remove()` on a tracked group
  does not take a child off screen when that child was also added in its
  own right (anything animated in via `Write`/`Create`/`FadeIn` is). Four
  detached children stayed at full size as orphans *and* dropped out of
  the overlap check, so nothing raised. Same fix as the other direction
  already documented: fade it, don't detach it.
- **`blankspace` drove a structural gain, not a nudge**: lifting the
  figure 0.45 units to clear the caption raised every segment's fill and
  cut deck-level dead space 14%→10%.
- **Timing caveat**: that run's `progress` report reads 4h32m with 91% in
  `validate`, which is wall clock across an interruption, not work. The
  tracker measures elapsed time between phase calls and **cannot tell a
  long think from an idle session**.

**15 (2026-08-28)** — Why documented fixes recur, then the distribution
slice that makes the question answerable.
- **The enforcement audit** (user's question: bugs already solved and
  written into the instructions keep coming back — what is failing).
  Measured: **none of R1-R7 had a mechanical gate.** Their "checks" were
  the agent grepping code it had just written and grading itself. The
  sharpest evidence is R1, whose stated check was "count the
  segment-opening `FadeOut`s ≤ 2": run literally against the skill's own
  output it fails 5-7 times per deck in every recent run, and no run ever
  reported it — because the agent silently applied the rule's *intent* (a
  partial fade alongside a carried figure), of which those decks have
  0-2, correctly. The decks are fine; the enforcement was fictional, and
  where letter and intent diverge the agent picks, with nothing to catch
  a pick in the wrong direction. Sorted by what guarded them at the moment
  of recurrence: **every rule that crossed into `validate.py` stopped
  recurring, and every rule that stayed prose recurred** (stale tracking,
  three variants; decorative-vs-safe-framed, sessions eight and
  fourteen). Other mechanisms recorded: conditional reads
  (`motion-recipes.md` only if the plan table names one of five
  constructs, though its gotchas are needed at coding time;
  `framework-rules.md` only *after* an `assert_*` raises, so its rules
  about failures that raise nothing sit behind a trigger that cannot
  fire); rules stated in one direction only; the silent-failure class,
  where the wrong move *disables* a guard rather than tripping it;
  `AUDIENCE` written by `scaffold.py` and read by nothing; the scaffold
  checklist deleting itself before review; and `progress.py`'s catch-up
  advice cutting the contact sheets first.
- **The environment question, answered with numbers.** A "test run"
  inside this repo cannot measure what a real install produces, and the
  skill's own test-run rule is powerless against the main reason:
  `CLAUDE.md` symlinks to a then-278-line `AGENTS.md` (373 today) that the
  *harness* injects before any skill is invoked. The rule can forbid reading
  `HANDOFF.md` and other decks; it cannot un-inject the architecture doc.
  Also non-reproducible: 11 prior decks and accumulated
  `slides/`/`media/` that `frames.py` and `blankspace.py` read from.
  Framework *code* was not a contaminant — the tree was clean.
- **Distribution built, so a run can start from nothing.** `npx
  open-manim-slides@latest new <dir>` creates a project with its own
  venv, the framework, the skill files, and an empty `decks/` — measured
  at 21s with a warm pip cache, so a clean environment per test run is
  not a cost worth optimising away.
  - **The skill files were never in the wheel.** `packages =
    ["src/open_manim_slides"]` shipped library code and no `create-deck`,
    so `pip install` gave no documented way to drive it. Fixed with a
    `force-include` of `.agents/skills` to `open_manim_slides/_skills`,
    which `init` copies back out — one source of truth, and the pipx/uvx
    paths work for free.
  - **A real bug fell out of the first fresh install**: `doctor` — whose
    whole job is to report that manim is missing or failed to build —
    crashed with `ModuleNotFoundError: No module named 'manim'`, because
    the console script's import ran `__init__.py`'s eager re-exports.
    Fixed by making `__init__` lazy (PEP 562), with a subprocess test
    asserting `import open_manim_slides` leaves `manim` out of
    `sys.modules`. This is the likeliest state of a first install, since
    `manimpango` compiles against system cairo/pango.
  - **A fresh install resolved manim 0.21.0 while this repo ran 0.20.1**,
    so "fresh framework every time" was also "different manim every
    time" — the dev repo was the *more* stable environment, the opposite
    of the intuition. Closed in session seventeen.
- Bearing on the recurring flash report: of 13 exported decks on disk only
  the newest carried the `instant_navigation` script, and
  `webrunner_output/` is a permanent static mount, so **every pre-fix
  export is still live at its original URL** — reachable from history or
  a bookmark, and it will flash however carefully the deck was generated.
  A per-run fresh project removes that class. → 155 tests.

**16 (2026-08-28)** — Enforcement moved into the authoring context,
driven by transcript evidence rather than by adding checks.
- **What the logs showed.** Six build sessions mined from
  `~/.claude/projects/.../*.jsonl` alongside `media/progress/*.json`.
  `validate.py` worked exactly as designed and still did not save the
  run: it cut cost *per* iteration (~9s render → ~2s validate) while
  leaving the iteration *count* untouched. The pre-validate build ran **23
  renders** in `AUTHOR RENDER` cycles (511 assistant turns); the
  validate-driven build ran **15 validates across 54 edits** (295 turns).
  Of 38 validate runs across four sessions, 24 passed — most invocations
  were confirmations, not discoveries. Session ten's finding held, and
  the cheaper check did not address it.
- **What the failures actually were**: ten-plus `AttributeError` on
  segment-to-segment state handoff, surfacing as a cascade several
  segments from the typo, and twelve overlap/safe-frame failures at
  invented per-segment coordinates. **Both are decided before any check
  can run** — a check can only report them after the code exists, which
  is the round trip.
- **The fix: `scaffold.py` emits authoring context, not just stubs.** It
  takes the plan table's own columns (`Segment(name, shows, carries,
  produces)`) and writes a composition block of named slots derived from
  the real frame, a declaration of every cross-segment attribute, and per
  segment its carried-in names, hand-off names, and the audience's
  play/word budget. The agent then positions against `COL_LEFT_X` instead
  of guessing `-3.5`, and writes `self.roof_fig` in both places because
  the name is already in the file.
  - **Declarations are annotations, never assignments.** `fig: Mobject`
    documents the name without creating the attribute, so a missed
    handoff still raises loudly, by name, locally. `fig = None` would
    trade a loud failure for a silent `None` flowing downstream; a test
    pins this.
  - **`check_plan()` rejects the plan itself**, before any code exists: a
    carried name no earlier segment produces, or a third cleared start
    (R1). R1 finally has a real gate, at the cheapest possible moment.
  - **The composition constants floor rather than round.** A test caught
    this while being written: rounding the column half-width put the outer
    edge at 6.62 against a 6.61 safe bound, so the slots meant to
    guarantee safe placement would themselves have failed the check.
- **Verified end to end**: a two-segment deck authored using only the
  emitted slots and declared names passed `validate` on the **first
  attempt**, no round trip — and the same scaffold runs in the fresh
  `npx` project on manim 0.21. → 169 tests.

**17 (2026-08-28)** — Next step 10 closed, two prose-only content rules
gated, everything measured against all 11 local decks (77 segments)
before being built.
- **The `decorative`/safe-framed pair check exists** — `TextOnDecorative`,
  reported by `validate.py` off `base.py`'s `find_text_over_decorative()`.
  The rule that works is **decorative *ink* vs tracked *text* box**, and
  each narrowing was forced by a measurement:
  - bbox-vs-bbox, the obvious rule, reports **25** findings — a brace
    hugging a side, ticks poking off a meter — nearly all benign. Testing
    the strokes reports 7, all real.
  - the strokes must be walked as a *polyline* through each leaf's Bezier
    control points. The control points alone miss the canonical case
    outright: a `Line` has four, all at its ends, so an axis running
    straight through a caption contains none of them.
  - only **text** is tested. Non-text over a backdrop is routinely
    correct — a plotted curve crosses its own axis by construction — and
    that ambiguity is the whole reason `decorative=True` exists.
  - a backdrop whose bbox *contains* the text is framing it, not
    colliding with it, and is skipped.
  - clearance 0.08 sits mid-plateau: the finding set is **identical** from
    0.0 to 0.08, and the first false positive lands at 0.12 (a label
    docked just outside the figure it belongs to). It is a collision
    detector; a real clearance policy flags deliberate work.
- **Positive control, because a check that reports nothing proves
  nothing.** Session fourteen's caption-through-tick-numbers bug,
  reconstructed by reverting the 0.45 figure lift that fixed it, is
  reported across six segments. It then found **two live collisions in
  decks that pass everything else**, both confirmed against the rendered
  frames: a marker stroke merging into the top of an `∫` glyph
  (`dominated_convergence` seg-07), and an `=` sign touching the box
  drawn around the result, in six segments of `basic_calculations`. Both
  still unfixed — deck content, per the scope boundary.
- **R2 and R4 are counted now, not self-graded** (`NoChangeAnimation`,
  `UnperformedAction`), and `AUDIENCE` — written since session sixteen
  and read by nothing — finally sets R2's floor. The evidence for wiring
  them: **19 R2 findings, every one in a deck written before the rule
  existed; zero in the seven written under it.** That is the profile
  worth gating on — it fires on the past and is silent on the present, so
  it is regression prevention, not discovery. Segment 0 is exempt (a
  cleared opening has nothing to change yet).
  - Emphasis must be excluded **by class, before descending**: `Indicate`
    is a `Transform` subclass and `Circumscribe`/`Flash` are
    `AnimationGroup`s, so the obvious isinstance test accepts a pulse as
    the segment's change — precisely what R2 says doesn't count.
- **R7 was the wrong next candidate, and the corpus says so.** Step 10
  named it as the remaining AST check. Measured: the longest prose string
  in any deck is 11 words against a 12-word cap, the largest on-screen
  total 14 against 25 — **zero violations anywhere, including in the
  decks that predate the rule**. Not built. R3 and R5 likewise (2
  findings each, both pre-rules): the yield doesn't pay for the surface.
- **A real harness bug fell out of the measurement.** `_instant_play`
  never replicated `Scene.compile_animation_data`'s
  `add_mobjects_from_animations`, so mobjects a real render puts on
  screen were absent from `scene.mobjects` here. Harmless for the
  existing checks — they read `_active_ids` — but it silently corrupted
  R2's count until fixed, and would corrupt any future scene-graph check.
- **The Liang-Barsky branches were inverted in the first
  implementation**, and both the probe and the shipped code carried the
  same error, so the corpus numbers agreed with each other while
  measuring the wrong predicate. A unit test written from the canonical
  case caught it; every number above is post-fix. **A measurement and the
  code it validates sharing an author is not independent confirmation.**
- → 187 tests. `SKILL.md`'s review step drops its two source greps (R2/R4
  are counted upstream now) and keeps the judgement they stood in for.
- **Committed and pushed.** Sessions fourteen through seventeen went in
  as five commits; `main` is pushed, and `origin/main` had been six
  commits behind since before this session. A `git+file://` install
  through the `npx` bootstrapper built a project from the *committed*
  tree — which is what proves the commits are self-sufficient, since a
  git install cannot see the working directory — and the default
  `--from git` path was then verified against GitHub itself: **13s** from
  nothing to a working project, full pipeline green (`init` → scaffold →
  `validate` → `-ql` render → `frames` → `blankspace` → HTML export →
  `playback`, 4/4 navigations correct).
- **Dev environment moved to manim 0.21.0**, closing session fifteen's
  drift risk. Only manim changed in the freeze. Evidence gathered before
  bumping `VERIFIED_MANIM`, since that constant means the recipes were
  re-checked rather than assumed: all 14 `motion-recipes.md` snippets
  construct-verified through the instant-play harness; both documented
  *bugs* still caught by the checks that catch them; recipe 10's
  behavioural claim reproduced numerically (`Angle` still sweeps 323° for
  rays at 0° and −37°, the exact figure it cites — a construct-only pass
  would have missed that changing); 187 tests passing; all 11 decks
  validating **identically** to the 0.20.1 baseline; and a 31-animation
  deck rendering clean in 5s.

**18 (2026-09-08)** — First outside review of the whole tree, by an agent
with no prior context. Read every module and both skill references, built
the environment from scratch, and ran the pipeline end to end in a fresh
`init` project. Findings are separated below into things that were wrong
and things that merely disagreed with each other, because the second kind
is what a review from inside the project reliably misses.

- **The environment build is itself a finding.** `pip install -e ".[dev]"`
  fails on a clean Ubuntu image — `manimpango` needs `libcairo2-dev` and
  `libpango1.0-dev`, which `README.md` says and the error does not, since
  it surfaces as a pkg-config exit status inside a build backend. `doctor`
  reports it correctly *after* the install fails, which is the state it was
  designed for. Nothing changed; recorded because the first ten minutes of
  any fresh review are spent here.
- **R2 rejected the framework's own recipe.** A segment whose change is
  `tracker.animate.set_value(...)` driving an `always_redraw` mobject —
  `motion-recipes.md` recipe 2, and named in R2's rule text — reported
  `NoChangeAnimation`. A `ValueTracker` keeps its number in its own
  coordinates and is never added to the scene (the recipe adds the *dot*),
  so `_change_animations`' on-screen family test structurally cannot see
  it. This is the failure mode the repo already knows is the worst kind:
  a check that fires on correct, documented work teaches the author to
  ignore the check, and `test_legible_text_swaps_are_not_flagged` says so
  in as many words. Fixed by exempting a tracker sweep **gated on
  something on screen carrying an updater**, so a tracker no figure reads
  still reports no change; both directions are pinned by tests. It went
  unmeasured in session seventeen because the corpus that validated R2 was
  eleven existing decks, and a check can only be measured against work
  that already exists — the recipes it *invites* are exactly what a corpus
  cannot cover.
- **The scaffolded file imported two names.** Session sixteen's thesis is
  that anything decided before a check can run belongs in the file the
  agent starts from, and `SKILL.md`'s own list of what makes a run balloon
  names "adding an import in one turn and using it in the next" — yet the
  file arrived with `Slide` and `assert_within_safe_frame` for a workflow
  whose documented segment shape uses `np.array`, `heading()`, `Text`,
  `VGroup`, `Transform` and a colour token in its first ten lines. Now
  emits `numpy as np`, `from manim import *`, and every theme token and
  template. The star import is the decision worth defending: a curated
  list is complete for the deck it was written for and wrong for the next
  one, which restores the same round trip *and* adds a question about
  whether extending it is allowed. It is also manim's own documented
  convention, and a deck is a leaf artifact. Verified by executing the
  emitted module and asserting each name the stub's checklist points at
  resolves.
- **Two layout systems, both recommended.** `theme.two_column()` arranges
  its halves with `VGroup.arrange`, which centres them on their own
  content width: measured at x = -1.05 / +2.00 for one pairing, moving to
  -1.02 / +1.00 when the content narrows. That is per-segment placement —
  precisely what the composition block exists to abolish — and
  `framework-rules.md` recommended it two sections after `SKILL.md`
  forbade the practice. Resolved by scope rather than deletion:
  `two_column` is for a self-contained pair inside one segment, the slots
  are the deck's layout, and the scaffolder omits `two_column` from a file
  that carries a composition block so the file cannot offer both.
- **`HEAD_Y` was off, and its comment claimed more than it knew.**
  `heading()` pins the text's *top* at 3.35, so a one-line 36pt heading
  centres at 3.11-3.16 and its descenders reach ~2.86; the slot asserted
  3.0 and said "heading() sits here". Now measured, and states the floor
  to keep clear. The comment column also aligns, which it did not for the
  one negative slot.
- **Tool and workflow disagreed on a number.** `blankspace` flagged a
  segment `<- sparse` below 15% fill while `SKILL.md`'s review makes a fix
  mandatory below 20%, so a segment at 18% read as fine in the output and
  had to be fixed by the table. Aligned to 0.20.
- **Smaller, all fixed.** `progress start <Deck> 0` raised
  `ZeroDivisionError` from inside the status line the tracker exists to
  print (a zero-length budget is now rejected at parse). `Slide.remove`
  overrode a method that returns `Self` and returned `None`. Every
  `read_text`/`write_text` in the package used the platform default
  encoding — harmless on Linux, and unable to write a deck title in the
  language this project was generalized from on Windows; all now pin
  UTF-8. The four tests that compile a `MathTex` hard-failed without
  latex, which `doctor` calls optional, so a correct checkout looked
  broken; they skip now, as the browser test already did.
- **What was deliberately not built.** Session seventeen measured R3, R5
  and R7 against 77 segments and declined them; nothing here revisits
  that, and the corpus is not in the repo (`decks/` is gitignored), so no
  claim in this entry rests on re-measuring it. The `decorative`-on-subject
  rule and the scaffold checklist deleting itself before review are still
  ungated, both known from session fifteen's audit.
- **Verified**: 193 tests (up from 187) plus the browser test skipped for
  want of Firefox; `init` → scaffold → author → `validate` clean on the
  first attempt for a middle-school deck (the ≥2-changes audience) →
  `-ql` render → `frames` → `blankspace` → HTML export with the enum
  quoting and the instant-navigation script both intact.

- **The validation corpus, built** (`tests/fixtures/corpus/`, driven by
  `tests/test_corpus.py`). The user's objection to a reference deck was
  correct and is the reason this is not one: a single canonical deck put in
  front of every agent costs exactly the presentational freedom the seven
  rules were written to protect, and the repo already fights that with
  `exemplar.md`'s anti-copy line and the test-run rule. What was missing is
  a different artifact, and it must not be good. Nine fixtures are wrong on
  purpose, one per gated finding, pinning that the check *can* fire and
  with what — the standard the browser test was held to in session
  thirteen, applied to the headless checks. Five are correct decks built
  from constructs the framework recommends, and they are the expensive
  half: the false-positive guard a proposed check is run against before it
  ships. They are deliberately heterogeneous (driven diagram, dissection,
  centred summary, boxed result, equation step) so passing the corpus does
  not silently become matching one house style.
  - **Writing it found three real defects in the fixtures themselves**, all
    caught by the checks under test: `Indicate(x)` beside `x.animate` in
    one play is a genuine `ConflictingAnimations`; shifting a result out
    from under its own `SurroundingRectangle` is a genuine
    `TextOnDecorative`. Both were my mistakes and the checks were right.
  - **The corpus immediately paid for itself on R4.** Building it surfaced
    that R4 scanned headings, so an opening segment headed "A Moving Point"
    was reported for promising an action nothing performs yet — and *every*
    deck titled after what it demonstrates hits this, because an opening
    segment only introduces things and introductions are not changes, which
    is exactly R4's firing condition. Fixed by scoping R4's scan to the set
    R7 already defines: "headings, labels, and equations don't count."
    The two rules had simply disagreed about what prose is. Size decides
    rather than track id, since an author may not have reached for
    `heading()`, and the comparison carries a point of slack because manim
    recomputes `font_size` from height — a 36pt heading reads back as
    35.999999999999964, so an exact `>=` silently missed every one of them.
    Both directions are pinned in the corpus:
    `heading_names_the_subject.py` must stay clean, `empty_promise.py` says
    the same words at caption size must still be reported.
  - `corpus/`, not `decks/`: the gitignore's bare `decks/` pattern matches
    at any depth, so `tests/fixtures/decks/` would have been silently
    untracked. The name also keeps it clear of the test-run rule.
- **Two configurable axes, and the design question is who chooses.** The
  user asked for customizable imports and a simple/advanced split. An
  option the *agent* re-picks every build is a fresh source of the
  inconsistency the composition block was added to remove, so both resolve
  from an explicit argument, then `open-manim-slides.json` in the project
  root, then the mode default. The project owner pins it once; the skill
  tells the agent to pass nothing.
  - `imports`: `"all"` (default star import), `"curated"` (the names the
    documented recipes use, which reads better and states the house
    vocabulary at the cost of one edit when a deck needs something else),
    `"minimal"` (the pre-session-18 bare file, kept as an explicit choice
    so nobody falls back into it), or an explicit list.
  - `mode`: `"simple"` or `"advanced"`. **The line between them is the
    whole design: advanced relaxes the pre-commitment gates, never the
    correctness checks.** Composition, R1's cleared-start ceiling and the
    stub checklist are house style, and a deck may have a good reason to
    differ. Safe frame, overlap, conflicting animations, illegible morphs,
    R2 and R4 catch defects, and `validate` is byte-identical under both.
    Without that line "advanced mode" would just mean "the checks are
    optional", which is the state the framework exists to leave.
- **`assert_no_overlap_among_tracked(allow=...)`** — the gap "remove some
  restrictions" actually pointed at. The framework had no sanctioned way to
  say two things overlap on purpose (a Venn lens, a label on its region, a
  card stack). The two things an author reached for instead were deleting
  the scaffolded call, which is silent and rule-forbidden, and
  `decorative=True`, which exempts the element from every comparison and is
  forbidden for a subject. `allow` takes a pair of ids, exempting only that
  pair, or a single id. It is narrower than either workaround and leaves
  the intent in the file where the next edit can read it.
- **Two smaller findings from the review closed.** `progress phase <Deck>
  reviewing` used to be stored happily and then read back as an expected
  share of zero, so every later call reported `BEHIND` and advised cutting
  scope for a run that was on time; an unknown phase name is now refused
  and the message lists the seven. And `frames.py` called `int()` on
  ffprobe's `nb_frames`, which is a container-level field: mp4 carries it,
  matroska reports `N/A`, a truncated file gives nothing, and the result
  was a bare `ValueError` that never named the video. It now falls back to
  counting packets (exact, one demux pass, which is why it is the fallback)
  and otherwise raises a `FramesError` saying which file and what both
  probes returned.
- **Verified**: 234 tests. `init --mode advanced` writes the settings file,
  and a deck scaffolded afterwards with no arguments picks it up — no
  composition block, curated imports, brief stub — and executes.

**19 (2026-09-22)** — First 3D deck, user-directed (`decks/
vectors_transformations_and_determinants.py`: vectors, addition, dot
product, a linear transformation, the determinant, then a real 3D vector
with a camera move). The environment had never been set up in this
container: `pip install -e ".[dev]"` needed `libcairo2-dev`/
`libpango1.0-dev`/`ffmpeg` (session 18's finding, still accurate) and no
LaTeX was installed at all, so `MathTex` was unavailable until
`texlive-latex-extra`/`texlive-science`/`dvisvgm`/`cm-super` went in.

- **`ThreeDSlide` built** (`base.py`) — `class ThreeDSlide(Slide,
  _BaseThreeDSlide)`, mirroring manim-slides' own `ThreeDSlide(Slide,
  ThreeDScene)` pattern one level down. Verified by construction that this
  MRO resolves without a custom `__init__` (neither `manim_slides.Slide`/
  `BaseSlide` nor `ThreeDScene` override it, so `Slide.__init__`'s existing
  `super().__init__(**kwargs)` chain already reaches `Scene.__init__`
  regardless of which mixin sits in between). Default camera (`phi=0`)
  renders identically to a plain `Slide`, so a deck can open flat and cut
  into 3D only for the segment that needs it — confirmed by rendering a
  fixed-in-frame heading over a tilted camera and reading the frame back:
  crisp, flat, unrotated.
  - **A real bug fell out immediately**: `validate.py`'s `load_scene_class`
    picked the deck's class by `issubclass(value, Slide) and value is not
    Slide` over the whole module namespace, and `ThreeDSlide` itself
    satisfies both conditions the moment a deck imports it to subclass —
    so every 3D deck reported a false "several Slide subclasses" ambiguity
    between the deck's own class and the base class it imported. Fixed by
    scoping candidates to `value.__module__ == module.__name__` (defined
    *in* the deck file, not merely imported into it), which also let the
    stale `value is not Slide` special-case be dropped entirely. Pinned
    with a regression test importing exactly that shape.
  - **Two 3D gotchas banked into `motion-recipes.md`** (recipe 12), both
    construct-verified before being written down, not assumed: `GrowArrow`
    raises on `Arrow3D` (`TypeError: VMobject.scale() got an unexpected
    keyword argument 'scale_tips'` — it calls `Arrow.scale(0,
    scale_tips=True, ...)`, a 2D-only override `Arrow3D` doesn't have; use
    `Create` instead), and `move_camera()`'s own animation never satisfies
    R2 (its phi/theta/zoom `ValueTracker`s are never part of
    `scene.mobjects`, so nothing about the cut itself can count as "changed
    something on screen" — pair it with a real change via `added_anims=`).
- **The safe-frame/overlap checks' 2D-only nature has a real cost in 3D,
  not just a theoretical one.** `_bbox` reads `get_corner()`'s x/y and
  ignores z, which is *exactly* right for a fixed-in-frame heading (still
  meaningful 2D screen-space) but only a rough proxy for a 3D mobject's
  true on-screen footprint under a rotated camera — two vectors separated
  in depth but sharing an x/y footprint report a false
  `assert_no_overlap_among_tracked` collision (worked around with `allow=`,
  same mechanism as any other deliberate overlap). Documented in
  `ThreeDSlide`'s own docstring so the next 3D deck doesn't rediscover it.
- **A shear's reach scales with the grid's own half-extent, and the first
  attempt at `apply_matrix()`-driven grid warping did not account for
  it.** Applying a shear matrix to a `NumberPlane` sized to fill the
  column (as segments 1-4 correctly do) sends its far corners flying: the
  top-right corner landed on top of the text column and the bottom-left
  corner left the safe frame entirely — both invisible until `validate`
  ran, at which point they read as an ordinary safe-frame/overlap failure
  with no hint of the geometric cause. Fixed by zooming the grid down by
  half (`plane`/`vec_v`/`vec_w` all `.animate.scale(0.5, about_point=
  origin)`) in its own beat *before* the shear, rather than shrinking the
  grid for the whole deck — segments 1-4 keep the larger, column-filling
  grid, only the transformation segment needs the extra headroom.
  `apply_matrix(matrix, about_point=...)` also defaults `about_point` to
  the *world* origin, not the mobject's own center — every call in this
  deck passes `about_point=plane.c2p(0, 0)` explicitly, and the plane's
  x/y scale has to be isotropic (equal scene-units-per-axis-unit on both
  axes) for a raw numeric matrix applied to *scene*-space points to equal
  the intended *axis*-space linear map at all.
- **The visual review caught what `validate` structurally cannot**, same
  shape as sessions eight/fourteen/seventeen: `vec_w` and the transformed
  unit square shared `COLOR_ACCENT_2`, reading as one indistinguishable
  yellow blob where they overlapped near the origin (fixed: the square
  isn't compared *against* v or w, it measures the region they span, so it
  took `COLOR_MUTED` instead) — no check flags a color choice. Also caught
  by rendering and reading the *contact sheet*, not the final frame
  (review Q7): a `FadeTransform` between the 3D deck's two fixed-in-frame
  headings rendered its interpolated mobject tilted with the still-moving
  camera, only snapping flat on landing, and a plain `FadeOut`+`Write` pair
  tried next just ghosted both strings through each other at one shared
  position. Neither is `IllegibleTextMorph` (both strings stay individually
  legible, just wrong), so neither is mechanically catchable — fixed with
  an instant `self.remove(old_head)` followed by a plain `Write(new_head)`,
  which is what segment 7's own (already-correct) heading entrance did
  from the start. **Lesson for `motion-recipes.md`'s `FadeTransform`
  guidance**: it is not proven safe with `add_fixed_in_frame_mobjects` and
  should not be reached for there without re-verifying.
- **Scope note**: this deck deliberately does not attempt R1's "≤3 new
  symbols" (middle-school) framing — high-school was picked as the closer
  audience fit for matrix/determinant notation, and even so the deck sits
  at roughly the ≤8 symbol ceiling by design (reusing `v`/`w` throughout,
  one concrete matrix, no generalization to `a,b,c,d`). Not re-litigated
  against session seventeen's R3/R5/R7 measurements — this is a single
  real deck, not a corpus addition.
- **Verified**: `validate` clean, `-ql` render → `frames` → `blankspace`
  (dead space 27%→26%, all 8 segments ≥20% fill after the grid-size and
  color fixes) → full-quality render, all in the fresh venv built this
  session. 238 tests collected (3 new: two for `ThreeDSlide` itself, one
  pinning the `load_scene_class` fix), 232 passed, 2 skipped (browser
  playback — no Firefox in this container, as session 18 also hit), 4
  failed on `test_webrunner.py` for want of the optional `fastapi` extra
  (`pip install -e ".[web]"` was never run this session — pre-existing gap,
  not a regression).

## Immediate next steps (priority order)

Done and folded into the history above: `assert_no_overlap` and its
wiring, the manifest appearance gap, the design system, the PR #664
workaround, the background-video flash, and the decorative/safe-framed
pair check.

1. **Site build-out** (decision 4) — `webrunner/` is a real but partial
   slice (render + present). Still unbuilt: the manifest-driven
   click-to-comment flow, the apply-comments skill, the public/author
   permission split. Natural next step: surface `track()`'s manifest ids
   in the runner's UI.
2. **Publish decision** — `open-manim-slides` is free on both npm and
   PyPI. `main` is pushed and the `npx … --from git` default is verified
   end-to-end against GitHub, so the workflow works today for anyone with
   the repo URL. Publishing is outward-facing and waits on the user; it
   needs `npm login` plus `build`/`twine`, neither installed here. Once
   published, `--from pypi` pins the framework to the npm package's own
   version so the two releases cannot drift.
3. **Grow example content** — eleven dev-only decks exist locally, none
   on `main` (`decks/` is gitignored). Promoting any to a curated public
   gallery is a content decision left to the user. Two of them carry
   known, unfixed collisions found in session seventeen.
4. **Bound manim in `pyproject.toml`?** — unpinned today. The 0.20.1 →
   0.21.0 move was clean (187 tests, 11 decks identical, 14/14 recipes
   re-verified), which argues for leaving it open rather than guaranteeing
   it stays true. Distribution policy, so the user's call.
5. **Convex-hull + SAT for `assert_no_overlap`** — session seventeen's
   ink check covers *text* over a decorative element, which was the
   recurring case. What remains is the diagonal-line-vs-nearby-content
   false positive between two genuinely independent non-text elements,
   where `decorative=True` is still the blunt workaround. Evaluated and
   deliberately deferred, not an oversight.
6. **Narration alongside decks** (session seven) — the upstream carrier
   exists (`next_slide(notes=...)` → RevealJS `show_notes`); the slice is
   scaffold placeholder → script written by `create-deck` → webrunner
   script pane, with TTS as a later layer. Awaiting direction.
7. **Deck series — shared context across related decks** (user's idea,
   not yet built). Every `create-deck` run is independent, so a second
   deck on the same topic re-decides everything the first settled: which
   color means which quantity, how the recurring figure is oriented,
   which symbols the audience has met. The framing that makes it
   concrete: **R1 lifted from the segment level to the deck level** —
   deck N+1 opens by *changing* deck N's closing figure, exactly as
   segment 4 opens by changing segment 3's. Sketch: a series file
   (`decks/<series>/series.json`) read before planning and appended to
   after building, carrying audience, color→meaning bindings, figures
   established and their orientation, symbols already introduced (so the
   "≤8 new symbols" budget becomes cumulative), and what each prior deck
   covered. Open questions: how a series is declared (directory vs
   explicit arg), and whether the carried closing figure is re-derived
   from source or from manifest bboxes. This pulls opposite to the
   test-run rule (load *less* context vs *more*) — correctly: a test run
   simulates an empty environment, while a series deliberately carries
   real, author-owned state forward.

## Reference

- Repo: https://github.com/lapotist/open-manim-slides
- Upstream manim-slides bug being tracked: https://github.com/jeertmans/manim-slides/pull/664
  (merged 2026-08-20, not yet released — still 5.6.0 from 2026-04-15; the
  workaround in `convert.py` stays until the floor moves past whichever
  release ships it)
- open-slide (design reference for *shape*, not a spec to copy blindly):
  https://open-slide.dev/, https://github.com/1weiho/open-slide
