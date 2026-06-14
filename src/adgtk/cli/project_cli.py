"""adgtk-project: Lightweight project scaffold and discovery CLI.

Safe to run from anywhere — does not require an ADGTK project context
and does not import any modules that create loggers at import time.
"""

import argparse
import os
import shutil
import sys
from importlib.metadata import version as _pkg_version
from importlib.resources import files
from adgtk.cli.bootstrap import in_project, is_project
from adgtk.cli.constants import BOOT_FILENAME, BOOT_PY
from adgtk.utils.defaults import (
    BATCH_DEF_DIR,
    EXP_DEF_DIR, LOG_DIR,
    SHARED_MODEL_DIR
)
from adgtk.utils.defaults import EXP_RESULTS_FOLDER

adgtk_ver = _pkg_version("adgtk")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="adgtk-project",
        description="ADGTK project management")
    parser.add_argument(
        "--version", action="version", version=f"ADGTK {adgtk_ver}")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    create_p = sub.add_parser("create", help="Create a new project")
    create_p.add_argument("name", type=str, help="Project folder name")

    sub.add_parser("list", help="List ADGTK projects in current directory")
    sub.add_parser("info", help="Show status of the current project")

    skills_p = sub.add_parser(
        "install-skills",
        help="Install the ADGTK Claude Code skill into your IDE skills folder")
    skills_p.add_argument(
        "--output-dir",
        default=".claude/skills",
        metavar="PATH",
        help="Destination folder for the skill file (default: .claude/skills)")

    return parser.parse_args()


def _build_project_folders(base_path: str) -> None:
    """Creates required project directories without importing tracking.utils
    (which creates a logger at module level and would pollute the
    caller's cwd).
    """
    for subdir in [BATCH_DEF_DIR, EXP_DEF_DIR, SHARED_MODEL_DIR,
                   LOG_DIR, EXP_RESULTS_FOLDER]:
        full = os.path.join(base_path, subdir)
        os.makedirs(full, exist_ok=True)


def _create_project(name: str) -> None:
    if in_project():
        print(
            "WARNING: You appear to be inside a project already. Cancelling.")
        sys.exit(1)
    if os.path.exists(name):
        print(f"ERROR: '{name}' already exists. Remove it first.")
        sys.exit(1)

    print(f"Creating project: {name}")
    os.makedirs(name, exist_ok=True)
    project_path = os.path.abspath(name)
    _build_project_folders(project_path)

    boot_path = os.path.join(project_path, BOOT_FILENAME)
    with open(boot_path, "w", encoding="utf-8") as f:
        f.write(BOOT_PY)

    print(f"Successfully created: {name}")
    print(f"  cd {name}")
    print("  adgtk list       # list experiments")
    print("  adgtk build      # build a new experiment")


def _list_projects() -> None:
    projects = sorted(
        f for f in os.listdir(".")
        if os.path.isdir(f) and is_project(f)
    )
    print("Available ADGTK projects")
    print("========================")
    if projects:
        for p in projects:
            print(f"  - {p}")
    else:
        print("  (none found in current directory)")


def _install_skills(output_dir: str) -> None:
    skill_src = files("adgtk.skills").joinpath("adgtk.md")
    os.makedirs(output_dir, exist_ok=True)
    dest = os.path.join(output_dir, "adgtk.md")
    shutil.copy2(str(skill_src), dest)
    print(f"Installed ADGTK skill -> {dest}")


def _project_info() -> None:
    cwd = os.getcwd()
    boot_exists = os.path.exists(BOOT_FILENAME)
    results_exists = os.path.isdir(EXP_RESULTS_FOLDER)
    inside = boot_exists and results_exists

    print("ADGTK Project Info")
    print("==================")
    print(f"  Location  : {cwd}")
    print(f"  bootstrap : {'found' if boot_exists else 'MISSING'}")
    print(f"  results/  : {'found' if results_exists else 'MISSING'}")
    print(f"  Status    : {'valid project' if inside else 'not a project'}")


def main() -> None:
    sys.path.insert(0, os.getcwd())
    args = _parse_args()

    if args.command is None:
        _project_info()
    elif args.command == "create":
        _create_project(args.name)
    elif args.command == "list":
        _list_projects()
    elif args.command == "info":
        _project_info()
    elif args.command == "install-skills":
        _install_skills(args.output_dir)

    sys.exit(0)


if __name__ == "__main__":
    main()
