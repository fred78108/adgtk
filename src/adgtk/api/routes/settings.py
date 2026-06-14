"""Settings page — view and edit project settings.yaml via the web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from adgtk.utils.project_settings import (
    ProjectSettings,
    TaskSettings,
    load_project_settings,
    save_project_settings,
)

router = APIRouter()
_templates: Jinja2Templates | None = None


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    from adgtk.api.server import get_config
    cfg = get_config()
    settings = load_project_settings()
    return _t().TemplateResponse(
        request,
        "settings.html",
        {
            "settings": settings,
            "active": "settings",
            "project_name": Path(cfg.project_dir).name,
            "saved": False,
        },
    )


@router.post("/settings", response_class=HTMLResponse)
async def save_settings(
    request: Request,
    tasks_ttl_days: int = Form(...),
    tasks_max_count: int = Form(...),
    tasks_auto_cleanup: str = Form(default="off"),
):
    from adgtk.api.server import get_config
    cfg = get_config()

    tasks_ttl_days = max(1, tasks_ttl_days)
    tasks_max_count = max(10, tasks_max_count)

    settings = ProjectSettings(
        tasks=TaskSettings(
            ttl_days=tasks_ttl_days,
            max_count=tasks_max_count,
            auto_cleanup=(tasks_auto_cleanup == "on"),
        )
    )
    save_project_settings(settings)

    return _t().TemplateResponse(
        request,
        "settings.html",
        {
            "settings": settings,
            "active": "settings",
            "project_name": Path(cfg.project_dir).name,
            "saved": True,
        },
    )
