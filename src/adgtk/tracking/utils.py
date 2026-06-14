"""For ease of working with the results folder. This module provides
a class to manage the folder structure for an experiment.

Logging
=======
1. uses the same logger file as experiment.runner. adgtk.runner.log

Testing
=======
py -m pytest -s test/common/test_results.py

"""

import logging
import os
from adgtk import __version__ as adgtk_ver
from adgtk.utils.defaults import (
    EXP_DATASET_FOLDER,
    EXP_METRICS_FOLDER,
    EXP_IMG_FOLDER,
    EXP_MODEL_DIR,
    EXP_OTHER_DIR,
    EXP_RESULTS_FOLDER,
    EXP_MODEL_TRAIN_LOG,
    BATCH_DEF_DIR,
    EXP_DEF_DIR,
    LOG_DIR,
    SHARED_MODEL_DIR,
)
from adgtk.tracking.structure import ExperimentRunFolders

_logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------
DEBUG = False

CONCLUSION = "conclusions"

README_FILENAME = "README.md"

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _write_run_readme(
    root_dir: str,
    experiment_name: str,
    run_id: str
) -> None:
    """Writes a README.md to the run root folder describing each subfolder.

    Args:
        root_dir (str): The root directory of the run.
        experiment_name (str): The name of the experiment.
        run_id (str): The unique identifier for this run.
    """
    content = f"""# Experiment Run: {experiment_name} / {run_id}

This folder contains the outputs of a single experiment run.

## Folder Reference

| Folder | Purpose |
|--------|---------|
| `datasets/` | Input datasets and data files used during this run |
| `metrics/` | Evaluation results, scores, and performance metrics |
| `images/` | Plots, charts, and other visualizations |
| `models/` | Model artifacts (weights, checkpoints) saved during this run |
| `model_train_runs/` | Training logs and per-epoch checkpoints |
| `llm/` | LLM prompt/response logs and related outputs |
| `conclusions/` | Summaries, notes, and conclusions drawn from this run |
| `other/` | Miscellaneous files that do not belong in the above folders |

## Shared Folder

The `common/` folder lives one level up (next to the numbered run folders) and
holds resources shared across all runs of this experiment — for example,
pre-processed datasets or reference files that every run can read.

## ADGTK
These results were created with ADGTK version {adgtk_ver}.
"""
    readme_path = os.path.join(root_dir, README_FILENAME)
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(content)
    _logger.info("Wrote run README to %s", readme_path)


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------


def _build_run_dirs(root_dir: str, experiment_name) -> ExperimentRunFolders:
    """Constructs the folder structure for a specific experiment run.

    Args:
        root_dir (str): The root directory of the experiment run.
        experiment_name (str): The name of the experiment.

    Returns:
        ExperimentRunFolders: An object containing the paths to all
            subdirectories.
    """
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
        train_log_dir=os.path.join(root_dir, EXP_MODEL_TRAIN_LOG),
        llm_dir=os.path.join(root_dir, "llm"),
    )


def _get_run_dir(experiment_name: str, run_id: str, build: bool = True) -> str:
    """Determines the directory path for a specific experiment run.

    Args:
        experiment_name (str): The name of the experiment.
        run_id (str): The unique identifier for the run.
        build (bool): Whether to create the directories if they don't exist.

    Returns:
        str: The path to the run directory.
    """

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

    Args:
        exp_prefix (str): The prefix of the experiment names to collect.
        results_dir (str): The directory where results are stored.

    Returns:
        list: A list of results.

    Raises:
        NotImplementedError: This function requires an update.
    """
    raise NotImplementedError("collect_batch_results() requires an update")
    # experiments = os.listdir(results_dir)
    # results = []
    # for experiment in experiments:
    #     if experiment.startswith(exp_prefix):
    #         folder_manager = ExperimentFolderManager(experiment)
    #         results.append((experiment, folder_manager.collect_results()))
    # return results


def build_project_folders(base_path: str = ""):
    """Builds all the required folders for a project.

    Args:
        base_path (str): The root path of the project.
    """
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

    Args:
        experiment_name (str): The experiment name.
        run_id (str): The id of the individual run.

    Returns:
        ExperimentRunFolders: A model providing easy access to run paths.

    Raises:
        FileNotFoundError: If required folders are missing.
    """
    root_dir = _get_run_dir(
        experiment_name=experiment_name, run_id=run_id, build=False)

    exp_dir_listing = _build_run_dirs(
        root_dir=root_dir,
        experiment_name=experiment_name)
    folders = exp_dir_listing.to_dict()
    missing = False
    for key, dir in folders.items():
        if not os.path.exists(dir) and not key == "experiment_name":
            if key == "common":
                msg = f"missing folder: {dir}"
                _logger.info(msg)
                missing = True
    if missing:
        raise FileNotFoundError("Missing one or more folders. Check log.")
    return exp_dir_listing


def setup_run(experiment_name: str, run_id: str) -> ExperimentRunFolders:
    """Creates all the required folders for results of an experiment run

    Args:
        experiment_name (str): The name of the experiment.
        run_id (str): The unique identifier of a run of an experiment.

    Returns:
        ExperimentRunFolders: An object for referring to different folders.
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
        if key != "experiment_name":
            os.makedirs(folder, exist_ok=True)
    # build the readme for the tree folder structure here
    _write_run_readme(
        root_dir=root_dir,
        experiment_name=experiment_name,
        run_id=run_id)

    # now verify and create ExperimentRunFolders
    listing = build_folder_listing(
        experiment_name=experiment_name,
        run_id=run_id
    )
    _logger.info(f"Setup folders using schema version {listing.version}")
    return listing
