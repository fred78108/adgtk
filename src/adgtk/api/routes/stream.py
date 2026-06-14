"""SSE streaming endpoint for background tasks."""

from __future__ import annotations

import asyncio
import html
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from adgtk.api.tasks import get_active_tasks, get_task, stop_task
from adgtk.experiment.task_record import (
    TaskRecord,
    delete_finished_task_records,
    get_all_task_records,
    get_task_record,
    read_output_lines,
)

router = APIRouter()
_templates: Jinja2Templates | None = None


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


def _duration_str(
    started_at: datetime,
    finished_at: datetime | None = None,
) -> str:
    end = finished_at or datetime.now(timezone.utc)
    # Normalize both sides to UTC-aware in case old records on disk have
    # naive datetimes (written before the timezone fix in api/tasks.py).
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    total = int((end - started_at).total_seconds())
    if total < 60:
        return f"{total}s"
    m, s = divmod(total, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def _task_rows(records=None):
    if records is None:
        records = get_all_task_records()
    return [
        {"record": r, "duration": _duration_str(r.started_at, r.finished_at)}
        for r in records
    ]


@router.get("/tasks", response_class=HTMLResponse)
async def tasks_list(request: Request):
    from adgtk.api.server import get_config
    cfg = get_config()
    return _t().TemplateResponse(
        request,
        "tasks_list.html",
        {
            "rows": _task_rows(),
            "active": "tasks",
            "project_name": Path(cfg.project_dir).name,
        },
    )


@router.post("/tasks/cleanup", response_class=HTMLResponse)
async def cleanup_tasks(request: Request):
    from adgtk.api.server import get_config
    cfg = get_config()
    delete_finished_task_records()
    return _t().TemplateResponse(
        request,
        "tasks_list.html",
        {
            "rows": _task_rows(),
            "active": "tasks",
            "project_name": Path(cfg.project_dir).name,
            "cleanup_done": True,
        },
    )


@router.get("/tasks/active-indicator", response_class=HTMLResponse)
async def active_indicator(request: Request):
    active = get_active_tasks()
    response = _t().TemplateResponse(
        request,
        "partials/active_indicator.html",
        {"active_tasks": active},
    )
    if not active:
        response.headers["HX-Trigger"] = "dashboardRefresh"
    return response


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(task_id: str, request: Request):
    task = get_task(task_id)
    record: TaskRecord | None
    if task:
        record = task.task_record
        output_lines = task.lines
        run_id = task.run_id
        is_live = task.status == "running"
    else:
        record = get_task_record(task_id)
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        output_lines = read_output_lines(task_id)
        run_id = record.run_id
        is_live = False
    return _t().TemplateResponse(
        request,
        "task_detail.html",
        {
            "record": record,
            "output_lines": output_lines,
            "run_id": run_id,
            "is_live": is_live,
        },
    )


@router.post("/tasks/{task_id}/stop", response_class=HTMLResponse)
async def stop_task_endpoint(task_id: str, request: Request):
    stop_task(task_id)
    active = get_active_tasks()
    return _t().TemplateResponse(
        request,
        "partials/active_indicator.html",
        {"active_tasks": active},
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str, request: Request) -> StreamingResponse:
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def generate():
        last_id = request.headers.get("last-event-id", "")
        try:
            idx = int(last_id) + 1 if last_id else 0
        except ValueError:
            idx = 0

        while True:
            if await request.is_disconnected():
                break

            while idx < len(task.lines):
                line = html.escape(task.lines[idx])
                yield (
                    f"id: {idx}\n"
                    f"data: <div class='font-mono text-xs"
                    f" leading-5'>{line}</div>\n\n"
                )
                idx += 1

            if task.status != "running":
                if task.status == "complete":
                    cls = "text-green-600"
                    label = "✓ complete"
                else:
                    cls = "text-red-600"
                    label = "✗ error"
                done_div = (
                    f"<div class='{cls} font-semibold text-xs"
                    f" mt-2 pt-2 border-t border-slate-200'>"
                    f"{label}</div>"
                )
                yield f"event: done\ndata: {done_div}\n\n"
                if task.status == "complete" and task.run_id:
                    exp = task.task_record.experiment_name
                    url = f"/results/{exp}/{task.run_id}"
                    yield f"event: navigate\ndata: {url}\n\n"
                yield "event: dashboardRefresh\ndata: \n\n"
                break

            await asyncio.sleep(0.1)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
