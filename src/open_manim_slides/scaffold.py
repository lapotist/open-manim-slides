"""Deterministic deck scaffolder.

Produces the mechanical, boilerplate part of a new deck file (one file per
deck, each segment as its own top-level function -- the resolved authoring-
unit convention). Content within each segment stays for the agent to fill
in; this module only owns file structure, so it can be tested independently
of any LLM-authored content.

Why it emits more than function stubs
-------------------------------------
Transcript evidence from six real builds: `validate.py` made each
check cheaper (~9s render -> ~2s validate) without reducing how *often* the
agent checked -- one build ran `validate` 15 times across 54 edits, in
`AUTHOR AUTHOR VALIDATE AUTHOR VALIDATE` cycles. Round-trip count, not
round-trip cost, is what a build spends its time on. The two failure
classes that drove those cycles were both decided before any check could
run:

* **State handoff.** Ten-plus `AttributeError: object has no attribute
  'figure' / 'roof_fig' / 'fan' / 'span'` -- a segment reading a name an
  earlier segment never set, surfacing as a cascade several segments away
  from the typo. The scaffolder used to thread nothing between segments, so
  every handoff name was invented twice, independently, from memory.
* **Placement.** Twelve overlap / safe-frame failures at literal
  coordinates, because each segment invented its own positions.

Both are answered by writing the answer into the file *before* the agent
starts: declared handoff names (as annotations, which document the name
without creating an attribute -- a missing handoff must still fail loudly,
just locally and by name), and a composition block of named slots that are
inside the safe frame by construction. The agent then positions against
`COL_LEFT_X` instead of guessing `-3.5`, and writes `self.roof_fig` in both
places because the name is already in front of it.
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

#: Manim's default frame, and the safe area inside `layout.py`'s 0.5 margin.
FRAME_WIDTH = 14.222222
FRAME_HEIGHT = 8.0
SAFE_MARGIN = 0.5

#: Per-audience ceilings, mirrored from create-deck's audience table. They
#: are emitted into each segment stub because a limit recalled from a table
#: read thirty turns earlier is not a limit.
AUDIENCE_BUDGETS = {
    "middle-school": {"plays": 4, "words": 18},
    "high-school": {"plays": 6, "words": 25},
}


@dataclass
class Segment:
    """One `next_slide()` segment, as planned before any code is written.

    The fields are the create-deck plan table's own columns, so planning
    produces the authoring context instead of prose the agent must
    remember.
    """

    name: str
    shows: str = ""
    #: `self.<attr>` names this segment reads, set by an earlier segment.
    carries: list[str] = field(default_factory=list)
    #: `self.<attr>` names this segment must set before returning.
    produces: list[str] = field(default_factory=list)


def _coerce(raw: object) -> Segment:
    if isinstance(raw, Segment):
        return raw
    if isinstance(raw, str):
        return Segment(name=raw)
    if isinstance(raw, dict):
        return Segment(
            name=str(raw.get("name", "")),
            shows=str(raw.get("shows", "")),
            carries=list(raw.get("carries", []) or []),
            produces=list(raw.get("produces", []) or []),
        )
    raise TypeError(f"Cannot read a segment from {type(raw).__name__}: {raw!r}")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "segment"


def _class_name(title: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", title).split()
    return "".join(word.capitalize() for word in words) or "Deck"


#: Where `theme.heading()` actually puts a one-line 36pt heading, and the
#: first text row beneath it. Both are emitted into the deck so a segment
#: can reserve the band instead of measuring it again.
HEAD_Y = 3.15
ROW_Y = (1.9, 0.9, -0.1, -1.1, -2.1)


def _slot(name: str, value: object, comment: str) -> str:
    """One composition constant, with its comment column aligned.

    Aligned by width rather than by hand-counted spaces: a negative slot
    value is one character wider than its positive twin, which used to push
    `COL_LEFT_X`'s comment out of line with every other row.
    """
    return f"{name} = {value!r}".ljust(38) + f"# {comment}"


def _composition_block() -> list[str]:
    """Named slots for the default two-column composition.

    Derived from the real frame rather than chosen by eye, so anything
    placed at these coordinates is inside the safe frame before
    `assert_within_safe_frame` is ever called.
    """
    safe_x = round(FRAME_WIDTH / 2 - SAFE_MARGIN, 2)
    safe_y = round(FRAME_HEIGHT / 2 - SAFE_MARGIN, 2)
    gutter = 0.3
    # Floor, never round: at two decimal places a rounded half-width can
    # push the column's outer edge past the safe bound it was derived from
    # (6.61 -> half 3.155 -> 3.16 -> edge 6.62). These constants exist so
    # that placing against them cannot fail the safe-frame check.
    col_half = math.floor((safe_x - gutter) / 2 * 100) / 100
    col_centre = round(gutter + col_half, 2)
    return [
        "# --- Composition ------------------------------------------------",
        "# One composition, held for the whole deck. Position against these",
        "# names, never a fresh literal per segment: invented per-segment",
        "# coordinates are what the safe-frame and overlap failures in past",
        "# builds were made of. Deviate deliberately (a full-width title, a",
        "# centred summary) -- just not by accident.",
        _slot("SAFE_X", safe_x, "|x| any element must stay within"),
        _slot("SAFE_Y", safe_y, "|y| any element must stay within"),
        # Measured, not guessed: `heading()` pins the text's *top* at
        # frame_height/2 - (margin + SPACING_XS) = 3.35, so a one-line 36pt
        # heading centres at ~3.11-3.16 and its lowest descender lands near
        # 2.86. Anything else in this band collides with the heading, which
        # is why the reserved floor is stated rather than left to be
        # rediscovered per deck.
        _slot("HEAD_Y", HEAD_Y, "heading() centres here; keep everything else below 2.8"),
        _slot("COL_LEFT_X", -col_centre, "centre of the figure column"),
        _slot("COL_RIGHT_X", col_centre, "centre of the accumulating-text column"),
        _slot("COL_W", round(col_half * 2, 2), "size the figure to FILL this, not float in it"),
        _slot("ROW_Y", ROW_Y, "text rows, top-down"),
        "",
    ]


#: Names from `theme.py` every deck is told to prefer over literal numbers.
#: `two_column` is deliberately absent whenever a composition block is
#: emitted: it centres its halves on their own content width, so the column
#: centres move from segment to segment -- the exact per-segment placement
#: `COL_LEFT_X`/`COL_RIGHT_X` exist to replace. Offering both in one file
#: is offering two layout systems and no way to choose.
_THEME_NAMES = (
    "COLOR_ACCENT",
    "COLOR_ACCENT_2",
    "COLOR_MUTED",
    "COLOR_TEXT",
    "FONT_SIZE_BODY",
    "FONT_SIZE_CAPTION",
    "FONT_SIZE_HEADING",
    "FONT_SIZE_TITLE",
    "SPACING_LG",
    "SPACING_MD",
    "SPACING_SM",
    "SPACING_XL",
    "SPACING_XS",
    "diagram_with_caption",
    "heading",
    "title_slide",
)


#: The manim names the documented recipes and the exemplar actually use.
#: This is the `imports="curated"` list: shorter to read than a star import
#: and, unlike one, it tells the author what the house vocabulary is. It is
#: also guaranteed to be wrong for some deck, which is why it is not the
#: default -- see `_import_block`.
_CURATED_MANIM_NAMES = (
    # geometry
    "Arc", "Arrow", "Axes", "Brace", "Circle", "Dot", "Line", "NumberLine",
    "Polygon", "Rectangle", "Square", "SurroundingRectangle",
    # containers
    "Group", "Mobject", "VGroup",
    # text
    "MathTex", "Tex", "Text",
    # entrances
    "Create", "DrawBorderThenFill", "FadeIn", "GrowArrow", "GrowFromCenter", "Write",
    # change
    "FadeTransform", "MoveAlongPath", "Rotate", "Transform", "TransformMatchingTex",
    # removal, emphasis, sequencing
    "Circumscribe", "FadeOut", "Indicate", "LaggedStart", "Succession",
    # driven diagrams
    "TracedPath", "ValueTracker", "always_redraw",
    # constants
    "DEGREES", "DOWN", "LEFT", "ORIGIN", "PI", "RIGHT", "TAU", "UP",
)

#: Segment-count range per audience, from create-deck's audience table.
AUDIENCE_SEGMENTS = {"middle-school": (5, 6), "high-school": (7, 9)}

#: R1: how many segments may begin from a cleared frame.
MAX_CLEARED_STARTS = 2


#: What each mode decides for you. The line between them is deliberate:
#: **advanced relaxes the pre-commitment gates, never the correctness
#: checks.** Composition, the plan's cleared-start ceiling and the stub's
#: checklist are house style, and a deck may have a good reason to differ.
#: Safe frame, overlap, conflicting animations, illegible morphs, R2 and R4
#: catch defects, and no mode turns those off -- `validate` behaves
#: identically either way.
MODE_DEFAULTS: dict[str, dict[str, object]] = {
    "simple": {
        "composition": "two-column",
        "imports": "all",
        "brief_stub": False,
        "max_cleared_starts": MAX_CLEARED_STARTS,
    },
    "advanced": {
        "composition": "none",
        "imports": "curated",
        "brief_stub": True,
        "max_cleared_starts": None,
    },
}

#: Project-level defaults, so the *project owner* pins the mode once rather
#: than the agent choosing per run. That distinction is the whole design:
#: an option the agent re-decides every build is a new source of exactly the
#: inconsistency the composition block was added to remove.
SETTINGS_FILE = "open-manim-slides.json"


def project_settings(root: Path | str = ".") -> dict:
    """Read `open-manim-slides.json`, or an empty dict if there isn't one."""
    import json

    path = Path(root) / SETTINGS_FILE
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def resolve_options(
    mode: str | None = None,
    composition: str | None = None,
    imports: object = None,
    root: Path | str = ".",
) -> dict:
    """Settle mode/composition/imports: explicit argument, then project file, then mode default."""
    settings = project_settings(root)
    mode = mode or settings.get("mode") or "simple"
    if mode not in MODE_DEFAULTS:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {', '.join(MODE_DEFAULTS)}.")
    defaults = MODE_DEFAULTS[mode]
    return {
        "mode": mode,
        "composition": composition or settings.get("composition") or defaults["composition"],
        "imports": imports if imports is not None else settings.get("imports", defaults["imports"]),
        "brief_stub": defaults["brief_stub"],
        "max_cleared_starts": defaults["max_cleared_starts"],
    }


def _import_block(composition: str, imports: object = "all") -> list[str]:
    """Everything a segment is going to reach for, imported up front.

    Transcript evidence names "adding an import in one turn and using it in
    the next" as one of the things that makes a build balloon, and the file
    used to arrive with two imports for a workflow whose own examples use
    `np.array`, `heading()`, `Text`, `VGroup`, `Transform` and a colour
    token in the first ten lines. Every one of those was a round trip.

    `imports` picks how much of manim comes in, and the default is the
    star import for a reason worth stating: any curated list is complete
    for the deck it was written for and wrong for the next one, which puts
    the author back in the edit-then-use cycle *and* leaves them guessing
    whether extending the list is sanctioned. The star import is also
    manim's own documented convention -- every upstream tutorial opens with
    it -- and a deck file is a leaf artifact, not library code.

    The other settings exist because that reasoning is a default, not a
    law, and a project may weigh it differently:

    * `"all"` -- `from manim import *`. Fewest decisions while authoring.
    * `"curated"` -- an explicit list of the names the documented recipes
      use. Reads better and states the house vocabulary, at the cost of
      one edit the first time a deck needs something outside it. The
      `advanced` mode's default, where deviating is the point anyway.
    * `"minimal"` -- nothing but the framework. For someone who would
      rather write their own imports than delete ones they did not choose.
    * an explicit sequence of manim names -- exactly those.

    The theme tokens come in under every setting except `"minimal"`: they
    are the thing the skill tells the author to use instead of a literal
    number, and a token that has to be imported first is a token that gets
    replaced by the literal.
    """
    if imports == "minimal":
        # Pre-scaffolded-imports behaviour, kept as an explicit choice
        # rather than as something to fall back into by accident.
        return [
            "from manim import Mobject",
            "from open_manim_slides import Slide, assert_within_safe_frame",
            "",
        ]

    names = list(_THEME_NAMES)
    if composition != "two-column":
        # No fixed column centres in this file, so the content-width
        # template is the right tool rather than a competing one.
        names.append("two_column")

    if imports == "all":
        manim_lines = ["from manim import *  # noqa: F403 - manim's own documented convention"]
    else:
        chosen = _CURATED_MANIM_NAMES if imports == "curated" else tuple(imports)
        if not chosen:
            raise ValueError("imports= was given an empty list of manim names.")
        manim_lines = ["from manim import ("]
        manim_lines += [f"    {name}," for name in sorted(dict.fromkeys(chosen))]
        manim_lines += [")"]

    lines = ["import numpy as np", *manim_lines, ""]
    lines += [
        "from open_manim_slides import Slide, assert_within_safe_frame",
        "from open_manim_slides.theme import (",
    ]
    lines += [f"    {name}," for name in sorted(names)]
    lines += [")", ""]
    return lines


def _state_block(segments: list[Segment]) -> list[str]:
    """Declare every cross-segment attribute, in first-produced order.

    Annotations, not assignments: an annotation documents the name without
    creating the attribute, so a segment that forgets its handoff still
    raises `AttributeError` -- which is the point. What changes is that the
    name is written down once, where both the producing and the consuming
    segment can see it, instead of being re-invented from memory at both
    ends.
    """
    names: list[str] = []
    for segment in segments:
        for attr in segment.produces:
            if attr not in names:
                names.append(attr)
    for segment in segments:
        for attr in segment.carries:
            if attr not in names:
                names.append(attr)
    if not names:
        return []
    lines = [
        "    # State handed from one segment to the next. Declared here so",
        "    # the producing and consuming segments spell it the same way;",
        "    # annotations create no attribute, so a missed handoff still",
        "    # fails loudly -- by name, in the segment that forgot it.",
    ]
    lines += [f"    {name}: Mobject" for name in names]
    lines.append("")
    return lines


def _segment_stub(
    segment: Segment,
    fn_name: str,
    audience: str | None,
    brief: bool = False,
    cleared_ceiling: int | None = MAX_CLEARED_STARTS,
) -> list[str]:
    budget = AUDIENCE_BUDGETS.get(audience or "", None)
    lines = [
        f"    def {fn_name}(self) -> None:",
        f'        """{segment.shows or segment.name}"""',
    ]
    if segment.carries:
        carried = ", ".join(f"self.{name}" for name in segment.carries)
        lines.append(f"        # carried in:  {carried}")
    elif cleared_ceiling is None:
        lines.append("        # carried in:  nothing -- starts from a cleared frame")
    else:
        lines.append("        # carried in:  nothing -- starts from a cleared frame (R1")
        lines.append(f"        #              allows at most {cleared_ceiling} of these per deck)")
    if segment.produces:
        produced = ", ".join(f"self.{name}" for name in segment.produces)
        lines.append(f"        # hand off:    {produced}   <- set before returning")
    if budget:
        lines.append(
            f"        # budget:      <= {budget['plays']} self.play() calls, "
            f"<= {budget['words']} words on screen  [{audience}]"
        )
    if brief:
        # Advanced mode: the checklist is the part that is house style, so
        # it goes. What stays is the line an author cannot infer -- which
        # guarantees `validate` still enforces, and the sanctioned way to
        # overlap on purpose, since deleting the call is still wrong.
        lines += [
            "        # You own the composition here. Still checked either way:",
            "        # something on screen must change, every action your text",
            "        # names must happen, nothing may leave the frame. Overlap",
            "        # that is the design goes in allow=, never in a deleted call:",
            "        #   self.assert_no_overlap_among_tracked(allow=[(\"a\", \"b\")])",
        ]
    else:
        lines += [
            "        # TODO: author above the assert, then delete these notes:",
            "        #  [ ] something already on screen must CHANGE (Transform / .animate /",
            "        #      MoveAlongPath) -- entrances like Write/FadeIn/Create don't count",
            "        #  [ ] at least one non-text mobject, with on-screen text anchored to it",
            "        #  [ ] every action named in on-screen text is performed by an animation",
            "        #  [ ] Write() is for text only -- Create/DrawBorderThenFill for shapes",
        ]
    lines += [
        "        self.assert_no_overlap_among_tracked()",
        "",
        "",
    ]
    return lines


def check_plan(
    segments: list[Segment],
    audience: str | None = None,
    max_cleared_starts: int | None = MAX_CLEARED_STARTS,
) -> list[str]:
    """Validate the *plan*, before a line of deck code exists.

    This is the cheapest possible moment to catch these. A handoff name that
    no earlier segment produces becomes, once written, an `AttributeError`
    raised several segments away from the typo -- the single most common
    failure across past builds, and one that reads as a cascade rather than
    a misspelling. Caught here it costs one plan edit; caught after coding
    it costs a validate round trip and a hunt for the origin.

    Raises `ValueError` for the two structural faults. Returns advisory
    notes (segment count against the audience) rather than raising, since
    those are guidelines a deliberate outline may exceed.

    `max_cleared_starts=None` lifts the R1 ceiling, which is what
    `mode="advanced"` does. The handoff check is never lifted: a carried
    name nothing produces is a defect in any style, while how many segments
    open on a cleared frame is a judgement about pacing.
    """
    produced: set[str] = set()
    for index, segment in enumerate(segments):
        unknown = [name for name in segment.carries if name not in produced]
        if unknown:
            known = ", ".join(sorted(produced)) or "nothing yet"
            raise ValueError(
                f"Segment {index + 1} ({segment.name!r}) carries in "
                f"{', '.join(unknown)}, which no earlier segment produces. "
                f"Available at that point: {known}. Fix the plan's "
                "carried-in/hand-off columns, not the deck code."
            )
        produced.update(segment.produces)

    planned = any(s.carries or s.produces for s in segments)
    if planned and max_cleared_starts is not None:
        cleared = [s.name for s in segments if not s.carries]
        if len(cleared) > max_cleared_starts:
            raise ValueError(
                f"{len(cleared)} segments start from a cleared frame "
                f"({', '.join(cleared)}); R1 allows {max_cleared_starts}. "
                "Give the others something to carry in and change."
            )

    notes: list[str] = []
    span = AUDIENCE_SEGMENTS.get(audience or "")
    if span and not (span[0] <= len(segments) <= span[1]):
        notes.append(
            f"note: {len(segments)} segments for {audience}; the audience "
            f"table suggests {span[0]}-{span[1]}."
        )
    return notes


def render_deck_source(
    title: str,
    segments: list[object],
    audience: str | None = None,
    composition: str | None = None,
    *,
    mode: str | None = None,
    imports: object = None,
    root: Path | str = ".",
) -> str:
    """Render the Python source for a new deck file.

    `segments` accepts plain names (`["intro", "summary"]`) or planned
    segments -- `Segment(...)` instances or dicts with `name` / `shows` /
    `carries` / `produces`, which are the create-deck plan table's columns.
    Passing the planned form is what makes the file arrive with its state
    handoffs already named.

    `audience` ("middle-school" / "high-school") is recorded as a
    module-level `AUDIENCE` constant *and* as a per-segment budget comment.
    The constant is deliberately not part of the docstring: the webrunner's
    deck-title regex captures everything between the docstring quotes, so a
    second line there would leak into the displayed title.

    `composition` emits the named-slot block; pass `"none"` to omit it.

    `mode` and `imports` decide how much the scaffold settles for you, and
    both fall back to `open-manim-slides.json` in `root` before their mode
    default -- so the *project* pins the choice once instead of the agent
    re-deciding it every build, which would be a fresh source of the
    inconsistency the composition block exists to remove.

    * `mode="simple"` (default) -- two-column composition, star import,
      the full authoring checklist, R1's cleared-start ceiling enforced.
      Fewest decisions, most consistent output.
    * `mode="advanced"` -- no composition block (the author designs the
      layout), curated imports, a short stub, no R1 ceiling. Room to
      present differently, at the cost of the rails.

    A mode changes only what is *written into the file*. It never changes
    what `validate` enforces: safe frame, overlap, conflicting animations,
    illegible morphs, R2 and R4 behave identically under both. What
    relaxes are the pre-commitment gates, which are house style; what does
    not are the checks that catch defects.
    """
    if not segments:
        raise ValueError("A deck needs at least one segment.")

    options = resolve_options(mode=mode, composition=composition, imports=imports, root=root)
    composition = str(options["composition"])

    planned = [_coerce(raw) for raw in segments]
    for note in check_plan(planned, audience, options["max_cleared_starts"]):
        print(note, file=sys.stderr)
    class_name = _class_name(title)

    seen: set[str] = set()
    fn_names: list[str] = []
    for segment in planned:
        fn_name = f"segment_{_slugify(segment.name)}"
        if fn_name in seen:
            raise ValueError(
                f"Duplicate segment name after slugifying: {segment.name!r} -> {fn_name!r}"
            )
        seen.add(fn_name)
        fn_names.append(fn_name)

    lines: list[str] = ['"""', f"{title}", '"""', ""]
    lines.extend(_import_block(composition, options["imports"]))
    if audience is not None:
        lines.append(f'AUDIENCE = "{audience}"')
        lines.append("")
    if composition == "two-column":
        lines.extend(_composition_block())
    lines.extend(["", f"class {class_name}(Slide):"])
    lines.extend(_state_block(planned))
    lines.append("    def construct(self) -> None:")
    for fn_name in fn_names:
        lines.append(f"        self.{fn_name}()")
        lines.append("        self.next_slide()")
    lines.extend(["", ""])

    for segment, fn_name in zip(planned, fn_names):
        lines.extend(
            _segment_stub(
                segment,
                fn_name,
                audience,
                brief=bool(options["brief_stub"]),
                cleared_ceiling=options["max_cleared_starts"],
            )
        )

    return "\n".join(lines).rstrip() + "\n"


def new_deck(
    title: str,
    segments: list[object],
    out_dir: Path | str,
    audience: str | None = None,
    composition: str | None = None,
    *,
    mode: str | None = None,
    imports: object = None,
    root: Path | str = ".",
) -> Path:
    """Write a new deck file into `out_dir` and return its path.

    See `render_deck_source` for `mode` / `imports`; `root` is where
    `open-manim-slides.json` is looked for, and defaults to the working
    directory, which for a `create-deck` run is the project root.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (_slugify(title) + ".py")
    # UTF-8 explicitly: the title goes into the file's docstring verbatim,
    # and this project's decks are routinely written in a language the
    # platform default encoding cannot represent.
    out_path.write_text(
        render_deck_source(
            title,
            segments,
            audience=audience,
            composition=composition,
            mode=mode,
            imports=imports,
            root=root,
        ),
        encoding="utf-8",
    )
    return out_path
