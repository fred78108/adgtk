"""adgtk-results: Results inventory and management CLI.

Must be run from within an ADGTK project directory.
"""

import argparse
import csv
import datetime
import io
import json
import os
import shutil
import sys
from typing import Optional, Literal

import yaml

from adgtk import __version__ as adgtk_ver
from adgtk.cli.bootstrap import require_project
from adgtk.utils.defaults import EXP_RESULTS_FOLDER, LOG_DIR

CONCLUSIONS_DIR = "conclusions"
RESULTS_FILE = "results.yaml"
RUN_CONFIG_FILE = "run.exp.config.yaml"


# ----------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------

def _folder_size(path: str) -> int:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total += os.path.getsize(fp)
    return total


def _fmt_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def _fmt_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "--"
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


def _confirm(prompt: str) -> bool:
    resp = input(f"{prompt} [y/N]: ").strip().lower()
    return resp in ("y", "yes")


# ----------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="adgtk-results",
        description="ADGTK results inventory and management")
    parser.add_argument(
        "--version", action="version", version=f"ADGTK {adgtk_ver}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # list [experiment]
    list_p = sub.add_parser(
        "list", help="List experiments or runs for one experiment")
    list_p.add_argument(
        "experiment", nargs="?", type=str,
        help="Experiment name — omit to list all experiments")

    # show <experiment> <run_id>
    show_p = sub.add_parser(
        "show", help="Show results and config for a specific run")
    show_p.add_argument("experiment", type=str)
    show_p.add_argument("run_id", type=str)

    # validate
    sub.add_parser(
        "validate",
        help="Report orphaned folders, incomplete runs, & missing registries")

    # sync
    sub.add_parser(
        "sync",
        help="Register on-disk runs that are missing from the registry")

    # disk-usage [experiment]
    du_p = sub.add_parser("disk-usage", help="Show disk usage for results")
    du_p.add_argument(
        "experiment", nargs="?", type=str,
        help="Experiment name — omit for all experiments")

    # export <experiment>
    export_p = sub.add_parser(
        "export", help="Export run results to JSON or CSV")
    export_p.add_argument("experiment", type=str)
    export_p.add_argument(
        "--format", choices=["json", "csv"], default="json",
        help="Output format (default: json)")
    export_p.add_argument(
        "--output", type=str, default=None,
        help="Output file path — prints to stdout if omitted")

    # prune <experiment> --keep N
    prune_p = sub.add_parser(
        "prune",
        help="Keep N most recent runs, purge the rest")
    prune_p.add_argument("experiment", type=str)
    prune_p.add_argument(
        "--keep", type=int, required=True,
        help="Number of most recent runs to keep")
    prune_p.add_argument(
        "-y", "--yes", action="store_true",
        help="Skip confirmation prompt")

    # purge {run,experiment}
    purge_p = sub.add_parser("purge", help="Purge results")
    purge_sub = purge_p.add_subparsers(dest="purge_target")

    purge_run_p = purge_sub.add_parser(
        "run", help="Purge results folder for a single run")
    purge_run_p.add_argument("experiment", type=str)
    purge_run_p.add_argument("run_id", type=str)
    purge_run_p.add_argument(
        "-y", "--yes", action="store_true",
        help="Skip confirmation prompt")

    purge_exp_p = purge_sub.add_parser(
        "experiment",
        help="Purge all results and logs for an experiment")
    purge_exp_p.add_argument("experiment", type=str)
    purge_exp_p.add_argument(
        "-y", "--yes", action="store_true",
        help="Skip confirmation prompt")

    return parser.parse_args()


# ----------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------

def _list_all_experiments() -> None:
    import adgtk.tracking.runs as run_registry

    runs = run_registry.get_runs()

    # Group registry entries by experiment
    experiments: dict[str, list] = {}
    for r in runs:
        experiments.setdefault(r.experiment_name, []).append(r)

    # Include any experiments found on disk but not in the registry
    if os.path.exists(EXP_RESULTS_FOLDER):
        for d in sorted(os.listdir(EXP_RESULTS_FOLDER)):
            if os.path.isdir(os.path.join(EXP_RESULTS_FOLDER, d)):
                experiments.setdefault(d, [])

    if not experiments:
        print("No experiments found.")
        return

    name_w, runs_w, last_w = 25, 6, 22
    header = f"{'Experiment':<{name_w}} {'Runs':>{runs_w}}  "
    header += f"{'Last Run':<{last_w}}  Status"
    bar = "=" * len(header)
    print(f"\n{header}\n{bar}")

    for exp_name in sorted(experiments.keys()):
        exp_runs = experiments[exp_name]
        run_count = len(exp_runs)
        last_run = "--"
        status_parts = []

        if exp_runs:
            dated = sorted(
                exp_runs, key=lambda r: r.timestamp_start or "", reverse=True)
            last_run = dated[0].timestamp_start or "--"

            n_incomplete = sum(1 for r in exp_runs if r.status == "incomplete")
            n_missing = sum(
                1 for r in exp_runs
                if not os.path.exists(r.results_path))

            if n_missing:
                status_parts.append(f"{n_missing} missing")
            if n_incomplete:
                status_parts.append(f"{n_incomplete} incomplete")
            if not status_parts:
                status_parts.append("OK")
        else:
            status_parts.append("unregistered")

        status_str = ", ".join(status_parts)
        out_str = f"{exp_name:<{name_w}} {run_count:>{runs_w}}  "
        out_str += f"{last_run:<{last_w}}  {status_str}"
        print(out_str)
    print()


def _list_experiment_runs(experiment_name: str) -> None:
    import adgtk.tracking.runs as run_registry

    runs = run_registry.get_runs(experiment_name=experiment_name)

    if not runs:
        print(f"No registered runs found for: {experiment_name}")
        exp_path = os.path.join(EXP_RESULTS_FOLDER, experiment_name)
        if os.path.exists(exp_path):
            print(f"  Folder exists at {exp_path}")
            print("  Run `adgtk-results sync` to register existing runs.")
        return

    runs = sorted(runs, key=lambda r: r.timestamp_start or "", reverse=True)

    run_w, status_w, dur_w = 30, 16, 12
    header = f"{'Run':<{run_w}} {'Status':<{status_w}} {'Duration':>{dur_w}}  "
    header += "Started"
    bar = "=" * (len(header) + 4)
    print(f"\n{header}\n{bar}")

    for r in runs:
        folder_ok = os.path.exists(r.results_path)
        display_status = r.status if folder_ok else "results_missing"
        ts = r.timestamp_start or "--"
        dur = _fmt_duration(r.duration_seconds)
        out_str = f"{r.run_id:<{run_w}} {display_status:<{status_w}} "
        out_str += f"{dur:>{dur_w}}  {ts}"
        print(out_str)
    print()


def _show_run(experiment_name: str, run_id: str) -> None:
    import adgtk.tracking.runs as run_registry

    runs = run_registry.get_runs(experiment_name=experiment_name)
    entry = next((r for r in runs if r.run_id == run_id), None)

    if entry is None:
        run_path = os.path.join(EXP_RESULTS_FOLDER, experiment_name, run_id)
        if not os.path.exists(run_path):
            print(f"Run not found: {experiment_name} / {run_id}")
            sys.exit(1)
        results_path = run_path
        print("(Run not in registry — reading from disk)")
    else:
        results_path = entry.results_path
        print(f"\nRun:      {run_id}")
        print(f"Experiment: {experiment_name}")
        print(f"Status:   {entry.status}")
        print(f"Started:  {entry.timestamp_start or '--'}")
        print(f"Ended:    {entry.timestamp_end or '--'}")
        print(f"Duration: {_fmt_duration(entry.duration_seconds)}")

    results_file = os.path.join(results_path, CONCLUSIONS_DIR, RESULTS_FILE)
    config_file = os.path.join(results_path, RUN_CONFIG_FILE)

    if os.path.exists(results_file):
        print("\n--- results.yaml ---")
        with open(results_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(f"\n(results.yaml not found at {results_file})")

    if os.path.exists(config_file):
        print("--- run.exp.config.yaml ---")
        with open(config_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(f"(run.exp.config.yaml not found at {config_file})")


def _validate() -> None:
    import adgtk.tracking.runs as run_registry

    runs = run_registry.get_runs()
    run_set = {(r.experiment_name, r.run_id) for r in runs}

    orphaned = []
    missing_folder = []
    incomplete = []

    for r in runs:
        if not os.path.exists(r.results_path):
            missing_folder.append(r)
        elif r.status == "incomplete":
            incomplete.append(r)

    if os.path.exists(EXP_RESULTS_FOLDER):
        for exp_name in os.listdir(EXP_RESULTS_FOLDER):
            exp_path = os.path.join(EXP_RESULTS_FOLDER, exp_name)
            if not os.path.isdir(exp_path):
                continue
            for run_dir in os.listdir(exp_path):
                if run_dir == "common":
                    continue
                run_path = os.path.join(exp_path, run_dir)
                if not os.path.isdir(run_path):
                    continue
                if (exp_name, run_dir) not in run_set:
                    orphaned.append((exp_name, run_dir))

    print("\nValidation Report")
    print("=================")

    if orphaned:
        print(f"\nOrphaned folders on disk (not in registry): {len(orphaned)}")
        for exp_name, run_dir in sorted(orphaned):
            print(f"  {exp_name} / {run_dir}")
        print("  → Run `adgtk-results sync` to register these runs")

    if incomplete:
        out_str = "\nIncomplete runs (registered, no results.yaml): "
        out_str += f"{len(incomplete)}"
        print(out_str)
        for r in incomplete:
            print(f"  {r.experiment_name} / {r.run_id}")

    if missing_folder:
        print(
            f"\nRegistry entries with missing folders: {len(missing_folder)}")
        for r in missing_folder:
            print(
                f"  {r.experiment_name} / {r.run_id}  (was: {r.results_path})")
        out_str = "  → Run `adgtk-results purge run <exp> <run>` to "
        out_str += "clean the registry"
        print(out_str)

    if not orphaned and not incomplete and not missing_folder:
        print("\nAll clean — no issues found.")

    print()


def _sync() -> None:
    import adgtk.tracking.runs as run_registry
    from adgtk.tracking.structure import RunEntryModel

    runs = run_registry.get_runs()
    run_set = {(r.experiment_name, r.run_id) for r in runs}
    added = 0

    if not os.path.exists(EXP_RESULTS_FOLDER):
        print("No results folder found.")
        return

    for exp_name in sorted(os.listdir(EXP_RESULTS_FOLDER)):
        exp_path = os.path.join(EXP_RESULTS_FOLDER, exp_name)
        if not os.path.isdir(exp_path):
            continue
        for run_dir in sorted(os.listdir(exp_path)):
            if run_dir == "common":
                continue
            run_path = os.path.join(exp_path, run_dir)
            if not os.path.isdir(run_path):
                continue
            if (exp_name, run_dir) in run_set:
                continue

            results_file = os.path.join(
                run_path, CONCLUSIONS_DIR, RESULTS_FILE)
            status: Literal['complete', 'incomplete'] = (
                "complete" if os.path.exists(results_file) else "incomplete"
            )

            # Use folder mtime as the best available timestamp (cross-platform)
            mtime = os.path.getmtime(run_path)
            ts = datetime.datetime.fromtimestamp(mtime).strftime(
                "%Y-%m-%d %H:%M:%S")

            run_registry.add_run(RunEntryModel(
                run_id=run_dir,
                experiment_name=exp_name,
                timestamp_start=ts,
                timestamp_end=None,
                duration_seconds=None,
                status=status,
                results_path=run_path
            ))
            print(f"  Registered: {exp_name} / {run_dir}  [{status}]")
            added += 1

    if added == 0:
        print("Registry is up to date — no new runs found on disk.")
    else:
        print(f"\nRegistered {added} run(s).")


def _disk_usage(experiment_name: Optional[str] = None) -> None:
    if not os.path.exists(EXP_RESULTS_FOLDER):
        print("No results folder found.")
        return

    if experiment_name:
        exp_names = [experiment_name]
    else:
        exp_names = sorted(
            d for d in os.listdir(EXP_RESULTS_FOLDER)
            if os.path.isdir(os.path.join(EXP_RESULTS_FOLDER, d))
        )

    name_w = 30
    header = f"{'Experiment / Run':<{name_w}}  {'Size':>10}"
    bar = "=" * len(header)
    print(f"\n{header}\n{bar}")

    total_all = 0
    for exp in exp_names:
        exp_path = os.path.join(EXP_RESULTS_FOLDER, exp)
        if not os.path.isdir(exp_path):
            print(f"{exp:<{name_w}}  (not found)")
            continue
        exp_size = _folder_size(exp_path)
        total_all += exp_size
        print(f"{exp:<{name_w}}  {_fmt_size(exp_size):>10}")

        if experiment_name:
            for run_dir in sorted(os.listdir(exp_path)):
                if run_dir == "common":
                    continue
                run_path = os.path.join(exp_path, run_dir)
                if not os.path.isdir(run_path):
                    continue
                run_size = _folder_size(run_path)
                label = f"  {run_dir}"
                print(f"{label:<{name_w}}  {_fmt_size(run_size):>10}")

    if not experiment_name and len(exp_names) > 1:
        print("-" * len(bar))
        print(f"{'Total':<{name_w}}  {_fmt_size(total_all):>10}")

    print()


def _export(experiment_name: str, fmt: str, output: Optional[str]) -> None:
    import adgtk.tracking.runs as run_registry

    runs = run_registry.get_runs(experiment_name=experiment_name)

    if not runs:
        print(f"No registered runs found for: {experiment_name}")
        return

    records = []
    for r in sorted(runs, key=lambda x: x.timestamp_start or ""):
        record: dict = {
            "run_id": r.run_id,
            "experiment_name": r.experiment_name,
            "status": r.status,
            "timestamp_start": r.timestamp_start,
            "timestamp_end": r.timestamp_end,
            "duration_seconds": r.duration_seconds,
            "results_path": r.results_path,
        }
        results_file = os.path.join(
            r.results_path, CONCLUSIONS_DIR, RESULTS_FILE)
        if os.path.exists(results_file):
            with open(results_file, "r", encoding="utf-8") as f:
                try:
                    results_data = yaml.safe_load(f) or {}
                    if isinstance(results_data, dict):
                        record.update(results_data)
                except yaml.YAMLError:
                    pass
        records.append(record)

    if fmt == "json":
        content = json.dumps(records, indent=2, default=str)
    else:
        all_keys: list[str] = []
        seen_keys: set[str] = set()
        for record in records:
            for k in record.keys():
                if k not in seen_keys:
                    seen_keys.add(k)
                    all_keys.append(k)
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
        content = buf.getvalue()

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Exported {len(records)} run(s) to {output}")
    else:
        print(content)


def _prune(experiment_name: str, keep: int, skip_confirm: bool) -> None:
    import adgtk.tracking.runs as run_registry

    runs = run_registry.get_runs(experiment_name=experiment_name)
    if not runs:
        print(f"No registered runs found for: {experiment_name}")
        return

    runs = sorted(runs, key=lambda r: r.timestamp_start or "", reverse=True)
    to_keep = runs[:keep]
    to_purge = runs[keep:]

    if not to_purge:
        out_str = f"Only {len(runs)} run(s) registered — nothing to "
        out_str += f"prune (--keep {keep})."
        print(out_str)
        return

    out_str = f"Keeping {len(to_keep)} most recent run(s). "
    out_str += f"Will purge {len(to_purge)}:"
    print(out_str)
    for r in to_purge:
        if os.path.exists(r.results_path):
            folder_note = ""
        else:
            folder_note = " (folder already gone)"
        print(f"  {r.run_id}  [{r.timestamp_start or '--'}]{folder_note}")

    if not skip_confirm and not _confirm("Proceed with purge?"):
        print("Aborted.")
        return

    for r in to_purge:
        if os.path.exists(r.results_path):
            shutil.rmtree(r.results_path)
        run_registry.remove_run(r.run_id, r.experiment_name)
        print(f"  Purged: {r.run_id}")

    print(f"\nPurged {len(to_purge)} run(s).")


def _purge_run(experiment_name: str, run_id: str, skip_confirm: bool) -> None:
    import adgtk.tracking.runs as run_registry

    runs = run_registry.get_runs(experiment_name=experiment_name)
    entry = next((r for r in runs if r.run_id == run_id), None)

    results_path = (
        entry.results_path if entry
        else os.path.join(EXP_RESULTS_FOLDER, experiment_name, run_id)
    )
    folder_exists = os.path.exists(results_path)

    if entry is None and not folder_exists:
        out_str = f"Run not found in registry or on disk: {experiment_name} "
        out_str += f"/ {run_id}"
        print(out_str)
        sys.exit(1)

    print(f"Purge run: {experiment_name} / {run_id}")
    if folder_exists:
        size = _folder_size(results_path)
        print(f"  Results folder: {results_path}  ({_fmt_size(size)})")
    else:
        print("  Results folder: not found (registry entry only)")

    if not skip_confirm and not _confirm("Proceed?"):
        print("Aborted.")
        return

    if folder_exists:
        shutil.rmtree(results_path)
        print(f"  Deleted: {results_path}")

    if entry is not None:
        run_registry.remove_run(run_id, experiment_name)
        print("  Registry entry removed.")

    print("Done.")


def _purge_experiment(experiment_name: str, skip_confirm: bool) -> None:
    import adgtk.tracking.runs as run_registry

    exp_results_path = os.path.join(EXP_RESULTS_FOLDER, experiment_name)
    exp_log_path = os.path.join(LOG_DIR, "runs", experiment_name)

    results_exist = os.path.exists(exp_results_path)
    logs_exist = os.path.exists(exp_log_path)
    runs = run_registry.get_runs(experiment_name=experiment_name)

    if not results_exist and not logs_exist and not runs:
        print(f"Nothing found for experiment: {experiment_name}")
        sys.exit(1)

    print(f"Purge experiment: {experiment_name}")
    if results_exist:
        size = _folder_size(exp_results_path)
        print(f"  Results : {exp_results_path}  ({_fmt_size(size)})")
    if logs_exist:
        print(f"  Logs    : {exp_log_path}")
    if runs:
        print(f"  Registry: {len(runs)} run entry/entries")
    print("  WARNING : This cannot be undone.")

    if not skip_confirm and not _confirm("Proceed?"):
        print("Aborted.")
        return

    if results_exist:
        shutil.rmtree(exp_results_path)
        print(f"  Deleted results: {exp_results_path}")

    if logs_exist:
        shutil.rmtree(exp_log_path)
        print(f"  Deleted logs: {exp_log_path}")

    if runs:
        removed = run_registry.remove_experiment(experiment_name)
        print(f"  Removed {removed} registry entry/entries.")

    print("Done.")


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

def main() -> None:
    sys.path.insert(0, os.getcwd())
    require_project()

    args = _parse_args()

    if args.command is None or args.command == "list":
        exp = getattr(args, "experiment", None)
        if exp:
            _list_experiment_runs(exp)
        else:
            _list_all_experiments()

    elif args.command == "show":
        _show_run(args.experiment, args.run_id)

    elif args.command == "validate":
        _validate()

    elif args.command == "sync":
        _sync()

    elif args.command == "disk-usage":
        _disk_usage(getattr(args, "experiment", None))

    elif args.command == "export":
        _export(args.experiment, args.format, args.output)

    elif args.command == "prune":
        _prune(args.experiment, args.keep, args.yes)

    elif args.command == "purge":
        if args.purge_target == "run":
            _purge_run(args.experiment, args.run_id, args.yes)
        elif args.purge_target == "experiment":
            _purge_experiment(args.experiment, args.yes)
        else:
            print("Usage: adgtk-results purge {run,experiment} ...")
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
