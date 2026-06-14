"""ADGTK web server — FastAPI app with HTMX + Jinja2 frontend."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from adgtk.api.config import ServerConfig

_config: ServerConfig | None = None


def get_config() -> ServerConfig:
    assert _config is not None, "Server not initialised"
    return _config


def create_app(config: ServerConfig) -> FastAPI:
    global _config
    _config = config

    app = FastAPI(title="ADGTK", docs_url=None, redoc_url=None)

    # ── Auth middleware ──────────────────────────────────────────────────────
    if config.requires_auth and config.token:
        from adgtk.api.auth import TokenAuthMiddleware
        app.add_middleware(TokenAuthMiddleware, token=config.token)

    # ── Static files ─────────────────────────────────────────────────────────
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount(
            "/static", StaticFiles(directory=str(static_dir)), name="static"
        )

    # ── Templates ────────────────────────────────────────────────────────────
    templates = Jinja2Templates(
        directory=str(Path(__file__).parent / "templates")
    )

    # ── Routes ───────────────────────────────────────────────────────────────
    from adgtk.api.routes import (
        batches, datasets, experiments, factory, logs,
        results, settings, stream, studies,
    )
    for module in (
        experiments, results, batches, studies, factory,
        datasets, stream, logs, settings,
    ):
        module.init(templates)

    app.include_router(stream.router)
    app.include_router(experiments.router)
    app.include_router(results.router)
    app.include_router(batches.router)
    app.include_router(studies.router)
    app.include_router(factory.router)
    app.include_router(datasets.router)
    app.include_router(logs.router)
    app.include_router(settings.router)

    # ── Auth pages ───────────────────────────────────────────────────────────
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, next: str = "/"):
        return templates.TemplateResponse(
            request, "login.html", {"next": next}
        )

    @app.post("/auth/login", response_class=HTMLResponse)
    async def do_login(
        request: Request,
        token: str = Form(...),
        next: str = Form(default="/"),
    ):
        if config.requires_auth and token == config.token:
            response = RedirectResponse(url=next, status_code=302)
            response.set_cookie(
                "adgtk_token", token, httponly=True, samesite="lax"
            )
            return response
        return templates.TemplateResponse(
            request,
            "login.html",
            {"next": next, "error": "Invalid token."},
            status_code=401,
        )

    # ── Dashboard ────────────────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        from adgtk.tracking.runs import get_runs
        from adgtk.tracking.project import get_available_experiments
        recent_runs = get_runs(None)[-5:][::-1]
        blueprints = get_available_experiments()
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "project_name": Path(config.project_dir).name,
                "experiment_count": len(blueprints),
                "recent_run_count": len(recent_runs),
                "recent_runs": recent_runs,
                "blueprints": blueprints,
                "active": "dashboard",
            },
        )

    @app.get("/dashboard/recent-runs", response_class=HTMLResponse)
    async def dashboard_recent_runs(request: Request):
        from adgtk.tracking.runs import get_runs
        recent_runs = get_runs(None)[-5:][::-1]
        return templates.TemplateResponse(
            request,
            "partials/dashboard_recent_runs.html",
            {"recent_runs": recent_runs},
        )

    @app.get("/dashboard/stats", response_class=HTMLResponse)
    async def dashboard_stats(request: Request):
        from adgtk.tracking.runs import get_runs
        from adgtk.tracking.project import get_available_experiments
        blueprints = get_available_experiments()
        recent_runs = get_runs(None)[-5:]
        return templates.TemplateResponse(
            request,
            "partials/dashboard_stats.html",
            {
                "experiment_count": len(blueprints),
                "recent_run_count": len(recent_runs),
            },
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start the ADGTK web interface.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  adgtk-web --project-dir ~/research/my-project\n"
            "  adgtk-web --project-dir ~/research/my-project --no-auth\n"
            "  adgtk-web --project-dir ~/research/my-project --token mysecret"
        ),
    )
    parser.add_argument("--project-dir", metavar="PATH", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--token", default=None, help="Auth token (random if omitted)"
    )
    parser.add_argument(
        "--no-auth", action="store_true", help="Disable authentication"
    )
    args = parser.parse_args()

    if args.project_dir:
        os.chdir(os.path.expanduser(args.project_dir))

    from adgtk.cli.bootstrap import in_project, run_bootstrap
    if not in_project():
        print(
            f"ERROR: '{os.getcwd()}' is not a valid ADGTK project directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    run_bootstrap()

    from adgtk.experiment.task_record import (
        cleanup_orphaned_tasks,
        purge_old_task_records,
    )
    from adgtk.utils.project_settings import load_project_settings
    cleanup_orphaned_tasks()
    _ps = load_project_settings()
    if _ps.tasks.auto_cleanup:
        purge_old_task_records(
            max_age_days=_ps.tasks.ttl_days,
            max_count=_ps.tasks.max_count,
        )

    config = ServerConfig(
        project_dir=os.getcwd(),
        host=args.host,
        port=args.port,
        token=args.token,
        no_auth=args.no_auth,
    )

    print("\n  ADGTK Web Interface")
    print(f"  {config.launch_url}\n")

    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port, log_level="warning")


if __name__ == "__main__":
    main()
