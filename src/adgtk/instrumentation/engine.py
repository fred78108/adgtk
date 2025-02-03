"""Provides an engine for driving measurements. The design pattern is to
be as modular as possible. The engine drives a set of measurements and
the measurements themselves as well as the filters, etc are all defined
by the user via the experiment and the factory. The engine should not
include any filtering or measuring within its code base.

The goal of this engine is to be as flexible as possible so no other
engine is needed. However, the framework architecutal approach remains
consistent in that this too can be swapped out by creation of another
type in the factory and use a scenario to invoke.


# TODO: Implement as part of the engine the STOP_WORD to Measurement!
"""


import logging
from typing import Union, List, Any
from adgtk.common import (
    ComponentDef,
    FactoryBlueprint,
    ArgumentSetting,
    FolderManager,
    ArgumentType)
from adgtk.tracking import MetricTracker
from adgtk.factory.component import ObjectFactory
from adgtk.journals import ExperimentJournal
from .base import SupportsMeasSetOps


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/instrumentation/test_engine.py


# ----------------------------------------------------------------------
# Module Constants
# ----------------------------------------------------------------------
DEBUG_TO_CONSOLE = False
LOW_DATA_THRESHOLD: Union[int, None] = None  # Set to None to disable


# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------


class MeasurementEngine:
    """Responsible for providing a wrapper around a group of measurement
    sets. It also exposes a measurement tracker for consumption of the
    measurement results. The overall design is lightweight, it invokes
    the measurement sets for interacting with their measurements."""

    description = "A measurement Engine is a collection of measurement sets."
    blueprint: FactoryBlueprint = {
        "group_label": "measurement-engine",
        "type_label": "simple",
        "introduction": """The Measurement Engine is a collection of measurement sets. The engine is responsible for invoking the measurements and storing the results. The engine is also responsible for exporting the results to a report. The engine is a lightweight wrapper around the measurement sets. You will need to configure the following:

        - The name of this engine
        - a measurement set (which is a collection of measurements)

note: The measurement Engine can have one or more measurement sets.""",
        "arguments": {
            "name": ArgumentSetting(
                help_str="the name of the measurement engine",
                default_value="main-engine",
                argument_type=ArgumentType.STRING),            
            "measurement_set_def": ArgumentSetting(
                help_str="A measurement set for this engine",
                argument_type=ArgumentType.LIST,
                group_label="measurement-set",
                list_intro="In order to create a measurement set, you will need to define the measurements. The measurements are the individual components that will be used to measure the data. The measurements are defined in the measurement set. The measurement set is a collection of measurements. You can have one or more measurement sets. This section will allow you to define the measurements for the measurement set.",
                list_min=1,
                list_arg_type=ArgumentType.BLUEPRINT,
                list_group_label="measurement-set")
        }
    }

    def __init__(
        self,
        factory: ObjectFactory,
        measurement_set_def: List[ComponentDef] | None = None,
        name: str = "default",
        journal: ExperimentJournal | None = None
    ):
        self.metric_tracker: Union[MetricTracker, None] = None
        self.name = name
        self._journal = journal
        self.factory = factory
        self._meas_sets: dict[str, SupportsMeasSetOps] = {}
        if measurement_set_def is None:
            measurement_set_def = []

        for meas_set_def in measurement_set_def:
            self.add_measurement_set(meas_set_def)

        if journal is not None:
            # tell the journal that the engine exists
            journal.register_meas_engine(self)
        else:
            logging.info("Measurement Engine created without a journal")

    def get_measurement_set_names(self) -> list:
        """Returns the names of the registered measurement sets. Usage
        includes for generating reports and needing to iterate the
        measurement tracker.

        :return: A list of the measurement set names
        :rtype: list
        """
        return list(self._meas_sets.keys())

    def add_measurement_set(self, meas_set_def: ComponentDef) -> None:
        """adds a new measurement set into the Engine. Used on init and
        if needed during experiment execution can be invoked to expand
        the data.

        :param meas_set_def: the measurement set to create and add
        :type meas_set_def: ComponentDef
        """
        meas_set: SupportsMeasSetOps
        meas_set = self.factory.create(meas_set_def)

        # update measurement_set engine name (reporting, exports, etc)
        meas_set.engine_name = self.name

        if meas_set.name in self._meas_sets:
            msg = "Attempted to insert a duplicate MeasurementSet "
            msg += f"{meas_set.name} into MeasurementEngine {self.name}"
            msg += ". Request ignored. No changes made."
            return None

        self._meas_sets[meas_set.name] = meas_set

    def remove_measurement_set(
        self,
        name: str,
        remove_data: bool = False
    ) -> None:
        """Removes a measurement set if one exists along

        :param name: The name of the measurement set to remove
        :type name: str
        :param remove_data: Also remove the tracking data,
            defaults to False
        :type remove_data: bool, optional
        """

        if name in self._meas_sets:
            _ = self._meas_sets.pop(name)

        if remove_data:
            raise NotImplementedError("Code more here!")

    def update_stopwords(self, stopwords: List[str]) -> None:
        """Iterates through all the different sets and updates stopwords
        as needed.

        :param stopwords: The stopwords used by measurements.
        :type stopwords: List[str]
        """
        for meas_set in self._meas_sets.values():
            meas_set.update_stopwords(stopwords)
            msg = f"Updated stopwords for {self.name}.{meas_set.name}"
            logging.info(msg)

    def update_metric_tracker(self, metric_tracker: MetricTracker):
        """Update the metric tracker"""
        self.metric_tracker = metric_tracker
        for meas_set in self._meas_sets.values():
            meas_set.register_metric_tracker(metric_tracker)

        # TODO: update journal(s)

    def perform_measurements(self, data: Any) -> None:
        """Executes the measurements currently active. All results are
        store in the measurement tracker.

        :param data: the data to measure
        :type data: Any
        """
        # ensure we have a metric tracker if one does not already exist
        if self.metric_tracker is None:
            metric_tracker = MetricTracker()
            self.update_metric_tracker(metric_tracker)

        meas_set: SupportsMeasSetOps
        for meas_set in self._meas_sets.values():
            meas_set.perform_measurements(data=data)

    def create_html_and_export(
        self,
        experiment_name: str,
        settings_file_override: Union[str, None] = None,
        header: int = 2,
        base_url: str = "http://127.0.0.1:8000"
    ) -> str:
        """Creates local files and returns HTML that can be used by the
        reports. In addition, exports data, builds images, etc in order
        to save and report.

        :param experiment_name: The experiment name.
        :type experiment_name: str
        :param settings_file_override: the filename of the settings file,
            defaults to None which will use the default file/path.
        :type str, optional
        :param header: The header, defaults to 1
        :type header: int, optional

        :return: HTML that can be used in a report.
        :rtype: str
        """

        html = f"""
        <div>
            <h{header}>Measurement Engine {self.name} </h{header}>
        """
        folders = FolderManager(
            name=experiment_name, settings_file_override=settings_file_override)

        meas_set: SupportsMeasSetOps
        for meas_set in self._meas_sets.values():
            # confirm/double check engine and override as needed
            meas_set.engine_name = self.name
            # now generate HTML
            html += meas_set.create_html_and_export(
                header=3, folders=folders, base_url=base_url)
        html += "</div>"
        return html
