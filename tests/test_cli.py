"""Tests for the project bootstrap CLI (`open-manim-slides init|doctor`)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from open_manim_slides import cli


def test_skills_source_contains_create_deck():
    source = cli._skills_source()
    assert (source / "create-deck" / "SKILL.md").is_file()


def test_init_writes_the_expected_tree(tmp_path):
    written = cli.init_project(tmp_path)

    skill = tmp_path / ".agents" / "skills" / "create-deck"
    assert (skill / "SKILL.md").is_file()
    assert (skill / "references" / "motion-recipes.md").is_file()
    assert (tmp_path / "decks").is_dir()
    assert (tmp_path / "AGENTS.md").is_file()
    assert any("AGENTS.md" in item for item in written)


def test_init_links_claude_projection_to_the_canonical_skill(tmp_path):
    cli.init_project(tmp_path)

    projection = tmp_path / ".claude" / "skills" / "create-deck"
    assert (projection / "SKILL.md").is_file()
    # Whether it is a symlink or a copy is platform-dependent; that it
    # resolves to the same content is not.
    canonical = tmp_path / ".agents" / "skills" / "create-deck" / "SKILL.md"
    assert (projection / "SKILL.md").read_text() == canonical.read_text()


def test_claude_md_mirrors_agents_md(tmp_path):
    cli.init_project(tmp_path)
    assert (tmp_path / "CLAUDE.md").read_text() == (tmp_path / "AGENTS.md").read_text()


def test_generated_agents_md_stays_small(tmp_path):
    """A generated project must not inherit the dev repo's 278-line AGENTS.md.

    That file is auto-loaded into an agent's context by the harness, so
    shipping the framework's internals in it would put every generated
    project back in the state a test run exists to avoid.
    """
    cli.init_project(tmp_path)
    lines = (tmp_path / "AGENTS.md").read_text().splitlines()
    assert len(lines) < 80
    assert "src/open_manim_slides" not in (tmp_path / "AGENTS.md").read_text()


def test_init_refuses_to_overwrite_without_force(tmp_path):
    cli.init_project(tmp_path)
    with pytest.raises(FileExistsError):
        cli.init_project(tmp_path)


def test_init_force_overwrites(tmp_path):
    cli.init_project(tmp_path)
    stray = tmp_path / ".agents" / "skills" / "create-deck" / "stray.md"
    stray.write_text("left over from a previous run")

    cli.init_project(tmp_path, force=True)
    assert not stray.exists()


def test_main_init_returns_zero(tmp_path, capsys):
    assert cli.main(["init", str(tmp_path)]) == 0
    assert "created" in capsys.readouterr().out


def test_main_init_reports_conflict_without_traceback(tmp_path, capsys):
    cli.main(["init", str(tmp_path)])
    assert cli.main(["init", str(tmp_path)]) == 1
    assert "--force" in capsys.readouterr().err


def test_check_import_reports_missing_module():
    ok, detail = cli._check_import("a_module_that_is_not_installed")
    assert ok is False
    assert "ModuleNotFoundError" in detail


def test_check_import_reports_present_module():
    ok, _ = cli._check_import("json")
    assert ok is True


def test_doctor_returns_an_exit_code(capsys):
    code = cli.doctor()
    out = capsys.readouterr().out
    assert code in (0, 1)
    assert "required:" in out and "manim" in out


def test_importing_the_package_does_not_import_manim():
    """The whole reason `__init__` is lazy.

    `open-manim-slides doctor` has to run on a machine where manim failed to
    build -- the most likely state of a first install, since manimpango
    compiles against system cairo/pango. Eager re-exports made the
    diagnostic crash with the very error it exists to report.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import open_manim_slides, sys; "
            "print('manim' in sys.modules or 'manim.__init__' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_lazy_exports_still_resolve():
    import open_manim_slides

    assert open_manim_slides.Slide.__name__ == "Slide"
    assert callable(open_manim_slides.heading)
    with pytest.raises(AttributeError):
        open_manim_slides.no_such_name
