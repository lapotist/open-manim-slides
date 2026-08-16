"""Deck discovery and render orchestration for the web runner.

Wraps `manim render` as a subprocess rather than importing/calling into
manim in-process -- this is what makes concurrent/repeated renders safe
despite the global `manim.config` state quirks noted elsewhere in this
project (see `tests/test_render_smoke.py`'s `config.output_file` note);
each render gets its own process and its own config.

Progress comes from parsing manim's own line-buffered tqdm output, which
survives being piped to a non-tty subprocess (verified empirically, not
assumed -- tqdm falls back to newline-terminated updates instead of
carriage-return overwrites when `stderr` isn't a real terminal). The total
animation count isn't known ahead of render, so it's estimated by counting
`self.play(` call sites in the deck's source; this is an estimate, not
exact (a single call can expand into more than one logged "Animation N"
entry), so the reported progress is capped at 99% until the process
actually exits successfully.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from open_manim_slides.convert import convert_to_html

DECKS_DIR = Path("decks")
SLIDES_DIR = Path("slides")
OUTPUT_DIR = Path("webrunner_output")

_CLASS_RE = re.compile(r"^class (\w+)\(Slide\):", re.MULTILINE)
_TITLE_RE = re.compile(r'^"""\s*\n(.+?)\n"""', re.MULTILINE | re.DOTALL)
_ANIMATION_PROGRESS_RE = re.compile(r"Animation (\d+): [^:]*:\s*(\d+)%\|")


def _progress_from_animation_line(index: int, within: int, total_estimate: int) -> tuple[int, int, str]:
    """Turn a parsed `Animation N: ...: XX%` line into (new_total, progress, message).

    `total_estimate` is a lower bound in practice, not exact (a single
    `self.play()` call can log as more than one "Animation N" entry) --
    self-corrected upward here rather than ever displaying a count past
    the stated total, e.g. "animation 12 of ~8", which reads as broken
    even though it's just an estimate catching up to reality.
    """
    total_estimate = max(total_estimate, index + 1)
    progress = min(99, round(100 * (index + within / 100) / total_estimate))
    message = f"Rendering animation {index + 1} of ~{total_estimate}"
    return total_estimate, progress, message


@dataclass(frozen=True)
class DeckInfo:
    id: str
    file: str
    class_name: str
    title: str


def list_decks(decks_dir: Path = DECKS_DIR) -> list[DeckInfo]:
    """Discover renderable decks in `decks_dir` from their source alone.

    A deck must define exactly one top-level `class Foo(Slide):` to be
    listed; the module docstring (as scaffold.py writes it) is used as the
    display title, falling back to the file's stem.
    """
    decks = []
    if not decks_dir.is_dir():
        return decks
    for path in sorted(decks_dir.glob("*.py")):
        source = path.read_text()
        class_match = _CLASS_RE.search(source)
        if not class_match:
            continue
        title_match = _TITLE_RE.search(source)
        title = title_match.group(1).strip() if title_match else path.stem
        decks.append(DeckInfo(id=path.stem, file=path.name, class_name=class_match.group(1), title=title))
    return decks


@dataclass
class RenderJob:
    id: str
    deck: DeckInfo
    status: str = "running"  # running | done | error
    progress: int = 0
    message: str = "Starting..."
    output_url: str | None = None
    error: str | None = None
    _subscribers: list[asyncio.Queue] = field(default_factory=list, repr=False, compare=False)

    def _state(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "output_url": self.output_url,
            "error": self.error,
        }

    def _publish(self) -> None:
        state = self._state()
        for queue in self._subscribers:
            queue.put_nowait(state)

    async def events(self) -> AsyncIterator[dict[str, Any]]:
        """Yield the current state immediately, then every update until done.

        A subscriber that connects after the job has already finished still
        gets one event (the final state) instead of hanging forever.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        try:
            yield self._state()
            while self.status == "running":
                yield await queue.get()
        finally:
            self._subscribers.remove(queue)


_JOBS: dict[str, RenderJob] = {}


def get_job(job_id: str) -> RenderJob | None:
    return _JOBS.get(job_id)


async def start_render(deck: DeckInfo) -> RenderJob:
    job = RenderJob(id=str(uuid.uuid4()), deck=deck)
    _JOBS[job.id] = job
    asyncio.create_task(_run_render(job))
    return job


async def _run_render(job: RenderJob) -> None:
    try:
        source = (DECKS_DIR / job.deck.file).read_text()
        total_estimate = max(source.count("self.play("), 1)

        proc = await asyncio.create_subprocess_exec(
            "manim",
            "render",
            str(DECKS_DIR / job.deck.file),
            job.deck.class_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode(errors="replace")
            match = _ANIMATION_PROGRESS_RE.search(line)
            if match:
                index, within = int(match.group(1)), int(match.group(2))
                total_estimate, job.progress, job.message = _progress_from_animation_line(
                    index, within, total_estimate
                )
                job._publish()

        returncode = await proc.wait()
        if returncode != 0:
            job.status = "error"
            job.error = f"manim render exited with code {returncode}"
            job.message = job.error
            job._publish()
            return

        job.progress = 99
        job.message = "Exporting presentation..."
        job._publish()

        output_dir = OUTPUT_DIR / job.id
        output_dir.mkdir(parents=True, exist_ok=True)
        dest = output_dir / "index.html"
        # Reveal.js only creates a segment's <video> element (and starts
        # fetching/decoding it) once that segment comes within
        # `view_distance` of the current one -- confirmed by reading
        # reveal.js 6.0.1's own source (js/reveal.js, js/controllers/
        # slidecontent.js), not assumed. Its default (3) means a deck's
        # later segments haven't started loading at all until you first
        # navigate near them, which is exactly the "sometimes laggy going
        # back and forth" symptom for these typically-small (5-8 segment)
        # decks. A generous fixed value covers any realistic deck size so
        # every segment's video starts loading immediately on page open.
        await asyncio.to_thread(
            convert_to_html,
            [job.deck.class_name],
            dest,
            SLIDES_DIR,
            view_distance=50,
            mobile_view_distance=50,
        )

        job.status = "done"
        job.progress = 100
        job.message = "Done."
        job.output_url = f"/output/{job.id}/index.html"
        job._publish()
    except Exception as exc:  # noqa: BLE001 - report to the UI instead of a bare 500
        job.status = "error"
        job.error = f"{type(exc).__name__}: {exc}"
        job.message = job.error
        job._publish()
