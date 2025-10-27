"""Internal tracking. Provides useful data structures.
"""

import copy
import csv
import os
from typing import Iterable, Union
import numpy as np
from adgtk.data.structure import PurposeTypes
import adgtk.tracking.journal as exp_journal
from adgtk.utils import get_scenario_logger
from .structure import ExperimentRunFolders
# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
DEBUG_TO_CONSOLE = False

# ----------------------------------------------------------------------
# Tracking of data
# ----------------------------------------------------------------------

class MetricTracker():
    """Used for tracking metrics."""

    def __init__(
        self,
        name:str="experiment",
        purpose:PurposeTypes="other"
    ):
        self.name = name    # for saving to disk
        self.purpose: PurposeTypes = purpose
        self.metrics: dict[str, list] = {}
        self.metadata: dict[str, dict] = {}
        self.logger = get_scenario_logger()

    def register_metric(
        self,
        label: str,
        metadata: Union[dict, None] = None
    ) -> bool:
        """Registers a metric.

        :param label: The label of the metric
        :type label: str
        :param metadata: _description_
        :type metadata: Union[dict, None]
        :return: T: created, F: did not create
        :rtype: bool
        """

        if metadata is not None:
            if label not in self.metadata:
                self.metadata[label] = metadata
        else:
            if label not in self.metadata:
                self.metadata[label] = {}

        if label not in self.metrics:
            self.metrics[label] = []
            return True
        return False

    def add_raw_data(self, label: str, values: Iterable) -> None:
        """Adds data as-is by iterating through and adding one by one.

        :param label: The label of the metric
        :type label: str
        :param values: the data to add
        :type values: Iterable
        """
        for data in values:
            self.add_data(label=label, value=data)

    def add_data(self, label: str, value: Union[int, float]) -> None:
        """Adds data

        :param label: The label of the metric
        :type label: str
        :raises KeyError: Label is not found
        :param value: the data to add
        :type Union[int, float]
        """
        if label not in self.metrics:
            self.metrics[label] = []

        self.metrics[label].append(value)

        if DEBUG_TO_CONSOLE:
            print(f"MetricTracker adding {value} to {label}")
            print(f"Updated Metrics: {self.metrics[label]}")

    def metric_exists(self, label: str) -> bool:
        """Does a metric exist?

        :param label: The label of the metric
        :type label: str
        :return: T: exists, F: does not
        :rtype: bool
        """
        if label not in self.metrics:
            return False

        return True

    def remove_metric(self, label: str) -> None:
        """Removes a metric from being tracked

        :param label: The label of the metric to remove
        :type label: str
        """
        if label in self.metrics:
            del self.metrics[label]

        if label in self.metadata:
            del self.metadata[label]

    def metric_labels(self) -> list:
        """Gets a list of metrics currently tracking

        :return: a list of the labels
        :rtype: list
        """
        return list(self.metrics.keys())

    def get_latest_value(self, label: str) -> float:
        """Gets the latest value from a label

        :param label: The label of the metric to get latest value
        :type label: str
        :raises KeyError: Invalid Metric
        :return: the latest value
        :rtype: float
        """
        if label not in self.metrics:
            msg = f"Requested invalid label: {label}"
            self.logger.error(msg)
            raise KeyError("Invalid metric")
        elif len(self.metrics[label]) == 0:
            return 0
        else:
            return self.metrics[label][-1]
        
    def get_latest_distribution(self, label: str) -> np.ndarray:
        """Gets the latest distribution from a label

        :param label: The label of the metric to get latest value
        :type label: str
        :raises KeyError: Invalid Metric
        :return: the latest value
        :rtype: np.ndarray
        """
        if label not in self.metrics:
            msg = f"Requested invalid label: {label}"
            self.logger.error(msg)
            raise KeyError("Invalid metric")
        elif len(self.metrics[label]) == 0:
            return np.ndarray([])
        else:
            return self.metrics[label][-1]

    def get_average(self, label: str) -> float:
        """Returns the average of all stored values for the label

        :param label: The label of the metric to get avg of
        :type label: str
        :raises KeyError: Invalid Metric
        :return: the average value
        :rtype: float
        """
        if label not in self.metrics:
            msg = f"Requested invalid label: {label}" 
            if DEBUG_TO_CONSOLE:
                print(f"METRIC_TRACKER_DATA: {self.metrics}")
                print(msg)
            self.logger.error(msg)
            raise KeyError("Invalid metric")
        elif len(self.metrics[label]) == 0:
            return 0
        else:
            return sum(self.metrics[label]) / len(self.metrics[label])

    def get_sum(self, label: str) -> float:
        """Returns the sum of all stored values for the label

        :param label: The label of the metric to get sum of
        :type label: str
        :raises KeyError: Invalid Metric
        :return: the sum of all stored values
        :rtype: float
        """
        if label not in self.metrics:
            msg = f"Requested invalid label: {label}"
            self.logger.error(msg)
            raise KeyError("Invalid metric")
        elif len(self.metrics[label]) == 0:
            return 0
        else:
            return sum(self.metrics[label])

    def clear_metric(self, label: str) -> None:
        """Clears the values of a  metric

        :param label: The label of the metric to clear data from
        :type label: str
        """
        self.metrics[label] = []

    def clear_results(self) -> None:
        """Clears all prior measurement results
        """
        for key in self.metrics.keys():
            self.metrics[key] = []

    def reset(self) -> None:
        """Deletes all data and labels and resets to no metrics tracked.
        """
        self.metrics = {}

    def measurement_count(self, label: str) -> int:
        """Returns the count of observations for a metric


        :param label: The label of the metric to get count of
        :type label: str
        :raises KeyError: Invalid Metric
        :return: the count of all entries
        :rtype: int
        """
        if label not in self.metrics:
            raise KeyError("Invalid metric")

        return len(self.metrics[label])

    def get_all_data(self, label: str) -> list:
        """Gets all data for a metric.

        :param label: The label of the metric to get data from
        :type label: str
        :raises KeyError: Invalid Metric
        :return: the data as a list
        :rtype: list
        """
        if self.metric_exists(label):
            return copy.deepcopy(self.metrics[label])

        msg = f"Requested invalid label: {label}"
        self.logger.error(msg)
        raise KeyError("Invalid metric")

    def get_metadata(self, label: str) -> dict:
        if label in self.metadata:
            return copy.deepcopy(self.metadata[label])

        msg = f"Requested invalid metadata for label: {label}"
        self.logger.error(msg)
        return {}

    def save_data(self, folders: ExperimentRunFolders) -> None:
        """Saves the data to disk using the pre-defined folder structure

        Args:
            folders (ExperimentRunFolders): The results folders
        """
        # prepare data
        labels = self.metric_labels()
        out_data = {}
        for label in labels:
            # always save all data
            data = self.get_all_data(label)                
            # now set the data, if exists
            if len(data) > 0:
                out_data[label] = data
            else:
                msg = f"{self.name} metric tracker had no data recorded "\
                      f"for {label}"
                self.logger.warning(msg)                
                out_data[label] = []

        # write to disk        
        for key, data in out_data.items():
            filename = os.path.join(
                        folders.metrics,
                        f"{self.name}.{key}.csv")

            with open(filename, "w", newline="") as outfile:
                writer = csv.writer(outfile)
                writer.writerow(data)

            self.logger.info(
                f"Saved {self.name}.{key} metric data to {filename}")

            exp_journal.add_file(filename=filename, purpose=self.purpose)

    def export_last_val_to_dict(self) -> dict:
        """Obtains the latest measurement as a dictionary.

        Returns:
            dict: the last value recorded by metric label
        """        
        # prepare data
        labels = self.metric_labels()
        out_data = {}        
        for label in labels:
            out_data[label] = self.get_latest_value(label)
        return out_data
