"""Provides an ADGTK managed dataset inventory CLI.

This module provides the command-line interface for managing datasets within
an ADGTK project, allowing for registration, retirement, and reporting.

Roadmap:
    1. loading of datasets from HuggingFace ds, other wrappers.
"""

import argparse
import os
import sys

from adgtk.cli.bootstrap import require_project
require_project()

from typing import Literal, Optional, cast
from adgtk.data.structure import (
    SUPPORTED_FILE_ENCODING_TYPES,
    FileEncodingTypes
)
from adgtk.data.dataset import DatasetManager
from adgtk.utils import get_user_input
from adgtk.utils import create_logger


_logger = create_logger(
    logfile="dataset.manager.log",
    subdir="common",
    logger_name=__name__
)

_USE_CHOICES = ["test", "train", "validate", "other"]
_BANNER_WIDTH = 70

# ----------------------------------------------------------------------
# Presentation helpers
# ----------------------------------------------------------------------


def _banner(title: str) -> None:
    line = "=" * _BANNER_WIDTH
    padded = title.center(_BANNER_WIDTH)
    print(f"\n{line}\n{padded}\n{line}")


def _section(title: str) -> None:
    print(f"\n  {title}")
    print("  " + "-" * (len(title) + 2))


def _ok(msg: str) -> None:
    print(f"  [OK]  {msg}")


def _err(msg: str) -> None:
    print(f"  [!!]  {msg}")


def _info(msg: str) -> None:
    print(f"        {msg}")


# ----------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    desc_str = "ADGTK Dataset Manager — register, inspect, and retire datasets"
    parser = argparse.ArgumentParser(
        prog="adgtk-ds",
        description=desc_str,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  adgtk-ds report\n"
            "  adgtk-ds register                              (interactive)\n"
            "  adgtk-ds register --file data/f.csv --encoding csv --use test\n"
            "  adgtk-ds retire                                (interactive)\n"
            "  adgtk-ds retire --id <uuid>\n"
            "  adgtk-ds find --filename train.csv\n"
        )
    )

    sub = parser.add_subparsers(dest="command", metavar="command")

    # ---- report ----
    report_p = sub.add_parser("report", help="Print inventory report")
    report_p.add_argument(
        "tags", nargs="*",
        help="Optional tag(s) to filter results"
    )

    # ---- register ----
    reg_p = sub.add_parser(
        "register",
        help="Register a new dataset file",
        description="Register a dataset file into the inventory. "
                    "Any omitted options are collected interactively."
    )
    reg_p.add_argument(
        "-f", "--file", type=str, dest="file",
        help="Path to the dataset file"
    )
    reg_p.add_argument(
        "-e", "--encoding", type=str,
        choices=SUPPORTED_FILE_ENCODING_TYPES,
        help=f"File encoding ({', '.join(SUPPORTED_FILE_ENCODING_TYPES)})"
    )
    reg_p.add_argument(
        "-u", "--use", type=str,
        choices=_USE_CHOICES, default=None,
        help=f"Intended use ({', '.join(_USE_CHOICES)}) — default: other"
    )
    reg_p.add_argument(
        "-d", "--description", type=str, default=None,
        help="Short description of the dataset"
    )
    reg_p.add_argument(
        "--id", type=str,
        help="Custom ID to assign (auto-generated if omitted)"
    )

    # ---- retire ----
    ret_p = sub.add_parser(
        "retire", help="Remove a dataset entry from the inventory")
    ret_p.add_argument(
        "--id", type=str, default=None,
        help="ID of the entry to retire (prompted if omitted)"
    )

    # ---- find ----
    find_p = sub.add_parser("find", help="Look up the ID for a filename")
    find_p.add_argument(
        "--filename", type=str, required=True,
        help="Filename to search for"
    )

    return parser.parse_args()


# ----------------------------------------------------------------------
# Command implementations
# ----------------------------------------------------------------------


def cmd_register(
    ds_mgr: DatasetManager,
    source_file: Optional[str],
    encoding: Optional[str],
    use: Optional[str],
    description: Optional[str],
    custom_id: Optional[str],
) -> None:
    _banner("Register Dataset")

    # --- file path ---
    if source_file is None:
        _section("File Path")
        source_file = str(get_user_input(
            user_prompt="Path to the dataset file",
            requested="str",
            helper="Absolute or relative path to the file to register",
            allow_whitespace=False,
            min_characters=1,
        ))

    source_file = os.path.normpath(source_file)
    if not os.path.exists(source_file):
        _err(f"File not found: {source_file}")
        sys.exit(1)

    _, filename = os.path.split(os.path.abspath(source_file))

    # --- encoding ---
    if encoding is None:
        _section("File Encoding")
        _info(f"Choices: {', '.join(SUPPORTED_FILE_ENCODING_TYPES)}")
        encoding_str = str(get_user_input(
            user_prompt="Encoding",
            requested="str",
            choices=SUPPORTED_FILE_ENCODING_TYPES,
            helper="The file format / encoding type",
        ))
    else:
        encoding_str = encoding

    if encoding_str not in SUPPORTED_FILE_ENCODING_TYPES:
        _err(f"Unrecognised encoding: {encoding_str}")
        sys.exit(1)
    enc = cast(FileEncodingTypes, encoding_str)

    # --- use / purpose ---
    if use is None:
        _section("Intended Use")
        _info(f"Choices: {', '.join(_USE_CHOICES)}")
        help_str = "How this dataset will be used (train / test / "
        help_str += "validate / other)"
        use = str(get_user_input(
            user_prompt="Intended use",
            requested="str",
            choices=_USE_CHOICES,
            helper=help_str,
            default_selection="other",
        ))
    use_typed = cast(Literal["test", "train", "validate", "other"], use)

    # --- confirm ---
    _section("Summary")
    _info(f"File        : {source_file}")
    _info(f"Encoding    : {enc}")
    _info(f"Use         : {use_typed}")
    _info(f"Description : {description or '(none)'}")
    _info(f"Custom ID   : {custom_id or '(auto)'}")
    print()
    confirm = str(get_user_input(
        user_prompt="Register this entry?",
        requested="str",
        choices=["yes", "no"],
        default_selection="yes",
        helper="Enter 'yes' to confirm or 'no' to cancel",
    ))
    if confirm.lower() != "yes":
        _info("Registration cancelled.")
        sys.exit(0)

    try:
        kwargs: dict = dict(
            source_file=source_file,
            encoding=enc,
            use=use_typed,
            description=description or None,
        )
        if custom_id and len(custom_id) > 1:
            kwargs["file_id"] = custom_id

        assigned_id = ds_mgr.register(**kwargs)
    except FileNotFoundError as exc:
        _err(str(exc))
        sys.exit(1)
    except IndexError as exc:
        _err(str(exc))
        sys.exit(1)

    print()
    _ok(f"Registered  : {filename}")
    _ok(f"Assigned ID : {assigned_id}")
    _logger.info("Registered %s as %s", source_file, assigned_id)


def cmd_retire(ds_mgr: DatasetManager, entry_id: Optional[str]) -> None:
    _banner("Retire Dataset Entry")

    if entry_id is None:
        # Show inventory so the user knows what IDs exist
        _section("Current Inventory")
        ds_mgr.report()

        ids = ds_mgr.get_file_ids_only()
        if not ids:
            _info("No entries to retire.")
            sys.exit(0)

        _section("Select Entry")
        entry_id = str(get_user_input(
            user_prompt="Enter the ID to retire",
            requested="str",
            choices=ids,
            helper="Copy the File ID from the report above",
            allow_whitespace=False,
            min_characters=1,
        ))

    try:
        ds_mgr.retire_file(entry_id)
    except IndexError as exc:
        _err(str(exc))
        _logger.error(exc)
        sys.exit(1)

    print()
    _ok(f"Retired: {entry_id}")
    _logger.info("Retired entry: %s", entry_id)


def cmd_find(ds_mgr: DatasetManager, filename: str) -> None:
    try:
        entry_id = ds_mgr.get_file_id(filename=filename)
        print(f"\n  {filename}  →  {entry_id}\n")
    except FileNotFoundError:
        _err(f"No entry found for filename: {filename}")
        sys.exit(1)


def cmd_report(ds_mgr: DatasetManager, tags: list[str]) -> None:
    _banner("Dataset Inventory")
    ds_mgr.report(tag=tags if tags else None)


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    os.makedirs(name=".tracking", exist_ok=True)
    ds_mgr = DatasetManager(folder=".tracking")

    if args.command == "report":
        cmd_report(ds_mgr, args.tags)

    elif args.command == "register":
        cmd_register(
            ds_mgr=ds_mgr,
            source_file=args.file,
            encoding=args.encoding,
            use=args.use,
            description=args.description,
            custom_id=args.id,
        )

    elif args.command == "retire":
        cmd_retire(ds_mgr=ds_mgr, entry_id=args.id)

    elif args.command == "find":
        cmd_find(ds_mgr=ds_mgr, filename=args.filename)

    else:
        # No command — print a clean usage summary
        _banner("ADGTK Dataset Manager")
        print(
            "\n"
            "  Manage the dataset inventory for your ADGTK project.\n"
            "\n"
            "  Commands\n"
            "  --------\n"
            "  register   Register a file (interactive when args omitted)\n"
            "  retire     Remove a dataset entry from the inventory\n"
            "  report     Print the inventory (optionally filter by tag)\n"
            "  find       Look up the ID assigned to a filename\n"
            "\n"
            "  Run  adgtk-ds <command> --help  for per-command options.\n"
        )
