"""adgtk: Primary experiment management CLI.

Must be run from within an ADGTK project directory.
Heavy imports (runner, builder, factory) are deferred until after
the project check so that their module-level bootstrap.py guards
do not fire before we've confirmed the context.
"""

import argparse
import os
import signal
import sys
from adgtk import __version__ as adgtk_ver
from adgtk.cli.bootstrap import PID_FILE, require_project, run_bootstrap
from adgtk.utils import get_scenario_logger


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="adgtk",
        description="ADGTK experiment management")
    parser.add_argument(
        "--version", action="version", version=f"ADGTK {adgtk_ver}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    run_p = sub.add_parser("run", help="Run an experiment")
    run_p.add_argument(
        "name", nargs="?", type=str,
        help="Experiment name — prompts interactively if omitted")
    run_p.add_argument(
        "--n", dest="n", type=int, default=1, metavar="N",
        help="Number of times to run the experiment (default: 1)")

    build_p = sub.add_parser("build", help="Build a new experiment definition")
    build_p.add_argument(
        "name", nargs="?", type=str,
        help="Experiment name — prompts interactively if omitted")

    sub.add_parser("list", help="List available experiments")

    report_p = sub.add_parser(
        "report", help="Generate a rollup report for an experiment")
    report_p.add_argument(
        "name", nargs="?", type=str,
        help="Experiment name — prompts interactively if omitted")

    copy_p = sub.add_parser("copy", help="Copy a blueprint under a new name")
    copy_p.add_argument(
        "source", nargs="?", type=str,
        help="Source blueprint name — prompts interactively if omitted")
    copy_p.add_argument(
        "dest", nargs="?", type=str,
        help="New blueprint name — prompts interactively if omitted")

    sub.add_parser("stop", help="Stop the currently running experiment")

    tasks_p = sub.add_parser("tasks", help="Manage task records")
    tasks_sub = tasks_p.add_subparsers(dest="tasks_command")
    tasks_sub.add_parser("list", help="List recent task records")
    tasks_cleanup_p = tasks_sub.add_parser(
        "cleanup", help="Remove all finished task records from disk"
    )
    tasks_cleanup_p.add_argument(
        "--auto",
        action="store_true",
        help=(
            "Apply TTL/count cleanup from settings.yaml"
            " instead of removing all"
        ),
    )

    return parser.parse_args()


def _cleanup(signum, frame):
    try:
        get_scenario_logger().info("Signal received. Exiting early.")
    except RuntimeError:
        print("Signal received. Exiting.")
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    sys.exit()


def _report_experiment(name: str | None) -> None:
    import adgtk.tracking.runs as run_registry
    from adgtk.tracking.report import generate_experiment_report

    if name is None:
        names = run_registry.get_experiment_names()
        if not names:
            print("No experiments found.")
            return
        if len(names) == 1:
            name = names[0]
        else:
            for idx, n in enumerate(names):
                print(f"  {idx} : {n}")
            raw = input("Experiment name or index: ").strip()
            try:
                name = names[int(raw)]
            except (ValueError, IndexError):
                name = raw

    print(f"Generating report for: {name}")
    try:
        report_path, csv_path = generate_experiment_report(name)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return

    print(f"  Report : {report_path}")
    print(f"  CSV    : {csv_path}")


def _copy_blueprint(source: str | None, dest: str | None) -> None:
    import shutil
    from adgtk.utils.defaults import EXP_DEF_DIR
    import adgtk.tracking.project as project_manager

    blueprints = project_manager.get_available_experiments()
    names = [e.name for e in blueprints]

    if not names:
        print("No blueprints found.")
        return

    if source is None:
        for idx, n in enumerate(names):
            print(f"  {idx} : {n}")
        raw = input("Source blueprint name or index: ").strip()
        try:
            source = names[int(raw)]
        except (ValueError, IndexError):
            source = raw

    src_path = os.path.join(EXP_DEF_DIR, source + ".yaml")
    if not os.path.exists(src_path):
        print(f"Error: blueprint '{source}' not found.")
        return

    if dest is None:
        dest = input("New blueprint name: ").strip()

    if not dest:
        print("Error: new blueprint name cannot be empty.")
        return

    dest_path = os.path.join(EXP_DEF_DIR, dest + ".yaml")
    if os.path.exists(dest_path):
        print(f"Error: blueprint '{dest}' already exists.")
        return

    shutil.copy2(src_path, dest_path)
    print(f"Copied '{source}' -> '{dest}'")


def _list_experiments() -> None:
    import adgtk.tracking.project as project_manager
    from adgtk.tracking.structure import AvailableExperimentModel
    from pydantic import ValidationError

    exp_list = project_manager.get_available_experiments()
    name_str = "experiment name"
    desc_str = "description"
    title = f"{name_str:<27} | {desc_str}"
    bar_length = len(title)
    entries_str = ""
    for idx, entry in enumerate(exp_list):
        if (not isinstance(entry, AvailableExperimentModel)
                and isinstance(entry, dict)):
            try:
                entry = AvailableExperimentModel(**entry)
            except ValidationError:
                continue
        entry_str = f" {idx} : {entry.name:<22} | {entry.description}"
        if len(entry_str) > bar_length:
            bar_length = len(entry_str)
        entries_str += f"{entry_str}\n"
    bar = "=" * bar_length
    print(f"\n{title}\n{bar}\n{entries_str}")


def _tasks_list() -> None:
    from adgtk.experiment.task_record import get_all_task_records

    records = get_all_task_records(limit=50)
    if not records:
        print("No task records found.")
        return

    header = f"{'ID':<10} {'STATUS':<10} {'EXPERIMENT':<30} {'STARTED'}"
    print(f"\n{header}")
    print("=" * len(header))
    for r in records:
        started = r.started_at.strftime("%Y-%m-%d %H:%M")
        print(
            f"{r.task_id:<10} {r.status:<10}"
            f" {r.experiment_name:<30} {started}"
        )
    print()


def _tasks_cleanup(auto: bool) -> None:
    if auto:
        from adgtk.experiment.task_record import (
            cleanup_orphaned_tasks,
            purge_old_task_records,
        )
        from adgtk.utils.project_settings import load_project_settings
        cleanup_orphaned_tasks()
        ps = load_project_settings()
        removed = purge_old_task_records(
            max_age_days=ps.tasks.ttl_days,
            max_count=ps.tasks.max_count,
        )
        print(
            f"Cleanup complete: {removed} task director"
            f"{'y' if removed == 1 else 'ies'} removed."
        )
        print(
            f"  (TTL: {ps.tasks.ttl_days}d,"
            f" max: {ps.tasks.max_count} records)"
        )
    else:
        from adgtk.experiment.task_record import delete_finished_task_records
        ans = input(
            "Remove ALL finished task records? [y/N] "
        ).strip().lower()
        if ans != "y":
            print("Aborted.")
            return
        removed = delete_finished_task_records()
        print(
            f"Removed {removed} finished task director"
            f"{'y' if removed == 1 else 'ies'}."
        )


def _stop_experiment() -> None:
    from datetime import datetime, timezone
    from adgtk.experiment.task_record import (
        cleanup_orphaned_tasks,
        get_active_task_record,
        update_task_record,
    )

    cleanup_orphaned_tasks()
    record = get_active_task_record()
    if record is None:
        print("No experiment is currently running.")
        return

    print(
        f"Stopping: {record.experiment_name}"
        f"  (pid {record.pid}, source={record.source})"
    )
    try:
        os.kill(record.pid, signal.SIGTERM)
    except ProcessLookupError:
        print(f"  Process {record.pid} is no longer running.")
    except PermissionError:
        print(f"  Permission denied: cannot signal pid {record.pid}.")
        sys.exit(1)

    update_task_record(
        record.task_id,
        status="stopped",
        finished_at=datetime.now(timezone.utc),
    )
    print("  Status: stopped")


def main() -> None:
    sys.path.insert(0, os.getcwd())

    # Parse early so "stop" can bypass bootstrap and PID-file setup entirely.
    args = _parse_args()

    if args.command == "stop":
        from adgtk.cli.bootstrap import is_project
        if not is_project(os.getcwd()):
            print(
                "ERROR: This command must be run"
                " from within an ADGTK project."
            )
            sys.exit(1)
        _stop_experiment()
        sys.exit(0)

    if args.command == "tasks":
        from adgtk.cli.bootstrap import is_project
        if not is_project(os.getcwd()):
            print(
                "ERROR: This command must be run"
                " from within an ADGTK project."
            )
            sys.exit(1)
        sub = getattr(args, "tasks_command", None)
        if sub == "list" or sub is None:
            _tasks_list()
        elif sub == "cleanup":
            _tasks_cleanup(auto=getattr(args, "auto", False))
        sys.exit(0)

    require_project()

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    run_bootstrap()

    # Deferred imports — these modules check for bootstrap.py at import time
    import adgtk.experiment.builder as experiment_builder
    import adgtk.experiment.runner as experiment_runner

    try:
        if args.command is None or args.command == "list":
            _list_experiments()
        elif args.command == "report":
            _report_experiment(getattr(args, "name", None))
        elif args.command == "run":
            resolved_filename = args.name
            for i in range(args.n):
                if args.n > 1:
                    print(f"Run {i + 1} of {args.n}")
                _, folders = experiment_runner.run_scenario(
                    filename=resolved_filename,
                    append_timestamp=False,
                    use_count=True)
                if resolved_filename is None:
                    from adgtk.utils.defaults import EXP_DEF_DIR
                    resolved_filename = os.path.join(
                        EXP_DEF_DIR, folders.experiment_name + ".yaml")
        elif args.command == "build":
            experiment_builder.build_experiment(name=args.name)
        elif args.command == "copy":
            _copy_blueprint(
                source=getattr(args, "source", None),
                dest=getattr(args, "dest", None))
    except FileNotFoundError:
        print(f"blueprint {args.name} not found")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        sys.exit(1)
    except KeyboardInterrupt:
        try:
            get_scenario_logger().info("Keyboard interrupt. Ending early.")
        except RuntimeError:
            pass
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

    sys.exit(0)


if __name__ == "__main__":
    main()
