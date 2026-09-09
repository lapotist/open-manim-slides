# Validation corpus

**These are test fixtures, not example decks. Do not read them as a style
reference, and do not copy their composition.** Half of them are wrong on
purpose. The clean half is deliberately heterogeneous — a driven diagram, a
dissection, a centred summary, a boxed result, an equation step — so that
nothing here reads as a house style. `create-deck`'s test-run rule covers
`decks/`; this directory is not that, and is not an exception to it.

## What it is for

Two questions, neither answerable without a corpus:

1. **Can the check fail?** A check that never fires proves nothing. Every
   gated finding has a fixture here that must produce it. The same standard
   the browser test was held to in session thirteen.
2. **Does the check misfire?** This is the expensive question. Every new
   content rule narrows what an agent dares to write, and a rule that
   reports correct work teaches the author to ignore the whole report. The
   clean half exists to be run against any *proposed* check before it
   ships: if it fires on one of these, it is not ready.

Session eighteen's tracker bug is the case in point. R2 was measured against
eleven decks that already existed, and it rejected `motion-recipes.md`'s own
recipe 2 — because the recipes a rule *invites* are exactly what a corpus of
past work cannot contain. `driven_diagram.py` is that recipe, frozen.

## Adding to it

A fixture should be small (two or three segments), contain one idea, and say
in its docstring which finding it exists to pin and why that finding is hard
to see any other way. Register it in `tests/test_corpus.py` with the exact
error types it must produce — `[]` for a clean one.

Prefer freezing a deck an agent actually generated, warts included, over
authoring a tidy one. Ugly is fine here. Wrong is useful.
