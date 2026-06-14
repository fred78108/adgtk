"""Tests for adgtk.tracking.base — MetricTracker.

Covers uncovered branches: error paths, clear/reset, save_data, export.

pytest test/tracking/test_base.py
"""

import os
import csv
import pytest
from unittest.mock import patch
from adgtk.tracking.base import MetricTracker
from adgtk.tracking.structure import ExperimentRunFolders


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker():
    return MetricTracker(name="test", purpose="other")


def _make_folders(tmp_path) -> ExperimentRunFolders:
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


# ---------------------------------------------------------------------------
# register_metric
# ---------------------------------------------------------------------------

def test_register_metric_creates_entry(tracker):
    assert tracker.register_metric("loss") is True
    assert "loss" in tracker.metrics


def test_register_metric_duplicate_returns_false(tracker):
    tracker.register_metric("loss")
    assert tracker.register_metric("loss") is False


def test_register_metric_with_metadata(tracker):
    tracker.register_metric("loss", metadata={"unit": "nats"})
    assert tracker.metadata["loss"] == {"unit": "nats"}


def test_register_metric_metadata_not_overwritten(tracker):
    tracker.register_metric("loss", metadata={"unit": "nats"})
    tracker.register_metric("loss", metadata={"unit": "bits"})
    assert tracker.metadata["loss"] == {"unit": "nats"}


def test_register_metric_no_metadata_sets_empty_dict(tracker):
    tracker.register_metric("loss")
    assert tracker.metadata["loss"] == {}


# ---------------------------------------------------------------------------
# add_data / add_raw_data
# ---------------------------------------------------------------------------

def test_add_data_auto_creates_metric(tracker):
    tracker.add_data("new_metric", 1.0)
    assert tracker.metrics["new_metric"] == [1.0]


def test_add_raw_data(tracker):
    tracker.register_metric("m")
    tracker.add_raw_data("m", [1, 2, 3])
    assert tracker.metrics["m"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# metric_exists / metric_labels
# ---------------------------------------------------------------------------

def test_metric_exists_true(tracker):
    tracker.register_metric("acc")
    assert tracker.metric_exists("acc") is True


def test_metric_exists_false(tracker):
    assert tracker.metric_exists("missing") is False


def test_metric_labels(tracker):
    tracker.register_metric("a")
    tracker.register_metric("b")
    labels = tracker.metric_labels()
    assert "a" in labels
    assert "b" in labels


# ---------------------------------------------------------------------------
# remove_metric
# ---------------------------------------------------------------------------

def test_remove_metric_removes_data_and_metadata(tracker):
    tracker.register_metric("loss", metadata={"unit": "nats"})
    tracker.add_data("loss", 0.5)
    tracker.remove_metric("loss")
    assert "loss" not in tracker.metrics
    assert "loss" not in tracker.metadata


def test_remove_nonexistent_metric_does_not_raise(tracker):
    tracker.remove_metric("does_not_exist")


# ---------------------------------------------------------------------------
# get_latest_value
# ---------------------------------------------------------------------------

def test_get_latest_value_returns_last(tracker):
    tracker.register_metric("x")
    tracker.add_data("x", 1.0)
    tracker.add_data("x", 2.0)
    assert tracker.get_latest_value("x") == 2.0


def test_get_latest_value_empty_returns_zero(tracker):
    tracker.register_metric("x")
    assert tracker.get_latest_value("x") == 0


def test_get_latest_value_invalid_raises(tracker):
    with pytest.raises(KeyError):
        tracker.get_latest_value("missing")


# ---------------------------------------------------------------------------
# get_latest_distribution
# ---------------------------------------------------------------------------

def test_get_latest_distribution_returns_last(tracker):
    tracker.register_metric("dist")
    tracker.add_data("dist", [1, 2, 3])
    result = tracker.get_latest_distribution("dist")
    assert result == [1, 2, 3]


def test_get_latest_distribution_empty(tracker):
    import numpy as np
    tracker.register_metric("dist")
    result = tracker.get_latest_distribution("dist")
    assert isinstance(result, np.ndarray)


def test_get_latest_distribution_invalid_raises(tracker):
    with pytest.raises(KeyError):
        tracker.get_latest_distribution("missing")


# ---------------------------------------------------------------------------
# get_average / get_sum
# ---------------------------------------------------------------------------

def test_get_average_computes_correctly(tracker):
    tracker.register_metric("v")
    tracker.add_data("v", 2.0)
    tracker.add_data("v", 4.0)
    assert tracker.get_average("v") == 3.0


def test_get_average_empty_returns_zero(tracker):
    tracker.register_metric("v")
    assert tracker.get_average("v") == 0


def test_get_average_invalid_raises(tracker):
    with pytest.raises(KeyError):
        tracker.get_average("missing")


def test_get_sum_computes_correctly(tracker):
    tracker.register_metric("v")
    tracker.add_data("v", 1.0)
    tracker.add_data("v", 2.0)
    assert tracker.get_sum("v") == 3.0


def test_get_sum_empty_returns_zero(tracker):
    tracker.register_metric("v")
    assert tracker.get_sum("v") == 0


def test_get_sum_invalid_raises(tracker):
    with pytest.raises(KeyError):
        tracker.get_sum("missing")


# ---------------------------------------------------------------------------
# clear_metric / clear_results / reset
# ---------------------------------------------------------------------------

def test_clear_metric_empties_one(tracker):
    tracker.register_metric("a")
    tracker.add_data("a", 1.0)
    tracker.clear_metric("a")
    assert tracker.metrics["a"] == []


def test_clear_results_empties_all(tracker):
    tracker.register_metric("a")
    tracker.register_metric("b")
    tracker.add_data("a", 1.0)
    tracker.add_data("b", 2.0)
    tracker.clear_results()
    assert tracker.metrics["a"] == []
    assert tracker.metrics["b"] == []


def test_reset_removes_all_metrics(tracker):
    tracker.register_metric("a")
    tracker.register_metric("b")
    tracker.reset()
    assert tracker.metrics == {}


# ---------------------------------------------------------------------------
# measurement_count
# ---------------------------------------------------------------------------

def test_measurement_count(tracker):
    tracker.register_metric("m")
    tracker.add_data("m", 1.0)
    tracker.add_data("m", 2.0)
    assert tracker.measurement_count("m") == 2


def test_measurement_count_invalid_raises(tracker):
    with pytest.raises(KeyError):
        tracker.measurement_count("missing")


# ---------------------------------------------------------------------------
# get_all_data
# ---------------------------------------------------------------------------

def test_get_all_data_returns_copy(tracker):
    tracker.register_metric("m")
    tracker.add_data("m", 1.0)
    data = tracker.get_all_data("m")
    data.append(999)
    assert tracker.metrics["m"] == [1.0]


def test_get_all_data_invalid_raises(tracker):
    with pytest.raises(KeyError):
        tracker.get_all_data("missing")


# ---------------------------------------------------------------------------
# get_metadata
# ---------------------------------------------------------------------------

def test_get_metadata_returns_copy(tracker):
    tracker.register_metric("m", metadata={"k": "v"})
    meta = tracker.get_metadata("m")
    assert meta == {"k": "v"}
    meta["k"] = "changed"
    assert tracker.metadata["m"]["k"] == "v"


def test_get_metadata_missing_returns_empty(tracker):
    result = tracker.get_metadata("nonexistent")
    assert result == {}


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------

def test_save_data_writes_csv(tmp_path):
    folders = _make_folders(tmp_path)
    t = MetricTracker(name="mytracker", purpose="other")
    t.register_metric("loss")
    t.add_data("loss", 0.5)
    t.add_data("loss", 0.3)

    with patch("adgtk.tracking.base.observations"):
        t.save_data(folders)

    csv_path = os.path.join(folders.metrics, "mytracker.loss.csv")
    assert os.path.exists(csv_path)
    with open(csv_path, newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["0.5", "0.3"]


def test_save_data_empty_metric_writes_empty_row(tmp_path):
    folders = _make_folders(tmp_path)
    t = MetricTracker(name="t", purpose="other")
    t.register_metric("empty_metric")

    with patch("adgtk.tracking.base.observations"):
        t.save_data(folders)

    csv_path = os.path.join(folders.metrics, "t.empty_metric.csv")
    assert os.path.exists(csv_path)


# ---------------------------------------------------------------------------
# export_last_val_to_dict
# ---------------------------------------------------------------------------

def test_export_last_val_to_dict(tracker):
    tracker.register_metric("a")
    tracker.register_metric("b")
    tracker.add_data("a", 10.0)
    tracker.add_data("a", 20.0)
    tracker.add_data("b", 5.0)
    result = tracker.export_last_val_to_dict()
    assert result["a"] == 20.0
    assert result["b"] == 5.0


def test_export_last_val_empty_metric(tracker):
    tracker.register_metric("x")
    result = tracker.export_last_val_to_dict()
    assert result["x"] == 0
