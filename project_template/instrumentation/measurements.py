"""Provides the built-in/included measurements.
"""


from typing import Union, List, Any
from adgtk.common import FactoryBlueprint, ArgumentSetting, ArgumentType
import adgtk.common.css as css
from adgtk.components.data import PresentableRecord
from adgtk.instrumentation import (    
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
        count_min=None,
        count_max=None,
        input_type=[
            MeasInputType.STRING,
            MeasInputType.PRESENTABLE_RECORD,
            MeasInputType.DICTIONARY
        ],
        output_type=MeasOutputType.FLOAT,
        can_use_stopwords=False)

    def __init__(self, tracker_label: str = "text-length"):
        self.name = "String Length"
        self.tracker_label = tracker_label

    def measure(
        self,
        a: Union[str, PresentableRecord, dict]
    ) -> int:
        if isinstance(a, str):
            return len(a)
        elif isinstance(a, PresentableRecord):
            b = f"{a}"
            return len(b)
        elif isinstance(a, dict):
            data_str = f"{a}"
            return len(data_str)

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Text Length</h{header}>"
        html += "<p>This measurement is focused on measuring text length.</p>"

        return html


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
        self.name = "Word count"
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

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Word Count</h{header}>"
        if self.ignore_case and self.use_stopwords:
            html += "<p>This measurement measures the number of words. It "\
                    "uses stopwords and ignores case"
        elif self.ignore_case:
            html += "<p>This measurement measures the number of words. It "\
                    "ignores case but does not have stop word removal set"
        else:
            html += "<p>This measurement measures the number of words. It "\
                    "does not have stop word removal set"
        return html

# ----------------------------------------------------------------------
# Presentable Record / Dict
# ----------------------------------------------------------------------


class MeasureKeyLength:
    """Returns the keys of the data. Useful for tracking/reporting"""
    description = "Returns the keys of the data. Useful for post-processing."
    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "measure-key-length",
        "arguments": {
            "tracker_label": ArgumentSetting(
                default_value="measure-key-length",
                help_str="The label for a metric tracker",
                argument_type=ArgumentType.STRING)
        }
    }

    features = MeasurementFeatures(
        count_min=None,
        count_max=None,
        input_type=[
            MeasInputType.DICTIONARY,
            MeasInputType.PRESENTABLE_RECORD],
        output_type=MeasOutputType.LIST,
        can_use_stopwords=False)

    def __init__(self, tracker_label: str = "measure-key-length"):
        self.tracker_label = tracker_label

    def measure(self, a: Union[dict[str, Any], PresentableRecord]) -> int:
        """Returns the keys as a list. Useful for comparing & measuring
        the number of keys.

        :param a: The item to measure
        :type a: Union[dict[str, Any], PresentableRecord]
        :raises InvalidMeasurementConfiguration: Unexpected data
        :return: The number of keys
        :rtype: int
        """
        if isinstance(a, dict):
            return len(a.keys())
        elif isinstance(a, PresentableRecord):
            data = a.create_copy_of_data()
            return len(data.keys())
        else:
            raise InvalidMeasurementConfiguration

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Measure Keys</h{header}>"
        html += "<p>This measurement is focused on measuring the key count.</p>"

        return html


# ----------------------------------------------------------------------
# Dataset/Datastore/Iterable measurements
# ----------------------------------------------------------------------

class MeasureUnusedKeys:
    """Measures unused keys within the dataset. i.e. overall coverage"""

    description = "The key coverage within a dataset"

    blueprint: FactoryBlueprint = {
        "group_label": "measurement",
        "type_label": "key-coverage",
        "arguments": {
            "expected": ArgumentSetting(
                default_value=[],
                help_str="The list of expected keys. empty for all",
                list_min=0,
                list_arg_type=ArgumentType.STRING,                
                argument_type=ArgumentType.LIST)
        }
    }

    features = MeasurementFeatures(
        count_min=1,
        count_max=None,
        input_type=[
            MeasInputType.ITERABLE,
            MeasInputType.RECORD_STORE,
            MeasInputType.LIST],
        output_type=MeasOutputType.FLOAT,
        can_use_stopwords=False)

    def __init__(self, expected: list):
        self.expected = expected

    def measure(self, a: Any) -> int:
        """Measures an object based on the configuration. it does so by
        counting the number of items in the object.

        :param a: The object to measure
        :type a: Any
        :return: number of items in the object a.
        :rtype: int
        """
        data: list[Any]
        if isinstance(a, dict):
            data = list(a.keys())
        elif isinstance(a, PresentableRecord):
            record_data = a.create_copy_of_data()
            data = list(record_data.keys())
        else:
            raise InvalidMeasurementConfiguration

        counter = 0
        for key in self.expected:
            if key not in data:
                counter += 1

        return counter

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Measure Unused Keys</h{header}>"
        html += "<p>This measurement returns the number of expected "
        html += "keys not in the record.</p>"

        return html


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

    def report(self, header: int = 3) -> str:
        """Generates HTML for reports. Used as part of the Meas Set
        HTML generation.

        :param header: The header, defaults to 3
        :type header: int, optional
        :return: HTML that introduces the measurement.
        :rtype: str
        """
        html = f"<h{header} class=\"{css.MEAS_HEADER_CSS_TAG}\">"
        html += f"Item Count</h{header}>"
        html += "<p>This measurement counts the number of items.</p>"

        return html
