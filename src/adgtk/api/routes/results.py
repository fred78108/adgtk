"""Results routes — experiment list, run list, run detail, export, validate."""

from __future__ import annotations

import csv as _csv
import json
from pathlib import Path
from typing import Literal, cast
from urllib.parse import quote as _urlquote

import yaml as _yaml
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

router = APIRouter()
_templates: Jinja2Templates | None = None


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


@router.get("/results", response_class=HTMLResponse)
async def results_index(request: Request):
    from adgtk.tracking.runs import get_experiment_names, get_runs
    names = get_experiment_names()
    summary = []
    for name in names:
        runs = get_runs(name)
        last = runs[0] if runs else None
        summary.append({
            "name": name,
            "count": len(runs),
            "last_verdict": getattr(last, "verdict", "—") if last else "—",
            "last_status": getattr(last, "status", "—") if last else "—",
            "last_run": getattr(last, "timestamp_start", "—") if last else "—",
            "has_missing": any(
                not Path(r.results_path).exists() for r in runs
            ),
        })
    return _t().TemplateResponse(
        request,
        "results_index.html",
        {"experiments": summary, "active": "results"},
    )


@router.get("/results/{experiment}", response_class=HTMLResponse)
async def results_runs(
    experiment: str, request: Request, tab: str | None = None
):
    import markdown as _md  # type: ignore[import-untyped]
    from adgtk.tracking.runs import get_runs
    from adgtk.utils.defaults import EXP_RESULTS_FOLDER

    runs = get_runs(experiment)

    exp_path = Path(EXP_RESULTS_FOLDER) / experiment
    report_path = exp_path / "experiment_report.md"
    report_html = None
    report_generated = False

    if exp_path.exists():
        should_generate = not report_path.exists()
        if not should_generate:
            report_mtime = report_path.stat().st_mtime
            for _run_dir in exp_path.iterdir():
                if not _run_dir.is_dir() or _run_dir.name == "common":
                    continue
                _manifest = _run_dir / "conclusions" / "run.manifest.json"
                if (
                    _manifest.exists()
                    and _manifest.stat().st_mtime > report_mtime
                ):
                    should_generate = True
                    break
        if should_generate:
            try:
                from adgtk.tracking.report import generate_experiment_report
                generate_experiment_report(experiment)
                report_generated = True
            except Exception:
                pass

    if report_path.exists():
        report_md = report_path.read_text(encoding="utf-8")
        report_html = _md.markdown(
            report_md, extensions=["tables", "fenced_code"]
        )

    initial_tab = tab if tab in ("runs", "report", "journal") else (
        "report" if report_html else "runs"
    )

    from adgtk.tracking.experiment_journal import load_journal
    journal_entries = load_journal(
        str(exp_path / "common")
    )

    return _t().TemplateResponse(
        request,
        "results_runs.html",
        {
            "experiment": experiment,
            "runs": runs,
            "report_html": report_html,
            "report_generated": report_generated,
            "initial_tab": initial_tab,
            "journal_entries": journal_entries,
            "active": "results",
        },
    )


@router.post("/results/{experiment}/report", response_class=HTMLResponse)
async def regenerate_report(experiment: str, request: Request):
    import markdown as _md  # type: ignore[import-untyped]
    from adgtk.tracking.report import generate_experiment_report

    try:
        report_path, _ = generate_experiment_report(experiment)
        report_md = Path(report_path).read_text(encoding="utf-8")
        report_html = _md.markdown(
            report_md, extensions=["tables", "fenced_code"]
        )
        error = None
    except Exception as exc:
        report_html = None
        error = str(exc)

    return _t().TemplateResponse(
        request,
        "partials/experiment_report.html",
        {"report_html": report_html, "error": error},
    )


def _read_agent_metric_series(
    metrics_dir: Path,
) -> dict[str, list[float]]:
    """Load raw per-step data from agent.*.csv files."""
    series: dict[str, list[float]] = {}
    if not metrics_dir.exists():
        return series
    for csv_path in sorted(metrics_dir.glob("agent.*.csv")):
        key = csv_path.stem  # e.g. "agent.latency"
        try:
            import csv as _csv_mod
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = _csv_mod.reader(f)
                for row in reader:
                    vals = []
                    for cell in row:
                        cell = cell.strip()
                        if cell:
                            try:
                                vals.append(float(cell))
                            except ValueError:
                                pass
                    if vals:
                        series[key] = vals
                        break
        except Exception:
            pass
    return series


@router.get("/results/{experiment}/{run_id}", response_class=HTMLResponse)
async def run_detail(experiment: str, run_id: str, request: Request):
    results_path = Path("results") / experiment / run_id
    if not results_path.exists():
        return HTMLResponse("Run not found.", status_code=404)

    results_data = manifest_data = config_data = report_md = None

    conclusions = results_path / "conclusions"
    rf = conclusions / "results.yaml"
    if rf.exists():
        results_data = _yaml.safe_load(rf.read_text(encoding="utf-8"))
    mf = conclusions / "run.manifest.json"
    if mf.exists():
        manifest_data = json.loads(mf.read_text(encoding="utf-8"))
        for a in (manifest_data.get("artifacts") or []):
            ep = _urlquote(a.get("path", ""), safe="")
            a["view_url"] = (
                f"/results/{experiment}/{run_id}/artifact?path={ep}"
            )
    rep = conclusions / "report.md"
    if rep.exists():
        report_md = rep.read_text(encoding="utf-8")
    cf = results_path / "run.exp.config.yaml"
    if cf.exists():
        config_data = _yaml.safe_load(cf.read_text(encoding="utf-8"))

    images_dir = results_path / "images"
    image_files = (
        sorted(
            f.name for f in images_dir.iterdir()
            if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".gif"}
        )
        if images_dir.exists() else []
    )

    metrics = (results_data or {}).get("metrics") or {}
    numeric_metrics = {
        k: v for k, v in metrics.items() if isinstance(v, (int, float))
    }
    max_metric_val = (
        max((abs(v) for v in numeric_metrics.values()), default=1) or 1
    )

    # Raw agent metric time-series (one value per step)
    agent_series = _read_agent_metric_series(results_path / "metrics")

    # LLM interaction logs stored under results/{exp}/{run}/llm/
    from adgtk.api.routes.logs import read_tail as _read_tail
    llm_logs: dict[str, str] = {}
    llm_dir = results_path / "llm"
    if llm_dir.exists():
        for lf in (
            sorted(llm_dir.glob("*.log"))
            + sorted(llm_dir.glob("*.jsonl"))
        ):
            llm_logs[lf.name] = _read_tail(lf)

    # Per-run scenario log stored alongside the run results
    scenario_log_path = results_path / "scenario.log"
    scenario_log = (
        _read_tail(scenario_log_path)
        if scenario_log_path.exists() else None
    )

    from adgtk.tracking.researcher_notes import load_notes
    researcher_notes = load_notes(str(conclusions))

    return _t().TemplateResponse(
        request,
        "results_detail.html",
        {
            "experiment": experiment,
            "run_id": run_id,
            "results": results_data,
            "manifest": manifest_data,
            "config": config_data,
            "report_md": report_md,
            "image_files": image_files,
            "numeric_metrics": numeric_metrics,
            "max_metric_val": max_metric_val,
            "agent_series": agent_series,
            "llm_logs": llm_logs,
            "scenario_log": scenario_log,
            "researcher_notes": researcher_notes,
            "active": "results",
        },
    )


@router.get("/results/{experiment}/{run_id}/lograw")
async def run_log_raw(experiment: str, run_id: str, name: str = ""):
    from fastapi.responses import PlainTextResponse
    from adgtk.api.routes.logs import read_tail as _read_tail
    results_path = Path("results") / experiment / run_id
    if name == "scenario":
        log_path = results_path / "scenario.log"
    elif (
        name.startswith("llm/")
        and "/" not in name[4:]
        and (name.endswith(".log") or name.endswith(".jsonl"))
    ):
        log_path = results_path / "llm" / name[4:]
    else:
        return PlainTextResponse("", status_code=400)
    try:
        resolved = log_path.resolve()
        root = results_path.resolve()
        if not str(resolved).startswith(str(root)):
            return PlainTextResponse("", status_code=403)
    except Exception:
        return PlainTextResponse("", status_code=403)
    return PlainTextResponse(_read_tail(log_path))


@router.get("/results/{experiment}/{run_id}/images/{filename}")
async def run_image(experiment: str, run_id: str, filename: str):
    from fastapi.responses import FileResponse
    img_path = Path("results") / experiment / run_id / "images" / filename
    if not img_path.exists() or not img_path.is_file():
        return Response(status_code=404)
    return FileResponse(str(img_path))


def _validate_artifact_path(path_str: str) -> Path | None:
    """Resolve artifact path; ensure it stays within the working dir."""
    if not path_str:
        return None
    try:
        p = Path(path_str)
        if not p.is_absolute():
            p = Path.cwd() / p
        p = p.resolve()
        cwd = Path.cwd().resolve()
        if not str(p).startswith(str(cwd) + "/"):
            return None
        if not p.exists() or not p.is_file():
            return None
        return p
    except Exception:
        return None


_CSV_EXTS = {".csv", ".tsv"}
_TEXT_EXTS = {
    ".txt", ".log", ".md", ".json", ".yaml", ".yml",
    ".py", ".toml", ".ini", ".cfg", ".rst", ".sh", ".xml",
}
_PREVIEW_LIMIT = 50


@router.get("/results/{experiment}/{run_id}/artifact/download")
async def artifact_download(experiment: str, run_id: str, path: str = ""):
    from fastapi.responses import FileResponse
    artifact_path = _validate_artifact_path(path)
    if artifact_path is None:
        return Response(status_code=404)
    return FileResponse(
        str(artifact_path),
        filename=artifact_path.name,
        headers={
            "Content-Disposition":
                f'attachment; filename="{artifact_path.name}"',
        },
    )


@router.get(
    "/results/{experiment}/{run_id}/artifact",
    response_class=HTMLResponse,
)
async def artifact_view(
    experiment: str, run_id: str, request: Request, path: str = ""
):
    artifact_path = _validate_artifact_path(path)
    if artifact_path is None:
        return HTMLResponse(
            "Artifact not found or access denied.", status_code=404
        )

    suffix = artifact_path.suffix.lower()
    filename = artifact_path.name
    file_size = artifact_path.stat().st_size

    if suffix in _CSV_EXTS:
        preview_type = "csv"
    elif suffix in _TEXT_EXTS:
        preview_type = "text"
    else:
        preview_type = "other"

    csv_headers: list | None = None
    csv_rows: list | None = None
    text_content: str | None = None
    truncated = False
    preview_error: str | None = None

    if preview_type == "csv":
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            with open(
                artifact_path, "r",
                encoding="utf-8", errors="replace",
            ) as f:
                reader = _csv.reader(f, delimiter=delimiter)
                csv_headers = next(reader, [])
                rows: list[list[str]] = []
                for row in reader:
                    if len(rows) >= _PREVIEW_LIMIT + 1:
                        break
                    rows.append(row)
            truncated = len(rows) > _PREVIEW_LIMIT
            csv_rows = rows[:_PREVIEW_LIMIT]
        except Exception as exc:
            preview_type = "error"
            preview_error = str(exc)

    elif preview_type == "text":
        try:
            with open(
                artifact_path, "r",
                encoding="utf-8", errors="replace",
            ) as f:
                lines: list[str] = []
                for line in f:
                    if len(lines) >= _PREVIEW_LIMIT + 1:
                        break
                    lines.append(line)
            truncated = len(lines) > _PREVIEW_LIMIT
            text_content = "".join(lines[:_PREVIEW_LIMIT])
        except Exception as exc:
            preview_type = "error"
            preview_error = str(exc)

    ep = _urlquote(path, safe="")
    download_url = (
        f"/results/{experiment}/{run_id}/artifact/download?path={ep}"
    )

    return _t().TemplateResponse(
        request,
        "artifact_view.html",
        {
            "experiment": experiment,
            "run_id": run_id,
            "filename": filename,
            "path": path,
            "file_size": file_size,
            "preview_type": preview_type,
            "csv_headers": csv_headers,
            "csv_rows": csv_rows,
            "text_content": text_content,
            "truncated": truncated,
            "preview_error": preview_error,
            "download_url": download_url,
            "active": "results",
        },
    )


def _notes_response(
    request: Request,
    experiment: str,
    run_id: str,
    conclusion_folder: Path,
):
    from adgtk.tracking.researcher_notes import load_notes
    notes = load_notes(str(conclusion_folder))
    return _t().TemplateResponse(
        request,
        "partials/researcher_notes.html",
        {"notes": notes, "experiment": experiment, "run_id": run_id},
    )


@router.get(
    "/results/{experiment}/{run_id}/notes",
    response_class=HTMLResponse,
)
async def get_notes(experiment: str, run_id: str, request: Request):
    conclusion_folder = (
        Path("results") / experiment / run_id / "conclusions"
    )
    return _notes_response(request, experiment, run_id, conclusion_folder)


@router.post(
    "/results/{experiment}/{run_id}/notes",
    response_class=HTMLResponse,
)
async def add_note(experiment: str, run_id: str, request: Request):
    from adgtk.tracking.researcher_notes import add_note as _add_note
    form = await request.form()
    text = str(form.get("text") or "").strip()
    conclusion_folder = Path("results") / experiment / run_id / "conclusions"
    if text:
        _add_note(text, str(conclusion_folder))
    return _notes_response(request, experiment, run_id, conclusion_folder)


@router.delete(
    "/results/{experiment}/{run_id}/notes/{note_id}",
    response_class=HTMLResponse,
)
async def delete_note(
    experiment: str, run_id: str, note_id: str, request: Request
):
    from adgtk.tracking.researcher_notes import delete_note as _delete_note
    conclusion_folder = Path("results") / experiment / run_id / "conclusions"
    _delete_note(note_id, str(conclusion_folder))
    return _notes_response(request, experiment, run_id, conclusion_folder)


def _journal_response(
    request: Request,
    experiment: str,
    common_folder: Path,
):
    from adgtk.tracking.experiment_journal import load_journal
    entries = load_journal(str(common_folder))
    return _t().TemplateResponse(
        request,
        "partials/experiment_journal.html",
        {"entries": entries, "experiment": experiment},
    )


@router.get(
    "/results/{experiment}/journal", response_class=HTMLResponse
)
async def get_journal(experiment: str, request: Request):
    common_folder = Path("results") / experiment / "common"
    return _journal_response(request, experiment, common_folder)


@router.post(
    "/results/{experiment}/journal", response_class=HTMLResponse
)
async def add_journal_entry(experiment: str, request: Request):
    from adgtk.tracking.experiment_journal import (
        add_entry as _add_entry,
    )
    form = await request.form()
    text = str(form.get("text") or "").strip()
    _VALID_TYPES = {"note", "hypothesis", "finding", "question"}
    entry_type_raw = str(form.get("entry_type") or "note").strip()
    entry_type = cast(
        Literal["note", "hypothesis", "finding", "question"],
        entry_type_raw if entry_type_raw in _VALID_TYPES else "note",
    )
    tags_raw = str(form.get("tags") or "").strip()
    linked_run_id = str(form.get("linked_run_id") or "").strip() or None
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
    common_folder = Path("results") / experiment / "common"
    if text:
        _add_entry(
            text,
            str(common_folder),
            entry_type=entry_type,
            tags=tags,
            linked_run_id=linked_run_id,
        )
    return _journal_response(request, experiment, common_folder)


@router.delete(
    "/results/{experiment}/journal/{entry_id}",
    response_class=HTMLResponse,
)
async def delete_journal_entry(
    experiment: str, entry_id: str, request: Request
):
    from adgtk.tracking.experiment_journal import (
        delete_entry as _delete_entry,
    )
    common_folder = Path("results") / experiment / "common"
    _delete_entry(entry_id, str(common_folder))
    return _journal_response(request, experiment, common_folder)


@router.post("/results/sync", response_class=HTMLResponse)
async def sync_results(request: Request):
    import datetime
    import os
    from adgtk.tracking.runs import (
        get_runs, add_run, remove_run, get_experiment_names,
    )
    from adgtk.tracking.structure import RunEntryModel
    from adgtk.utils.defaults import EXP_RESULTS_FOLDER

    CONCLUSIONS_DIR = "conclusions"
    RESULTS_FILE = "results.yaml"

    runs = get_runs(None)

    # Remove registry entries whose results folder no longer exists on disk
    removed = []
    for r in runs:
        if not Path(r.results_path).exists():
            remove_run(r.run_id, r.experiment_name)
            removed.append({
                "experiment": r.experiment_name,
                "run_id": r.run_id,
            })

    # Re-fetch after removals, then add on-disk runs missing from registry
    runs = get_runs(None)
    run_set = {(r.experiment_name, r.run_id) for r in runs}
    added = []

    if Path(EXP_RESULTS_FOLDER).exists():
        for exp_name in sorted(os.listdir(EXP_RESULTS_FOLDER)):
            exp_path = Path(EXP_RESULTS_FOLDER) / exp_name
            if not exp_path.is_dir():
                continue
            for run_dir in sorted(os.listdir(exp_path)):
                if run_dir == "common":
                    continue
                run_path = exp_path / run_dir
                if not run_path.is_dir():
                    continue
                if (exp_name, run_dir) in run_set:
                    continue
                results_file = run_path / CONCLUSIONS_DIR / RESULTS_FILE
                status = "complete" if results_file.exists() else "incomplete"
                mtime = run_path.stat().st_mtime
                ts = datetime.datetime.fromtimestamp(mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                add_run(RunEntryModel(
                    run_id=run_dir,
                    experiment_name=exp_name,
                    timestamp_start=ts,
                    timestamp_end=None,
                    duration_seconds=None,
                    status=cast(
                        Literal["complete", "incomplete", "results_missing"],
                        status,
                    ),
                    results_path=str(run_path),
                ))
                added.append({
                    "experiment": exp_name,
                    "run_id": run_dir,
                    "status": status,
                })

    # Rebuild experiments summary for OOB table refresh
    names = get_experiment_names()
    summary = []
    for name in names:
        exp_runs = get_runs(name)
        last = exp_runs[0] if exp_runs else None
        summary.append({
            "name": name,
            "count": len(exp_runs),
            "last_verdict": getattr(last, "verdict", "—") if last else "—",
            "last_status": getattr(last, "status", "—") if last else "—",
            "last_run": getattr(last, "timestamp_start", "—") if last else "—",
            "has_missing": any(
                not Path(r.results_path).exists() for r in exp_runs
            ),
        })

    return _t().TemplateResponse(
        request,
        "partials/sync_results.html",
        {"added": added, "removed": removed, "experiments": summary},
    )


@router.post("/results/validate", response_class=HTMLResponse)
async def validate_results(request: Request):
    from adgtk.tracking.runs import get_runs
    runs = get_runs(None)
    results_root = Path("results")
    registered = {r.results_path for r in runs}
    orphaned, incomplete, missing = [], [], []

    if results_root.exists():
        for exp_dir in results_root.iterdir():
            if not exp_dir.is_dir():
                continue
            for run_dir in exp_dir.iterdir():
                if run_dir.is_dir() and str(run_dir) not in registered:
                    orphaned.append(str(run_dir))

    for run in runs:
        p = Path(run.results_path)
        if not p.exists():
            missing.append(run.run_id)
        elif not (p / "conclusions" / "results.yaml").exists():
            incomplete.append(run.run_id)

    healthy = not (orphaned or incomplete or missing)
    return _t().TemplateResponse(
        request,
        "partials/validate_results.html",
        {
            "healthy": healthy,
            "orphaned": orphaned,
            "incomplete": incomplete,
            "missing": missing,
        },
    )
