"""Tests for adgtk.tracking.runs — the per-run registry.

Uses monkeypatch to redirect TRACKING_FOLDER to a temp dir and resets
module-level state between tests.

pytest test/tracking/test_runs.py
"""

import json
import os
import pytest
from adgtk.tracking import runs as run_registry
from adgtk.tracking.structure import RunEntryModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_runs_state(tmp_path, monkeypatch):
    monkeypatch.setattr(run_registry, "TRACKING_FOLDER", str(tmp_path))
    run_registry._runs.clear()
    run_registry._loaded = False
    yield
    run_registry._runs.clear()
    run_registry._loaded = False


def _make_entry(
    run_id: str = "001",
    experiment_name: str = "exp_a",
    status: str = "complete",
    tags: dict | None = None,
) -> RunEntryModel:
    return RunEntryModel(
        run_id=run_id,
        experiment_name=experiment_name,
        timestamp_start="2026-01-01 00:00:00",
        timestamp_end="2026-01-01 00:01:00",
        duration_seconds=60.0,
        status=status,
        results_path="/tmp/results",
        tags=tags or {},
    )


# ---------------------------------------------------------------------------
# _load — initial creation
# ---------------------------------------------------------------------------

def test_load_creates_runs_file(tmp_path):
    assert not (tmp_path / run_registry.RUNS_FILE).exists()
    run_registry._load()
    assert (tmp_path / run_registry.RUNS_FILE).exists()


def test_load_reads_existing_entries(tmp_path):
    entry = _make_entry()
    runs_path = tmp_path / run_registry.RUNS_FILE
    runs_path.write_text(
        json.dumps([entry.model_dump()])
    )
    run_registry._load()
    assert len(run_registry._runs) == 1
    assert run_registry._runs[0].run_id == "001"


def test_load_with_clear_existing(tmp_path):
    run_registry._runs.append(_make_entry(run_id="old"))
    run_registry._loaded = True

    runs_path = tmp_path / run_registry.RUNS_FILE
    runs_path.write_text("[]")

    run_registry._load(clear_existing=True)
    assert run_registry._runs == []


# ---------------------------------------------------------------------------
# add_run
# ---------------------------------------------------------------------------

def test_add_run_stores_entry():
    entry = _make_entry()
    run_registry.add_run(entry)
    assert len(run_registry._runs) == 1
    assert run_registry._runs[0].run_id == "001"


def test_add_run_persists_to_disk(tmp_path):
    entry = _make_entry()
    run_registry.add_run(entry)
    runs_path = tmp_path / run_registry.RUNS_FILE
    data = json.loads(runs_path.read_text())
    assert len(data) == 1
    assert data[0]["run_id"] == "001"


def test_add_run_duplicate_skipped():
    entry = _make_entry()
    run_registry.add_run(entry)
    run_registry.add_run(entry)
    assert len(run_registry._runs) == 1


def test_add_run_same_id_different_experiment_allowed():
    e1 = _make_entry(run_id="001", experiment_name="exp_a")
    e2 = _make_entry(run_id="001", experiment_name="exp_b")
    run_registry.add_run(e1)
    run_registry.add_run(e2)
    assert len(run_registry._runs) == 2


# ---------------------------------------------------------------------------
# get_runs
# ---------------------------------------------------------------------------

def test_get_runs_returns_all():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    run_registry.add_run(_make_entry(run_id="002", experiment_name="b"))
    result = run_registry.get_runs()
    assert len(result) == 2


def test_get_runs_filtered_by_experiment():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    run_registry.add_run(_make_entry(run_id="002", experiment_name="b"))
    result = run_registry.get_runs("a")
    assert len(result) == 1
    assert result[0].experiment_name == "a"


def test_get_runs_filter_no_match():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    result = run_registry.get_runs("nonexistent")
    assert result == []


def test_get_runs_returns_copy():
    run_registry.add_run(_make_entry())
    result = run_registry.get_runs()
    result.clear()
    assert len(run_registry._runs) == 1


# ---------------------------------------------------------------------------
# get_experiment_names
# ---------------------------------------------------------------------------

def test_get_experiment_names_returns_sorted_unique():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="zebra"))
    run_registry.add_run(_make_entry(run_id="002", experiment_name="apple"))
    run_registry.add_run(_make_entry(run_id="003", experiment_name="zebra"))
    names = run_registry.get_experiment_names()
    assert names == ["apple", "zebra"]


def test_get_experiment_names_empty():
    names = run_registry.get_experiment_names()
    assert names == []


# ---------------------------------------------------------------------------
# remove_run
# ---------------------------------------------------------------------------

def test_remove_run_returns_true_when_found():
    entry = _make_entry(run_id="001", experiment_name="a")
    run_registry.add_run(entry)
    result = run_registry.remove_run("001", "a")
    assert result is True
    assert len(run_registry._runs) == 0


def test_remove_run_persists_deletion(tmp_path):
    entry = _make_entry(run_id="001", experiment_name="a")
    run_registry.add_run(entry)
    run_registry.remove_run("001", "a")
    data = json.loads((tmp_path / run_registry.RUNS_FILE).read_text())
    assert data == []


def test_remove_run_returns_false_when_not_found():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    result = run_registry.remove_run("999", "a")
    assert result is False


def test_remove_run_wrong_experiment_not_removed():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    result = run_registry.remove_run("001", "b")
    assert result is False
    assert len(run_registry._runs) == 1


# ---------------------------------------------------------------------------
# remove_experiment
# ---------------------------------------------------------------------------

def test_remove_experiment_removes_all_matching():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    run_registry.add_run(_make_entry(run_id="002", experiment_name="a"))
    run_registry.add_run(_make_entry(run_id="003", experiment_name="b"))
    removed = run_registry.remove_experiment("a")
    assert removed == 2
    assert len(run_registry._runs) == 1
    assert run_registry._runs[0].experiment_name == "b"


def test_remove_experiment_returns_zero_when_not_found():
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    removed = run_registry.remove_experiment("nonexistent")
    assert removed == 0


def test_remove_experiment_persists_to_disk(tmp_path):
    run_registry.add_run(_make_entry(run_id="001", experiment_name="a"))
    run_registry.add_run(_make_entry(run_id="002", experiment_name="b"))
    run_registry.remove_experiment("a")
    data = json.loads((tmp_path / run_registry.RUNS_FILE).read_text())
    assert len(data) == 1
    assert data[0]["experiment_name"] == "b"
