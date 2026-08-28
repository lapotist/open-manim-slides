# Framework rules — tracking, checks, and templates

Read this when an `assert_*` raises, before changing any code — the fix
is usually placement or a flag, not deleting the check.

## `track()` — what and how

Wrap every meaningful on-screen element (titles, diagrams, labels,
anything a future edit-request might reference) with
`self.track(mobj, id="...")` — short, descriptive, kebab-case ids.
Duplicate id **within one segment** raises (almost always a copy-paste
mistake); reuse **across segments** is expected and means "this element
persists or reappears". The ids feed an ID-addressable manifest
(`<DeckClass>.manifest.json`) used by the review tooling.

## `assert_within_safe_frame(mobj)`

Call on placed elements (or a `VGroup` of them) before animating them
in: raises at construction time if anything extends past the 0.5-unit
frame margin, with the offending coordinates in the message. Check
*groups* where the combined extent matters — two halves can each fit
while the pair doesn't.

## `assert_no_overlap_among_tracked()`

The scaffolded last line of every segment. Checks every currently
active, non-decorative tracked element pairwise; raises with both
bounding boxes on collision. Two things about it are silent, which is
why they're rules:

- **Never delete the call.** Nothing raises if you do; the check just
  stops existing.
- **Never silence it with `decorative=True`** — see below.

If it fires on genuinely misplaced content, move the content. If it
fires on a backdrop/containment pair (below), flag the backdrop.

### `decorative=True` — narrow, exact criteria

The overlap check compares axis-aligned bounding boxes, which are a
structurally poor proxy for curved or diagonal shapes: any point on or
inside a circle is inside the circle's own bbox, so a circle checked
against its own radius line false-positives at every angle.
`decorative=True` keeps such an element in the manifest but out of the
overlap check. It is **only** for:

- `Axes` / `NumberPlane` (plotted content sits inside them by design);
- a `SurroundingRectangle`, `Brace`, `Angle`, or `RightAngle` that hugs
  another element by construction;
- a `Line` / `Arrow` that starts or ends *on* another tracked element;
- a `Circle` or guide curve that other tracked elements sit on or inside;
- a shape or region fill that tiles *flush* against another element by
  construction — a square drawn on a triangle's hypotenuse, the
  uncovered region of a dissection proof. The placement is geometrically
  exact; a bounding box simply cannot represent diagonal adjacency.

It is **not** for "this figure keeps tripping the check". If you're
marking something decorative to silence a collision, move it instead.
**Never mark a segment's subject decorative** — a decorative subject
means the slide's main content is exempt from the one check that guards
it. (The old decks did exactly this and shipped unchecked diagrams.)

The flag is narrower than it used to be. `validate` reports
`TextOnDecorative` when a text element lands on a decorative element's
actual **strokes** — the recurring failure that no check's scope spanned,
since the overlap check drops decorative ids from both sides. Bounding
boxes are untouched by it, so everything above still holds: a label
docked outside a figure, a curve inside its own axes, and a brace hugging
a side all stay clear. What it catches is the caption crossing an axis's
tick numbers, and the `=` sign touching a box drawn around the result.

### Composite figures: one designed unit, one id

Parts that *intentionally* touch — a label centered inside its square, a
figure whose pieces tile flush against each other — should be built as
one `VGroup` and tracked under **one id**. The pairwise check runs
between ids, so deliberate internal containment stops false-positiving
while the composite as a whole is still checked against everything
else. This keeps the subject checked (unlike `decorative=True`, which
exempts it entirely).

## Removal — off screen means actually removed

`self.play(FadeOut(mobj))` routes through `Scene.remove`, which tells
the framework the element left. An element merely *covered* by newer
content keeps participating in every later segment's overlap check —
correct for anything still visible, a false-positive factory for
anything that should have been removed. The same applies in reverse:
`TransformMatchingTex(a, b)` removes `a` and adds an untracked `b` —
re-track `b` or it disappears from the manifest and the checks.

**Fade the tracked mobject itself, not a re-wrapping of its children.**
If you tracked `group = self.track(VGroup(*parts), id=...)`, then
`FadeOut(VGroup(*parts))` — a *different* wrapper — takes the parts off
screen but the framework still considers `group` active, and its stale
bounding box will collide with whatever comes next. Keep a reference to
the tracked wrapper and fade *that*.

## `assert_reasonably_centered_among_tracked()`

Opt-in, for slides where centering is the point (title, summary, boxed
result): raises if the *combined* bounding box of everything active
sits noticeably off the frame center. Build such a slide as one
`VGroup`, `group.move_to(ORIGIN)`, then play the pieces. Don't call it
on diagram-plus-heading layouts — those naturally sit off-center.
Unlike the overlap check it does **not** skip decorative elements: a
backdrop still occupies visual space.

## Theme templates and tokens

Prefer tokens over numbers, templates over hand-rolled patterns:

- `heading(self, "...", id="heading")` — per-segment heading at
  `FONT_SIZE_HEADING`, pinned near the top with real slack, tracked and
  safe-frame-checked. **Not** `title_slide(...).to_edge(UP)` — that's
  the oversized-heading-on-the-margin look the old decks shipped.
- `title_slide(self, "...", id="title")` — the deck's opening title
  only.
- `two_column(left, right)` — side-by-side halves, safe-frame-checked
  as a pair.
- `diagram_with_caption(self, diagram, "...", id="...")` — one
  explanatory line under a figure.
- Font sizes: `FONT_SIZE_TITLE/HEADING/BODY/CAPTION`. Spacing for every
  `buff=`: `SPACING_XS/SM/MD/LG/XL`. Colors: `COLOR_TEXT/MUTED/ACCENT/
  ACCENT_2/BACKGROUND`. A literal number where a token exists is a
  smell.

## Segment structure

One file per deck; each `self.next_slide()` segment is its own
`segment_<name>` method called in order from `construct()`. Segments
share state through `self.<attr>` handoffs (a persisting figure, a
carried equation) — set them explicitly at the end of the segment that
creates them; the scaffolder threads nothing implicitly.
