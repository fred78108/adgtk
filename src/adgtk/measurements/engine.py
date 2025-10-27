"""Provides an Engine for measuring a dataset.

This module defines the `MeasurementEngine` class, which facilitates the 
measurement of data using various measurement types and factories. It also 
includes helper functions to validate measurement types.

TODO: Get the scenario logger and set it as the logger for the engine!
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
    """Records and reports on a single label/measurement and all its data"""
    label: str
    description: str
    data: list

class MeasurementReport(TypedDict):
    """A report structure that can be used by an agent to undertstand the
    measurements and associated results"""
    engine_id: str
    measurements: list[MeasurementData]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def supports_measurement_type(func, *args) -> bool:
    """
    Validates if the provided arguments match the expected types of a function.

    Args:
        func: The function whose parameter types are to be validated.
        *args: The arguments to validate against the function's parameter types.

    Returns:
        bool: True if all arguments match the expected types, False otherwise.
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
                    if not any(isinstance(arg, t) for t in get_args(expected_type)):
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
        Initializes the MeasurementEngine.

        Args:
            engine_id (Optional[str]): A unique identifier for the engine.
            add_factory_ids (Optional[list[str]]): A list of factory IDs to 
                register during initialization.
            add_by_type (Optional[measurement_type]): A measurement type to 
                register factories by.
            add_by_tag (Optional[Union[str, list[measurement_type]]]): A tag 
                or list of tags to register factories by.
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
            entries = get_measurements_by_type(add_by_type)
            for entry in entries:
                self.add(entry['factory_id'])
        if add_by_tag is not None:
            entries = get_measurements_by_tag(add_by_tag)
            for entry in entries:                
                self.add(entry['factory_id'])

    def clear_results(self) -> None:
        """Clears all prior measurements but retains the definitions.
        """
        self.metric_tracker.clear_results()

    def get_all_data(self, label:str) -> list:
        """Gets all the data stored for a label

        Args:
            label (str): The label of the measurement

        Returns:
            list: the data
        """
        return self.metric_tracker.get_all_data(label)
    
    def measurement_count(self, label:str)-> int:
        """The number of measurements stored

        Args:
            label (str): the label of the measurement

        Returns:
            int: The count of data stored
        """
        return self.metric_tracker.measurement_count(label)

    def get_average(self, label:str) -> float:
        """Returns the average value for a measurement

        Args:
            label (str): the label of the measurement

        Returns:
            float: The average value
        """
        return self.metric_tracker.get_average(label)

    def get_latest_value(self, label:str)-> float:
        """Gets the latest value recorded

        Args:
            label (str): the label of the measurement

        Returns:
            float: The latest value
        """
        return self.metric_tracker.get_latest_value(label)

    def get_latest_distribution(self, label:str) -> np.ndarray:
        """Gets the latest distribution stored with a label.

        Args:
            label (str): the label of the measurement

        Returns:
            np.ndarray: The latest distribution
        """
        return self.metric_tracker.get_latest_distribution(label)

    def get_description(self, factory_id:str) -> str:
        """Retrieves the description of a measurement.

        Args:
            factory_id (str): The measurement to retrieve

        Returns:
            str: The description
        """
        if factory_id not in self.details.keys():
            raise IndexError("Unable to locate id %s", factory_id)
        
        entry = self.details[factory_id]
        return entry["description"]

        
    def add(self, factory_id: str, **kwargs) -> None:
        """
        Registers a measurement factory with the engine.

        Args:
            factory_id (str): The ID of the factory to register.
            **kwargs: Additional arguments for the factory creation.

        Raises:
            IndexError: If the factory ID is invalid or not found.
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
        Records the results of a measurement in the tracker.

        Args:
            label (str): The tracker label.
            results (list): The data to add.
            record_as (calculation_type, optional): How to record the results. 
                Defaults to "avg".
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
        Performs measurements on the provided dataset.

        Args:
            data (Iterable): The dataset to measure.
            record_as (calculation_type, optional): How to record the results. 
                Defaults to "avg".
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
        Performs measurements on the provided dataset.

        Args:
            data (Iterable): The dataset to measure.
            record_as (calculation_type, optional): How to record the results. 
                Defaults to "avg".
        """
        for label, meas in self.measurements.items():
            all_results = []
            if inspect.isclass(meas):
                meas = cast(ClassBasedComparison, meas)
            else:
                meas = cast(direct_comparison, meas)                
            for a,b in data:
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
        """Saves the data to disk using the pre-defined folder structure

        Args:
            folders (ExperimentRunFolders): The results folders
        """
        self.metric_tracker.save_data(folders)

    def debug_report(self) -> None:
        """Prints a report to screen. Primary purpose is development.        
        """
        print(f"------- Measurement Engine: {self.engine_id} -------")
        max_key_length = max(len(k) for k in self.measurements.keys())
        for k, v in self.measurements.items():
            print(f"{k:<{max_key_length}}  {type(v).__name__}")

    def report(self) -> MeasurementReport:
        """Generates a measurement report based on the defined measurements
        and their associated data.
        
        Returns:
            MeasurementReport: A structured report containing engine ID and 
                all measurement data with labels, descriptions, and values.
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
        """Obtains the latest measurement as a dictionary.

        Returns:
            dict: the last value recorded by metric label
        """
        return self.metric_tracker.export_last_val_to_dict()
