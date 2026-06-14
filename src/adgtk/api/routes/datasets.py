"""Dataset routes — list and manage registered datasets."""

from __future__ import annotations

import csv as _csv
from pathlib import Path
from typing import Literal, cast

from fastapi import APIRouter, Form, Request  # noqa: F401
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.templating import Jinja2Templates

router = APIRouter()
_templates: Jinja2Templates | None = None

_CSV_EXTS = {".csv", ".tsv"}
_TEXT_EXTS = {
    ".txt", ".log", ".md", ".json", ".yaml", ".yml",
    ".py", ".toml", ".ini", ".cfg", ".rst", ".sh", ".xml",
}
_PREVIEW_LIMIT = 50


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


def _build_preview(full_path: Path):
    """Build preview data for a dataset file.

    Returns a 6-tuple: (preview_type, csv_headers, csv_rows,
    text_content, truncated, error).
    """
    if not full_path.exists():
        return "missing", None, None, None, False, None

    suffix = full_path.suffix.lower()
    if suffix in _CSV_EXTS:
        preview_type = "csv"
    elif suffix in _TEXT_EXTS:
        preview_type = "text"
    else:
        preview_type = "other"

    csv_headers, csv_rows, text_content, preview_error = None, None, None, None
    truncated = False

    if preview_type == "csv":
        delimiter = "\t" if suffix == ".tsv" else ","
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
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
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
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

    return (
        preview_type, csv_headers, csv_rows,
        text_content, truncated, preview_error,
    )


@router.post("/datasets/register", response_class=HTMLResponse)
async def register_dataset(
    source_file: str = Form(...),
    encoding: str = Form("csv"),
    use: str = Form("other"),
    tags: str = Form(""),
    custom_id: str = Form(""),
    description: str = Form(""),
):
    from adgtk.data.dataset import DatasetManager
    try:
        new_tags = [t.strip() for t in tags.split(",") if t.strip()]
        mgr = DatasetManager()
        result_id = mgr.register(
            source_file=source_file.strip(),
            encoding=cast(
                Literal["csv", "hf-json", "json", "pickle", "pandas", "text"],
                encoding,
            ),
            tags=new_tags or None,
            file_id=custom_id.strip() or None,
            use=cast(Literal["test", "train", "validate", "other"], use),
            description=description.strip() or None,
        )
        return HTMLResponse(
            f'<div class="rounded-md border px-4 py-3 text-sm'
            f' bg-green-50 text-green-800 border-green-200">'
            f'Registered as <code class="font-mono">{result_id}</code>.'
            f' <a href="/datasets/{result_id}"'
            f'    class="ml-1 underline font-medium">View dataset →</a>'
            f'</div>',
            headers={"HX-Trigger": "datasetRegistered"},
        )
    except Exception as exc:
        return HTMLResponse(
            f'<div class="rounded-md border px-4 py-3 text-sm'
            f' bg-red-50 text-red-800 border-red-200">{exc}</div>'
        )


def _build_rows(datasets):
    from adgtk.data.dataset import find_blueprints_using_dataset
    rows = []
    for d in datasets:
        full_path = Path(d.path) / d.filename
        rows.append({
            "defn": d,
            "exists": full_path.exists(),
            "blueprints": find_blueprints_using_dataset(d.file_id),
        })
    return rows


@router.get("/datasets", response_class=HTMLResponse)
async def datasets_page(request: Request):
    from adgtk.data.dataset import DatasetManager
    mgr = DatasetManager()
    rows = _build_rows(mgr.list_files())
    return _t().TemplateResponse(
        request, "datasets.html", {"rows": rows, "active": "datasets"}
    )


@router.get("/datasets/table", response_class=HTMLResponse)
async def datasets_table(request: Request):
    """Partial used by HTMX to refresh the dataset list after registration."""
    from adgtk.data.dataset import DatasetManager
    mgr = DatasetManager()
    rows = _build_rows(mgr.list_files())
    return _t().TemplateResponse(
        request,
        "partials/datasets_table.html",
        {"rows": rows},
    )


@router.get("/datasets/{dataset_id}", response_class=HTMLResponse)
async def dataset_detail(dataset_id: str, request: Request):
    from adgtk.data.dataset import DatasetManager
    mgr = DatasetManager()
    try:
        defn = mgr.get_file_definition(dataset_id)
    except KeyError:
        return HTMLResponse("Dataset not found.", status_code=404)

    full_path = Path(defn.path) / defn.filename
    file_exists = full_path.exists()
    file_size = full_path.stat().st_size if file_exists else None

    (
        preview_type, csv_headers, csv_rows,
        text_content, truncated, preview_error,
    ) = _build_preview(full_path)

    import json as _json
    tags_str = ", ".join(defn.tags) if defn.tags else ""
    ext_meta_str = (
        _json.dumps(defn.extended_metadata, indent=2)
        if defn.extended_metadata else ""
    )

    return _t().TemplateResponse(
        request,
        "dataset_detail.html",
        {
            "defn": defn,
            "file_exists": file_exists,
            "file_size": file_size,
            "preview_type": preview_type,
            "csv_headers": csv_headers,
            "csv_rows": csv_rows,
            "text_content": text_content,
            "truncated": truncated,
            "preview_error": preview_error,
            "tags_str": tags_str,
            "ext_meta_str": ext_meta_str,
            "active": "datasets",
        },
    )


@router.get("/datasets/{dataset_id}/download")
async def dataset_download(dataset_id: str):
    from adgtk.data.dataset import DatasetManager
    mgr = DatasetManager()
    try:
        defn = mgr.get_file_definition(dataset_id)
    except KeyError:
        return Response(status_code=404)
    full_path = Path(defn.path) / defn.filename
    if not full_path.exists():
        return Response(status_code=404)
    return FileResponse(
        str(full_path),
        filename=defn.filename,
        headers={
            "Content-Disposition": f'attachment; filename="{defn.filename}"'
        },
    )


@router.post("/datasets/{dataset_id}/update", response_class=HTMLResponse)
async def update_dataset(
    dataset_id: str,
    new_id: str = Form(""),
    tags: str = Form(""),
    description: str = Form(""),
    extended_metadata: str = Form(""),
):
    import json as _json
    from adgtk.data.dataset import DatasetManager
    mgr = DatasetManager()
    try:
        new_tags = [t.strip() for t in tags.split(",") if t.strip()]
        resolved_id = new_id.strip() or dataset_id

        ext_meta: dict | None = None
        if extended_metadata.strip():
            try:
                ext_meta = _json.loads(extended_metadata.strip())
                if not isinstance(ext_meta, dict):
                    raise ValueError(
                        "Extended metadata must be a JSON object."
                    )
            except _json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON: {exc}") from exc

        result_id = mgr.update_file(
            dataset_id,
            new_id=resolved_id if resolved_id != dataset_id else None,
            new_tags=new_tags,
            new_description=description.strip() or None,
            new_extended_metadata=ext_meta,
        )
        if result_id != dataset_id:
            return HTMLResponse(
                "",
                status_code=200,
                headers={"HX-Redirect": f"/datasets/{result_id}"},
            )
        msg = "Dataset updated."
        cls = "bg-green-50 text-green-800 border-green-200"
    except Exception as exc:
        msg = str(exc)
        cls = "bg-red-50 text-red-800 border-red-200"
    return HTMLResponse(
        f'<div class="rounded-md border px-4 py-3 text-sm {cls}">{msg}</div>'
    )


@router.post("/datasets/{dataset_id}/retire", response_class=HTMLResponse)
async def retire_dataset(dataset_id: str):
    try:
        from adgtk.data.dataset import DatasetManager
        DatasetManager().retire_file(dataset_id)
        msg = f"Dataset '{dataset_id}' retired."
        cls = "bg-green-50 text-green-800 border-green-200"
    except Exception as exc:
        msg = str(exc)
        cls = "bg-red-50 text-red-800 border-red-200"
    return HTMLResponse(
        f'<div class="rounded-md border px-4 py-3 text-sm {cls}">{msg}</div>'
    )
