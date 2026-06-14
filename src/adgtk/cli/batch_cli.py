"""adgtk-batch: Batch job management CLI.

Must be run from within an ADGTK project directory.
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
        prog="adgtk-batch",
        description="ADGTK batch job management")
    parser.add_argument(
        "--version", action="version", version=f"ADGTK {adgtk_ver}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    run_p = sub.add_parser("run", help="Run a batch job")
    run_p.add_argument("name", type=str, help="Batch job name")

    preview_p = sub.add_parser("preview", help="Preview a batch job")
    preview_p.add_argument("name", type=str, help="Batch job name")

    sub.add_parser("list", help="List available batch jobs")

    create_p = sub.add_parser("create", help="Create a batch job definition")
    create_p.add_argument("name", type=str, help="Batch job name")

    return parser.parse_args()


def _cleanup(signum, frame):
    try:
        get_scenario_logger().info("Signal received. Exiting early.")
    except RuntimeError:
        print("Signal received. Exiting.")
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    sys.exit()


def _list_batches() -> None:
    from adgtk.utils.defaults import BATCH_DEF_DIR
    if not os.path.isdir(BATCH_DEF_DIR):
        print("Batch directory not found.")
        return
    batches = sorted(
        f.replace(".yaml", "")
        for f in os.listdir(BATCH_DEF_DIR)
        if f.endswith(".yaml")
    )
    print("Available batch jobs")
    print("====================")
    if batches:
        for b in batches:
            print(f"  - {b}")
    else:
        print("  (none found)")


def main() -> None:
    sys.path.insert(0, os.getcwd())
    require_project()

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    with open(PID_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    # _logger: Optional[Logger] = create_logger(
    #     "adgtk.batch.log", logger_name=__name__, subdir="framework")

    run_bootstrap()

    # Deferred import — runner checks for bootstrap.py at import time
    import adgtk.experiment.runner as experiment_runner

    args = _parse_args()

    try:
        if args.command is None or args.command == "list":
            _list_batches()
        elif args.command == "run":
            experiment_runner.run_batch(filename=args.name)
        elif args.command == "preview":
            print(f"Preview not yet implemented for: {args.name}")
        elif args.command == "create":
            out_str = "Interactive batch creation not yet implemented "
            out_str += f"for: {args.name}"
            print(out_str)
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
