"""Compatibility bridge between the experiment runner and task_record.

Provides the three functions called by experiment/runner.py and
re-exports task_safe_to_start for api/routes/experiments.py.

Launch-path logic
-----------------
CLI direct (ADGTK_TASK_ID not set in environment)
    save_active_task  -- creates a new TaskRecord with source='cli'
                         and returns the task_id string.
    clear_active_task -- updates the record to status='complete'.

Web subprocess (ADGTK_TASK_ID is set by the web server before spawn)
    save_active_task  -- updates the PID of the existing web-created
                         record; does NOT create a duplicate.
    clear_active_task -- no-op; api/tasks.run_subprocess owns the
                         final status write after proc.wait() returns.

See ADR-009 for the full design rationale.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from adgtk.experiment.task_record import (
    TaskRecord,
    create_task_record,
    get_active_task_record,
    task_safe_to_start,      # re-exported for api/routes/experiments
    update_task_record,
)

__all__ = [
    "clear_active_task",
    "get_active_task",
    "save_active_task",
    "task_safe_to_start",
]

_TASK_ID_ENV = "ADGTK_TASK_ID"


def save_active_task(experiment_name: str) -> str:
    """Start tracking an experiment task and return the task ID.

    CLI path: creates a new TaskRecord with source='cli'.

    Web path: the ADGTK_TASK_ID environment variable is set by the
    web server before spawning this subprocess.  We update the
    existing record with the real subprocess PID rather than creating
    a duplicate record.

    Args:
        experiment_name: Name of the experiment being run.

    Returns:
        The task_id string for the active record.
    """
    task_id = os.environ.get(_TASK_ID_ENV)
    if task_id:
        update_task_record(task_id, pid=os.getpid())
        return task_id
    record = create_task_record(
        experiment_name=experiment_name,
        source="cli",
    )
    return record.task_id


def clear_active_task(
    task_id: Optional[str] = None,
    status: str = "complete",
) -> None:
    """Mark a task as finished.

    CLI path: updates the TaskRecord with the given status and
    sets finished_at to the current UTC time.

    Web path: no-op.  api/tasks.run_subprocess owns the final status
    write after proc.wait() returns and has access to the returncode.

    Args:
        task_id: The task to clear.  Required on the CLI path;
            ignored (the call is a no-op) on the web path.
        status: The final status string.  Defaults to 'complete'.
    """
    if os.environ.get(_TASK_ID_ENV):
        return  # web subprocess — parent process owns this write
    if task_id is None:
        return
    update_task_record(
        task_id,
        status=status,
        finished_at=datetime.now(timezone.utc),
    )


def get_active_task() -> Optional[TaskRecord]:
    """Return the currently running TaskRecord, or None.

    Retained for call-site compatibility with runner.py imports.
    Delegates to get_active_task_record() in task_record.
    """
    return get_active_task_record()
