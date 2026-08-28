"""Command-line entry point: scaffold a project, check the environment.

This is the half of the package that makes a *fresh install* usable. The
Python modules alone are not the framework -- the authoring workflow lives
in `.agents/skills/create-deck/`, which is force-included into the wheel
as `open_manim_slides/_skills/` (see `pyproject.toml`). Without `init`
copying those files into a project, `pip install open-manim-slides` gives
you library code and no way to drive it.

`init` deliberately writes a *minimal* `AGENTS.md`. The development repo's
own `AGENTS.md` is 278 lines of file-by-file internals, and a symlinked
`CLAUDE.md` means an agent working in that repo has all of it in context
before any skill is invoked -- which is precisely the state a real user
does not have, and the reason a "test run" performed inside the dev repo
measures something other than what the skill's own guidance achieves.
Reproducing that file here would rebuild the same leak in every generated
project.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_NAMES = ("create-deck",)

#: The manim release every snippet in `references/motion-recipes.md` was
#: construct-verified against. A fresh install resolves whatever manim is
#: current, which will not stay this version -- and an animation recipe that
#: silently changed behaviour is the kind of defect that surfaces as a bad
#: rendered frame rather than an error, so `doctor` says when they differ.
VERIFIED_MANIM = "0.20.1"

PROJECT_AGENTS_MD = """\
# AGENTS.md

Instructions for an AI coding agent working in this project. Claude Code
reads this file through the `CLAUDE.md` symlink; other agents read it
directly.

## What this is

A [Manim Slides](https://github.com/jeertmans/manim-slides) deck project
built with [open-manim-slides](https://github.com/lapotist/open-manim-slides).
Decks live in `decks/`, one file per deck.

## Building a deck

Use the `create-deck` skill (`.agents/skills/create-deck/SKILL.md`) rather
than hand-writing a deck file. It plans the deck against seven countable
content rules, scaffolds the file, fills in each segment, validates the
layout without rendering, then reviews the rendered frames.

## Authoring convention

**One file per deck.** Each `self.next_slide()` segment is its own
top-level method (`segment_<name>`), called in sequence from
`construct()`. Segments share state through `self.<attr>` handoffs.

## Commands

```bash
python -m open_manim_slides.validate decks/<slug>.py   # layout checks, no render
manim render -ql decks/<slug>.py <ClassName>           # draft render
python -m open_manim_slides.frames <ClassName>         # per-segment review stills
python -m open_manim_slides.blankspace <ClassName>     # dead-space report
manim-slides present <ClassName>                       # present locally
```

`open-manim-slides doctor` checks that the system dependencies are in
place.
"""


def _skills_source() -> Path:
    """Where the canonical skill files are, installed or in a source tree."""
    packaged = Path(__file__).resolve().parent / "_skills"
    if packaged.is_dir():
        return packaged
    # Editable/source checkout: the canonical files still live at the repo
    # root, which is not inside the package directory.
    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / ".agents" / "skills"
    if source.is_dir():
        return source
    raise FileNotFoundError(
        "Cannot locate the skill files. Expected them at "
        f"{packaged} (installed) or {source} (source checkout)."
    )


def _link_or_copy(link: Path, target: Path) -> str:
    """Symlink `link` -> `target`, falling back to a copy where links fail.

    Windows without Developer Mode refuses symlink creation for
    unprivileged users, and a copy is a correct-if-duplicated fallback.
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        else:
            link.unlink()
    relative = os.path.relpath(target, link.parent)
    try:
        link.symlink_to(relative, target_is_directory=target.is_dir())
        return "symlink"
    except (OSError, NotImplementedError):
        if target.is_dir():
            shutil.copytree(target, link)
        else:
            shutil.copy2(target, link)
        return "copy"


def init_project(directory: Path, force: bool = False) -> list[str]:
    """Write the project scaffold into `directory`; return what was written."""
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)

    source = _skills_source()
    written: list[str] = []

    for name in SKILL_NAMES:
        src = source / name
        if not src.is_dir():
            raise FileNotFoundError(f"Skill {name!r} not found in {source}")
        dest = directory / ".agents" / "skills" / name
        if dest.exists():
            if not force:
                raise FileExistsError(
                    f"{dest} already exists. Re-run with --force to overwrite."
                )
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
        written.append(str(dest.relative_to(directory)))

        # Claude Code discovers skills under `.claude/skills`; the canonical
        # copy stays agent-agnostic under `.agents/`.
        link = directory / ".claude" / "skills" / name
        kind = _link_or_copy(link, dest)
        written.append(f"{link.relative_to(directory)} ({kind})")

    agents_md = directory / "AGENTS.md"
    if not agents_md.exists() or force:
        agents_md.write_text(PROJECT_AGENTS_MD)
        written.append("AGENTS.md")
    claude_md = directory / "CLAUDE.md"
    if not claude_md.exists() or force:
        kind = _link_or_copy(claude_md, agents_md)
        written.append(f"CLAUDE.md ({kind})")

    decks = directory / "decks"
    decks.mkdir(exist_ok=True)
    gitkeep = decks / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("")
    written.append("decks/")

    return written


#: (label, check) pairs. A check returns (ok, detail).
def _check_python() -> tuple[bool, str]:
    v = sys.version_info
    return (v >= (3, 10), f"{v.major}.{v.minor}.{v.micro}")


def _check_command(name: str, args: list[str]) -> tuple[bool, str]:
    path = shutil.which(name)
    if path is None:
        return (False, "not on PATH")
    try:
        out = subprocess.run(
            [path, *args], capture_output=True, text=True, timeout=20
        )
        first = (out.stdout or out.stderr).strip().splitlines()
        return (True, first[0][:60] if first else path)
    except (OSError, subprocess.SubprocessError) as exc:
        return (False, f"{type(exc).__name__}")


def _check_import(module: str) -> tuple[bool, str]:
    try:
        __import__(module)
    except Exception as exc:  # noqa: BLE001 - report any import failure
        return (False, f"{type(exc).__name__}: {exc}"[:60])
    try:
        return (True, importlib.metadata.version(module.replace("_", "-")))
    except importlib.metadata.PackageNotFoundError:
        return (True, "installed")


def doctor() -> int:
    """Print an environment report; return 0 if every required check passed."""
    required = [
        ("python >= 3.10", _check_python()),
        ("ffmpeg", _check_command("ffmpeg", ["-version"])),
        ("manim", _check_import("manim")),
        ("manim-slides", _check_import("manim_slides")),
        # manimpango is where missing cairo/pango headers actually surface.
        ("cairo/pango (manimpango)", _check_import("manimpango")),
    ]
    optional = [
        ("latex (MathTex/Tex)", _check_command("latex", ["--version"])),
        ("dvisvgm (MathTex/Tex)", _check_command("dvisvgm", ["--version"])),
        ("firefox (playback check)", _check_command("firefox", ["--version"])),
    ]

    failures = 0
    notes: list[str] = []

    manim_ok, manim_detail = required[2][1]
    if manim_ok:
        installed = manim_detail.split(".")[:2]
        verified = VERIFIED_MANIM.split(".")[:2]
        if installed != verified:
            notes.append(
                f"manim {manim_detail} is installed; the motion recipes were "
                f"verified against {VERIFIED_MANIM}. Animation behaviour may "
                "differ from what the skill's snippets describe."
            )

    print("required:")
    for label, (ok, detail) in required:
        mark = "ok  " if ok else "MISS"
        if not ok:
            failures += 1
        print(f"  [{mark}] {label:26} {detail}")
    print("optional:")
    for label, (ok, detail) in optional:
        print(f"  [{'ok  ' if ok else '--  '}] {label:26} {detail}")

    for note in notes:
        print(f"\nnote: {note}")

    if failures:
        print(
            f"\n{failures} required check(s) failed. See "
            "https://github.com/lapotist/open-manim-slides#requirements"
        )
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="open-manim-slides",
        description="Scaffold an open-manim-slides deck project.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="write the project scaffold here")
    p_init.add_argument("directory", nargs="?", default=".", type=Path)
    p_init.add_argument("--force", action="store_true", help="overwrite existing files")

    sub.add_parser("doctor", help="check system dependencies")
    sub.add_parser("version", help="print the installed version")

    args = parser.parse_args(argv)

    if args.command == "init":
        try:
            written = init_project(args.directory, force=args.force)
        except (FileExistsError, FileNotFoundError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for item in written:
            print(f"  created {item}")
        return 0

    if args.command == "doctor":
        return doctor()

    try:
        print(importlib.metadata.version("open-manim-slides"))
    except importlib.metadata.PackageNotFoundError:
        print("unknown (not installed as a distribution)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
