"""Handlers for the CLI tools for this project
"""

# import http.server
import logging
from typing import Literal, Union
import argparse
import sys
import os
import shutil
# import http
import signal
import tarfile
import importlib.resources
import toml
import yaml
from jinja2 import Environment, FileSystemLoader
from adgtk.common import DEFAULT_SETTINGS
from adgtk.scenario import ScenarioManager
from adgtk.experiment import ExperimentBuilder
from adgtk.utils import (
    start_logging,
    clear_screen,
    create_line,
    load_settings,
    prepare_string,
    TerminalCSS)
from adgtk import __version__ as adgtk_ver

# ----------------------------------------------------------------------
# Module configuration
# ----------------------------------------------------------------------
WIZARD_OPTIONS = ("agent", "environment", "policy", "scenario", "custom")


# ----------------------------------------------------------------------
# Signal handlers
# ----------------------------------------------------------------------


def signal_handler(signum, frame):
    """Handles the signal from the OS

    :param signum: The signal number
    :type signum: int
    :param frame: the frame object
    :type frame: stack frame
    """
    # https://docs.python.org/3/library/signal.html
    if signal.SIGINT == signum:
        print('\nRecievd Ctrl+C! Canceling action.')
    sys.exit(0)


# ----------------------------------------------------------------------
# Management
# ----------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parses the command line arguments

    Returns:
        argparse.Namespace: The command line input
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--create", help="The project to create")
    # parser.add_argument("-p", "--plugin", help="Initiate the plugin wizard")
    parser.add_argument("-d", "--destroy", help="The project to destroy")
    parser.add_argument("-p", "--preview", help="The experiment to preview")
    parser.add_argument("-r", "--run", help="The experiment to run")
    parser.add_argument(
        "-l",
        "--list",
        help="Available experiments to run",
        action="store_true")
    parser.add_argument(
        "-S",
        "--Server",
        help="Start results server",
        action="store_true")
    parser.add_argument(
        "-s",
        "--status",
        help="Process status",
        action="store_true")
    parser.add_argument(
        "--no-color", help="Disable color prompts", action="store_true")
    parser.add_argument(
        "-f",
        "--factory",
        help="Display scenario manager's factory report",
        action="store_true")
    parser.add_argument(
        "-F",
        "--Factory",
        help="Display scenario manager's factory report for a single group")
    parser.add_argument(
        "-b", "--builder",
        help="Interactive mode to build an experiment using blueprints",
        action="store_true")
    parser.add_argument(
        '--version', action='version', version=f"ADGTK {adgtk_ver}")
    parser.add_argument(
        "--yaml",
        help="Use YAML format when creating the project settings.file.",
        action="store_true")

    args = parser.parse_args()
    return args


def build_folders_from_settings():
    """Builds out the folders based on settings"""
    settings = load_settings()
    if not os.path.exists(settings.experiment["data_dir"]):
        os.makedirs(name=settings.experiment["data_dir"], exist_ok=True)
    if not os.path.exists(settings.experiment["results_dir"]):
        os.makedirs(name=settings.experiment["results_dir"], exist_ok=True)
    if not os.path.exists(settings.experiment["tensorboard_dir"]):
        os.makedirs(name=settings.experiment["tensorboard_dir"], exist_ok=True)
    if not os.path.exists(settings.experiment["definition_dir"]):
        os.makedirs(name=settings.experiment["definition_dir"], exist_ok=True)
    if not os.path.exists(settings.logging["log_dir"]):
        os.makedirs(name=settings.logging["log_dir"], exist_ok=True)
    if not os.path.exists(settings.blueprint_dir):
        os.makedirs(name=settings.blueprint_dir, exist_ok=True)


def create_settings_file(
    project_name: str,
    data_format: Literal["toml", "yaml"] = "toml"
) -> None:
    """Creates the settings file on project creation. It uses a template
    to create the settings file.

    :param project_name: _description_
    :type project_name: str
    :param data_format: _description_, defaults to "toml"
    :type data_format: Literal[&quot;toml&quot;, &quot;yaml&quot;], optional
    """

    filename = "settings.toml"
    options = "Invalid file type"
    if data_format == "toml":
        options = toml.dumps(DEFAULT_SETTINGS)
    elif data_format == "yaml":
        filename = "settings.yaml"
        options = yaml.safe_dump(
            DEFAULT_SETTINGS, sort_keys=False, default_flow_style=False)

    # now craft the file
    env = Environment(loader=FileSystemLoader(
        os.path.join(project_name, 'templates')))
    template = env.get_template("settings.jinja")
    output = template.render(version=adgtk_ver, options=options)

    target_file = os.path.join(project_name, filename)
    with open(file=target_file, encoding="utf-8", mode="w") as outfile:
        outfile.write(output)


def build_experiment(
    use_formatting: bool = True,
    dark_mode: bool = False,
) -> None:
    """Builds an experiment and saves to disk

    :param dark_mode: account for dark mode, defaults to False
    :type dark_mode: bool, optional
    :param use_formatting: format the output?, defaults to True
    :type use_formatting: bool, optional
    :param terminal_css: The user requested CSS, defaults to None
    :type terminal_css: Union[TerminalCSS, None], optional

    """
    # Just in case. Build folder(s)
    build_folders_from_settings()

    # and now build the experiment
    builder = ExperimentBuilder(
        use_formatting=use_formatting,
        dark_mode=dark_mode,
        scenario_manager=None)

    builder.build_interactive()

# ---------------------------------------------------------------------
# Project functions
# ---------------------------------------------------------------------


def create_project(
    name: str,
    file_format: Literal["yaml", "toml"] = "toml"
) -> bool:
    """Creates a project with the basic information needed.

    Args:
        name (str): The project/directory name to create

    Returns:
        bool: True if successful, else False
    """
    if name is None:
        return False

    if os.path.exists(name):
        print("Unable to create a project. remove the other first!")
    elif name is None:
        print("Please specify a name of your project")
    else:
        print(f"Attempting to create {name}")
        filestream = importlib.resources.files(
            "adgtk").joinpath("template.tar").open("rb")

        archive = tarfile.open(fileobj=filestream)
        archive.extractall("./")
        archive.close()

        # and rename
        os.rename("template", name)

        # safety check
        if os.path.exists(name):
            # now create the settings.py
            create_settings_file(name, data_format=file_format)
            # and let the user know it worked
            print(f"Successfully created project {name}")
            return True

    print(f"Error creating {name}")
    return False


def destroy_project(name: str) -> bool:
    """Destroys a folder and all its contents

    Args:
        name (str): The folder to destroy
    """
    if name is not None:
        if os.path.exists(name):
            confirmation = input(
                f"CAUTION: Please type [{name}] to confirm deleting this project: ")
            if confirmation.lower() == name.lower():
                shutil.rmtree(name)
                if os.path.exists(name):
                    print("Failed to remove. Please check case")
                else:
                    print(f"Successfully destroyed {name}")
            else:
                print("No action taken.")
            return True
        else:
            print(f"Unable to find project {name} to destroy")
            return True

    return False


def execute(experiment: str) -> None:
    """Runs an experiment

    Args:
        experiment (str): The experiment-definition to run. This is the
            file located in the definition folder as outlined in the
            settings.py file.
    """
    if os.path.exists("settings.toml") or os.path.exists("settings.yaml"):
        start_logging(name=experiment, surpress_chatty=True, preview=False)
    else:
        print("Execution is unable to find the settings file")
        sys.exit(0)

    loader = ScenarioManager(experiment_definition_dir="experiment-def")
    loader.load_experiment(experiment)
    if loader.active_scenario is not None:
        loader.run_experiment()
    else:
        msg = "Failure establishing scenario from file"
        logging.error(msg)
        print(msg)

    sys.exit(0)


def preview(experiment: str) -> None:
    """Previews an experiment

    :param experiment: The experiment to preview.
    :type experiment: str
    """
    start_logging(name=experiment, surpress_chatty=True, preview=True)
    loader = ScenarioManager(experiment_definition_dir="experiment-def")
    loader.load_experiment(experiment)
    if loader.active_scenario is not None:
        loader.preview_experiment()
    else:
        print("Failure establishing scenario from file")

    sys.exit(0)


def print_title(
        dark_mode: bool = False,
        use_formatting: bool = True,
        terminal_css: Union[TerminalCSS, None] = None,
        clear_screen_first: bool = True
) -> None:
    """Clears the screen and prints to console the title

    :param dark_mode: account for dark mode, defaults to False
    :type dark_mode: bool, optional
    :param use_formatting: format the output?, defaults to True
    :type use_formatting: bool, optional
    :param terminal_css: The user requested CSS, defaults to None
    :type terminal_css: Union[TerminalCSS, None], optional
    """
    title_string = f"ADGTK - Version {adgtk_ver}"
    line = create_line(title_string)
    if clear_screen_first:
        clear_screen()

    if use_formatting:
        title_string = prepare_string(
            text=title_string,
            css="emphasis",
            terminal_css=terminal_css,
            dark_mode=dark_mode)
        line = prepare_string(
            text=line,
            css="emphasis",
            terminal_css=terminal_css,
            dark_mode=dark_mode)

    print(line)
    print(title_string)
    print(line)
    print()


# ---------------------------------------------------------------------
# interacting with files and folders
# ---------------------------------------------------------------------
def get_exp_comments_w_basename(file_w_path: str) -> tuple:
    title = os.path.basename(file_w_path)
    comments = "Not set"

    if file_w_path.lower().endswith(".toml"):
        with open(file_w_path, "r", encoding="utf-8") as infile:
            exp_def = toml.load(infile)
    elif file_w_path.lower().endswith(".yaml"):
        with open(file_w_path, "r", encoding="utf-8") as infile:
            exp_def = yaml.safe_load(infile)

    if title.endswith(".toml") or title.endswith(".yaml"):
        title = title[:-5]

    if "comments" in exp_def:
        if len(exp_def["comments"]) > 0:
            comments = exp_def["comments"]

    return title, comments


def list_experiments(
    exp_def_dir: Union[str, None] = None,
    use_formatting: bool = True,
    dark_mode: bool = False
) -> None:

    if exp_def_dir is None:
        # try the default
        exp_def_dir = "experiment-def"
    try:
        files = os.listdir(exp_def_dir)
    except FileNotFoundError:

        print(
            "ERROR: experiment definition directory not found. Check the path.")
        print("Unable to list experiments")
        return None

    title = "Experiment"
    comments = "Comments"
    msg = "  Available experiments"
    line = create_line("", char="-", modified=79)
    if use_formatting:
        msg = prepare_string(
            text=msg, css="emphasis", dark_mode=dark_mode)
    print(msg)
    print(line)

    for file in files:
        file_w_path = os.path.join(exp_def_dir, file)
        title, comments = get_exp_comments_w_basename(file_w_path)
        if use_formatting:
            title = prepare_string(
                text=title, css="emphasis", dark_mode=dark_mode)

        print(f"{title:<30} | {comments}")

    print(line)

# --------------------------------------------------------------------
# --------------------------------------------------------------------
#          !!! MANAGER !!! THIS IS THE MAIN FUNCTION
# --------------------------------------------------------------------
# --------------------------------------------------------------------


def manager() -> None:
    """provides a CLI management"""

    signal.signal(signal.SIGINT, signal_handler)

    args = parse_args()
    use_formatting = True
    inside_a_project = False
    # using local variables with a fallback to default for safety

    if args.no_color:
        use_formatting = False

    try:
        settings = load_settings()
        exp_def_dir = settings.experiment["definition_dir"]
        user_modules = settings.user_modules
        inside_a_project = True
        print("true, so oddly true?")
    except FileNotFoundError:
        exp_def_dir = None
        user_modules = []

    if args.Factory:
        if not inside_a_project:
            print("No setttings file found. Please check the path")
            sys.exit(0)
        group_label = args.Factory
        msg = f"Scenario factory/report for group {group_label}"
        if use_formatting:
            group_label = prepare_string(text=group_label, css="build")
            msg = f"Scenario factory/report for group {group_label}"
        line = create_line(msg, char=".")
        print_title(clear_screen_first=False, use_formatting=use_formatting)
        print(msg)
        print(line)
        print()
        scenario_mgr = ScenarioManager(
            load_user_modules=user_modules,
            use_formatting=use_formatting,
            dark_mode=False)

        print(scenario_mgr.group_report(args.Factory))

        # any problems loading?
        if len(scenario_mgr.load_user_modules_errs) > 0:
            print("ERRORS")
            print("------")
            for err in scenario_mgr.load_user_modules_errs:
                print(f" - {err}")
        sys.exit(0)

    if args.factory:
        if not inside_a_project:
            print("No setttings file found. Please check the path")
            sys.exit(0)

        msg = "Scenario factory/report"
        line = create_line(msg, char=".")
        print_title(clear_screen_first=False, use_formatting=use_formatting)
        print(msg)
        print(line)
        print()

        scenario_mgr = ScenarioManager(
            load_user_modules=user_modules,
            use_formatting=use_formatting,
            dark_mode=False)
        print(scenario_mgr)

        # any problems loading?
        if len(scenario_mgr.load_user_modules_errs) > 0:
            print("ERRORS")
            print("------")
            for err in scenario_mgr.load_user_modules_errs:
                print(f" - {err}")

        sys.exit(0)

    if args.Server:
        # https://docs.python.org/3/library/http.server.html
        print("TODO!! for now just do: py -m http.server")
        sys.exit(0)

    if args.list:
        print_title(clear_screen_first=False, use_formatting=use_formatting)
        list_experiments(exp_def_dir)
        sys.exit(0)

    if args.builder:
        if not inside_a_project:
            print("No setttings file found. Please check the path")
            sys.exit(0)

        print_title(clear_screen_first=True, use_formatting=use_formatting)
        build_experiment(use_formatting)
        sys.exit()

    if "destroy" in args and args.destroy is not None:
        print_title(clear_screen_first=False, use_formatting=use_formatting)
        if not destroy_project(args.destroy):
            print("Error processing\n")
        else:
            sys.exit()
    elif "create" in args and args.create is not None:
        print_title(clear_screen_first=False, use_formatting=use_formatting)
        if args.yaml:
            result = create_project(name=args.create, file_format="yaml")
        else:
            result = create_project(name=args.create, file_format="toml")
        if not result:
            print("Error processing\n")
        else:
            sys.exit()
    elif "preview" in args and args.preview is not None:
        if not inside_a_project:
            print("No setttings file found. Please check the path")
            sys.exit(0)

        print_title(clear_screen_first=True, use_formatting=use_formatting)
        preview(args.preview)

    elif "run" in args and args.run is not None:
        if not inside_a_project:
            print("No setttings file found. Please check the path")
            sys.exit(0)

        print_title(clear_screen_first=True, use_formatting=use_formatting)

        # remove any .toml or .yaml from the filename in order to be
        # consistent with the processing done with files and folders.
        if args.run.endswith(".toml") or args.run.endswith(".yaml"):
            args.run = args.run[:-5]
        execute(args.run)
    else:
        print("WARNING: No option specified.")
        print("Please see --help for more information\n")


if __name__ == '__main__':
    manager()
