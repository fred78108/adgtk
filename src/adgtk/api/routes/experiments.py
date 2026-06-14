"""Experiment routes — list, run, edit, copy, report, builder wizard."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any, Optional

import yaml as _yaml
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from adgtk.api.tasks import (
    TaskState, create_task, get_active_tasks, run_subprocess,
)
from adgtk.experiment.task import task_safe_to_start

router = APIRouter()
_templates: Jinja2Templates | None = None


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


# -- Builder state models ----------------------------------------------------

class _BuilderStackFrame(BaseModel):
    attribute: str
    factory_id: str
    factory_init: bool = True
    q_index: int = 0
    answers: list[dict] = []


class _ListExpandCtx(BaseModel):
    attribute: str
    group: str
    question_text: str
    accumulated: list[dict] = []


class _BuilderState(BaseModel):
    scenario_factory_id: str
    stack: list[_BuilderStackFrame]
    list_expand_ctx: Optional[_ListExpandCtx] = None
    completed: Optional[dict] = None
    editing_name: Optional[str] = None
    prefill: dict = {}


# -- Builder helpers ---------------------------------------------------------

def _advance_state(
    state: _BuilderState,
) -> tuple[_BuilderState, Optional[str]]:
    """Resolve completed frames.

    Returns (state, early_action) where early_action is 'list_expand_more'
    when the user needs to be asked "add another?", otherwise None.
    """
    import adgtk.factory.component as fac

    while state.stack:
        frame = state.stack[-1]
        interview = fac.get_interview(frame.factory_id)

        if frame.q_index < len(interview):
            return state, None  # frame still has questions

        # Frame is complete — build its AttributeEntry dict
        completed = {
            "attribute": frame.attribute,
            "factory_id": frame.factory_id,
            "factory_init": frame.factory_init,
            "init_config": frame.answers,
        }

        if len(state.stack) == 1:
            # Root (scenario) frame — we're done with the interview
            state.completed = completed
            state.stack = []
            return state, None

        # Pop and handle
        state.stack.pop()

        if state.list_expand_ctx is not None:
            # We just finished a list[expand] sub-interview
            state.list_expand_ctx.accumulated.append(completed)
            return state, "list_expand_more"

        # Normal expand — add result to parent and advance its index
        parent = state.stack[-1]
        parent.answers.append(completed)
        parent.q_index += 1
        # loop to check if parent is also done

    return state, None  # empty stack → name form


def _get_next_ui_action(state: _BuilderState) -> str:
    """Inspect current state and return the UI action needed."""
    if not state.stack:
        return "name_form"
    import adgtk.factory.component as fac
    frame = state.stack[-1]
    interview = fac.get_interview(frame.factory_id)
    q = interview[frame.q_index]
    if q.entry_type == "expand":
        return "expand_pick"
    if q.entry_type == "list[expand]":
        return "list_expand_pick"
    return "next_question"


def _get_prefill_prefix(state: _BuilderState) -> str:
    """Build the dot-separated path prefix for the current stack depth."""
    if len(state.stack) <= 1:
        return ""
    return ".".join(f.attribute for f in state.stack[1:]) + "."


def _build_prefill(init_config_list: list, prefix: str = "") -> dict:
    """Flatten an init_config list into a {attr_path: value} prefill dict."""
    result: dict = {}
    if not isinstance(init_config_list, list):
        return result
    for entry in init_config_list:
        if not isinstance(entry, dict):
            continue
        attr = entry.get("attribute", "")
        fid = entry.get("factory_id")
        init = entry.get("init_config")
        key = f"{prefix}{attr}"
        if fid:
            result[f"{key}._factory_id"] = fid
            if isinstance(init, list):
                result.update(_build_prefill(init, f"{key}."))
        else:
            result[key] = init
    return result


async def _parse_form_answer(
    form: Any, attribute: str, entry_type: str
) -> Any:
    """Parse the answer value(s) from a form submission."""
    key = f"answer_{attribute}"
    if entry_type in ("str", "ml-string"):
        return str(form.get(key, ""))
    if entry_type == "int":
        raw = form.get(key, "0") or "0"
        return int(raw)
    if entry_type == "float":
        raw = form.get(key, "0") or "0"
        return float(raw)
    if entry_type == "bool":
        return form.get(key, "false") in ("true", "True", "1", "yes", "on")
    if entry_type in ("list[str]", "list[int]", "list[float]", "list[bool]"):
        values = form.getlist(f"{key}[]")
        if entry_type == "list[int]":
            return [int(v) for v in values if str(v).strip()]
        if entry_type == "list[float]":
            return [float(v) for v in values if str(v).strip()]
        if entry_type == "list[bool]":
            return [v in ("true", "True", "1", "yes", "on") for v in values]
        return [str(v) for v in values if str(v).strip()]
    raise ValueError(f"Cannot parse answer for type {entry_type}")


def _render_builder_step(
    request: Request, state: _BuilderState
) -> HTMLResponse:
    """Advance state and render the appropriate next wizard step."""
    import adgtk.factory.component as fac

    state, early = _advance_state(state)
    state_json = state.model_dump_json()

    if early == "list_expand_more":
        return _t().TemplateResponse(
            request, "partials/builder_list_expand_more.html", {
                "state_json": state_json,
                "ctx": state.list_expand_ctx,
            })

    action = _get_next_ui_action(state)

    if action == "name_form":
        from adgtk.tracking.project import get_prefix_list
        return _t().TemplateResponse(
            request, "partials/builder_name_form.html", {
                "state_json": state_json,
                "editing_name": state.editing_name,
                "prefixes": get_prefix_list(),
                "scenario_factory_id": state.scenario_factory_id,
            })

    frame = state.stack[-1]
    interview = fac.get_interview(frame.factory_id)
    current_q = interview[frame.q_index]
    prefix = _get_prefill_prefix(state)

    if action in ("expand_pick", "list_expand_pick"):
        if action == "list_expand_pick" and state.list_expand_ctx is None:
            state.list_expand_ctx = _ListExpandCtx(
                attribute=current_q.attribute,
                group=current_q.group or "",
                question_text=current_q.question,
                accumulated=[],
            )
            state_json = state.model_dump_json()

        entries = fac.list_entries(group=current_q.group or "")
        attr_key = f"{prefix}{current_q.attribute}._factory_id"
        prefill_fid = state.prefill.get(attr_key)
        count = (
            len(state.list_expand_ctx.accumulated)
            if state.list_expand_ctx else 0
        )
        return _t().TemplateResponse(
            request, "partials/builder_expand_pick.html", {
                "state_json": state_json,
                "question": current_q,
                "entries": entries,
                "is_list": action == "list_expand_pick",
                "count": count,
                "prefill_factory_id": prefill_fid,
            })

    # next_question
    prefill_val = state.prefill.get(f"{prefix}{current_q.attribute}")
    return _t().TemplateResponse(request, "partials/builder_question.html", {
        "state_json": state_json,
        "question": current_q,
        "component_id": frame.factory_id,
        "q_num": frame.q_index + 1,
        "q_total": len(interview),
        "prefill": prefill_val,
    })


# -- Multi-run helpers -------------------------------------------------------

def _write_transient_batch(
    task_id: str, experiment_name: str, n_runs: int, project_dir: str
) -> Path:
    from adgtk.utils.defaults import BATCH_DEF_DIR
    batch_dir = Path(project_dir) / BATCH_DEF_DIR
    batch_dir.mkdir(exist_ok=True)
    batch_name = f"_transient_{task_id}"
    batch_path = batch_dir / f"{batch_name}.yaml"
    batch_path.write_text(
        _yaml.safe_dump({
            "name": batch_name,
            "experiments": [experiment_name] * n_runs,
        }),
        encoding="utf-8",
    )
    return batch_path


async def _run_with_cleanup(
    task: TaskState, cmd: list[str], cwd: str, batch_path: Path
) -> None:
    try:
        await run_subprocess(task, cmd, cwd)
    finally:
        batch_path.unlink(missing_ok=True)


# -- Pages ------------------------------------------------------------------

@router.get("/experiments", response_class=HTMLResponse)
async def experiments_page(request: Request):
    from adgtk.tracking.project import get_available_experiments
    experiments = get_available_experiments()
    return _t().TemplateResponse(
        request,
        "experiments.html",
        {"experiments": experiments, "active": "experiments"},
    )


# -- Builder wizard ----------------------------------------------------------

@router.get("/experiments/builder", response_class=HTMLResponse)
async def builder_scenario_list(request: Request):
    import adgtk.factory.component as fac
    scenarios = fac.list_entries(group="scenario")
    return _t().TemplateResponse(
        request, "partials/builder_scenario_list.html", {
            "scenarios": scenarios,
        })


@router.post("/experiments/builder/start", response_class=HTMLResponse)
async def builder_start(
    request: Request, scenario_factory_id: str = Form(...)
):
    state = _BuilderState(
        scenario_factory_id=scenario_factory_id,
        stack=[_BuilderStackFrame(
            attribute="scenario",
            factory_id=scenario_factory_id,
            factory_init=True,
            q_index=0,
            answers=[],
        )],
    )
    return _render_builder_step(request, state)


@router.post("/experiments/builder/answer", response_class=HTMLResponse)
async def builder_answer(request: Request):
    import adgtk.factory.component as fac
    form = await request.form()
    state = _BuilderState.model_validate_json(
        str(form.get("state_json", "{}"))
    )

    frame = state.stack[-1]
    interview = fac.get_interview(frame.factory_id)
    current_q = interview[frame.q_index]

    value = await _parse_form_answer(
        form, current_q.attribute, current_q.entry_type
    )
    frame.answers.append({
        "attribute": current_q.attribute,
        "factory_id": None,
        "factory_init": False,
        "init_config": value,
    })
    frame.q_index += 1

    return _render_builder_step(request, state)


@router.post("/experiments/builder/expand-pick", response_class=HTMLResponse)
async def builder_expand_pick(request: Request):
    import adgtk.factory.component as fac
    form = await request.form()
    state = _BuilderState.model_validate_json(
        str(form.get("state_json", "{}"))
    )
    picked_fid = str(form.get("picked_factory_id", ""))

    frame = state.stack[-1]
    interview = fac.get_interview(frame.factory_id)
    current_q = interview[frame.q_index]

    sub_interview = fac.get_interview(picked_fid)

    if len(sub_interview) == 0:
        # Component needs no configuration — add directly
        entry = {
            "attribute": current_q.attribute,
            "factory_id": picked_fid,
            "factory_init": True,
            "init_config": [],
        }
        if state.list_expand_ctx is not None:
            state.list_expand_ctx.accumulated.append(entry)
            state_json = state.model_dump_json()
            return _t().TemplateResponse(
                request, "partials/builder_list_expand_more.html", {
                    "state_json": state_json,
                    "ctx": state.list_expand_ctx,
                })
        frame.answers.append(entry)
        frame.q_index += 1
        return _render_builder_step(request, state)

    # Push new frame for sub-interview
    state.stack.append(_BuilderStackFrame(
        attribute=current_q.attribute,
        factory_id=picked_fid,
        factory_init=True,
        q_index=0,
        answers=[],
    ))
    return _render_builder_step(request, state)


@router.post(
    "/experiments/builder/list-expand-more", response_class=HTMLResponse
)
async def builder_list_expand_more(request: Request):
    form = await request.form()
    state = _BuilderState.model_validate_json(
        str(form.get("state_json", "{}"))
    )
    add_more = form.get("add_more", "no")

    if add_more == "yes":
        # Keep list_expand_ctx, re-render the picker
        return _render_builder_step(request, state)

    # Finalize the list
    ctx = state.list_expand_ctx
    assert ctx is not None
    state.list_expand_ctx = None

    frame = state.stack[-1]
    frame.answers.append({
        "attribute": ctx.attribute,
        "factory_id": None,
        "factory_init": False,
        "init_config": ctx.accumulated,
    })
    frame.q_index += 1
    return _render_builder_step(request, state)


@router.get("/experiments/builder/suggest-name", response_class=HTMLResponse)
async def builder_suggest_name(prefix: str = "exp"):
    """Return the next auto-generated name for a prefix."""
    from adgtk.tracking.project import generate_experiment_name
    try:
        name = generate_experiment_name(
            prefix=prefix.strip() or "exp", update_next="minor"
        )
        return HTMLResponse(name)
    except Exception:
        return HTMLResponse("exp.1.1", status_code=200)


@router.post("/experiments/builder/create", response_class=HTMLResponse)
async def builder_create(request: Request):
    form = await request.form()
    state = _BuilderState.model_validate_json(
        str(form.get("state_json", "{}"))
    )
    exp_name = str(form.get("exp_name", "")).strip()
    description = str(form.get("description", "")).strip()

    err = '<div class="text-red-600 text-sm px-6 py-2">'
    if not exp_name:
        return HTMLResponse(err + "Name is required.</div>")
    if not description:
        return HTMLResponse(err + "Description is required.</div>")

    from adgtk.experiment.structure import (
        AttributeEntry, ExperimentDefinition, EXPERIMENT_LABEL
    )

    path = Path("blueprints") / f"{exp_name}.yaml"
    if state.editing_name is None and path.exists():
        return HTMLResponse(
            err + f'Blueprint "{exp_name}" already exists.</div>'
        )

    try:
        scenario_entry = AttributeEntry.model_validate(state.completed)
        exp_def = ExperimentDefinition(
            attribute=EXPERIMENT_LABEL,
            description=description,
            factory_init=True,
            init_config=scenario_entry,
        )
        Path("blueprints").mkdir(exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            _yaml.safe_dump(
                exp_def.model_dump(),
                f,
                default_flow_style=False,
                sort_keys=False,
            )
    except Exception as exc:
        return HTMLResponse(
            f'<div class="text-red-600 text-sm px-6 py-2">Error: {exc}</div>'
        )

    response = HTMLResponse("", status_code=200)
    response.headers["HX-Redirect"] = "/experiments"
    return response


@router.get("/experiments/{name}/edit", response_class=HTMLResponse)
async def builder_edit(request: Request, name: str):
    path = Path("blueprints") / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(404, "Blueprint not found")

    raw = _yaml.safe_load(path.read_text(encoding="utf-8"))
    from adgtk.experiment.structure import AttributeEntry, ExperimentDefinition
    try:
        exp_def = ExperimentDefinition.model_validate(raw)
    except Exception:
        raise HTTPException(400, "Could not parse blueprint")

    scenario_entry = exp_def.init_config
    if not isinstance(scenario_entry, AttributeEntry):
        raise HTTPException(400, "Blueprint has no scenario factory_id")
    if not scenario_entry.factory_id:
        raise HTTPException(400, "Blueprint has no scenario factory_id")

    scenario_fid = scenario_entry.factory_id

    # Build prefill from existing scenario config
    prefill: dict = {}
    init_cfg = scenario_entry.init_config
    if isinstance(init_cfg, list):
        raw_list = [
            e.model_dump() if isinstance(e, BaseModel) else e
            for e in init_cfg
        ]
        prefill = _build_prefill(raw_list)

    state = _BuilderState(
        scenario_factory_id=scenario_fid,
        stack=[_BuilderStackFrame(
            attribute="scenario",
            factory_id=scenario_fid,
            factory_init=True,
            q_index=0,
            answers=[],
        )],
        editing_name=name,
        prefill=prefill,
    )
    return _render_builder_step(request, state)


# -- HTMX actions -----------------------------------------------------------

@router.post("/experiments/{name}/run", response_class=HTMLResponse)
async def run_experiment(name: str, request: Request):
    if get_active_tasks() or not task_safe_to_start():
        return HTMLResponse(
            '<div class="rounded-md border px-4 py-3 text-sm'
            ' bg-amber-50 text-amber-800 border-amber-200">'
            "An experiment is already running. Wait for it to finish"
            " before starting another.</div>"
        )
    from adgtk.api.server import get_config
    cfg = get_config()
    task = create_task(f"run: {name}", experiment_name=name)
    asyncio.create_task(
        run_subprocess(task, ["adgtk", "run", name], cwd=cfg.project_dir)
    )
    return HTMLResponse(
        "", headers={"HX-Redirect": f"/tasks/{task.task_id}"}
    )


@router.get("/experiments/{name}/runner", response_class=HTMLResponse)
async def runner_page(request: Request, name: str):
    path = Path("blueprints") / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(404, "Blueprint not found")
    return _t().TemplateResponse(request, "runner.html", {"name": name})


@router.post("/experiments/{name}/runner", response_class=HTMLResponse)
async def run_with_count(
    name: str, request: Request, n_runs: int = Form(1)
):
    if get_active_tasks() or not task_safe_to_start():
        return HTMLResponse(
            '<div class="rounded-md border px-4 py-3 text-sm'
            ' bg-amber-50 text-amber-800 border-amber-200">'
            "An experiment is already running. Wait for it to finish"
            " before starting another.</div>"
        )
    from adgtk.api.server import get_config
    cfg = get_config()

    if n_runs <= 1:
        task = create_task(f"run: {name}", experiment_name=name)
        asyncio.create_task(
            run_subprocess(task, ["adgtk", "run", name], cwd=cfg.project_dir)
        )
    else:
        task = create_task(f"run: {name} ×{n_runs}", experiment_name=name)
        batch_path = _write_transient_batch(
            task.task_id, name, n_runs, cfg.project_dir
        )
        asyncio.create_task(
            _run_with_cleanup(
                task,
                ["adgtk-batch", "run", batch_path.stem],
                cfg.project_dir,
                batch_path,
            )
        )

    return HTMLResponse("", headers={"HX-Redirect": f"/tasks/{task.task_id}"})


@router.post("/experiments/{name}/report", response_class=HTMLResponse)
async def experiment_report(name: str, request: Request):
    try:
        from adgtk.tracking.report import generate_experiment_report
        report_path, csv_path = generate_experiment_report(name)
        msg = f"Report saved to {report_path}"
        cls = "bg-green-50 text-green-800 border-green-200"
    except Exception as exc:
        msg = str(exc)
        cls = "bg-red-50 text-red-800 border-red-200"
    return HTMLResponse(
        f'<div class="rounded-md border px-4 py-3 text-sm {cls}">{msg}</div>'
    )


@router.get("/experiments/{name}/yaml", response_class=HTMLResponse)
async def get_yaml(name: str):
    path = Path("blueprints") / f"{name}.yaml"
    if not path.exists():
        raise HTTPException(404, "Blueprint not found")
    return HTMLResponse(path.read_text(encoding="utf-8"))


@router.put("/experiments/{name}/yaml", response_class=HTMLResponse)
async def save_yaml(name: str, content: str = Form(...)):
    path = Path("blueprints") / f"{name}.yaml"
    try:
        path.write_text(content, encoding="utf-8")
        cls = "bg-green-50 text-green-800 border-green-200"
        msg = "Blueprint saved."
    except Exception as exc:
        cls = "bg-red-50 text-red-800 border-red-200"
        msg = str(exc)
    return HTMLResponse(
        f'<div class="rounded-md border px-4 py-3 text-sm {cls}">{msg}</div>'
    )


@router.post("/experiments/copy", response_class=HTMLResponse)
async def copy_experiment(
    request: Request,
    source: str = Form(...),
    destination: str = Form(...),
):
    src = Path("blueprints") / f"{source}.yaml"
    dst = Path("blueprints") / f"{destination}.yaml"
    red = "bg-red-50 text-red-800 border-red-200"
    if not src.exists():
        msg = f"Blueprint '{source}' not found."
    elif dst.exists():
        msg = f"'{destination}' already exists."
    else:
        shutil.copy2(src, dst)
        return HTMLResponse("", headers={"HX-Refresh": "true"})
    return HTMLResponse(
        f'<div class="rounded-md border px-4 py-3 text-sm {red}">{msg}</div>'
    )
