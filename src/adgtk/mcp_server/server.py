"""ADGTK MCP Server.

Exposes ADGTK project operations as MCP tools so Claude and other agents
can run experiments, inspect results, and manage studies.

Usage:
    adgtk-mcp --project-dir /path/to/project

The server must be started from (or pointed at) a valid ADGTK project
directory. It calls run_bootstrap() once at startup to register all
user-defined components with the factory.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ADGTK",
    instructions=(
        "Tools for managing ADGTK (Agentic Data Generation Toolkit) research "
        "projects. Use these tools to run experiments, inspect results, "
        "generate reports, and analyse cross-experiment studies. All "
        "operations act on the project directory the server was started with."
    ),
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_dict(obj: Any) -> Any:
    """Recursively convert ADGTK model objects to JSON-serialisable types."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(i) for i in obj]
    if hasattr(obj, "__dict__"):
        return {k: _to_dict(v) for k, v in obj.__dict__.items()
                if not k.startswith("_")}
    return obj


# ─── Project ─────────────────────────────────────────────────────────────────

@mcp.tool()
def project_status() -> dict:
    """Return validation status and directory of the active ADGTK project."""
    from adgtk.cli.bootstrap import in_project
    return {
        "project_dir": os.getcwd(),
        "valid": in_project(),
    }


# ─── Experiments ─────────────────────────────────────────────────────────────

@mcp.tool()
def list_experiments() -> list[dict]:
    """List all experiment blueprints available in the project."""
    from adgtk.tracking.project import get_available_experiments
    return [_to_dict(e) for e in get_available_experiments()]


@mcp.tool()
def run_experiment(name: str) -> dict:
    """Run an experiment blueprint and return the result summary.

    Args:
        name: Experiment blueprint name (without .yaml extension).
    """
    from adgtk.experiment.runner import run_scenario
    try:
        result, folders = run_scenario(
            filename=name,
            append_timestamp=False,
            use_count=True,
            print_to_console=False,
        )
        return {
            "status": "complete",
            "experiment": name,
            "results_path": str(folders.root_dir) if folders else None,
            "result": _to_dict(result),
        }
    except FileNotFoundError:
        return {"status": "error", "error": f"Blueprint '{name}' not found."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def generate_experiment_report(experiment_name: str) -> dict:
    """Generate a markdown and CSV report for a completed experiment.

    Args:
        experiment_name: Name of the experiment to report on.
    """
    from adgtk.tracking.report import generate_experiment_report as _gen
    try:
        report_path, csv_path = _gen(experiment_name)
        return {
            "status": "complete",
            "report_path": report_path,
            "csv_path": csv_path,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def copy_experiment(source: str, destination: str) -> dict:
    """Copy an experiment blueprint to a new name.

    Args:
        source: Existing blueprint name (without .yaml extension).
        destination: Name for the new blueprint (without .yaml extension).
    """
    import shutil
    src = Path("blueprints") / f"{source}.yaml"
    dst = Path("blueprints") / f"{destination}.yaml"
    if not src.exists():
        return {"status": "error", "error": f"Blueprint '{source}' not found."}
    if dst.exists():
        return {
            "status": "error",
            "error": f"Blueprint '{destination}' already exists."
        }
    try:
        shutil.copy2(src, dst)
        return {"status": "complete", "copied_to": str(dst)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Batches ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_batches() -> list[str]:
    """List available batch job definition names."""
    batch_dir = Path("batches")
    if not batch_dir.exists():
        return []
    return sorted(f.stem for f in batch_dir.glob("*.yaml"))


@mcp.tool()
def run_batch(name: str) -> dict:
    """Run all experiments defined in a batch file sequentially.

    Args:
        name: Batch job name (without .yaml extension).
    """
    from adgtk.experiment.runner import run_batch as _run
    try:
        _run(filename=name, print_to_console=False)
        return {"status": "complete", "batch": name}
    except FileNotFoundError:
        return {"status": "error", "error": f"Batch '{name}' not found."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Results ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_runs(experiment_name: str | None = None) -> list[dict]:
    """List experiment runs, optionally filtered to a single experiment.

    Args:
        experiment_name: Restrict to this experiment. Omit to list all runs.
    """
    from adgtk.tracking.runs import get_runs
    return [_to_dict(r) for r in get_runs(experiment_name)]


@mcp.tool()
def get_run_details(experiment_name: str, run_id: str) -> dict:
    """Return the config and results for a specific run.

    Args:
        experiment_name: Name of the experiment.
        run_id: Run identifier (e.g. run-001).
    """
    import yaml as _yaml

    results_root = Path("results") / experiment_name / run_id
    if not results_root.exists():
        return {
            "status": "error",
            "error": f"Run '{run_id}' not found for '{experiment_name}'."}

    data: dict = {
        "status": "complete",
        "experiment": experiment_name,
        "run_id": run_id,
    }

    results_file = results_root / "results.yaml"
    if results_file.exists():
        with open(results_file, encoding="utf-8") as fh:
            data["results"] = _yaml.safe_load(fh)

    config_file = results_root / "run.exp.config.yaml"
    if config_file.exists():
        with open(config_file, encoding="utf-8") as fh:
            data["config"] = _yaml.safe_load(fh)

    return data


@mcp.tool()
def export_results(experiment_name: str, format: str = "json") -> dict:
    """Export all run records for an experiment.

    Args:
        experiment_name: Name of the experiment.
        format: Output format — "json" (default) or "csv".
    """
    from adgtk.tracking.runs import get_runs
    runs = [_to_dict(r) for r in get_runs(experiment_name)]

    if format == "csv":
        import io
        import pandas as pd
        buf = io.StringIO()
        pd.DataFrame(runs).to_csv(buf, index=False)
        return {"status": "complete", "format": "csv", "data": buf.getvalue()}

    return {"status": "complete", "format": "json", "data": runs}


@mcp.tool()
def validate_results() -> dict:
    """Check the results registry for orphaned, incomplete, or missing runs."""
    from adgtk.tracking.runs import get_runs
    runs = get_runs(None)
    results_root = Path("results")

    registered_paths = {
        r.results_path for r in runs}  # type: ignore[attr-defined]
    orphaned: list[str] = []
    incomplete: list[dict] = []
    missing_folder: list[dict] = []

    if results_root.exists():
        for exp_dir in results_root.iterdir():
            if not exp_dir.is_dir():
                continue
            for run_dir in exp_dir.iterdir():
                if not run_dir.is_dir():
                    continue
                if str(run_dir) not in registered_paths:
                    orphaned.append(str(run_dir))

    for run in runs:
        path = Path(run.results_path)  # type: ignore[attr-defined]
        if not path.exists():
            missing_folder.append(_to_dict(run))
        elif not (path / "results.yaml").exists():
            incomplete.append(_to_dict(run))

    return {
        "healthy": not (orphaned or incomplete or missing_folder),
        "orphaned_folders": orphaned,
        "incomplete_runs": incomplete,
        "missing_folders": missing_folder,
    }


# ─── Studies ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_studies() -> list[str]:
    """List available study blueprint names."""
    from adgtk.experiment.study.builder import list_study_blueprints
    return list_study_blueprints()


@mcp.tool()
def run_study(name: str) -> dict:
    """Generate a cross-experiment study report.

    Args:
        name: Study blueprint name.
    """
    from adgtk.experiment.study.report import generate_study_report
    try:
        report_path, csv_path = generate_study_report(name)
        return {
            "status": "complete",
            "report_path": report_path,
            "csv_path": csv_path,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Factory ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_components(
    group: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """List registered factory components, optionally filtered.

    Args:
        group: Restrict to this component group (e.g. "scenario", "model").
        tags: Restrict to components carrying all of these tags.
    """
    from adgtk.factory.component import list_entries
    return [_to_dict(e) for e in list_entries(group=group, tags=tags)]


# ─── Datasets ────────────────────────────────────────────────────────────────

@mcp.tool()
def list_datasets() -> list[str]:
    """List the IDs of all datasets registered in this project."""
    from adgtk.data.dataset import DatasetManager
    try:
        return DatasetManager().get_file_ids_only()
    except Exception as e:
        return [f"error: {e}"]


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Start the ADGTK MCP server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  adgtk-mcp --project-dir ~/research/my-project\n\n"
            "Claude Desktop config (claude_desktop_config.json):\n"
            '  "adgtk": {\n'
            '    "command": "adgtk-mcp",\n'
            '    "args": ["--project-dir", "/abs/path/to/project"]\n'
            '  }'
        ),
    )
    help_str = "ADGTK project directory (defaults to current working "
    help_str += "directory)."
    parser.add_argument(
        "--project-dir",
        metavar="PATH",
        default=None,
        help=help_str,
    )
    args = parser.parse_args()

    if args.project_dir:
        target = os.path.expanduser(args.project_dir)
        os.chdir(target)

    from adgtk.cli.bootstrap import in_project, run_bootstrap
    if not in_project():
        print(
            f"ERROR: '{os.getcwd()}' is not a valid ADGTK project directory.\n"
            "Run `adgtk-project create <name>` to create one, or pass "
            "--project-dir to point at an existing project.",
            file=sys.stderr,
        )
        sys.exit(1)

    run_bootstrap()
    mcp.run()


if __name__ == "__main__":
    main()
