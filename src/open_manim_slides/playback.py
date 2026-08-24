"""Navigation check for an exported deck, driven through a real browser.

`python -m open_manim_slides.playback <exported.html>` opens the page in
headless Firefox, walks it with the arrow keys, and reports every
navigation where the viewer would see the wrong thing. It exists because
the bug it guards against is invisible to every other check in this
project: the deck renders correctly, every frame is right, and the export
is valid -- what goes wrong is *which already-decoded frame the compositor
is still showing* at the moment a slide becomes current.

What it measures, and why that specifically
-------------------------------------------
`currentTime` is not the observable. It updates synchronously while the
compositor keeps presenting the previous frame, so a video can read
`currentTime == 0` while the viewer is still looking at the segment's
final frame. That gap is the flash. The instrument that does see it is
`requestVideoFrameCallback`, which reports the `mediaTime` of each frame
actually *presented*.

So the check is: at the moment a slide becomes current, is the frame
already on screen (the last one presented for that video) the pose the
viewer should be seeing -- 0 going forward, the final frame going
backward? A run that satisfies that never flashes, on any hardware.
Timings are reported but deliberately not asserted on: the magnitude is
environment-specific (37 ms under headless software compositing for a
stale frame that stood ~400 ms on a GPU-composited desktop), while the
wrong-pose condition is not.

Requires Firefox on PATH; no Python dependencies (the WebDriver BiDi
client below is a ~90-line stdlib WebSocket speaker). Not imported by the
core package and never run during a deck build -- it is a check on the
finished artifact, not a step in producing one.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

# Arrow keys as WebDriver normalises them (a `keyDown` value browsers map
# back to the real key), not as JS key names.
_ARROW_LEFT = "\ue012"
_ARROW_RIGHT = "\ue014"

#: How far the frame on screen may sit from the pose it should be at
#: before the viewer is seeing the wrong part of the segment. Scaled to
#: the segment, with a floor, rather than a flat number of seconds --
#: "a quarter of the way into the build" means the same thing whether the
#: segment runs 1 s or 10 s.
#:
#: This is deliberately not tight, and the reason is worth keeping. A
#: hidden video's *composited* surface can lag its `currentTime`: parking
#: it off screen seeks it correctly, but no page JS can force the browser
#: to present that frame while nothing is showing it. So re-entering a
#: segment quickly can flash, for one frame, the frame the viewer was
#: looking at when they left it. That is a hiccup on content they have
#: already seen. What this check exists to catch is the other thing --
#: being shown a part of the segment they have *not* seen, above all its
#: ending on the way in, which spoils the build the deck exists to
#: perform. Those are different defects and only one of them is a bug.
_MINIMUM_TOLERANCE = 0.5
_TOLERANCE_FRACTION = 0.25


def _tolerance(duration: float) -> float:
    return max(_MINIMUM_TOLERANCE, _TOLERANCE_FRACTION * duration)


class _WebSocket:
    """The few frames of RFC 6455 needed to talk to Firefox's BiDi agent.

    Text frames only, client-masked, no continuation or compression --
    which is all the protocol uses. Written out rather than taking a
    dependency so this check runs from a bare `pip install -e .`.
    """

    def __init__(self, host: str, port: int, path: str) -> None:
        self._sock = socket.create_connection((host, port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self._sock.sendall(
            (
                f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
                "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        header = self._read_until(b"\r\n\r\n").decode("latin-1")
        if " 101 " not in header.split("\r\n")[0]:
            raise RuntimeError(f"WebSocket upgrade refused: {header.splitlines()[0]}")
        if expected.lower() not in header.lower():
            raise RuntimeError("WebSocket accept key mismatch")
        self._buffer = b""

    def _read_until(self, marker: bytes) -> bytes:
        data = b""
        while marker not in data:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise RuntimeError("connection closed during handshake")
            data += chunk
        head, _, rest = data.partition(marker)
        self._buffer = rest
        return head + marker

    def _recv_exactly(self, n: int) -> bytes:
        while len(self._buffer) < n:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise RuntimeError("connection closed")
            self._buffer += chunk
        out, self._buffer = self._buffer[:n], self._buffer[n:]
        return out

    def send(self, payload: str) -> None:
        data = payload.encode()
        header = bytearray([0x81])  # FIN + text
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < (1 << 16):
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        mask = os.urandom(4)
        header += mask
        self._sock.sendall(bytes(header) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self) -> str:
        while True:
            first, second = self._recv_exactly(2)
            opcode = first & 0x0F
            length = second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exactly(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exactly(8))[0]
            payload = self._recv_exactly(length)
            if second & 0x80:  # server frames are never masked, but be safe
                raise RuntimeError("unexpected masked server frame")
            if opcode == 0x1:
                return payload.decode()
            if opcode == 0x8:
                raise RuntimeError("WebSocket closed by browser")
            # ping/pong and anything else: ignore and keep reading

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class _Browser:
    """A headless Firefox speaking WebDriver BiDi, as a context manager."""

    def __init__(self, port: int = 9222) -> None:
        self._port = port
        self._profile = tempfile.mkdtemp(prefix="oms-playback-")
        self._process: subprocess.Popen[bytes] | None = None
        self._ws: _WebSocket | None = None
        self._next_id = 0

    def __enter__(self) -> _Browser:
        firefox = shutil.which("firefox")
        if firefox is None:
            raise RuntimeError("firefox not found on PATH")
        self._process = subprocess.Popen(
            [
                firefox, "--headless", "--new-instance",
                "--profile", self._profile,
                "--remote-debugging-port", str(self._port),
                "--remote-allow-hosts", "127.0.0.1,localhost",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                self._ws = _WebSocket("127.0.0.1", self._port, "/session")
                break
            except (OSError, RuntimeError):
                time.sleep(0.25)
        if self._ws is None:
            raise RuntimeError("Firefox did not open its BiDi port within 60s")
        self.call("session.new", {"capabilities": {}})
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._ws is not None:
            self._ws.close()
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self._process.kill()
        shutil.rmtree(self._profile, ignore_errors=True)

    def call(self, method: str, params: dict | None = None) -> dict:
        assert self._ws is not None
        self._next_id += 1
        message_id = self._next_id
        self._ws.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self._ws.recv())
            if message.get("id") != message_id:
                continue  # an event, or a reply we are no longer waiting on
            if message.get("type") == "error":
                raise RuntimeError(f"{method}: {message.get('error')}: {message.get('message')}")
            return message.get("result", {})

    # -- page helpers -----------------------------------------------------

    def open(self, url: str) -> str:
        context = self.call("browsingContext.getTree")["contexts"][0]["context"]
        self.call(
            "browsingContext.setViewport",
            {"context": context, "viewport": {"width": 1280, "height": 720}, "devicePixelRatio": 1},
        )
        self.call("browsingContext.navigate", {"context": context, "url": url, "wait": "complete"})
        return context

    def evaluate(self, context: str, expression: str) -> object:
        result = self.call(
            "script.evaluate",
            {
                "expression": expression,
                "target": {"context": context},
                "awaitPromise": False,
                "resultOwnership": "none",
            },
        )
        if result.get("type") == "exception":
            detail = result.get("exceptionDetails", {}).get("text", result)
            raise RuntimeError(f"page threw: {detail}")
        return result.get("result", {}).get("value")

    def press(self, context: str, key: str) -> None:
        self.call(
            "input.performActions",
            {
                "context": context,
                "actions": [
                    {
                        "type": "key",
                        "id": "keyboard",
                        "actions": [{"type": "keyDown", "value": key}, {"type": "keyUp", "value": key}],
                    }
                ],
            },
        )


# Installed in the page before navigating. Records the mediaTime of every
# frame each background video actually presents, plus the time of every
# slide change, on one clock.
_RECORDER = """
(() => {
  const videos = Array.from(document.querySelectorAll('.slide-background video'));
  if (!videos.length) return 'NO_VIDEOS';
  if (typeof videos[0].requestVideoFrameCallback !== 'function') return 'NO_RVFC';
  const origin = performance.now();
  const now = () => +(performance.now() - origin).toFixed(1);
  window.__omsPlayback = {
    paints: [],
    navigations: [],
    durations: videos.map(v => +(v.duration || 0).toFixed(3)),
  };
  videos.forEach((video, index) => {
    const onFrame = (_, metadata) => {
      window.__omsPlayback.paints.push({ index, t: now(), mediaTime: +metadata.mediaTime.toFixed(3) });
      video.requestVideoFrameCallback(onFrame);
    };
    video.requestVideoFrameCallback(onFrame);
  });
  Reveal.on('slidechanged', event => {
    window.__omsPlayback.navigations.push({ t: now(), h: event.indexh });
  });
  return 'ok';
})()
"""

_READY = """
(() => {
  const videos = [...document.querySelectorAll('.slide-background video')];
  return !!(window.Reveal && Reveal.isReady && Reveal.isReady())
    && videos.length > 0 && videos.every(v => v.readyState >= 2);
})()
"""


@dataclass(frozen=True)
class Navigation:
    """One slide change, and what the viewer was looking at during it."""

    direction: str
    from_index: int
    to_index: int
    expected_pose: float
    #: mediaTime of the last frame presented for the entered slide's video
    #: before the change -- i.e. what stays on screen until something
    #: repaints. `None` when that video has never presented a frame, which
    #: is always fine (nothing stale can be showing).
    on_screen: float | None
    #: ms from the slide change to the next frame presented for it, or
    #: `None` if nothing repainted while the slide was current (also fine:
    #: it means the correct frame was already there and stayed).
    repaint_ms: float | None

    #: The entered segment's length, for scaling the tolerance.
    duration: float

    @property
    def ok(self) -> bool:
        if self.on_screen is None:
            return True
        return abs(self.on_screen - self.expected_pose) <= _tolerance(self.duration)

    def describe(self) -> str:
        arrow = "->" if self.direction == "forward" else "<-"
        repaint = "no repaint" if self.repaint_ms is None else f"repaint +{self.repaint_ms:.0f}ms"
        on_screen = "nothing yet" if self.on_screen is None else f"{self.on_screen:.2f}s"
        status = "ok" if self.ok else "WRONG FRAME ON SCREEN"
        return (
            f"  {self.direction:8s} {self.from_index} {arrow} {self.to_index}  "
            f"on screen {on_screen:>11s}  want ~{self.expected_pose:.2f}s  "
            f"({repaint})  {status}"
        )


def _analyse(recording: dict) -> list[Navigation]:
    durations = recording["durations"]
    paints = recording["paints"]
    navigations = recording["navigations"]
    results: list[Navigation] = []
    previous = 0
    for position, change in enumerate(navigations):
        index, at = change["h"], change["t"]
        # Only frames presented while this slide is still current count as
        # its repaint; anything later belongs to the next navigation (and
        # to the off-screen parking seek, which is the point of the fix).
        until = navigations[position + 1]["t"] if position + 1 < len(navigations) else float("inf")
        mine = [p for p in paints if p["index"] == index]
        before = [p for p in mine if p["t"] < at]
        during = [p for p in mine if at <= p["t"] < until]
        forward = index > previous
        duration = durations[index] if index < len(durations) else 0.0
        results.append(
            Navigation(
                direction="forward" if forward else "backward",
                from_index=previous,
                to_index=index,
                expected_pose=0.0 if forward else duration,
                on_screen=before[-1]["mediaTime"] if before else None,
                repaint_ms=(during[0]["t"] - at) if during else None,
                duration=duration,
            )
        )
        previous = index
    return results


def check(url: str, *, steps: list[str] | None = None, settle: float = 2.5) -> list[Navigation]:
    """Walk `url` with the arrow keys and report what each navigation showed.

    `steps` is a list of `"forward"`/`"backward"`; the default walks three
    segments in, then back out and in again, which is the shortest path
    that reaches every case: a first visit, a return to a finished
    segment, and -- the one that regressed -- a *forward* re-entry into a
    segment previously left parked at its end.
    """
    steps = steps or ["forward", "forward", "forward", "backward", "backward", "forward", "backward"]
    with _Browser() as browser:
        context = browser.open(url)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if browser.evaluate(context, _READY):
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("deck never became ready (no Reveal, or videos never loaded)")
        # Segment videos autoplay on load; let the first one finish so the
        # walk starts from a settled deck rather than mid-animation.
        time.sleep(settle)
        status = browser.evaluate(context, _RECORDER)
        if status != "ok":
            raise RuntimeError(f"cannot record this page: {status}")
        for step in steps:
            browser.press(context, _ARROW_RIGHT if step == "forward" else _ARROW_LEFT)
            time.sleep(settle)
        recording = json.loads(str(browser.evaluate(context, "JSON.stringify(window.__omsPlayback)")))
    return _analyse(recording)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        print("usage: python -m open_manim_slides.playback <exported.html|url>")
        return 2
    target = argv[0]
    url = target if "://" in target else Path(target).resolve().as_uri()
    navigations = check(url)
    print(f"navigation check: {url}")
    for navigation in navigations:
        print(navigation.describe())
    bad = [n for n in navigations if not n.ok]
    if bad:
        print(
            f"\n{len(bad)} of {len(navigations)} navigations showed the wrong frame. "
            "The viewer sees that frame until the video repaints -- a flash of a "
            "segment's ending on the way in, or of its beginning on the way back."
        )
        return 1
    print(f"\nall {len(navigations)} navigations showed the correct frame immediately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
