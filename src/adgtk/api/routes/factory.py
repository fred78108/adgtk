"""Factory routes — browse registered components."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
_templates: Jinja2Templates | None = None


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


@router.get("/factory", response_class=HTMLResponse)
async def factory_page(request: Request):
    from adgtk.factory.component import list_entries
    group = request.query_params.get("group") or None
    tag = request.query_params.get("tag") or None
    tags = [tag] if tag else None
    components = list_entries(group=group, tags=tags)
    groups = sorted({
        getattr(c, "group", "")
        for c in list_entries()
        if getattr(c, "group", "")
    })
    return _t().TemplateResponse(
        request,
        "factory.html",
        {
            "components": components,
            "groups": groups,
            "active_group": group or "",
            "active_tag": tag or "",
            "active": "factory",
        },
    )
