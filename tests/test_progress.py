from pathlib import Path

import pytest

from open_manim_slides.progress import (
    ProgressError,
    Run,
    expected_fraction_at,
    final_report,
    format_duration,
    main,
    mark_phase,
    parse_budget,
    start,
    status_line,
    verdict,
)


def _run(phases: list[tuple[str, float]], budget: int | None = 1200, started: float = 1000.0) -> Run:
    return Run(
        deck="Deck",
        started=started,
        budget=budget,
        phases=[{"name": name, "at": started + offset} for name, offset in phases],
    )


@pytest.mark.parametrize(
    ("text", "seconds"),
    [("20m", 1200), ("90s", 90), ("1h30m", 5400), ("2h", 7200), ("15", 900), ("1.5", 90)],
)
def test_parse_budget_accepts_the_forms_a_person_would_type(text, seconds):
    assert parse_budget(text) == seconds


def test_parse_budget_rejects_nonsense():
    with pytest.raises(ProgressError, match="Could not read a duration"):
        parse_budget("soon")


@pytest.mark.parametrize(
    ("seconds", "text"), [(45, "45s"), (60, "1m00s"), (330, "5m30s"), (3600, "1h00m"), (5430, "1h30m")]
)
def test_format_duration(seconds, text):
    assert format_duration(seconds) == text


def test_expected_fraction_is_cumulative_and_starts_at_zero():
    assert expected_fraction_at("plan") == 0.0
    assert expected_fraction_at("code") == pytest.approx(0.14)
    assert expected_fraction_at("finish") == pytest.approx(0.90)


def test_time_spent_inside_a_phase_is_not_drift():
    """The phase's own allocation being used is not evidence of falling
    behind; judging live elapsed against expected-at-entry would flag
    every run the moment it started working."""
    run = _run([("plan", 0), ("scaffold", 130), ("code", 150)])

    state, _ = verdict(run, "code", now=1000 + 330)

    assert state == "ON TRACK"


def test_entering_a_phase_late_is_drift():
    run = _run([("plan", 0), ("scaffold", 200), ("code", 240), ("validate", 800), ("render", 930), ("review", 980)])

    state, advice = verdict(run, "review", now=1000 + 1010)

    assert state == "BEHIND"
    assert "skip re-review" in advice


def test_exhausted_budget_is_reported_live_not_at_the_next_boundary():
    run = _run([("plan", 0), ("code", 300)])

    state, advice = verdict(run, "code", now=1000 + 1300)

    assert state == "OVER"
    assert "Stop adding" in advice


def test_a_run_without_a_budget_is_never_judged():
    run = _run([("plan", 0), ("code", 300)], budget=None)

    assert verdict(run, "code", now=1000 + 99_999)[0] == "untimed"


def test_status_line_shows_budget_use_when_budgeted():
    line = status_line(_run([("plan", 0), ("code", 150)]), now=1000 + 330)

    assert "5m30s / 20m00s" in line
    assert "28%" in line


def test_status_line_falls_back_to_elapsed_when_untimed():
    line = status_line(_run([("plan", 0), ("code", 150)], budget=None), now=1000 + 330)

    assert "5m30s elapsed" in line
    assert "/" not in line.splitlines()[0]


def test_status_line_marks_finished_and_current_phases():
    line = status_line(_run([("plan", 0), ("code", 150)]), now=1000 + 330)

    assert "v plan" in line
    assert "> code" in line


def test_start_then_phase_round_trips_through_disk(tmp_path: Path):
    start("Deck", "20m", progress_dir=tmp_path)
    run = mark_phase("Deck", "code", progress_dir=tmp_path)

    assert run.budget == 1200
    assert [entry["name"] for entry in run.phases] == ["plan", "code"]
    assert Run.load("Deck", progress_dir=tmp_path).budget == 1200


def test_phase_without_a_started_run_says_so(tmp_path: Path):
    with pytest.raises(ProgressError, match="No run in progress"):
        mark_phase("Ghost", "code", progress_dir=tmp_path)


def test_final_report_breaks_total_down_by_phase():
    text = final_report(_run([("plan", 0), ("code", 150), ("review", 470)]), now=1000 + 790)

    assert "total 13m10s of 20m00s budget" in text
    assert "plan" in text and "code" in text and "review" in text


def test_main_rejects_wrong_arg_count(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
