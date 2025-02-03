"""Provides the built-in/included measurements.
"""


from typing import Union, List, Any
from adgtk.common import FactoryBlueprint, ArgumentSetting, ArgumentType
# from adgtk.factory import FactoryImplementable
from adgtk.data import PresentableRecord
# from adgtk.utils.measurements import measure_only_check
from .base import (
    InvalidMeasurementConfiguration,
    MeasInputType,
    MeasOutputType,
    MeasurementFeatures)


# ----------------------------------------------------------------------
#
# ----------------------------------------------------------------------
# py -m pytest -s test/instrumentation/test_measurements.py


# ----------------------------------------------------------------------
# Functions
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# Text measurements
# ----------------------------------------------------------------------

class MeasureTextLength:
    """Measure a strings length"""
    description = "Measures the char length of a string"
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "text-length",
        "arguments": {
            "tracker_label": ArgumentSetting(
                default_value="text-length",
                help_str="The label for a metric tracker",
                argument_type=ArgumentType.STRING)
        }
    }
    features = MeasurementFeatures(
        object_factory=False,
        experiment_journal=False,
        count_min=None,
        count_max=None,
        input_type=[MeasInputType.STRING, MeasInputType.PRESENTABLE_RECORD],
        output_type=MeasOutputType.FLOAT,
        can_use_stopwords=False)

    def __init__(self, tracker_label: str = "text-length"):
        self.tracker_label = tracker_label

    def measure(self, a: Union[str, PresentableRecord]) -> int:
        if isinstance(a, str):
            return len(a)
        elif isinstance(a, PresentableRecord):
            b = f"{a}"
            return len(b)


class MeasureWordCount:
    """Measures the number of words in a text"""
    description = "Measures the number of words in a string"
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "word-count",
        "arguments": {
            "tracker_label": ArgumentSetting(
                default_value="word-count",
                help_str="The label for a metric tracker",
                argument_type=ArgumentType.STRING),
            "seperator": ArgumentSetting(
                default_value=None,
                help_str="The seperator for words",
                argument_type=ArgumentType.STRING),
            "use_stopwords": ArgumentSetting(
                default_value=False,
                help_str="Use stopwords",
                argument_type=ArgumentType.BOOL),
            "ignore_case": ArgumentSetting(
                default_value=True,
                help_str="Ignore case",
                argument_type=ArgumentType.BOOL)
        }
    }
    features = MeasurementFeatures(
        object_factory=False,
        experiment_journal=False,
        count_min=None,
        count_max=None,
        input_type=[MeasInputType.STRING, MeasInputType.PRESENTABLE_RECORD],
        output_type=MeasOutputType.FLOAT,
        can_use_stopwords=True)

    def __init__(
        self,
        tracker_label: str = "word-count",
        use_stopwords: bool = False,
        stopwords: Union[List[str], None] = None,
        seperator: Union[str, None] = None,
        ignore_case: Union[bool, None] = True
    ):
        """Initializes a word counter. By design the stop words are
        set at runtime and not on init. This allows delayed setting as
        well as updating at runtime. These updates are done at runtime
        by the MeasurementEngine if the flag use_stopwords is set.

        :param use_stopwords: flag for loading post init stopwords,
            defaults to False
        :type stopwords: bool
        :param seperator: _description_, defaults to None
        :type seperator: Union[str, None], optional
        :param ignore_case: _description_, defaults to True
        :type ignore_case: Union[bool, None], optional
        """
        self.use_stopwords = use_stopwords
        self.seperator = seperator
        self.stopwords = stopwords
        self.ignore_case = ignore_case

        self.tracker_label = tracker_label
        if tracker_label == "word-count":
            if use_stopwords:
                self.tracker_label = f"{tracker_label}.w_stopwords"

    def measure(self, a: Union[str, PresentableRecord]) -> int:

        if isinstance(a, str):
            b = a
        elif isinstance(a, PresentableRecord):
            b = f"{a}"
            return len(b)

        if self.ignore_case:
            # assumes stopword list is all lower case. See param on init
            b = b.lower()

        # separate the words
        if self.seperator is not None:
            words = b.split(sep=self.seperator)
        else:
            words = b.split()

        # now filter for stop words
        if self.stopwords is not None and self.use_stopwords:
            filtered_words = [x for x in words if x not in self.stopwords]
            return len(filtered_words)

        return len(words)


# ----------------------------------------------------------------------
# Presentable Record / Dict
# ----------------------------------------------------------------------

class MeasureKeys:
    """Returns the keys of the data. Useful for tracking/reporting"""
    description = "Returns the keys of the data. Useful for post-processing."
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "measure-keys",
        "arguments": {
            "tracker_label": ArgumentSetting(
                default_value="measure-keys",
                help_str="The label for a metric tracker",
                argument_type=ArgumentType.STRING)
        }
    }

    features = MeasurementFeatures(
        object_factory=False,
        experiment_journal=False,
        count_min=None,
        count_max=None,
        input_type=[
            MeasInputType.DICTIONARY,
            MeasInputType.PRESENTABLE_RECORD],
        output_type=MeasOutputType.LIST,
        can_use_stopwords=False)

    def __init__(self, tracker_label: str = "measure-keys"):
        self.tracker_label = tracker_label

    def measure(self, a: Union[dict[str, Any], PresentableRecord]) -> list:
        """Returns the keys as a list. Useful for comparing & measuring
        the keys. Can be used as a building block for other wrapper
        measurements or directly.

        :param a: The item to measure
        :type a: Union[dict[str, Any], PresentableRecord]
        :raises InvalidMeasurementConfiguration: Unexpected data
        :return: A list of the keys
        :rtype: list
        """
        if isinstance(a, dict):
            return list(a.keys())
        elif isinstance(a, PresentableRecord):
            data = a.create_copy_of_data()
            return list(data.keys())
        else:
            raise InvalidMeasurementConfiguration


# ----------------------------------------------------------------------
# Dataset/Datastore/Iterable measurements
# ----------------------------------------------------------------------


class MeasureItemCount:
    """Measure the number of items in an Iterable item such a list."""
    description = "Returns the number of items in an Iterable."
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "item-count",
        "arguments": {
            "tracker_label": ArgumentSetting(
                default_value="item-count",
                help_str="The label for a metric tracker",
                argument_type=ArgumentType.STRING)
        }
    }

    features = MeasurementFeatures(
        object_factory=False,
        experiment_journal=False,
        count_min=None,
        count_max=None,
        input_type=[
            MeasInputType.ITERABLE,
            MeasInputType.RECORD_STORE,
            MeasInputType.LIST],
        output_type=MeasOutputType.INT,
        can_use_stopwords=False)

    def __init__(
        self,
        tracker_label: str = "item-count"
    ) -> None:
        """Creates an instance of MeasureItemCount. Care should be taken
        if using a more open filter such as iterable and any that the
        results are as expected.

        :param measure_only: limit measurments to, defaults to [Iterable]
        :type measure_only: tuple[Literal[&quot;datastore&quot;,
            &quot;Iterable&quot;]], optional
        """
        self.tracker_label = tracker_label

    def measure(self, a: Any) -> int:
        """Measures an object based on the configuration. it does so by
        counting the number of items in the object.

        :param a: The object to measure
        :type a: Any
        :return: number of items in the object a.
        :rtype: int
        """
        return len(a)
