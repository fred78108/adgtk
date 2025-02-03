
"""Used for tracking of measurement and other data points.
"""

import os
import logging
import copy
from typing import Union
import csv
import matplotlib.pyplot as plt
import toml
from adgtk.common import FolderManager
from adgtk.tracking import MetricTracker

# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/journals/test_metric_tracker.py


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
DEBUG_TO_CONSOLE = False


# ----------------------------------------------------------------------
# Presentation and transformation of data
# ----------------------------------------------------------------------


class MetricTrackingReporter:
    """Responsible for providing a presentation layer for the Metric
    Tracker."""

    def __init__(
        self,
        name: str,
        settings_file_override: Union[str, None] = None
    ):        
        self.name = name
        # no clear/reset. just get the structure
        self.folders = FolderManager(
            name=name, settings_file_override=settings_file_override)


    def __str__(self) -> str:
        to_string = f"MetricTrackingReporter for {self.name}\n"
        to_string += f"{self.folders}"
        return to_string

    def generate_csv_exports(
        self,
        metric_tracker: MetricTracker,
        engine_name: str,
        meas_set_name: str
    ) -> None:
        """_summary_Performs the processing of a measurement set

        :param metric_tracker: The tracker with the data
        :type metric_tracker: MetricTracker
        :param engine_name: The engine name for file naming
        :type engine_name: str
        :param meas_set_name: The set to process
        :type meas_set_name: str
        """

        metric_labels = metric_tracker.metric_labels()

        for metric in metric_labels:
            self._write_csv_and_metadata(
                metric=metric,
                metric_tracker=metric_tracker,
                engine_name=engine_name,
                meas_set_name=meas_set_name)

    def _write_csv_and_metadata(
        self,
        metric_tracker: MetricTracker,
        metric: str,
        engine_name: str,
        meas_set_name: str,
    ) -> None:
        """performs the file processing of a single metric

        :param metric_tracker: The tracker with the data
        :type metric_tracker: MetricTracker
        :param engine_name: The engine name for file naming
        :type engine_name: str        
        :param meas_set_name: The set name for file naming
        :type meas_set_name: str
        :param metric: The metric to export
        :type metric: str
        """

        file_prefix = f"{engine_name}.{meas_set_name}"
        # metadata first
        meta_file = os.path.join(
            self.folders.metrics_data,
            f"{file_prefix}.meta.toml")

        with open(meta_file, "w", encoding="utf-8") as meta_out:
            meta = metric_tracker.get_metadata(metric)
            toml.dump(meta, meta_out)

        # now CSV
        data_file = os.path.join(
            self.folders.metrics_data,
            f"{file_prefix}.{metric}.csv")
        with open(data_file, "w", encoding="utf-8") as data_out:
            writer = csv.writer(data_out)
            data = metric_tracker.get_all_data(metric)            
            writer.writerow(data)
