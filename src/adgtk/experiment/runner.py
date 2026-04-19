"""runner.py is focused on running and managing a scenario. A Scenario
is the root of any experiment.

TODO
====

1. finalize design for how to handle results
2. log results, experiment run, etc
3. Test nested definitions

Defects
=======
1. log to console is not printing. observed w/nohop at least, need to TS
"""

import datetime
import os
import sys
# before importing others
# ----------------------------------------------------------------------
# Start of path verification
# ----------------------------------------------------------------------
path = os.getcwd()
bootstrap_file = os.path.join(path, "bootstrap.py")
if not os.path.exists(bootstrap_file):
    print("ERROR: Unable to locate the bootstrap.py. Please check your path.")
    sys.exit(1)
# ----------------------------------------------------------------------
# End of path verification
# ----------------------------------------------------------------------

# setup logfile for this and sub-modules
from adgtk.utils import create_logger
from logging import Logger
import inspect
from typing import Optional, Union
import yaml
from pydantic import ValidationError
from adgtk.common.defaults import (
    EXP_DEF_DIR,
    BATCH_DEF_DIR,
    SCENARIO_LOGGER_NAME
)
from adgtk.experiment.structure import (
    AttributeEntry,
    ExperimentDefinition,
    ScenarioResults,
    ScenarioProtocol,
    BuildComponentResult,
)
import adgtk.factory.component as factory
import adgtk.tracking.project as project_manager
import adgtk.tracking.journal as exp_journal
from adgtk.tracking.structure import (
    AvailableExperimentModel,
    ExperimentRunFolders)
from adgtk.tracking.utils import setup_run
from adgtk.utils import get_user_input
from adgtk.experiment.structure import BatchDefinition


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
RESULTS_FILE = "results.yaml"
RUN_CONFIG_FILE = "run.exp.config.yaml"
TO_CONSOLE = False                           # for development only

# ----------------------------------------------------------------------
# Logging. target log varies by need
# ----------------------------------------------------------------------
_logger: Optional[Logger] = None

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _contains_blueprint_dir(path: str) -> bool:
    """Checks if the path contains the experiment blueprints directory.

    Args:
        path: The path to inspect.

    Returns:
        True if the path contains the blueprints directory, False otherwise.
    """

    # Normalize path to avoid issues with slashes
    parts = os.path.normpath(path).split(os.sep)
    return EXP_DEF_DIR in parts


def _contains_batch_dir(path: str) -> bool:
    """Checks if the path contains the batch directory.

    Args:
        path: The path to inspect.

    Returns:
        True if the path contains the batch directory, False otherwise.
    """
    parts = os.path.normpath(path).split(os.sep)
    return BATCH_DEF_DIR in parts


def _build_component(
    attribute_def: AttributeEntry,
) -> BuildComponentResult:
    """Builds a component recursively based on the attribute definition.

    Args:
        attribute_def: The configuration entry to build.

    Returns:
        The built component. At the root, it is usually a Callable (Scenario);
        otherwise, it returns primitive types or lists.

    Raises:
        ValueError: If the entry type is invalid or the definition is corrupt.
    """

    # setup
    if isinstance(attribute_def, dict):
        try:
            attribute_def = AttributeEntry(**attribute_def)
        except Exception:
            msg = f"Invalid enty type: {attribute_def}"
            if _logger is not None:
                _logger.error(msg)
            raise ValueError(msg)
    if isinstance(attribute_def.init_config, (bool, int, str, float)):
        msg = (f"Attribute: {attribute_def.attribute} = "
               f"{attribute_def.init_config}")
        if _logger is not None:
            _logger.info(msg)
        return attribute_def.init_config

    # 1. ensure proper type alignment
    if not isinstance(attribute_def, AttributeEntry):
        try:
            attribute_def = AttributeEntry(**attribute_def)
        except ValidationError:
            msg = f"Corrupt definition: {attribute_def}"
            raise ValueError(msg)

    # 1.5 A list[str], list[bool], etc
    factory_id = attribute_def.factory_id
    if factory_id is None:
        # its not a factory id. so. prepare as-is
        # TODO: do better at typing.
        return attribute_def.init_config    # type: ignore
        # msg = f"Corrupt definition: {attribute_def}"
        # if _logger is not None:
        #     _logger.info(msg)
        # raise ValueError(msg)

    if not attribute_def.factory_init:
        msg = f"Getting creator not init for {factory_id}"
        if _logger is not None:
            _logger.info(msg)

        return factory.get_callable(factory_id)

    # 2. assemble init values (if going to init)
    args = {}
    init_config = attribute_def.init_config
    # in the event factory can init but there is nothing to config and
    # the user code does not set init_config.
    if init_config is None:
        init_config = []

    if init_config is None:
        msg = f"Corrupt definition: {attribute_def}. Unexpected None"
        if _logger is not None:
            _logger.info(msg)

        raise ValueError(msg)

    if not isinstance(init_config, list):
        msg = f"Corrupt definition: {attribute_def}. Expected init_config list"
        if _logger is not None:
            _logger.info(msg)
        raise ValueError(msg)

    for item in init_config:
        if isinstance(item, dict):
            try:
                item = AttributeEntry(**item)
            except ValidationError:
                msg = f"Unexpected dict: {init_config}"
                if _logger is not None:
                    _logger.info(msg)
                raise ValueError(msg)

        # and final check
        if isinstance(item, AttributeEntry):
            args[item.attribute] = _build_component(item)

    result = factory.create(factory_id=factory_id, **args)
    return result   # type: ignore


def _load_scenario(
        exp_config: ExperimentDefinition) -> ScenarioProtocol:
    """Loads a scenario after performing structural safety checks.

    Args:
        exp_config: The experiment definition to load.

    Returns:
        An instantiated scenario object implementing the ScenarioProtocol.

    Raises:
        ValueError: If the definition is invalid or if the built object
            fails to implement ScenarioProtocol.
    """

    # Safety checks
    if not isinstance(exp_config, ExperimentDefinition):
        try:
            exp_config = ExperimentDefinition(**exp_config)
        except ValidationError:
            msg = "Invalid experiment definition"
            raise ValueError(msg)

    scenario_config = exp_config.init_config

    if not isinstance(scenario_config, AttributeEntry):
        msg = f"Invalid Scenario definition. got {type(scenario_config)}"
        if _logger is not None:
            _logger.info(msg)
        raise ValueError(msg)
    # now build
    msg = f"Attempting to load Scenario: {scenario_config}"
    if _logger is not None:
        _logger.info(msg)
    scenario = _build_component(scenario_config)

    if not isinstance(scenario, ScenarioProtocol):
        msg = (
            "Object defined does not implement the Scenario Protocol. "
            f"Type found is {type(scenario)}"
        )
        if _logger is not None:
            _logger.error(msg)
        raise ValueError(msg)

    # and one last safety check
    if inspect.isclass(scenario):
        msg = f"failed to create scenario. created: {type(scenario)}"
        if _logger is not None:
            _logger.info(msg)
        raise ValueError(msg)

    return scenario


def _load_experiment_file(filename: str) -> ExperimentDefinition:
    """Loads and validates an experiment definition from a YAML file.

    Args:
        filename: The name or path of the YAML file to load.

    Returns:
        A validated ExperimentDefinition object.

    Raises:
        ValueError: If the YAML file is malformed.
    """
    # get config
    if not _contains_blueprint_dir(filename):
        file_w_path = os.path.join("blueprints", filename)
    else:
        file_w_path = filename

    if not file_w_path.endswith(".yaml"):
        file_w_path += ".yaml"

    with open(file=file_w_path, mode="r", encoding="utf-8") as infile:
        try:
            exp_def = yaml.safe_load(infile)
        except yaml.YAMLError:
            msg = f"Malformed file: {file_w_path}"
            if _logger is not None:
                _logger.info(msg)
            raise ValueError(msg)

    # and convert for safety and validation
    try:
        exp_config = ExperimentDefinition(**exp_def)
    except ValidationError:
        msg = f"Corrupted experiment configuration: {filename}"
        if _logger is not None:
            _logger.info(msg)
        sys.exit(1)

    return exp_config


def _select_experiment() -> str:
    """Displays available experiments and prompts the user for a selection.

    Returns:
        The name of the selected experiment.

    Raises:
        ValueError: If there is an unexpected type encountered during listing.
        RuntimeError: If the selection process fails.
    """
    choices = []
    idx_to_choice_map = []

    available_list = project_manager.get_available_experiments()
    if len(available_list) == 0:
        msg = "No available experiments found."
        if _logger is not None:
            _logger.info(msg)
        print(msg)
        sys.exit(0)

    name_str = "name"
    desc_str = "description"

    title = f"{name_str:<25} | {desc_str}"
    bar_length = len(title)
    entries_str = ""
    for idx, entry in enumerate(available_list):
        if not isinstance(entry, AvailableExperimentModel) and \
                isinstance(entry, dict):
            try:
                entry = AvailableExperimentModel(**entry)
            except ValidationError:
                msg = ("Unexpected type from project_manager for exp "
                       f"listing. Observed: {type(entry)}")
                if _logger is not None:
                    _logger.info(msg)
                raise ValueError(msg)

        entry_str = f" {idx} : {entry.name:<22} | {entry.description}"
        if len(entry_str) > bar_length:
            bar_length = len(entry_str)
        entries_str += f"{entry_str}\n"
        choices.append(entry.name)
        choices.append(str(idx))
        idx_to_choice_map.append(entry.name)

    bar = "="*bar_length
    output_str = f"\n{title}\n{bar}\n{entries_str}\n"
    print(output_str)
    exp_choice = get_user_input(
        user_prompt="Which experiment do you want to run",
        requested="str",
        choices=choices,
        helper="Based on current blueprints folder listing"
    )
    try:
        idx = int(exp_choice)
        return idx_to_choice_map[idx]
    except ValueError:
        if isinstance(exp_choice, str):
            return exp_choice

    if _logger is not None:
        _logger.info("Failed to determine experiment")
    raise RuntimeError("Get experiment failure")


def _save_copy_of_config(
    config: Union[ExperimentDefinition, dict],
    root_dir: str
) -> None:
    """Saves a copy of the experiment configuration to the run directory.

    Args:
        config: The configuration object or dictionary.
        root_dir: The destination directory for the configuration copy.

    Raises:
        FileNotFoundError: If the root_dir does not exist.
    """
    if not os.path.exists(root_dir):
        raise FileNotFoundError(root_dir)

    if isinstance(config, ExperimentDefinition):
        config = config.model_dump()

    file_w_path = os.path.join(root_dir, RUN_CONFIG_FILE)
    with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
        yaml.dump(config, outfile)


# ----------------------------------------------------------------------
# Public
# ----------------------------------------------------------------------
# Design detail: Only the public can set the _logger. This helps ensure
# a consistent behavior with the logger.

def run_scenario(
    filename: Optional[str] = None,
    append_timestamp: bool = False,
    use_count: bool = True,
    print_to_console: bool = True
) -> tuple[ScenarioResults, ExperimentRunFolders]:
    """Executes a scenario based on an experiment definition file.

    Args:
        filename: The experiment file to load. If None, triggers UX selection.
        append_timestamp: Whether to include a timestamp in the run ID.
        use_count: Whether to use an incremental integer for the run ID.
        print_to_console: Whether to log output to the console.

    Returns:
        A tuple containing the ScenarioResults and the ExperimentRunFolders.
    """
    global _logger
    exp_journal.reset()  # cover any batch processing
    if filename is None:
        exp_name = _select_experiment()
        exp_name += ".yaml"
        filename = os.path.join(EXP_DEF_DIR, exp_name)
    config = _load_experiment_file(filename)
    run_id = project_manager.get_next_experiment_run_id(
        experiment_name=config.name,
        use_count=use_count,
        append_timestamp=append_timestamp,
        prefix=None
    )
    _logger = create_logger(
        logfile="scenario.log",
        logger_name=SCENARIO_LOGGER_NAME,
        subdir="runs",
        experiment_name=config.name,
        log_to_console=print_to_console or TO_CONSOLE
    )
    # setup the folders for the results
    folders = setup_run(experiment_name=config.name, run_id=run_id)
    # and save a copy for future reference
    _save_copy_of_config(config=config, root_dir=folders.root_dir)
    # so I  can log
    log_file = os.path.join("logs", "runs", config.name, "scenario.log")
    scenario = _load_scenario(config)
    _logger.info("-"*60)
    _logger.info("Starting Scenario")
    _logger.info("Results folder: %s", folders.root_dir)
    _logger.info("Starting logging at %s", log_file)
    _logger.info("-"*60)
    intro = f"| Starting experiment {config.name}: run {run_id} |"
    print("-"*len(intro))
    print(intro)
    print("-"*len(intro))
    result = scenario.run_scenario(result_folders=folders)
    exp_journal.save_journal(folders.conclusion)
    _logger.info("-"*60)
    _logger.info("Scenario Execution complete")
    _logger.info("-"*60)

    # ensure valid
    if not isinstance(result, ScenarioResults):
        try:
            result = ScenarioResults(**result)
        except ValidationError:
            msg = "Unable to convert Scenario result. Unable to update project"
            _logger.error(msg)
            print("ERROR: " + msg)

    # no central tracking of results. saving on-disk. less to centrally manage
    # and if in the future a listing is needed its safer to walk the disk.
    results_file_w_path = os.path.join(folders.conclusion, RESULTS_FILE)

    with open(file=results_file_w_path, mode="w", encoding="utf-8") as outfile:
        yaml.safe_dump(result.model_dump(), outfile)
    return (result, folders)


def run_batch(filename: str, print_to_console: bool = True) -> None:
    """Executes a series of experiments defined in a batch file.

    Args:
        filename: The path to the batch YAML configuration.
        print_to_console: Whether to log output to the console.

    Raises:
        FileNotFoundError: If the batch file cannot be located.
    """
    global _logger
    if _logger is None:
        _logger = create_logger(
            logfile="adgtk.runner.log",
            logger_name=__name__,
            subdir="framework",
            log_to_console=print_to_console or TO_CONSOLE
        )

    if not _contains_batch_dir(filename):
        filename = os.path.join(BATCH_DEF_DIR, filename)

    if not filename.endswith(".yaml"):
        filename += ".yaml"

    if not os.path.exists(filename):
        msg = f"Unable to find batch: {filename}"

        _logger.info(msg)

        raise FileNotFoundError(msg)

    with open(file=filename, mode="r", encoding="utf-8") as infile:
        data = yaml.safe_load(infile)

    try:
        batch = BatchDefinition(**data)

    except ValidationError:
        msg = f"Corrupt batch file: {filename}"
        if _logger:
            _logger.error(msg)
        print(msg)  # always print when this occurs
        sys.exit(1)

    # now run the experiments. serially of course.
    _logger.info("Starting batch run %s", batch.name)
    print(f"Starting batch run {batch.name}")
    for idx, experiment in enumerate(batch.experiments):
        print(f"{datetime.datetime.now()} Running Experiment: {experiment}: "
              f"{idx} of {len(batch.experiments)}")
        _logger.info("Batch running experiment %s. %d of %d",
                     experiment,
                     idx,
                     len(batch.experiments))

        _ = run_scenario(filename=experiment)
