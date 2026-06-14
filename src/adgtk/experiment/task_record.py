"""Unified task tracking for CLI and web interfaces.

Each experiment run, regardless of whether it was launched from the
CLI or the web server, gets a directory under .tracking/tasks/::

    .tracking/tasks/{task_id}/
        record.json   -- TaskRecord (status, pid, timestamps, returncode)
        output.log    -- captured stdout/stderr, one line per entry

record.json is written by both the CLI runner (source="cli") and the
web server (source="web").  output.log is appended line-by-line by
the web's run_subprocess; CLI-direct runs do not capture to disk.

Orphan detection
----------------
Any record whose status is "running" but whose PID is no longer alive
is marked "error" the next time cleanup_orphaned_tasks() runs.  That
function is called by task_safe_to_start() and at web-server startup.

Legacy migration
----------------
_migrate_legacy_active_task() converts a pre-ADR-009
.tracking/active.task file to an error TaskRecord on first call and
deletes the legacy file.  It is invoked at the top of
cleanup_orphaned_tasks() so no explicit migration step is required.

See ADR-009 for the full design rationale.
"""

import json
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from adgtk.utils.defaults import TASKS_DIR, TRACKING_FOLDER
from adgtk.utils.process import is_process_running

# Path of the legacy single-file PID record (pre-ADR-009).
_LEGACY_TASK_FILE = Path(TRACKING_FOLDER) / "active.task"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class TaskRecord(BaseModel):
    """Durable state for a single experiment run task.

    Written to disk by both the CLI runner (source='cli') and the web
    server (source='web').  The proc and lines fields of
    api.tasks.TaskState are intentionally excluded — they are transient
    and in-memory only.
    """

    task_id: str
    experiment_name: str
    label: str
    status: Literal["running", "complete", "error", "stopped"]
    pid: int
    source: Literal["cli", "web"]
    started_at: datetime
    finished_at: Optional[datetime] = None
    returncode: Optional[int] = None
    run_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _task_dir(task_id: str) -> Path:
    """Return the directory for a given task."""
    return Path(TASKS_DIR) / task_id


def _record_path(task_id: str) -> Path:
    """Return the path to a task's record.json."""
    return _task_dir(task_id) / "record.json"


def log_path(task_id: str) -> Path:
    """Return the path to a task's output.log.

    Exposed publicly so SSE streaming code can locate the log file
    after a server restart (recommendation 2.1 log-replay).
    """
    return _task_dir(task_id) / "output.log"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_task_record(
    experiment_name: str,
    source: Literal["cli", "web"],
    pid: Optional[int] = None,
    task_id: Optional[str] = None,
) -> TaskRecord:
    """Create a new TaskRecord, persist it, and return it.

    Args:
        experiment_name: The name of the experiment being run.
        source: Whether the task was launched by the CLI or web server.
        pid: The process ID.  Defaults to os.getpid().  Pass 0 when
            the subprocess PID is not yet known (web path); update
            later with update_task_record().
        task_id: Optional explicit task ID.  A UUID hex slice is
            generated when not provided.

    Returns:
        The newly created and persisted TaskRecord.
    """
    if task_id is None:
        task_id = uuid.uuid4().hex[:8]
    if pid is None:
        pid = os.getpid()
    record = TaskRecord(
        task_id=task_id,
        experiment_name=experiment_name,
        label=experiment_name,
        status="running",
        pid=pid,
        source=source,
        started_at=datetime.now(timezone.utc),
    )
    _task_dir(task_id).mkdir(parents=True, exist_ok=True)
    _record_path(task_id).write_text(
        record.model_dump_json(indent=2)
    )
    return record


def update_task_record(
    task_id: str,
    **kwargs,
) -> Optional[TaskRecord]:
    """Apply keyword updates to a TaskRecord and persist the result.

    Performs a read-merge-write so only the supplied fields change.

    Args:
        task_id: The task to update.
        **kwargs: Fields to update on the TaskRecord.

    Returns:
        The updated TaskRecord, or None if the record does not exist.
    """
    path = _record_path(task_id)
    if not path.exists():
        return None
    record = TaskRecord.model_validate_json(path.read_text())
    updated = record.model_copy(update=kwargs)
    path.write_text(updated.model_dump_json(indent=2))
    return updated


def get_task_record(task_id: str) -> Optional[TaskRecord]:
    """Read and return a single TaskRecord from disk.

    Args:
        task_id: The task to retrieve.

    Returns:
        The TaskRecord, or None if the record file does not exist.
    """
    path = _record_path(task_id)
    if not path.exists():
        return None
    return TaskRecord.model_validate_json(path.read_text())


def get_all_task_records(limit: int = 50) -> list[TaskRecord]:
    """Return task records sorted by modification time, newest first.

    Args:
        limit: Maximum number of records to return.

    Returns:
        List of TaskRecord instances, newest first.  Corrupt or
        unreadable record files are skipped silently.
    """
    tasks_dir = Path(TASKS_DIR)
    if not tasks_dir.exists():
        return []
    record_files = sorted(
        tasks_dir.glob("*/record.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]
    records: list[TaskRecord] = []
    for path in record_files:
        try:
            records.append(
                TaskRecord.model_validate_json(path.read_text())
            )
        except Exception:
            pass  # corrupt file — skip without crashing
    return records


def get_active_task_record() -> Optional[TaskRecord]:
    """Return the first TaskRecord with status 'running', or None."""
    for record in get_all_task_records():
        if record.status == "running":
            return record
    return None


# ---------------------------------------------------------------------------
# Orphan cleanup and safety check
# ---------------------------------------------------------------------------

def cleanup_orphaned_tasks() -> int:
    """Mark running tasks whose PID is dead as 'error'.

    Called at web-server startup and inside task_safe_to_start() so
    the running-task list is always accurate before a new task is
    considered.

    Also runs the one-time legacy migration from active.task if that
    file is still present.

    Returns:
        The number of orphaned records that were updated.
    """
    _migrate_legacy_active_task()
    # When called from within a web subprocess, skip our own task so we
    # don't orphan the pid=0 placeholder before the parent writes the
    # real PID.
    current_task_id = os.environ.get("ADGTK_TASK_ID")
    count = 0
    for record in get_all_task_records():
        if record.status != "running":
            continue
        if record.task_id == current_task_id:
            continue
        # pid=0 is a placeholder (web path, PID not yet assigned) and
        # os.kill(0, 0) always succeeds on Linux, so check explicitly.
        if record.pid == 0 or not is_process_running(record.pid):
            update_task_record(
                record.task_id,
                status="error",
                finished_at=datetime.now(timezone.utc),
            )
            count += 1
    return count


def task_safe_to_start() -> bool:
    """Return True if no experiment task is currently running.

    Runs orphan cleanup first so stale records from crashed processes
    do not block new experiments.
    """
    cleanup_orphaned_tasks()
    active = get_active_task_record()
    if active is None:
        return True
    # When launched as a web subprocess, the only remaining "running"
    # task may be our own (pid=0 until the parent calls update_task_record).
    current_task_id = os.environ.get("ADGTK_TASK_ID")
    return current_task_id is not None and active.task_id == current_task_id


# ---------------------------------------------------------------------------
# Retention / purge
# ---------------------------------------------------------------------------

def purge_old_task_records(
    max_age_days: int = 30,
    max_count: int = 200,
) -> int:
    """Delete finished task directories that exceed the retention policy.

    Two rules are applied in order:
    1. Any finished task whose ``finished_at`` is older than *max_age_days*
       is deleted.
    2. If more than *max_count* task directories remain after step 1, the
       oldest ones (by finish or start time) are deleted until the count is
       within the limit.

    Running tasks (status == 'running') are never deleted regardless of age.

    Args:
        max_age_days: Delete finished tasks older than this many days.
        max_count: Keep at most this many task directories on disk.

    Returns:
        Total number of task directories removed.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    removed = 0

    # Pass 1 — TTL: remove any finished task older than the cutoff.
    for record in get_all_task_records(limit=10_000):
        if record.status == "running":
            continue
        ref_time = record.finished_at or record.started_at
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)
        if ref_time < cutoff:
            task_dir = _task_dir(record.task_id)
            if task_dir.exists():
                shutil.rmtree(task_dir, ignore_errors=True)
                removed += 1

    # Pass 2 — count cap: if still over limit, drop oldest finished tasks.
    remaining = get_all_task_records(limit=10_000)
    finished = [r for r in remaining if r.status != "running"]
    if len(remaining) > max_count:
        overflow = len(remaining) - max_count
        # finished is already sorted newest-first; trim from the tail (oldest)
        to_delete = (
            finished[-overflow:] if overflow <= len(finished) else finished
        )
        for record in to_delete:
            task_dir = _task_dir(record.task_id)
            if task_dir.exists():
                shutil.rmtree(task_dir, ignore_errors=True)
                removed += 1

    return removed


def delete_finished_task_records() -> int:
    """Delete all task directories with a finished status.

    Covers complete, error, and stopped statuses.

    Used by the manual "cleanup" button in the web UI and CLI.  Running
    tasks are never touched.

    Returns:
        Number of task directories removed.
    """
    removed = 0
    for record in get_all_task_records(limit=10_000):
        if record.status == "running":
            continue
        task_dir = _task_dir(record.task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir, ignore_errors=True)
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# Output log helpers
# ---------------------------------------------------------------------------

def append_output_line(task_id: str, line: str) -> None:
    """Append a single output line to the task's output.log.

    Creates the file on first call.  Called by the web's
    run_subprocess for every captured stdout/stderr line.

    Args:
        task_id: The task whose log should be appended to.
        line: A single decoded, stripped output line.
    """
    with log_path(task_id).open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_output_lines(task_id: str) -> list[str]:
    """Read all captured output lines from the task's output.log.

    Args:
        task_id: The task whose log to read.

    Returns:
        List of output lines (without trailing newlines).  Returns an
        empty list if the file does not exist (e.g. CLI-launched task
        or web task that has not yet produced output).
    """
    log = log_path(task_id)
    if not log.exists():
        return []
    return log.read_text(encoding="utf-8").splitlines()


# ---------------------------------------------------------------------------
# Legacy migration (private)
# ---------------------------------------------------------------------------

def _migrate_legacy_active_task() -> None:
    """Convert a legacy active.task file to an error TaskRecord.

    If .tracking/active.task exists from a pre-ADR-009 installation,
    convert it to a TaskRecord with status='error' and remove the
    legacy file.  Safe to call repeatedly — exits silently when the
    legacy file is absent.
    """
    if not _LEGACY_TASK_FILE.exists():
        return
    try:
        data = json.loads(_LEGACY_TASK_FILE.read_text())
        exp = data.get("experiment_name", "unknown")
        pid = int(data.get("pid", 0))
        record = create_task_record(
            experiment_name=exp,
            source="cli",
            pid=pid,
        )
        update_task_record(
            record.task_id,
            status="error",
            finished_at=datetime.now(timezone.utc),
        )
    except Exception:
        pass  # malformed legacy file — delete it anyway
    finally:
        _LEGACY_TASK_FILE.unlink(missing_ok=True)
