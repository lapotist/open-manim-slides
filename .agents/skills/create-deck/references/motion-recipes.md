# Motion recipes (verified against manim 0.20.1)

Every snippet here was construct-checked headlessly and rendered in one
real deck before being written down. Use these instead of guessing API —
the decks that render clean on the first try are the ones that didn't
improvise the tricky calls.

## How motion interacts with this framework (read first)

- **The checks can't see motion.** `assert_no_overlap_among_tracked()`
  and `assert_within_safe_frame()` run at construction time, at the end
  of a segment — they sample the final layout only. **Transient overlap
  during an animation is free**: a dot may sweep straight across a label
  mid-play; only where things *land* is checked.
- **Never `track()` or `assert_within_safe_frame()` a `ValueTracker`.**
  It stores its number in its coordinates, so `ValueTracker(9.0)` has a
  bounding box at x = 9.0 and "extends outside the safe frame". It is an
  invisible control object, not on-screen content.
- **`clear_updaters()` before fading out** any `always_redraw` /
  `TracedPath` mobject — otherwise the updater rebuilds it at full
  opacity every frame and the `FadeOut` appears to do nothing.
- **`Transform(a, b)` mutates `a`**: `a` stays on screen wearing `b`'s
  appearance, and `track()` still points at `a`. But
  **`TransformMatchingTex(a, b)` removes `a` and adds `b`** — re-track
  `b` under a new id after it (see the exemplar).
- An element that should be gone must actually leave:
  `self.play(FadeOut(mobj))` routes through `Scene.remove`, which is how
  the framework knows to stop expecting it. Anything merely covered
  keeps participating in every later overlap check.

## Entrances: which animation for which mobject

`Write` is for text only. `self.play(Write(some_polygon))` is a bug.

| mobject | entrance |
|---|---|
| `Text` / `Tex` / `MathTex` | `Write` |
| outline shapes (`Circle`, `Line`, `Axes`, `Brace`) | `Create` |
| filled shapes (`fill_opacity > 0`) | `DrawBorderThenFill` |
| `Arrow` | `GrowArrow` |
| `Dot`, small marks | `FadeIn(m, shift=UP * 0.2)` or `GrowFromCenter` |

## 1. `.animate` — move/scale/recolor what's already there

```python
self.play(fig.animate.scale(0.6).to_edge(LEFT, buff=SPACING_MD))
self.play(dot.animate(path_arc=PI / 2).move_to(target))  # curved path
```

Gotcha: `.animate.rotate(angle)` interpolates start→end points linearly,
so the shape shrinks through the turn. For a visible rotation use
`Rotate(mobj, angle, about_point=...)`.

## 2. `ValueTracker` + `always_redraw` — a driven diagram

```python
x_val = ValueTracker(0.5)
dot = always_redraw(
    lambda: Dot(axes.c2p(x_val.get_value(), f(x_val.get_value())), color=COLOR_ACCENT_2)
)
self.play(FadeIn(dot))
self.play(x_val.animate.set_value(4.5), run_time=1.5)
dot.clear_updaters()          # REQUIRED before FadeOut — see above
self.play(FadeOut(dot))
```

## 3. A dot travelling a path, leaving a trail

```python
runner = Dot(path.point_from_proportion(0))
trail = TracedPath(runner.get_center, stroke_color=COLOR_ACCENT_2)
self.add(trail)
self.play(MoveAlongPath(runner, path), run_time=1.5)
trail.clear_updaters()        # same updater gotcha as always_redraw
```

## 4. `Axes` — plot and position ON the axes

```python
axes = Axes(x_range=[0, 5, 1], y_range=[0, 4, 1], x_length=6, y_length=3.5)
graph = axes.plot(lambda x: 0.5 * x + 1, x_range=[0, 5], color=COLOR_ACCENT)
point = Dot(axes.c2p(2, 2))   # ALWAYS c2p(), never raw scene coordinates
```

Track axes as `decorative=True` (everything plotted on them sits inside
their bounding box by construction).

## 5. Equation steps — multi-arg `MathTex` for stable coloring

```python
eq = MathTex("a^2", "+", "b^2", "=", "c^2")   # one arg per term
eq[0].set_color(COLOR_ACCENT)                  # eq[0] is exactly "a^2"
eq2 = MathTex("a^2", "+", "b^2", "=", "25")
self.play(TransformMatchingTex(eq, eq2))       # matching parts glide
self.track(eq2, id="eq-after")                 # eq was REPLACED — re-track
```

Gotcha: single-string `MathTex(r"a^2+b^2")[0][1:]` is glyph-indexed and
unpredictable; per-term args make indexing mean something.

Gotcha: **never chain two of these in one segment.** Plays auto-advance,
so the middle line of `eq1 → eq2 → eq3` is on screen for about a second
— nobody reads it. One derivation step per segment (R5): the presenter's
click is what advances the algebra.

## 6. `Brace` — measure or annotate without collisions

```python
brace = self.track(Brace(figure, DOWN, buff=SPACING_XS), id="side-brace", decorative=True)
label = self.track(brace.get_tex("x + 3"), id="side-label", decorative=True)
self.play(Create(brace), Write(label))
```

Positions itself outside the figure — prefer it over hand-placing a
label near an edge.

## 7. Highlighting a sub-expression

```python
box = self.track(SurroundingRectangle(eq[4], buff=0.1), id="box", decorative=True)
self.play(Create(box))
```

## 8. Arriving together — one beat, not five

```python
self.play(Write(head), Create(figure))                       # together
self.play(LaggedStart(*(FadeIn(d) for d in dots), lag_ratio=0.2))  # staggered
```

`Succession(...)` chains animations inside one `self.play` when order
matters within a single beat.

## 9. Emphasis — allowed, but it is NOT change

`Indicate`, `Flash`, `Circumscribe`, `Wiggle`, `ShowPassingFlash` draw
the eye without altering anything. Use them sparingly — and know that
**they do not satisfy the something-must-change rule (R2)**. A segment
whose only non-entrance animation is an `Indicate` is still a static
slide with a twitch.

## Out of scope

Anything needing `MovingCameraScene` or `ThreeDScene` — decks subclass
the framework's `Slide`, which is neither.
