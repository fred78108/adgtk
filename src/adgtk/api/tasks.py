"""Background task management for long-running subprocess operations.

TaskState is the in-memory representation used for live SSE streaming.
It holds a reference to a TaskRecord (the durable on-disk state) so
that status, returncode, and finished_at are persisted to
.tracking/tasks/{task_id}/ as the subprocess runs.

Coordination with the CLI runner
---------------------------------
run_subprocess sets ADGTK_TASK_ID in the child environment so that
experiment/task.save_active_task() updates the PID of the existing
record instead of creating a duplicate.  The subprocess's
clear_active_task() is a no-op when that env var is present; final
status is written here in run_subprocess's finally block.

See ADR-009 for the full design rationale.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from adgtk.utils import get_project_logger
from adgtk.experiment.task_record import (
    TaskRecord,
    append_output_line,
    create_task_record,
    update_task_record,
)
from adgtk.utils.defaults import EXP_RESULTS_FOLDER

_registry: dict[str, "TaskState"] = {}


def _find_run_id(
    experiment_name: str, project_dir: str, since: datetime
) -> Optional[str]:
    """Return the run directory name created under results/{experiment_name}/
    after *since*, or None if nothing matches.

    Called after a successful subprocess exit to discover which run_id
    was produced so the task page can navigate to the report.
    """
    results_dir = Path(project_dir) / EXP_RESULTS_FOLDER / experiment_name
    if not results_dir.exists():
        return None
    # subtract 1s to absorb sub-second timing between task start and fs write
    cutoff = since.timestamp() - 1
    newest: Optional[str] = None
    newest_mtime: float = cutoff
    for entry in results_dir.iterdir():
        if entry.is_dir():
            mtime = entry.stat().st_mtime
            if mtime > newest_mtime:
                newest = entry.name
                newest_mtime = mtime
    return newest


@dataclass
class TaskState:
    """In-memory state for a running or recently-finished task.

    The proc and lines fields are transient and intentionally excluded
    from TaskRecord (the durable on-disk model).  All other state that
    needs to survive a restart lives in task_record.
    """

    task_id: str
    label: str
    status: str  # "running" | "complete" | "error" | "stopped"
    task_record: TaskRecord
    lines: list[str] = field(default_factory=list)
    returncode: Optional[int] = None
    run_id: Optional[str] = None
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    finished_at: Optional[datetime] = None
    proc: Optional[asyncio.subprocess.Process] = field(
        default=None, repr=False
    )


def create_task(
    label: str, experiment_name: Optional[str] = None
) -> TaskState:
    """Create a TaskState, persist a TaskRecord to disk, and register.

    The TaskRecord is written with pid=0 as a placeholder; the real
    subprocess PID is filled in by run_subprocess once the process
    starts.

    Args:
        label: Human-readable description shown in the web UI.
        experiment_name: Bare experiment name stored in TaskRecord for
            run_id discovery after completion.  Defaults to *label*.

    Returns:
        The newly created and registered TaskState.
    """
    task_id = uuid.uuid4().hex[:8]
    record = create_task_record(
        experiment_name=experiment_name or label,
        source="web",
        pid=0,
        task_id=task_id,
    )
    task = TaskState(
        task_id=task_id,
        label=label,
        status="running",
        task_record=record,
    )
    _registry[task_id] = task
    return task


def get_task(task_id: str) -> Optional[TaskState]:
    """Return the TaskState for the given ID, or None."""
    return _registry.get(task_id)


def get_active_tasks() -> list[TaskState]:
    """Return all TaskState entries currently in 'running' status."""
    return [t for t in _registry.values() if t.status == "running"]


def stop_task(task_id: str) -> bool:
    """Kill a running subprocess and mark the task as stopped.

    Appends a '[stopped by user]' line to both the in-memory lines
    list and the on-disk output.log.

    Args:
        task_id: The task to stop.

    Returns:
        True if the task was found and killed, False otherwise.
    """
    _logger = get_project_logger()
    _logger.warning(
        "A web request to stop the experiment was received."
    )
    task = _registry.get(task_id)
    if task and task.proc and task.status == "running":
        task.proc.kill()
        task.status = "stopped"
        task.finished_at = datetime.now(timezone.utc)
        line = "[stopped by user]"
        task.lines.append(line)
        append_output_line(task_id, line)
        update_task_record(
            task_id,
            status="stopped",
            finished_at=task.finished_at,
        )
        return True
    return False


async def run_subprocess(
    task: TaskState,
    cmd: list[str],
    cwd: str,
) -> None:
    """Spawn *cmd* in *cwd*, capturing stdout/stderr to memory and disk.

    Each captured line is appended to task.lines (for live SSE
    streaming) and to .tracking/tasks/{task_id}/output.log (for
    replay after completion or server restart).

    ADGTK_TASK_ID is set in the child environment so that
    experiment/task.save_active_task() links to this record instead
    of creating a duplicate.

    Args:
        task: The TaskState to populate with output and final status.
        cmd: The command to run as a list of strings.
        cwd: Working directory for the subprocess.
    """
    env = {**os.environ, "ADGTK_TASK_ID": task.task_id}
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
            env=env,
        )
        task.proc = proc
        update_task_record(task.task_id, pid=proc.pid)
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode(errors="replace").rstrip()
            task.lines.append(line)
            append_output_line(task.task_id, line)
        await proc.wait()
        task.returncode = proc.returncode
        task.status = (
            "complete" if proc.returncode == 0 else "error"
        )
        if task.status == "complete":
            task.run_id = _find_run_id(
                task.task_record.experiment_name, cwd, task.started_at
            )
    except Exception as exc:
        line = f"[internal error] {exc}"
        task.lines.append(line)
        append_output_line(task.task_id, line)
        task.status = "error"
        task.returncode = -1
    finally:
        task.finished_at = datetime.now(timezone.utc)
        update_task_record(
            task.task_id,
            status=task.status,
            returncode=task.returncode,
            finished_at=task.finished_at,
            run_id=task.run_id,
        )
