"""Handlers for the CLI tools for this project
"""

import logging
from typing import Literal, Union
import argparse
import sys
import os
import shutil
import signal
import tarfile
import importlib.resources
import toml
import yaml
from jinja2 import Environment, FileSystemLoader
from adgtk.common import DEFAULT_SETTINGS, DEFAULT_EXP_DEF_DIR
from adgtk.scenario import ScenarioManager
from adgtk.experiment import ExperimentBuilder
from adgtk.utils import (
    get_user_input,
    start_logging,
    clear_screen,
    create_line,
    load_settings)
from adgtk import __version__ as adgtk_ver
from .intro import intro

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

    # modifiers
    parser.add_argument(
        '-f','--file',        
        type=str,
        help="override the settings file with this file")
    parser.add_argument(
        '--version', action='version', version=f"ADGTK {adgtk_ver}")
    parser.add_argument(
        '--sample',
        action='store_true',
        help="Creates a project with sample code.")
    parser.add_argument(
        "--yaml",
        help="Use YAML format when creating the project settings.file.",
        action="store_true")

    # now positional
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands")

    # Project
    project_parser = subparsers.add_parser("project", help="Project actions")
    project_parser.add_argument(
        "action",
        choices=["create", "destroy"],
        help="Available project actions")
    project_parser.add_argument(
        "name",
        type=str,
        nargs="?",
        help="The project name")

    # Experiment
    exp_parser = subparsers.add_parser(
        "experiment", help="Experiment actions")
    exp_parser.add_argument(
        "action",
        choices=["create", "destroy", "list", "run", "preview"],
        help="Available experiment actions")
    exp_parser.add_argument(
        "name",
        type=str,
        nargs="?",
        help="The experiment name")

    # Factory
    factory_parser = subparsers.add_parser(
        "factory", help="Factory actions")
    factory_parser.add_argument(
        "name",
        type=str,
        nargs="?",
        help="The group name")
    

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
    data_format: Literal["toml", "yaml"] = "toml",
    clean: bool = False
) -> None:
    """Creates the settings file on project creation. It uses a template
    to create the settings file.

    :param project_name: The project name to be created
    :type project_name: str
    :param data_format: The format of the settings file,
        defaults to "toml"
    :type data_format: Literal[&quot;toml&quot;, &quot;yaml&quot;],
        optional
    :param clean: _description_, defaults to False
    :type clean: bool, optional        
    """

    filename = "project.toml"
    options = "Invalid file type"

    settings_data = DEFAULT_SETTINGS.copy()
    if clean:
        settings_data["user_modules"] = []

    if data_format == "toml":        
        options = toml.dumps(settings_data)
    elif data_format == "yaml":
        filename = "project.yaml"
        options = yaml.safe_dump(
            settings_data, sort_keys=False, default_flow_style=False)

    # now craft the file
    env = Environment(loader=FileSystemLoader(
        os.path.join(project_name, 'templates')))
    template = env.get_template("settings.jinja")
    output = template.render(version=adgtk_ver, options=options)

    target_file = os.path.join(project_name, filename)
    with open(file=target_file, encoding="utf-8", mode="w") as outfile:
        outfile.write(output)


def build_experiment(
    experiment_definition_dir: str,
    load_user_modules:list,
    use_formatting: bool = True,    
    name: Union[str, None] = None
) -> None:
    """Builds an experiment and saves to disk


    :param name: The name of the experiment, defaults to None
    :type name: Union[str, None], optional
    """
    # Just in case. Build folder(s)
    build_folders_from_settings()

    # and now build the experiment
    builder = ExperimentBuilder(
        experiment_definition_dir=experiment_definition_dir,
        load_user_modules=load_user_modules,
        scenario_manager=None)

    builder.build_interactive(name)

# ---------------------------------------------------------------------
# Project functions
# ---------------------------------------------------------------------

def create_project(
    name: str,
    file_format: Literal["yaml", "toml"] = "toml",
    sample: bool = False
) -> bool:
    """Creates a project

    :param name: The project/directory name to create
    :type name: str
    :param file_format: the format of the settings, defaults to "toml"
    :type file_format: Literal[&quot;yaml&quot;, &quot;toml&quot;], optional
    :param sample: Include sample files, defaults to False
    :type sample: bool, optional
    :return: True if successful, else False
    :rtype: bool
    """
    print(f"Creating project: {sample}")

    if name is None:
        return False
    
    if os.path.exists(name):
        print("Unable to create a project. remove the other first!")
    elif name is None:
        print("Please specify a name of your project")
    else:
        print(f"Attempting to create {name}")
        if not sample:
            # the clean.tar doesn't have the sample code. See Makefile
            filestream = importlib.resources.files(
                "adgtk").joinpath("clean.tar").open("rb")
        else:
            filestream = importlib.resources.files(
                "adgtk").joinpath("template.tar").open("rb")

        archive = tarfile.open(fileobj=filestream)
        archive.extractall("./")
        archive.close()

        # and rename
        os.rename("project_template", name)

        # safety check
        if os.path.exists(name):
            # now create the settings.py
            clean = True
            if sample:
                clean = False
                
            create_settings_file(name, data_format=file_format, clean=clean)
            # and let the user know it worked
            print(f"Successfully created project {name}")
            print(f"`cd {name}` to work with the project")
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
            exp_file = os.path.join(name, "project.toml")
            if not os.path.exists(exp_file):
                print("Does not appear to be an ADGTK project. Cancelling")
                return False
            ask_to_remove = f": Please type [{name}] to confirm deleting this project: "
            confirmation = input(ask_to_remove)
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


def execute(experiment: str, load_user_modules:list) -> None:
    """Runs an experiment

    Args:
        experiment (str): The experiment-definition to run. This is the
            file located in the definition folder as outlined in the
            settings.py file.
    """
    if os.path.exists("project.toml") or os.path.exists("project.yaml"):
        start_logging(name=experiment, surpress_chatty=True, preview=False)
    else:
        print("Execution is unable to find the settings file")
        sys.exit(0)

    loader = ScenarioManager(
        load_user_modules=load_user_modules,
        experiment_definition_dir=DEFAULT_EXP_DEF_DIR)
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
    loader = ScenarioManager(
        experiment_definition_dir=DEFAULT_EXP_DEF_DIR)
    loader.load_experiment(experiment)
    if loader.active_scenario is not None:
        loader.preview_experiment()
    else:
        print("Failure establishing scenario from file")

    sys.exit(0)


def print_title(clear_screen_first: bool = True) -> None:
    """Clears the screen and prints to console the title

    :param clear_screen_first: Clear screen first, defaults to True
    :type clear_screen_first: bool, optional
    """

    title_string = f"ADGTK - Version {adgtk_ver}"
    line = create_line(title_string)
    if clear_screen_first:
        clear_screen()

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
    error_found = False
    exp_def = {}
    if file_w_path.lower().endswith(".toml"):
        with open(file_w_path, "r", encoding="utf-8") as infile:
            exp_def = toml.load(infile)
    elif file_w_path.lower().endswith(".yaml"):
        with open(file_w_path, "r", encoding="utf-8") as infile:
            try:
                exp_def = yaml.safe_load(infile)
            except yaml.parser.ParserError as e:
                error_found = True
                comments = f"INVALID: {e}"

    if title.endswith(".toml") or title.endswith(".yaml"):
        title = title[:-5]

    if not error_found:
        if "comments" in exp_def:
            if len(exp_def["comments"]) > 0:
                comments = exp_def["comments"]

    return title, comments


def get_experiment_list(exp_def_dir: Union[str, None] = None) -> list:
    if exp_def_dir is None:
        # try the default
        exp_def_dir = DEFAULT_EXP_DEF_DIR
    try:
        in_files = os.listdir(exp_def_dir)
        files = sorted(in_files)
    except FileNotFoundError:
        print(
            "ERROR: experiment definition directory not found. Check the path.")
        print("Unable to list experiments")
        return []

    return files


def get_exp_to_run(exp_def_dir: Union[str, None] = None) -> str:

    if exp_def_dir is None:
        exp_def_dir = DEFAULT_EXP_DEF_DIR

    experiments = get_experiment_list(exp_def_dir=exp_def_dir)
    if len(experiments) == 0:
        print(f"No experiments found. Please check path for {exp_def_dir}")
        sys.exit(1)

    title = "Experiment"
    comments = "Comments"
    msg = "  Select which experiment to run:"
    line = create_line("", char="-", modified=79)
    print(msg)
    print(line)
    choices = []

    for file in experiments:
        file_w_path = os.path.join(exp_def_dir, file)
        title, comments = get_exp_comments_w_basename(file_w_path)
        choices.append(title)
        print(f"{title:<40} | {comments}")

    print()
    val = get_user_input(
        configuring="experiment",
        request="Which experiment to run?",
        choices=choices,
        requested="str")
    
    return str(val)


def list_experiments(exp_def_dir: Union[str, None] = None) -> list:

    if exp_def_dir is None:
        exp_def_dir = DEFAULT_EXP_DEF_DIR

    experiments = get_experiment_list(exp_def_dir=exp_def_dir)
    if len(experiments) == 0:
        return []

    title = "Experiment"
    comments = "Comments"
    msg = "  Available experiments"
    line = create_line("", char="-", modified=79)
    print(msg)
    print(line)

    experiments = []

    for file in experiments:
        file_w_path = os.path.join(exp_def_dir, file)
        title, comments = get_exp_comments_w_basename(file_w_path)
        experiments.append(title)
        print(f"{title:<40} | {comments}")

    print(line)
    return experiments

# --------------------------------------------------------------------
# --------------------------------------------------------------------
#          !!! MANAGER !!! THIS IS THE MAIN FUNCTION
# --------------------------------------------------------------------
# --------------------------------------------------------------------


def manager() -> None:
    """provides a CLI management"""

    signal.signal(signal.SIGINT, signal_handler)

    args = parse_args()
    inside_a_project = False
    # using local variables with a fallback to default for safety

    try:
        if args.file is not None:
            print(f"ADGTK: Loading settings from file {args.file}")
            settings = load_settings(args.file)
        else:
            settings = load_settings()
        exp_def_dir = settings.experiment["definition_dir"]
        user_modules = settings.user_modules
        inside_a_project = True
    except FileNotFoundError:
        exp_def_dir = None
        user_modules = []    
    except ValueError:
        msg  = f"""
ERROR: Unable to load settings from {args.file}
Reminder: File must end with .toml or .yaml and be properly formatted.
"""
        print(msg)
        sys.exit(1)

    # ----- Project command ------
    if args.command == 'project':
        if args.name is None:
            print("Name of the project is required")
            sys.exit()
        print(args)
        sample = False

        if args.action == "create":
            if args.sample:
                print("TT")
                sample = False
                if args.sample:
                    sample = True
        
            if args.yaml:
                result = create_project(
                    name=args.name, file_format="yaml", sample=sample)
            else:
                result = create_project(
                    name=args.name, file_format="toml", sample=sample)
            if not result:
                print("Error processing\n")
        elif args.action == "destroy":
            if not destroy_project(args.name):
                print("Error processing\n")

        sys.exit(0)

    # ----- experiment command ------
    elif args.command == 'experiment':
        if not inside_a_project:
            print("No setttings file found. Please check the path")
            sys.exit(0)

        # work the action
        if args.action == "list":
            print_title(clear_screen_first=False)
            _ = list_experiments(exp_def_dir)
        elif args.action == "run":
            if args.name is None:
                exp_file = get_exp_to_run(exp_def_dir)
                execute(experiment=exp_file, load_user_modules=user_modules)
            else:
                # cleanup
                if exp_def_dir in args.name:
                    args.name.replace(exp_def_dir, "")
                    args.name.replace("/", "")
                    args.name.replace("\\", "")
                if args.name.endswith(".toml") or args.name.endswith(".yaml"):
                    args.name = args.run[:-5]

                # and execute
                execute(experiment=args.name, load_user_modules=user_modules)

            sys.exit(0)

        elif args.action == "create":
            print_title(clear_screen_first=True)
            build_experiment(
                experiment_definition_dir=exp_def_dir,                
                load_user_modules=user_modules,
                name=args.name)

        elif args.action == "destroy":
            print("Roadmap item. Not implemented yet")
        elif args.action == "preview":
            print_title(clear_screen_first=True)
            preview(args.Preview)
        sys.exit(0)

    elif args.command == "factory":
        if not inside_a_project:
            print("No setttings file found. Please check the path")
            sys.exit(0)

        print_title(clear_screen_first=False)

        if args.name is not None:
            msg = f"Scenario factory/report for group {args.name}"
            group_label = args.name

            msg = f"Scenario factory/report for group {group_label}"
            line = create_line(msg, char=".")
            print(msg)
            print(line)
            print()
            scenario_mgr = ScenarioManager(load_user_modules=user_modules)
            print(scenario_mgr.group_report(args.name))

            # any problems loading?
            if len(scenario_mgr.load_user_modules_errs) > 0:
                print("ERRORS")
                print("------")
                for err in scenario_mgr.load_user_modules_errs:
                    print(f" - {err}")
        else:
            msg = "Scenario factory/report"
            line = create_line(msg, char=".")
            print(msg)
            print(line)
            print()

            scenario_mgr = ScenarioManager(load_user_modules=user_modules)
            print(scenario_mgr)

            # any problems loading?
            if len(scenario_mgr.load_user_modules_errs) > 0:
                print("ERRORS")
                print("------")
                for err in scenario_mgr.load_user_modules_errs:
                    print(f" - {err}")

        # end of factory option
        sys.exit(0)

    print(intro)
    sys.exit()


if __name__ == '__main__':
    manager()
