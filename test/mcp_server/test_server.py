"""Tests for adgtk.mcp_server.server — all MCP tool functions.

Each tool is called directly as a Python function (FastMCP's @mcp.tool()
returns the original function unchanged).  ADGTK module dependencies are
patched at their source; filesystem tools use monkeypatch.chdir(tmp_path).

pytest test/mcp_server/test_server.py
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from adgtk.mcp_server.server import (
    _to_dict,
    copy_experiment,
    export_results,
    generate_experiment_report,
    get_run_details,
    list_batches,
    list_components,
    list_datasets,
    list_experiments,
    list_runs,
    list_studies,
    project_status,
    run_batch,
    run_experiment,
    run_study,
    validate_results,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

class _Obj:
    """Plain object with public and private attrs for _to_dict testing."""
    def __init__(self):
        self.public = "yes"
        self._private = "hidden"


class _MockRun:
    """Minimal run object with a results_path attribute."""
    def __init__(self, results_path: str):
        self.results_path = results_path


# ─── _to_dict ─────────────────────────────────────────────────────────────────

def test_to_dict_pydantic_model():
    m = MagicMock()
    m.model_dump.return_value = {"key": "value"}
    result = _to_dict(m)
    assert result == {"key": "value"}
    m.model_dump.assert_called_once()


def test_to_dict_nested_dict_and_list():
    data = {"items": [1, "two", {"inner": 3}]}
    assert _to_dict(data) == {"items": [1, "two", {"inner": 3}]}


def test_to_dict_plain_object_excludes_private():
    result = _to_dict(_Obj())
    assert result == {"public": "yes"}
    assert "_private" not in result


def test_to_dict_primitive_passthrough():
    assert _to_dict(42) == 42
    assert _to_dict("hello") == "hello"
    assert _to_dict(None) is None


# ─── project_status ───────────────────────────────────────────────────────────

def test_project_status_valid():
    with patch("adgtk.cli.bootstrap.in_project", return_value=True):
        result = project_status()
    assert result["valid"] is True
    assert "project_dir" in result


def test_project_status_invalid():
    with patch("adgtk.cli.bootstrap.in_project", return_value=False):
        result = project_status()
    assert result["valid"] is False


# ─── list_experiments ─────────────────────────────────────────────────────────

def test_list_experiments_empty():
    with patch("adgtk.tracking.project.get_available_experiments", return_value=[]):
        result = list_experiments()
    assert result == []


def test_list_experiments_returns_dicts():
    exp = MagicMock()
    exp.model_dump.return_value = {"name": "exp1", "description": "desc"}
    with patch("adgtk.tracking.project.get_available_experiments", return_value=[exp]):
        result = list_experiments()
    assert result == [{"name": "exp1", "description": "desc"}]


# ─── run_experiment ───────────────────────────────────────────────────────────

def test_run_experiment_success():
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {"score": 0.9}
    mock_folders = MagicMock()
    mock_folders.root_dir = "/tmp/results/exp1/run-001"
    with patch("adgtk.experiment.runner.run_scenario",
               return_value=(mock_result, mock_folders)):
        result = run_experiment("exp1")
    assert result["status"] == "complete"
    assert result["experiment"] == "exp1"
    assert result["result"] == {"score": 0.9}


def test_run_experiment_file_not_found():
    with patch("adgtk.experiment.runner.run_scenario",
               side_effect=FileNotFoundError):
        result = run_experiment("missing")
    assert result["status"] == "error"
    assert "missing" in result["error"]


def test_run_experiment_generic_error():
    with patch("adgtk.experiment.runner.run_scenario",
               side_effect=RuntimeError("boom")):
        result = run_experiment("exp1")
    assert result["status"] == "error"
    assert "boom" in result["error"]


# ─── generate_experiment_report ───────────────────────────────────────────────

def test_generate_experiment_report_success():
    with patch(
        "adgtk.tracking.report.generate_experiment_report",
        return_value=("/reports/exp1.md", "/reports/exp1.csv"),
    ):
        result = generate_experiment_report("exp1")
    assert result["status"] == "complete"
    assert result["report_path"] == "/reports/exp1.md"
    assert result["csv_path"] == "/reports/exp1.csv"


def test_generate_experiment_report_error():
    with patch(
        "adgtk.tracking.report.generate_experiment_report",
        side_effect=ValueError("no runs"),
    ):
        result = generate_experiment_report("exp1")
    assert result["status"] == "error"
    assert "no runs" in result["error"]


# ─── copy_experiment ──────────────────────────────────────────────────────────

def test_copy_experiment_source_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "blueprints").mkdir()
    result = copy_experiment("nonexistent", "dest")
    assert result["status"] == "error"
    assert "nonexistent" in result["error"]


def test_copy_experiment_destination_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bp = tmp_path / "blueprints"
    bp.mkdir()
    (bp / "src.yaml").write_text("name: src")
    (bp / "dst.yaml").write_text("name: dst")
    result = copy_experiment("src", "dst")
    assert result["status"] == "error"
    assert "dst" in result["error"]


def test_copy_experiment_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bp = tmp_path / "blueprints"
    bp.mkdir()
    (bp / "src.yaml").write_text("name: src")
    result = copy_experiment("src", "dst")
    assert result["status"] == "complete"
    assert (bp / "dst.yaml").exists()


# ─── list_batches ─────────────────────────────────────────────────────────────

def test_list_batches_no_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert list_batches() == []


def test_list_batches_returns_sorted_stems(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    batches = tmp_path / "batches"
    batches.mkdir()
    (batches / "z_batch.yaml").write_text("")
    (batches / "a_batch.yaml").write_text("")
    result = list_batches()
    assert result == ["a_batch", "z_batch"]


# ─── run_batch ────────────────────────────────────────────────────────────────

def test_run_batch_success():
    with patch("adgtk.experiment.runner.run_batch", return_value=None):
        result = run_batch("mybatch")
    assert result == {"status": "complete", "batch": "mybatch"}


def test_run_batch_file_not_found():
    with patch("adgtk.experiment.runner.run_batch", side_effect=FileNotFoundError):
        result = run_batch("missing")
    assert result["status"] == "error"
    assert "missing" in result["error"]


def test_run_batch_generic_error():
    with patch("adgtk.experiment.runner.run_batch",
               side_effect=RuntimeError("fail")):
        result = run_batch("mybatch")
    assert result["status"] == "error"
    assert "fail" in result["error"]


# ─── list_runs ────────────────────────────────────────────────────────────────

def test_list_runs_no_filter():
    runs = [_MockRun("/results/exp1/run-001"), _MockRun("/results/exp2/run-001")]
    with patch("adgtk.tracking.runs.get_runs", return_value=runs) as mock_get:
        result = list_runs()
    mock_get.assert_called_once_with(None)
    assert len(result) == 2
    assert result[0]["results_path"] == "/results/exp1/run-001"


def test_list_runs_filtered():
    runs = [_MockRun("/results/exp1/run-001")]
    with patch("adgtk.tracking.runs.get_runs", return_value=runs) as mock_get:
        result = list_runs("exp1")
    mock_get.assert_called_once_with("exp1")
    assert len(result) == 1


# ─── get_run_details ──────────────────────────────────────────────────────────

def test_get_run_details_missing_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = get_run_details("exp1", "run-001")
    assert result["status"] == "error"


def test_get_run_details_with_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "results" / "exp1" / "run-001"
    run_dir.mkdir(parents=True)
    (run_dir / "results.yaml").write_text("score: 0.9\n")
    (run_dir / "run.exp.config.yaml").write_text("name: exp1\n")
    result = get_run_details("exp1", "run-001")
    assert result["status"] == "complete"
    assert result["results"] == {"score": 0.9}
    assert result["config"] == {"name": "exp1"}


def test_get_run_details_dir_exists_no_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "results" / "exp1" / "run-001").mkdir(parents=True)
    result = get_run_details("exp1", "run-001")
    assert result["status"] == "complete"
    assert "results" not in result
    assert "config" not in result


# ─── export_results ───────────────────────────────────────────────────────────

def test_export_results_json():
    runs = [_MockRun("/results/exp1/run-001")]
    with patch("adgtk.tracking.runs.get_runs", return_value=runs):
        result = export_results("exp1", format="json")
    assert result["status"] == "complete"
    assert result["format"] == "json"
    assert isinstance(result["data"], list)
    assert result["data"][0]["results_path"] == "/results/exp1/run-001"


def test_export_results_csv():
    runs = [_MockRun("/results/exp1/run-001")]
    with patch("adgtk.tracking.runs.get_runs", return_value=runs):
        result = export_results("exp1", format="csv")
    assert result["status"] == "complete"
    assert result["format"] == "csv"
    assert "results_path" in result["data"]


# ─── validate_results ─────────────────────────────────────────────────────────

def test_validate_results_healthy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]):
        result = validate_results()
    assert result["healthy"] is True
    assert result["orphaned_folders"] == []
    assert result["incomplete_runs"] == []
    assert result["missing_folders"] == []


def test_validate_results_orphaned_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "results" / "exp1" / "run-001").mkdir(parents=True)
    with patch("adgtk.tracking.runs.get_runs", return_value=[]):
        result = validate_results()
    assert not result["healthy"]
    assert any("run-001" in p for p in result["orphaned_folders"])


def test_validate_results_missing_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run = _MockRun(str(tmp_path / "results" / "exp1" / "run-001"))
    with patch("adgtk.tracking.runs.get_runs", return_value=[run]):
        result = validate_results()
    assert not result["healthy"]
    assert len(result["missing_folders"]) == 1


def test_validate_results_incomplete_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "results" / "exp1" / "run-001"
    run_dir.mkdir(parents=True)
    run = _MockRun(str(run_dir))
    with patch("adgtk.tracking.runs.get_runs", return_value=[run]):
        result = validate_results()
    assert not result["healthy"]
    assert len(result["incomplete_runs"]) == 1


# ─── list_studies ─────────────────────────────────────────────────────────────

def test_list_studies():
    with patch(
        "adgtk.experiment.study.builder.list_study_blueprints",
        return_value=["study_a", "study_b"],
    ):
        result = list_studies()
    assert result == ["study_a", "study_b"]


# ─── run_study ────────────────────────────────────────────────────────────────

def test_run_study_success():
    with patch(
        "adgtk.experiment.study.report.generate_study_report",
        return_value=("/reports/study_a.md", "/reports/study_a.csv"),
    ):
        result = run_study("study_a")
    assert result["status"] == "complete"
    assert result["report_path"] == "/reports/study_a.md"
    assert result["csv_path"] == "/reports/study_a.csv"


def test_run_study_error():
    with patch(
        "adgtk.experiment.study.report.generate_study_report",
        side_effect=ValueError("missing data"),
    ):
        result = run_study("study_a")
    assert result["status"] == "error"
    assert "missing data" in result["error"]


# ─── list_components ──────────────────────────────────────────────────────────

def test_list_components_no_filter():
    entry = MagicMock()
    entry.model_dump.return_value = {"name": "c1"}
    with patch("adgtk.factory.component.list_entries",
               return_value=[entry]) as mock_fn:
        result = list_components()
    mock_fn.assert_called_once_with(group=None, tags=None)
    assert result == [{"name": "c1"}]


def test_list_components_with_group():
    with patch("adgtk.factory.component.list_entries",
               return_value=[]) as mock_fn:
        list_components(group="scenario")
    mock_fn.assert_called_once_with(group="scenario", tags=None)


# ─── list_datasets ────────────────────────────────────────────────────────────

def test_list_datasets_success():
    mock_mgr = MagicMock()
    mock_mgr.get_file_ids_only.return_value = ["ds1", "ds2"]
    with patch("adgtk.data.dataset.DatasetManager", return_value=mock_mgr):
        result = list_datasets()
    assert result == ["ds1", "ds2"]


def test_list_datasets_error():
    with patch("adgtk.data.dataset.DatasetManager",
               side_effect=RuntimeError("no db")):
        result = list_datasets()
    assert len(result) == 1
    assert "no db" in result[0]
