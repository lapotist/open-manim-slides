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

## The seven rules

Every segment is written against these. Each has a mechanical check —
run the checks on your finished deck, don't trust your intent.

- **R1 — Carry something forward.** At most 2 segments in the whole deck
  may start from a cleared frame; every other segment begins by
  *changing* what's already there (shrink and move the previous figure
  aside, dim a heading, transform an equation into its next form).
  Check: count the segment-opening `FadeOut`s ≤ 2.
- **R2 — Something must change, not just appear.** Each segment needs at
  least one `self.play()` that alters a mobject already on screen.
  Counts: `Transform`/`ReplacementTransform`/`TransformMatchingTex`,
  `.animate`, `MoveAlongPath`, `Rotate`, `ValueTracker` +
  `.animate.set_value`. Doesn't count: entrances (`Write`, `Create`,
  `FadeIn`, `GrowArrow`, ...), the clearing `FadeOut`, or emphasis
  (`Indicate`, `Flash`, `Circumscribe`, `Wiggle`). The change must carry
  the idea: if deleting it would make the segment say *less* — not just
  look duller — it counts.
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
  sentence — it's a promise the slide doesn't keep.
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
`framework-rules.md`).

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

## 2. Plan before code — the segment table

Read `references/exemplar.md` now. Then produce this table, one row per
segment, and show it to the user with the outline:

| # | segment | the one thing it shows | carried in from previous | the change animation (R2) | the non-text mobject (R3) |
|---|---|---|---|---|---|

Every cell filled, before any code. If "carried in" is empty for more
than 2 rows, the deck is a slideshow — redesign the outline so segments
build on each other. If a "change animation" cell names `Transform`,
`ValueTracker`, `MoveAlongPath`, `Axes`, or `Brace`, read
`references/motion-recipes.md` before writing that segment.

## 3. Scaffold (deterministic, not freehand)

```bash
python -c "
from pathlib import Path
from open_manim_slides.scaffold import new_deck
path = new_deck(title='<title>', segments=[<segment names>], out_dir=Path('decks'), audience='<audience>')
print(path)
"
```

Writes `decks/<slug>.py`: one `segment_<name>` method per row of your
table, each ending in `self.assert_no_overlap_among_tracked()` (not
optional), each carrying a checklist comment you delete as you satisfy
it.

## 4. Fill in each segment

The shape of a good segment (see the exemplar for a real one):

```python
def segment_<name>(self) -> None:
    """<the one thing this segment shows>"""
    # carried in: self.figure, self.eq   (R1 — or nothing, max twice per deck)
    self.play(self.figure.animate.scale(0.6).to_edge(LEFT, buff=SPACING_MD))

    head = heading(self, "<3-5 words>")               # 36pt, top, tracked
    part = self.track(Polygon(...), id="<kebab-id>")
    assert_within_safe_frame(VGroup(head, part))
    self.play(Write(head), Create(part))              # R5: arrive together

    self.play(Transform(part, part_after))            # R2: the change that IS the idea

    self.figure = part                                # hand off to the next segment
    self.assert_no_overlap_among_tracked()            # never delete
```

Mechanics: `track()` every meaningful element; `assert_within_safe_frame`
before animating in; theme tokens (`FONT_SIZE_*`, `SPACING_*`,
`COLOR_*`) over literal numbers. Full rules: `references/framework-rules.md`.

## 5. Render and look at what you made

Iterate at low quality; full quality only once the deck passes review:

```bash
manim render -ql decks/<slug>.py <ClassName>
python -m open_manim_slides.frames <ClassName>
```

The second command writes, per segment, a final-frame PNG and a 6-tile
contact sheet under `media/review/<ClassName>/`. **Read every image.**
For each segment fill this table — closed answers only:

| # | Q1 eye lands on subject? | Q2 empty region ≥ ⅓ frame? | Q3 elements touching? | Q4 words on screen | Q5 element restating another? | Q6 diff vs previous final frame (≤ 10 words) |

- Q1: where does your eye land first — is it the segment's subject?
- Q2: name the empty region (or "none").
- Q3: name the touching pair (or "no").
- Q4: count words.
- Q5: name the redundant pair — caption restating the equation, label
  restating the heading (or "no").
- Q6: put this final frame beside the previous segment's. What changed?
  **If the answer is "the heading and one new element", the segment
  built on nothing — that's a design failure, not a polish issue.**

Then two source greps per segment, because frames can't show them: the
R2 animation list, and the R4 verb list against every on-screen string.

**Fix a segment only if**: Q1 no · Q2 names a region · Q3 names a pair ·
Q4 > 25 (18 middle-school) · Q5 names a pair · Q6 is heading-only · R2
grep empty · R4 grep has an unperformed verb. **Nothing else. "Could be
prettier" is not a reason.**

One full round; then re-review only the segments you edited. If the
first round flags more than half the segments, stop — the outline is
wrong; report which segments failed and why, and ask the user whether to
restructure.

## 6. Finish

Final full-quality render and confirm it completes without errors:

```bash
manim render decks/<slug>.py <ClassName>
```

Tell the user it's ready, including your review table and what you fixed.
