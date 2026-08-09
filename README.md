# open-manim-slides

An open-source framework for building [Manim Slides](https://github.com/jeertmans/manim-slides)
presentations, inspired by [open-slide](https://open-slide.dev/) — a
controlled, skill-driven workflow for generating and iterating on slide
decks with an AI coding agent, instead of relying on a long prose
instructions file.

Status: early scaffold, under active development. See `HANDOFF.md` and
`AGENTS.md` for design background and conventions.

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

## License

MIT — see `LICENSE`.
