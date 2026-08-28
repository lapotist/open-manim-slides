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
        f"SAFE_X = {safe_x}          # |x| any element must stay within",
        f"SAFE_Y = {safe_y}           # |y| any element must stay within",
        "HEAD_Y = 3.0           # heading() sits here; leave this band clear",
        f"COL_LEFT_X = {-col_centre}      # centre of the figure column",
        f"COL_RIGHT_X = {col_centre}      # centre of the accumulating-text column",
        f"COL_W = {round(col_half * 2, 2)}           # size the figure to FILL this, not float in it",
        "ROW_Y = (1.9, 0.9, -0.1, -1.1, -2.1)   # text rows, top-down",
        "",
    ]


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


def _segment_stub(segment: Segment, fn_name: str, audience: str | None) -> list[str]:
    budget = AUDIENCE_BUDGETS.get(audience or "", None)
    lines = [
        f"    def {fn_name}(self) -> None:",
        f'        """{segment.shows or segment.name}"""',
    ]
    if segment.carries:
        carried = ", ".join(f"self.{name}" for name in segment.carries)
        lines.append(f"        # carried in:  {carried}")
    else:
        lines.append("        # carried in:  nothing -- starts from a cleared frame (R1")
        lines.append("        #              allows at most 2 of these per deck)")
    if segment.produces:
        produced = ", ".join(f"self.{name}" for name in segment.produces)
        lines.append(f"        # hand off:    {produced}   <- set before returning")
    if budget:
        lines.append(
            f"        # budget:      <= {budget['plays']} self.play() calls, "
            f"<= {budget['words']} words on screen  [{audience}]"
        )
    lines += [
        "        # TODO: author above the assert, then delete these notes:",
        "        #  [ ] something already on screen must CHANGE (Transform / .animate /",
        "        #      MoveAlongPath) -- entrances like Write/FadeIn/Create don't count",
        "        #  [ ] at least one non-text mobject, with on-screen text anchored to it",
        "        #  [ ] every action named in on-screen text is performed by an animation",
        "        #  [ ] Write() is for text only -- Create/DrawBorderThenFill for shapes",
        "        self.assert_no_overlap_among_tracked()",
        "",
        "",
    ]
    return lines


#: Segment-count range per audience, from create-deck's audience table.
AUDIENCE_SEGMENTS = {"middle-school": (5, 6), "high-school": (7, 9)}

#: R1: how many segments may begin from a cleared frame.
MAX_CLEARED_STARTS = 2


def check_plan(segments: list[Segment], audience: str | None = None) -> list[str]:
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
    if planned:
        cleared = [s.name for s in segments if not s.carries]
        if len(cleared) > MAX_CLEARED_STARTS:
            raise ValueError(
                f"{len(cleared)} segments start from a cleared frame "
                f"({', '.join(cleared)}); R1 allows {MAX_CLEARED_STARTS}. "
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
    composition: str = "two-column",
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
    """
    if not segments:
        raise ValueError("A deck needs at least one segment.")

    planned = [_coerce(raw) for raw in segments]
    for note in check_plan(planned, audience):
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

    needs_mobject = any(s.produces or s.carries for s in planned)

    lines: list[str] = ['"""', f"{title}", '"""', ""]
    if needs_mobject:
        lines.append("from manim import Mobject")
    lines.append("from open_manim_slides import Slide, assert_within_safe_frame")
    lines.append("")
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
        lines.extend(_segment_stub(segment, fn_name, audience))

    return "\n".join(lines).rstrip() + "\n"


def new_deck(
    title: str,
    segments: list[object],
    out_dir: Path | str,
    audience: str | None = None,
    composition: str = "two-column",
) -> Path:
    """Write a new deck file into `out_dir` and return its path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (_slugify(title) + ".py")
    out_path.write_text(
        render_deck_source(title, segments, audience=audience, composition=composition)
    )
    return out_path
