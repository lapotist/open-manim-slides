"""Deterministic deck scaffolder.

Produces the mechanical, boilerplate part of a new deck file (one file per
deck, each segment as its own top-level function -- the resolved
authoring-unit convention). Content within each segment stays for the agent
to fill in; this module only owns file structure, so it can be tested
independently of any LLM-authored content.
"""

from __future__ import annotations

import re
from pathlib import Path


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "segment"


def _class_name(title: str) -> str:
    words = re.sub(r"[^a-zA-Z0-9]+", " ", title).split()
    return "".join(word.capitalize() for word in words) or "Deck"


def render_deck_source(title: str, segments: list[str], audience: str | None = None) -> str:
    """Render the Python source for a new deck file.

    `segments` is a list of short segment names (e.g. ["intro", "main-idea",
    "summary"]); each becomes its own `segment_<name>` function, called in
    order from `construct()`.

    `audience` (e.g. "middle-school", "high-school") is recorded as a
    module-level `AUDIENCE` constant so a later editing session inherits
    the constraint. Deliberately *not* part of the docstring: the
    webrunner's deck-title regex captures everything between the docstring
    quotes, so a second line there would leak into the displayed title.
    """
    if not segments:
        raise ValueError("A deck needs at least one segment.")

    class_name = _class_name(title)
    seen: set[str] = set()
    segment_fn_names: list[str] = []
    for raw_name in segments:
        slug = _slugify(raw_name)
        fn_name = f"segment_{slug}"
        if fn_name in seen:
            raise ValueError(f"Duplicate segment name after slugifying: {raw_name!r} -> {fn_name!r}")
        seen.add(fn_name)
        segment_fn_names.append(fn_name)

    lines: list[str] = [
        '"""',
        f"{title}",
        '"""',
        "",
        "from open_manim_slides import Slide, assert_within_safe_frame",
        "",
    ]
    if audience is not None:
        lines.append(f'AUDIENCE = "{audience}"')
        lines.append("")
    lines.extend(
        [
            "",
            f"class {class_name}(Slide):",
            "    def construct(self) -> None:",
        ]
    )
    for fn_name in segment_fn_names:
        lines.append(f"        self.{fn_name}()")
        lines.append("        self.next_slide()")
    lines.append("")
    lines.append("")

    # The checklist rides inside the file the agent is editing -- in
    # context on every edit, deleted as the segment gets filled in --
    # rather than living only in skill prose it may have stopped attending
    # to. Mirrors the create-deck skill's content rules; keep in sync.
    checklist = [
        "        # TODO: author this segment above the assert, then delete this checklist:",
        "        #  [ ] something already on screen must CHANGE (Transform / .animate /",
        "        #      MoveAlongPath) -- entrances like Write/FadeIn/Create don't count",
        "        #  [ ] carry the previous segment's figure in and move it aside; only 2",
        "        #      segments per deck may start from a cleared frame",
        "        #  [ ] at least one non-text mobject, with on-screen text anchored to it",
        "        #  [ ] every action named in on-screen text is performed by an animation",
        "        #  [ ] Write() is for text only -- Create/DrawBorderThenFill for shapes",
    ]
    for raw_name, fn_name in zip(segments, segment_fn_names):
        lines.append(f"    def {fn_name}(self) -> None:")
        lines.append(f'        """{raw_name}"""')
        lines.extend(checklist)
        lines.append("        self.assert_no_overlap_among_tracked()")
        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def new_deck(title: str, segments: list[str], out_dir: Path | str, audience: str | None = None) -> Path:
    """Write a new deck file into `out_dir` and return its path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = _slugify(title) + ".py"
    out_path = out_dir / file_name
    out_path.write_text(render_deck_source(title, segments, audience=audience))
    return out_path
