---
name: create-deck
description: Scaffold a new Manim Slides deck (one file, one segment function per slide) and fill in its content from a natural-language description. Use when the user asks to create, start, or generate a new deck, presentation, or lesson.
---

# create-deck

Builds a deck that *moves*. A deck where every segment clears the screen,
writes a heading, and parks a static picture under it is a slideshow —
the failure mode this workflow exists to prevent.

References (in this skill's `references/` directory):

- `exemplar.md` — one segment at target quality. **Read it in step 2.**
- `motion-recipes.md` — verified animation snippets. **Read it the
  moment your plan table names `Transform`, `ValueTracker`,
  `MoveAlongPath`, `Axes`, or `Brace` — before writing that segment.**
- `framework-rules.md` — tracking/check mechanics. **Read it whenever an
  `assert_*` raises, before changing any code.**

**If the user calls this a test run**, build from these references and the
framework's own API surface (`theme.py`, `base.py`, `layout.py`) only.
Do **not** read other files under `decks/`, and do **not** read this
repo's development docs (`HANDOFF.md`, session history). A test run
simulates a real invocation — and someone who installed this package to
build a deck has none of that: no example decks, no handoff notes, no dev
history. Reading them measures a context no real run would have, hides the
gaps in this skill's own written guidance, and biases the output toward
copying an existing deck instead of reasoning from the rules.

## The seven rules

Every segment is written against these. Each has a mechanical check —
run the checks on your finished deck, don't trust your intent.

- **R1 — Carry something forward.** At most 2 segments in the whole deck
  may start from a cleared frame; every other segment begins by
  *changing* what's already there (shrink and move the previous figure
  aside, dim a heading, transform an equation into its next form).
  Enforced when you scaffold: the plan's "carries in" column is what
  decides this, and a third cleared start is rejected there — before any
  code exists.
- **R2 — Something must change, not just appear.** Each segment needs at
  least one `self.play()` that alters a mobject already on screen.
  Counts: `Transform`/`ReplacementTransform`/`TransformMatchingTex`,
  `.animate`, `MoveAlongPath`, `Rotate`, `ValueTracker` +
  `.animate.set_value`. Doesn't count: entrances (`Write`, `Create`,
  `FadeIn`, `GrowArrow`, ...), the clearing `FadeOut`, or emphasis
  (`Indicate`, `Flash`, `Circumscribe`, `Wiggle`). The change must carry
  the idea: if deleting it would make the segment say *less* — not just
  look duller — it counts. `validate` counts the floor for you (reading
  `AUDIENCE`, so middle school needs two); whether the change carries the
  idea is the half no count reaches.
- **R3 — A non-text mobject in every segment** except the opening title
  and closing summary, with on-screen text *anchored* to it: a `Brace`
  with `get_tex()` under the term being discussed, an arrow from symbol
  to referent, or the previous segment's figure kept alongside. A shape
  nothing refers to doesn't satisfy this.
- **R4 — If you write it, show it.** Scan every on-screen string for
  action verbs (*rotate, turn, move, slide, grow, shrink, add, double,
  halve, fold, flip, sweep, split, combine, rearrange, fill, cover,
  trace, increase, decrease, cancel, balance*). Each hit needs an
  animation in that segment performing it. Can't animate it? Delete the
  sentence — it's a promise the slide doesn't keep. `validate` reports
  the flagrant case (a verb on screen while nothing but text is animated);
  matching each verb to the animation that performs it is yours.
- **R5 — At most 6 `self.play()` per segment** (4 for middle school),
  and the heading arrives *with* the first figure, never on its own
  beat: `self.play(Write(head), Create(figure))`. And the reader sets
  the pace, not the renderer: plays inside one segment auto-advance, so
  **an equation the audience must read gets its own segment** — never
  chain two equation transforms back-to-back in one segment; the
  intermediate line flashes past before anyone reads it.
- **R6 — Color carries meaning.** Each thing a segment compares gets its
  own color (`COLOR_ACCENT`, `COLOR_ACCENT_2`) and keeps it; equations
  are built multi-arg (`MathTex("a^2", "+", "b^2")`) so a term can wear
  the color of the shape it counts. Never color for decoration.
- **R7 — One sentence of prose on screen at a time, ≤ 12 words.**
  Headings, labels (`a`, `θ`), and equations don't count.

Two framework rules with no error message when violated, so they live
here: **never delete the scaffolded
`self.assert_no_overlap_among_tracked()` line**, and **never mark a
segment's subject `decorative=True`** (exact criteria for that flag:
`framework-rules.md`). Marking something decorative no longer hides it
completely — `validate` reports text landing on a decorative element's
strokes — but it does still remove it from the overlap check, so the rule
stands.

## 1. Gather the deck's shape

From the user's request (ask if missing):

- **Title** — short, human-readable.
- **Audience** — `middle-school` or `high-school`. This changes the
  outline, not just wording:

| | middle-school | high-school |
|---|---|---|
| segments | 5–6 | 7–9 |
| new symbols in the whole deck | ≤ 3 | ≤ 8 |
| notation ceiling | `+ − × ÷ = < >`, `x²`; variables from `a b c x y`; no subscripts, no `f(x)`, no `Σ` | `f(x)`, subscripts, fractions, radicals, `Σ` |
| concrete vs general | concrete numbers first (a 3-4-5 triangle, not `a, b, c`); general form last or never | one concrete case, then generalize |
| derivations | no symbolic chains — one step per segment, each step also shown on the picture | ≤ 3 steps, one segment each (R5), still anchored to a figure (R3) |
| words on screen at once | ≤ 18 | ≤ 25 |
| sentences | ≤ 10 words, present tense | ≤ 14 words |
| change animations per segment (R2) | ≥ 2 — the picture *is* the argument | ≥ 1 |
| `self.play()` per segment (R5) | ≤ 4 | ≤ 6 |
| opening segment | a visual situation before any symbol | may open with the statement |

- **Time budget** — optional, e.g. "20 minutes", "quick". If the user
  gives one, pass it to the tracker below and scale the work to fit; if
  they don't, track time anyway and don't cut anything.

### Start the tracker, and report progress as you go

```bash
python -m open_manim_slides.progress start <ClassName> [budget]   # e.g. 20m
```

Then at **every** phase boundary — `scaffold`, `code`, `validate`,
`render`, `review`, `finish`:

```bash
python -m open_manim_slides.progress phase <ClassName> <phase>
```

**Paste the line it prints into your reply to the user.** A command's
output goes to you, not reliably to their terminal, so relaying it is the
only thing that makes it a status update — and going silent through a
long build is the specific complaint this exists to fix. One line per
boundary, nothing more.

The tracker judges drift at each boundary and prints `BEHIND` with what
to cut, or `OVER` when the budget is spent. **Follow that advice** — it
is scoped to the phase you are entering. Budget shapes the plan up front
too:

| budget | segments | review | render |
|---|---|---|---|
| ≤ 10 min | audience minimum (5 / 7) | one round, final frames only, no re-review | `-ql`; full-quality only if time is left |
| 10–25 min | normal for the audience | one round + re-review of edited segments | `-ql`, then full-quality |
| > 25 min or unset | normal | full round + re-review | `-ql`, then full-quality |

Finish with `python -m open_manim_slides.progress report <ClassName>` and
include the breakdown in your closing message.

## 2. Plan before code — the segment table

Read `references/exemplar.md` now. Then produce this table, one row per
segment, and show it to the user with the outline:

| # | segment | the one thing it shows | carries in (`self.x`) | hands off (`self.x`) | the change animation (R2) | the non-text mobject (R3) |
|---|---|---|---|---|---|---|

Every cell filled, before any code. **The two `self.x` columns are
attribute names, not prose** — `fig`, `axes`, `eq_area` — and they are
what step 3 feeds to the scaffolder, so spell them exactly. A segment's
"carries in" must appear in some earlier segment's "hands off"; the
scaffolder rejects the plan otherwise, before any code exists. That check
is worth its weight: a carried name that nothing produces is the single
most common failure in past builds, and once written it surfaces as an
`AttributeError` several segments away from the typo.

If "carries in" is empty for more than 2 rows, the deck is a slideshow —
redesign the outline so segments build on each other (the scaffolder
rejects a third cleared start too). If a "change animation" cell names
`Transform`, `ValueTracker`, `MoveAlongPath`, `Axes`, or `Brace`, read
`references/motion-recipes.md` before writing that segment.

### Commit to one composition, for the whole deck

Decide *now* where things live, and hold it in every segment. Deciding
per-segment is what produces a deck with a figure adrift in the middle
and a third of the frame no segment ever touches.

You do not have to invent the numbers: the scaffolded file arrives with
a composition block already derived from the real frame, and every slot in
it is inside the safe margin by construction.

```python
SAFE_X = 6.61          # |x| any element must stay within
SAFE_Y = 3.5           # |y| any element must stay within
HEAD_Y = 3.0           # heading() sits here; leave this band clear
COL_LEFT_X = -3.45     # centre of the figure column
COL_RIGHT_X = 3.45     # centre of the accumulating-text column
COL_W = 6.3            # size the figure to FILL this, not float in it
ROW_Y = (1.9, 0.9, -0.1, -1.1, -2.1)   # text rows, top-down
```

- **Left column** — the figure, sized to *fill* `COL_W` (roughly 5-6
  units wide). A 2-3 unit diagram in a 6-unit column is the single most
  common cause of an empty-looking deck.
- **Right column** — the accumulating text: equations, results, the
  running reference. Start at `ROW_Y[0]` and grow *downward*, so the space
  beneath is visibly reserved for later segments rather than left over.
- **Position against these names, never a fresh literal.** Every
  safe-frame and overlap failure in past builds was an invented
  per-segment coordinate. `move_to(np.array([COL_LEFT_X, ROW_Y[1], 0.0]))`
  cannot produce one.

Decide here — not while debugging a layout — where you deviate (a
full-width title, a summary that centres).

Targets, checked mechanically in step 6: **every segment ≥ 20% fill, no
region ≥ 15% of the frame left unused by the whole deck.**

## 3. Scaffold (deterministic, not freehand)

Feed it the table — every column, not just the names. The plan is the
input to the file's structure, so nothing you decided in step 2 has to be
remembered again while coding:

```bash
python -c "
from pathlib import Path
from open_manim_slides.scaffold import new_deck, Segment
path = new_deck(
    title='<title>',
    audience='<audience>',
    out_dir=Path('decks'),
    segments=[
        Segment('<name>', shows='<the one thing it shows>',
                carries=[], produces=['<self.x it hands off>']),
        Segment('<name>', shows='<...>',
                carries=['<self.x from an earlier segment>'], produces=['<...>']),
    ],
)
print(path)
"
```

It **rejects the plan** — before a line of deck code exists — if a
segment carries a name no earlier segment produces, or if more than two
segments start from a cleared frame. Fix the plan, not the deck.

Writes `decks/<slug>.py`: the composition block above, a declaration of
every handed-off attribute, and one `segment_<name>` method per row —
each stating what it carries in, what it must hand off, its audience play
and word budget, and ending in `self.assert_no_overlap_among_tracked()`
(not optional). The notes are there to be deleted as you satisfy them.

## 4. Fill in each segment

The shape of a good segment (see the exemplar for a real one):

The stub already tells you what this segment carries in, what it must
hand off, and its play/word budget. Author against those and the
composition slots:

```python
def segment_<name>(self) -> None:
    """<the one thing this segment shows>"""
    # carried in:  self.figure, self.eq
    # hand off:    self.part   <- set before returning
    # budget:      <= 6 self.play() calls, <= 25 words on screen  [high-school]
    self.play(self.figure.animate.scale(0.6).move_to(np.array([COL_LEFT_X, 0.0, 0.0])))

    head = heading(self, "<3-5 words>")               # 36pt, top, tracked
    part = self.track(Polygon(...), id="<kebab-id>")
    assert_within_safe_frame(VGroup(head, part))
    self.play(Write(head), Create(part))              # R5: arrive together

    self.play(Transform(part, part_after))            # R2: the change that IS the idea

    self.part = part                                  # the hand off, by the declared name
    self.assert_no_overlap_among_tracked()            # never delete
```

Mechanics: `track()` every meaningful element; `assert_within_safe_frame`
before animating in; theme tokens (`FONT_SIZE_*`, `SPACING_*`, `COLOR_*`)
and composition slots (`COL_LEFT_X`, `ROW_Y[...]`) over literal numbers.
Delete each `#  [ ]` note as you satisfy it; keep the `carried in` /
`hand off` / `budget` lines — they are what the next edit reads. Full
rules: `references/framework-rules.md`.

## 5. Check the math before you render it

```bash
python -m open_manim_slides.validate decks/<slug>.py
```

Runs every segment's construction and every mechanical check — safe
frame, overlap, centering, duplicate ids, illegible text morphs
(`Transform` between two sentences, which spends most of the play as
unreadable glyph soup), conflicting animations (two animations in one
`play()` driving the same mobject), text sitting on a decorative
element's strokes, and R2/R4 — **without rendering a frame**. Two
seconds instead of ten, and it reports *every* broken segment at once
where a render aborts at the first.

`ConflictingAnimations` is worth fixing the moment it appears: manim can
**deadlock** on it, hanging the render with no traceback and no partial
output, which reads as a slow render rather than a bug.

`IllegibleTextMorph` is the one finding here that no amount of looking at
final frames would catch, because the final frame is the one moment
nothing is moving. Fix it with `FadeTransform` (re-tracking the id — it
replaces the mobject rather than mutating it) or `TransformMatchingTex`
for `MathTex`; see `references/motion-recipes.md`.

`TextOnDecorative` is the pair no other check spans: the overlap check
drops `decorative` ids from *both* sides, so a caption crossing an axis's
tick numbers passes everything and is still wrong on screen. It tests the
decorative element's actual strokes, not its bounding box, so a label
docked just outside a figure is fine — what it reports is text landing on
ink. Move the text, or shrink the figure; do not un-mark the decorative.

`NoChangeAnimation` and `UnperformedAction` are R2 and R4, counted rather
than self-graded — R2 reads `AUDIENCE` for the per-audience floor, and R4
fires when on-screen prose promises an action and nothing but text is
animated. Both are floors, not the whole rule: passing them does not mean
the change carries the idea, which is still yours to judge.

**Fix everything it lists, re-run until it prints `layout OK`, and only
then render.** Rendering to discover a placement error is the slowest
possible way to do arithmetic: the failures are all "this brace overhangs
the edge" and "these two boxes land on each other", and finding five of
them one render at a time is most of a wasted half hour.

Failures marked `likely a cascade` come from state an earlier failing
segment never set, or from an element it left in a bad place — fix the
first one and re-run before touching them.

## 6. Render and look at what you made

Iterate at low quality; full quality only once the deck passes review:

One command block, not three round-trips — and keep the render quiet, it
prints a progress bar per animation that buries anything useful:

```bash
manim render -ql decks/<slug>.py <ClassName> 2>&1 | tail -3
python -m open_manim_slides.frames <ClassName> > /dev/null
python -m open_manim_slides.blankspace <ClassName>
```

`frames` writes, per segment, a final-frame PNG and a 6-tile contact
sheet under `media/review/<ClassName>/`. **Read every image — all of
them in one batch, not one per turn.** `blankspace` measures those same
stills and prints per-segment fill percentages plus any region **no
segment ever uses** — do not eyeball emptiness, read its numbers.

For each segment fill this table — closed answers only:

| # | Q1 eye lands on subject? | Q2 fill % (from blankspace) | Q3 elements touching? | Q4 words on screen | Q5 element restating another? | Q6 diff vs previous final frame (≤ 10 words) | Q7 every tile of the contact sheet legible? |

- Q1: where does your eye land first — is it the segment's subject?
- Q2: copy the segment's fill % from `blankspace`. It also names that
  segment's largest empty block; note it if ≥ 25%.
- Q3: name the touching pair (or "no").
- Q4: count words.
- Q5: name the redundant pair — caption restating the equation, label
  restating the heading (or "no").
- Q6: put this final frame beside the previous segment's. What changed?
  **If the answer is "the heading and one new element", the segment
  built on nothing — that's a design failure, not a polish issue.**
- Q7: **the final frame is the one moment nothing is moving** — Q1-Q6
  cannot see a defect that only exists mid-play. Open `seg-NN-sheet.png`
  and read all six tiles. Name any tile where text is unreadable, or
  answer "all legible".
  The usual culprit: `Transform(old_text, new_text)` interpolates glyph
  *outlines* between two strings that have no letter correspondence, so
  a heading or caption swap spends most of a second as garbage
  (`Ch⊃∂s A T'w? 3f£!vG`). Text→text swaps want `FadeTransform`; see
  `motion-recipes.md`. Ignore `Write`'s partial strokes — that is the
  animation working.

R2 and R4 are already counted by `validate` (step 5), so there is no
grep to run here — what is left for you is the part no count reaches:
whether the change *carries the idea*, rather than merely existing.

**Fix a segment only if**: Q1 no · Q2 fill < 20% · Q3 names a pair ·
Q4 > 25 (18 middle-school) · Q5 names a pair · Q6 is heading-only ·
Q7 names a tile.
**Nothing else. "Could be prettier" is not a reason.**

**Then fix the deck-level layout if** `blankspace` reports a dead region
≥ 15% of the frame. That space is not reserved for anything — every
segment ran and none of them reached it. The fix is structural (enlarge
the figure, rebalance the columns, move the running elements into it),
never a nudge: a deck whose subject occupies half the frame reads as a
diagram with slides built around it. Re-run `blankspace` after fixing and
confirm the number moved.

**Batch the fixes.** Collect every issue the round found, then apply them
together — one edit per segment, in one turn — and re-validate and
re-render once. Fixing one thing, re-rendering, fixing the next is the
same trap step 5 exists to avoid, just later in the workflow.

One full round; then re-review only the segments you edited. If the
first round flags more than half the segments, stop — the outline is
wrong; report which segments failed and why, and ask the user whether to
restructure.

## 7. Finish

Final full-quality render and confirm it completes without errors:

```bash
manim render decks/<slug>.py <ClassName> 2>&1 | tail -3
```

Tell the user it's ready, including your review table and what you fixed.

## The shape of a good run

Steps 1-7 done well is roughly a dozen turns, most of them batched. It is
worth knowing what makes a run balloon to four times that, because none
of it is the renderer — a full render of an 8-segment deck is ~9 seconds
at `-ql`, and a whole run's machine time is under three minutes:

- **Rendering to find layout errors.** Step 5 exists for this. Five
  placement mistakes found one render at a time is five cycles for
  arithmetic that validates in two seconds, all at once.
- **Unbatched edits.** Adding an import in one turn and using it in the
  next; fixing one review finding, re-rendering, fixing the next. Group
  them.
- **Dumping raw tool output.** `tail -100` on a render captures a hundred
  lines of progress bars; `tail -3` carries the same signal.
- **Re-reading files you just wrote.** Keep track of what you authored
  instead of re-reading it to find an edit anchor.
