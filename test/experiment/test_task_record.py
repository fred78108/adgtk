# pyright: reportPrivateUsage=false

"""test_task_record.py

Tests for adgtk.experiment.task_record — the unified task-tracking
layer introduced in ADR-009.

Each test redirects TASKS_DIR and _LEGACY_TASK_FILE to a temporary
directory via the ``tasks_dir`` fixture so no test writes to the real
.tracking/ tree.

Run with: pytest test/experiment/test_task_record.py
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import adgtk.experiment.task_record as trmod
from adgtk.experiment.task_record import (
    TaskRecord,
    _migrate_legacy_active_task,
    append_output_line,
    cleanup_orphaned_tasks,
    create_task_record,
    get_active_task_record,
    get_all_task_records,
    get_task_record,
    log_path,
    read_output_lines,
    task_safe_to_start,
    update_task_record,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def tasks_dir(tmp_path, monkeypatch):
    """Redirect task_record globals to a per-test temp directory.

    Returns the Path to the tasks subdirectory so individual tests can
    inspect its contents directly.
    """
    td = str(tmp_path / "tasks")
    legacy = tmp_path / "active.task"
    monkeypatch.setattr(trmod, "TASKS_DIR", td)
    monkeypatch.setattr(trmod, "_LEGACY_TASK_FILE", legacy)
    return Path(td)


# ---------------------------------------------------------------------------
# create_task_record
# ---------------------------------------------------------------------------

def test_create_task_record_creates_directory(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    assert (tasks_dir / record.task_id).is_dir()


def test_create_task_record_writes_record_json(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    record_file = tasks_dir / record.task_id / "record.json"
    assert record_file.exists()
    loaded = json.loads(record_file.read_text())
    assert loaded["task_id"] == record.task_id


def test_create_task_record_default_pid_is_current_process(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    assert record.pid == os.getpid()


def test_create_task_record_explicit_pid(tasks_dir):
    record = create_task_record("my-exp", source="cli", pid=12345)
    assert record.pid == 12345


def test_create_task_record_explicit_task_id(tasks_dir):
    record = create_task_record(
        "my-exp", source="cli", task_id="abc123"
    )
    assert record.task_id == "abc123"


def test_create_task_record_status_is_running(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    assert record.status == "running"


def test_create_task_record_source_cli(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    assert record.source == "cli"


def test_create_task_record_source_web(tasks_dir):
    record = create_task_record("my-exp", source="web")
    assert record.source == "web"


def test_create_task_record_label_equals_experiment_name(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    assert record.label == "my-exp"


def test_create_task_record_started_at_is_utc(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    assert record.started_at.tzinfo is not None


def test_create_task_record_returns_pydantic_model(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    assert isinstance(record, TaskRecord)


# ---------------------------------------------------------------------------
# update_task_record
# ---------------------------------------------------------------------------

def test_update_task_record_updates_status(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    updated = update_task_record(record.task_id, status="complete")
    assert updated is not None
    assert updated.status == "complete"


def test_update_task_record_updates_returncode(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    updated = update_task_record(record.task_id, returncode=0)
    assert updated is not None
    assert updated.returncode == 0


def test_update_task_record_updates_finished_at(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    ts = datetime.now(timezone.utc)
    updated = update_task_record(record.task_id, finished_at=ts)
    assert updated is not None
    assert updated.finished_at is not None


def test_update_task_record_multiple_fields(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    ts = datetime.now(timezone.utc)
    updated = update_task_record(
        record.task_id,
        status="error",
        returncode=-1,
        finished_at=ts,
    )
    assert updated is not None
    assert updated.status == "error"
    assert updated.returncode == -1
    assert updated.finished_at is not None


def test_update_task_record_preserves_unmodified_fields(tasks_dir):
    record = create_task_record(
        "my-exp", source="cli", pid=42
    )
    updated = update_task_record(record.task_id, status="complete")
    assert updated is not None
    assert updated.pid == 42
    assert updated.experiment_name == "my-exp"
    assert updated.source == "cli"


def test_update_task_record_persisted_to_disk(tasks_dir):
    record = create_task_record("my-exp", source="cli")
    update_task_record(record.task_id, status="complete")
    reloaded = get_task_record(record.task_id)
    assert reloaded is not None
    assert reloaded.status == "complete"


def test_update_task_record_missing_returns_none(tasks_dir):
    result = update_task_record("nonexistent", status="complete")
    assert result is None


# ---------------------------------------------------------------------------
# get_task_record
# ---------------------------------------------------------------------------

def test_get_task_record_round_trips(tasks_dir):
    original = create_task_record(
        "round-trip", source="web", pid=9999
    )
    loaded = get_task_record(original.task_id)
    assert loaded is not None
    assert loaded.task_id == original.task_id
    assert loaded.pid == 9999
    assert loaded.source == "web"


def test_get_task_record_missing_returns_none(tasks_dir):
    assert get_task_record("does-not-exist") is None


# ---------------------------------------------------------------------------
# get_all_task_records
# ---------------------------------------------------------------------------

def test_get_all_task_records_empty_dir_returns_empty(tasks_dir):
    tasks_dir.mkdir(parents=True, exist_ok=True)
    assert get_all_task_records() == []


def test_get_all_task_records_no_dir_returns_empty(tasks_dir):
    # tasks_dir fixture sets path but doesn't create it yet
    assert not tasks_dir.exists()
    assert get_all_task_records() == []


def test_get_all_task_records_returns_all_records(tasks_dir):
    r1 = create_task_record("exp-a", source="cli")
    r2 = create_task_record("exp-b", source="web")
    records = get_all_task_records()
    ids = {r.task_id for r in records}
    assert r1.task_id in ids
    assert r2.task_id in ids


def test_get_all_task_records_respects_limit(tasks_dir):
    for i in range(5):
        create_task_record(f"exp-{i}", source="cli")
    assert len(get_all_task_records(limit=3)) == 3


def test_get_all_task_records_skips_corrupt_file(tasks_dir):
    good = create_task_record("good-exp", source="cli")
    # Inject a corrupt record file
    bad_dir = tasks_dir / "badbadba"
    bad_dir.mkdir(parents=True)
    (bad_dir / "record.json").write_text("not valid json {{{")
    records = get_all_task_records()
    ids = {r.task_id for r in records}
    assert good.task_id in ids
    assert "badbadba" not in ids


# ---------------------------------------------------------------------------
# get_active_task_record
# ---------------------------------------------------------------------------

def test_get_active_task_record_finds_running(tasks_dir, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: True
    )
    record = create_task_record("active-exp", source="cli")
    found = get_active_task_record()
    assert found is not None
    assert found.task_id == record.task_id


def test_get_active_task_record_none_when_complete(tasks_dir):
    record = create_task_record("done-exp", source="cli")
    update_task_record(
        record.task_id,
        status="complete",
        finished_at=datetime.now(timezone.utc),
    )
    assert get_active_task_record() is None


def test_get_active_task_record_none_when_no_records(tasks_dir):
    assert get_active_task_record() is None


def test_get_active_task_record_skips_error_and_stopped(tasks_dir):
    r1 = create_task_record("err-exp", source="cli")
    update_task_record(r1.task_id, status="error")
    r2 = create_task_record("stopped-exp", source="cli")
    update_task_record(r2.task_id, status="stopped")
    assert get_active_task_record() is None


# ---------------------------------------------------------------------------
# cleanup_orphaned_tasks
# ---------------------------------------------------------------------------

def test_cleanup_marks_dead_pid_as_error(tasks_dir, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    record = create_task_record(
        "orphan-exp", source="cli", pid=99999
    )
    count = cleanup_orphaned_tasks()
    assert count == 1
    updated = get_task_record(record.task_id)
    assert updated is not None
    assert updated.status == "error"
    assert updated.finished_at is not None


def test_cleanup_does_not_touch_live_pid(tasks_dir, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: True
    )
    record = create_task_record(
        "live-exp", source="cli", pid=os.getpid()
    )
    count = cleanup_orphaned_tasks()
    assert count == 0
    unchanged = get_task_record(record.task_id)
    assert unchanged is not None
    assert unchanged.status == "running"


def test_cleanup_returns_correct_count(tasks_dir, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    create_task_record("orphan-1", source="cli", pid=11111)
    create_task_record("orphan-2", source="cli", pid=22222)
    assert cleanup_orphaned_tasks() == 2


def test_cleanup_ignores_already_finished(tasks_dir, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    record = create_task_record("done-exp", source="cli")
    update_task_record(
        record.task_id,
        status="complete",
        finished_at=datetime.now(timezone.utc),
    )
    count = cleanup_orphaned_tasks()
    assert count == 0


def test_cleanup_mixed_live_and_dead(tasks_dir, monkeypatch):
    dead_pids = {11111, 22222}
    monkeypatch.setattr(
        trmod,
        "is_process_running",
        lambda pid: pid not in dead_pids,
    )
    create_task_record("dead-1", source="cli", pid=11111)
    create_task_record("dead-2", source="cli", pid=22222)
    create_task_record("live-1", source="cli", pid=os.getpid())
    count = cleanup_orphaned_tasks()
    assert count == 2


# ---------------------------------------------------------------------------
# task_safe_to_start
# ---------------------------------------------------------------------------

def test_task_safe_to_start_true_when_no_tasks(tasks_dir, monkeypatch):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    assert task_safe_to_start() is True


def test_task_safe_to_start_false_when_task_running(
    tasks_dir, monkeypatch
):
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: True
    )
    create_task_record(
        "running-exp", source="cli", pid=os.getpid()
    )
    assert task_safe_to_start() is False


def test_task_safe_to_start_true_after_orphan_cleanup(
    tasks_dir, monkeypatch
):
    # Record exists but PID is dead — cleanup should clear it
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    create_task_record("orphan-exp", source="cli", pid=99999)
    assert task_safe_to_start() is True


# ---------------------------------------------------------------------------
# append_output_line / read_output_lines / log_path
# ---------------------------------------------------------------------------

def test_append_output_line_creates_file(tasks_dir):
    record = create_task_record("log-exp", source="web")
    append_output_line(record.task_id, "hello world")
    assert log_path(record.task_id).exists()


def test_append_output_line_multiple_lines_preserved(tasks_dir):
    record = create_task_record("log-exp", source="web")
    lines = ["line one", "line two", "line three"]
    for line in lines:
        append_output_line(record.task_id, line)
    stored = read_output_lines(record.task_id)
    assert stored == lines


def test_read_output_lines_missing_file_returns_empty(tasks_dir):
    record = create_task_record("no-log", source="web")
    assert read_output_lines(record.task_id) == []


def test_read_output_lines_returns_correct_content(tasks_dir):
    record = create_task_record("log-exp", source="web")
    append_output_line(record.task_id, "alpha")
    append_output_line(record.task_id, "beta")
    result = read_output_lines(record.task_id)
    assert result == ["alpha", "beta"]


def test_log_path_is_inside_task_dir(tasks_dir):
    record = create_task_record("path-exp", source="web")
    lp = log_path(record.task_id)
    assert lp.parent == tasks_dir / record.task_id
    assert lp.name == "output.log"


# ---------------------------------------------------------------------------
# _migrate_legacy_active_task
# ---------------------------------------------------------------------------

def test_migrate_legacy_no_op_when_file_absent(tasks_dir, tmp_path):
    legacy = tmp_path / "active.task"
    assert not legacy.exists()
    _migrate_legacy_active_task()  # must not raise


def test_migrate_legacy_creates_error_record(tasks_dir, tmp_path):
    legacy = tmp_path / "active.task"
    legacy.write_text(json.dumps({
        "experiment_name": "old-exp",
        "pid": 12345,
        "started": "2026-01-01T00:00:00+00:00",
    }))
    _migrate_legacy_active_task()
    records = get_all_task_records()
    assert len(records) == 1
    assert records[0].status == "error"
    assert records[0].experiment_name == "old-exp"


def test_migrate_legacy_deletes_legacy_file(tasks_dir, tmp_path):
    legacy = tmp_path / "active.task"
    legacy.write_text(json.dumps({
        "experiment_name": "old-exp",
        "pid": 12345,
        "started": "2026-01-01T00:00:00+00:00",
    }))
    _migrate_legacy_active_task()
    assert not legacy.exists()


def test_migrate_legacy_handles_corrupt_file(tasks_dir, tmp_path):
    legacy = tmp_path / "active.task"
    legacy.write_text("{{{{ not json }")
    _migrate_legacy_active_task()  # must not raise
    assert not legacy.exists()  # file still cleaned up


def test_migrate_legacy_safe_to_call_twice(tasks_dir, tmp_path):
    # First call does the migration; second call is a no-op.
    legacy = tmp_path / "active.task"
    legacy.write_text(json.dumps({
        "experiment_name": "old-exp",
        "pid": 12345,
        "started": "2026-01-01T00:00:00+00:00",
    }))
    _migrate_legacy_active_task()
    _migrate_legacy_active_task()  # must not raise
    assert get_all_task_records()  # record from first call still there


def test_cleanup_runs_legacy_migration(tasks_dir, tmp_path, monkeypatch):
    """cleanup_orphaned_tasks should trigger the legacy migration."""
    legacy = tmp_path / "active.task"
    legacy.write_text(json.dumps({
        "experiment_name": "via-cleanup",
        "pid": 12345,
        "started": "2026-01-01T00:00:00+00:00",
    }))
    monkeypatch.setattr(
        trmod, "is_process_running", lambda pid: False
    )
    cleanup_orphaned_tasks()
    assert not legacy.exists()
    records = get_all_task_records()
    names = [r.experiment_name for r in records]
    assert "via-cleanup" in names
