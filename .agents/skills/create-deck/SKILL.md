---
name: create-deck
description: Scaffold a new Manim Slides deck (one file, one segment function per slide) and fill in its content from a natural-language description. Use when the user asks to create, start, or generate a new deck, presentation, or lesson.
---

# create-deck

Scaffolds a new deck file using the framework's deterministic generator,
then fills in each segment's content.

## 1. Gather the deck's shape

Ask the user (or infer from their request) for:

- **Title** — short, human-readable.
- **Segments** — a rough ordered outline of the deck's slides/beats (e.g.
  `["intro", "the problem", "the idea", "example", "summary"]`). If the user
  only gave a topic, propose a 4-6 segment outline and confirm before
  scaffolding.

## 2. Scaffold the file (deterministic, not freehand)

Do **not** hand-write the deck file's structure. Call the scaffolder so the
file's shape (imports, class, one function per segment, `next_slide()`
calls) is generated consistently and matches what the test suite checks:

```bash
python -c "
from pathlib import Path
from open_manim_slides.scaffold import new_deck
path = new_deck(title='<title>', segments=[<segment names>], out_dir=Path('decks'))
print(path)
"
```

This writes `decks/<slug>.py` with one `segment_<name>` function per
segment, each currently a `# TODO` stub, called in order from
`construct()`.

## 3. Fill in each segment's content

For each `segment_<name>` method, replace the `# TODO` stub with real
Manim code for that beat of the deck. Rules:

- Every meaningful on-screen element (titles, key diagrams, anything a
  future edit-request might need to reference) should be wrapped with
  `self.track(mobj, id="...")` — pick a short, descriptive, kebab-case id.
  Don't invent ids for incidental/decorative elements.
- Wrap placed elements with `assert_within_safe_frame(mobj)` (imported at
  the top of the generated file already) before animating them in, so
  margin/overlap mistakes fail loudly instead of silently rendering wrong.
- Keep one segment's content self-contained where possible; if an element
  must persist from an earlier segment, that's fine (Manim keeps mobjects
  on screen across `next_slide()` by default) — just don't assume the
  scaffolder threads any implicit state between segment functions.

## 4. Verify

Render the deck and confirm it produces output with no errors before
telling the user it's ready:

```bash
manim render decks/<slug>.py <ClassName>
```
