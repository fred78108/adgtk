"""Tracks various performance statistics and writes to disk"""

import logging
import os
import csv
from typing import Union, Any
from adgtk.common import FolderManager
from adgtk.journals import ExperimentJournal
from .base import MetricTracker


class PerformanceTracker():
    """Used to track and report on running performance. Examples include
    success rate, average time to complete a task, etc. The design is to
    be as flexible as possible to support any future user needs.
    """


    def __init__(
        self,
        experiment_name:str,
        component:str,
        last_only:bool=True,
        journal: Union[ExperimentJournal, None] = None
    ):
        """Create a new PerformanceTracker object.

        :param experiment_name: The name of the experiment
        :type experiment_name: str
        :param component: The name of the component recording the data
        :type component: str
        :param journal: The experiment journal. defaults to None
        :type journal: ExperimentJournal
        :param last_only: return only the last value, defaults to True
        :type last_only: bool, optional      
        """
        
        
        super().__init__()
        self.last_only = last_only
        self.metric_tracker = MetricTracker()
        self.folders = FolderManager(experiment_name)
        self.component = component
        self.journal =journal

    def register_statistic(self, label:str):
        """Registers a statistic. Enables tracking of values using this
        label. This allows for fetch by the label as well as the ability
        to save this data by label to disk.

        :param label: The label for the statistic
        :type label: str
        """
        self.metric_tracker.register_metric(label=label)

    def add_data(self, label:str, value:float|int):
        """Add data to the performance tracker for a given label. If the
        label is not found the method will attempt to register the label
        then add the data.

        :param label: the label for the statistic
        :type label: str
        :param value: The value to record
        :type value: float | int
        """
        try:
            self.metric_tracker.add_data(label=label, value=value)
        except KeyError:
            # likely tried to add data to an unregistered label.
            # One last try. let raise occur if happens again.
            self.metric_tracker.register_metric(label=label)
            self.metric_tracker.add_data(label=label, value=value)

        
    def save_data(self):
        """Saves the data to disk using the pre-defined folder structure
        """
        # prepare data
        labels = self.metric_tracker.metric_labels()
        out_data = {}
        for label in labels:
            # always save all data
            data = self.metric_tracker.get_all_data(label)                
            # now set the data, if exists
            if len(data) > 0:
                out_data[label] = data
            else:
                msg = f"{self.component} metric tracker had no data recorded "\
                      f"for {label}"
                logging.warning(msg)                
                out_data[label] = []

        # write to disk        
        for key, data in out_data.items():
            filename = os.path.join(
                        self.folders.performance,
                        f"{self.component}.{key}.csv")

            with open(filename, "w", newline="") as outfile:
                writer = csv.writer(outfile)
                writer.writerow(data)

                if self.journal is not None:
                    # Log the write to the report
                    self.journal.log_data_write(
                        description=f"{self.component}.{key} metric data",
                        file_w_path=filename,
                        component=f"{self.component}.{key}",
                        entry_type="metrics")
