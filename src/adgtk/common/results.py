"""For ease of working with the results folder
"""

import logging
import os
import shutil
from typing import Union
from adgtk.utils import load_settings

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/common/test_results.py

# ----------------------------------------------------------------------
# CONSTANTS
# ----------------------------------------------------------------------
METRICS_FOLDER = "metrics"
METRICS_IMG_FOLDER = "images"
METRICS_DATA_FOLDER = "data"
DATASET_FOLDER = "datasets"
AGENT_FOLDER = "agent"
PERFORMANCE_FOLDER = "performance"

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------


class FolderManager:
    """A simple class to help manage and ensure a consistent folder
    structure for an experiment results."""

    def __init__(
        self,
        name: str,
        settings_file_override: Union[str, None] = None,
        clear_and_rebuild: bool = False
    ):
        """Initialize and create if needed

        :param name: the experiment name
        :type name: str
        :param clear_and_rebuild: deletes all results, defaults to False
        :type clear_and_rebuild: bool
        :param settings_file_override: redirect settings file location,
            defaults to None
        :type settings_file_override: Union[str, None], optional
        :raises FileNotFoundError: Unable to load the settings file
        """

        # cleanup to ensure consistency
        name = name.lower()
        if name.endswith(".toml") or name.endswith(".yaml"):
            name = name[:-5]

        # now load the settings and set the items to manage
        try:
            settings = load_settings(file_override=settings_file_override)
        except FileNotFoundError as e:
            if settings_file_override is not None:
                msg = f"Unable to locate settings file {settings_file_override}"
            else:
                msg = "Unable to locate settings file from default location"
            logging.error(msg)
            raise FileNotFoundError(msg) from e

        exp_result_dir = os.path.join(settings.experiment["results_dir"], name)
        self.base_folder = exp_result_dir

        if os.path.exists(exp_result_dir) and clear_and_rebuild:
            shutil.rmtree(exp_result_dir)

        if not os.path.exists(exp_result_dir):
            os.makedirs(exp_result_dir, exist_ok=True)
            logging.info(f"Created {exp_result_dir}")
        else:
            msg = f"Folder Manager found {exp_result_dir}. No action taken "\
                  "to create additional folders"
            logging.info(msg)

        # Agent data
        self.agent = os.path.join(exp_result_dir, AGENT_FOLDER)
        os.makedirs(self.agent, exist_ok=True)

        # Create metrics sub-folder(s)
        self.metrics = os.path.join(exp_result_dir, METRICS_FOLDER)
        self.metrics_data = os.path.join(
            self.metrics, METRICS_DATA_FOLDER)
        self.metrics_img = os.path.join(self.metrics, METRICS_IMG_FOLDER)

        os.makedirs(self.metrics, exist_ok=True)
        os.makedirs(self.metrics_data, exist_ok=True)
        os.makedirs(self.metrics_img, exist_ok=True)

        # create dataset folder
        self.dataset = os.path.join(exp_result_dir, DATASET_FOLDER)
        os.makedirs(self.dataset, exist_ok=True)

        # Performance
        self.performance = os.path.join(exp_result_dir, PERFORMANCE_FOLDER)
        os.makedirs(self.performance, exist_ok=True)

        # and additional/existing files/folders
        self.logfile = os.path.join(settings.logging["log_dir"], f"{name}.log")
        self.data_dir = settings.experiment["data_dir"]
        self.tensorboard_dir = settings.experiment["tensorboard_dir"]
        self.blueprint_dir = settings.blueprint_dir

    def __str__(self) -> str:
        to_string = "FolderManager\n"
        to_string += "-------------\n"
        to_string += f" - log: {self.logfile}\n"
        to_string += f" - tensorboard: {self.tensorboard_dir}\n"
        to_string += f" - metrics: {self.metrics}\n"
        to_string += f"    - data: {self.metrics_data}\n"
        to_string += f"    - images: {self.metrics_img}\n"
        to_string += f" - dataset: {self.dataset}\n"

        return to_string
