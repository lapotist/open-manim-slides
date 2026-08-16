#!/usr/bin/env bash
# Quick-launch the local web runner (render decks + present them in-browser).
# Requires `pip install -e ".[web]"` to have been run once already.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec .venv/bin/python -m open_manim_slides.webrunner
