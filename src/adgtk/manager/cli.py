"""Handlers for the CLI tools for this project

# TODO: move logging into the individual files, ex. runner, builder, etc
  each module should have its own. ex. experiment running should use the
  unique name of the experiment, while the builder is a common one.

# TODO: set log-level via a flag. shared module w/running config

"""
from logging import Logger
import signal
from typing import Optional
import argparse
import sys
import os
from pydantic import ValidationError
import adgtk.factory.component as factory
from adgtk.tracking.structure import EXP_RESULTS_FOLDER
from adgtk.tracking.utils import build_project_folders
from adgtk.manager.constants import BOOT_PY, BOOT_FILENAME
from adgtk import __version__ as adgtk_ver
from adgtk.manager.intro import intro
import adgtk.experiment.builder as experiment_builder
import adgtk.experiment.runner as experiment_runner
import adgtk.tracking.project as project_manager
from adgtk.tracking.structure import AvailableExperimentModel
from adgtk.utils import create_logger, get_scenario_logger
# and for the local project bootstrap.py
import importlib.util

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
PID_FILE = "adgtk-mgr.pid"


# ----------------------------------------------------------------------
# extensibility (getting user code into the ecosystem) - bootstrap.py
# ----------------------------------------------------------------------


def load_bootstrap():
    """Loads the user-defined bootstrap module if present."""
    bootstrap_path = os.path.join(os.getcwd(), "bootstrap.py")
    if not os.path.exists(bootstrap_path):
        print("No bootstrap.py found.")
        return None

    spec = importlib.util.spec_from_file_location(
        "user_bootstrap", bootstrap_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load bootstrap module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# ----------------------------------------------------------------------
# Bootstrap hook executor
# ----------------------------------------------------------------------


def execute_bootstrap_hooks(module):
    """Calls foundation(), builtin(), and user_code() from bootstrap.py."""
    for hook in ["foundation", "builtin", "user_code"]:
        func = getattr(module, hook, None)
        if callable(func):
            try:
                func()
            except ModuleNotFoundError as e:
                print(f"Missing module in bootstrap hook '{hook}': {e.name}")
                sys.exit(1)
            except Exception as e:
                print(f"Error in bootstrap hook '{hook}': {e}")
                sys.exit(1)


# ----------------------------------------------------------------------
# Signal management
# ----------------------------------------------------------------------
def cleanup(signum, frame):
    try:
        scenario_logger = get_scenario_logger()
        scenario_logger.info("signal recieved. exiting early")
    except RuntimeError:
        print("Signal recieved. exiting process")
        pass
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    sys.exit()
# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
BUILDER_LOG = "adgtk.builder.log"
_logger: Optional[Logger] = None
# ----------------------------------------------------------------------
# Module variables
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Private
# ----------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    """Parses the command line arguments

    Returns:
        argparse.Namespace: The command line input
    """
    parser = argparse.ArgumentParser()

    # modifiers
    parser.add_argument(
        '--version', action='version', version=f"ADGTK {adgtk_ver}")

    # now positional
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")

    # Project
    project_parser = subparsers.add_parser("project", help="Project actions")
    project_parser.add_argument(
        "action",
        choices=["create", "list"],
        help="Available project actions")
    project_parser.add_argument(
        "folder",
        type=str,
        nargs="?",
        help="The project folder name")

    # Experiment
    exp_parser = subparsers.add_parser(
        "experiment", help="Experiment actions")
    exp_parser.add_argument(
        "action",
        choices=["build", "list", "run"],
        help="Available experiment actions")
    exp_parser.add_argument(
        "--name",
        help="The name of the experiment",
        type=str)

    # Factory
    factory_parser = subparsers.add_parser(
        "factory", help="Factory actions")
    factory_parser.add_argument(
        "group",
        type=str,
        nargs="?",
        help="The group name")

    factory_parser.add_argument(
        "--tags",
        type=str,
        nargs='+',
        help="The tags to filter one"
    )

    # Batch
    batch_parser = subparsers.add_parser(
        "batch", help="Batch actions")
    batch_parser.add_argument(
        "action",
        choices=["run", "preview", "list", "create"],
        help="Available batch actions")
    batch_parser.add_argument(
        "name",
        type=str,
        nargs="?",
        help="The batch name")

    args = parser.parse_args()
    return args


# ---------------------------------------------------------------------
# Project creation
# ---------------------------------------------------------------------
def _create_boot_py(base_path: str = ""):
    """Creates the bootstrap.py file when creating a new project.

    :param base_path: The path to include, defaults to ""
    :type base_path: str, optional
    """
    file_w_path = os.path.join(base_path, BOOT_FILENAME)
    with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
        outfile.write(BOOT_PY)


def _create_project(name: str) -> None:
    """Creates a project

    :param name: The project/directory name to create
    :type name: str
    """
    print(f"Creating project: {name}")

    if os.path.exists(name):
        msg = f"Unable to create a project {name}. remove the other first!"
        print(msg)
    elif name is None:
        print("Please specify a name of your project")
    else:
        print(f"Attempting to create {name}")

        os.makedirs(name, exist_ok=True)
        os.chdir(name)
        build_project_folders(base_path=os.getcwd())
        _create_boot_py(base_path=os.getcwd())
        # and let the user know it worked
        print(f"Successfully created project {name}")
        print(f"`cd {name}` to work with the project")
        return None

    print(f"Error creating {name}")


def _list_projects() -> None:
    """Experience in which a list of available projects are sent to the
    screen.
    """
    project_folders = []
    folders = os.listdir("./")
    for folder_or_file in folders:
        if os.path.isdir(folder_or_file):
            if is_project(folder_or_file):
                project_folders.append(folder_or_file)

    print("Available projects")
    print("==================")
    for project in project_folders:
        print(f"- {project}")


def _run_bootstrap():
    """Loads the bootstrap file
    """
    # invoke the expected functions
    try:
        bootstrap = load_bootstrap()
        if bootstrap and hasattr(bootstrap, 'foundation'):
            bootstrap.foundation()
        if bootstrap and hasattr(bootstrap, 'builtin'):
            bootstrap.builtin()
        if bootstrap and hasattr(bootstrap, 'user_code'):
            bootstrap.user_code()

    except Exception as e:
        print(f"Unable to load boostrap. Code raised: {e}")
        sys.exit(1)


def _in_project() -> bool:
    if not os.path.exists("bootstrap.py"):
        return False
    if not os.path.exists(EXP_RESULTS_FOLDER):
        return False
    try:
        bootstrap = load_bootstrap()
        expected_funcs = ['foundation', 'builtin', 'user_code']
        for func in expected_funcs:
            if not hasattr(bootstrap, func):
                print(f"WARNING: Bootstrap missing expected function: {func}")
                return False
    except Exception as e:
        print(f"ERROR: Bootstrap inspection failed: {e}")
        #return True  # fallback: we assume it's okay for now
        # TODO: consider setting argument to return True vs dump.
        raise e

    return True


def is_project(folder: str) -> bool:
    """Does a lightweight inspection of a folder to determine if it
    appears to be a project. Note that a deeper inspection is performed
    by _in_project in that function inspects the bootstrap file by
    loading from within a project. However, function does not rely on
    needing to load user modules, etc so it is primarly used outside of
    a project such as getting a listing of projects.

    :param folder: The folder to inspect
    :type folder: str
    :return: True if it appears to be a project.
    :rtype: bool
    """
    if not os.path.isdir(folder):
        return False

    bootstrap_file_w_path = os.path.join(folder, "bootstrap.py")

    if not os.path.exists(bootstrap_file_w_path):
        return False

    with open(bootstrap_file_w_path, "r", encoding="utf-8") as infile:
        raw_text = infile.read()
        # it will always have a few things
        if not "foundation()" in raw_text:
            return False
        if not "builtin()" in raw_text:
            return False
        if not "user_code()" in raw_text:
            return False

    # now check for the results folder
    results_folder = os.path.join(folder, EXP_RESULTS_FOLDER)
    if not os.path.exists(results_folder):
        return False
    if not os.path.isdir(results_folder):
        return False

    return True


def _list_experiments():
    """Lists the experiments to the console.

    :raises ValueError: failed to properly parse an experiment
    """
    exp_list = project_manager.get_available_experiments()
    name_str = "experiment name"
    desc_str = "description"

    title = f"{name_str:<27} | {desc_str}"
    bar_length = len(title)
    entries_str = ""
    for idx, entry in enumerate(exp_list):
        if not isinstance(entry, AvailableExperimentModel) and \
                isinstance(entry, dict):
            try:
                entry = AvailableExperimentModel(**entry)
            except ValidationError:
                msg = ("Unexpected type from project_manager for exp "
                       f"listing. Observed: {type(entry)}")
                if _logger is not None:
                    _logger.error(msg)
                raise ValueError(msg)

        entry_str = f" {idx} : {entry.name:<22} | {entry.description}"
        if len(entry_str) > bar_length:
            bar_length = len(entry_str)
        entries_str += f"{entry_str}\n"

    bar = "="*bar_length
    output_str = f"\n{title}\n{bar}\n{entries_str}"
    print(output_str)

# --------------------------------------------------------------------
# --------------------------------------------------------------------
#          !!! MANAGER !!! THIS IS THE MAIN FUNCTION
# --------------------------------------------------------------------
# --------------------------------------------------------------------


def manager() -> None:
    """provides a CLI management"""
    global _logger

    # -------- setup ------------
    args = _parse_args()
    exp_name: Optional[str] = None
    scenario_logger: Optional[Logger] = None
    
    # Ensures current directory is part of the path
    sys.path.insert(0, os.getcwd())

    # register signal handlers
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    
    # now see if in-project
    inside_a_project = _in_project()
    try:
        # logging? only if its in a project
        if inside_a_project:
            # Save pid
            pid = os.getpid()
            with open(file=PID_FILE, mode="w", encoding="utf-8") as pidfile:
                pidfile.write(str(pid))
                pidfile.close()
            # Set up module-specific logger
            _logger = create_logger(
                "adgtk.cli.log",
                logger_name=__name__,
                subdir="framework"
            )
            # load bootstrap file
            _run_bootstrap()
        else:
            print("Not in bootstrap?")

        if args.command is None:
            print(intro)
            sys.exit(0)

        # ----- Project command ------
        if args.command == 'project':
            if args.action == "list":
                _list_projects()
                sys.exit(0)
            if args.action == "create":
                if inside_a_project:
                    msg = (
                        "WARNING: It appears you are in a project. "
                        "Cancelling request to create a project.")
                    print(msg)
                    if _logger is not None:
                        _logger.error(msg)
                    sys.exit(1)
                if args.folder is None:
                    print("Name of the project is required")
                    sys.exit()
                print(args)
                _create_project(name=args.folder)

            sys.exit(0)

        # ----- batch command ------
        elif args.command == 'batch':
            if args.name is None:
                print("Missing batch name. Name is required for batch jobs")
            experiment_runner.run_batch(filename=args.name)
            sys.exit(0)

        # ----- experiment command ------
        elif args.command == 'experiment':
            if args.action == "build":
                exp_name = None
                if args.name is not None:
                    exp_name = args.name

                experiment_builder.build_experiment(name=args.name)
                sys.exit()
            elif args.action == "list":
                _list_experiments()
                sys.exit(0)
            elif args.action == "run":
                # get the name of the experiment
                if args.name is not None:
                    exp_name = args.name

                experiment_runner.run_scenario(
                    filename=exp_name,
                    append_timestamp=False,
                    use_count=True)                
                sys.exit()

            else:
                print("unknown action")
                sys.exit()

        elif args.command == "factory":
            factory.report(group=args.group, tags=args.tags)
            sys.exit()
    except KeyboardInterrupt:
        try:        
            scenario_logger = get_scenario_logger()
            scenario_logger.info("Keyboard interupt. ending early")
        except RuntimeError:
            # if logger does not exist, it raises RuntimeError
            pass
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

if __name__ == '__main__':
    manager()
