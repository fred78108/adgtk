"""Tests for adgtk.cli.exp_cli — argument parsing and helper functions.

Tests the _parse_args function and the helper functions that implement
each sub-command, using mocks to avoid requiring a live project.

pytest test/cli/test_exp_cli.py
"""

import sys
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# _parse_args
# ---------------------------------------------------------------------------

def _parse(argv: list[str]):
    from adgtk.cli.exp_cli import _parse_args
    with patch.object(sys, "argv", ["adgtk"] + argv):
        return _parse_args()


def test_parse_no_args_command_is_none():
    args = _parse([])
    assert args.command is None


def test_parse_list_command():
    args = _parse(["list"])
    assert args.command == "list"


def test_parse_run_with_name():
    args = _parse(["run", "my_exp"])
    assert args.command == "run"
    assert args.name == "my_exp"
    assert args.n == 1


def test_parse_run_with_count():
    args = _parse(["run", "my_exp", "--n", "5"])
    assert args.n == 5


def test_parse_run_no_name():
    args = _parse(["run"])
    assert args.name is None


def test_parse_build_with_name():
    args = _parse(["build", "new_exp"])
    assert args.command == "build"
    assert args.name == "new_exp"


def test_parse_report_with_name():
    args = _parse(["report", "exp_a"])
    assert args.command == "report"
    assert args.name == "exp_a"


def test_parse_copy_with_source_and_dest():
    args = _parse(["copy", "old", "new"])
    assert args.command == "copy"
    assert args.source == "old"
    assert args.dest == "new"


def test_parse_stop():
    args = _parse(["stop"])
    assert args.command == "stop"


def test_parse_tasks_list():
    args = _parse(["tasks", "list"])
    assert args.command == "tasks"
    assert args.tasks_command == "list"


def test_parse_tasks_cleanup():
    args = _parse(["tasks", "cleanup"])
    assert args.command == "tasks"
    assert args.tasks_command == "cleanup"
    assert args.auto is False


def test_parse_tasks_cleanup_auto():
    args = _parse(["tasks", "cleanup", "--auto"])
    assert args.auto is True


# ---------------------------------------------------------------------------
# _list_experiments
# ---------------------------------------------------------------------------

def test_list_experiments_empty(capsys):
    from adgtk.cli.exp_cli import _list_experiments
    with patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        _list_experiments()
    out = capsys.readouterr().out
    assert "experiment name" in out


def test_list_experiments_with_entries(capsys):
    from adgtk.cli.exp_cli import _list_experiments
    from adgtk.tracking.structure import AvailableExperimentModel
    entries = [AvailableExperimentModel(name="exp_a", description="first exp")]
    with patch("adgtk.tracking.project.get_available_experiments", return_value=entries):
        _list_experiments()
    out = capsys.readouterr().out
    assert "exp_a" in out


# ---------------------------------------------------------------------------
# _copy_blueprint
# ---------------------------------------------------------------------------

def test_copy_blueprint_no_blueprints_found(capsys):
    from adgtk.cli.exp_cli import _copy_blueprint
    with patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        _copy_blueprint("old", "new")
    out = capsys.readouterr().out
    assert "No blueprints found" in out


def test_copy_blueprint_source_not_found(capsys, tmp_path):
    from adgtk.cli.exp_cli import _copy_blueprint
    from adgtk.tracking.structure import AvailableExperimentModel
    entries = [AvailableExperimentModel(name="other", description="other exp")]
    with patch("adgtk.tracking.project.get_available_experiments", return_value=entries), \
         patch("adgtk.utils.defaults.EXP_DEF_DIR", str(tmp_path)):
        _copy_blueprint("missing", "new_name")
    out = capsys.readouterr().out
    assert "not found" in out


def test_copy_blueprint_dest_already_exists(capsys, tmp_path):
    from adgtk.cli.exp_cli import _copy_blueprint
    from adgtk.tracking.structure import AvailableExperimentModel
    (tmp_path / "old.yaml").write_text("model: gpt-4")
    (tmp_path / "new.yaml").write_text("model: gpt-3.5")
    entries = [AvailableExperimentModel(name="old", description="")]
    with patch("adgtk.tracking.project.get_available_experiments", return_value=entries), \
         patch("adgtk.utils.defaults.EXP_DEF_DIR", str(tmp_path)):
        _copy_blueprint("old", "new")
    out = capsys.readouterr().out
    assert "already exists" in out


def test_copy_blueprint_empty_dest_name(capsys, tmp_path):
    from adgtk.cli.exp_cli import _copy_blueprint
    from adgtk.tracking.structure import AvailableExperimentModel
    (tmp_path / "old.yaml").write_text("model: gpt-4")
    entries = [AvailableExperimentModel(name="old", description="")]
    with patch("adgtk.tracking.project.get_available_experiments", return_value=entries), \
         patch("adgtk.utils.defaults.EXP_DEF_DIR", str(tmp_path)):
        _copy_blueprint("old", "")
    out = capsys.readouterr().out
    assert "cannot be empty" in out


def test_copy_blueprint_success(capsys, tmp_path):
    from adgtk.cli.exp_cli import _copy_blueprint
    from adgtk.tracking.structure import AvailableExperimentModel
    (tmp_path / "source_exp.yaml").write_text("model: gpt-4")
    entries = [AvailableExperimentModel(name="source_exp", description="")]
    with patch("adgtk.tracking.project.get_available_experiments", return_value=entries), \
         patch("adgtk.utils.defaults.EXP_DEF_DIR", str(tmp_path)):
        _copy_blueprint("source_exp", "dest_exp")
    out = capsys.readouterr().out
    assert "Copied" in out
    assert (tmp_path / "dest_exp.yaml").exists()


# ---------------------------------------------------------------------------
# _tasks_list
# ---------------------------------------------------------------------------

def test_tasks_list_empty(capsys):
    from adgtk.cli.exp_cli import _tasks_list
    with patch("adgtk.experiment.task_record.get_all_task_records", return_value=[]):
        _tasks_list()
    out = capsys.readouterr().out
    assert "No task records found" in out


def test_tasks_list_with_records(capsys):
    from adgtk.cli.exp_cli import _tasks_list
    from datetime import datetime
    record = MagicMock()
    record.task_id = "t001"
    record.status = "complete"
    record.experiment_name = "exp_a"
    record.started_at = datetime(2026, 1, 1, 10, 0, 0)
    with patch("adgtk.experiment.task_record.get_all_task_records",
               return_value=[record]):
        _tasks_list()
    out = capsys.readouterr().out
    assert "t001" in out
    assert "exp_a" in out


# ---------------------------------------------------------------------------
# _stop_experiment
# ---------------------------------------------------------------------------

def test_stop_experiment_no_active(capsys):
    from adgtk.cli.exp_cli import _stop_experiment
    with patch("adgtk.experiment.task_record.cleanup_orphaned_tasks"), \
         patch("adgtk.experiment.task_record.get_active_task_record",
               return_value=None):
        _stop_experiment()
    out = capsys.readouterr().out
    assert "No experiment is currently running" in out
