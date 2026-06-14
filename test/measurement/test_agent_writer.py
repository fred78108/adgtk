"""Tests for adgtk.measurements.agent_writer — AgentWriter and track_step.

pytest test/measurement/test_agent_writer.py
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from adgtk.measurements.agent_writer import AgentWriter, track_step
from adgtk.tracking.structure import ExperimentRunFolders


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def folders(tmp_path) -> ExperimentRunFolders:
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir()
    return ExperimentRunFolders(
        log_dir=str(tmp_path / "logs"),
        datasets=str(tmp_path / "datasets"),
        metrics=str(metrics_dir),
        images=str(tmp_path / "images"),
        other=str(tmp_path / "other"),
        conclusion=str(tmp_path / "conclusion"),
        root_dir=str(tmp_path),
        experiment_name="test_exp",
        common=str(tmp_path / "common"),
        model_dir=str(tmp_path / "models"),
        train_log_dir=str(tmp_path / "train_logs"),
        llm_dir=str(tmp_path / "llm"),
    )


@pytest.fixture
def writer(folders) -> AgentWriter:
    return AgentWriter(folders)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_writer_init(writer):
    assert writer.step_count() == 0
    assert writer.tool_distribution() == {}


def test_writer_custom_name(folders):
    w = AgentWriter(folders, name="custom")
    assert w._tracker.name == "custom"


# ---------------------------------------------------------------------------
# log_step
# ---------------------------------------------------------------------------

def test_log_step_increments_step_count(writer):
    writer.log_step()
    assert writer.step_count() == 1
    writer.log_step()
    assert writer.step_count() == 2


def test_log_step_records_latency(writer):
    writer.log_step(latency=1.5)
    assert writer._tracker.get_latest_value("latency") == 1.5


def test_log_step_records_tokens(writer):
    writer.log_step(tokens_in=100, tokens_out=50)
    assert writer._tracker.get_latest_value("tokens_in") == 100.0
    assert writer._tracker.get_latest_value("tokens_out") == 50.0


def test_log_step_records_error(writer):
    writer.log_step(error=True)
    assert writer._tracker.get_latest_value("error") == 1.0


def test_log_step_no_error_records_zero(writer):
    writer.log_step()
    assert writer._tracker.get_latest_value("error") == 0.0


def test_log_step_omitted_fields_not_stored(writer):
    writer.log_step()
    assert writer._tracker.measurement_count("latency") == 0
    assert writer._tracker.measurement_count("tokens_in") == 0


# ---------------------------------------------------------------------------
# log_tool_call
# ---------------------------------------------------------------------------

def test_log_tool_call_records_tool_count(writer):
    writer.log_tool_call("search")
    assert writer._tracker.measurement_count("tool_call_count") == 1


def test_log_tool_call_records_success(writer):
    writer.log_tool_call("search", success=True)
    assert writer._tracker.get_latest_value("tool.search") == 1.0


def test_log_tool_call_records_failure(writer):
    writer.log_tool_call("search", success=False)
    assert writer._tracker.get_latest_value("tool.search") == 0.0


def test_log_tool_call_updates_distribution(writer):
    writer.log_tool_call("search")
    writer.log_tool_call("search")
    writer.log_tool_call("bash")
    dist = writer.tool_distribution()
    assert dist["search"] == 2
    assert dist["bash"] == 1


def test_log_tool_call_multiple_tools(writer):
    writer.log_tool_call("read")
    writer.log_tool_call("write")
    assert writer._tracker.metric_exists("tool.read")
    assert writer._tracker.metric_exists("tool.write")


# ---------------------------------------------------------------------------
# log_outcome
# ---------------------------------------------------------------------------

def test_log_outcome_records_success(writer):
    writer.log_outcome(success=True)
    assert writer._tracker.get_latest_value("success") == 1.0


def test_log_outcome_records_failure(writer):
    writer.log_outcome(success=False)
    assert writer._tracker.get_latest_value("success") == 0.0


def test_log_outcome_records_goal_completion(writer):
    writer.log_outcome(success=True, goal_completion=0.75)
    assert writer._tracker.get_latest_value("goal_completion") == 0.75


def test_log_outcome_first_attempt_success_recorded_once(writer):
    writer.log_outcome(success=True)
    writer.log_outcome(success=False)
    assert writer._tracker.measurement_count("first_attempt_success") == 1
    assert writer._tracker.get_all_data("first_attempt_success")[0] == 1.0


def test_log_outcome_retry_count(writer):
    writer.log_outcome(success=False)
    writer.log_outcome(success=True)
    data = writer._tracker.get_all_data("retry_count")
    assert data[0] == 0.0
    assert data[1] == 1.0


def test_log_outcome_path_efficiency_with_steps(writer):
    writer.log_step()
    writer.log_step()
    writer.log_outcome(success=True, optimal_steps=1)
    eff = writer._tracker.get_latest_value("path_efficiency")
    assert eff == 0.5


def test_log_outcome_path_efficiency_capped_at_one(writer):
    writer.log_step()
    writer.log_outcome(success=True, optimal_steps=10)
    eff = writer._tracker.get_latest_value("path_efficiency")
    assert eff == 1.0


def test_log_outcome_no_path_efficiency_without_optimal_steps(writer):
    writer.log_step()
    writer.log_outcome(success=True)
    assert writer._tracker.measurement_count("path_efficiency") == 0


def test_log_outcome_no_path_efficiency_without_steps(writer):
    writer.log_outcome(success=True, optimal_steps=5)
    assert writer._tracker.measurement_count("path_efficiency") == 0


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------

def test_save_writes_csv_files(writer, folders):
    writer.log_step(latency=1.0)
    writer.log_outcome(success=True)
    with patch("adgtk.tracking.base.observations"):
        writer.save()
    assert any(f.endswith(".csv") for f in os.listdir(folders.metrics))


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def test_summary_includes_scalar_metrics(writer):
    writer.log_step(latency=2.0)
    s = writer.summary()
    assert "latency" in s
    assert s["latency"] == 2.0


def test_summary_includes_step_count(writer):
    writer.log_step()
    writer.log_step()
    s = writer.summary()
    assert s["total_steps"] == 2


def test_summary_includes_tool_info(writer):
    writer.log_tool_call("bash")
    s = writer.summary()
    assert s["tool_unique_count"] == 1
    assert s["tool_distribution"]["bash"] == 1


def test_summary_empty_writer(writer):
    s = writer.summary()
    assert s["total_steps"] == 0
    assert s["tool_unique_count"] == 0


# ---------------------------------------------------------------------------
# track_step decorator
# ---------------------------------------------------------------------------

def test_track_step_records_latency(writer):
    @track_step(writer)
    def do_work():
        return 42

    result = do_work()
    assert result == 42
    assert writer.step_count() == 1
    assert writer._tracker.measurement_count("latency") == 1


def test_track_step_records_error_on_exception(writer):
    @track_step(writer)
    def failing():
        raise ValueError("oops")

    with pytest.raises(ValueError):
        failing()

    assert writer._tracker.get_latest_value("error") == 1.0


def test_track_step_no_error_logging(writer):
    @track_step(writer, log_errors=False)
    def failing():
        raise ValueError("oops")

    with pytest.raises(ValueError):
        failing()

    assert writer._tracker.get_latest_value("error") == 0.0


def test_track_step_preserves_function_name(writer):
    @track_step(writer)
    def my_special_function():
        pass

    assert my_special_function.__name__ == "my_special_function"
