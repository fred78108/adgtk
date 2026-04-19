"""Measurement engine for running and tracking dataset measurements.

This module defines `MeasurementEngine`, which manages measurement factory
registration, executes measurements and comparisons, and records results via
`MetricTracker`.

It also includes helper utilities for validating measurement function
signatures against runtime arguments.
"""

from collections.abc import Iterable
import inspect
from logging import getLogger
from typing import (
    Any,
    Literal,
    Optional,
    TypedDict,
    Union,
    cast,
    get_args,
    get_origin
)
import uuid
import numpy as np
from adgtk.common.defaults import SCENARIO_LOGGER_NAME
from adgtk.common import UnableToMeasureException
from adgtk.tracking import ExperimentRunFolders, MetricTracker
from .factory import create_measurement
from .factory import (
    ClassBasedComparison,
    ClassBasedMeasurement,
    MeasFactoryEntry,
    direct_comparison,
    direct_measurement,
    distribution_measurement,
    distribution_comparison,
    get_measurements_by_tag,
    get_measurements_by_type,
    get_measurement_factory_entry,
    measurement_type,
    supports_factory
)

# ----------------------------------------------------------------------
# Development support only
# ----------------------------------------------------------------------
DEBUG = False

# ----------------------------------------------------------------------
# Structure
# ----------------------------------------------------------------------
calculation_type = Literal["avg", "sum", "max", "min", "raw", "distribution"]


class MeasurementData(TypedDict):
    """Data recorded for a single measurement label."""
    label: str
    description: str
    data: list


class MeasurementReport(TypedDict):
    """Structured report containing all recorded measurements for an engine."""
    engine_id: str
    measurements: list[MeasurementData]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def supports_measurement_type(func, *args) -> bool:
    """
    Return whether the provided arguments match a callable's annotations.

    Args:
        func: Callable to validate.
        *args: Runtime arguments to check against annotated parameter types.

    Returns:
        True if argument count and annotated types are compatible; otherwise
        False.
    """
    sig = inspect.signature(func)
    parameters = sig.parameters
    for i, (_, param) in enumerate(parameters.items()):
        if param.annotation != inspect.Parameter.empty:
            expected_type = param.annotation
            if i < len(args):
                arg = args[i]
                if DEBUG:
                    # Show the expected type and the argument type
                    print(f"Expected type: {expected_type}, "
                          f"Argument type: {type(arg)}")
                # Handle Union types
                if get_origin(expected_type) is Union:
                    if not any(
                        isinstance(arg, t) for t in get_args(expected_type)
                    ):
                        return False
                # Handle regular types
                elif not isinstance(arg, expected_type):
                    return False

    if len(args) != len(parameters):
        return False

    return True
# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------


class MeasurementEngine:
    """Drives measurements of data.

    The `MeasurementEngine` class manages the registration of measurement
    factories, tracks metrics, and performs measurements on datasets.

    Attributes:
        engine_id (Optional[str]): A unique identifier for the engine.
        measurements (dict[str, supports_factory]): A dictionary of registered
            measurement factories.
        details (dict[str, MeasFactoryEntry]): A dictionary containing details
            about each registered measurement factory.
        metric_tracker (MetricTracker): Tracks metrics for the measurements.
        logger: Logger instance for logging engine-related events.
    """

    def __init__(
        self,
        engine_id: Optional[str] = None,
        add_factory_ids: Optional[list[str]] = None,
        add_by_type: Optional[measurement_type] = None,
        add_by_tag: Optional[Union[str, list[measurement_type]]] = None
    ) -> None:
        """
        Initialize a new measurement engine.
        """
        self.engine_id = engine_id or str(uuid.uuid4())
        self.measurements: dict[str, supports_factory] = {}
        self.details: dict[str, MeasFactoryEntry] = {}
        self.metric_tracker = MetricTracker(
            name=self.engine_id,
            purpose="measurement"
        )
        self.logger = getLogger(SCENARIO_LOGGER_NAME)

        if add_factory_ids is not None:
            for entry in add_factory_ids:
                self.add(entry)
        if add_by_type is not None:
            tag_entries = get_measurements_by_type(add_by_type)
            for tag_entry in tag_entries:
                assert isinstance(tag_entry, dict)
                self.add(tag_entry['factory_id'])
        if add_by_tag is not None:
            tag_entries = get_measurements_by_tag(add_by_tag)
            for tag_entry in tag_entries:
                assert isinstance(tag_entry, dict)
                self.add(tag_entry['factory_id'])

    def clear_results(self) -> None:
        """Clear all recorded results while keeping metric registrations."""
        self.metric_tracker.clear_results()

    def get_all_data(self, label: str) -> list:
        """Return all values currently recorded for a metric label.

        Args:
            label: Metric label.

        Returns:
            Recorded values for the label.
        """
        return self.metric_tracker.get_all_data(label)

    def measurement_count(self, label: str) -> int:
        """Return the number of recorded values for a metric label.

        Args:
            label: Metric label.

        Returns:
            Number of values recorded for the label.
        """
        return self.metric_tracker.measurement_count(label)

    def get_average(self, label: str) -> float:
        """Return the average recorded value for a metric label.

        Args:
            label: Metric label.

        Returns:
            Average value.
        """
        return self.metric_tracker.get_average(label)

    def get_latest_value(self, label: str) -> float:
        """Return the most recently recorded scalar value for a label.

        Args:
            label: Metric label.

        Returns:
            Latest scalar value.
        """
        return self.metric_tracker.get_latest_value(label)

    def get_latest_distribution(self, label: str) -> np.ndarray:
        """Return the most recently recorded distribution for a label.

        Args:
            label: Metric label.

        Returns:
            Latest distribution array.
        """
        return self.metric_tracker.get_latest_distribution(label)

    def get_description(self, factory_id: str) -> str:
        """Return the description for a registered measurement factory.

        Args:
            factory_id: Measurement factory ID.

        Returns:
            Factory description text.
        """
        if factory_id not in self.details.keys():
            raise IndexError("Unable to locate id %s", factory_id)
        entry = self.details[factory_id]
        return entry["description"]

    def add(self, factory_id: str, **kwargs) -> None:
        """
        Register a measurement factory and corresponding metric label.

        Args:
            factory_id: Factory ID to register.
            **kwargs: Reserved for future factory-creation options.

        Raises:
            IndexError: If the factory ID is invalid.
        """
        try:
            entry = get_measurement_factory_entry(factory_id)
            self.measurements[factory_id] = create_measurement(factory_id)
            self.details[factory_id] = entry
            self.metric_tracker.register_metric(label=factory_id)
        except IndexError:
            self.logger.error(
                "Measurement engine %s unable to add %s due to already "
                "registered. Ignoring request",
                self.engine_id, factory_id)

    def _update_tracker(
        self,
        label: str,
        results: list,
        record_as: calculation_type = "avg"
    ) -> None:
        """
        Aggregate measurement results and store them in the metric tracker.

        Args:
            label: Metric label.
            results: Raw results returned by a measurement.
            record_as: Aggregation/storage mode ("avg", "sum", "max", "min",
                "raw", or "distribution").
        """
        if len(results) == 0:
            results = [0]
            self.logger.warning(
                "Measurement engine %s performed zero measurements.",
                self.engine_id)
        if record_as == "avg":
            value = sum(results) / len(results)
            self.metric_tracker.add_data(label=label, value=value)
        elif record_as == "max":
            value = max(results)
            self.metric_tracker.add_data(label=label, value=value)
        elif record_as == "min":
            value = min(results)
            self.metric_tracker.add_data(label=label, value=value)
        elif record_as == "sum":
            value = sum(results)
            self.metric_tracker.add_data(label=label, value=value)
        elif record_as == "raw":
            self.metric_tracker.add_raw_data(label=label, values=results)

    def measure(
        self,
        data: Iterable,
        record_as: calculation_type = "avg"
    ) -> None:
        """
        Run registered measurements against an input dataset.

        Each measurement is first attempted with the full dataset. If argument
        compatibility fails, the engine falls back to per-item iteration.

        Args:
            data: Input dataset.
            record_as: Aggregation/storage mode for recorded results.
        """
        for label, meas in self.measurements.items():
            all_results = []
            if inspect.isclass(meas):
                meas = cast(ClassBasedMeasurement, meas)
            else:
                meas = cast(direct_measurement, meas)

            # first, does the measurement want all the data?
            if supports_measurement_type(meas, data):
                try:
                    result = meas(data)
                    all_results.append(result)
                except UnableToMeasureException:
                    # NO-OP
                    pass
            else:
                # if not, then iterate over the values
                # this is a fallback. measurements should be designed to
                # consider iterable values.
                for entry in data:
                    # Verify if the measurement type is supported
                    try:
                        if supports_measurement_type(meas, entry):
                            result = meas(entry)
                            if isinstance(result, (int, float)):
                                all_results.append(result)
                            elif isinstance(result, list):
                                all_results.extend(result)
                        else:
                            self.logger.warning(
                                f"{self.engine_id} No valid data for {label}. "
                                "skipping measure")
                            break
                    except UnableToMeasureException:
                        # NO-OP
                        pass
            self._update_tracker(
                label=label, results=all_results, record_as=record_as)

    def measure_dataset_distribution(self, dataset: Iterable) -> None:
        """Run distribution measurements that operate on the full dataset.

        Args:
            dataset: Dataset to measure.
        """
        for label, meas in self.measurements.items():
            all_results = []
            if inspect.isclass(meas):
                meas = cast(ClassBasedMeasurement, meas)
            else:
                meas = cast(distribution_measurement, meas)
            # now measure
            if supports_measurement_type(meas, dataset):
                try:
                    result = meas(dataset)
                    all_results.append(result)
                except UnableToMeasureException:
                    # NO-OP
                    pass
            self._update_tracker(
                label=label,
                results=all_results,
                record_as="distribution"
            )

    def compare_dataset_distribution(
        self,
        dataset_one: Iterable,
        dataset_two: Iterable,
        record_as: calculation_type = "avg"
    ) -> None:
        """Compare two datasets using distribution-based comparison functions.

        Args:
            dataset_one: First dataset.
            dataset_two: Second dataset.
            record_as: Aggregation/storage mode for recorded results.
        """
        for label, meas in self.measurements.items():
            all_results = []
            if inspect.isclass(meas):
                meas = cast(ClassBasedComparison, meas)
            else:
                meas = cast(distribution_comparison, meas)
            if supports_measurement_type(meas, dataset_one, dataset_two):
                try:
                    result = meas(dataset_one, dataset_two)
                    all_results.append(result)
                except UnableToMeasureException:
                    # NO-OP
                    pass
            self._update_tracker(
                label=label,
                results=all_results,
                record_as=record_as
            )

    def compare(
        self,
        data: Iterable[tuple[Any, Any]],
        record_as: calculation_type = "avg"
    ) -> None:
        """
        Run pairwise comparison measurements over an iterable of value pairs.

        Args:
            data: Iterable of `(a, b)` pairs to compare.
            record_as: Aggregation/storage mode for recorded results.
        """
        for label, meas in self.measurements.items():
            all_results = []
            if inspect.isclass(meas):
                meas = cast(ClassBasedComparison, meas)
            else:
                meas = cast(direct_comparison, meas)
            for a, b in data:
                # Verify if the measurement type is supported
                if supports_measurement_type(meas, a, b):
                    result = meas(a, b)
                    if isinstance(result, (int, float)):
                        all_results.append(result)
                    elif isinstance(result, list):
                        all_results.extend(result)
            self._update_tracker(
                label=label, results=all_results, record_as=record_as)

    def save_data(self, folders: ExperimentRunFolders) -> None:
        """Persist tracked metric data to disk.

        Args:
            folders: Predefined experiment output folder structure.
        """
        self.metric_tracker.save_data(folders)

    def debug_report(self) -> None:
        """Print a simple console report of registered measurements."""
        print(f"------- Measurement Engine: {self.engine_id} -------")
        max_key_length = max(len(k) for k in self.measurements.keys())
        for k, v in self.measurements.items():
            print(f"{k:<{max_key_length}}  {type(v).__name__}")

    def report(self) -> MeasurementReport:
        """Build and return a structured report of all recorded measurements.

        Returns:
            Report containing engine ID and per-measurement data.
        """
        measurements_data = []

        for factory_id in self.measurements.keys():
            # Get all data for this measurement
            data = self.get_all_data(factory_id)

            # Get description from details
            description = self.get_description(factory_id)

            measurement_data = MeasurementData(
                label=factory_id,
                description=description,
                data=data
            )
            measurements_data.append(measurement_data)

        return MeasurementReport(
            engine_id=self.engine_id,
            measurements=measurements_data
        )

    def export_last_val_to_dict(self) -> dict:
        """Return the latest recorded value for each metric label.

        Returns:
            Dictionary mapping metric label to latest recorded value.
        """
        return self.metric_tracker.export_last_val_to_dict()
