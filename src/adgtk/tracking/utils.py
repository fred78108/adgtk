"""For ease of working with the results folder. This module provides
a class to manage the folder structure for an experiment.

Logging
=======
1. uses the same logger file as experiment.runner. adgtk.runner.log

Testing
=======
py -m pytest -s test/common/test_results.py

"""

# setup logfile for this and sub-modules
from adgtk.tracking.structure import (
    EXP_DATASET_FOLDER,
    EXP_METRICS_FOLDER,
    EXP_IMG_FOLDER,
    EXP_MODEL_DIR,
    EXP_OTHER_DIR,
    EXP_RESULTS_FOLDER,
    EXP_MODEL_TRAIN_LOG,
    ExperimentRunFolders
)
from adgtk.common.defaults import (
    BATCH_DEF_DIR,
    EXP_DEF_DIR,
    LOG_DIR,
    SHARED_MODEL_DIR)
import os
from adgtk.utils import create_logger

# Set up module-specific logger
_logger = create_logger(
    "adgtk.runner.log",
    logger_name=__name__,
    subdir="framework"
)


# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------
DEBUG = False

CONCLUSION = "conclusions"

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _build_run_dirs(root_dir: str, experiment_name) -> ExperimentRunFolders:
    _logger.info("Building run folders at %s", root_dir)
    
    return ExperimentRunFolders(
        datasets=os.path.join(root_dir, EXP_DATASET_FOLDER),
        metrics=os.path.join(root_dir, EXP_METRICS_FOLDER),
        images=os.path.join(root_dir, EXP_IMG_FOLDER),
        other=os.path.join(root_dir, EXP_OTHER_DIR),
        conclusion=os.path.join(root_dir, CONCLUSION),
        root_dir=root_dir,
        log_dir=os.path.join("logs", "runs", experiment_name),
        experiment_name=experiment_name,
        common=os.path.join(EXP_RESULTS_FOLDER, experiment_name, "common"),
        model_dir=os.path.join(root_dir, EXP_MODEL_DIR),
        train_log_dir=os.path.join(root_dir, EXP_MODEL_TRAIN_LOG)
    )


def _get_run_dir(experiment_name: str, run_id: str, build: bool = True) -> str:

    # Experiment
    exp_folder = os.path.join(EXP_RESULTS_FOLDER, experiment_name)
    # RUN
    run_dir = os.path.join(exp_folder, run_id)
    common_dir = os.path.join(exp_folder, "common")
    if build:
        os.makedirs(EXP_RESULTS_FOLDER, exist_ok=True)
        os.makedirs(exp_folder, exist_ok=True)
        os.makedirs(run_dir, exist_ok=True)
        os.makedirs(common_dir, exist_ok=True)
    return run_dir
# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------

# TODO: Broken


def collect_batch_results(exp_prefix: str, results_dir: str) -> list:
    """Retrieves the results and the configuration of an experiment and
    puts it into a dictionary for processing.

    :param experiment_name: The name of the experiment
    :type experiment_name: str
    :return: a tuple of filename and a dict that contains results
    :rtype: dict
    """
    raise NotImplementedError("collect_batch_results() requires an update")
    experiments = os.listdir(results_dir)
    results = []
    # for experiment in experiments:
    #     if experiment.startswith(exp_prefix):
    #         folder_manager = ExperimentFolderManager(experiment)
    #         results.append((experiment, folder_manager.collect_results()))

    return results


def build_project_folders(base_path: str = ""):
    """Builds all the required folders for a project."""
    def make_dir(path):
        full_path = os.path.join(base_path, path) if base_path else path
        os.makedirs(full_path, exist_ok=True)
        _logger.info(f"Created folder: {full_path}")
    make_dir(BATCH_DEF_DIR)
    make_dir(EXP_DEF_DIR)
    make_dir(SHARED_MODEL_DIR)
    make_dir(LOG_DIR)
    make_dir(EXP_RESULTS_FOLDER)


def build_folder_listing(
    experiment_name: str,
    run_id: str
) -> ExperimentRunFolders:
    """Verifies the folders exist and returns an easy to use object for
    use within different code bases.

    :param experiment_name: The experiment name
    :type experiment_name: str
    :param run_id: The id of the individual run
    :type run_id: str
    :return: a Pydantic Model that provides ease of use
    :rtype: ExperimentRunFolders
    """
    root_dir = _get_run_dir(
        experiment_name=experiment_name, run_id=run_id, build=False)
    
    exp_dir_listing = _build_run_dirs(
        root_dir=root_dir,
        experiment_name=experiment_name)
    folders = exp_dir_listing.to_dict()
    missing = False
    for key, dir in folders.items():
        if not os.path.exists(dir) and not key == "experiment_name" \
            and key == "common":
            msg = f"missing folder: {dir}"
            _logger.info(msg)
            missing = True

    if missing:
        raise FileNotFoundError("Missing one or more folders. Check log.")
    return exp_dir_listing


def setup_run(experiment_name: str, run_id: str) -> ExperimentRunFolders:
    """Creates all the required folders for results of an experiment run

    :param experiment_name: The name of the experiment
    :type experiment_name: str
    :param run_id: The unique idenfier of a run of an experiment
    :type run_id: str
    :return: An easy to use object for referring to different folders
        for the run such as the datasets folder.
    :rtype: ExperimentRunFolders
    """
    # ensure results folder exists
    root_dir = _get_run_dir(
        experiment_name=experiment_name, run_id=run_id, build=True)

    exp_dir_listing = _build_run_dirs(
        root_dir=root_dir,
        experiment_name=experiment_name)
    folders = exp_dir_listing.to_dict()
    # Builds the subfolders, etc.
    for key, folder in folders.items():
        if key != "experiment_name" :
            os.makedirs(folder, exist_ok=True)

    # now verify and create ExperimentRunFolders
    listing = build_folder_listing(
        experiment_name=experiment_name,
        run_id=run_id
    )
    _logger.info(f"Setup folders using schema version {listing.version}")
    return listing
