"""test_task.py

Tests for adgtk.experiment.task — the compatibility shim that
bridges experiment/runner.py to the unified task_record layer.

Tests cover the two launch paths defined in ADR-009:
  - CLI direct  (ADGTK_TASK_ID not set)
  - Web subprocess  (ADGTK_TASK_ID set before spawn)

Run with: pytest test/experiment/test_task.py
"""

import os

import pytest

import adgtk.experiment.task_record as trmod
from adgtk.experiment.task import (
    clear_active_task,
    get_active_task,
    save_active_task,
    task_safe_to_start,
)
from adgtk.experiment.task_record import (
    create_task_record,
    get_task_record,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_tasks(tmp_path, monkeypatch):
    """Redirect task_record storage to a per-test temp directory."""
    monkeypatch.setattr(trmod, "TASKS_DIR", str(tmp_path / "tasks"))
    monkeypatch.setattr(
        trmod, "_LEGACY_TASK_FILE", tmp_path / "active.task"
    )
    # Ensure ADGTK_TASK_ID is clean at the start of every test
    monkeypatch.delenv("ADGTK_TASK_ID", raising=False)


# ---------------------------------------------------------------------------
# save_active_task — CLI direct path (no env var)
# ---------------------------------------------------------------------------

def test_save_active_task_creates_cli_record(tmp_path):
    task_id = save_active_task("my-experiment")
    record = get_task_record(task_id)
    assert record is not None
    assert record.source == "cli"
    assert record.experiment_name == "my-experiment"


def test_save_active_task_returns_str(tmp_path):
    task_id = save_active_task("my-experiment")
    assert isinstance(task_id, str)
    assert len(task_id) > 0


def test_save_active_task_pid_is_current_process(tmp_path):
    task_id = save_active_task("my-experiment")
    record = get_task_record(task_id)
    assert record is not None
    assert record.pid == os.getpid()


def test_save_active_task_status_is_running(tmp_path):
    task_id = save_active_task("my-experiment")
    record = get_task_record(task_id)
    assert record is not None
    assert record.status == "running"


# ---------------------------------------------------------------------------
# save_active_task — web subprocess path (ADGTK_TASK_ID set)
# ---------------------------------------------------------------------------

def test_save_active_task_web_updates_pid(tmp_path, monkeypatch):
    pre = create_task_record(
        "web-exp", source="web", pid=0
    )
    monkeypatch.setenv("ADGTK_TASK_ID", pre.task_id)
    returned_id = save_active_task("web-exp")
    assert returned_id == pre.task_id
    updated = get_task_record(pre.task_id)
    assert updated is not None
    assert updated.pid == os.getpid()


def test_save_active_task_web_does_not_create_duplicate(
    tmp_path, monkeypatch
):
    pre = create_task_record("web-exp", source="web", pid=0)
    monkeypatch.setenv("ADGTK_TASK_ID", pre.task_id)
    save_active_task("web-exp")
    from adgtk.experiment.task_record import get_all_task_records
    records = get_all_task_records()
    assert len(records) == 1


def test_save_active_task_web_does_not_overwrite_source(
    tmp_path, monkeypatch
):
    pre = create_task_record("web-exp", source="web", pid=0)
    monkeypatch.setenv("ADGTK_TASK_ID", pre.task_id)
    save_active_task("web-exp")
    updated = get_task_record(pre.task_id)
    assert updated is not None
    assert updated.source == "web"


# ---------------------------------------------------------------------------
# clear_active_task — CLI direct path (no env var)
# ---------------------------------------------------------------------------

def test_clear_active_task_marks_complete(tmp_path):
    task_id = save_active_task("my-experiment")
    clear_active_task(task_id)
    record = get_task_record(task_id)
    assert record is not None
    assert record.status == "complete"


def test_clear_active_task_sets_finished_at(tmp_path):
    task_id = save_active_task("my-experiment")
    clear_active_task(task_id)
    record = get_task_record(task_id)
    assert record is not None
    assert record.finished_at is not None


def test_clear_active_task_custom_status(tmp_path):
    task_id = save_active_task("my-experiment")
    clear_active_task(task_id, status="error")
    record = get_task_record(task_id)
    assert record is not None
    assert record.status == "error"


def test_clear_active_task_noop_with_none_task_id(tmp_path):
    clear_active_task(None)  # must not raise


def test_clear_active_task_noop_with_missing_task_id(tmp_path):
    clear_active_task("does-not-exist")  # must not raise


# ---------------------------------------------------------------------------
# clear_active_task — web subprocess path (ADGTK_TASK_ID set)
# ---------------------------------------------------------------------------

def test_clear_active_task_noop_when_env_var_set(
    tmp_path, monkeypatch
):
    pre = create_task_record("web-exp", source="web", pid=99)
    monkeypatch.setenv("ADGTK_TASK_ID", pre.task_id)
    clear_active_task(pre.task_id)
    # Record should remain unchanged (still "running")
    record = get_task_record(pre.task_id)
    assert record is not None
    assert record.status == "running"


# ---------------------------------------------------------------------------
# get_active_task
# ---------------------------------------------------------------------------

def test_get_active_task_returns_running_record(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: True
    )
    task_id = save_active_task("running-exp")
    found = get_active_task()
    assert found is not None
    assert found.task_id == task_id


def test_get_active_task_returns_none_when_no_tasks(tmp_path):
    assert get_active_task() is None


def test_get_active_task_returns_none_after_clear(tmp_path):
    task_id = save_active_task("done-exp")
    clear_active_task(task_id)
    assert get_active_task() is None


# ---------------------------------------------------------------------------
# task_safe_to_start (re-exported from task_record)
# ---------------------------------------------------------------------------

def test_task_safe_to_start_true_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    assert task_safe_to_start() is True


def test_task_safe_to_start_false_when_running(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: True
    )
    save_active_task("blocking-exp")
    assert task_safe_to_start() is False


def test_task_safe_to_start_true_after_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    task_id = save_active_task("temp-exp")
    clear_active_task(task_id)
    assert task_safe_to_start() is True
