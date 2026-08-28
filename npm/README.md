# open-manim-slides

Bootstrap a [Manim Slides](https://github.com/jeertmans/manim-slides) deck
project built for an AI coding agent to author.

```bash
npx open-manim-slides@latest new my-deck
```

That creates a directory containing a Python virtualenv with the framework
installed, the `create-deck` skill files (`.agents/skills/`, projected to
`.claude/skills/` for Claude Code), and an empty `decks/`. Open it with
your agent and ask for a deck.

This package is a bootstrapper, not the framework. The framework is the
Python distribution `open-manim-slides`; Node is only the delivery
mechanism, chosen because `npx <pkg>@latest` reliably fetches the current
version with nothing installed globally to go stale.

## Options

| flag | meaning |
|---|---|
| `--from <pypi\|git\|SPEC>` | where to install the framework from (default `git`) |
| `--ref <ref>` | git ref, or exact version with `--from pypi` |
| `--python <exe>` | interpreter to build the venv with (needs >= 3.10) |
| `--web` | also install the optional local web runner |
| `--force` | write into a non-empty directory |
| `--no-install` | scaffold only; skip the venv and install |

## What it cannot install for you

`manim` builds `manimpango` against system **cairo** and **pango**
development headers, and `MathTex`/`Tex` need a **LaTeX** distribution.
You also need **ffmpeg**. The generated project reports on all of them:

```bash
.venv/bin/open-manim-slides doctor
```

MIT licensed. Source: https://github.com/lapotist/open-manim-slides
