# open-manim-slides

An open-source framework for building [Manim Slides](https://github.com/jeertmans/manim-slides)
presentations, inspired by [open-slide](https://open-slide.dev/) — a
controlled, skill-driven workflow for generating and iterating on slide
decks with an AI coding agent, instead of relying on a long prose
instructions file.

Status: early scaffold, under active development. See `HANDOFF.md` and
`AGENTS.md` for design background and conventions.

## Quick start

Create a fresh deck project — a virtualenv with the framework installed,
the `create-deck` skill files, and an empty `decks/` directory:

```bash
npx open-manim-slides@latest new my-deck
cd my-deck && source .venv/bin/activate
```

Then open the directory with your coding agent and ask it to build a deck.
`@latest` fetches the newest published version every time, so each project
starts from a clean, current framework rather than whatever a long-lived
checkout has accumulated — which is what you want when you are measuring
how well the workflow itself performs.

No Node? The same bootstrap without it:

```bash
pipx run --spec open-manim-slides open-manim-slides init my-deck   # or uvx
```

Check the system dependencies at any time:

```bash
open-manim-slides doctor
```

## Requirements

- Python >= 3.10
- System libraries for `manimpango` (a `manim` dependency): `cairo` and
  `pango` development headers (e.g. `sudo dnf install cairo-devel
  pango-devel` on Fedora, `sudo apt install libcairo2-dev libpango1.0-dev`
  on Debian/Ubuntu).
- `ffmpeg`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running a deck

CLI: render, then present with arrow keys / click:

```bash
manim render decks/<file>.py <ClassName>
manim-slides present <ClassName>
```

Or a local web UI that does both, with a progress bar and an in-browser
presenter — see `src/open_manim_slides/webrunner/`. One-time setup, then
launch any time with `./run-webrunner.sh`:

```bash
pip install -e ".[web]"   # once
./run-webrunner.sh        # every time after that
# open http://127.0.0.1:8000
```

## License

MIT — see `LICENSE`.
