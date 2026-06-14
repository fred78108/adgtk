"""adgtk-study: Study management CLI.

Manages study blueprints (stored in ``studies/``) and generates
cross-experiment rollup reports (written to ``study-results/``).

Must be run from within an ADGTK project directory.
"""

from __future__ import annotations

import argparse
import os
import sys

from adgtk.cli.bootstrap import require_project, run_bootstrap


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="adgtk-study",
        description="ADGTK study management — cross-experiment rollup")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    build_p = sub.add_parser("build", help="Build a new study blueprint")
    build_p.add_argument(
        "name", nargs="?", type=str,
        help="Study name — prompts interactively if omitted")

    run_p = sub.add_parser(
        "run", help="Generate a study report from a blueprint")
    run_p.add_argument(
        "name", nargs="?", type=str,
        help="Study name — prompts interactively if omitted")

    sub.add_parser("list", help="List available study blueprints")

    return parser.parse_args()


def _list_studies() -> None:
    from adgtk.experiment.study.builder import list_study_blueprints
    names = list_study_blueprints()
    if not names:
        print("No study blueprints found in studies/")
        return
    print()
    print(f"{'name':<30} | path")
    print("=" * 55)
    for name in names:
        print(f"  {name:<28} | studies/{name}.yaml")
    print()


def _build_study(name: str | None) -> None:
    from adgtk.experiment.study.builder import build_study
    build_study(name=name)


def _run_study(name: str | None) -> None:
    from adgtk.experiment.study.builder import list_study_blueprints
    from adgtk.experiment.study.report import generate_study_report

    if name is None:
        names = list_study_blueprints()
        if not names:
            print("No study blueprints found in studies/")
            return
        if len(names) == 1:
            name = names[0]
        else:
            for idx, n in enumerate(names):
                print(f"  {idx} : {n}")
            raw = input("Study name or index: ").strip()
            try:
                name = names[int(raw)]
            except (ValueError, IndexError):
                name = raw

    print(f"Generating study report for: {name}")
    try:
        report_path, csv_path = generate_study_report(name)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return

    print(f"  Report : {report_path}")
    print(f"  CSV    : {csv_path}")


def main() -> None:
    sys.path.insert(0, os.getcwd())
    require_project()
    run_bootstrap()

    args = _parse_args()

    if args.command is None or args.command == "list":
        _list_studies()
    elif args.command == "build":
        _build_study(getattr(args, "name", None))
    elif args.command == "run":
        _run_study(getattr(args, "name", None))

    sys.exit(0)


if __name__ == "__main__":
    main()
