"""adgtk-factory: Component factory inspection CLI.

Must be run from within an ADGTK project directory.
"""

import argparse
import os
import sys

from adgtk import __version__ as adgtk_ver
from adgtk.cli.bootstrap import require_project, run_bootstrap


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="adgtk-factory",
        description="ADGTK factory component inspection")
    parser.add_argument(
        "--version", action="version", version=f"ADGTK {adgtk_ver}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    list_p = sub.add_parser("list", help="List registered components")
    list_p.add_argument(
        "group", nargs="?", type=str, help="Filter by group name")
    list_p.add_argument(
        "--tags", nargs="+", type=str, help="Filter by tags")

    return parser.parse_args()


def main() -> None:
    sys.path.insert(0, os.getcwd())
    require_project()
    run_bootstrap()

    # Deferred import — factory checks for bootstrap.py at import time
    import adgtk.factory.component as factory

    args = _parse_args()

    group = getattr(args, "group", None)
    tags = getattr(args, "tags", None)
    factory.report(group=group, tags=tags)

    sys.exit(0)


if __name__ == "__main__":
    main()
