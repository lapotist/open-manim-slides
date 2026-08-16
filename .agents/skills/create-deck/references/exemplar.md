# One segment at target quality

This is a real, rendered segment (asserts pass, frames verified). Study
the **moves**, marked `[move]`, not the shapes.

**The weak version already exists in this repo**: read
`decks/the_pythagorean_theorem.py`, `segment_the_algebra` — a heading, a
three-stage `MathTex` `Transform` chain, nothing else on screen. That is
exactly the pattern this replaces: the algebra happens, but nothing the
algebra *talks about* is visible, so nothing meaningful can move.

> **This example is about areas. If your deck is not about areas, copy
> its structure and none of its objects. If your segment has a `Square`
> in it because this example did, delete it.**

## The segment

Topic: completing the square. The previous segment ended with a heading
(`self.head`), the expression `x² + 6x` colored term-by-term
(`self.expr`), and two literal areas: a blue x-by-x square
(`self.x_square`) and a yellow x-by-6 strip (`self.strip`).

```python
def segment_complete_the_square(self) -> None:
    """Rearrange the strip into an L; one small corner is missing."""
    # [carry in, make room] Nothing is cleared. The heading dims because
    # its job is done; the square slides toward where the finished
    # picture will be centered (it grows right and down, so start
    # up-left of true center by half the growth).
    self.play(
        self.head.animate.set_opacity(0.3),
        self.x_square.animate.shift(RIGHT * 0.6 + DOWN * 0.2),
    )

    # [split one thing into the parts the algebra names] 6x becomes
    # 3x + 3x. The strip fades out (FadeOut routes through Scene.remove,
    # so the framework stops tracking it) while two halves fade in over
    # its footprint.
    half_a = self.track(
        Rectangle(width=H, height=X, color=COLOR_ACCENT_2, fill_color=COLOR_ACCENT_2, fill_opacity=0.5),
        id="half-a",
    )
    half_b = self.track(
        Rectangle(width=H, height=X, color=COLOR_ACCENT_2, fill_color=COLOR_ACCENT_2, fill_opacity=0.5),
        id="half-b",
    )
    VGroup(half_a, half_b).arrange(RIGHT, buff=SPACING_XS).move_to(self.strip)
    self.play(FadeOut(self.strip), FadeIn(half_a), FadeIn(half_b))

    # [the rearrangement that IS the claim] One half docks to the
    # square's right edge, the other rotates under its bottom edge.
    # This motion is the mathematical content — delete it and the
    # segment says less, not just looks duller.
    gap = SPACING_XS
    right_target = self.x_square.get_right() + RIGHT * (gap + H / 2)
    below_target = self.x_square.get_bottom() + DOWN * (gap + H / 2)
    self.play(
        half_a.animate.move_to(right_target),
        half_b.animate.rotate(PI / 2).move_to(below_target),
    )

    # [show the gap the formula fills] The L doesn't close: a muted
    # 3-by-3 corner is missing — that IS the "+ 9". The equation
    # transforms in the same play, and the new term wears the corner's
    # color, so symbol and picture are the same object.
    corner = self.track(
        Square(side_length=H, color=COLOR_MUTED, fill_color=COLOR_MUTED, fill_opacity=0.25),
        id="missing-corner",
    )
    corner.move_to([half_a.get_center()[0], half_b.get_center()[1], 0])
    new_expr = MathTex("x^2", "+", "6x", "+", "9", "=", "(x+3)^2", font_size=44)
    new_expr[0].set_color(COLOR_ACCENT)     # matches the blue square
    new_expr[2].set_color(COLOR_ACCENT_2)   # matches the yellow halves
    new_expr[4].set_color(COLOR_MUTED)      # matches the missing corner
    new_expr.move_to(self.expr)
    assert_within_safe_frame(new_expr)
    self.play(FadeIn(corner), TransformMatchingTex(self.expr, new_expr))
    self.track(new_expr, id="expr-completed")

    # [name the result] A brace measures the finished side. Brace and
    # label hug the figure by construction — the only decorative=True
    # in the segment.
    completed = VGroup(self.x_square, half_a, half_b, corner)
    brace = self.track(Brace(completed, DOWN, buff=SPACING_XS), id="side-brace", decorative=True)
    side_label = self.track(brace.get_tex("x + 3"), id="side-label", decorative=True)
    assert_within_safe_frame(VGroup(completed, brace, side_label))
    self.play(Create(brace), Write(side_label))

    self.assert_no_overlap_among_tracked()
```

## Why this is the target (keyed to the rules)

1. **R1** — nothing is cleared; every object either came from the
   previous segment or is a named part of one that did.
2. **R2** — five plays, four of them change something already on screen
   (`set_opacity`, `shift`, `move_to`, `rotate`, `TransformMatchingTex`).
   The only pure entrances are the halves and the corner, and each
   arrives *as* something else changes.
3. **R3** — the equation never stands alone: each term is the color of
   the shape it counts.
4. **R4** — the caption-free segment makes no written claims it doesn't
   perform. The docstring's "rearrange" happens on screen.
5. **R5** — 5 plays total; nothing arrives on an empty beat.
6. **R6** — blue = x², yellow = 6x, gray = the missing 9, in both the
   picture and the symbols. No color is decoration.
7. **decorative=True** appears exactly twice, both for a brace/label
   pair that hugs the figure by construction — never for the subject.

## Same moves, other subjects

The moves transfer; the shapes don't.

| move | a geometry deck | an algebra deck | a science deck |
|---|---|---|---|
| carry in, make room | shrink last segment's triangle toward the left edge | dim the solved equation, slide it to the top | scale the labelled diagram into a corner |
| split into named parts | cut the square along its diagonal into two triangles | break `6x` into `3x + 3x` | separate "rainfall" into runoff and groundwater arrows |
| the rearrangement that is the claim | pinwheel four copies inside a frame | dock the halves onto two sides of the square | route the arrows into a closed loop |
| show the gap | the uncovered tilted square in the middle | the missing 3-by-3 corner | the evaporation arrow that must close the loop |
| name the result | brace the side, label it `c` | brace the side, label it `x + 3` | label the loop "the water cycle" |
