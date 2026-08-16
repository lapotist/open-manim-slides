"""FastAPI app: browse decks, trigger a render with a live progress bar, and
present the finished deck in-browser -- a local, click-to-run alternative
to `manim render` + `manim-slides present` on the CLI, with the same
underlying commands doing the work.

Run with `python -m open_manim_slides.webrunner`.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from open_manim_slides.webrunner.render import OUTPUT_DIR, get_job, list_decks, start_render

_STATIC_DIR = Path(__file__).resolve().parent / "static"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="open-manim-slides runner")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/api/decks")
async def api_list_decks() -> list[dict]:
    return [dataclasses.asdict(deck) for deck in list_decks()]


@app.post("/api/render/{deck_id}")
async def api_start_render(deck_id: str) -> dict:
    decks = {deck.id: deck for deck in list_decks()}
    deck = decks.get(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail=f"No deck {deck_id!r}")
    job = await start_render(deck)
    return {"job_id": job.id}


@app.get("/api/render/{job_id}/events")
async def api_render_events(job_id: str) -> StreamingResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No job {job_id!r}")

    async def event_stream():
        async for state in job.events():
            yield f"data: {json.dumps(state)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
