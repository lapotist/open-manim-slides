"""Phase timer and budget tracker for a deck build.

Two jobs, both aimed at the same complaint: a `create-deck` run goes quiet
for a long time and nobody can tell whether it is progressing or stuck.

1. **Status.** Marks phase boundaries and renders a one-line progress bar
   with elapsed time per phase. Because wall clock between two calls
   includes the agent's own thinking, this measures the part that
   `frames.py`/render timings never could — drafting and code writing are
   most of a run, and were previously invisible.
2. **Budget.** Given a time limit, says on every phase call whether the
   run is on track, and what to cut when it is not. The verdict is
   phase-aware: 70% of the budget spent entering `review` is fine, the
   same number entering `code` is not.

**The bar has to be relayed, not just printed.** A command's stdout goes
to the agent, not reliably to the user's terminal, so the agent is
responsible for pasting the status line into its own visible reply. The
skill says so explicitly; this module only computes it.

State lives in `media/progress/<Deck>.json` (media/ is gitignored).

Usage:
    python -m open_manim_slides.progress start <Deck> [budget]
    python -m open_manim_slides.progress phase <Deck> <phase>
    python -m open_manim_slides.progress report <Deck>

`budget` accepts `20m`, `90s`, `1h30m`, or a bare number of minutes.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROGRESS_DIR = Path("media") / "progress"

# Nominal share of a run each phase should take, from a measured build of
# this repo's trig deck. Used only to judge whether the run is ahead or
# behind at a given point -- never to hurry a phase that is going fine.
PHASE_SHARE: dict[str, float] = {
    "plan": 0.12,
    "scaffold": 0.02,
    "code": 0.34,
    "validate": 0.08,
    "render": 0.06,
    "review": 0.28,
    "finish": 0.10,
}
PHASE_ORDER = list(PHASE_SHARE)

# How far past the expected share a run may drift before it is "behind".
DRIFT_TOLERANCE = 1.25

BAR_WIDTH = 14


class ProgressError(RuntimeError):
    """A progress-tracking failure with a user-facing message."""


def parse_budget(text: str) -> int:
    """Seconds from `20m`, `90s`, `1h30m`, or a bare number of minutes."""
    text = text.strip().lower()
    if not text:
        raise ProgressError("Empty budget.")
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return int(float(text) * 60)
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*([hms])", text)
    if not matches:
        raise ProgressError(f"Could not read a duration from {text!r} (try '20m', '90s', '1h30m').")
    scale = {"h": 3600, "m": 60, "s": 1}
    return int(sum(float(value) * scale[unit] for value, unit in matches))


def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m{rest:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


@dataclass
class Run:
    deck: str
    started: float
    budget: int | None
    phases: list[dict]  # [{"name": str, "at": float}, ...]
    directory: Path = PROGRESS_DIR

    @property
    def path(self) -> Path:
        return self.directory / f"{self.deck}.json"

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"deck": self.deck, "started": self.started, "budget": self.budget, "phases": self.phases},
                indent=2,
            )
        )

    @classmethod
    def load(cls, deck: str, progress_dir: Path = PROGRESS_DIR) -> Run:
        path = progress_dir / f"{deck}.json"
        if not path.is_file():
            raise ProgressError(f"No run in progress for {deck!r} -- run `progress start {deck}` first.")
        data = json.loads(path.read_text())
        return cls(
            deck=data["deck"],
            started=data["started"],
            budget=data["budget"],
            phases=data["phases"],
            directory=progress_dir,
        )

    def elapsed(self, now: float | None = None) -> float:
        return (time.time() if now is None else now) - self.started

    def phase_durations(self, now: float | None = None) -> list[tuple[str, float, bool]]:
        """[(name, seconds, finished), ...] in order; the last phase is open."""
        now = time.time() if now is None else now
        out: list[tuple[str, float, bool]] = []
        for index, entry in enumerate(self.phases):
            end = self.phases[index + 1]["at"] if index + 1 < len(self.phases) else now
            out.append((entry["name"], end - entry["at"], index + 1 < len(self.phases)))
        return out


def _bar(fraction: float, width: int = BAR_WIDTH) -> str:
    fraction = max(0.0, min(1.0, fraction))
    filled = int(round(fraction * width))
    return "#" * filled + "." * (width - filled)


def expected_fraction_at(phase: str) -> float:
    """Share of the budget that should be spent by the time `phase` starts."""
    if phase not in PHASE_SHARE:
        return 0.0
    return sum(PHASE_SHARE[name] for name in PHASE_ORDER[: PHASE_ORDER.index(phase)])


def verdict(run: Run, current_phase: str, now: float | None = None) -> tuple[str, str]:
    """(state, advice) for the run's position against its budget.

    Drift is judged at the moment a phase *starts*, not at "now": time
    spent inside the current phase is that phase's own allocation being
    used, not evidence of falling behind. Comparing live elapsed against
    the expected-at-entry figure flags every run as behind the moment it
    starts working. Budget exhaustion is still judged live, because
    running out mid-phase matters immediately.
    """
    if run.budget is None:
        return ("untimed", "")
    if run.elapsed(now) >= run.budget:
        return (
            "OVER",
            "Stop adding. Do the final render, then report what exists and what you would have polished.",
        )

    entered_at = run.phases[-1]["at"] if run.phases else run.started
    used_at_entry = (entered_at - run.started) / run.budget
    expected = expected_fraction_at(current_phase)
    if used_at_entry > max(expected, 0.05) * DRIFT_TOLERANCE:
        return ("BEHIND", _catch_up_advice(current_phase, run.elapsed(now) / run.budget))
    return ("ON TRACK", "")


def _catch_up_advice(phase: str, used: float) -> str:
    """What to cut, specific to where the run is when it falls behind."""
    remaining = f"{(1 - used) * 100:.0f}% of budget left"
    advice = {
        "plan": "Cut the outline to the audience minimum and start coding.",
        "scaffold": "Nothing to cut here -- the overrun is upstream; keep moving.",
        "code": "Simplify the remaining segments: fewer parts per figure, reuse the established composition.",
        "validate": "Fix only what validate reports; do not polish while you are in here.",
        "render": "Render at -ql only; leave the full-quality pass for the end.",
        "review": "One round, final frames only -- skip contact sheets and skip re-review.",
        "finish": "Report now; list remaining polish as follow-ups instead of doing it.",
    }
    return f"{remaining}. {advice.get(phase, 'Reduce scope on the remaining phases.')}"


def status_line(run: Run, now: float | None = None) -> str:
    """The one-line bar plus a per-phase breakdown, for the agent to relay."""
    durations = run.phase_durations(now)
    current = durations[-1][0] if durations else "-"
    elapsed = run.elapsed(now)

    if run.budget is not None:
        fraction = elapsed / run.budget
        head = (
            f"{run.deck}  [{_bar(fraction)}]  {fraction * 100:.0f}%  "
            f"{format_duration(elapsed)} / {format_duration(run.budget)}  ({current})"
        )
    else:
        done = sum(1 for _, _, finished in durations if finished)
        head = (
            f"{run.deck}  [{_bar(done / len(PHASE_ORDER))}]  "
            f"{format_duration(elapsed)} elapsed  ({current})"
        )

    parts = [
        f"{'v' if finished else '>'} {name} {format_duration(seconds)}"
        for name, seconds, finished in durations
    ]
    lines = [head, "  " + "  ".join(parts)]

    state, advice = verdict(run, current, now)
    if state not in ("ON TRACK", "untimed"):
        lines.append(f"  {state} -- {advice}")
    return "\n".join(lines)


def start(deck: str, budget: str | None = None, progress_dir: Path = PROGRESS_DIR) -> Run:
    now = time.time()
    run = Run(
        deck=deck,
        started=now,
        budget=parse_budget(budget) if budget else None,
        phases=[{"name": PHASE_ORDER[0], "at": now}],
        directory=progress_dir,
    )
    run.save()
    return run


def mark_phase(deck: str, phase: str, progress_dir: Path = PROGRESS_DIR) -> Run:
    run = Run.load(deck, progress_dir)
    run.phases.append({"name": phase, "at": time.time()})
    run.save()
    return run


def final_report(run: Run, now: float | None = None) -> str:
    durations = run.phase_durations(now)
    total = run.elapsed(now)
    widest = max((len(name) for name, _, _ in durations), default=5)
    lines = [f"{run.deck} -- total {format_duration(total)}" + (f" of {format_duration(run.budget)} budget" if run.budget else "")]
    for name, seconds, _ in durations:
        share = seconds / total if total > 0 else 0.0
        lines.append(f"  {name:<{widest}}  {format_duration(seconds):>7}  {_bar(share, 10)}  {share * 100:.0f}%")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    usage = (
        "usage:\n"
        "  python -m open_manim_slides.progress start <Deck> [budget]\n"
        "  python -m open_manim_slides.progress phase <Deck> <phase>\n"
        "  python -m open_manim_slides.progress report <Deck>"
    )
    if len(args) < 2:
        print(usage, file=sys.stderr)
        return 2
    command, deck = args[0], args[1]
    try:
        if command == "start":
            run = start(deck, args[2] if len(args) > 2 else None)
            print(status_line(run))
        elif command == "phase":
            if len(args) < 3:
                print(usage, file=sys.stderr)
                return 2
            print(status_line(mark_phase(deck, args[2])))
        elif command == "report":
            print(final_report(Run.load(deck)))
        else:
            print(usage, file=sys.stderr)
            return 2
    except ProgressError as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
