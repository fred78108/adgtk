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
from enum import Enum, auto
from typing import (
    Union,
    List,
    Literal,
    Final,
    Any,
    Sequence)
from adgtk.common import (
    ComponentDef,
    FactoryBlueprint,
    ArgumentSetting,
    ListArgumentSetting,
    ArgumentType)
from adgtk.tracking import MetricTracker
from adgtk.factory.base import ComponentFeatures
from adgtk.factory.component import ObjectFactory
from adgtk.journals import ExperimentJournal
from adgtk.data import (
    RecordStore,
    CanFindRandomRecord,
    CanGetAllRecords,
    SupportsFiltering,
    PresentableRecord,
    PresentableGroup)
from .base import (
    MeasInputType,
    SupportsMeasDef,
    Measurement,
    SupportsStopwords,
    Comparison,
    SupportsMeasSetOps,
    ComponentFeatures,
    InvalidMeasurementConfiguration)


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/instrumentation/test_engine.py


# ----------------------------------------------------------------------
# Module Constants
# ----------------------------------------------------------------------
DEBUG_TO_CONSOLE = False
DEFAULT_MAX_IN_GROUP: Final[int] = 1000000  # for min/max checks if None
LOW_DATA_THRESHOLD: int = 2       # Set to None to disable


class RecordAs(Enum):
    """Used internally to this module to keep things consistent"""
    SUM = auto()
    AVG = auto()
    LATEST = auto()
    RAW = auto()

# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------


def convert_record_as(
    record_as: Literal["sum", "avg", "latest", "raw"]
) -> RecordAs:
    """Converts the string into an Enum

    :param record_as: the text mapping to RecordAs
    :type record_as: Literal[&quot;sum&quot;, &quot;avg&quot;, &quot;latest&quot;, &quot;raw&quot;]
    :raises InvalidMeasurementConfiguration: Unknown record_as value
    :return: The converted value
    :rtype: RecordAs
    """
    if record_as == "sum":
        return RecordAs.SUM
    elif record_as == "avg":
        return RecordAs.AVG
    elif record_as == "latest":
        return RecordAs.LATEST
    elif record_as == "raw":
        return RecordAs.RAW
    else:
        msg = f"Unknown record_as: {record_as} setting."
        raise InvalidMeasurementConfiguration(msg)


def process_as(data: Any) -> tuple:
    """Seeks to provide data

    :param data: The data to inspect
    :type data: Any
    :return: a tuple (process data, if iterable the items as)
    :rtype: Tuple[MeasInputType]
    """
    if isinstance(data, PresentableRecord):
        return (MeasInputType.PRESENTABLE_RECORD,
                MeasInputType.NOOP)
    elif isinstance(data, str):
        return (MeasInputType.STRING, MeasInputType.NOOP)
    elif isinstance(data, PresentableGroup):
        # A presentable group by design only has presentable records
        return (
            MeasInputType.PRESENTABLE_GROUP,
            MeasInputType.PRESENTABLE_RECORD)

    elif isinstance(data, RecordStore):
        a = MeasInputType.UNKNOWN
        if len(data) == 0:
            return (MeasInputType.EMPTY, None)
        # get a sample
        elif isinstance(data, CanFindRandomRecord):
            random_record = data.find_random_record()
        elif isinstance(data, CanGetAllRecords):
            # lot slower, but better than unable to match
            random_record = data.get_all_records()
        else:
            logging.error("Unable to determine protocol for process_as")

        a, _ = process_as(random_record[0])
        return (MeasInputType.RECORD_STORE, a)

    elif isinstance(data, list):
        if len(data) == 0:
            return (MeasInputType.EMPTY, MeasInputType.NOOP)

        a, _ = process_as(data[0])

        if len(data) == 2:
            return (MeasInputType.PAIR_AS_LIST, a)

        return (MeasInputType.LIST, a)

    elif isinstance(data, Sequence):
        if len(data) == 0:
            return (MeasInputType.EMPTY, MeasInputType.NOOP)
        sample = data[0]
        a, _ = process_as(sample)
        if a is not MeasInputType.UNKNOWN:
            return (MeasInputType.ITERABLE, a)

        return (MeasInputType.ITERABLE, MeasInputType.NOOP)

    return (MeasInputType.UNKNOWN, MeasInputType.UNKNOWN)


def min_max_group_check(meas: SupportsMeasDef, data: PresentableGroup) -> bool:
    """checking for the director the different combinations makes the
    method is_measurable_with a bit too long. breaking out this code
    into a function for readability. This function validates whether
    the data and measurement requirements are met.

    :param meas: The measurement to check
    :type meas: SupportsMeasDef
    :type data: PresentableGroup
    :return: True if valid measurement for this group, else False
    :rtype: bool
    """
    min_val = meas.features.count_min
    max_val = meas.features.count_max

    if min_val is None:
        min_val = 0
    if max_val is None:
        max_val = DEFAULT_MAX_IN_GROUP

    record_count = len(data)

    if min_val <= record_count <= max_val:
        return True

    return False

# ----------------------------------------------------------------------
# MeasurementSet
# ----------------------------------------------------------------------


class MeasurementSet:
    """Provides a protocol for a pre-defined grouping of measurements
    """
    blueprint: FactoryBlueprint = {
        "group_label": "measurement-set",
        "type_label": "single",
        "arguments": {
            "name": ArgumentSetting(
                argument_type=ArgumentType.STRING,
                default_value="default",
                help_str="The name of the measurement-set"),
            "measurement_def": ListArgumentSetting(
                argument_type=ArgumentType.LIST,
                default_value=[],
                help_str="A measurement that are part of this set",
                list_arg_type=ArgumentType.BLUEPRINT,
                list_arg_default_value="measurement"),
            "expected_result": ArgumentSetting(
                help_str="The result type. valid options are: number...",
                default_value="number",
                argument_type=ArgumentType.STRING),
            "record_as": ArgumentSetting(
                help_str="The results should be saved as an avg, sum...",
                default_value="avg",
                argument_type=ArgumentType.STRING),
            "measurement_type": ArgumentSetting(
                help_str="The measurement type",
                default_value="single",
                argument_type=ArgumentType.STRING),
            "filters": ListArgumentSetting(
                help_str="Filters for measuring 'not used yet'",
                default_value=[],
                argument_type=ArgumentType.LIST,
                list_arg_type=ArgumentType.STRING,
                list_arg_default_value=""),
            "create_metric_tracker": ArgumentSetting(
                help_str="Create a metric tracker if not passed",
                default_value=True,
                argument_type=ArgumentType.BOOL)
        }
    }

    features = ComponentFeatures(
        object_factory=True,
        experiment_journal=True)
    # Note, no features at this time.

    def __init__(
        self,
        factory: ObjectFactory,
        name: str,
        measurement_def: Union[List[ComponentDef], None],
        expected_result: Literal["number", "list", "string"],
        record_as: Literal["sum", "avg", "latest", "raw"],
        measurement_type: Literal["single", "compare", "dataset"],
        filters: List[SupportsFiltering],
        create_metric_tracker: bool = True,
        journal: Union[ExperimentJournal, None] = None
    ) -> None:
        """MeasurementSet ensures that the engine can properly
        interact with the individual measurements.
        :param factory: The object factory
        :type factory: ObjectFactory
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
        :param create_metric_tracker: Create a local metric tracker?,
            defaults to True
        :type create_metric_tracker: bool
        :param journal: The Experiment journal, optional, defaults to None
        :type journal: ExperimentJournal
        """
        self.name = name
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

        self.filters: List[SupportsFiltering] = []
                    
        if filters is not None:            
            for candidate in filters:
                if isinstance(candidate, SupportsFiltering):
                    self.filters.append(candidate)            

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
        if len(self.filters) > 0:
            raise NotImplementedError("DEVELOPMENT NEEDED")

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


# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------


class MeasurementEngine:
    """Responsible for providing a wrapper around a group of measurement
    sets. It also exposes a measurement tracker for consumption of the
    measurement results. The overall design is lightweight, it invokes
    the measurement sets for interacting with their measurements."""

    blueprint: FactoryBlueprint = {
        "group_label": "measurement-engine",
        "type_label": "simple",
        "arguments": {
            "measurement_set_def": ListArgumentSetting(
                help_str="A measurement set for this engine",
                argument_type=ArgumentType.LIST,
                default_value="measurement-set",
                list_arg_type=ArgumentType.BLUEPRINT,
                list_arg_default_value="measurement-set"),
            "name": ArgumentSetting(
                help_str="the name of the measurement engine",
                default_value="default",
                argument_type=ArgumentType.STRING
            )
        }
    }
    features = ComponentFeatures(
        object_factory=True,
        experiment_journal=True)

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
