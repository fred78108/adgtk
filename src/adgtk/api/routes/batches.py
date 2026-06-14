"""Batch routes — list and run batch jobs."""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adgtk.api.tasks import create_task, run_subprocess

router = APIRouter()
_templates: Jinja2Templates | None = None


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


@router.get("/batches", response_class=HTMLResponse)
async def batches_page(request: Request):
    batch_dir = Path("batches")
    batches = sorted(
        f.stem for f in batch_dir.glob("*.yaml")
        if not f.stem.startswith("_transient_")
    ) if batch_dir.exists() else []
    return _t().TemplateResponse(
        request, "batches.html", {"batches": batches, "active": "batches"}
    )


@router.post("/batches/{name}/run", response_class=HTMLResponse)
async def run_batch(name: str, request: Request):
    from adgtk.api.server import get_config
    cfg = get_config()
    task = create_task(f"batch: {name}")
    asyncio.create_task(
        run_subprocess(task, ["adgtk-batch", "run", name], cwd=cfg.project_dir)
    )
    return _t().TemplateResponse(
        request,
        "partials/run_output.html",
        {"task": task, "label": f"Batch: {name}"},
    )
