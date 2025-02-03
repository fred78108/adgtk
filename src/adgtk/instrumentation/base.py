"""Foundation for instrumentation.

# Module Design notes - Key objects

- Measurement / comparison:
- Performs the measurement
- MeasurementSet
-- a group of measurements / comparisons.
-- The filters are global. For example, a ds and you want matches only
-- The measure_only is defined per measure. This will allow a set to
   contain a mixture of measurements.
- MeasurementEngine
-- Can support multiple MeasurementSets at one time.
-- There can be more than one MeasurementEngine. If the name is set it
   will prepend its name to any output.

# Architecture Principles

- all Measurements are Classes to ensure consistency between those that
  do and those that do not require maintaining internal structure.
- The engine, the measurement set, and the measurements are all easy to
  replace if needed by the user. However, for most use cases this will
  likely not be needed.
"""

from __future__ import annotations
from enum import Enum, auto
from typing import (
    Protocol,
    Union,
    runtime_checkable,
    Any,
    List)
from dataclasses import dataclass
from adgtk.common import FolderManager
from adgtk.tracking import MetricTracker

# ----------------------------------------------------------------------
# testing
# ----------------------------------------------------------------------
# py -m pytest -s test/folder/.py


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

DEBUG_TO_CONSOLE = False

# ----------------------------------------------------------------------
# Exceptions
# ----------------------------------------------------------------------


class InvalidMeasurementConfiguration(Exception):
    """Used for when a requested configuration is not valid"""

    default_msg = "Invalid measurement configuration. Unable to measure."

    def __init__(self, message: str = default_msg):
        super().__init__(message)

# ----------------------------------------------------------------------
# Protocols & Types
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# for measurement check
# ----------------------------------------------------------------------

class MeasInputType(Enum):
    """Used for code maintance internally. Use the loosest setting for
    example a Data Store is iterable, and the measurement also supports
    a List and other Iterables then the value should be ITERABLE. The
    Invoking measurement should always be watching for an Exception so
    if its invalid then continue operations without stopping, simply 
    skipping the measurement for the given data.

    The ANY and custom are for extensibility. The ANY sends all and
    expects the measurement to handle the different types.
    """
    PRESENTABLE_GROUP = auto()  # a presentable group
    PRESENTABLE_RECORD = auto()  # a presentable record
    RECORD_STORE = auto()       # a data store
    PAIR_AS_LIST = auto()       # a pair within a list.
    DICTIONARY = auto()         # a dictionary
    LIST = auto()               # a list
    ITERABLE = auto()           # not one of the above but iterates
    EMPTY = auto()              # iterable/ds/list but empty
    STRING = auto()             # a string
    UNKNOWN = auto()            # if all else fails
    NOOP = auto()               # do not process
    ANY = auto()                # Future / user use


class MeasOutputType(Enum):
    """Used for signaling the caller of a measurement object the
    expected output. 4 custom types for user to extend if needed. The
    invoker of the object must be capable of handling the response."""
    FLOAT = auto()
    INT = auto()
    LIST = auto()

# ----------------------------------------------------------------------
# Measurement specific Protocols
# ----------------------------------------------------------------------


@runtime_checkable
class SupportsStopwords(Protocol):
    """The item supports stop word actions"""
    stopwords: List[str]    # updates post init
    use_stopwords: bool     # flag configured at init


# ----------------------------------------------------------------------
# Base structure
# ----------------------------------------------------------------------


class RecordAs(Enum):
    """Used internally to this module to keep things consistent"""
    SUM = auto()
    AVG = auto()
    LATEST = auto()
    RAW = auto()


@dataclass
class MeasurementFeatures:
    """Supported measurement features"""
    input_type: List[MeasInputType]
    output_type: MeasOutputType
    can_use_stopwords: bool
    count_min: Union[int, None]
    count_max: Union[int, None]


@runtime_checkable
class SupportsMeasDef(Protocol):
    """The base for both measurements (direct) and comparisons"""
    features: MeasurementFeatures
    tracker_label: str


@runtime_checkable
class Measurement(SupportsMeasDef, Protocol):
    """Although a bit more code than calling a function directly the
    approach with this Protocol is to ensure consistency and keep the
    complexity at configuration and not within the factory. By using a
    measurement Class this will allow for both those without and those
    with a need to maintain an internal structure, objects, etc.
    """

    # plot_type: Literal["line", "bar", "scatter", "hist"]  # TODO: needed?

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """

    def measure(self, a: Any) -> Any:
        """Measures a single item

        :param a: The item to measure
        :type a: Any
        :return: The measurement result
        :rtype: Any
        """


@runtime_checkable
class Comparison(SupportsMeasDef, Protocol):
    """This Protocol ensures that the comparion measurements remain
    consistent and thus allowing creation by a factory and invoked by
    a measurement engine. By using a class instead of a function allows
    for consistency between measurements that need an internal structure
    and those that do not.
    """

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """

    def compare(self, a: Any, b: Any) -> Any:
        """compares two objects (string, record, etc)

        :param a: _description_
        :type a: Any
        :param b: _description_
        :type b: Any
        :return: _description_
        :rtype: Any
        """


class SupportsMeasSetOps(Protocol):
    """Provides a protocol for a pre-defined grouping of measurements.
    Using a protocol as the minimum required by the engine for easy
    extensibility but for most users they can use MeasurementSet as
    defined at instrumentation.MeasurementSet.
    """
    metric_tracker: Union[MetricTracker, None]
    name: str               # name of the measurement set
    engine_name: str        # name of the associated engine

    def update_stopwords(self, stopwords: List[str]) -> None:
        """Updates every measurement that relies on stopwords

        :param stopwords: The stopwords used by measurements.
        :type stopwords: List[str]
        """

    def perform_measurements(self, data: Any) -> None:
        """Executes the measurements currently active. All results are
        store in the measurement tracker.

        :param data: the data to measure
        :type data: Any
        """

    def register_metric_tracker(self, metric_tracker: MetricTracker) -> None:
        """Registers metric labels into a metric_tracker.

        :param metric_tracker: The metric tracker to register to
        :type metric_tracker: MetricTracker
        """

    # NOTE: do I want this in a set or create a new set??
    def add_measurement(self, measurement: SupportsMeasDef):
        """Adds a measurement to a measurement set

        :param measurement: _description_
        :type measurement: SupportsMeasDef
        """

    def remove_measurement(self, name: str):
        """Removes a measurement if one exists

        :param name: the name of the measurement to remove
        :type name: str
        """

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
        :param header: The header, defaults to "h2"
        :type header: int, optional

        :return: HTML that can be used in a report.
        :rtype: str
        """


class MeasurementExecution(Protocol):
    """This is the Protocol for a Measurement Engine.The base Engine is
    expected to work for most use cases but by design can be replaced if
    needed in the future by users of the package."""
    measurement_results: MetricTracker

    def remove_measurement_set(self, name: str, remove_data: bool) -> None:
        """Removes a measurement set if one exists along

        :param name: The name of the measurement set to remove
        :type name: str
        :param remove_data: Also remove the tracking data
        :type remove_data: bool
        """

    def add_measurement_set(self, measurement_set: Any) -> None:
        """Adds a measurement set to the list of measures to perform

        :param measurement_set: The measurement set to add
        :type measurement_set: Any
        """

    def perform_measurements(self, data: Any) -> None:
        """Executes the measurements currently active. All results are
        store in the measurement tracker.

        :param data: the data to measure
        :type data: Any
        """

    def create_html_and_export(
        self,
        experiment_name: str,
        settings_file_override: Union[str, None] = None,
        header: int = 1
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
