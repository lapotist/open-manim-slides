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


def render_deck_source(title: str, segments: list[str]) -> str:
    """Render the Python source for a new deck file.

    `segments` is a list of short segment names (e.g. ["intro", "main-idea",
    "summary"]); each becomes its own `segment_<name>` function, called in
    order from `construct()`.
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
        "",
        f"class {class_name}(Slide):",
        "    def construct(self) -> None:",
    ]
    for fn_name in segment_fn_names:
        lines.append(f"        self.{fn_name}()")
        lines.append("        self.next_slide()")
    lines.append("")
    lines.append("")

    for raw_name, fn_name in zip(segments, segment_fn_names):
        lines.append(f"    def {fn_name}(self) -> None:")
        lines.append(f'        """{raw_name}"""')
        lines.append("        # TODO: author this segment's content.")
        lines.append("        pass")
        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def new_deck(title: str, segments: list[str], out_dir: Path | str) -> Path:
    """Write a new deck file into `out_dir` and return its path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = _slugify(title) + ".py"
    out_path = out_dir / file_name
    out_path.write_text(render_deck_source(title, segments))
    return out_path
