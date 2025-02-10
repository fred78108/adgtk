"""Tracks various performance statistics and writes to disk"""

import os
from typing import Union, Any
import pandas as pd
from adgtk.common import FolderManager
from .base import MetricTracker


class PerformanceTracker():
    """Used to track and report on running performance. Examples include
    success rate, average time to complete a task, etc. The design is to
    be as flexible as possible to support any future user needs."""

    def __init__(self, experiment_name:str, component:str, last_only:bool=True):
        """Create a new PerformanceTracker object

        :param experiment_name: The name of the experiment
        :type experiment_name: str
        :param component: The name of the component recording the data
        :type component: str
        :param last_only: return only the last value, defaults to True
        :type last_only: bool, optional
        """
        super().__init__()
        self.last_only = last_only
        self.metric_tracker = MetricTracker()
        folders = FolderManager(experiment_name)
        self.filename = os.path.join(folders.performance, f"{component}.csv")


    def register_statistic(self, label:str):
        """_summary_

        :param label: The label for the statistic
        :type label: str
        """
        self.metric_tracker.register_metric(label=label)

    def add_data(self, label:str, value:float|int):
        """Add data to the performance tracker for a given label

        :param label: the label for the statistic
        :type label: str
        :param value: The value to record
        :type value: float | int
        """
        self.metric_tracker.add_data(label=label, value=value)
        
    def save_data(self):
        """Saves the data to disk using the pre-defined folder structure
        """
        labels = self.metric_tracker.metric_labels()
        out_data = {}
        for label in labels:
            if self.last_only:
                value = self.metric_tracker.get_latest_value(label)
                data = [value]
            else:
                data = self.metric_tracker.get_all_data(label)                

            # now set the data
            out_data[label] = data

        df = pd.DataFrame(out_data)
        df.to_csv(self.filename)