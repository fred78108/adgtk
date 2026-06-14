"""Logs routes — browse and view framework/common/run log files."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
_templates: Jinja2Templates | None = None

LOG_DIR = Path("logs")
MAX_LOG_BYTES = 200_000  # tail last 200 KB


def init(templates: Jinja2Templates) -> None:
    global _templates
    _templates = templates


def _t() -> Jinja2Templates:
    assert _templates is not None
    return _templates


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", text)


def read_tail(path: Path, max_bytes: int = MAX_LOG_BYTES) -> str:
    if not path.exists() or not path.is_file():
        return ""
    size = path.stat().st_size
    with path.open("r", encoding="utf-8", errors="replace") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
            f.readline()  # discard partial first line
        return strip_ansi(f.read())


def collect_log_groups() -> dict[str, list[dict]]:
    """Return log files grouped by category label."""
    groups: dict[str, list[dict]] = {}

    for cat in ("framework", "common"):
        cat_path = LOG_DIR / cat
        if cat_path.exists():
            files = sorted(cat_path.glob("*.log"))
            if files:
                groups[cat] = [
                    {"name": f.name, "key": f"{cat}/{f.name}",
                     "size": f.stat().st_size}
                    for f in files
                ]

    runs_path = LOG_DIR / "runs"
    if runs_path.exists():
        for exp_dir in sorted(runs_path.iterdir()):
            if not exp_dir.is_dir():
                continue
            files = (
                sorted(exp_dir.glob("*.log"))
                + sorted(exp_dir.glob("*.jsonl"))
            )
            agent_dir = exp_dir / "agent"
            if agent_dir.exists():
                files += (
                    sorted(agent_dir.glob("*.log"))
                    + sorted(agent_dir.glob("*.jsonl"))
                )
            if files:
                label = f"runs/{exp_dir.name}"
                groups[label] = [
                    {"name": f.name,
                     "key": str(f.relative_to(LOG_DIR)),
                     "size": f.stat().st_size}
                    for f in files
                ]

    return groups


def _safe_log_path(key: str) -> Path | None:
    """Resolve a log key to an absolute path, confined to LOG_DIR."""
    try:
        resolved = (LOG_DIR / key).resolve()
        root = LOG_DIR.resolve()
        if str(resolved).startswith(str(root) + "/") or resolved == root:
            return resolved
    except Exception:
        pass
    return None


@router.get("/logs/raw")
async def logs_raw(file: str | None = None):
    from fastapi.responses import PlainTextResponse
    if not file:
        return PlainTextResponse("", status_code=400)
    log_path = _safe_log_path(file)
    if not log_path:
        return PlainTextResponse("", status_code=403)
    return PlainTextResponse(read_tail(log_path))


@router.get("/logs", response_class=HTMLResponse)
async def logs_index(request: Request, file: str | None = None):
    groups = collect_log_groups()
    content = ""
    selected = None

    if file:
        log_path = _safe_log_path(file)
        if log_path:
            content = read_tail(log_path)
            selected = file

    return _t().TemplateResponse(
        request,
        "logs.html",
        {
            "groups": groups,
            "content": content,
            "selected": selected,
            "active": "logs",
        },
    )
