"""Shared bootstrap utilities for ADGTK in-project CLI tools."""

import importlib.util
import os
import sys

from adgtk.cli.constants import BOOT_FILENAME
from adgtk.utils.defaults import EXP_RESULTS_FOLDER

PID_FILE = "adgtk-mgr.pid"


def load_bootstrap():
    """Loads the user-defined bootstrap module if present.

    Returns:
        The loaded module, or None if bootstrap.py is not found.

    Raises:
        ImportError: If the file is found but cannot be loaded.
    """
    bootstrap_path = os.path.join(os.getcwd(), BOOT_FILENAME)
    if not os.path.exists(bootstrap_path):
        return None

    spec = importlib.util.spec_from_file_location(
        "user_bootstrap", bootstrap_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load bootstrap module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_bootstrap() -> None:
    """Loads and executes foundation(), builtin(), and user_code() hooks."""
    try:
        bootstrap = load_bootstrap()
        if bootstrap is None:
            print("No bootstrap.py found.")
            sys.exit(1)
        for hook in ["foundation", "builtin", "user_code"]:
            func = getattr(bootstrap, hook, None)
            if callable(func):
                try:
                    func()
                except ModuleNotFoundError as e:
                    print(
                        f"Missing module in bootstrap hook '{hook}': {e.name}")
                    sys.exit(1)
                except Exception as e:
                    print(f"Error in bootstrap hook '{hook}': {e}")
                    sys.exit(1)
    except Exception as e:
        print(f"Unable to load bootstrap. Code raised: {e}")
        sys.exit(1)


def is_project(folder: str) -> bool:
    """Lightweight structural check — does not load user modules.

    Args:
        folder: Path to inspect.

    Returns:
        True if the folder looks like a valid ADGTK project.
    """
    if not os.path.isdir(folder):
        return False

    bootstrap_file = os.path.join(folder, BOOT_FILENAME)
    if not os.path.exists(bootstrap_file):
        return False

    with open(bootstrap_file, "r", encoding="utf-8") as f:
        raw = f.read()
        if "foundation()" not in raw:
            return False
        if "builtin()" not in raw:
            return False
        if "user_code()" not in raw:
            return False

    results_folder = os.path.join(folder, EXP_RESULTS_FOLDER)
    return os.path.isdir(results_folder)


def in_project() -> bool:
    """Returns True if cwd is a valid ADGTK project.

    Performs a lightweight check first (file/folder existence), then
    loads the bootstrap module to confirm required hooks are present.
    """
    if not os.path.exists(BOOT_FILENAME):
        return False
    if not os.path.exists(EXP_RESULTS_FOLDER):
        return False
    try:
        bootstrap = load_bootstrap()
        if bootstrap is None:
            return False
        for func_name in ["foundation", "builtin", "user_code"]:
            if not hasattr(bootstrap, func_name):
                print(
                    f"WARNING: Bootstrap missing function: {func_name}")
                return False
    except Exception as e:
        print(f"ERROR: Bootstrap inspection failed: {e}")
        raise
    return True


def require_project() -> None:
    """Exits with a clear error if not in a valid ADGTK project."""
    if not in_project():
        print("ERROR: This command must be run from within an ADGTK project.")
        print("  Run `adgtk-project list` to see available projects.")
        print("  Run `adgtk-project create <name>` to create a new one.")
        sys.exit(1)
