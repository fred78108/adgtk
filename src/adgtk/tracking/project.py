"""project.py is responsible for tracking experiments within a project.

Goals
=====
1. an inventory of experiments that the agent performed.
2. an easy to use mechanism for the agent to refer back to later.

Design
======
writes: The scenario runner will record the results here.


Note
====
1. going with json over a database for ease of use/code maintenance over
   the speed found in a database. This approach also allows for easy
   updates to data structures and patterns. Future designs may rely on
   a database of course. For now, keeping things simple.

TODO
====
1. consider adding tagging functionality. perhaps by feature?
2. write list_experiment_results function
3. do I write scenario results here?
"""
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
from adgtk.tracking.structure import (
    AvailableExperimentModel,
    ExperimentEntryModel,
    PrefixModel,
    EXP_RESULTS_FOLDER,
    EXP_RUN_DIR,
    TRACKING_FOLDER)
from adgtk.common.defaults import EXP_DEF_DIR
from pydantic import BaseModel, ValidationError
import yaml
import uuid
from typing import Optional, Literal
import secrets
import json
import datetime
import copy
from adgtk.utils import create_logger

# Set up module-specific logger
_logger = create_logger(
    "adgtk.project.log",
    logger_name=__name__,
    subdir="framework"
)

# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------

# data
_log: list[ExperimentEntryModel] = []
_prefix_entries: dict[str, BaseModel] = {}
_available_experiments: list[AvailableExperimentModel] = []

PROJECT_LOG_FILE = "project.json"
PROJECT_PREFIX_FILE = "prefix.json"
AVAILABLE_FILE = "available.experiments.json"
COMPLETED_FILE = "completed.experiments.json"
# control
_log_loaded: bool = False
_prefix_loaded: bool = False

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _load_prefix_file():
    """Loads the prefix file from disk

    :raises ValueError: Issues with the file
    """
    global _prefix_entries, _prefix_loaded
    file_w_path = os.path.join(TRACKING_FOLDER, PROJECT_PREFIX_FILE)
    os.makedirs(TRACKING_FOLDER, exist_ok=True)
    if os.path.exists(file_w_path):
        with open(file=file_w_path, mode="r", encoding="utf-8") as infile:
            tmp = json.load(infile)

        for k, v in tmp.items():
            try:
                _prefix_entries[k] = PrefixModel(**v)
            except ValidationError:
                msg = f"Corrupt {file_w_path} prefix file."
                _logger.error(msg)
                raise ValueError(msg)

    _prefix_loaded = True
    _logger.info(f"Loaded prefix_file: {file_w_path}")


def _save_prefix_file():
    """Saves the prefix data to disk
    """
    global _prefix_entries, _prefix_loaded
    file_w_path = os.path.join(TRACKING_FOLDER, PROJECT_PREFIX_FILE)
    os.makedirs(TRACKING_FOLDER, exist_ok=True)

    prefix_dict = {k: v.model_dump() for k, v in _prefix_entries.items()}
    with open(file=file_w_path, mode="w", encoding="utf-8") as outfile:
        json.dump(prefix_dict, outfile)
        _logger.info(f"Saved prefix_file: {file_w_path}")


def _load_log(clear_existing: bool = False, ok_to_create: bool = True):
    """Loads the log into memory. If there are already entries which is
    an unintended state there is additional safety with the ability to
    ignore via the clear_existing

    :param clear_existing: If exiting is found clear?, defaults to False
    :type clear_existing: bool, optional
    :param ok_to_create: if the file doesn't exit, it creates it,
        defaults to True
    :type ok_to_create: bool, optional
    """

    global _log, _log_loaded    # pylint: disable=global-statement

    file_w_path = os.path.join(TRACKING_FOLDER, PROJECT_LOG_FILE)
    if not os.path.exists(file_w_path):
        if not ok_to_create:
            msg = f"missing_project_log_file: {file_w_path}. unable to load"
            _logger.error(msg)
            raise ValueError(msg)

        # creating the logfile
        os.makedirs(TRACKING_FOLDER, exist_ok=True)
        with open(file_w_path, "w", encoding="utf-8") as f:
            f.write("[]")
            _logger.info(f"Creating project logfile: {file_w_path}")

    with open(file=file_w_path, mode="r", encoding="utf-8") as infile:
        data = json.load(infile)

    # clear the _log.
    if clear_existing:
        if len(_log) > 0:
            _logger.warning("cleared entries in performance log due to load")
        _log = []
    # now convert data back to ExperimentEntryModel
    try:
        for entry in data:
            _log.append(ExperimentEntryModel(**entry))
    except ValidationError as e:
        msg = f"Corrupt project journal: {e}"
        _logger.error(msg)
        raise

    _logger.info("Loaded project log from %s", file_w_path)
    _log_loaded = True


def _save_log():
    """Saves the log to disk.
    """

    file_w_path = os.path.join(TRACKING_FOLDER, PROJECT_LOG_FILE)
    os.makedirs(TRACKING_FOLDER, exist_ok=True)

    log_as_dict = [entry.model_dump() for entry in _log]

    # Now write to JSON
    with open(file=file_w_path, mode='w', encoding="utf-8") as outfile:
        json.dump(log_as_dict, outfile, indent=2)

    _logger.info("Saved project log to %s", file_w_path)


def _refresh_using_blueprints():
    """This function will use the files in the blueprints directory to
    refresh the internal tracking by deleting all current entries and by
    processing each file in this directory repopulate the tracking data.

    It does not modify the prefix tracking, only the experiment
    inventory.
    """
    global _available_experiments

    files = os.listdir(EXP_DEF_DIR)
    files_w_path = [os.path.join(EXP_DEF_DIR, file) for file in files]
    for file in files_w_path:
        with open(file=file, mode="r", encoding="utf-8") as infile:
            try:
                file_data = yaml.safe_load(infile)
            except yaml.YAMLError:
                _logger.error(f"Unable to process {file} on refresh.")
                continue

            # verify naming alignment (file to file_data.name)
            file_part = os.path.basename(file)
            if not file_part.removesuffix(".yaml") == file_data["name"]:
                _logger.error(f"name to filename mismatch for {file}")
                continue
            try:
                entry = AvailableExperimentModel(
                    name=file_data["name"],
                    description=file_data["description"])
            except KeyError:
                _logger.error(f"missing required keys for {file}")
                continue

            _available_experiments.append(entry)


# ----------------------------------------------------------------------
# Experiment focused entries
# ----------------------------------------------------------------------
def get_entries_by_name(name: str) -> list[ExperimentEntryModel]:
    """Searches projects based on a filename.

    Reminder: id must be unique but name can have multiple. this allows
    for multiple runs of the same experiment.

    :param name: The name to search for.
    :type name: str
    :return: a list of all entries found with this name.
    :rtype: list[ExperimentEntryModel]
    """
    if not _log_loaded:
        _load_log(clear_existing=False)

    found = []
    for entry in _log:
        if entry.name == name:
            found.append(entry)
    return found


def get_entry_by_id(experiment_id: str) -> ExperimentEntryModel:
    """Retrieves an experiment by id

    :param experiment_id: The id of the experiment to retrieve
    :type experiment_id: str
    :raises KeyError: id is not found
    :return: The entry in the log
    :rtype: ExperimentEntryModel
    """
    for entry in _log:
        if entry.id == experiment_id:
            return entry

    msg = f"experiment id: {experiment_id} not found"
    raise KeyError(msg)


def id_exists(experiment_id: str) -> bool:
    """Confirms the id is unique.

    :param experiment_id: The ID to search for
    :type experiment_id: str
    :return: True if found
    :rtype: bool
    """
    for entry in _log:
        if entry.id == experiment_id:
            return True
    return False


def add_entry(
    entry: ExperimentEntryModel,
    request_prefix_registration: bool = False,
    register_prefix_delimiter="."
) -> None:
    """Adds an experiment entry into the log.

    If `request_prefix_registration` is True, attempts to register a
    prefix using the experiment name (split by the specified delimiter).
    The function ensures that the entry ID is unique (generates one if
    missing), appends the entry to the log, and saves the log to disk.

    :param entry: The experiment entry to add.
    :type entry: ExperimentEntryModel
    :param request_prefix_registration: If True, auto-registers a prefix
        from the experiment name using the delimiter. Defaults to False.
    :type request_prefix_registration: bool, optional
    :param register_prefix_delimiter: Delimiter used to split the
        experiment name for prefix registration. Defaults to ".".
    :type register_prefix_delimiter: str, optional
    :raises KeyError: If an entry with the same ID already exists.
    """
    if not _log_loaded:
        _load_log(clear_existing=False)

    if request_prefix_registration:
        # Provide a bit of convience in scenarios to save the user a step.
        splits = entry.name.split(register_prefix_delimiter)
        if len(splits) < 2:
            msg = (f"Unable to split {entry.name} using "
                   f"{register_prefix_delimiter}. Unable to register prefix")
            _logger.warning(msg)
        else:
            prefix = splits[0]
            start_major = 0
            start_minor = 0
            if len(splits) == 3:
                try:
                    start_major = int(splits[1])
                    start_minor = int(splits[2])
                except ValueError:
                    pass

            register_prefix(
                prefix=prefix,
                start_major=start_major,
                start_minor=start_minor)

    if entry.id is None:
        entry.id = str(uuid.uuid4())
    if id_exists(experiment_id=entry.id):
        msg = f"ID {entry.id} already in log."
        raise KeyError(msg)
    _log.append(entry)
    _logger.info("Added entry for experiment: %s", entry.name)
    # and always save
    _save_log()


def remove_entry(experiment_id: str) -> bool:
    """Removes an entry from the log

    :param id: The id to remove
    :type id: str
    :return: True if able to remove from the log
    :rtype: bool
    """
    to_remove: Optional[ExperimentEntryModel] = None

    if not _log_loaded:
        _load_log(clear_existing=False)

    for entry in _log:
        if entry.id == experiment_id:
            to_remove = entry

    if to_remove is not None:
        _log.remove(to_remove)
        _logger.info("Removed project entry id: %s", id)
        _save_log()
        return True

    return False


# ----------------------------------------------------------------------
# Name generation and tracking
# ----------------------------------------------------------------------


# -------------------- prefix management -------------------------------
def register_prefix(prefix: str, start_major: int = 0, start_minor: int = 0) -> None:
    """Registers a prefix

    :param prefix: The prefix to register
    :type prefix: str
    :param start_major: the counter for the next major, defaults to 0
    :type start_major: int, optional
    :param start_minor: the counter for the next minor, defaults to 0
    :type start_minor: int, optional
    """
    global _prefix_entries

    # load from disk
    _load_prefix_file()

    if prefix in _prefix_entries.keys():
        msg = f"register_prefix failed. prefix= {prefix} already exists"
        _logger.warning(msg)
    else:
        _prefix_entries[prefix] = PrefixModel(
            prefix=prefix,
            major_counter=start_major,
            minor_counter=start_minor)

        # and save
        _save_prefix_file()


def retire_prefix(prefix: str) -> None:
    """Retires a prefix if it exists

    :param prefix: the prefix to remove
    :type prefix: str
    """
    global _prefix_entries

    # load from disk
    _load_prefix_file()

    if prefix in _prefix_entries.keys():
        del _prefix_entries[prefix]
        msg = f"Removing prefix: {prefix}"
        _logger.info(msg)

    # and save
    _save_prefix_file()


def get_prefix_list() -> list[str]:
    return list(_prefix_entries.keys())


def reset_prefix(prefix: str) -> None:
    global _prefix_entries
    _load_prefix_file()

    if prefix not in _prefix_entries.keys():
        register_prefix(prefix=prefix)

    entry = _prefix_entries[prefix]
    if not isinstance(entry, PrefixModel) and isinstance(entry, dict):
        try:
            entry = PrefixModel(**entry)
        except ValidationError:
            msg = "corrupted prefix_entries"
            _logger.error(msg)
            raise ValueError(msg)
    if isinstance(entry, PrefixModel):
        entry.major_counter = 0
        entry.minor_counter = 0
        _save_prefix_file()
        msg = f"Reset prefix {prefix}"
        _logger.info(msg)


# ------------------------ generation ----------------------------------
def generate_experiment_name(
    prefix: str = "exp",
    update_next: Literal["major", "minor"] = "minor",
) -> str:
    """Optional function to ease naming of experiments. If the prefix is
    not already registered it registers the prefix

    :param prefix: The prefix to use, defaults to "exp"
    :type prefix: str, optional
    :param update_next: major or minor version?, defaults to "minor"
    :type update_next: Literal["major", "minor"], optional
    :raises ValueError: Corrupt prefix_entry
    :raises RuntimeError: Failed to generate experiment name
    :return: The name as prefix.major.minor
    :rtype: str
    """
    global _prefix_entries
    _load_prefix_file()

    if prefix not in _prefix_entries.keys():
        register_prefix(prefix=prefix)

    entry = _prefix_entries[prefix]
    if not isinstance(entry, PrefixModel) and isinstance(entry, dict):
        try:
            entry = PrefixModel(**entry)
        except ValidationError:
            msg = "corrupted prefix_entries"
            _logger.error(msg)
            raise ValueError(msg)

    if isinstance(entry, PrefixModel):
        if update_next == "major":
            entry.major_counter += 1
            entry.minor_counter = 0
        else:
            entry.minor_counter += 1

        _save_prefix_file()  # save before returning
        return f"{prefix}.{entry.major_counter}.{entry.minor_counter}"

    msg = "failed to generate experiment name"
    _logger.error(msg)
    raise RuntimeError(msg)


def get_available_experiments() -> list[AvailableExperimentModel]:
    _refresh_using_blueprints()
    return copy.deepcopy(_available_experiments)


# ----------------------------------------------------------------------
# Tracking of runs
# ----------------------------------------------------------------------

def get_next_experiment_run_id(
    experiment_name: str,
    use_count: bool = True,
    prefix: Optional[str] = None,
    append_timestamp: bool = False
) -> str:
    """
    Generates a unique run identifier for an experiment execution.

    This function produces a run ID string for tracking individual runs
    of a given experiment. The format is influenced by options for using
    a count-based identifier or a random token, optionally prefixed
    and/or suffixed with a timestamp.

    :param experiment_name: Name of the experiment (used to locate the
        results folder if `use_count` is True).
    :type experiment_name: str
    :param use_count: If True, attempts to generate an integer-based run
        ID. If False, uses a secure random string instead.
    :type use_count: bool, optional
    :param prefix: Optional prefix to prepend to the run ID.
    :type prefix: Optional[str], optional
    :param append_timestamp: If True, appends the current timestamp to
        the run ID (format: YYYY-MM-DD_HH-MM-SS).
    :type append_timestamp: bool, optional
    :return: A string representing the next experiment run ID.
    :rtype: str
    """
    # we include the root experiment name as part of this string
    exp_name = experiment_name
    exp_root = os.path.join(EXP_RESULTS_FOLDER, experiment_name)

    if use_count:
        # we will inspect the results folder for the next entry
        if not os.path.exists(exp_root):
            msg = f"unable to inspect {exp_root} for next run_id"
            _logger.warning(msg)
            exp_name = "0." + experiment_name
        else:
            # count the folders
            prev_runs = os.listdir(exp_root)
            exp_name = str(len(prev_runs)) + "." + experiment_name
    else:
        # use random
        exp_name = secrets.token_hex(4) + experiment_name

    if prefix is not None:
        exp_name = f"{prefix}{exp_name}"

    if append_timestamp:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        exp_name += f".TS.{timestamp}"

    # confirm run_id is unique
    check_run_exists = os.path.join(exp_root, exp_name)
    if not os.path.exists(check_run_exists):
        return exp_name

    # and safety/fallback
    _logger.info(
        "run_id creation reverting to random due to run name collision")
    run_id = f"random.{secrets.token_hex(4)}"
    check_run_exists = os.path.join(exp_root, run_id)
    if not os.path.exists(check_run_exists):
        return run_id

    raise RuntimeError("Failed to create unique run_id")
