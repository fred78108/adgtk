"""Study routes — list, create, run."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
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


@router.get("/studies", response_class=HTMLResponse)
async def studies_page(request: Request):
    from adgtk.experiment.study.builder import list_study_blueprints
    from adgtk.tracking.runs import get_experiment_names
    studies = list_study_blueprints()
    experiments = get_experiment_names()
    return _t().TemplateResponse(
        request,
        "studies.html",
        {"studies": studies, "experiments": experiments, "active": "studies"},
    )


@router.post("/studies/{name}/run", response_class=HTMLResponse)
async def run_study(name: str, request: Request):
    try:
        from adgtk.experiment.study.report import generate_study_report
        report_path, csv_path = generate_study_report(name)
        msg = f"Report: {report_path}"
        cls = "bg-green-50 text-green-800 border-green-200"
    except Exception as exc:
        msg = str(exc)
        cls = "bg-red-50 text-red-800 border-red-200"
    return HTMLResponse(
        f'<div class="rounded-md border px-4 py-3 text-sm {cls}">{msg}</div>'
    )


@router.post("/studies", response_class=HTMLResponse)
async def create_study(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    experiments: list[str] = Form(default=[]),
):
    try:
        from adgtk.experiment.study.builder import (
            StudyBlueprint, save_study_blueprint,
        )
        bp = StudyBlueprint(
            name=name, description=description, experiments=experiments
        )
        save_study_blueprint(bp)
        msg = f"Study '{name}' created."
        cls = "bg-green-50 text-green-800 border-green-200"
    except Exception as exc:
        msg = str(exc)
        cls = "bg-red-50 text-red-800 border-red-200"
    return HTMLResponse(
        f'<div class="rounded-md border px-4 py-3 text-sm {cls}">{msg}</div>'
    )
