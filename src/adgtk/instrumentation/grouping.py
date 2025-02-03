"""Measurement set is doing the heavy lifting of organization of
measurements. This module supports this set operations.
"""


import logging
import os
import csv
from urllib.parse import urljoin
import toml
from typing import (
    Union,
    List,
    Literal,
    Any,
    Sequence)
from adgtk.common import (
    ComponentDef,
    FactoryBlueprint,
    ArgumentSetting,
    FolderManager,
    InsufficientData,
    ArgumentType)
from adgtk.tracking import MetricTracker
from adgtk.factory.component import ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.components.data import SupportsFiltering
from adgtk.utils.records import convert_record_as, process_as
from .base import (
    MeasInputType,
    Measurement,
    RecordAs,
    SupportsStopwords,
    Comparison,
    InvalidMeasurementConfiguration)


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/instrumentation/test_meas_set.py


# ----------------------------------------------------------------------
# Module Constants
# ----------------------------------------------------------------------
DEBUG_TO_CONSOLE = False
LOW_DATA_THRESHOLD: Union[int, None] = None  # Set to None to disable


# ----------------------------------------------------------------------
# MeasurementSet
# ----------------------------------------------------------------------


class MeasurementSet:
    """Provides a protocol for a pre-defined grouping of measurements
    """
    description = "A measurement set which is a group of measurements."
    blueprint: FactoryBlueprint = {
        "group_label": "measurement-set",
        "type_label": "basic-set",
        "arguments": {
            "name": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                default_value="main",
                help_str="The name of the measurement-set"),            
            "expected_result": ArgumentSetting(
                help_str="The result type. valid options are: number, list, string",
                default_value="number",
                argument_type=ArgumentType.STRING),
            "record_as": ArgumentSetting(
                help_str="The results should be saved as an avg, sum, latest, or raw",
                default_value="avg",
                argument_type=ArgumentType.STRING),
            "measurement_type": ArgumentSetting(
                help_str="The measurement type",
                default_value="single",
                argument_type=ArgumentType.STRING),
            "measurement_def": ArgumentSetting(
                argument_type=ArgumentType.LIST,
                help_str="A measurement that are part of this set",
                list_intro="This section will allow you to define the measurements for the measurement set.",
                list_min=1,
                list_arg_type=ArgumentType.BLUEPRINT,
                list_group_label="measurement"),
                        
            # TODO: Future release. Roadmap item.
            # "filters": ArgumentSetting(
            #     help_str="Filters for measuring 'placeholder only. hit enter.'",
            #     argument_type=ArgumentType.LIST,
            #     list_arg_type=ArgumentType.STRING),
        }
    }

    def __init__(
        self,
        factory: ObjectFactory,
        journal: ExperimentJournal,
        name: str,
        measurement_def: Union[List[ComponentDef], None],
        expected_result: Literal["number", "list", "string"],
        record_as: Literal["sum", "avg", "latest", "raw"],
        measurement_type: Literal["single", "compare", "dataset"],
        # filters: List[SupportsFiltering],
        create_metric_tracker: bool = True,        
        engine_name: str = "main"
    ) -> None:
        """MeasurementSet ensures that the engine can properly
        interact with the individual measurements.
        :param factory: The object factory
        :type factory: ObjectFactory
        :param journal: The Experiment journal
        :type journal: ExperimentJournal
        :param name: The unique name of the measurement set
        :type name: str
        :param measurement_type: The type of measurement
        :type measurement_type: Literal[&quot;single&quot;, &quot;compare&quot;, &quot;dataset&quot;]
        :param director_override_blueprint: The director used for determing whether to run a measurement against a data type.
        :type director_override_blueprint: Union[dict, None]
        :param expected_result: The type of result expected from the measurement. Used to further filter measurements to run.
        :type expected_result: Literal[&quot;float&quot;, &quot;list&quot;, &quot;string&quot;, &quot;int&quot;]
        :param record_as: How should they be presented as output?
        :type record_as: Literal[&quot;sum&quot;, &quot;avg&quot;, &quot;latest&quot;]
        :param measure_only: Provides filtering of data type
        :type measure_only: Union[List[Union[str, None]], None]
        :param filters: A filter of the data, defaults to None
        :type filters: Union[ List[Union[SupportsFiltering, Callable, None]], None], optional
        :param measurement_def: The measurements to perform,
            defaults to None
        :type measurement_def: Union[ List[dict], None], optional
        :param engine_name: The engine it supports, optional, defaults to main
        :type engine_name: str

        """
        self.name = name
        self.engine_name = engine_name
        self._journal = journal
        self.measurement_type = measurement_type  # lets the user update
        self.expected_result = expected_result  # lets the user update

        # convert and setup record_as
        try:
            self.record_as: RecordAs = convert_record_as(record_as)
        except InvalidMeasurementConfiguration as e:
            msg = f"meas-set: {name} has invalid record_as: {record_as}"
            logging.error(msg)
            raise InvalidMeasurementConfiguration(msg) from e

        # TODO: Roadmap
        # self.filters: List[SupportsFiltering] = []
        # if filters is not None:
        #     for candidate in filters:
        #         if isinstance(candidate, SupportsFiltering):
        #             self.filters.append(candidate)

        self.execution_count = 0

        # create measurements
        self._measurements: List[
            Comparison | Measurement] = []
        if measurement_def is not None:
            for meas_def in measurement_def:
                self._measurements.append(factory.create(meas_def))

        # and track. Set to create a metric tracker or expect to be
        # set post init for using a shared metric tracker?
        self.metric_tracker: Union[MetricTracker, None] = None
        self._metric_tracker_labels_created = False
        if create_metric_tracker:
            # create a metric tracker specific to this meas set
            self.metric_tracker = MetricTracker()
            self._init_metrics_into_metric_tracker()

    def _create_html_link(
        self,
        description: str,
        file_w_path: str,
        base_url: str = "http://127.0.0.1:8000"
    ) -> str:
        url_str = urljoin(
            base=base_url,
            url=file_w_path)
        return f"<a href={url_str}>{description}</a>"

    def _write_csv_and_metadata(
        self, metric: str,
        folders: FolderManager,
        base_url: str = "http://127.0.0.1:8000"
    ) -> str:
        """Performs the file processing of a single metric

        :param metric: The metric to export
        :type metric: str
        :param folders: The folders to save to local disk
        :type folders: FolderManager

        :return: HTML that can be used in a report.
        :rtype: str
        """
        html = ""
        file_prefix = f"{self.engine_name}.{self.name}"
        # metadata first
        meta_file = os.path.join(
            folders.metrics_data,
            f"{file_prefix}.meta.toml")

        # first metadata
        if self.metric_tracker is not None:
            meta = self.metric_tracker.get_metadata(metric)
            if len(meta) > 0:
                html += "<ul><li> Metadata "
                html += self._create_html_link(
                    description=meta_file,
                    file_w_path=meta_file,
                    base_url=base_url)

                html += "</li>"
                with open(meta_file, "w", encoding="utf-8") as meta_out:
                    if self.metric_tracker is not None:
                        toml.dump(meta, meta_out)

        # now data -> CSV
        if self.metric_tracker is not None:
            data = self.metric_tracker.get_all_data(metric)
            if len(data) > 0:
                html += "<li> Data file "
                data_file = os.path.join(
                    folders.metrics_data,
                    f"{file_prefix}.{metric}.csv")
                html += self._create_html_link(
                    description=data_file,
                    file_w_path=data_file,
                    base_url=base_url)
                html += "</li><ul>"

                with open(data_file, "w", encoding="utf-8") as data_out:
                    writer = csv.writer(data_out)
                    writer.writerow(data)

            elif self.metric_tracker is not None:
                logging.info(
                    f"Metric {metric} had zero data in set {self.name}")
        else:
            html += "<li> No Metric tracker found </li>"

        return html

    def create_html_and_export(
        self,
        folders: FolderManager,
        header: int = 2,
        base_url: str = "http://127.0.0.1:8000"
    ) -> str:
        """Creates local files and returns HTML that can be used by the
        reports. In addition, exports data, builds images, etc in order
        to save and report.

        :param folders: The folders to save to local disk
        :type folders: FolderManager
        :param header: The header, defaults to 2
        :type header: int, optional

        :return: HTML that can be used in a report.
        :rtype: str
        """

        # metadata & data
        if self.metric_tracker is None:
            return ""

        html = f"""
        <div>
            <h{header}>Measurement set {self.name}</h{header}>
        """

        meas_header = header+1

        for meas in self._measurements:
            # intro
            html += meas.report(header=meas_header)
            # image
            f_prefix = f"{self.engine_name}.{self.name}.{meas.tracker_label}"
            try:
                img_file = self.metric_tracker.line_plot(
                    label=meas.tracker_label,
                    folder=folders.metrics_img,
                    file_prefix=f_prefix)

                url_str = urljoin(
                    base=base_url,
                    url=img_file)

                html += f'<img src="{url_str}" alt="{meas.tracker_label}">'
            except InsufficientData:
                # NO-OP. unable to plot so not adding HTML for the IMG.
                pass

            # data
            html += self._write_csv_and_metadata(
                metric=meas.tracker_label,
                folders=folders,
                base_url=base_url)

        html += f"</div>"
        return html

    def register_metric_tracker(self, metric_tracker: MetricTracker) -> None:
        """Registers metric labels into a metric_tracker.

        :param metric_tracker: The metric tracker to register to
        :type metric_tracker: MetricTracker
        """
        self.metric_tracker = metric_tracker
        self._init_metrics_into_metric_tracker()

    def _init_metrics_into_metric_tracker(self) -> None:
        """Supports a first load of a set of metrics into the metric
        tracker. Used on init when create_metric_tracker is True or when
        running measurements for the first time the flag
        _metric_tracker_labels_created is False.

        Note: A MeasurementSet should not change, the design is that the
        Engine will add another set versus modify an existing one! So,
        This flag need only be set and checked once.
        """
        # safety first!
        if self.metric_tracker is None:
            raise InvalidMeasurementConfiguration("metric_tracker not set")

        # TODO: Consider moving from bool to raise Exception when an
        # entry exists. not needed for MVP.
        for meas in self._measurements:
            # registers using the component def set tracker_label
            ack = self.metric_tracker.register_metric(label=meas.tracker_label)
            if not ack:
                msg = f"{self.name} failed to register {meas.tracker_label}"
                logging.warning(msg)

        # and only perform once
        self._metric_tracker_labels_created = True

    def update_stopwords(self, stopwords: List[str]) -> None:
        """Updates every measurement that relies on stopwords.

        :param stopwords: The stopwords used by measurements.
        :type stopwords: List[str]
        """
        # NOTE: potential revisit this pattern. by having each measure
        # have a copy of the STOPWORDS it may be memory inefficient. The
        # benefit though is that each one is isolated and there should
        # be a minimum number of measurements.

        # update each measurement that supports stopwords
        for meas in self._measurements:
            if meas.features.can_use_stopwords:
                if isinstance(meas, SupportsStopwords):
                    if meas.use_stopwords:
                        meas.stopwords = stopwords

    def _process_measurement_w_data(
        self,
        data: Any,
        meas: Union[
            Measurement,
            Comparison],
        perform_compare_split: bool = False
    ) -> None:
        """Processes measurements

        :param data: The data to measure
        :type data: Any
        :param meas: The measurement
        :type meas: Union[ Measurement, Comparison]
        :param perform_compare_split: do a split?, defaults to False
        :type perform_compare_split: bool, optional
        :raises InvalidMeasurementConfiguration: missing tracker
        :raises InvalidMeasurementConfiguration: unknown split
        :raises InvalidMeasurementConfiguration: uknown type
        """

        # safety first
        if self.metric_tracker is None:
            raise InvalidMeasurementConfiguration("Missing metric_tracker")

        results = []
        if (isinstance(meas, Comparison)):
            if perform_compare_split:
                for row in data:
                    results.append(meas.compare(a=row[0], b=row[1]))
            else:
                # should be checked before invoking this method.
                msg = f"Unknown how to split for comparison {type(data)}"
                logging.error(msg)
                raise InvalidMeasurementConfiguration(msg)

        elif (isinstance(meas, Measurement)):
            for row in data:
                results.append(meas.measure(row))
        else:
            # should be checked before invoking this method.
            msg = f"Unknown measurement type: {type(meas)}"
            logging.error(msg)
            raise InvalidMeasurementConfiguration(msg)

        # safety
        if len(results) != len(data):
            # Don't store results. There is an issue
            msg = f"Failed to properly measure {meas.tracker_label}"
            logging.error(msg)
            return None

        if self.record_as == RecordAs.SUM:
            self.metric_tracker.add_data(
                label=meas.tracker_label,
                value=sum(results))
        elif self.record_as == RecordAs.AVG:
            self.metric_tracker.add_data(
                label=meas.tracker_label,
                value=sum(results) / len(results))
        elif self.record_as == RecordAs.AVG:
            self.metric_tracker.add_data(
                label=meas.tracker_label,
                value=results[-1])
        elif self.record_as == RecordAs.RAW:
            self.metric_tracker.add_raw_data(
                label=meas.tracker_label,
                values=results)
        else:
            msg = f"Unknown value of record_as: {self.record_as}"
            logging.error(msg)
            raise InvalidMeasurementConfiguration(msg)

    def perform_measurements(self, data: Sequence) -> None:
        """Executes the measurements if valid. Increments the
        execution_count if measurements are performed.

        :param data: the data to measure
        :type data: Any
        """
        # TODO: code filters
        # if len(self.filters) > 0:
        #     raise NotImplementedError("DEVELOPMENT NEEDED")

        if self.metric_tracker is None:
            raise InvalidMeasurementConfiguration("metric_tracker not set")

        if LOW_DATA_THRESHOLD is not None:
            if len(data) <= LOW_DATA_THRESHOLD:
                msg = f"{self.name}: low data threshold alert on measure"
                logging.warning(msg)

        # ensure metric tracker is setup (needed with delayed setup)
        if not self._metric_tracker_labels_created:
            self._init_metrics_into_metric_tracker()

        # Get data type
        input_type = process_as(data)
        perform_compare_split = False
        if input_type == MeasInputType.PAIR_AS_LIST:
            perform_compare_split = True

        update_counter = False
        for meas in self._measurements:
            # execute measurement
            if input_type[0] in meas.features.input_type or \
                    input_type[1] in meas.features.input_type:
                update_counter = True
                self._process_measurement_w_data(
                    data=data,
                    meas=meas,
                    perform_compare_split=perform_compare_split)
            elif DEBUG_TO_CONSOLE:
                print(f"Skipping {meas.tracker_label} : "
                      f"{input_type[0]} | {input_type[1]}")

        # wrap-up. Increment the counter.
        if update_counter:
            self.execution_count += 1
