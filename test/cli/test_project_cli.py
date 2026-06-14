"""Tests for adgtk.cli.project_cli — project scaffold CLI.

pytest test/cli/test_project_cli.py
"""

import os
import sys
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------

def _parse(argv: list[str]):
    from adgtk.cli.project_cli import _parse_args
    with patch.object(sys, "argv", ["adgtk-project"] + argv):
        return _parse_args()


def test_parse_no_args():
    args = _parse([])
    assert args.command is None


def test_parse_create():
    args = _parse(["create", "myproject"])
    assert args.command == "create"
    assert args.name == "myproject"


def test_parse_list():
    args = _parse(["list"])
    assert args.command == "list"


def test_parse_info():
    args = _parse(["info"])
    assert args.command == "info"


def test_parse_install_skills_default():
    args = _parse(["install-skills"])
    assert args.command == "install-skills"
    assert args.output_dir == ".claude/skills"


def test_parse_install_skills_custom_dir():
    args = _parse(["install-skills", "--output-dir", "/tmp/skills"])
    assert args.output_dir == "/tmp/skills"


# ---------------------------------------------------------------------------
# _build_project_folders
# ---------------------------------------------------------------------------

def test_build_project_folders_creates_dirs(tmp_path):
    from adgtk.cli.project_cli import _build_project_folders
    _build_project_folders(str(tmp_path))
    assert any(os.path.isdir(os.path.join(tmp_path, d))
               for d in os.listdir(tmp_path))


# ---------------------------------------------------------------------------
# _create_project
# ---------------------------------------------------------------------------

def test_create_project_creates_directory(tmp_path):
    from adgtk.cli.project_cli import _create_project
    target = str(tmp_path / "new_proj")
    with patch("adgtk.cli.project_cli.in_project", return_value=False):
        _create_project(target)
    assert os.path.isdir(target)


def test_create_project_inside_project_exits(capsys):
    from adgtk.cli.project_cli import _create_project
    with patch("adgtk.cli.project_cli.in_project", return_value=True), \
         pytest.raises(SystemExit) as exc:
        _create_project("anything")
    assert exc.value.code == 1


def test_create_project_existing_path_exits(tmp_path, capsys):
    from adgtk.cli.project_cli import _create_project
    existing = tmp_path / "exists"
    existing.mkdir()
    with patch("adgtk.cli.project_cli.in_project", return_value=False), \
         pytest.raises(SystemExit) as exc:
        _create_project(str(existing))
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "already exists" in out


# ---------------------------------------------------------------------------
# _list_projects
# ---------------------------------------------------------------------------

def test_list_projects_with_projects(tmp_path, capsys, monkeypatch):
    from adgtk.cli.project_cli import _list_projects
    monkeypatch.chdir(tmp_path)
    (tmp_path / "proj_a").mkdir()
    with patch("adgtk.cli.project_cli.is_project", side_effect=lambda p: p == "proj_a"):
        _list_projects()
    out = capsys.readouterr().out
    assert "proj_a" in out


def test_list_projects_none_found(tmp_path, capsys, monkeypatch):
    from adgtk.cli.project_cli import _list_projects
    monkeypatch.chdir(tmp_path)
    with patch("adgtk.cli.project_cli.is_project", return_value=False):
        _list_projects()
    out = capsys.readouterr().out
    assert "none found" in out.lower()


# ---------------------------------------------------------------------------
# _project_info
# ---------------------------------------------------------------------------

def test_project_info_valid_project(tmp_path, capsys, monkeypatch):
    from adgtk.cli.project_cli import _project_info
    from adgtk.cli.constants import BOOT_FILENAME
    monkeypatch.chdir(tmp_path)
    (tmp_path / BOOT_FILENAME).write_text("")
    results = tmp_path / "results"
    results.mkdir()
    with patch("adgtk.cli.project_cli.EXP_RESULTS_FOLDER", str(results)):
        _project_info()
    out = capsys.readouterr().out
    assert "valid project" in out


def test_project_info_not_a_project(tmp_path, capsys, monkeypatch):
    from adgtk.cli.project_cli import _project_info
    monkeypatch.chdir(tmp_path)
    with patch("adgtk.cli.project_cli.EXP_RESULTS_FOLDER", str(tmp_path / "nope")):
        _project_info()
    out = capsys.readouterr().out
    assert "not a project" in out


# ---------------------------------------------------------------------------
# _install_skills
# ---------------------------------------------------------------------------

def test_install_skills_copies_file(tmp_path, capsys):
    from adgtk.cli.project_cli import _install_skills
    with patch("adgtk.cli.project_cli.files") as mock_files:
        mock_skill = mock_files.return_value.joinpath.return_value
        mock_skill.__str__ = lambda self: str(tmp_path / "adgtk.md")
        (tmp_path / "adgtk.md").write_text("# skill content")
        dest_dir = str(tmp_path / "out")
        with patch("shutil.copy2") as mock_copy:
            _install_skills(dest_dir)
        mock_copy.assert_called_once()
    out = capsys.readouterr().out
    assert "Installed" in out
