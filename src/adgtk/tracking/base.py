"""Internal tracking. Provides useful data structures.

TODO: Need to improve handling of raw. recall eda_3 and trying to use
the batch_ measurements
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
        name: str = "experiment",
        purpose: PurposeTypes = "other"
    ):
        """Initializes the MetricTracker.

        Args:
            name (str): The name of the tracker. Defaults to "experiment".
            purpose (PurposeTypes): The purpose of the tracked data.
                Defaults to "other".
        """
        self.name = name
        self.purpose: PurposeTypes = purpose
        self.metrics: dict[str, list] = {}
        self.metadata: dict[str, dict] = {}
        self.logger = get_scenario_logger()

    def register_metric(
        self,
        label: str,
        metadata: Union[dict, None] = None
    ) -> bool:
        """Registers a metric for tracking.

        Args:
            label (str): The label of the metric.
            metadata (Optional[dict]): Additional metadata for the metric.
                Defaults to None.

        Returns:
            bool: True if created, False if it already exists.
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
        """Adds raw data by iterating through values and adding each.

        Args:
            label (str): The label of the metric.
            values (Iterable): The data values to add.
        """
        for data in values:
            self.add_data(label=label, value=data)

    def add_data(self, label: str, value: Union[int, float]) -> None:
        """Adds a single data point to a metric.

        Args:
            label (str): The label of the metric.
            value (Union[int, float]): The value to add.
        """
        if label not in self.metrics:
            self.metrics[label] = []

        self.metrics[label].append(value)

        if DEBUG_TO_CONSOLE:
            print(f"MetricTracker adding {value} to {label}")
            print(f"Updated Metrics: {self.metrics[label]}")

    def metric_exists(self, label: str) -> bool:
        """Checks if a metric exists.

        Args:
            label (str): The label of the metric.

        Returns:
            bool: True if it exists, False otherwise.
        """
        if label not in self.metrics:
            return False

        return True

    def remove_metric(self, label: str) -> None:
        """Removes a metric and its metadata from being tracked.

        Args:
            label (str): The label of the metric to remove.
        """
        if label in self.metrics:
            del self.metrics[label]

        if label in self.metadata:
            del self.metadata[label]

    def metric_labels(self) -> list:
        """Gets a list of currently tracked metric labels.

        Returns:
            list: A list of metric labels.
        """
        return list(self.metrics.keys())

    def get_latest_value(self, label: str) -> float:
        """Gets the latest value recorded for a metric.

        Args:
            label (str): The label of the metric.

        Returns:
            float: The latest value, or 0 if no data is present.

        Raises:
            KeyError: If the metric label is not found.
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
        """Gets the latest distribution (array) recorded for a metric.

        Args:
            label (str): The label of the metric.

        Returns:
            np.ndarray: The latest distribution, or an empty array if
                no data.

        Raises:
            KeyError: If the metric label is not found.
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
        """Calculates the average of all stored values for a metric.

        Args:
            label (str): The label of the metric.

        Returns:
            float: The average value, or 0 if no data is present.

        Raises:
            KeyError: If the metric label is not found.
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
        """Calculates the sum of all stored values for a metric.

        Args:
            label (str): The label of the metric.

        Returns:
            float: The sum of values, or 0 if no data is present.

        Raises:
            KeyError: If the metric label is not found.
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
        """Clears all values for a specific metric.

        Args:
            label (str): The label of the metric to clear.
        """
        self.metrics[label] = []

    def clear_results(self) -> None:
        """Clears measurement results for all tracked metrics."""
        for key in self.metrics.keys():
            self.metrics[key] = []

    def reset(self) -> None:
        """Deletes all metrics and metadata, resetting the tracker."""
        self.metrics = {}

    def measurement_count(self, label: str) -> int:
        """Returns the count of observations for a metric.

        Args:
            label (str): The label of the metric.

        Returns:
            int: The count of all entries for the metric.

        Raises:
            KeyError: If the metric label is not found.
        """
        if label not in self.metrics:
            raise KeyError("Invalid metric")

        return len(self.metrics[label])

    def get_all_data(self, label: str) -> list:
        """Retrieves a copy of all data points for a metric.

        Args:
            label (str): The label of the metric.

        Returns:
            list: A list containing all data points.

        Raises:
            KeyError: If the metric label is not found.
        """
        if self.metric_exists(label):
            return copy.deepcopy(self.metrics[label])

        msg = f"Requested invalid label: {label}"
        self.logger.error(msg)
        raise KeyError("Invalid metric")

    def get_metadata(self, label: str) -> dict:
        """Retrieves a copy of the metadata for a metric.

        Args:
            label (str): The label of the metric.

        Returns:
            dict: A dictionary containing the metadata.
        """
        if label in self.metadata:
            return copy.deepcopy(self.metadata[label])

        msg = f"Requested invalid metadata for label: {label}"
        self.logger.error(msg)
        return {}

    def save_data(self, folders: ExperimentRunFolders) -> None:
        """Saves the metric data to disk.

        Args:
            folders (ExperimentRunFolders): The experiment result folders.
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
        """Exports the latest recorded value for each metric to a dict.

        Returns:
            dict: A mapping of metric labels to their latest values.
        """
        # prepare data
        labels = self.metric_labels()
        out_data = {}
        for label in labels:
            out_data[label] = self.get_latest_value(label)
        return out_data
